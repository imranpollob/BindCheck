#!/usr/bin/env python3
"""Recount EVAL stratum populations two ways and compare with EVAL-SAMPLE-PLAN-v2.md.

(a) canonical-row label: v2_maturity of the single in-scope EVAL row per family;
(b) sampler rule (eval/common.py:143-150): strongest v2_maturity over all rows
    of the family (including dup rows), excluding families that also have a DEV row.

Also recounts the reviews' "audited-production rows with 0 stars" claim and the
recall-set counting rules. Writes reports/groundtruth/recounts.json.

Usage: python3 -I reports/groundtruth/scripts/strata_recount.py
"""
from __future__ import annotations

import csv
import json
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
STRATA = ["verified-deployed", "deployed-address-in-docs", "audited-production", "hackathon-student", "unclassified"]
PLAN_STATED = {"audited-production": 207, "deployed-address-in-docs": 303, "hackathon-student": 81, "unclassified": 755, "verified-deployed": 38}


def main() -> int:
    with (ROOT / "dataset/source-corpus-v2.csv").open(newline="") as h:
        rows = list(csv.DictReader(h))
    by_family = defaultdict(list)
    for r in rows:
        by_family[r["v2_family_id"]].append(r)
    dev_families = {r["v2_family_id"] for r in rows if r["split"] == "DEV"}
    canonical = [r for r in rows if r["split"] == "EVAL" and r["v2_disposition"] == "in-scope" and r["v2_family_id"] not in dev_families]
    a = Counter(r["v2_maturity"] for r in canonical)
    rank = {s: i for i, s in enumerate(STRATA)}
    b = Counter(min({m["v2_maturity"] for m in by_family[r["v2_family_id"]]}, key=rank.__getitem__) for r in canonical)
    aud = [r for r in canonical if r["v2_maturity"] == "audited-production"]

    with (ROOT / "dataset/recall-set-v2.csv").open(newline="") as h:
        recall = list(csv.DictReader(h))
    v1 = [r for r in recall if r["scope_class"] == "integration"]
    v2 = [r for r in recall if r["v2_scope_class"] == "integration"]
    resolved = "vulnerable-and-fixed-resolved"
    out = {
        "generated_by": "reports/groundtruth/scripts/strata_recount.py",
        "eligible_eval_families": len(canonical),
        "strata_canonical_row_label": dict(a),
        "strata_sampler_rule_family_strongest": dict(b),
        "strata_stated_in_EVAL-SAMPLE-PLAN-v2": PLAN_STATED,
        "canonical_equals_plan": dict(a) == PLAN_STATED,
        "sampler_equals_plan": dict(b) == PLAN_STATED,
        "audited_production_canonical_rows": len(aud),
        "audited_production_canonical_rows_stars_0": sum(1 for r in aud if r["stars"] == "0"),
        "recall_cases": len(recall),
        "recall_v1_scope_class_integration": len(v1),
        "recall_v2_scope_class_integration": len(v2),
        "recall_promoted_v1_broader_to_v2_strict": sum(1 for r in recall if r["v2_scope_class"] == "integration" and r["scope_class"] != "integration"),
        "recall_v2_strict_resolved_pairs": sum(1 for r in v2 if r["v2_pair_status"] == resolved),
        "recall_v1_strict_resolved_pairs": sum(1 for r in v1 if r["v2_pair_status"] == resolved),
        "recall_all_resolved_pairs": sum(1 for r in recall if r["v2_pair_status"] == resolved),
        "recall_expectations_rows": sum(1 for _ in csv.DictReader((ROOT / "eval/recall-expectations.csv").open(newline=""))),
    }
    (ROOT / "reports/groundtruth/recounts.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
