#!/usr/bin/env python3
"""Summarize oracle run result.json files into an operator x variant matrix.

Usage: python3 oracle/summarize.py <result-dir> [<result-dir> ...]
Reads each run's result.json (the runner summary) and prints, per variant, the
per-operator verdict and wall time. Read-only; for the S4 report.
"""
import json
import sys
from pathlib import Path

SHORT = {"E4-CONFIRMED": "E4", "NOT_CONFIRMED": "NOT", "UNKNOWN": "UNK"}


def summarize(run_dir: Path):
    summary = json.loads((run_dir / "result.json").read_text())
    print(f"\n== {summary['case_id']}  ({run_dir.name})  status={summary['status']}  wall={summary['wall_seconds']:.1f}s")
    if summary.get("failure"):
        print(f"   FAILURE: {summary['failure']}")
    for variant in summary.get("variants", []):
        honest = variant["honest"]
        print(f"  -- variant {variant['variant']}: honest_ok={honest['succeeded']} verifier_accepted={honest['verifier_accepted']}")
        for t in variant["trials"]:
            v = SHORT.get(t["result"], t["result"])
            print(f"       {t['id']:20s} {v:4s} {t.get('wall_seconds', 0):6.2f}s  {t['reason'][:58]}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        summarize(Path(arg))
