#!/usr/bin/env python3
"""Reproducible D1P-12R WarpToad artifact and honest-proof fixture runner.

The runner operates only in results/raw/D1P-12R.  It records command output,
wall time, observed resident memory and free disk, refuses a third proof
attempt, and gives each proof command a hard 30-minute deadline.  A proof
attempt is consumed only when the TypeScript harness writes its marker
immediately before calling the pinned project's createProof function.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-12R"
SOURCE = RAW / "workspace/source"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
FIELD_MODULUS = 21888242871839275222246405745257275088548364400416034343698204186575808495617
ARTIFACT = SOURCE / "frontend/src/lib/circuits/withdraw.json"
TARGET_ARTIFACT = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
VERIFIER = SOURCE / "backend/contracts/verifier/WithdrawVerifier.sol"
HARNESS_TEMPLATE = ROOT / "scripts/fixtures/d1p_12r_warptoad_fixture.ts"
HARNESS = SOURCE / "backend/test/d1p12r.fixture.ts"
VK_TEMPLATE = ROOT / "scripts/fixtures/d1p_12r_generate_vk.ts"
VK_HELPER = SOURCE / "backend/scripts/d1p12rGenerateVk.ts"
ATTEMPT_LEDGER = RAW / "proof-attempts.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, base: Path = SOURCE) -> dict:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def process_tree_rss_kib(root_pid: int) -> int:
    """Best-effort resident-memory sum for a process and its descendants."""
    try:
        out = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,rss="], text=True,
            capture_output=True, timeout=5, check=True,
        ).stdout
        rows = []
        for line in out.splitlines():
            fields = line.split()
            if len(fields) == 3:
                rows.append(tuple(map(int, fields)))
        wanted = {root_pid}
        changed = True
        while changed:
            changed = False
            for pid, ppid, _rss in rows:
                if ppid in wanted and pid not in wanted:
                    wanted.add(pid)
                    changed = True
        return sum(rss for pid, _ppid, rss in rows if pid in wanted)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 extra_env: dict[str, str] | None = None) -> dict:
    LOGS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    stdout_path = LOGS / f"{label}.stdout.txt"
    stderr_path = LOGS / f"{label}.stderr.txt"
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started_at = utc_now()
    started = time.monotonic()
    max_rss = 0
    min_free = shutil.disk_usage(ROOT).free
    timed_out = False
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, text=True, stdout=stdout, stderr=stderr,
            start_new_session=True,
        )
        while proc.poll() is None:
            max_rss = max(max_rss, process_tree_rss_kib(proc.pid))
            min_free = min(min_free, shutil.disk_usage(ROOT).free)
            if time.monotonic() - started >= timeout:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(1)
        exit_code = proc.wait()
    record = {
        "schema": "bindcheck.d1p12r.command/v1",
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "wall_seconds": round(time.monotonic() - started, 3),
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "max_process_tree_rss_kib_observed": max_rss,
        "min_free_disk_bytes_observed": min_free,
        "stdout": file_record(stdout_path, RAW),
        "stderr": file_record(stderr_path, RAW),
    }
    write_json(RECORDS / f"{label}.json", record)
    return record


def require_checkout() -> None:
    if not (SOURCE / ".git").exists():
        raise SystemExit(f"missing Git checkout: {SOURCE}")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    if head != PIN:
        raise SystemExit(f"wrong checkout revision: {head}")


def pnpm_argv(*args: str) -> list[str]:
    """Use the pinned package manager without relying on a global pnpm."""
    corepack = shutil.which("corepack")
    if corepack:
        return [corepack, "pnpm", *args]
    npx = shutil.which("npx")
    if not npx:
        raise SystemExit("neither corepack nor npx is available for pnpm@10.8.1")
    return [npx, "--yes", "pnpm@10.8.1", *args]


def inventory() -> int:
    require_checkout()
    d1p11 = json.loads((ROOT / "results/raw/D1P-11/retrieved-source-hashes.json").read_text())
    expected = {
        item["path"]: item["sha256"] for item in d1p11["sources"]
        if item.get("application") == "warp-toad"
    }
    matched = []
    for relative, expected_hash in expected.items():
        path = SOURCE / relative
        matched.append({
            **file_record(path), "expected_sha256": expected_hash,
            "matches_d1p11": sha256(path) == expected_hash,
        })

    crate_paths = [
        "backend/circuits/hashing/Nargo.toml",
        "backend/circuits/hashing/src/lib.nr",
        "backend/circuits/nargo_hashing/Nargo.toml",
        "backend/circuits/nargo_hashing/src/lib.nr",
        "backend/circuits/constants/Nargo.toml",
        "backend/circuits/constants/src/lib.nr",
    ]
    crates = [file_record(SOURCE / relative) for relative in crate_paths]
    root_package = json.loads((SOURCE / "package.json").read_text())
    backend_package = json.loads((SOURCE / "backend/package.json").read_text())
    artifact = json.loads(ARTIFACT.read_text())
    git_status = subprocess.run(
        ["git", "status", "--short"], cwd=SOURCE, text=True,
        capture_output=True, check=True,
    ).stdout.splitlines()
    payload = {
        "schema": "bindcheck.d1p12r.inventory/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "source": {
            "head": PIN,
            "origin": subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=SOURCE,
                text=True, capture_output=True, check=True,
            ).stdout.strip(),
            "status_before_d1p12r_generated_files": git_status,
            "d1p11_hashes": matched,
        },
        "host": {
            "platform": platform.platform(), "machine": platform.machine(),
            "python": sys.version.split()[0], "logical_cpus": os.cpu_count(),
            "free_disk_bytes": shutil.disk_usage(ROOT).free,
        },
        "manifests": [
            file_record(SOURCE / "package.json"),
            file_record(SOURCE / "backend/package.json"),
            file_record(SOURCE / "pnpm-lock.yaml"),
            file_record(SOURCE / "backend/hardhat.config.ts"),
            file_record(SOURCE / "backend/circuits/withdraw/Nargo.toml"),
            file_record(SOURCE / "backend/scripts/regenerateVerifier.ts"),
        ],
        "declared_toolchain": {
            "package_manager": root_package.get("packageManager"),
            "node_engine": root_package.get("engines", {}).get("node"),
            "noir_js": backend_package["dependencies"]["@noir-lang/noir_js"],
            "bb_js": backend_package["dependencies"]["@aztec/bb.js"],
            "hardhat_range": backend_package["devDependencies"]["hardhat"],
            "artifact_noir_version": artifact.get("noir_version"),
            "solidity": "0.8.29; optimizer enabled, runs 1; EVM Cancun",
            "proof_and_verifier_mode": "UltraHonk keccakZK:true",
        },
        "historical_artifacts": [file_record(ARTIFACT), file_record(VERIFIER)],
        "circuit_crates": crates,
        "hashing_name_resolution": {
            "withdraw_dependency": "hashing = { path = ../nargo_hashing }",
            "note": "The withdrawal package aliases nargo_hashing as hashing. The separate hashing package also exists; both are recorded and inspected.",
        },
        "field_modulus_decimal": str(FIELD_MODULUS),
    }
    write_json(RAW / "setup-inventory.json", payload)
    print(json.dumps({"inventory": str(RAW / "setup-inventory.json"), "d1p11_matches": sum(x["matches_d1p11"] for x in matched)}))
    return 0


def retrieve() -> int:
    """Fetch the exact authorized commit from the declared origin."""
    require_checkout()
    origin = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=SOURCE, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    record = run_recorded(
        "fetch-pinned-source",
        ["git", "fetch", "--depth=1", "origin", PIN], SOURCE, 600,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    fetch_head = (SOURCE / ".git/FETCH_HEAD").read_text().strip() if (SOURCE / ".git/FETCH_HEAD").exists() else None
    payload = {
        "schema": "bindcheck.d1p12r.retrieval/v1",
        "url": origin,
        "origin": "github.com",
        "requested_revision": PIN,
        "command": record,
        "head_after": head,
        "fetch_head": fetch_head,
        "revision_matches": head == PIN and bool(fetch_head and fetch_head.startswith(PIN)),
        "blocked_request": None if record["exit_code"] == 0 else {
            "url": origin, "origin": "github.com",
            "error_log": record["stderr"],
        },
    }
    write_json(RAW / "retrieval.json", payload)
    return record["exit_code"] or 0


def install() -> int:
    require_checkout()
    launcher = pnpm_argv()
    write_json(RAW / "package-manager-bootstrap.json", {
        "declared_package_manager": "pnpm@10.8.1",
        "corepack_path": shutil.which("corepack"),
        "npx_path": shutil.which("npx"),
        "selected_exact_launcher": launcher,
        "note": "The first wrapper invocation stopped before a subprocess because corepack was absent; no dependency install or network request occurred.",
    })
    version = run_recorded(
        "pinned-pnpm-version", pnpm_argv("--version"), SOURCE, 300,
    )
    if version["exit_code"] != 0:
        return version["exit_code"] or 1
    record = run_recorded(
        "pnpm-install-frozen", pnpm_argv("install", "--frozen-lockfile"),
        SOURCE, 1800,
    )
    return record["exit_code"] or 0


def prepare() -> int:
    require_checkout()
    if not (SOURCE / "node_modules").exists():
        raise SystemExit("dependencies absent; run --stage install first")
    (RAW / "artifacts/historical").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ARTIFACT, RAW / "artifacts/historical/withdraw.json")
    shutil.copy2(VERIFIER, RAW / "artifacts/historical/WithdrawVerifier.sol")
    TARGET_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ARTIFACT, TARGET_ARTIFACT)
    shutil.copy2(HARNESS_TEMPLATE, HARNESS)
    pre = {
        "historical_compiled_artifact": file_record(ARTIFACT),
        "target_artifact_exact_copy": file_record(TARGET_ARTIFACT),
        "historical_verifier": file_record(VERIFIER),
        "fixture_template": file_record(HARNESS_TEMPLATE, ROOT),
        "fixture_installed": file_record(HARNESS),
    }
    write_json(RAW / "artifact-chain-before-generation.json", pre)
    verifier = run_recorded(
        "generate-verifier",
        pnpm_argv("--filter", "@warp-toad/backend", "exec", "tsx", "scripts/regenerateVerifier.ts"),
        SOURCE, 1800,
    )
    if verifier["exit_code"] != 0:
        return verifier["exit_code"] or 1
    generated_dir = RAW / "artifacts/generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VERIFIER, generated_dir / "WithdrawVerifier.sol")
    after = {
        "input_artifact": file_record(TARGET_ARTIFACT),
        "newly_generated_verifier": file_record(VERIFIER),
        "saved_generated_verifier": file_record(generated_dir / "WithdrawVerifier.sol", RAW),
        "byte_identical_to_historical": sha256(VERIFIER) == sha256(RAW / "artifacts/historical/WithdrawVerifier.sol"),
        "generation_command": verifier,
    }
    write_json(RAW / "artifact-chain-after-generation.json", after)
    compile_record = run_recorded(
        "hardhat-compile",
        pnpm_argv("--filter", "@warp-toad/backend", "compile"),
        SOURCE, 1800,
    )
    return compile_record["exit_code"] or 0


def proof() -> int:
    require_checkout()
    attempts = load_json(ATTEMPT_LEDGER, {"schema": "bindcheck.d1p12r.proof-attempts/v1", "attempts": []})
    assert isinstance(attempts, dict)
    prior = attempts.get("attempts", [])
    if len(prior) >= 2:
        raise SystemExit("proof-attempt limit exhausted")
    if (RAW / "honest-proof.json").exists():
        raise SystemExit("honest-proof evidence already exists; refusing to regenerate")
    marker = RAW / "proof-attempt-marker.json"
    marker.unlink(missing_ok=True)
    result_path = RAW / "execution-result.json"
    env = {
        "D1P12R_RESULT": str(result_path),
        "D1P12R_PROOF": str(RAW / "honest-proof.json"),
        "D1P12R_RECEIPT": str(RAW / "mint-receipt.json"),
        "D1P12R_CANONICALITY": str(RAW / "canonicality.json"),
        "D1P12R_ATTEMPT_MARKER": str(marker),
    }
    label = f"proof-attempt-{len(prior) + 1}"
    record = run_recorded(
        label,
        pnpm_argv("--filter", "@warp-toad/backend", "exec", "hardhat", "test", "--network", "edr", "--no-compile", "test/d1p12r.fixture.ts"),
        SOURCE, 1800, env,
    )
    if marker.exists():
        marker_data = json.loads(marker.read_text())
        prior.append({"attempt": len(prior) + 1, "marker": marker_data, "command": record})
        attempts["attempts"] = prior
        write_json(ATTEMPT_LEDGER, attempts)
    else:
        write_json(RAW / f"{label}-not-consumed.json", {
            "reason": "fixture command ended before createProof marker",
            "command": record,
        })
    return record["exit_code"] or 0


def save_vk() -> int:
    """Save the deterministic VK and its directly derived verifier."""
    require_checkout()
    out = RAW / "artifacts/generated"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VK_TEMPLATE, VK_HELPER)
    vk = out / "withdraw-vk.bin"
    verifier = out / "WithdrawVerifier-from-saved-vk.sol"
    record = run_recorded(
        "save-verification-key",
        pnpm_argv("--filter", "@warp-toad/backend", "exec", "tsx", "scripts/d1p12rGenerateVk.ts"),
        SOURCE, 1800, {
            "D1P12R_CIRCUIT": str(TARGET_ARTIFACT),
            "D1P12R_VK": str(vk),
            "D1P12R_VK_VERIFIER": str(verifier),
        },
    )
    if record["exit_code"] == 0:
        write_json(RAW / "verification-key.json", {
            "schema": "bindcheck.d1p12r.verification-key/v1",
            "input_artifact": file_record(TARGET_ARTIFACT),
            "verification_key": file_record(vk, RAW),
            "verifier_from_saved_key": file_record(verifier, RAW),
            "matches_pinned_generator_output": sha256(verifier) == sha256(VERIFIER),
            "matches_historical_verifier": sha256(verifier) == sha256(RAW / "artifacts/historical/WithdrawVerifier.sol"),
            "settings": {"backend": "UltraHonkBackend", "keccakZK": True, "threads": os.cpu_count()},
            "command": record,
        })
    return record["exit_code"] or 0


def audit() -> int:
    """Record reader behavior, resolved identities, preservation, and controls."""
    require_checkout()
    sys.path.insert(0, str(ROOT / "src"))
    from bindcheck_d1.frontends.acir_binary_v1 import decode  # noqa: PLC0415
    from bindcheck_d1.model_v2 import Unsupported  # noqa: PLC0415

    reader: dict
    try:
        decoded = decode(ARTIFACT)
        reader = {"status": "SUPPORTED", "identity": decoded.get("identity")}
    except Unsupported as exc:
        reader = {
            "status": "INCOMPATIBLE",
            "reason": exc.reason,
            "detail": str(exc),
            "reader_expected": "1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051",
            "artifact_observed": json.loads(ARTIFACT.read_text()).get("noir_version"),
            "frontend_changed": False,
        }
    write_json(RAW / "acir-reader-compatibility.json", reader)

    versions = run_recorded(
        "resolved-package-versions",
        pnpm_argv("--filter", "@warp-toad/backend", "list", "--depth", "0", "--json"),
        SOURCE, 300,
    )
    pytest = shutil.which("pytest")
    if not pytest:
        raise SystemExit("pytest executable not available for repository controls")
    controls = run_recorded(
        "repository-reader-controls-with-pythonpath",
        [pytest, "-q", "tests/d1/test_v2_core.py", "tests/d1/test_typed_bindings.py"],
        ROOT, 600, {"PYTHONPATH": str(ROOT / "src")},
    )

    prior_expected = {
        "reports/D1P-12.md": "57a5f3c9560cb01b31f66fae8ddaca1d2d71a5b0eb00959fc8f71f086a215762",
        "scripts/d1p_12_warptoad_fixture.py": "20ee14663351b9ae283ecebc83657b46fafa08418bc9e31dec63609845b106f4",
        "protocols/d1/d1p-12-warptoad-fixture.json": "6bf31890ffd85eed1fa45f93bfe77f34dfdd9b362c2bb1ecdafff39eb4434657",
        "metadata/d1/d1p-12-artifact-manifest.json": "1464df6639da580bd5e1ac1649bf5ee90d2cf591818dcd65857cc4d59d0e8581",
        "results/raw/D1P-12/preflight.json": "e1392aaf4349603ea568aa3ed0e959013e58986ca34827bc00651b384c5c9eb5",
        "results/raw/D1P-12/commands.txt": "483a4238a94d7bc35676e47612f9d645dbcd99d32f6dbc1f06f5052ccee10a75",
    }
    preserved = []
    for relative, expected_hash in prior_expected.items():
        path = ROOT / relative
        actual = sha256(path)
        preserved.append({
            "path": relative, "expected_sha256": expected_hash,
            "actual_sha256": actual, "matches": actual == expected_hash,
        })

    artifact = json.loads(ARTIFACT.read_text())
    abi_parameters = artifact["abi"]["parameters"]
    post = {
        "schema": "bindcheck.d1p12r.audit/v1",
        "created_at_utc": utc_now(),
        "acir_reader": reader,
        "resolved_versions_command": versions,
        "repository_controls": controls,
        "d1p12_preservation": preserved,
        "proof_attempts": load_json(ATTEMPT_LEDGER, {"attempts": []}),
        "artifact_abi": {
            "parameter_count": len(abi_parameters),
            "public_parameters": [p for p in abi_parameters if p.get("visibility") == "public"],
            "private_parameters": [p for p in abi_parameters if p.get("visibility") == "private"],
            "return_type": artifact["abi"].get("return_type"),
        },
        "checkout_after": {
            "status_short": subprocess.run(
                ["git", "status", "--short"], cwd=SOURCE, text=True,
                capture_output=True, check=True,
            ).stdout.splitlines(),
            "tracked_diff_empty": subprocess.run(
                ["git", "diff", "--quiet"], cwd=SOURCE, check=False,
            ).returncode == 0,
        },
        "artifacts": {
            "historical_compiled": file_record(ARTIFACT),
            "target_exact_copy": file_record(TARGET_ARTIFACT),
            "historical_verifier_saved": file_record(RAW / "artifacts/historical/WithdrawVerifier.sol", RAW),
            "new_generated_verifier_saved": file_record(RAW / "artifacts/generated/WithdrawVerifier.sol", RAW),
            "verification_key": file_record(RAW / "artifacts/generated/withdraw-vk.bin", RAW),
            "verifier_from_saved_key": file_record(RAW / "artifacts/generated/WithdrawVerifier-from-saved-vk.sol", RAW),
            "compiled_honk_verifier_artifact": file_record(SOURCE / "backend/artifacts/contracts/verifier/WithdrawVerifier.sol/HonkVerifier.json"),
            "honest_proof": file_record(RAW / "honest-proof.json", RAW),
            "execution": file_record(RAW / "execution-result.json", RAW),
            "receipt": file_record(RAW / "mint-receipt.json", RAW),
            "canonicality": file_record(RAW / "canonicality.json", RAW),
        },
        "resource_boundary": "Observed usage only; not a performance result.",
    }
    write_json(RAW / "post-run-audit.json", post)
    print(json.dumps({
        "reader": reader["status"],
        "controls_exit": controls["exit_code"],
        "d1p12_preserved": all(x["matches"] for x in preserved),
    }))
    return controls["exit_code"] or 0


def finalize() -> int:
    """Create compact summaries and a curated raw-evidence checksum manifest."""
    require_checkout()
    canonicality = json.loads((RAW / "canonicality.json").read_text())

    def deepest_data(error: object) -> object:
        current = error
        result = None
        while isinstance(current, dict):
            if current.get("data") is not None:
                result = current["data"]
            current = current.get("cause")
        return result

    compact_cases = []
    for case in canonicality["cases"]:
        error = case.get("error")
        compact_cases.append({
            "index": case["index"], "boundary": case["boundary"],
            "word": case["word"], "behavior": case["behavior"],
            "returned": case.get("returned"),
            "revert_detail": error.get("details") if isinstance(error, dict) else None,
            "revert_data": deepest_data(error),
        })
    compact = {
        "schema": "bindcheck.d1p12r.canonicality-summary/v1",
        "field_modulus": canonicality["fieldModulus"],
        "honest_proof_accepted": canonicality["honestProofAccepted"],
        "cases": compact_cases,
        "all_rejected_by_revert": all(x["behavior"] == "reverted" for x in compact_cases),
        "unique_revert_details": sorted({x["revert_detail"] for x in compact_cases}),
        "unique_revert_data": sorted({x["revert_data"] for x in compact_cases}),
        "interpretation": "Observed strict field-boundary rejection, not a vulnerability verdict.",
    }
    write_json(RAW / "canonicality-summary.json", compact)

    hardhat = json.loads((SOURCE / "backend/artifacts/contracts/verifier/WithdrawVerifier.sol/HonkVerifier.json").read_text())
    bytecode = hardhat["bytecode"]
    deployed = hardhat["deployedBytecode"]
    write_json(RAW / "compiled-verifier-identity.json", {
        "artifact": file_record(SOURCE / "backend/artifacts/contracts/verifier/WithdrawVerifier.sol/HonkVerifier.json"),
        "contract_name": hardhat["contractName"],
        "source_name": hardhat["sourceName"],
        "creation_bytecode_template_hex_chars": len(bytecode.removeprefix("0x")),
        "creation_bytecode_template_sha256": hashlib.sha256(bytecode.encode()).hexdigest(),
        "deployed_bytecode_template_hex_chars": len(deployed.removeprefix("0x")),
        "deployed_bytecode_template_sha256": hashlib.sha256(deployed.encode()).hexdigest(),
        "link_references": hardhat["linkReferences"],
        "deployed_link_references": hardhat["deployedLinkReferences"],
        "note": "Hashes cover Hardhat bytecode template strings; library placeholders are linked by the pinned deployment helper.",
    })

    curated = [
        "setup-inventory.json", "retrieval.json", "package-manager-bootstrap.json",
        "artifact-chain-before-generation.json", "artifact-chain-after-generation.json",
        "verification-key.json", "acir-reader-compatibility.json",
        "proof-attempts.json", "honest-proof.json", "execution-result.json",
        "mint-receipt.json", "canonicality.json", "canonicality-summary.json",
        "compiled-verifier-identity.json", "post-run-audit.json",
        "artifacts/historical/withdraw.json",
        "artifacts/historical/WithdrawVerifier.sol",
        "artifacts/generated/withdraw-vk.bin",
        "artifacts/generated/WithdrawVerifier.sol",
        "artifacts/generated/WithdrawVerifier-from-saved-vk.sol",
    ]
    curated.extend(str(path.relative_to(RAW)) for path in sorted(RECORDS.glob("*.json")))
    curated.extend(str(path.relative_to(RAW)) for path in sorted(LOGS.glob("*.txt")))
    records = [file_record(RAW / relative, RAW) for relative in sorted(set(curated))]
    write_json(RAW / "evidence-manifest.json", {
        "schema": "bindcheck.d1p12r.raw-evidence-manifest/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "records": records,
        "record_count": len(records),
        "regular_file_bytes": sum(item["bytes"] for item in records),
        "workspace_exclusion": "The ignored source checkout, node_modules, Hardhat cache and bulk artifacts are reproducible workspace state and are not recursively included.",
    })
    print(json.dumps({"records": len(records), "canonicality_cases": len(compact_cases)}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("inventory", "retrieve", "install", "prepare", "proof", "vk", "audit", "finalize"))
    args = parser.parse_args()
    return {"inventory": inventory, "retrieve": retrieve, "install": install, "prepare": prepare, "proof": proof, "vk": save_vk, "audit": audit, "finalize": finalize}[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
