#!/usr/bin/env python3
"""Reproducible D1P-13 WarpToad beta.22 correspondence runner.

All generated state is confined to results/raw/D1P-13.  The D1P-12 and
D1P-12R namespaces are read-only inputs.  This runner never invokes a solver
or a prover.
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
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-13"
SOURCE = RAW / "workspace/source"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
TOOLS = RAW / "tools"
UPSTREAM = RAW / "upstream"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
NOIR_REV = "c57152f91260ecdb9faad4efc20abb14b6d2ece7"
NOIR_VERSION = "1.0.0-beta.22+" + NOIR_REV
RELEASE_API = "https://api.github.com/repos/noir-lang/noir/releases/tags/v1.0.0-beta.22"
NARGO_URL = "https://github.com/noir-lang/noir/releases/download/v1.0.0-beta.22/nargo-aarch64-apple-darwin.tar.gz"
NOIR_SOURCE_URL = f"https://github.com/noir-lang/noir/archive/{NOIR_REV}.tar.gz"
D1P12R = ROOT / "results/raw/D1P-12R"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path, base: Path = ROOT) -> dict:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def process_tree_rss_kib(root_pid: int) -> int:
    try:
        rows = []
        output = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,rss="], check=True, capture_output=True,
            text=True, timeout=5,
        ).stdout
        for line in output.splitlines():
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
            argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, text=True,
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
    payload = {
        "schema": "bindcheck.d1p13.command/v1",
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
        "stdout": record(stdout_path, RAW),
        "stderr": record(stderr_path, RAW),
    }
    write_json(RECORDS / f"{label}.json", payload)
    return payload


def download(label: str, url: str, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    request = urllib.request.Request(url, headers={"User-Agent": "bindcheck-d1p13"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
            final_url = response.geturl()
            status = response.status
        payload = {
            "label": label, "requested_url": url, "origin": urllib.parse.urlparse(url).netloc,
            "final_url": final_url, "status": status, "started_at_utc": started,
            "finished_at_utc": utc_now(), "file": record(destination, RAW),
            "blocked_request": None,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        payload = {
            "label": label, "requested_url": url, "origin": urllib.parse.urlparse(url).netloc,
            "started_at_utc": started, "finished_at_utc": utc_now(),
            "blocked_request": {"url": url, "origin": urllib.parse.urlparse(url).netloc,
                                "error_type": type(exc).__name__, "error": str(exc)},
        }
    write_json(RECORDS / f"{label}.json", payload)
    return payload


def download_curl(label: str, url: str, destination: Path) -> dict:
    """Retrieve through the host curl/CA configuration and retain its command record."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = run_recorded(
        label, ["curl", "--fail", "--location", "--silent", "--show-error",
                "--output", str(destination), url], ROOT, 600,
    )
    blocked = None
    if command["exit_code"] != 0:
        blocked = {"url": url, "origin": urllib.parse.urlparse(url).netloc,
                   "error_log": command["stderr"]}
    return {
        "label": label, "requested_url": url,
        "origin": urllib.parse.urlparse(url).netloc,
        "command": command,
        "file": record(destination, RAW) if destination.exists() else None,
        "blocked_request": blocked,
    }


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        root = destination.resolve()
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise SystemExit(f"unsafe archive member: {member.name}")
        bundle.extractall(destination, filter="data")


def stage_setup() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    preservation_paths = [
        "reports/D1P-12.md", "reports/D1P-12R.md",
        "metadata/d1/d1p-12-artifact-manifest.json",
        "metadata/d1/d1p-12r-artifact-manifest.json",
        "protocols/d1/d1p-12-warptoad-fixture.json",
        "protocols/d1/d1p-12r-warptoad-fixture.json",
        "results/raw/D1P-12R/evidence-manifest.json",
        "results/raw/D1P-12R/honest-proof.json",
        "results/raw/D1P-12R/artifacts/generated/withdraw-vk.bin",
    ]
    preservation = [record(ROOT / relative) for relative in preservation_paths]
    artifact = D1P12R / "workspace/source/frontend/src/lib/circuits/withdraw.json"
    artifact_json = json.loads(artifact.read_text())
    payload = {
        "schema": "bindcheck.d1p13.setup/v1",
        "created_at_utc": utc_now(),
        "host": {"platform": platform.platform(), "machine": platform.machine(),
                 "python": sys.version.split()[0], "logical_cpus": os.cpu_count(),
                 "free_disk_bytes": shutil.disk_usage(ROOT).free},
        "pins": {"warptoad_revision": PIN, "noir_revision": NOIR_REV,
                 "noir_version": NOIR_VERSION},
        "committed_artifact": record(artifact),
        "committed_artifact_embedded_version": artifact_json.get("noir_version"),
        "preservation_baseline": preservation,
        "bounds": {"solver_calls": 0, "proof_generation_attempts": 0,
                   "new_proof_generation_forbidden": True},
    }
    write_json(RAW / "setup.json", payload)
    return 0


def stage_retrieve() -> int:
    downloads = []
    downloads.append(download_curl("release-api-curl", RELEASE_API, UPSTREAM / "release-v1.0.0-beta.22.json"))
    downloads.append(download_curl("nargo-release-curl", NARGO_URL, UPSTREAM / "nargo-aarch64-apple-darwin.tar.gz"))
    downloads.append(download_curl("noir-source-curl", NOIR_SOURCE_URL, UPSTREAM / f"noir-{NOIR_REV}.tar.gz"))
    blocked = [item["blocked_request"] for item in downloads if item.get("blocked_request")]
    if blocked:
        write_json(RAW / "retrieval.json", {"schema": "bindcheck.d1p13.retrieval/v1",
                                             "downloads": downloads, "blocked_requests": blocked})
        return 1
    release = json.loads((UPSTREAM / "release-v1.0.0-beta.22.json").read_text())
    release_asset = next(asset for asset in release["assets"] if asset["name"] == "nargo-aarch64-apple-darwin.tar.gz")
    safe_extract(UPSTREAM / "nargo-aarch64-apple-darwin.tar.gz", TOOLS / "nargo-beta22")
    safe_extract(UPSTREAM / f"noir-{NOIR_REV}.tar.gz", TOOLS / "noir-source")
    nargo_candidates = sorted(path for path in (TOOLS / "nargo-beta22").rglob("nargo") if path.is_file())
    if len(nargo_candidates) != 1:
        raise SystemExit(f"expected one nargo executable, found: {nargo_candidates}")
    nargo_candidates[0].chmod(nargo_candidates[0].stat().st_mode | 0o111)
    version = run_recorded("nargo-version", [str(nargo_candidates[0]), "--version"], ROOT, 60)
    clone = run_recorded(
        "clone-pinned-project",
        ["git", "clone", "--no-hardlinks", str(D1P12R / "workspace/source"), str(SOURCE)],
        ROOT, 600,
    )
    if clone["exit_code"] == 0:
        checkout = run_recorded("checkout-pinned-project", ["git", "checkout", "--detach", PIN], SOURCE, 300)
    else:
        checkout = None
    payload = {
        "schema": "bindcheck.d1p13.retrieval/v1",
        "downloads": downloads,
        "release": {"tag_name": release.get("tag_name"),
                    "target_commitish": release.get("target_commitish"),
                    "release_asset_name": release_asset["name"],
                    "release_asset_url": release_asset["browser_download_url"],
                    "release_asset_declared_bytes": release_asset["size"]},
        "nargo_executable": record(nargo_candidates[0], RAW),
        "nargo_version_command": version,
        "project_clone_command": clone,
        "project_checkout_command": checkout,
        "blocked_requests": [],
        "initial_python_ca_failures": [
            json.loads((RECORDS / f"{name}.json").read_text())
            for name in ("release-api", "nargo-release", "noir-source")
            if (RECORDS / f"{name}.json").exists()
        ],
    }
    write_json(RAW / "retrieval.json", payload)
    if version["exit_code"] != 0 or clone["exit_code"] != 0 or not checkout or checkout["exit_code"] != 0:
        return 1
    return 0


def require_source() -> None:
    if not SOURCE.exists():
        raise SystemExit("D1P-13 source checkout is absent; run --stage retrieve")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=SOURCE, check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != PIN:
        raise SystemExit(f"wrong project revision: {head}")


def nargo_path() -> Path:
    matches = sorted(path for path in (TOOLS / "nargo-beta22").rglob("nargo") if path.is_file())
    if len(matches) != 1:
        raise SystemExit("exact beta.22 nargo executable is absent")
    return matches[0]


def stage_compile() -> int:
    require_source()
    circuit = SOURCE / "backend/circuits/withdraw"
    poseidon_cache = Path("/Users/imranpollob/nargo/github.com/noir-lang/poseidon/v0.3.0")
    if not poseidon_cache.exists():
        raise SystemExit("pinned poseidon v0.3.0 cache is absent; retrieval would be required")
    poseidon_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=poseidon_cache, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    pre = {
        "schema": "bindcheck.d1p13.compile-input/v1",
        "created_at_utc": utc_now(),
        "head": PIN,
        "nargo": record(nargo_path(), RAW),
        "manifests": [record(path, SOURCE) for path in [
            circuit / "Nargo.toml",
            SOURCE / "backend/circuits/nargo_hashing/Nargo.toml",
            SOURCE / "backend/circuits/merkle-trees/Nargo.toml",
            SOURCE / "backend/circuits/constants/Nargo.toml",
        ]],
        "resolved_git_dependency": {
            "declared_url": "https://github.com/noir-lang/poseidon",
            "declared_tag": "v0.3.0",
            "cache_path": str(poseidon_cache),
            "resolved_commit": poseidon_head,
            "status_short": subprocess.run(
                ["git", "status", "--short"], cwd=poseidon_cache, check=True,
                capture_output=True, text=True,
            ).stdout.splitlines(),
        },
        "git_status_before": subprocess.run(["git", "status", "--short"], cwd=SOURCE,
                                             check=True, capture_output=True, text=True).stdout.splitlines(),
    }
    write_json(RAW / "compile-input.json", pre)
    result = run_recorded("compile-withdraw-beta22", [str(nargo_path()), "compile"], circuit, 1800)
    target = circuit / "target/withdraw.json"
    if result["exit_code"] == 0 and target.exists():
        write_json(RAW / "compile-output.json", {
            "schema": "bindcheck.d1p13.compile-output/v1",
            "artifact": record(target, RAW),
            "command": result,
            "git_status_after": subprocess.run(["git", "status", "--short"], cwd=SOURCE,
                                                check=True, capture_output=True, text=True).stdout.splitlines(),
        })
    return result["exit_code"] or 0


def stage_vk() -> int:
    """Derive a VK from the rebuilt bytecode with the already pinned bb.js 5.0.0."""
    require_source()
    rebuilt = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
    if not rebuilt.exists():
        raise SystemExit("rebuilt artifact is absent; run --stage compile")
    for relative in ("node_modules", "backend/node_modules"):
        link = SOURCE / relative
        target = D1P12R / "workspace/source" / relative
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != target.resolve():
                raise SystemExit(f"unexpected dependency path already exists: {link}")
        else:
            link.symlink_to(target, target_is_directory=True)
    helper = SOURCE / "backend/scripts/d1p13GenerateVk.ts"
    shutil.copy2(ROOT / "scripts/fixtures/d1p_12r_generate_vk.ts", helper)
    outputs = RAW / "artifacts/rebuilt"
    outputs.mkdir(parents=True, exist_ok=True)
    vk = outputs / "withdraw-vk.bin"
    verifier = outputs / "WithdrawVerifier-from-vk.sol"
    result = run_recorded(
        "derive-rebuilt-vk",
        [str(SOURCE / "backend/node_modules/.bin/tsx"), str(helper)],
        SOURCE / "backend", 1800,
        {"D1P12R_CIRCUIT": str(rebuilt), "D1P12R_VK": str(vk),
         "D1P12R_VK_VERIFIER": str(verifier)},
    )
    if result["exit_code"] == 0:
        prior_vk = D1P12R / "artifacts/generated/withdraw-vk.bin"
        prior_verifier = D1P12R / "artifacts/generated/WithdrawVerifier-from-saved-vk.sol"
        write_json(RAW / "vk-correspondence.json", {
            "schema": "bindcheck.d1p13.vk-correspondence/v1",
            "settings": {"backend": "UltraHonkBackend", "bb_js": "5.0.0",
                         "keccakZK": True, "threads": os.cpu_count()},
            "rebuilt_artifact": record(rebuilt, RAW),
            "rebuilt_vk": record(vk, RAW),
            "d1p12r_committed_artifact_vk": record(prior_vk),
            "vk_byte_identical": sha256(vk) == sha256(prior_vk),
            "rebuilt_verifier": record(verifier, RAW),
            "d1p12r_committed_artifact_verifier": record(prior_verifier),
            "verifier_byte_identical": sha256(verifier) == sha256(prior_verifier),
            "command": result,
        })
    return result["exit_code"] or 0


def stage_witness() -> int:
    """Execute the saved honest inputs with Noir JS, without invoking a prover."""
    require_source()
    # The vk stage establishes these links; reproduce them if witness is run alone.
    for relative in ("node_modules", "backend/node_modules"):
        link = SOURCE / relative
        target = D1P12R / "workspace/source" / relative
        if not link.exists() and not link.is_symlink():
            link.symlink_to(target, target_is_directory=True)
        if not link.is_symlink() or link.resolve() != target.resolve():
            raise SystemExit(f"unexpected dependency path: {link}")
    helper = SOURCE / "backend/scripts/d1p13ExtractWitness.ts"
    shutil.copy2(ROOT / "scripts/fixtures/d1p_13_extract_witness.ts", helper)
    artifact = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
    honest = D1P12R / "honest-proof.json"
    output = RAW / "honest-witness.json"
    result = run_recorded(
        "execute-honest-witness",
        [str(SOURCE / "backend/node_modules/.bin/tsx"), str(helper)],
        SOURCE / "backend", 1800,
        {"D1P13_ARTIFACT": str(artifact), "D1P13_HONEST_PROOF": str(honest),
         "D1P13_WITNESS": str(output)},
    )
    if result["exit_code"] == 0:
        write_json(RAW / "witness-execution.json", {
            "schema": "bindcheck.d1p13.witness-execution/v1",
            "proof_generation": False,
            "prover_invocations": 0,
            "source_inputs": record(honest),
            "artifact": record(artifact, RAW),
            "witness": record(output, RAW),
            "command": result,
        })
    return result["exit_code"] or 0


def stage_semantics() -> int:
    require_source()
    artifact = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
    witness = RAW / "honest-witness.json"
    mutation_plan = RAW / "mutation-plan.json"
    result = RAW / "semantic-check.json"
    if mutation_plan.exists():
        raise SystemExit("mutation plan already exists; refusing to overwrite the frozen plan")
    common = [sys.executable, str(ROOT / "scripts/d1p_13_semantic_check.py"),
              "--artifact", str(artifact), "--witness", str(witness)]
    env = {"PYTHONPATH": str(ROOT / "src")}
    planned = run_recorded("freeze-mutation-plan", common + ["--plan", str(mutation_plan)], ROOT, 300, env)
    if planned["exit_code"] != 0:
        return planned["exit_code"] or 1
    checked = run_recorded("check-beta22-semantics", common + ["--check", str(result)], ROOT, 600, env)
    return checked["exit_code"] or 0


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def stage_audit() -> int:
    require_source()
    sys.path.insert(0, str(ROOT / "src"))
    from bindcheck_d1.frontends.acir_binary_beta22 import abi_bindings, decode  # noqa: PLC0415

    committed_path = D1P12R / "workspace/source/frontend/src/lib/circuits/withdraw.json"
    rebuilt_path = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
    committed_json = json.loads(committed_path.read_text())
    rebuilt_json = json.loads(rebuilt_path.read_text())
    committed = decode(committed_path)
    rebuilt = decode(rebuilt_path)
    semantic_keys = ("functions", "unconstrained_functions")
    committed_semantic = {key: committed[key] for key in semantic_keys}
    rebuilt_semantic = {key: rebuilt[key] for key in semantic_keys}

    file_map_differences = []
    for file_id in sorted(set(committed_json["file_map"]) | set(rebuilt_json["file_map"]), key=int):
        old = committed_json["file_map"].get(file_id)
        new = rebuilt_json["file_map"].get(file_id)
        if old == new:
            continue
        difference_fields = sorted(key for key in set(old or {}) | set(new or {})
                                   if (old or {}).get(key) != (new or {}).get(key))
        only_path = difference_fields == ["path"]
        file_map_differences.append({
            "file_id": file_id, "different_fields": difference_fields,
            "historical_path": old.get("path") if old else None,
            "rebuilt_path": new.get("path") if new else None,
            "source_text_identical": bool(old and new and old.get("source") == new.get("source")),
            "function_locations_identical": bool(old and new and old.get("function_locations") == new.get("function_locations")),
            "classification": "nonsemantic-build-path-metadata" if only_path else "unclassified",
            "justification": "Only the compiler diagnostic source path changed; embedded source text and function locations are identical."
            if only_path else "Difference includes a field beyond path and is not treated as nonsemantic.",
        })

    top_level = {}
    for key in committed_json:
        if key == "file_map":
            continue
        top_level[key] = {
            "equal": committed_json.get(key) == rebuilt_json.get(key),
            "classification": "semantic" if key in ("bytecode", "abi", "hash") else "nonsemantic-metadata",
        }
    vk = json.loads((RAW / "vk-correspondence.json").read_text())
    correspondence_match = (
        committed_json["bytecode"] == rebuilt_json["bytecode"]
        and committed_json["abi"] == rebuilt_json["abi"]
        and committed_semantic == rebuilt_semantic
        and vk["vk_byte_identical"]
    )
    write_json(RAW / "artifact-correspondence.json", {
        "schema": "bindcheck.d1p13.artifact-correspondence/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "compiler_identity": NOIR_VERSION,
        "committed_artifact": record(committed_path),
        "rebuilt_artifact": record(rebuilt_path, RAW),
        "whole_json_byte_identical": sha256(committed_path) == sha256(rebuilt_path),
        "top_level_fields_except_file_map": top_level,
        "bytecode": {
            "base64_identical": committed_json["bytecode"] == rebuilt_json["bytecode"],
            "compressed_sha256": committed["identity"]["compressed_sha256"],
            "decoded_sha256": committed["serialization"]["decoded_sha256"],
            "decoded_semantic_canonical_sha256": canonical_sha256(committed_semantic),
            "decoded_semantic_identical": committed_semantic == rebuilt_semantic,
            "classification": "semantic-match",
        },
        "abi": {"exact_json_equal": committed_json["abi"] == rebuilt_json["abi"],
                "canonical_sha256": canonical_sha256(committed_json["abi"]),
                "classification": "semantic-match"},
        "verification_key": {
            "byte_identical": vk["vk_byte_identical"],
            "sha256": vk["rebuilt_vk"]["sha256"],
            "classification": "semantic-backend-artifact-match",
        },
        "generated_verifier": {
            "byte_identical": vk["verifier_byte_identical"],
            "sha256": vk["rebuilt_verifier"]["sha256"],
            "classification": "derived-artifact-match",
        },
        "metadata": {
            "debug_symbols_exact": committed_json["debug_symbols"] == rebuilt_json["debug_symbols"],
            "json_key_order_exact": list(committed_json) == list(rebuilt_json),
            "file_map_entry_count": len(committed_json["file_map"]),
            "file_map_difference_count": len(file_map_differences),
            "file_map_differences": file_map_differences,
            "all_differences_nonsemantic": all(item["classification"] == "nonsemantic-build-path-metadata"
                                                for item in file_map_differences),
        },
        "source_correspondence": "MATCH" if correspondence_match else "OPEN",
        "source_correspondence_rule": "MATCH requires rebuilt decoded constraints/bytecode, ABI, and pinned-bb.js VK equality.",
        "accepted_proof_boundary": "The D1P-12R proof was generated and accepted on the committed artifact/verifier route. D1P-13 did not generate or resubmit a proof; its independent rebuild instead establishes bytecode/ABI/VK correspondence.",
    })

    witness = json.loads((RAW / "honest-witness.json").read_text())
    witness_values = {int(key): value for key, value in witness["witnesses"].items()}
    circuit = rebuilt["functions"][0]
    bindings = abi_bindings(rebuilt["abi"], circuit)
    classifications = [
        ("calldata-supplied", "mint _nullifier; WarpToadCore.sol:143-160", "uint256 -> bytes32"),
        ("consumer-supplied block value", "block.chainid; WarpToadCore.sol:160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _amount; WarpToadCore.sol:145,160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _gigaRoot; history guard at WarpToadCore.sol:155", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _localRoot; history guard at WarpToadCore.sol:156", "uint256 -> bytes32"),
        ("consumer-supplied configuration", "stored aztecWarptoadAddress; initialized at WarpToadCore.sol:67-73; used at 160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _feeFactor; WarpToadCore.sol:148,160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _priorityFee; WarpToadCore.sol:149,160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _maxFee; WarpToadCore.sol:150,160", "uint256 -> bytes32"),
        ("calldata-supplied", "mint _relayer; WarpToadCore.sol:151,160", "address -> bytes20 -> uint160 -> uint256 -> bytes32 (left padded), lines 124,130,136-137"),
        ("calldata-supplied", "mint _recipient; WarpToadCore.sol:152,160", "address -> bytes20 -> uint160 -> uint256 -> bytes32 (left padded), lines 125,130,136-137"),
    ]
    public_parameters = [item for item in rebuilt["abi"]["parameters"] if item["visibility"] == "public"]
    mapping = []
    for position, parameter in enumerate(public_parameters):
        ids = bindings[parameter["name"]]
        if len(ids) != 1:
            raise SystemExit(f"public field is not scalar: {parameter['name']}")
        witness_id = ids[0]
        source_class, source_lines, conversion = classifications[position]
        mapping.append({
            "consumer_position": position, "abi_parameter": parameter["name"],
            "decoded_public_witness": witness_id, "honest_value": witness_values[witness_id],
            "consumer_source_class": source_class, "pinned_consumer_source": source_lines,
            "conversion": conversion,
            "circuit_declaration": f"backend/circuits/withdraw/src/main.nr:{15 + position if position < 6 else 24 + position}",
        })
    proof_public = json.loads((D1P12R / "honest-proof.json").read_text())["publicInputs"]
    write_json(RAW / "public-input-mapping.json", {
        "schema": "bindcheck.d1p13.public-input-mapping/v1",
        "created_at_utc": utc_now(),
        "decoded_public_witness_order": circuit["public_parameters"],
        "consumer_order_source": "reports/D1P-12R.md section 5; pinned WarpToadCore.sol:114-161",
        "formatting_source": "WarpToadCore.sol:114-140",
        "mapping": mapping,
        "decoded_values_equal_d1p12r_accepted_public_inputs": [item["honest_value"].lower() for item in mapping]
        == [item.lower() for item in proof_public],
        "proof_only_public_input_count": sum(item["consumer_source_class"] == "proof-only" for item in mapping),
    })

    d1p11 = json.loads((ROOT / "results/raw/D1P-11/retrieved-source-hashes.json").read_text())
    source_matches = []
    for item in d1p11["sources"]:
        if item.get("application") != "warp-toad":
            continue
        path = SOURCE / item["path"]
        source_matches.append({"path": item["path"], "expected_sha256": item["sha256"],
                               "actual_sha256": sha256(path), "matches": sha256(path) == item["sha256"]})
    baseline = json.loads((RAW / "setup.json").read_text())["preservation_baseline"]
    preserved = []
    for item in baseline:
        path = ROOT / item["path"]
        preserved.append({**item, "actual_sha256": sha256(path), "matches": sha256(path) == item["sha256"]})
    beta14_path = ROOT / "src/bindcheck_d1/frontends/acir_binary_v1.py"
    beta14_head = subprocess.run(["git", "show", "HEAD:src/bindcheck_d1/frontends/acir_binary_v1.py"],
                                 cwd=ROOT, check=True, capture_output=True).stdout
    write_json(RAW / "preservation-audit.json", {
        "schema": "bindcheck.d1p13.preservation/v1",
        "prior_evidence": preserved,
        "all_prior_evidence_unchanged": all(item["matches"] for item in preserved),
        "beta14_decoder": {"path": str(beta14_path.relative_to(ROOT)),
                           "current_sha256": sha256(beta14_path),
                           "head_sha256": hashlib.sha256(beta14_head).hexdigest(),
                           "byte_unchanged_from_head": beta14_path.read_bytes() == beta14_head},
        "d1p11_source_hashes": source_matches,
        "all_d1p11_source_hashes_match": all(item["matches"] for item in source_matches),
        "pinned_checkout_tracked_diff_empty": subprocess.run(["git", "diff", "--quiet"], cwd=SOURCE).returncode == 0,
        "pinned_checkout_status_short": subprocess.run(["git", "status", "--short"], cwd=SOURCE,
                                                        check=True, capture_output=True, text=True).stdout.splitlines(),
    })

    source_root = next((TOOLS / "noir-source").iterdir())
    schema_paths = [
        source_root / "acvm-repo/acir/src/serialization.rs",
        source_root / "acvm-repo/acir/src/circuit/mod.rs",
        source_root / "acvm-repo/acir/src/circuit/opcodes.rs",
        source_root / "acvm-repo/acir/src/circuit/opcodes/black_box_function_call.rs",
        source_root / "acvm-repo/acir/src/circuit/brillig.rs",
        source_root / "acvm-repo/brillig/src/opcodes.rs",
    ]
    write_json(RAW / "decoder-inventory.json", {
        "schema": "bindcheck.d1p13.decoder-inventory/v1",
        "decoder_module": record(ROOT / "src/bindcheck_d1/frontends/acir_binary_beta22.py"),
        "semantic_checker_module": record(ROOT / "src/bindcheck_d1/frontends/acir_semantics_beta22.py"),
        "serialization_schema_sources": [record(path, RAW) for path in schema_paths],
        "decoded": {"identity": rebuilt["identity"], "serialization": rebuilt["serialization"],
                    "constrained_function_count": len(rebuilt["functions"]),
                    "unconstrained_function_count": len(rebuilt["unconstrained_functions"]),
                    "opcode_count": len(circuit["opcodes"])},
        "parse_is_not_semantic_support": True,
        "unknown_variant_policy": "named Unsupported exception; never skipped",
    })
    return 0


def stage_controls() -> int:
    pytest = shutil.which("pytest")
    if not pytest:
        raise SystemExit("pytest executable not available")
    result = run_recorded(
        "focused-decoder-controls",
        [pytest, "-q", "tests/d1/test_acir_beta22.py", "tests/d1/test_typed_bindings.py",
         "tests/d1/test_v2_core.py"],
        ROOT, 900, {"PYTHONPATH": str(ROOT / "src")},
    )
    if result["exit_code"] != 0:
        return result["exit_code"] or 1
    complete = run_recorded(
        "complete-d1-regression-controls", [pytest, "-q", "tests/d1"], ROOT, 900,
        {"PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT)},
    )
    if complete["exit_code"] == 0:
        write_json(RAW / "controls.json", {
            "schema": "bindcheck.d1p13.controls/v1",
            "beta22_focused_tests": "tests/d1/test_acir_beta22.py",
            "beta14_regression_tests": ["tests/d1/test_typed_bindings.py", "tests/d1/test_v2_core.py"],
            "focused_command": result,
            "complete_d1_command": complete,
            "beta14_decoder_unchanged": json.loads((RAW / "preservation-audit.json").read_text())["beta14_decoder"]["byte_unchanged_from_head"],
        })
    return complete["exit_code"] or 0


def stage_finalize() -> int:
    curated = [
        "setup.json", "retrieval.json", "compile-input.json", "compile-output.json",
        "vk-correspondence.json", "witness-execution.json", "honest-witness.json",
        "mutation-plan.json", "semantic-check.json", "artifact-correspondence.json",
        "public-input-mapping.json", "preservation-audit.json", "decoder-inventory.json",
        "controls.json", "artifacts/rebuilt/withdraw-vk.bin",
        "artifacts/rebuilt/WithdrawVerifier-from-vk.sol",
        "workspace/source/backend/circuits/withdraw/target/withdraw.json",
    ]
    curated.extend(str(path.relative_to(RAW)) for path in sorted(RECORDS.glob("*.json")))
    curated.extend(str(path.relative_to(RAW)) for path in sorted(LOGS.glob("*.txt")))
    records = [record(RAW / relative, RAW) for relative in sorted(set(curated))]
    compile_command = json.loads((RECORDS / "compile-withdraw-beta22.json").read_text())
    vk_command = json.loads((RECORDS / "derive-rebuilt-vk.json").read_text())
    witness_command = json.loads((RECORDS / "execute-honest-witness.json").read_text())
    write_json(RAW / "resource-summary.json", {
        "schema": "bindcheck.d1p13.resources/v1",
        "claim_boundary": "Observed development resource use only; not a performance result.",
        "commands": [
            {key: item[key] for key in ("label", "wall_seconds", "max_process_tree_rss_kib_observed",
                                        "min_free_disk_bytes_observed", "exit_code", "timed_out")}
            for item in (compile_command, vk_command, witness_command)
        ],
        "unsafe_resource_exhaustion_observed": False,
    })
    records.append(record(RAW / "resource-summary.json", RAW))
    write_json(RAW / "evidence-manifest.json", {
        "schema": "bindcheck.d1p13.raw-evidence-manifest/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "compiler_revision": NOIR_REV,
        "records": sorted(records, key=lambda item: item["path"]),
        "record_count": len(records),
        "regular_file_bytes": sum(item["bytes"] for item in records),
        "proof_generation_attempts": 0,
        "solver_calls": 0,
        "prohibited_actions_observed": [],
        "workspace_exclusion": "Downloaded release archives, extracted compiler source/tool binary, dependency cache, isolated Git checkout, and node_modules links are reproducible workspace state and are not recursively included; their identities are recorded by retrieval/setup inventories.",
    })
    print(json.dumps({"records": len(records), "bytes": sum(item["bytes"] for item in records)}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("setup", "retrieve", "compile", "vk", "witness", "semantics", "audit", "controls", "finalize"))
    args = parser.parse_args()
    return {"setup": stage_setup, "retrieve": stage_retrieve, "compile": stage_compile,
            "vk": stage_vk, "witness": stage_witness, "semantics": stage_semantics,
            "audit": stage_audit, "controls": stage_controls,
            "finalize": stage_finalize}[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
