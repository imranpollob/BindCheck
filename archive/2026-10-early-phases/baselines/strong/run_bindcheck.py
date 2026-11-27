"""Run the unhinted BindCheck CLI on the frozen local adversarial cases."""
from __future__ import annotations

import argparse
import json
import os
import pathlib

from .common import ROOT, retain_native, run_command, sha256_file, utc_now, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    expected_path = ROOT / "redteam" / "adversarial" / "expected.json"
    cases = json.loads(expected_path.read_text(encoding="utf-8"))["cases"]
    records = []
    for case in cases:
        case_id = case["id"]
        case_dir = output / "cases" / case_id
        source = ROOT / "redteam" / "adversarial" / case_id
        record = run_command([str(ROOT / "bindcheck-zk"), "analyze", str(source)],
                             cwd=ROOT, timeout=args.timeout, process_group=True)
        native = retain_native(record, case_dir / "native", "bindcheck")
        parsed = None
        reason = None
        if record["timed_out"]:
            reason = "TIMEOUT"
        else:
            try:
                parsed = json.loads(record["stdout"])
            except json.JSONDecodeError:
                reason = "INVALID_JSON"
        if parsed is not None:
            write_json(case_dir / "result.json", parsed)
        records.append({
            "id": case_id,
            "native": native,
            "result_path": str(case_dir / "result.json") if parsed is not None else None,
            "result_sha256": sha256_file(case_dir / "result.json") if parsed is not None else None,
            "run_status": parsed.get("run", {}).get("status") if parsed is not None else ("TIMEOUT" if record["timed_out"] else "UNKNOWN"),
            "fatal_reason": parsed.get("run", {}).get("fatal_reason") if parsed is not None else reason,
            "pattern_verdicts": {key: value["verdict"] for key, value in parsed.get("patterns", {}).items()} if parsed is not None else {},
        })
        print(case_id, records[-1]["run_status"], flush=True)
    write_json(output / "manifest.json", {
        "schema": "bindcheck-redteam.bindcheck-manifest/v1",
        "generated_utc": utc_now(),
        "expected_path": str(expected_path), "expected_sha256": sha256_file(expected_path),
        "timeout_seconds": args.timeout, "records": records,
        "configured_circom": os.environ.get("BINDCHECK_CIRCOM"),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
