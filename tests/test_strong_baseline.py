from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from baselines.strong.arm_c import analyze_arm_c
from baselines.strong.solidity_scan import scan_repository


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADV = ROOT / "redteam" / "adversarial"


def fake_b(root: pathlib.Path) -> dict:
    return {
        "run": {"status": "completed"},
        "result": {"verdict": "UNKNOWN", "findings": []},
        "native": {"signals": []},
        "inputs": {"root": str(root)},
    }


class StrongBaselineTests(unittest.TestCase):
    def test_expectations_are_balanced_and_unique(self) -> None:
        expected = json.loads((ADV / "expected.json").read_text(encoding="utf-8"))
        self.assertEqual(len(expected["cases"]), 46)
        self.assertEqual(sum(case["label"] == "VULNERABLE" for case in expected["cases"]), 23)
        self.assertEqual(sum(case["label"] == "LEGITIMATE" for case in expected["cases"]), 23)
        self.assertEqual(len({case["id"] for case in expected["cases"]}), 46)

    def test_policies_do_not_encode_expected_verdicts(self) -> None:
        for path in sorted(ADV.glob("ADV-*/policy.json")):
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn('"verdict"', text, path)
            self.assertNotIn('"vulnerable"', text, path)
            self.assertNotIn('"missing_constraint"', text, path)

    def test_effect_scanner_separates_recipient_pair(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V01")
        legitimate = scan_repository(ADV / "ADV-L01")
        self.assertIn("A_EFFECT_RECIPIENT_UNBOUND", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_EFFECT_RECIPIENT_UNBOUND", {item["code"] for item in legitimate["findings"]})

    def test_guard_scanner_requires_dominance(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V06")
        legitimate = scan_repository(ADV / "ADV-L06")
        self.assertIn("A_GUARD_NOT_DOMINATING", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_GUARD_NOT_DOMINATING", {item["code"] for item in legitimate["findings"]})

    def test_native_call_value_is_detected_through_payable_cast(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V03")
        legitimate = scan_repository(ADV / "ADV-L03")
        self.assertIn("A_CALL_VALUE_UNBOUND", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_CALL_VALUE_UNBOUND", {item["code"] for item in legitimate["findings"]})

    def test_replay_guard_is_position_specific(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V09")
        legitimate = scan_repository(ADV / "ADV-L09")
        self.assertIn("A_REPLAY_POSITION_FIELD_GUARD_MISSING", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_REPLAY_POSITION_FIELD_GUARD_MISSING", {item["code"] for item in legitimate["findings"]})

    def test_safe_transfer_record_amount(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V21")
        legitimate = scan_repository(ADV / "ADV-L21")
        self.assertIn("A_EFFECT_AMOUNT_UNBOUND", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_EFFECT_AMOUNT_UNBOUND", {item["code"] for item in legitimate["findings"]})

    def test_nested_replay_uses_final_key(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V22")
        legitimate = scan_repository(ADV / "ADV-L22")
        self.assertIn("A_REPLAY_KEY_UNBOUND", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_REPLAY_KEY_UNBOUND", {item["code"] for item in legitimate["findings"]})

    def test_erc721_safe_mint_recipient(self) -> None:
        vulnerable = scan_repository(ADV / "ADV-V23")
        legitimate = scan_repository(ADV / "ADV-L23")
        self.assertIn("A_EFFECT_RECIPIENT_UNBOUND", {item["code"] for item in vulnerable["findings"]})
        self.assertNotIn("A_EFFECT_RECIPIENT_UNBOUND", {item["code"] for item in legitimate["findings"]})

    def test_composition_checks_commitment_order(self) -> None:
        for case_id, expected in (("ADV-V16", "VIOLATION"), ("ADV-L16", "VERIFIED_WITHIN_SCOPE")):
            root = ADV / case_id
            scan = scan_repository(root)
            fake_a = {
                "run": {"status": "completed"},
                "result": {"verdict": "VIOLATION", "findings": scan["findings"]},
            }
            with tempfile.TemporaryDirectory() as temp:
                result = analyze_arm_c(root, pathlib.Path(temp), fake_a, fake_b(root))
            self.assertEqual(result["result"]["verdict"], expected)

    def test_composition_checks_array_extent(self) -> None:
        for case_id, expected in (("ADV-V11", "VIOLATION"), ("ADV-L11", "VERIFIED_WITHIN_SCOPE")):
            root = ADV / case_id
            fake_a = {"run": {"status": "completed"}, "result": {"verdict": "UNKNOWN", "findings": []}}
            with tempfile.TemporaryDirectory() as temp:
                result = analyze_arm_c(root, pathlib.Path(temp), fake_a, fake_b(root))
            self.assertEqual(result["result"]["verdict"], expected)


if __name__ == "__main__":
    unittest.main()
