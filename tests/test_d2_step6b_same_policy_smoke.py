from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/d2_step6b_same_policy_smoke.py"
SPEC = importlib.util.spec_from_file_location("d2_step6b_same_policy_smoke", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
D2_06B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2_06B)


class D2Step6BSamePolicySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(D2_06B.DEFAULT_PROTOCOL.read_text())
        cls.inventory = json.loads(D2_06B.DEFAULT_INVENTORY.read_text())

    def test_protocol_stays_unscored_unknown_and_unsealed(self) -> None:
        self.assertEqual(self.protocol["status"], D2_06B.UNSCORED_STATUS)
        self.assertEqual(self.protocol["research_verdict"], "UNKNOWN")
        boundary = self.protocol["execution_boundary"]
        self.assertFalse(boundary["scored_execution_authorized"])
        self.assertFalse(boundary["step_7_seal_present"])
        self.assertEqual(len(self.protocol["smoke_cases"]), 2)

    def test_policy_exactly_matches_preexisting_harness(self) -> None:
        declared = sorted(
            item["invariant"] for item in self.protocol["same_policy"]["obligations"]
        )
        self.assertEqual(declared, D2_06B.harness_invariants())
        implementation = self.protocol["same_policy"]["implementation"]
        self.assertEqual(D2_06B.sha256(D2_06B.HARNESS), implementation["sha256"])
        self.assertEqual(implementation["evidence_ceiling"], "E1")

    def test_missing_human_policy_roles_are_not_silently_satisfied(self) -> None:
        independence = self.protocol["same_policy"]["independence"]
        self.assertEqual(independence["human_policy_author_status"], "UNRESOLVED")
        self.assertEqual(independence["different_human_reviewer_status"], "UNRESOLVED")
        self.assertIn("BLOCKED", independence["step_7_eligibility"])

    def test_native_parser_preserves_pass_fail_only(self) -> None:
        sample = """
[PASS] invariant_alpha
[FAIL: assertion failed] invariant_beta
[Sequence] this line is native detail, not a new diagnosis
[PASS] invariant_alpha
"""
        self.assertEqual(
            D2_06B.parse_foundry_invariants(sample),
            {"invariant_alpha": "PASS", "invariant_beta": "FAIL"},
        )

    def test_archived_native_transcripts_exercise_both_adapter_paths(self) -> None:
        pinned = (
            ROOT
            / "results/raw/D1P-32/foundry-policy-pinned/invariant-g4-final.stdout.txt"
        ).read_text()
        m_src = (
            ROOT
            / "results/raw/D1P-32/foundry-policy-m-src/invariant-g4-final.stdout.txt"
        ).read_text()
        pinned_outcomes = D2_06B.parse_foundry_invariants(pinned)
        m_src_outcomes = D2_06B.parse_foundry_invariants(m_src)
        self.assertEqual(set(pinned_outcomes.values()), {"PASS"})
        self.assertEqual(
            [name for name, status in m_src_outcomes.items() if status == "FAIL"],
            ["invariant_roots_are_admitted"],
        )
        self.assertEqual(set(pinned_outcomes), set(D2_06B.harness_invariants()))
        self.assertEqual(set(m_src_outcomes), set(D2_06B.harness_invariants()))

    def test_inventory_is_complete_and_llm_arm_is_not_selected(self) -> None:
        ids = {item["id"] for item in self.inventory["comparators"]}
        self.assertEqual(ids, D2_06B.REQUIRED_COMPARATORS)
        elsa = next(item for item in self.inventory["comparators"] if item["id"] == "CMP-ELSA")
        self.assertEqual(elsa["arms"]["llm_supplement"], "NOT_SELECTED")
        self.assertIsNone(elsa["pin"]["model"])
        self.assertIsNone(elsa["pin"]["prompt"])

    def test_protocol_and_inventory_hash_validation(self) -> None:
        validated = D2_06B.validate_protocol(self.protocol, self.inventory)
        self.assertEqual(validated["declared_invariants"], D2_06B.harness_invariants())
        self.assertEqual(set(validated["comparator_ids"]), D2_06B.REQUIRED_COMPARATORS)

    def test_smoke_config_is_reduced_fixed_offline_and_not_final(self) -> None:
        config = self.protocol["smoke_configuration"]
        self.assertEqual(config["runs"], 32)
        self.assertEqual(config["depth"], 20)
        self.assertEqual(config["network_calls"], 0)
        self.assertEqual(config["scientific_retries"], 0)
        rendered = D2_06B.foundry_config(self.protocol)
        self.assertIn("offline = true", rendered)
        self.assertIn("runs = 32", rendered)
        self.assertIn("depth = 20", rendered)
        self.assertIn("construction smoke", config["purpose_limit"].lower())


if __name__ == "__main__":
    unittest.main()
