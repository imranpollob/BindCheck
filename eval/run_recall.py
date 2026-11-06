#!/usr/bin/env python3
"""Run frozen vulnerable/fixed recall pairs once under the EVAL gates."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import shutil
import sys
from collections import Counter
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import (  # noqa: E402
    PATTERNS,
    RECALL_EXPECTATIONS,
    RECALL_LEDGER,
    ROOT,
    SOURCE_LEDGER,
    EvaluationError,
    GateError,
    analyzer_build_success,
    atomic_write_json,
    check_eval_gate,
    load_json,
    pattern_locations,
    read_csv,
    sha256_bytes,
    sha256_file,
    utc_now,
)
from eval.run_heldout import acquire_once, run_tool_once  # noqa: E402


def strict_resolved_rows(rows: list[dict[str, str]], split: str) -> list[dict[str, str]]:
    split = split.upper()
    if split == "EVAL":
        if any("split" in row for row in rows):
            rows = [row for row in rows if row.get("split", "EVAL") == "EVAL"]
        return [
            row for row in rows
            if row.get("v2_scope_class") == "integration"
            and row.get("v2_pair_status") == "vulnerable-and-fixed-resolved"
        ]
    if not rows or "split" not in rows[0]:
        raise EvaluationError("DEV recall tests require an explicit split column in a DEV fixture ledger")
    return [
        row for row in rows
        if row.get("split") == "DEV"
        and row.get("v2_pair_status") == "vulnerable-and-fixed-resolved"
    ]


def load_expectations(path: pathlib.Path, case_ids: set[str]) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_case: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = row.get("case_id", "")
        if not case_id or case_id in by_case:
            raise EvaluationError(f"missing or duplicate case_id in recall expectations: {case_id!r}")
        by_case[case_id] = row
    missing = sorted(case_ids - set(by_case))
    extras = sorted(set(by_case) - case_ids)
    if missing or extras:
        raise EvaluationError(f"recall expectation coverage differs; missing={missing}, extras={extras}")
    for case_id, row in by_case.items():
        if row.get("review_status") != "REVIEWED":
            raise EvaluationError(f"{case_id}: expectation is not REVIEWED")
        if row.get("expected_pattern") not in PATTERNS:
            raise EvaluationError(f"{case_id}: expected_pattern must be one of {PATTERNS}")
        expression = row.get("expected_location_regex", "")
        if not expression:
            raise EvaluationError(f"{case_id}: expected_location_regex is required")
        try:
            re.compile(expression)
        except re.error as exc:
            raise EvaluationError(f"{case_id}: invalid location regex: {exc}") from exc
    return by_case


def _max_pattern_grades(payload: Mapping[str, Any], pattern: str) -> list[str]:
    return sorted({
        str((triple.get("patterns") or {}).get(pattern, {}).get("evidence_grade", "E0"))
        for triple in payload.get("triples", []) or []
        if (triple.get("patterns") or {}).get(pattern, {}).get("verdict") == "VIOLATION"
    })


def score_pair(
    expected_pattern: str,
    expected_location_regex: str,
    vulnerable: Mapping[str, Any],
    fixed: Mapping[str, Any],
) -> dict[str, Any]:
    vulnerable_verdict = ((vulnerable.get("patterns") or {}).get(expected_pattern) or {}).get("verdict", "UNKNOWN")
    fixed_verdict = ((fixed.get("patterns") or {}).get(expected_pattern) or {}).get("verdict", "UNKNOWN")
    locations = pattern_locations(vulnerable, expected_pattern)
    matching_locations = [
        location for location in locations if re.search(expected_location_regex, location)
    ]
    grades = _max_pattern_grades(vulnerable, expected_pattern)
    return {
        "expected_pattern": expected_pattern,
        "expected_location_regex": expected_location_regex,
        "vulnerable_verdict": vulnerable_verdict,
        "fixed_verdict": fixed_verdict,
        "predicate_detected": vulnerable_verdict == "VIOLATION" and fixed_verdict != "VIOLATION",
        "vulnerable_violation_locations": locations,
        "matching_locations": matching_locations,
        "location_match": bool(matching_locations),
        "vulnerable_build_success": analyzer_build_success(vulnerable),
        "fixed_build_success": analyzer_build_success(fixed),
        "pair_build_success": analyzer_build_success(vulnerable) and analyzer_build_success(fixed),
        "vulnerable_violation_evidence_grades": grades,
        "e4": "E4" in grades,
    }


def run_revision(
    case: Mapping[str, str], revision_name: str, case_dir: pathlib.Path, work_root: pathlib.Path
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    commit = case[f"{revision_name}_commit"]
    revision_dir = case_dir / revision_name
    revision_dir.mkdir(parents=True, exist_ok=True)
    family = {
        "family_id": case["case_id"],
        "repository": case["repository"],
        "commit": commit,
        "sample_hash": sha256_bytes(f"{case['case_id']}|{revision_name}|{commit}".encode("utf-8")),
        "rank": 1,
        "stratum": "recall",
    }
    atomic_write_json(revision_dir / "revision.json", family)
    checkout = work_root / (revision_name + "-" + family["sample_hash"][:12])
    try:
        acquisition = acquire_once(family, revision_dir, checkout)
        if acquisition.get("status") != "ready":
            normalized = {
                "schema": "bindcheck-zk.eval-tool-result/v1",
                "tool": "bindcheck-zk",
                "verdict": "UNKNOWN",
                "reasons": ["ACQUISITION_FAILED"],
                "patterns": {},
            }
            atomic_write_json(revision_dir / "bindcheck-zk.json", normalized)
            return normalized, {"patterns": {}, "coverage": {}}
        normalized = run_tool_once("bindcheck-zk", checkout, revision_dir)
        raw_path = revision_dir / "bindcheck-zk-raw.json"
        payload = load_json(raw_path) if raw_path.exists() else {"patterns": {}, "coverage": {}}
        return normalized, payload
    finally:
        if checkout.exists():
            shutil.rmtree(checkout)


def run_case(
    case: Mapping[str, str], expectation: Mapping[str, str], output: pathlib.Path
) -> dict[str, Any]:
    case_hash = sha256_bytes(case["case_id"].encode("utf-8"))
    case_dir = output / "cases" / case_hash[:16]
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "case-result.json"
    if result_path.exists():
        return load_json(result_path)
    atomic_write_json(case_dir / "case.json", dict(case))
    work_root = output / "work" / case_hash[:16]
    work_root.mkdir(parents=True, exist_ok=True)
    vulnerable_normalized, vulnerable = run_revision(case, "vulnerable", case_dir, work_root)
    fixed_normalized, fixed = run_revision(case, "fixed", case_dir, work_root)
    score = score_pair(
        expectation["expected_pattern"], expectation["expected_location_regex"],
        vulnerable, fixed,
    )
    result = {
        "schema": "bindcheck-zk.recall-case/v1",
        "case_id": case["case_id"],
        "repository": case["repository"],
        "vulnerable_commit": case["vulnerable_commit"],
        "fixed_commit": case["fixed_commit"],
        "source_pattern": case.get("pattern"),
        "expectation": dict(expectation),
        "vulnerable_result": vulnerable_normalized,
        "fixed_result": fixed_normalized,
        "score": score,
        "completed_utc": utc_now(),
        "clones_deleted": not any(work_root.iterdir()),
    }
    atomic_write_json(result_path, result)
    if work_root.exists() and not any(work_root.iterdir()):
        work_root.rmdir()
    return result


def summarize_recall(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    denominator = len(results)
    predicate = sum(bool(item["score"]["predicate_detected"]) for item in results)
    build = sum(bool(item["score"]["pair_build_success"]) for item in results)
    locations = sum(bool(item["score"]["location_match"]) for item in results)
    e4 = sum(bool(item["score"]["e4"]) for item in results)
    return {
        "schema": "bindcheck-zk.recall-summary/v1",
        "cases": denominator,
        "predicate_recall": {"detected": predicate, "eligible": denominator, "rate": predicate / denominator if denominator else None},
        "build_recall": {"pairs_built": build, "eligible": denominator, "rate": build / denominator if denominator else None},
        "location_match": {"matched": locations, "eligible": denominator, "rate": locations / denominator if denominator else None},
        "e4": {"cases": e4, "eligible": denominator, "rate": e4 / denominator if denominator else None},
        "vulnerable_verdicts": dict(sorted(Counter(item["score"]["vulnerable_verdict"] for item in results).items())),
        "fixed_verdicts": dict(sorted(Counter(item["score"]["fixed_verdict"] for item in results).items())),
        "generated_utc": utc_now(),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--split", required=True, choices=("DEV", "EVAL"))
    result.add_argument("--ledger", type=pathlib.Path, default=RECALL_LEDGER)
    result.add_argument("--expectations", type=pathlib.Path, default=RECALL_EXPECTATIONS)
    result.add_argument("--source-ledger", type=pathlib.Path, default=SOURCE_LEDGER)
    result.add_argument("--output", type=pathlib.Path)
    result.add_argument("--preflight", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    split = args.split.upper()
    ledger = args.ledger.resolve()
    expectations_path = args.expectations.resolve()
    source_ledger = args.source_ledger.resolve()
    rows = strict_resolved_rows(read_csv(ledger), split)
    expectations = load_expectations(expectations_path, {row["case_id"] for row in rows})
    gate = None
    if split == "EVAL":
        try:
            gate = check_eval_gate(
                ROOT, source_ledger, recall_ledger=ledger,
                recall_expectations=expectations_path,
            )
        except GateError as exc:
            print(f"RECALL REFUSED: {exc}", file=sys.stderr)
            return 3
        if args.preflight:
            print(json.dumps(gate, indent=2, sort_keys=True))
            return 0
    output = (args.output or ROOT / "results" / "raw" / "T25" / f"recall-{sha256_file(ledger)[:12]}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "bindcheck-zk.recall-run/v1",
        "split": split,
        "started_utc": utc_now(),
        "ledger_sha256": sha256_file(ledger),
        "expectations_sha256": sha256_file(expectations_path),
        "source_ledger_sha256": sha256_file(source_ledger),
        "cases": [row["case_id"] for row in rows],
        "gate": gate,
        "no_retry_policy": "one fetch and one analyzer attempt per revision",
    }
    manifest_path = output / "run-manifest.json"
    if manifest_path.exists():
        existing = load_json(manifest_path)
        for key in ("ledger_sha256", "expectations_sha256", "source_ledger_sha256", "cases"):
            if existing.get(key) != manifest[key]:
                raise EvaluationError(f"existing recall run differs at {key}")
        manifest = existing
    else:
        atomic_write_json(manifest_path, manifest)
    results = []
    for index, case in enumerate(rows, 1):
        item = run_case(case, expectations[case["case_id"]], output)
        results.append(item)
        print(
            f"RECALL\t{index:02d}\tpredicate={item['score']['predicate_detected']}\t"
            f"build={item['score']['pair_build_success']}\t{case['case_id']}",
            flush=True,
        )
    summary = summarize_recall(results)
    atomic_write_json(output / "recall-summary.json", summary)
    manifest["completed_utc"] = utc_now()
    manifest["summary"] = summary
    atomic_write_json(manifest_path, manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
