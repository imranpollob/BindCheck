#!/usr/bin/env python3
"""D1P-15 owned-local runner and resource recorder.

The runner has no solver entry point.  Its ``record`` command exists so every
compile, witness execution, key derivation, and concrete fixture execution is
captured under the new D1P-15 namespace with a process-tree RSS sample.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-15"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
WORKSPACE = RAW / "workspace/source"
PINNED_ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
PINNED_VK = ROOT / "results/raw/D1P-13/artifacts/rebuilt/withdraw-vk.bin"
NARGO = ROOT / "results/raw/D1P-13/tools/nargo-beta22/nargo"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, base: Path = ROOT) -> dict:
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
            argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
            text=True, start_new_session=True,
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
        "schema": "bindcheck.d1p15.command/v1",
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
    write_json(RECORDS / f"{label}.json", payload)
    return payload


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def audit() -> dict:
    """Fail closed over the frozen evidence and emit compact audit records."""
    provenance = read_json(RAW / "poseidon2-provenance.json")
    references = read_json(RAW / "hash-reference-check.json")
    execution = read_json(RAW / "o1-execution.json")
    honest = read_json(RAW / "honest-proof.json")
    foreign = read_json(RAW / "foreign-proof.json")

    assert provenance["artifact"]["sha256"] == sha256(PINNED_ARTIFACT)
    assert len(provenance["calls"]) == 86
    assert provenance["counts"] == {"merkle_node": 84, "siloed_note": 1, "unique_note": 1}
    assert provenance["orientation_counts"] == {"node_left": 42, "node_right": 42}
    assert references["allPassed"] and len(references["fixtures"]) == 2
    assert all(fixture["poseidon2"]["checkedOpcodes"] == 86 for fixture in references["fixtures"])
    assert execution["status"] == "PASS" and execution["injected"] is True
    assert execution["configuredWarpToadAddress"] != execution["foreignContractAddress"]
    assert len(execution["proofGenerationAttempts"]) == 2
    assert execution["cases"]["honest"]["pinnedExecution"]["outcome"] == "accepted"
    assert execution["cases"]["foreign"]["pinnedExecution"]["outcome"] == "rejected"
    assert "Cannot satisfy constraint" in execution["cases"]["foreign"]["pinnedExecution"]["error"]["message"]
    for case_name, proof in (("honest", honest), ("foreign", foreign)):
        assert proof["case"] == case_name and proof["injected"] is True
        assert proof["proofBytes"] == 9152 and len(proof["publicInputs"]) == 11
        assert proof["jsVerified"] and proof["generatedVerifierAccepted"]
        effects = execution["cases"][case_name]["mint"]["effects"]
        assert effects == {
            "nullifierWritten": True,
            "recipientDelta": "5000000000000000000",
            "relayerDelta": "0",
            "totalSupplyDelta": "5000000000000000000",
        }
    mutation_vk = RAW / "artifacts/m-dom-vk.bin"
    assert sha256(mutation_vk) != sha256(PINNED_VK)
    assert execution["artifacts"]["mutation"]["sha256"] == sha256(RAW / "artifacts/m-dom-withdraw.json")
    assert execution["artifacts"]["pinned"]["sha256"] == sha256(PINNED_ARTIFACT)

    records = [read_json(path) for path in sorted(RECORDS.glob("*.json"))]
    solver_tokens = ("cvc5", "z3", "yices", "boolector")
    solver_commands = [
        record["label"] for record in records
        if any(any(token in arg.lower() for token in solver_tokens) for arg in record["argv"])
    ]
    assert not solver_commands
    failures = [record["label"] for record in records if record["exit_code"] != 0]
    assert failures == ["o1-injected-vexec-preflight-import-failure"]

    source_diff = subprocess.run(
        ["git", "diff", "--", "backend/circuits/nargo_hashing/src/lib.nr", "backend/circuits/withdraw/src/main.nr"],
        cwd=WORKSPACE, capture_output=True, text=True, check=True,
    ).stdout
    (RAW / "m-dom-source.diff").write_text(source_diff)
    assert "D1P-15 INJECTED M-DOM" in source_diff
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert head == PIN

    setup = {
        "schema": "bindcheck.d1p15.setup-identities/v1",
        "pinned_source_revision": head,
        "isolated_workspace": str(WORKSPACE.relative_to(ROOT)),
        "workspace_ignored": True,
        "toolchain": {
            "nargo": {
                **file_record(NARGO),
                "version": "1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7",
            },
            "bb_js": "5.0.0",
            "noir_js": "1.0.0-beta.22",
            "solc": "0.8.29",
        },
        "locked_dependencies": {
            "pnpm_lock": file_record(WORKSPACE / "pnpm-lock.yaml"),
            "backend_package": file_record(WORKSPACE / "backend/package.json"),
            "poseidon2": "@zkpassport/poseidon2@0.6.2",
            "poseidon_bn254": "poseidon-lite@0.3.0",
        },
        "artifact_identity": {
            "pinned_artifact": file_record(PINNED_ARTIFACT),
            "mutation_artifact": file_record(RAW / "artifacts/m-dom-withdraw.json"),
            "pinned_vk": file_record(PINNED_VK),
            "mutation_vk": file_record(mutation_vk),
            "mutation_verifier": file_record(RAW / "artifacts/MdomWithdrawVerifier.sol"),
            "own_key_identity": sha256(mutation_vk) != sha256(PINNED_VK),
        },
    }
    write_json(RAW / "setup-identities.json", setup)

    proof_ledger = {
        "schema": "bindcheck.d1p15.proof-attempt-ledger/v1",
        "limit": 2,
        "attempts": [
            {
                **item,
                "proof": file_record(RAW / f"{item['case']}-proof.json"),
                "proof_bytes": read_json(RAW / f"{item['case']}-proof.json")["proofBytes"],
                "outcome": "generated; bb.js accepted; generated Solidity verifier accepted; consumer mint succeeded",
            }
            for item in execution["proofGenerationAttempts"]
        ],
        "preflight_failure": {
            "record": file_record(RECORDS / "o1-injected-vexec-preflight-import-failure.json"),
            "stage": "TypeScript module import before backend construction or proof generation",
            "proof_attempts_consumed": 0,
        },
        "parameter_search": False,
    }
    write_json(RAW / "proof-attempt-ledger.json", proof_ledger)

    resource_summary = {
        "schema": "bindcheck.d1p15.resource-summary/v1",
        "classification": "development resource observation; not performance evidence",
        "commands": [{
            "label": record["label"],
            "wall_seconds": record["wall_seconds"],
            "max_process_tree_rss_kib_observed": record["max_process_tree_rss_kib_observed"],
            "timed_out": record["timed_out"],
            "exit_code": record["exit_code"],
        } for record in records],
        "unsafe_resource_exhaustion": False,
    }
    write_json(RAW / "resource-summary.json", resource_summary)

    result = {
        "schema": "bindcheck.d1p15.audit/v1",
        "status": "PASS",
        "checks": {
            "pinned_revision": True,
            "poseidon2_calls_fully_classified": 86,
            "reference_checks": 172,
            "own_mutation_key": True,
            "honest_mutation_mint": True,
            "foreign_mutation_v_exec": True,
            "foreign_pinned_rejection": True,
            "proof_attempts": 2,
            "solver_commands": solver_commands,
            "only_expected_preflight_failure": failures,
        },
        "claim_limits": {
            "injected": True,
            "synthetic_fixed_state": True,
            "cross_chain_reachability": False,
            "security_verdict": "UNKNOWN",
            "performance_result": False,
        },
    }
    write_json(RAW / "audit.json", result)

    excluded = {RAW / "evidence-manifest.json"}
    files = [
        path for path in sorted(RAW.rglob("*"))
        if path.is_file() and path not in excluded and "workspace" not in path.relative_to(RAW).parts
    ]
    manifest = {
        "schema": "bindcheck.d1p15.evidence-manifest/v1",
        "namespace": "D1P-15",
        "pinned_revision": PIN,
        "workspace_excluded_from_inventory": True,
        "files": [file_record(path) for path in files],
    }
    write_json(RAW / "evidence-manifest.json", manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--label", required=True)
    record.add_argument("--cwd", type=Path, default=ROOT)
    record.add_argument("--timeout", type=int, default=1800)
    record.add_argument("argv", nargs=argparse.REMAINDER)
    sub.add_parser("audit")
    args = parser.parse_args()
    if args.command == "record":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            parser.error("record requires a command after --")
        result = run_recorded(args.label, argv, args.cwd.resolve(), args.timeout)
        return result["exit_code"] or (124 if result["timed_out"] else 0)
    if args.command == "audit":
        print(json.dumps(audit(), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
