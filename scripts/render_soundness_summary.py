#!/usr/bin/env python3
"""Render exact T25-to-soundness DEV counts from retained per-row ledgers."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib


PATTERNS = ("P1", "P2", "P3", "P4", "P5")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=pathlib.Path)
    parser.add_argument("--before-manifest", required=True, type=pathlib.Path)
    parser.add_argument("--after-manifest", required=True, type=pathlib.Path)
    parser.add_argument("--after-raw-ledger", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.ledger.open(encoding="utf-8", newline="")))
    before = {row["id"]: row for row in rows if row["phase"] == "before"}
    after = {row["id"]: row for row in rows if row["phase"] == "after"}
    if set(before) != set(after) or len(before) != 56:
        raise ValueError("expected identical 56-row before/after DEV populations")

    pattern_summary: dict[str, object] = {}
    for pattern in PATTERNS:
        counts = {
            phase: dict(sorted(collections.Counter(
                row[f"{pattern}_verdict"] for row in population.values()
            ).items()))
            for phase, population in (("before", before), ("after", after))
        }
        applicability = {
            phase: dict(sorted(collections.Counter(
                row[f"{pattern}_applicability"] for row in population.values()
            ).items()))
            for phase, population in (("before", before), ("after", after))
        }
        applicable_decisions = {}
        for phase, population in (("before", before), ("after", after)):
            applicable_rows = [
                row for row in population.values()
                if row[f"{pattern}_applicability"] == "APPLICABLE"
            ]
            applicable_decisions[phase] = {
                "applicable": len(applicable_rows),
                "decided": sum(
                    row[f"{pattern}_verdict"] != "UNKNOWN" for row in applicable_rows
                ),
                "unknown": sum(
                    row[f"{pattern}_verdict"] == "UNKNOWN" for row in applicable_rows
                ),
            }
        transitions = []
        for row_id in sorted(before):
            old = before[row_id][f"{pattern}_verdict"]
            new = after[row_id][f"{pattern}_verdict"]
            if old != new:
                transitions.append({
                    "id": row_id,
                    "repository": after[row_id]["repository"],
                    "before": old,
                    "after": new,
                    "after_reasons": after[row_id][f"{pattern}_reasons"].split(";")
                    if after[row_id][f"{pattern}_reasons"] else [],
                })
        pattern_summary[pattern] = {
            "counts": counts,
            "applicability": applicability,
            "applicable_decisions": applicable_decisions,
            "transitions": transitions,
        }

    before_manifest = json.loads(args.before_manifest.read_text(encoding="utf-8"))
    after_manifest = json.loads(args.after_manifest.read_text(encoding="utf-8"))
    after_raw = json.loads(args.after_raw_ledger.read_text(encoding="utf-8"))
    spsc = {
        phase: {
            key: population["DEV-F12"][key]
            for key in (
                "id", "repository", "commit", "P1_verdict", "P1_applicability",
                "P1_reasons", "P1_unknown_reason_codes",
            )
        }
        for phase, population in (("before", before), ("after", after))
    }
    payload = {
        "schema": "bindcheck-zk.soundness-dev-summary/v1",
        "population": {
            "rows_per_phase": len(before),
            "phases": 2,
            "ledger_rows": len(rows),
            "same_row_ids": True,
        },
        "sources": {
            "ledger": {"path": str(args.ledger), "sha256": sha256(args.ledger)},
            "before_manifest": {"path": str(args.before_manifest), "sha256": sha256(args.before_manifest)},
            "after_manifest": {"path": str(args.after_manifest), "sha256": sha256(args.after_manifest)},
            "after_raw_ledger": {"path": str(args.after_raw_ledger), "sha256": sha256(args.after_raw_ledger)},
        },
        "runs": {
            "before": {
                "revision": before_manifest.get("started_from_revision"),
                "analyzer_content_sha256": before_manifest.get("analyzer_content_sha256"),
            },
            "after": {
                "revision": after_manifest.get("started_from_revision"),
                "analyzer_content_sha256": after_manifest.get("analyzer_content_sha256"),
                "crashes": sum(bool(item["crash"]) for item in after_raw),
                "rows_with_triples": sum(item["triples"] > 0 for item in after_raw),
                "builds_ok": sum(item["builds_ok"] for item in after_raw),
                "builds_failed": sum(item["builds_failed"] for item in after_raw),
                "summed_analyzer_seconds": sum(item["runtime_seconds"] for item in after_raw),
                "slowest": max(
                    ({"id": item["id"], "runtime_seconds": item["runtime_seconds"]} for item in after_raw),
                    key=lambda item: item["runtime_seconds"],
                ),
            },
        },
        "patterns": pattern_summary,
        "spsc": spsc,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
