#!/usr/bin/env python3
"""Record the frozen D1P-06 execution abort without launching a process."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAILURE = (
    "D1P-05 run_monitored observed the goal-only prefix solver root disappear "
    "before Popen.poll() reported completion, then kill_process_group raised "
    "PermissionError: [Errno 1] Operation not permitted. The exception escaped "
    "before a per-call JSON record or campaign ledger was written."
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"fresh abort ledger required: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def plan(manifest):
    rows = []
    for item in manifest["controls"]:
        rows.append(("control", item["name"], item))
    for arm in ("goal_only", "cone_only", "combined"):
        for item in manifest[arm]:
            rows.append((arm, item["slot"], item))
    for group in manifest["partitioned"]:
        for item in group["cells"]:
            rows.append(("partitioned", f"{group['slot']}/{item['id']}", item))
    if len(rows) != 166:
        raise RuntimeError(f"unexpected plan length: {len(rows)}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--raw-ledger", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    freeze = json.loads(args.freeze.read_text())
    manifest = json.loads(args.manifest.read_text())
    rows = plan(manifest)
    calls = args.execution_root / "calls"
    records = []

    completed_files = [
        calls / "001_control_known_equivalence.json",
        calls / "002_control_deliberate_mismatch.json",
        calls / "003_goal_only_check_added__nonvacuous.json",
    ]
    for expected_index, path in enumerate(completed_files, 1):
        record = json.loads(path.read_text())
        if record["index"] != expected_index or record.get("attempts") != 1:
            raise RuntimeError(f"unexpected completed record: {path}")
        records.append(record)

    arm, name, item = rows[3]
    if (arm, name) != ("goal_only", "check_added/prefix"):
        raise RuntimeError("fourth frozen call identity changed")
    stdout = calls / "004_goal_only_check_added__prefix.stdout"
    stderr = calls / "004_goal_only_check_added__prefix.stderr"
    if not stdout.is_file() or not stderr.is_file():
        raise RuntimeError("partial fourth-call output is missing")
    lines = stdout.read_text(errors="replace").splitlines()
    if not lines or lines[0].strip().lower() != "sat" or stderr.stat().st_size != 0:
        raise RuntimeError("unexpected partial fourth-call output")
    if sha256(ROOT / item["path"]) != item["sha256"]:
        raise RuntimeError("fourth query input changed")
    records.append({
        "index": 4, "arm": arm, "kind": arm, "name": name,
        "query_path": item["path"], "query_sha256": item["sha256"],
        "attempts": 1, "status": "MONITORING_CLEANUP_EXCEPTION",
        "result": "UNKNOWN", "parsed_stdout": "sat",
        "stdout_path": relative(stdout), "stdout_sha256": sha256(stdout),
        "stderr_path": relative(stderr), "stderr_sha256": sha256(stderr),
        "exit_status": None, "elapsed_seconds": None,
        "peak_tree_rss_bytes": None, "memory_samples": None,
        "sat_witness_output_present_but_unusable": len(lines) > 1,
        "validated_full_acir_evidence": False,
        "error": FAILURE,
    })

    stop_reason = "infrastructure failure on frozen call 4: " + FAILURE
    for index, (arm, name, item) in enumerate(rows[4:], 5):
        records.append({
            "index": index, "arm": arm, "name": name,
            "query_path": item["path"], "query_sha256": item["sha256"],
            "attempts": 0, "status": "UNRUN", "result": "UNRUN",
            "reason": stop_reason,
        })

    if len(records) != 166:
        raise RuntimeError(f"unexpected ledger size: {len(records)}")
    goal_records = [r for r in records if r["arm"] == "goal_only"]
    goal_summary = []
    for record in goal_records:
        goal_summary.append({
            "slot": record["name"], "result": record["result"],
            "attempted": record["attempts"] == 1,
            "usable": record["status"] == "COMPLETED" and record["result"] in ("SAT", "UNSAT"),
            "elapsed_seconds": record.get("slot_elapsed_seconds", record.get("elapsed_seconds")),
            "observed_peak_tree_rss_bytes": record.get("peak_tree_rss_bytes"),
        })
    comparison = []
    for family in ("check_added", "running_flag"):
        for query in ("nonvacuous", "prefix", "tail"):
            comparison.append({
                "slot": f"{family}/{query}", "unsplit_result": "UNRUN",
                "unsplit_elapsed_seconds": None, "partitioned_result": "UNRUN",
                "partitioned_elapsed_seconds": None,
                "cell_counts": {"sat": 0, "unsat": 0, "unknown": 0, "unrun": 25},
                "resource_use": None, "overhead_seconds": None,
            })
    attempted = [r for r in records if r["attempts"] == 1]
    usable = [r for r in attempted if r["status"] == "COMPLETED"]
    ledger = {
        "task": "D1P-06",
        "status": "CAMPAIGN_STOPPED_INFRASTRUCTURE_FAILURE",
        "task_completion": "INCOMPLETE",
        "research_verdict": "UNKNOWN",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "stop_reason": stop_reason,
        "freeze": {"path": relative(args.freeze), "sha256": sha256(args.freeze)},
        "input_manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest)},
        "reference_environment": freeze["reference_environment"],
        "solver": freeze["solver"], "resource_policy": freeze["resource_policy"],
        "limits": freeze["limits"],
        "counts": {
            "planned_calls": 166, "attempted_calls": len(attempted),
            "usable_completed_calls": len(usable), "unusable_attempted_calls": 1,
            "unrun_calls": 162, "controls_attempted": 2, "controls_passed": 2,
            "primary_attempted": 2, "primary_usable": 1,
            "combined_attempted": 0, "partitioned_cells_attempted": 0,
        },
        "observations": {
            "controls": [
                {"name": r["name"], "result": r["result"],
                 "elapsed_seconds": r["elapsed_seconds"],
                 "peak_tree_rss_bytes": r["peak_tree_rss_bytes"]}
                for r in records[:2]
            ],
            "goal_only": goal_summary, "cone_only": [],
            "comparison": comparison,
        },
        "observed_peak_tree_rss_bytes_over_usable_records": max(
            r.get("peak_tree_rss_bytes", 0) or 0 for r in usable
        ),
        "known_usable_solver_wall_seconds": round(sum(
            r.get("elapsed_seconds", 0) or 0 for r in usable
        ), 6),
        "records": records,
        "historical_linux_background": {
            "scope": "six exact combined queries only; background, not timing parity",
            "result": "six timeouts/UNKNOWN",
            "elapsed_seconds": [300.207, 300.131, 300.147, 300.167, 300.127, 300.192],
            "resource_policy": "4 GiB RLIMIT_AS on Linux x86_64",
        },
        "interpretation": (
            "The controls and one goal-only diagnostic are usable. The fourth "
            "call's SAT text is not a usable result because exit/resource/elapsed "
            "recording did not complete. No combined or partitioned query ran, so "
            "D1P-06 does not answer the decomposition question. The sampled cutoff "
            "is not a hard cap, and the D1 verdict remains UNKNOWN."
        ),
    }
    write_json(args.raw_ledger, ledger)
    write_json(args.ledger, ledger)
    print(json.dumps({"status": ledger["status"], **ledger["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
