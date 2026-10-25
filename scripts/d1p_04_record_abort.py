#!/usr/bin/env python3
"""Record the frozen D1P-04 launch failure without invoking a solver."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_COMMAND = (
    ".venv-d1p-00/bin/python -I scripts/d1p_04_validate.py "
    "--freeze metadata/d1/d1p-04-execution-freeze.json "
    "--manifest metadata/d1/d1p-04-artifact-manifest.json "
    "--output results/raw/D1P-04/validation "
    "--ledger metadata/d1/d1p-04-equivalence-ledger.json"
)
STOP_REASON = (
    "The known-equivalence control could not start: subprocess.Popen raised "
    "SubprocessError('Exception occurred in preexec_fn.') while applying the "
    "frozen 4 GiB RLIMIT_AS; cvc5 was not executed."
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


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

    freeze = json.loads(args.freeze.read_text())
    manifest = json.loads(args.manifest.read_text())
    raw_ledger = args.output / "equivalence-ledger.json"
    error_path = args.output / "launch-error.json"
    for path in (raw_ledger, error_path, args.ledger):
        if path.exists():
            raise FileExistsError(f"refusing to replace evidence: {path}")
    if sha256(args.manifest) != freeze["artifact_manifest_sha256"]:
        raise RuntimeError("manifest no longer matches execution freeze")
    if len(manifest["artifacts"]) != 150 or len(manifest["controls"]) != 2:
        raise RuntimeError("unexpected frozen call plan")

    planned = []
    for control in manifest["controls"]:
        planned.append({
            "kind": "control",
            "name": control["name"],
            "query_path": control["path"],
            "query_sha256": control["sha256"],
            "expected": control["expected"],
        })
    for artifact in manifest["artifacts"]:
        planned.append({
            "kind": "cell",
            "name": artifact["slot"],
            "query_path": artifact["equivalence"]["path"],
            "query_sha256": artifact["equivalence"]["sha256"],
            "expected": "unsat",
        })

    records = []
    for index, item in enumerate(planned, 1):
        record = {"index": index, **item, "solver_process_launched": False}
        if index == 1:
            record.update({
                "status": "NOT_LAUNCHED_PREEXEC_FAILURE",
                "attempts": 1,
                "exit_status": None,
                "elapsed_solver_seconds": 0,
                "error_class": "subprocess.SubprocessError",
                "error": "Exception occurred in preexec_fn.",
                "reason": STOP_REASON,
            })
        else:
            record.update({
                "status": "UNRUN_STOPPED",
                "attempts": 0,
                "exit_status": None,
                "elapsed_solver_seconds": 0,
                "reason": "Stopped after the first control launch failure; no retry was permitted.",
            })
        records.append(record)

    recorded_at = datetime.now(timezone.utc).isoformat()
    error = {
        "task": "D1P-04",
        "recorded_at_utc": recorded_at,
        "runner_command": RUNNER_COMMAND,
        "runner_exit_status": 1,
        "first_planned_call": records[0],
        "exception_terminal_line": (
            "subprocess.SubprocessError: Exception occurred in preexec_fn."
        ),
        "independent_no_solver_diagnosis": {
            "command": (
                ".venv-d1p-00/bin/python - <<'PY' # getrlimit/setrlimit probe; "
                "no subprocess or solver invocation"
            ),
            "rlimit_as_before": [9223372036854775807, 9223372036854775807],
            "setrlimit_request": [4294967296, 4294967296],
            "result": "ValueError('current limit exceeds maximum limit')",
        },
        "solver_stdout_files": [],
        "solver_stderr_files": [],
        "interpretation": (
            "The failure occurred in the child pre-exec hook before exec of the "
            "cvc5 binary. There is therefore no solver exit status or solver log."
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    error_path.write_text(json.dumps(error, indent=2, sort_keys=True) + "\n")

    ledger = {
        "task": "D1P-04",
        "status": "VALIDATION_INCOMPLETE",
        "research_verdict": "UNKNOWN",
        "partition_eligible_for_primary_use": False,
        "recorded_at_utc": recorded_at,
        "stop_reason": STOP_REASON,
        "freeze": {"path": relative(args.freeze), "sha256": sha256(args.freeze)},
        "artifact_manifest": {
            "path": relative(args.manifest),
            "sha256": sha256(args.manifest),
        },
        "launch_error": {"path": relative(error_path), "sha256": sha256(error_path)},
        "solver": freeze["solver"],
        "platform": freeze["platform"],
        "limits": freeze["limits"],
        "counts": {
            "planned": 152,
            "launch_attempts": 1,
            "solver_processes_launched": 0,
            "solver_calls_executed": 0,
            "unrun": 152,
            "controls_executed": 0,
            "cells_executed": 0,
            "cells_unsat": 0,
            "cells_sat": 0,
            "cells_unknown_or_error": 0,
            "cells_unrun": 150,
            "producer_prefix_audits_passed": sum(
                bool(a["producer_prefix_audit"]["ordered_bytes_identical"])
                for a in manifest["artifacts"]
            ),
        },
        "solver_elapsed_seconds": 0,
        "records": records,
        "interpretation": (
            "All 150 cells are unusable for primary work because SMT equivalence "
            "is unestablished. Generation and byte audits are not a research result; "
            "no parent satisfiability, consumer-direction, proof, consumer, or D1 "
            "verdict follows."
        ),
    }
    payload = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    raw_ledger.write_text(payload)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(payload)
    print(json.dumps({"status": ledger["status"], **ledger["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
