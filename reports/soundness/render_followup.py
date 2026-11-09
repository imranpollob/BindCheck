#!/usr/bin/env python3
"""Render a complete, reproducible prior-after versus follow-up DEV ledger."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib


PATTERNS = ("P1", "P2", "P3", "P4", "P5")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=pathlib.Path, required=True)
    parser.add_argument("--after", type=pathlib.Path, required=True)
    parser.add_argument("--csv", type=pathlib.Path, required=True)
    parser.add_argument("--summary", type=pathlib.Path, required=True)
    args = parser.parse_args()
    old = {row["id"]: row for row in json.loads(args.before.read_text())}
    new = {row["id"]: row for row in json.loads(args.after.read_text())}
    if len(old) != 56 or set(old) != set(new):
        raise ValueError("DEV population mismatch")
    rows = []
    for row_id in sorted(old):
        if (old[row_id]["repository"], old[row_id]["commit"]) != (new[row_id]["repository"], new[row_id]["commit"]):
            raise ValueError(f"pinned source changed: {row_id}")
        for pattern in PATTERNS:
            prior, current = old[row_id], new[row_id]
            rows.append({
                "id": row_id, "repository": current["repository"], "commit": current["commit"],
                "pattern": pattern,
                "before_verdict": prior["verdicts"][pattern],
                "after_verdict": current["verdicts"][pattern],
                "before_reasons": ";".join(prior["reasons"][pattern]),
                "after_reasons": ";".join(current["reasons"][pattern]),
                "before_applicability": prior["applicability"][pattern],
                "after_applicability": current["applicability"][pattern],
            })
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema": "bindcheck-zk.soundness-followup-summary/v1",
        "population_rows": len(old),
        "before": {"path": str(args.before), "sha256": digest(args.before)},
        "after": {"path": str(args.after), "sha256": digest(args.after)},
        "ledger": {"path": str(args.csv), "sha256": digest(args.csv)},
        "patterns": {},
        "changed_verdicts": [row for row in rows if row["before_verdict"] != row["after_verdict"]],
        "changed_reasons_only": [row for row in rows if row["before_verdict"] == row["after_verdict"] and row["before_reasons"] != row["after_reasons"]],
    }
    for pattern in PATTERNS:
        selected = [row for row in rows if row["pattern"] == pattern]
        summary["patterns"][pattern] = {
            "before": dict(sorted(collections.Counter(row["before_verdict"] for row in selected).items())),
            "after": dict(sorted(collections.Counter(row["after_verdict"] for row in selected).items())),
        }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
