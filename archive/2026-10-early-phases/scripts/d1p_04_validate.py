#!/usr/bin/env python3
"""Run the frozen D1P-04 controls and 150 equivalence queries once each."""

import argparse
import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDRESS_SPACE = 4 * 1024**3
SECONDS = 30


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def limit_child():
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE, ADDRESS_SPACE))


def verify_freeze(freeze, manifest_path):
    for item in freeze["frozen_files"]:
        path = ROOT / item["path"]
        actual = sha256(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"frozen file mismatch {item['path']}: {actual}")
    if sha256(manifest_path) != freeze["artifact_manifest_sha256"]:
        raise RuntimeError("artifact manifest mismatch")
    solver = Path(freeze["solver"]["path"])
    if sha256(solver) != freeze["solver"]["sha256"]:
        raise RuntimeError("solver binary mismatch")
    if freeze["limits"] != {
        "calls_max": 152,
        "seconds_per_call": SECONDS,
        "solver_wall_seconds_max": 4560,
        "address_space_bytes": ADDRESS_SPACE,
        "attempts_per_call": 1,
        "sequential": True,
    }:
        raise RuntimeError("unexpected frozen limits")
    actual_platform = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    if freeze["platform"] != actual_platform:
        raise RuntimeError(f"platform mismatch: {actual_platform}")
    return solver


def run_one(index, kind, name, query_path, expected, solver, argv_tail, logs_dir):
    query_path = Path(query_path)
    input_bytes = query_path.read_bytes()
    stem = f"{index:03d}_{kind}_{name.replace('/', '__')}"
    stdout_path = logs_dir / f"{stem}.stdout"
    stderr_path = logs_dir / f"{stem}.stderr"
    record_path = logs_dir / f"{stem}.json"
    argv = [str(solver), *argv_tail]
    started_utc = utc_now()
    started = time.monotonic()
    timed_out = False
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        preexec_fn=limit_child,
    )
    try:
        stdout, stderr = process.communicate(input=input_bytes, timeout=SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    elapsed = time.monotonic() - started
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    output_lines = stdout.decode("utf-8", errors="replace").splitlines()
    parsed = output_lines[0].strip().lower() if output_lines else "missing"
    if parsed not in ("sat", "unsat", "unknown"):
        parsed = "malformed"
    ok = (not timed_out and process.returncode == 0 and parsed == expected)
    record = {
        "index": index,
        "kind": kind,
        "name": name,
        "query_path": str(query_path.relative_to(ROOT)),
        "query_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "query_bytes": len(input_bytes),
        "expected": expected,
        "parsed": parsed,
        "ok": ok,
        "argv": argv,
        "stdin": "exact query_path bytes",
        "started_utc": started_utc,
        "finished_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 6),
        "exit_status": process.returncode,
        "timed_out": timed_out,
        "seconds_limit": SECONDS,
        "address_space_bytes": ADDRESS_SPACE,
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stdout_sha256": sha256(stdout_path),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "stderr_sha256": sha256(stderr_path),
        "record_path": str(record_path.relative_to(ROOT)),
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    args.freeze = args.freeze.resolve()
    args.manifest = args.manifest.resolve()
    args.output = args.output.resolve()
    args.ledger = args.ledger.resolve()
    for path in (args.output, args.ledger):
        if path.exists():
            raise FileExistsError(f"fresh output required: {path}")
    freeze = json.loads(args.freeze.read_text())
    manifest = json.loads(args.manifest.read_text())
    solver = verify_freeze(freeze, args.manifest)
    if manifest["counts"] != {"parents": 6, "cells_per_parent": 25,
                              "specialized_queries": 150,
                              "equivalence_queries": 150, "controls": 2}:
        raise RuntimeError("unexpected artifact counts")
    args.output.mkdir(parents=True)
    logs_dir = args.output / "calls"
    logs_dir.mkdir()

    planned = []
    for control in manifest["controls"]:
        planned.append(("control", control["name"], ROOT / control["path"],
                        control["sha256"], control["expected"]))
    for artifact in manifest["artifacts"]:
        planned.append(("cell", artifact["slot"], ROOT / artifact["equivalence"]["path"],
                        artifact["equivalence"]["sha256"], "unsat"))
    if len(planned) != 152:
        raise RuntimeError(f"unexpected call plan: {len(planned)}")
    for _, name, path, expected_hash, _ in planned:
        if sha256(path) != expected_hash:
            raise RuntimeError(f"planned query mismatch: {name}")

    records = []
    stop_reason = None
    total_started = time.monotonic()
    for index, (kind, name, path, _, expected) in enumerate(planned, 1):
        if stop_reason is not None:
            records.append({"index": index, "kind": kind, "name": name,
                            "query_path": str(path.relative_to(ROOT)),
                            "status": "UNRUN_STOPPED", "reason": stop_reason})
            continue
        record = run_one(index, kind, name, path, expected, solver,
                         freeze["solver"]["arguments"], logs_dir)
        records.append(record)
        if not record["ok"]:
            stop_reason = f"{kind} {name} expected {expected}, got {record['parsed']}"

    elapsed = time.monotonic() - total_started
    executed = [record for record in records if "parsed" in record]
    cell_records = [record for record in executed if record["kind"] == "cell"]
    eligible = (stop_reason is None and len(cell_records) == 150
                and all(record["parsed"] == "unsat" and record["ok"] for record in cell_records)
                and all(artifact["producer_prefix_audit"]["ordered_bytes_identical"]
                        for artifact in manifest["artifacts"]))
    ledger = {
        "task": "D1P-04",
        "status": "VALIDATION_PASS" if eligible else "VALIDATION_INCOMPLETE",
        "research_verdict": "UNKNOWN",
        "partition_eligible_for_primary_use": eligible,
        "stop_reason": stop_reason,
        "freeze": {"path": str(args.freeze.relative_to(ROOT)), "sha256": sha256(args.freeze)},
        "artifact_manifest": {"path": str(args.manifest.relative_to(ROOT)),
                              "sha256": sha256(args.manifest)},
        "solver": freeze["solver"],
        "platform": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "limits": freeze["limits"],
        "counts": {
            "planned": len(planned),
            "executed": len(executed),
            "unrun": len(planned) - len(executed),
            "controls_executed": sum(r.get("kind") == "control" and "parsed" in r for r in records),
            "cells_executed": len(cell_records),
            "cells_unsat": sum(r["parsed"] == "unsat" for r in cell_records),
            "cells_sat": sum(r["parsed"] == "sat" for r in cell_records),
            "cells_unknown_or_error": sum(r["parsed"] not in ("sat", "unsat") or not r["ok"]
                                          for r in cell_records),
            "producer_prefix_audits_passed": sum(
                artifact["producer_prefix_audit"]["ordered_bytes_identical"]
                for artifact in manifest["artifacts"]),
        },
        "elapsed_seconds": round(elapsed, 6),
        "solver_elapsed_seconds": round(sum(r["elapsed_seconds"] for r in executed), 6),
        "records": records,
        "interpretation": (
            "Eligibility is transformation evidence only; no parent satisfiability, "
            "consumer-direction, proof, consumer, or D1 verdict follows."
        ),
    }
    raw_ledger = args.output / "equivalence-ledger.json"
    payload = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    raw_ledger.write_text(payload)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(payload)
    print(json.dumps({"status": ledger["status"], **ledger["counts"],
                      "elapsed_seconds": ledger["elapsed_seconds"]}, sort_keys=True))
    raise SystemExit(0 if eligible else 2)


if __name__ == "__main__":
    main()
