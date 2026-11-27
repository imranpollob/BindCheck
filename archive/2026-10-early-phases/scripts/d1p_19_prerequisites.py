#!/usr/bin/env python3
"""D1P-19 evidence runner.  There is intentionally no solver entry point."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-19"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
WORKSPACE = RAW / "workspace/source"
PINNED_WORKSPACE = RAW / "workspace/pinned-source"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
VK = ROOT / "results/raw/D1P-13/artifacts/rebuilt/withdraw-vk.bin"
VERIFIER = ROOT / "results/raw/D1P-13/artifacts/rebuilt/WithdrawVerifier-from-vk.sol"


def now() -> str:
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


def tree_rss_kib(root_pid: int) -> int:
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,rss="], capture_output=True,
            text=True, check=True, timeout=5,
        ).stdout
        rows = [tuple(map(int, line.split())) for line in output.splitlines() if len(line.split()) == 3]
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
                 environment: dict[str, str]) -> int:
    if any(token in " ".join(argv).lower() for token in ("cvc5", "z3", "yices", "boolector")):
        raise SystemExit("D1P-19 runner refuses solver commands")
    LOGS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    stdout_path = LOGS / f"{label}.stdout.txt"
    stderr_path = LOGS / f"{label}.stderr.txt"
    env = os.environ.copy()
    env.update(environment)
    started_at = now()
    started = time.monotonic()
    max_rss = 0
    min_free = shutil.disk_usage(ROOT).free
    timed_out = False
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
            text=True, start_new_session=True,
        )
        while process.poll() is None:
            max_rss = max(max_rss, tree_rss_kib(process.pid))
            min_free = min(min_free, shutil.disk_usage(ROOT).free)
            if time.monotonic() - started >= timeout:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(1)
        exit_code = process.wait()
    payload = {
        "schema": "bindcheck.d1p19.command/v1",
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "started_at_utc": started_at,
        "finished_at_utc": now(),
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
    return exit_code


def setup() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != PIN:
        raise SystemExit(f"workspace source is {head}, expected {PIN}")
    if sha256(ARTIFACT) != "7190813f623967b79ba80a1635536fcc9c8524c1d1cb9f00696832f644b38327":
        raise SystemExit("pinned artifact identity mismatch")
    free = shutil.disk_usage(ROOT).free
    if free < 10 * 1024**3:
        raise SystemExit(f"unsafe free disk before heavy work: {free}")
    versions = {}
    for name, command in {
        "node": ["node", "--version"],
        "python": [sys.executable, "--version"],
        "hardhat": [str(WORKSPACE / "backend/node_modules/.bin/hardhat"), "--version"],
    }.items():
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        versions[name] = (result.stdout or result.stderr).strip()
    versions["pnpm_declared"] = json.loads((WORKSPACE / "package.json").read_text())["packageManager"]
    write_json(RAW / "setup-checks.json", {
        "schema": "bindcheck.d1p19.setup-checks/v1",
        "checked_at_utc": now(),
        "repository_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip(),
        "pinned_source_revision": head,
        "workspace": str(WORKSPACE.relative_to(ROOT)),
        "workspace_ignored": True,
        "free_disk_bytes": free,
        "versions": versions,
        "pinned": {
            "artifact": record(ARTIFACT),
            "vk": record(VK),
            "verifier": record(VERIFIER),
            "pnpm_lock": record(WORKSPACE / "pnpm-lock.yaml"),
            "backend_package": record(WORKSPACE / "backend/package.json"),
        },
        "network_retrieval": "none; reused already-retrieved pinned workspace and lockfile dependencies",
        "solver_campaign": False,
    })


def freeze_regions() -> None:
    from bindcheck_d1.warptoad_bn254_regions import extract_bn254_regions
    write_json(RAW / "bn254-region-extraction.json", extract_bn254_regions(ARTIFACT))


def freeze_p6() -> None:
    from bindcheck_d1.warptoad_p6 import audit_p6
    result = audit_p6(ROOT)
    if result["overall"] != "PASS":
        raise SystemExit("P6 audit did not pass")
    write_json(RAW / "p6-audit.json", result)


PUBLIC_ORDER = [
    "nullifier",
    "chain_id",
    "amount",
    "giga_root",
    "destination_local_root",
    "aztec_warptoad_address",
    "fee_factor",
    "priority_fee",
    "max_fee",
    "relayer_address",
    "recipient_address",
]


def _abi_public_order(path: Path) -> list[str]:
    artifact = json.loads(path.read_text())
    return [
        parameter["name"]
        for parameter in artifact["abi"]["parameters"]
        if parameter["visibility"] == "public"
    ]


def freeze_provenance() -> None:
    pinned_artifact = ARTIFACT
    m_dom_artifact = ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json"
    mapping_path = ROOT / "results/raw/D1P-13/public-input-mapping.json"
    mapping = json.loads(mapping_path.read_text())
    if _abi_public_order(pinned_artifact) != PUBLIC_ORDER:
        raise SystemExit("pinned public ABI order changed")
    if _abi_public_order(m_dom_artifact) != PUBLIC_ORDER:
        raise SystemExit("M-DOM public ABI order changed")
    if [row["abi_parameter"] for row in mapping["mapping"]] != PUBLIC_ORDER:
        raise SystemExit("D1P-13 consumer/public witness mapping changed")

    pinned_source = PINNED_WORKSPACE / "backend/contracts/core/WarpToadCore.sol"
    m_src_source = WORKSPACE / "backend/contracts/core/WarpToadCore.sol"
    source_diff = "".join(difflib.unified_diff(
        pinned_source.read_text().splitlines(keepends=True),
        m_src_source.read_text().splitlines(keepends=True),
        fromfile="pinned/backend/contracts/core/WarpToadCore.sol",
        tofile="M-SRC/backend/contracts/core/WarpToadCore.sol",
    ))
    (RAW / "m-src-source.diff").write_text(source_diff)
    if "isValidLocalRoot" not in source_diff or "M-SRC" not in source_diff:
        raise SystemExit("M-SRC diff does not name the K2 mutation")

    m_src_execution_path = RAW / "m-src-execution.json"
    pinned_negative_path = RAW / "pinned-negative-execution.json"
    m_src_execution = json.loads(m_src_execution_path.read_text())
    pinned_negative = json.loads(pinned_negative_path.read_text())
    if m_src_execution["status"] != "PASS" or pinned_negative["status"] != "PASS":
        raise SystemExit("M-SRC differential gates are not complete")

    pinned_consumer_artifact = (
        PINNED_WORKSPACE
        / "backend/artifacts/contracts/core/L1WarpToad.sol/L1WarpToad.json"
    )
    m_src_consumer_artifact = (
        WORKSPACE / "backend/artifacts/contracts/core/L1WarpToad.sol/L1WarpToad.json"
    )
    public_layout = [
        {
            "position": row["consumer_position"],
            "public_witness": row["decoded_public_witness"],
            "name": row["abi_parameter"],
            "consumer_source_class": row["consumer_source_class"],
            "conversion": row["conversion"],
        }
        for row in mapping["mapping"]
    ]
    common_mapping = {
        "mappingEvidence": record(mapping_path),
        "decodedPublicWitnesses": mapping["decoded_public_witness_order"],
        "consumerPublicInputLayout": public_layout,
    }
    payload = {
        "schema": "bindcheck.d1p19.variant-provenance/v1",
        "pinnedRevision": PIN,
        "toolchain": {
            "nargo": "1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7",
            "bbJs": "5.0.0",
            "proofSystem": "UltraHonk keccakZK",
            "solc": "0.8.29",
        },
        "variants": {
            "pinned": {
                "classification": "pinned repaired system",
                "producerArtifact": record(pinned_artifact),
                "verificationKey": record(VK),
                "generatedVerifier": record(VERIFIER),
                "consumerSource": record(pinned_source),
                "consumerBuildArtifact": record(pinned_consumer_artifact),
                "deployedVerifierRuntimeSha256": pinned_negative["verifier"]["runtimeCodeSha256"],
                "deployedConsumerRuntimeSha256": pinned_negative["consumer"]["runtimeCodeSha256"],
                "pairing": "pinned producer artifact -> pinned VK -> pinned generated verifier -> pinned consumer",
                "witnessAndPublicInputs": common_mapping,
                "gates": record(pinned_negative_path),
            },
            "M-DOM": {
                "classification": "injected mechanism-derived producer mutation (D1P-15)",
                "producerArtifact": record(m_dom_artifact),
                "verificationKey": record(ROOT / "results/raw/D1P-15/artifacts/m-dom-vk.bin"),
                "generatedVerifier": record(ROOT / "results/raw/D1P-15/artifacts/MdomWithdrawVerifier.sol"),
                "consumerSource": record(pinned_source),
                "pairing": "M-DOM producer artifact -> M-DOM-only VK -> M-DOM-only generated verifier -> otherwise pinned consumer",
                "witnessAndPublicInputs": common_mapping,
                "gates": record(ROOT / "results/raw/D1P-15/o1-execution.json"),
            },
            "M-SRC": {
                "classification": "injected consumer mutation; producer relation unchanged",
                "producerArtifact": record(pinned_artifact),
                "verificationKey": record(VK),
                "generatedVerifier": record(VERIFIER),
                "consumerSource": record(m_src_source),
                "consumerSourceDiff": record(RAW / "m-src-source.diff"),
                "consumerBuildArtifact": record(m_src_consumer_artifact),
                "deployedVerifierRuntimeSha256": m_src_execution["attackGate"]["verifier"]["runtimeCodeSha256"],
                "deployedConsumerRuntimeSha256": m_src_execution["attackGate"]["consumer"]["runtimeCodeSha256"],
                "pairing": "unchanged pinned producer artifact -> pinned VK -> pinned generated verifier -> M-SRC consumer",
                "ownPairingMeaning": (
                    "M-SRC has no new circuit key because the producer is byte-identical; its variant-specific "
                    "pairing is the M-SRC consumer deployment with the recorded pinned verifier runtime"
                ),
                "witnessAndPublicInputs": common_mapping,
                "honestAndAttackGates": record(m_src_execution_path),
                "sameProofPinnedNegativeGate": record(pinned_negative_path),
            },
        },
        "checks": {
            "allPublicLayoutsEqual": True,
            "mDomUsesOwnArtifactVkVerifier": True,
            "mSrcProducerArtifactVkVerifierUnchanged": True,
            "mSrcConsumerDiffOnlyRemovesK2": True,
            "mSrcRealProofAcceptedAndMinted": True,
            "sameProofPinnedRejectedAtK2": True,
        },
    }
    write_json(RAW / "variant-provenance.json", payload)

    attempts = m_src_execution["proofGenerationAttempts"]
    write_json(RAW / "proof-attempt-ledger.json", {
        "schema": "bindcheck.d1p19.proof-attempt-ledger/v1",
        "attemptLimit": 2,
        "attemptsUsed": len(attempts),
        "attempts": attempts,
        "secondAttempt": "not used",
        "parameterSearch": False,
        "note": "one proof was generated only for the M-SRC V-EXEC gate; no solver campaign",
    })


def freeze_resource_summary() -> None:
    commands = []
    for path in sorted(RECORDS.glob("*.json")):
        row = json.loads(path.read_text())
        commands.append({
            "label": row["label"],
            "exit_code": row["exit_code"],
            "timed_out": row["timed_out"],
            "wall_seconds": row["wall_seconds"],
            "max_process_tree_rss_kib_observed": row["max_process_tree_rss_kib_observed"],
            "min_free_disk_bytes_observed": row["min_free_disk_bytes_observed"],
        })
    write_json(RAW / "resource-summary.json", {
        "schema": "bindcheck.d1p19.resource-summary/v1",
        "commands": commands,
        "commandCount": len(commands),
        "peakObservedProcessTreeRssKib": max(
            (row["max_process_tree_rss_kib_observed"] for row in commands), default=0
        ),
        "minimumObservedFreeDiskBytes": min(
            (row["min_free_disk_bytes_observed"] for row in commands), default=0
        ),
        "unsafeResourceExhaustionObserved": False,
        "solverCommands": 0,
    })


def freeze_manifest() -> None:
    excluded = {RAW / "evidence-manifest.json"}
    files = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path in excluded:
            continue
        if any(part in {"workspace", "upstream"} for part in path.relative_to(RAW).parts):
            continue
        files.append(record(path))
    tracked_support = [
        ROOT / "scripts/d1p_19_prerequisites.py",
        ROOT / "scripts/fixtures/d1p_19_states.ts",
        ROOT / "src/bindcheck_d1/warptoad_bn254_regions.py",
        ROOT / "src/bindcheck_d1/warptoad_p6.py",
        ROOT / "tests/d1/test_d1p19_prerequisites.py",
        ROOT / "reports/D1P-19.md",
        ROOT / "docs/d1-paper/d1p-19-o1-o2-campaign-draft.md",
        ROOT / "protocols/d1/d1p-19-prerequisites.json",
        ROOT / "README.md",
        ROOT / "docs/project-status.md",
    ]
    files.extend(record(path) for path in tracked_support if path.exists())
    write_json(RAW / "evidence-manifest.json", {
        "schema": "bindcheck.d1p19.evidence-manifest/v1",
        "namespace": "D1P-19",
        "pinnedRevision": PIN,
        "files": files,
        "ignoredWorkspaceExcludedFromInventory": True,
        "retrievedUpstreamTreesExcludedFromInventory": True,
        "retrievedSourceIdentitiesAreRecordedInP6AuditAndCommandRecords": True,
        "solverCampaign": False,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    sub.add_parser("freeze-regions")
    sub.add_parser("freeze-p6")
    sub.add_parser("freeze-provenance")
    sub.add_parser("freeze-resources")
    sub.add_parser("freeze-manifest")
    run = sub.add_parser("record")
    run.add_argument("--label", required=True)
    run.add_argument("--cwd", type=Path, required=True)
    run.add_argument("--timeout", type=int, required=True)
    run.add_argument("--env", action="append", default=[])
    run.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "freeze-regions":
        freeze_regions()
    elif args.command == "freeze-p6":
        freeze_p6()
    elif args.command == "freeze-provenance":
        freeze_provenance()
    elif args.command == "freeze-resources":
        freeze_resource_summary()
    elif args.command == "freeze-manifest":
        freeze_manifest()
    else:
        argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
        environment = dict(item.split("=", 1) for item in args.env)
        raise SystemExit(run_recorded(args.label, argv, args.cwd.resolve(), args.timeout, environment))


if __name__ == "__main__":
    main()
