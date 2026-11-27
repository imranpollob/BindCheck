#!/usr/bin/env python3
"""Render the tracked T24 before/after per-row ledger from sealed raw runs."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib


PATTERNS = ("P1", "P2", "P3", "P4", "P5")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=pathlib.Path)
    parser.add_argument("--after", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    fields = [
        "phase", "id", "repository", "commit", "crash", "run_status",
        "circuits", "verifiers", "consumers", "triples", "builds_ok",
        "builds_failed", "build_failure_causes", "files_inventoried",
        "files_skipped_by_cap", "excluded_before_cap", "excluded_paths",
        *PATTERNS, "runtime_seconds",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for phase, directory in (("before", args.before), ("after", args.after)):
            rows = json.loads((directory / "per-row-ledger.json").read_text(encoding="utf-8"))
            for row in sorted(rows, key=lambda item: item["id"]):
                writer.writerow({
                    "phase": phase,
                    "id": row["id"],
                    "repository": row["repository"],
                    "commit": row["commit"],
                    "crash": str(row["crash"]).lower(),
                    "run_status": row["run_status"],
                    "circuits": row["circuits"],
                    "verifiers": row["verifiers"],
                    "consumers": row["consumers"],
                    "triples": row["triples"],
                    "builds_ok": row["builds_ok"],
                    "builds_failed": row["builds_failed"],
                    "build_failure_causes": json.dumps(row["build_failure_causes"], sort_keys=True),
                    "files_inventoried": row["files_inventoried"],
                    "files_skipped_by_cap": row["files_skipped_by_cap"],
                    "excluded_before_cap": len(row["excluded"]),
                    "excluded_paths": ";".join(
                        f"{item.get('category', '')}:{item.get('path', '')}"
                        for item in row["excluded"]
                    ),
                    **{pattern: row["verdicts"][pattern] for pattern in PATTERNS},
                    "runtime_seconds": row["runtime_seconds"],
                })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
