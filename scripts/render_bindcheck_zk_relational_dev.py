#!/usr/bin/env python3
"""Render tracked exact-count tables from one relational DEV raw run."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DIMENSIONS = ("EXTENT", "MASK", "REPRESENTATION", "MULTIPLICITY_SCOPE", "ROLE_IDENTITY")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_run", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "reports" / "relational")
    args = parser.parse_args()
    raw_run = args.raw_run.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((raw_run / "per-row-ledger.json").read_text(encoding="utf-8"))
    manifest = json.loads((raw_run / "manifest.json").read_text(encoding="utf-8"))

    ledger_path = output_dir / "dev-ledger.csv"
    fields = [
        "id", "repository", "commit", "fatal_reason", "compiled_relations", "paired_paths",
    ]
    for dimension in DIMENSIONS:
        fields.extend([
            f"{dimension}_verdict", f"{dimension}_applicability",
            f"{dimension}_applicable_results", f"{dimension}_decided_results",
            f"{dimension}_violation_results", f"{dimension}_reasons",
        ])
    with ledger_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ledger:
            rendered: dict[str, Any] = {key: row[key] for key in fields[:6]}
            for dimension in DIMENSIONS:
                item = row["dimensions"][dimension]
                rendered.update({
                    f"{dimension}_verdict": item["verdict"],
                    f"{dimension}_applicability": item["applicability"],
                    f"{dimension}_applicable_results": item["applicable_results"],
                    f"{dimension}_decided_results": item["decided_results"],
                    f"{dimension}_violation_results": item["violation_results"],
                    f"{dimension}_reasons": ";".join(item["reasons"]),
                })
            writer.writerow(rendered)

    pair_findings: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    decision_rows: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    for row in ledger:
        result_path = raw_run / f"{row['id']}--result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        for pair_index, pair in enumerate(payload.get("relational", {}).get("pairs", [])):
            for dimension, finding in pair["dimensions"].items():
                pair_findings[dimension].append(finding)
                record = {
                    "id": row["id"],
                    "repository": row["repository"],
                    "commit": row["commit"],
                    "pair_index": pair_index,
                    "dimension": dimension,
                    "verdict": finding["verdict"],
                    "reason": finding["reason"],
                    "circuit": pair["circuit"]["path"],
                    "consumer": pair["consumer"]["path"],
                    "function": pair["consumer"]["function"],
                    "result": result_path.relative_to(ROOT).as_posix(),
                }
                if finding["verdict"] != "UNKNOWN":
                    decision_rows.append(record)
                if finding["verdict"] == "VIOLATION":
                    flags.append(record)

    decisions_path = output_dir / "dev-decisions.csv"
    decision_fields = [
        "id", "repository", "commit", "pair_index", "dimension", "verdict", "reason",
        "circuit", "consumer", "function", "result",
    ]
    with decisions_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decision_rows)

    flags_path = output_dir / "dev-flag-adjudication.csv"
    flag_fields = decision_fields + ["builder_opinion", "builder_basis", "limitations"]
    with flags_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=flag_fields)
        writer.writeheader()
        for flag in flags:
            writer.writerow({
                **flag,
                "builder_opinion": "MISSING",
                "builder_basis": "MISSING",
                "limitations": "MISSING",
            })

    summary = {
        "schema": "bindcheck-zk.relational-dev-summary/v1",
        "source": {
            "raw_run": raw_run.relative_to(ROOT).as_posix(),
            "manifest": (raw_run / "manifest.json").relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256(raw_run / "manifest.json"),
            "raw_ledger": (raw_run / "per-row-ledger.json").relative_to(ROOT).as_posix(),
            "raw_ledger_sha256": sha256(raw_run / "per-row-ledger.json"),
            "git_revision": manifest["git_revision"],
            "analyzer_content_sha256": manifest["analyzer_content_sha256"],
        },
        "rows": len(ledger),
        "fatal_rows": sum(row["fatal_reason"] is not None for row in ledger),
        "compiled": {
            "rows": sum(row["compiled_relations"] > 0 for row in ledger),
            "relations": sum(row["compiled_relations"] for row in ledger),
        },
        "paired": {
            "rows": sum(row["paired_paths"] > 0 for row in ledger),
            "paths": sum(row["paired_paths"] for row in ledger),
        },
        "dimensions": {},
        "decisions": len(decision_rows),
        "flags": len(flags),
        "tracked_outputs": {
            "ledger": ledger_path.relative_to(ROOT).as_posix(),
            "decisions": decisions_path.relative_to(ROOT).as_posix(),
            "flag_adjudication": flags_path.relative_to(ROOT).as_posix(),
        },
    }
    for dimension in DIMENSIONS:
        findings = pair_findings[dimension]
        row_verdicts = collections.Counter(row["dimensions"][dimension]["verdict"] for row in ledger)
        row_applicability = collections.Counter(row["dimensions"][dimension]["applicability"] for row in ledger)
        summary["dimensions"][dimension] = {
            "row_verdicts": dict(sorted(row_verdicts.items())),
            "row_applicability": dict(sorted(row_applicability.items())),
            "pair_results": len(findings),
            "applicable_pair_results": sum(finding["applicability"] == "APPLICABLE" for finding in findings),
            "decided_pair_results": sum(
                finding["applicability"] == "APPLICABLE" and finding["verdict"] != "UNKNOWN"
                for finding in findings
            ),
            "violation_pair_results": sum(finding["verdict"] == "VIOLATION" for finding in findings),
        }
    summary_path = output_dir / "dev-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "summary": summary_path.relative_to(ROOT).as_posix(),
        "summary_sha256": sha256(summary_path),
        "ledger_sha256": sha256(ledger_path),
        "decisions_sha256": sha256(decisions_path),
        "flag_adjudication_sha256": sha256(flags_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
