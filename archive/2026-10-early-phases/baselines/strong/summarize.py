#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
from typing import Any

from .common import sha256_file, write_json


def load_results(campaign: pathlib.Path) -> dict[str, dict[str, dict[str, Any]]]:
    output: dict[str, dict[str, dict[str, Any]]] = {arm: {} for arm in ("A", "B", "C")}
    for arm in output:
        manifest = json.loads((campaign / f"arm-{arm}-manifest.json").read_text(encoding="utf-8"))
        for record in manifest["records"]:
            path = campaign / "cases" / record["id"] / f"{arm}.json"
            if sha256_file(path) != record["result_sha256"]:
                raise ValueError(f"manifest hash mismatch: {path}")
            output[arm][record["id"]] = json.loads(path.read_text(encoding="utf-8"))
    return output


def summarize_counts(results: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm, rows in results.items():
        verdicts = collections.Counter(row["result"]["verdict"] for row in rows.values())
        statuses = collections.Counter(row["run"]["status"] for row in rows.values())
        failures = collections.Counter(row["run"].get("fatal_reason") or "NONE" for row in rows.values())
        codes = collections.Counter(
            item["code"]
            for row in rows.values()
            for item in row["result"]["findings"]
        )
        summary[arm] = {
            "rows": len(rows),
            "verdicts": dict(sorted(verdicts.items())),
            "run_statuses": dict(sorted(statuses.items())),
            "fatal_reasons": dict(sorted(failures.items())),
            "finding_instances_by_code": dict(sorted(codes.items())),
            "rows_with_findings": sum(bool(row["result"]["findings"]) for row in rows.values()),
        }
        if arm == "B":
            native_codes = collections.Counter(
                item["code"]
                for row in rows.values()
                for item in row.get("native", {}).get("signals", [])
            )
            tool_status = collections.defaultdict(collections.Counter)
            for row in rows.values():
                for tool, detail in row.get("native", {}).get("tools", {}).items():
                    tool_status[tool][detail.get("status", "MISSING")] += 1
            summary[arm]["native_signal_instances_by_code"] = dict(sorted(native_codes.items()))
            summary[arm]["tool_statuses"] = {
                tool: dict(sorted(counter.items())) for tool, counter in sorted(tool_status.items())
            }
    return summary


def score_synthetic(campaign: pathlib.Path, results: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    expected_path = pathlib.Path(__file__).resolve().parents[2] / "redteam" / "adversarial" / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for case in expected["cases"]:
        case_id = case["id"]
        for arm in ("A", "B", "C"):
            observed = results[arm][case_id]
            expected_arm = case["expected"][arm]
            observed_codes = sorted(item["code"] for item in observed["result"]["findings"])
            native_codes = sorted(item["code"] for item in observed.get("native", {}).get("signals", []))
            required_codes = sorted(expected_arm.get("findings", []))
            required_native = sorted(expected_arm.get("native_signals", []))
            rows.append({
                "id": case_id,
                "label": case["label"],
                "family": case["family"],
                "arm": arm,
                "expected_verdict": expected_arm["verdict"],
                "observed_verdict": observed["result"]["verdict"],
                "verdict_match": expected_arm["verdict"] == observed["result"]["verdict"],
                "required_finding_codes": required_codes,
                "observed_finding_codes": observed_codes,
                "required_findings_present": set(required_codes).issubset(observed_codes),
                "required_native_signals": required_native,
                "observed_native_signals": native_codes,
                "required_native_signals_present": set(required_native).issubset(native_codes),
                "expected_false_alarm": expected_arm.get("expected_false_alarm", False),
                "run_status": observed["run"]["status"],
                "fatal_reason": observed["run"].get("fatal_reason"),
            })
    csv_path = campaign / "synthetic-score.csv"
    fields = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    by_arm: dict[str, Any] = {}
    for arm in ("A", "B", "C"):
        selected = [row for row in rows if row["arm"] == arm]
        by_arm[arm] = {
            "rows": len(selected),
            "verdict_matches": sum(row["verdict_match"] for row in selected),
            "required_findings_present": sum(row["required_findings_present"] for row in selected),
            "required_native_signals_present": sum(row["required_native_signals_present"] for row in selected),
            "vulnerable_rows_reported_violation": sum(
                row["label"] == "VULNERABLE" and row["observed_verdict"] == "VIOLATION" for row in selected
            ),
            "legitimate_rows_reported_violation": sum(
                row["label"] == "LEGITIMATE" and row["observed_verdict"] == "VIOLATION" for row in selected
            ),
            "unknown_rows": sum(row["observed_verdict"] == "UNKNOWN" for row in selected),
            "noncompleted_rows": sum(row["run_status"] != "completed" for row in selected),
        }
    score = {
        "schema": "bindcheck-redteam.synthetic-score/v1",
        "expected_sha256": sha256_file(expected_path),
        "rows": len(rows),
        "cases": len(expected["cases"]),
        "by_arm": by_arm,
        "detail_csv": csv_path.name,
        "detail_csv_sha256": sha256_file(csv_path),
    }
    write_json(campaign / "synthetic-score.json", score)
    return score


def write_adjudication_template(campaign: pathlib.Path, results: dict[str, dict[str, dict[str, Any]]]) -> pathlib.Path:
    rows: list[dict[str, Any]] = []
    for arm in ("A", "C"):
        for case_id, result in sorted(results[arm].items()):
            for item in result["result"]["findings"]:
                rows.append({
                    "id": case_id,
                    "arm": arm,
                    "code": item["code"],
                    "path": (item.get("location") or {}).get("path"),
                    "line": (item.get("location") or {}).get("line"),
                    "source_excerpt": item.get("facts", {}).get("source_excerpt"),
                    "author_opinion": "UNREVIEWED",
                    "human_review_required": "true",
                    "reason": "",
                })
    path = campaign / "finding-adjudication.csv"
    fields = ["id", "arm", "code", "path", "line", "source_excerpt", "author_opinion", "human_review_required", "reason"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=pathlib.Path)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    campaign = args.campaign.resolve()
    results = load_results(campaign)
    summary = {
        "schema": "bindcheck-redteam.campaign-summary/v1",
        "campaign": json.loads((campaign / "campaign.json").read_text(encoding="utf-8"))["campaign"],
        "counts": summarize_counts(results),
    }
    adjudication = write_adjudication_template(campaign, results)
    summary["adjudication_template"] = adjudication.name
    summary["adjudication_template_sha256"] = sha256_file(adjudication)
    if args.synthetic:
        summary["synthetic_score"] = score_synthetic(campaign, results)
    write_json(campaign / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
