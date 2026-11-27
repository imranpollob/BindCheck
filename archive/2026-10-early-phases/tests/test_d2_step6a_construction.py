from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols/d2/d2-06a-construction-v1.json"
RAW = ROOT / "results/raw/D2-06A/construction-03"
ARMS = (
    "producer-only",
    "consumer-only",
    "unjoined-union",
    "basic-structural-composition",
    "strong-simple-composition",
    "full-bindcheck",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class D2Step6AConstructionTest(unittest.TestCase):
    def test_protocol_is_unscored_and_binds_its_runner(self) -> None:
        protocol = load(PROTOCOL)
        self.assertEqual(protocol["status"], "FROZEN_FOR_UNSCORED_CONSTRUCTION")
        self.assertEqual(protocol["research_verdict"], "UNKNOWN")
        self.assertEqual(
            tuple(protocol["baseline_construction"]["required_arms"]), ARMS
        )
        self.assertEqual(protocol["baseline_construction"]["planned_case_arms"], 78)
        runner = protocol["implementation"]["runner"]
        self.assertEqual(sha256(ROOT / runner["path"]), runner["sha256"])
        self.assertFalse(protocol["implementation"]["analyzer_changed"])
        self.assertEqual(protocol["resource_budget"]["proof_calls"], 0)
        self.assertEqual(protocol["resource_budget"]["network_calls"], 0)

    def test_final_run_is_construction_only_and_hash_complete(self) -> None:
        summary = load(RAW / "run-summary.json")
        manifest = load(RAW / "run-manifest.json")
        self.assertEqual(summary["status"], "COMPLETE_CONSTRUCTION_SMOKE_ONLY")
        self.assertFalse(summary["scored"])
        self.assertEqual(summary["research_verdict"], "UNKNOWN")
        self.assertEqual(summary["equal_policy_information"],
                         "UNRESOLVED_EQUAL_POLICY_INTERFACE")
        self.assertEqual(manifest["protocol"]["sha256"], sha256(PROTOCOL))
        self.assertFalse(manifest["scored"])
        self.assertEqual(manifest["cost_accounting"]["proof_calls"], 0)
        self.assertEqual(manifest["cost_accounting"]["network_calls"], 0)
        self.assertLessEqual(
            manifest["cost_accounting"]["subprocess_call_count"],
            manifest["resource_budget"]["external_compiler_or_execution_calls"],
        )
        for name, record in summary["outputs"].items():
            path = RAW / record["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256(path), record["sha256"], name)
            self.assertEqual(path.stat().st_size, record["size_bytes"], name)

    def test_all_case_arm_appearances_are_retained_without_scoring(self) -> None:
        baseline = load(RAW / "baseline-smoke-summary.json")
        self.assertEqual(baseline["case_appearances"], 13)
        self.assertEqual(baseline["arm_count"], 6)
        self.assertEqual(baseline["planned_case_arms"], 78)
        self.assertEqual(len(baseline["rows"]), 78)
        self.assertEqual(
            baseline["construction_status_counts"], {"SUPPORTED": 72, "UNKNOWN": 6}
        )
        pairs = Counter((row["case_id"], row["arm"]) for row in baseline["rows"])
        self.assertEqual(len({case_id for case_id, _ in pairs}), 13)
        self.assertEqual(set(arm for _, arm in pairs), set(ARMS))
        self.assertTrue(all(count == 1 for count in pairs.values()))
        self.assertTrue(all(row["scored"] is False for row in baseline["rows"]))
        self.assertTrue(
            all(row["policy_review_status"] == "NOT_SUPPLIED"
                for row in baseline["rows"])
        )

    def test_union_is_exact_and_unknown_is_not_coerced(self) -> None:
        audit = load(RAW / "union-audit.json")
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["examples"], 9)
        self.assertEqual(audit["supported_examples"], 8)
        self.assertEqual(audit["unknown_examples"], 1)
        self.assertTrue(all(row["matches"] for row in audit["rows"]))
        self.assertEqual(
            [row["id"] for row in audit["rows"] if row["status"] == "UNKNOWN"],
            ["E8"],
        )

    def test_transformation_controls_and_rejections_are_both_retained(self) -> None:
        ledger = load(RAW / "transformation-ledger.json")
        self.assertEqual(ledger["planned_count"], 6)
        self.assertEqual(ledger["attempted_count"], 4)
        self.assertEqual(ledger["semantically_controlled_count"], 4)
        self.assertEqual(ledger["stability_eligible_count"], 4)
        self.assertEqual(ledger["preconstruction_rejected_count"], 2)
        attempted = [row for row in ledger["rows"] if row["attempted"]]
        rejected = [row for row in ledger["rows"] if not row["attempted"]]
        for row in attempted:
            self.assertEqual(row["status"], "SEMANTICALLY_CONTROLLED")
            self.assertTrue(row["accepted_for_transformation_stability"])
            self.assertTrue(all(row["semantic_identity_stability"].values()))
            self.assertEqual(set(row["semantic_identity_stability"]), set(ARMS))
            self.assertEqual(row["control_summary"]["formal_equivalence_proof"],
                             "NOT_ESTABLISHED")
        for row in rejected:
            self.assertEqual(row["status"], "REJECTED_PRECONSTRUCTION")
            self.assertTrue(row["reason"])

    def test_information_parity_blocker_remains_explicit(self) -> None:
        matrix = load(RAW / "information-budget-matrix.json")
        self.assertEqual(matrix["status"], "UNRESOLVED_EQUAL_POLICY_INTERFACE")
        self.assertFalse(matrix["scored_comparison_allowed"])
        self.assertTrue(matrix["strong_vs_full_shared_implementation_facts"])
        self.assertFalse(matrix["strong_vs_full_equal_reviewed_policy_consumption"])
        by_arm = {row["arm"]: row for row in matrix["rows"]}
        self.assertEqual(set(by_arm), set(ARMS))
        self.assertEqual(by_arm["strong-simple-composition"]["reviewed_policy"],
                         "INTERFACE_SUPPORTED_BUT_NOT_SUPPLIED")
        self.assertEqual(by_arm["full-bindcheck"]["reviewed_policy"],
                         "RECORDED_NOT_CONSUMED")


if __name__ == "__main__":
    unittest.main()
