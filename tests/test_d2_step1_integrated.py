"""Controls for the D2-01 result reconciliation runner."""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from scripts import d2_step1_integrated as D2
from scripts import d1p_43_role_ablation_preliminary as D1P43


class D2Step1Tests(unittest.TestCase):
    def test_association_requires_rule_kind_and_complete_boundary_index_set(self) -> None:
        association = {
            "rule": "R-ROLE",
            "kinds": ["state-identity"],
            "public_indices": [3, 4],
        }
        one_of_two = {
            "rule": "R-ROLE",
            "evidence": {"kind": "state-identity", "public_index": 4},
        }
        other = {
            "rule": "R-ROLE",
            "evidence": {"kind": "state-identity", "public_index": 3},
        }
        self.assertFalse(D2.association_satisfied([one_of_two], association))
        self.assertTrue(D2.association_satisfied([one_of_two, other], association))
        self.assertFalse(D2.association_satisfied([one_of_two, {
            **other, "evidence": {"kind": "polarity", "public_index": 3},
        }], association))

    def test_case_table_has_required_fields_and_separate_datasets(self) -> None:
        integrated = {"targets": [{
            "target": "WT-C01",
            "family": "WarpToad",
            "binding_broken": "nullifier",
            "expected_effect": "arbitrary-nullifier mint",
            "classification": "DETECTED",
            "all_required_associations_satisfied": True,
            "expected_associations": [{"rule": "R-BIND"}],
            "matched_warning_ids": ["W001"],
            "matched_stable_ids": ["BC-1"],
            "analysis": {"path": "results/raw/D2-01/integrated/WT-C01.json"},
        }]}
        ablation = {
            "schema": "test-ablation",
            "_result_path": str(D2.ROOT / "results/raw/D2-01/d1p43.json"),
            "ablation_examples": [{
                "id": "E1", "target": "WT-C01", "clean_control": False,
                "intended_policy": "policy", "expected_outcome_before_arms": "warning",
                "arms": {"full-bindcheck": {"support_gate": None, "score": {
                    "status": "SUPPORTED", "detection": True,
                    "related_warning_ids": ["W001"], "irrelevant_warning_ids": [],
                }}},
            }],
            "role_targets": [{
                "id": "R1", "target": "WT-C05", "status": "SUPPORTED",
                "intended_policy": "policy", "expected_outcome_before_run": "role warning",
                "matching_warning_count": 1, "expected_kinds": ["state-identity"],
                "matches_expected_outcome": True,
                "expected_public_indices": [4], "warnings": [{
                    "id": "ROLE001", "rule": "R-ROLE",
                    "evidence": {"kind": "state-identity", "public_index": 4},
                }], "support_gate": None,
            }],
        }
        payy = [{
            "revision": "earlier", "observed_r_extent": True,
            "r_extent_ids": ["W001"], "r_extent_stable_ids": ["BC-2"],
            "all_warning_rules": ["R-EXTENT"],
            "all_warning_ids": ["W001"], "all_stable_ids": ["BC-2"],
            "other_warnings": [],
            "analysis": {"path": "results/raw/D2-01/integrated/payy-earlier.json"},
        }]
        rows = D2.case_table(
            integrated_benchmark=integrated, ablation=ablation, payy=payy,
        )
        self.assertEqual(
            {row["dataset"] for row in rows},
            {"mutant-benchmark-current", "d1p41-discriminating-rerun",
             "d1p43-role-target-rerun", "payy-extent-pair"},
        )
        required = {
            "case", "family", "exposure", "version", "policy", "expected_defect",
            "outcome", "warning_association", "evidence_grade", "raw_output_path",
        }
        self.assertTrue(all(required.issubset(row) for row in rows))

    def test_protocol_keeps_versioned_datasets_separate(self) -> None:
        protocol = json.loads(D2.PROTOCOL.read_text())
        self.assertEqual(
            [item["id"] for item in protocol["datasets"]],
            ["mutant-benchmark-current", "d1p41-discriminating-rerun",
             "d1p43-role-target-rerun", "payy-extent-pair"],
        )
        self.assertEqual(protocol["resource_budget"]["solver_calls"], 0)
        self.assertEqual(protocol["resource_budget"]["proof_calls"], 0)
        self.assertIsNone(protocol["resource_budget"]["memory_mib"])
        self.assertEqual(
            protocol["components"]["benchmark_associations"],
            "protocols/d2/d2-01-benchmark-associations-v1.json",
        )

    def test_frozen_association_ledger_covers_manifest_exactly(self) -> None:
        ledger = json.loads(D2.ASSOCIATIONS.read_text())
        manifest = json.loads(D2.BENCHMARK_MANIFEST.read_text())
        self.assertEqual(set(ledger["targets"]), set(manifest["mutants"]))
        self.assertEqual(
            sum(item["expected_outcome"] == "DETECTED"
                for item in ledger["targets"].values()),
            17,
        )

    def test_d1p43_scoring_requires_union_to_cover_all_expected_indices(self) -> None:
        example = {
            "clean_control": False,
            "expected_boundary": {
                "rules": ["R-ROLE"],
                "public_indices": [3, 4],
            },
        }
        warnings = [{
            "id": "ROLE001", "rule": "R-ROLE",
            "evidence": {"kind": "state-identity", "public_index": 4},
        }]
        partial = D1P43.score_arm(
            warnings, example, "state-identity",
            status="SUPPORTED", expected_unknown=False,
        )
        self.assertFalse(partial["detection"])
        warnings.append({
            "id": "ROLE002", "rule": "R-ROLE",
            "evidence": {"kind": "state-identity", "public_index": 3},
        })
        complete = D1P43.score_arm(
            warnings, example, "state-identity",
            status="SUPPORTED", expected_unknown=False,
        )
        self.assertTrue(complete["detection"])
        self.assertEqual(complete["related_warning_count"], 2)

    def test_environment_path_override_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {"BINDCHECK_PAYY_ROOT": "/tmp/not-the-frozen-payy-root"},
            clear=False,
        ):
            result = D2.verify_environment_paths()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["mismatches"][0]["variable"], "BINDCHECK_PAYY_ROOT")


if __name__ == "__main__":
    unittest.main()
