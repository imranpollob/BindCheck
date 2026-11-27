#!/usr/bin/env python3
"""Validate the D2-02 exposed-development ecosystem inventory.

This script is deliberately read-only.  It checks the tracked ledger against
the already preserved D1/D2 evidence; it does not discover repositories, run
the analyzer, or write a new result namespace.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "protocols/d2/d2-02-ecosystem-inventory-v1.json"
EXPECTED_STATUSES = {
    "UNAVAILABLE",
    "INELIGIBLE",
    "BUILD_FAILED",
    "UNSUPPORTED",
    "ANALYZABLE",
}


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(ledger_path: Path = DEFAULT_LEDGER) -> list[str]:
    ledger_path = ledger_path.resolve()
    ledger = _load(ledger_path)
    checks: list[str] = []

    _require(
        ledger.get("schema") == "bindcheck.d2.ecosystem-inventory/v1",
        "unexpected inventory schema",
    )
    _require(ledger.get("research_verdict") == "UNKNOWN", "verdict must remain UNKNOWN")
    taxonomy = ledger.get("compatibility_status_taxonomy", {})
    _require(set(taxonomy) == EXPECTED_STATUSES, "compatibility taxonomy is incomplete")
    checks.append("schema-and-status-taxonomy")

    population = ledger["eligible_population"]
    candidates = population["candidates"]
    _require(len(candidates) == population["candidate_revision_count"], "candidate count mismatch")
    observed_statuses = Counter(candidate["compatibility_status"] for candidate in candidates)
    for status in EXPECTED_STATUSES:
        _require(
            observed_statuses[status] == population["status_counts"][status],
            f"population status mismatch for {status}",
        )
    repositories = {candidate["repository"] for candidate in candidates}
    lineages = {candidate["family_lineage"]["id"] for candidate in candidates}
    revisions = [candidate["revision"] for candidate in candidates]
    _require(len(repositories) == population["unique_repository_count"] == 2, "repository count mismatch")
    _require(len(lineages) == population["architectural_lineage_count"] == 2, "lineage count mismatch")
    _require(len(revisions) == len(set(revisions)) == 3, "candidate revisions must be unique")
    _require(
        Counter(candidate["family_lineage"]["id"] for candidate in candidates)
        == Counter(
            {
                "lineage-warptoad-withdraw-mint": 1,
                "lineage-payy-agg-agg-final-rollupv1": 2,
            }
        ),
        "candidate lineage split mismatch",
    )
    checks.append("eligible-population-counts")

    sources = ledger["audit_sources"]
    source_paths = [record["path"] for record in sources]
    _require(len(source_paths) == len(set(source_paths)), "duplicate audit source path")
    for record in sources:
        path = ROOT / record["path"]
        _require(path.is_file() and not path.is_symlink(), f"audit source missing: {record['path']}")
        _require(_sha256(path) == record["sha256"], f"audit source hash mismatch: {record['path']}")
    checks.append(f"audit-source-hashes:{len(sources)}")

    collections = {record["id"]: record for record in ledger["development_case_collections"]}
    mutant_collection = collections["d2-01-current-binding-mutants"]
    benchmark = _load(ROOT / "results/raw/D2-01-recovery-01/integrated/benchmark-results.json")
    targets = benchmark["targets"]
    _require(len(targets) == mutant_collection["total"] == 30, "mutant total mismatch")
    family_counts = Counter(target["family"] for target in targets)
    _require(family_counts == Counter({"WarpToad": 18, "Payy": 12}), "mutant family split mismatch")
    classification_counts = Counter(target["classification"] for target in targets)
    _require(classification_counts == Counter({"DETECTED": 17, "UNSUPPORTED": 13}), "mutant outcome mismatch")
    _require(benchmark["counts"]["misses"] == 0, "mutant misses changed")
    reason_counts = Counter(
        reason
        for target in targets
        if target["classification"] == "UNSUPPORTED"
        for reason in target.get("support_reasons", [])
    )
    _require(
        reason_counts == Counter(mutant_collection["first_stop_reasons"]),
        "unsupported reason distribution mismatch",
    )
    unsupported_ids = {target["target"] for target in targets if target["classification"] == "UNSUPPORTED"}
    _require("WT-S04" in unsupported_ids, "WT-S04 must remain unsupported")
    _require(len({case for case in unsupported_ids if case.startswith("PY-")}) == 12, "Payy unsupported set mismatch")
    checks.append("current-mutant-ledger")

    payy = _load(ROOT / "results/raw/D2-01-recovery-01/integrated/payy-results.json")
    payy_targets = payy["targets"]
    _require(len(payy_targets) == collections["d2-01-exact-payy-pair"]["total"] == 2, "Payy pair count mismatch")
    _require(all(target["matches_expected"] for target in payy_targets), "Payy R-EXTENT outcome mismatch")
    _require(
        {target["revision"]: target["observed_r_extent"] for target in payy_targets}
        == {"earlier": True, "check-added": False},
        "Payy revision outcome vector mismatch",
    )
    checks.append("exact-payy-pair")

    synthetic = _load(ROOT / "results/raw/D2-01-recovery-01/d1p42-rerun/synthetic-results.json")
    synthetic_record = collections["d1p42-authored-synthetic-extent-controls"]
    _require(len(synthetic["pairs"]) == synthetic_record["analysis_pairs"] == 3, "synthetic pair count mismatch")
    _require(
        len(synthetic["execution_controls"]) == synthetic_record["execution_controls"] == 6,
        "synthetic execution-control count mismatch",
    )
    _require(
        all(case["expected_exit"] == case["observed_exit"] for case in synthetic["execution_controls"]),
        "synthetic execution control changed",
    )
    checks.append("synthetic-control-counts")

    historical = ledger["historical_transfer_reconciliation"]
    attempts = historical["attempt_counts"]
    _require(attempts["analysis_attempts"] == 12, "historical attempt count mismatch")
    _require(attempts["unique_projects"] == 8, "historical unique-project count mismatch")
    _require(attempts["repeat_attempts"] == 4, "historical repeat count mismatch")
    _require(attempts["unsupported_attempts"] == 12, "historical unsupported count mismatch")
    _require(attempts["adjudicated_independent_family_count"] is None, "historical family count must be null")
    scans = historical["scan_records"]
    _require(sum(scan["analysis_attempts"] for scan in scans) == 12, "scan attempt sum mismatch")
    combined = Counter()
    for scan in scans:
        combined.update(scan["blocker_occurrences"])
        _require(
            sum(scan["blocker_occurrences"].values()) == scan["unsupported_attempts"],
            f"blocker count mismatch in {scan['report']}",
        )
    recorded_combined = Counter(
        {
            category: count
            for category, count in historical["combined_attempt_occurrences"].items()
            if category not in {"total", "interpretation"}
        }
    )
    _require(combined == recorded_combined, "combined historical blocker distribution mismatch")
    _require(sum(combined.values()) == historical["combined_attempt_occurrences"]["total"] == 12, "combined blocker total mismatch")
    latest = historical["latest_unique_project_distribution"]
    _require(sum(row["affected_unique_projects"] for row in latest) == 8, "latest unique-project distribution mismatch")
    _require(all(row["affected_families"] is None for row in latest), "historical family counts must remain null")
    checks.append("historical-attempt-vs-project-reconciliation")

    ranking = ledger["blocker_distribution_and_ranking"]["current_development_ranking"]
    _require([row["rank"] for row in ranking] == [1, 2], "development ranking must be contiguous")
    _require(ranking[0]["affected_architectural_lineages"] == 2, "consumer blocker lineage count mismatch")
    _require(ranking[0]["affected_target_variants"] == 13, "consumer blocker target count mismatch")
    _require(ranking[1]["affected_architectural_lineages"] == 1, "mapping blocker lineage count mismatch")
    _require(ranking[1]["affected_target_variants"] == 12, "mapping blocker target count mismatch")
    _require(ranking[1]["first_stop_reason"] is None, "nested mapping contributor must not become a first-stop result")
    checks.append("family-ranked-development-blockers")

    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", nargs="?", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(argv)
    try:
        checks = validate(args.ledger)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema": "bindcheck.d2.ecosystem-inventory-validation/v1",
                    "status": "FAIL",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "schema": "bindcheck.d2.ecosystem-inventory-validation/v1",
                "status": "PASS",
                "ledger": args.ledger.resolve().relative_to(ROOT).as_posix(),
                "checks": checks,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
