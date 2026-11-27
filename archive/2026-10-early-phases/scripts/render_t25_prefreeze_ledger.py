#!/usr/bin/env python3
"""Render the tracked T25 old-tool/new-tool full-DEV per-row ledger."""

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

    pattern_fields = [
        f"{pattern}_{suffix}"
        for pattern in PATTERNS
        for suffix in ("verdict", "applicability", "reasons", "unknown_reason_codes")
    ]
    fields = [
        "phase", "id", "repository", "commit", "crash", "run_status",
        "circuits", "verifiers", "consumers", "triples", "builds_ok",
        "builds_failed", "build_failure_causes", "files_inventoried",
        "files_skipped_by_cap", *pattern_fields, "runtime_seconds",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for phase, directory in (("before", args.before), ("after", args.after)):
            rows = json.loads((directory / "per-row-ledger.json").read_text(encoding="utf-8"))
            for row in sorted(rows, key=lambda item: item["id"]):
                pattern_values: dict[str, str] = {}
                for pattern in PATTERNS:
                    pattern_values[f"{pattern}_verdict"] = row["verdicts"][pattern]
                    pattern_values[f"{pattern}_applicability"] = row.get("applicability", {}).get(pattern, "NOT_REPORTED")
                    pattern_values[f"{pattern}_reasons"] = ";".join(row.get("reasons", {}).get(pattern, []))
                    pattern_values[f"{pattern}_unknown_reason_codes"] = ";".join(
                        row.get("unknown_reason_codes", {}).get(pattern, [])
                    ) or ("NOT_REPORTED" if phase == "before" else "")
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
                    **pattern_values,
                    "runtime_seconds": row["runtime_seconds"],
                })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
