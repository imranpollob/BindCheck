from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/d2_step7_gate_a.py"
SPEC = importlib.util.spec_from_file_location("d2_step7_gate_a", MODULE_PATH)
assert SPEC and SPEC.loader
D2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2)


class D2Step7GateATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = D2.read_json(D2.DEFAULT_PROTOCOL)
        cls.sources = D2.load_sources(ROOT)

    def test_known_answer_is_inconclusive_with_zero_scored_arms(self) -> None:
        result = D2.assess_readiness(self.protocol, self.sources)
        self.assertEqual(result["status"], "BLOCKED_BEFORE_SCORE")
        self.assertEqual(result["gate_a_decision"], "INCONCLUSIVE")
        self.assertEqual(result["research_verdict"], "UNKNOWN")
        self.assertFalse(result["scored_execution_authorized"])
        self.assertEqual(result["scored_arm_count"], 0)
        self.assertEqual(result["objective_subset"], [])
        self.assertEqual(result["candidate_case_count"], 13)
        self.assertEqual(set(result["blocker_codes"]), D2.EXPECTED_BLOCKERS)
        self.assertEqual(
            set(result["row_local_unresolved_codes"]),
            D2.EXPECTED_ROW_LOCAL_UNRESOLVED,
        )
        self.assertNotIn(
            "TRANSFORMATION_PROOF_CONTROLS_INCOMPLETE",
            result["blocker_codes"],
        )
        self.assertTrue(
            all(
                set(group["reason_codes"]) == D2.EXPECTED_BLOCKERS
                for group in self.protocol["case_and_target_dispositions"]
            )
        )

    def test_missing_machine_blocker_fails_closed(self) -> None:
        sources = copy.deepcopy(self.sources)
        sources["information"]["strong_vs_full_equal_reviewed_policy_consumption"] = True
        with self.assertRaisesRegex(ValueError, "evidence blocker set mismatch"):
            D2.assess_readiness(self.protocol, sources)

    def test_bounded_transforms_cannot_be_upgraded_to_formal_proof(self) -> None:
        sources = copy.deepcopy(self.sources)
        first = next(
            row for row in sources["transformations"]["rows"] if row.get("attempted")
        )
        first["control_summary"]["formal_equivalence_proof"] = "ESTABLISHED"
        with self.assertRaisesRegex(ValueError, "must not upgrade"):
            D2.assess_readiness(self.protocol, sources)

    def test_protocol_binds_inputs_forms_and_prototype_budget(self) -> None:
        bound = D2.verify_bound_files(
            ROOT, self.protocol["controlling_artifact_bindings"]
        )
        forms = D2.verify_bound_files(ROOT, self.protocol["forms"])
        self.assertEqual(len(bound), 13)
        self.assertEqual(len(forms), 4)
        self.assertEqual(
            self.protocol["prospective_missing_mechanism_prototype"]["budget"],
            {"researcher_days": 2, "machine_hours": 8},
        )
        self.assertFalse(
            self.protocol["prospective_missing_mechanism_prototype"][
                "implemented_in_step_7"
            ]
        )
        recommendation = self.protocol["scope_recommendation"]
        self.assertEqual(recommendation["decision"], "BOUNDED_PROTOTYPE")
        self.assertEqual(
            recommendation["mechanical_fixture_phase"]["required_label"],
            "UNREVIEWED_DEVELOPMENT_FIXTURE",
        )
        self.assertEqual(
            recommendation["primary_discriminating_experiment"]["status"],
            "BLOCKED_PENDING_HUMAN_POLICY_ROLES",
        )
        self.assertFalse(recommendation["reserved_data_authorized"])
        self.assertFalse(recommendation["retroactive_gate_a_rescore_authorized"])

    def test_packet_inventory_is_complete_and_hashes_are_real(self) -> None:
        readiness = D2.assess_readiness(self.protocol, self.sources)
        packet = D2.build_packet_manifest(
            root=ROOT,
            protocol_path=D2.DEFAULT_PROTOCOL,
            protocol=self.protocol,
            readiness=readiness,
            sources=self.sources,
            created_at="2026-11-02T00:00:00+00:00",
        )
        self.assertEqual(len(packet["case_and_target_inventory"]), 13)
        self.assertTrue(
            all(row["status"] == "UNRESOLVED" for row in packet["case_and_target_inventory"])
        )
        self.assertTrue(
            all(row["semantic_target"] for row in packet["case_and_target_inventory"])
        )
        self.assertTrue(
            all(
                row["construction_source"]["sha256"]
                for row in packet["case_and_target_inventory"]
            )
        )
        self.assertTrue(
            all(
                row["construction_policy_record"]["policy_author"] is None
                and row["construction_policy_record"]["policy_reviewer"] is None
                for row in packet["case_and_target_inventory"]
            )
        )
        self.assertEqual(len(packet["arm_inventory"]["internal"]), 6)
        self.assertEqual(len(packet["arm_inventory"]["external"]), 11)
        self.assertEqual(len(packet["form_inventory"]), 4)
        self.assertEqual(len(packet["runner_inventory"]), 4)
        by_path = {row["path"]: row for row in packet["artifact_inventory"]}
        for required in (
            "results/raw/D2-06A/construction-01/run-summary.json",
            "results/raw/D2-06A/construction-02/run-summary.json",
            "results/raw/D2-06A/construction-03/run-summary.json",
            "results/raw/D2-06B/smoke-summary.json",
            "results/raw/D2-06B/recovery-01/smoke-summary.json",
            "scripts/d2_step7_gate_a.py",
            "tests/test_d2_step7_gate_a.py",
            "reports/D2-07.md",
            "results/raw/D2-07/content-seal-v1.json",
        ):
            self.assertIn(required, by_path)
            self.assertEqual(
                by_path[required]["sha256"], D2.sha256(ROOT / required), required
            )

    def test_finalizer_seals_and_verifies_without_scores_or_overwrite(self) -> None:
        raw_parent = ROOT / "results/raw"
        with tempfile.TemporaryDirectory(dir=raw_parent) as temporary:
            out = Path(temporary) / "D2-07-test"
            summary = D2.finalize(
                root=ROOT, protocol_path=D2.DEFAULT_PROTOCOL, out=out
            )
            self.assertFalse(summary["scored_execution"])
            self.assertEqual(summary["score_rows"], [])
            self.assertEqual(summary["outcome_counts"]["DETECTED"], 0)
            self.assertEqual(summary["outcome_counts"]["MISSED"], 0)
            verification = json.loads((out / "seal-verification.json").read_text())
            self.assertEqual(verification["status"], "PASS")
            self.assertEqual(
                verification["packet_to_seal_consistency"]["status"], "PASS"
            )
            self.assertEqual(
                verification["packet_to_seal_consistency"][
                    "declared_generated_extras"
                ],
                4,
            )
            prior = json.loads((out / "prior-attempt-audit.json").read_text())
            self.assertEqual(prior["status"], "PASS_FOR_RECOVERY")
            self.assertEqual(prior["current_verification"]["status"], "FAIL")
            self.assertFalse(prior["scored_execution"])
            seal = json.loads((out / "content-seal-v1.json").read_text())
            sealed_paths = {row["path"] for row in seal["files"]}
            self.assertIn(
                (out / "packet-manifest.json").relative_to(ROOT).as_posix(),
                sealed_paths,
            )
            self.assertNotIn(
                (out / "seal-verification.json").relative_to(ROOT).as_posix(),
                sealed_paths,
            )
            with self.assertRaises(FileExistsError):
                D2.finalize(root=ROOT, protocol_path=D2.DEFAULT_PROTOCOL, out=out)

    def test_initial_attempt_is_bound_zero_score_and_currently_invalid(self) -> None:
        audit = D2.audit_prior_attempt(root=ROOT, protocol=self.protocol)
        self.assertEqual(audit["status"], "PASS_FOR_RECOVERY")
        self.assertEqual(audit["recorded_at_creation_verification"]["status"], "PASS")
        self.assertEqual(audit["current_verification"]["status"], "FAIL")
        self.assertFalse(audit["scored_execution"])
        self.assertEqual(audit["score_rows"], [])
        self.assertFalse(audit["scientific_retry"])

    def test_packet_to_seal_comparison_detects_changed_member(self) -> None:
        readiness = D2.assess_readiness(self.protocol, self.sources)
        packet = D2.build_packet_manifest(
            root=ROOT,
            protocol_path=D2.DEFAULT_PROTOCOL,
            protocol=self.protocol,
            readiness=readiness,
            sources=self.sources,
            created_at="2026-11-02T00:00:00+00:00",
        )
        seal = {"files": copy.deepcopy(packet["artifact_inventory"])}
        seal["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not equal final seal"):
            D2.assert_packet_matches_seal(
                root=ROOT, packet=packet, seal=seal, generated_paths=[]
            )


if __name__ == "__main__":
    unittest.main()
