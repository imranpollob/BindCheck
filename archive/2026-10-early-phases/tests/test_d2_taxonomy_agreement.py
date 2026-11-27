"""Known-answer and fail-closed controls for D2 taxonomy agreement."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts import d2_taxonomy_agreement as agreement


def axes() -> dict[str, tuple[str, ...]]:
    return agreement._protocol_axes()


def rating(relevance: str) -> dict:
    return {
        "relevance": relevance,
        **{
            axis: {label: "absent" for label in labels}
            for axis, labels in axes().items()
        },
    }


def fixture() -> dict:
    relevance_1 = ["include", "include", "exclude", "unresolved"]
    relevance_2 = ["include", "exclude", "exclude", "unresolved"]
    items = []
    for index, (first, second) in enumerate(zip(relevance_1, relevance_2), 1):
        items.append({
            "item_id": f"I{index}",
            "family_id": f"F{index}",
            "prior_exposure": "fresh_to_both_raters",
            "ratings": {"H1": rating(first), "H2": rating(second)},
        })
    pattern_1 = ["present", "present", "absent", "absent"]
    pattern_2 = ["present", "absent", "present", "absent"]
    for item, first, second in zip(items, pattern_1, pattern_2):
        item["ratings"]["H1"]["causes"]["C_RELATION_GAP"] = first
        item["ratings"]["H2"]["causes"]["C_RELATION_GAP"] = second
    return {
        "schema": agreement.INPUT_SCHEMA,
        "codebook_version": "0.3.0",
        "study_design": "fresh_independent",
        "raters": [
            {"id": "H1", "kind": "human", "prior_exposure_summary": "none"},
            {"id": "H2", "kind": "human", "prior_exposure_summary": "none"},
        ],
        "items": items,
    }


class AgreementTests(unittest.TestCase):
    def test_known_nominal_and_binary_kappas(self) -> None:
        result = agreement.analyze(fixture())
        self.assertEqual(result["relevance"]["raw_agreement"], 0.75)
        self.assertAlmostEqual(result["relevance"]["cohen_kappa"], 7 / 11)
        label = result["multilabel_axes"]["causes"]["C_RELATION_GAP"]
        self.assertEqual(label["raw_agreement"], 0.5)
        self.assertEqual(label["chance_agreement"], 0.5)
        self.assertEqual(label["cohen_kappa"], 0.0)
        self.assertEqual(label["positive_agreement"], 0.5)
        self.assertEqual(label["negative_agreement"], 0.5)
        self.assertEqual(label["rater_1_positive_prevalence"], 0.5)
        self.assertEqual(label["rater_2_positive_prevalence"], 0.5)

    def test_no_chance_variance_is_null_not_perfect_kappa(self) -> None:
        result = agreement.analyze(fixture())
        label = result["multilabel_axes"]["causes"]["C_FIELD_MAPPING"]
        self.assertEqual(label["raw_agreement"], 1.0)
        self.assertIsNone(label["cohen_kappa"])
        self.assertEqual(label["cohen_kappa_null_reason"], "NO_CHANCE_VARIANCE")
        self.assertIsNone(label["positive_agreement"])
        self.assertEqual(label["positive_agreement_null_reason"],
                         "NO_POSITIVE_RATINGS")

    def test_missing_is_not_coerced_to_absent(self) -> None:
        data = fixture()
        data["items"][0]["ratings"]["H1"]["roles"]["A_PUBLIC_CALLER"] = "uncertain"
        data["items"][1]["ratings"]["H2"]["roles"]["A_PUBLIC_CALLER"] = None
        result = agreement.analyze(data)
        label = result["multilabel_axes"]["roles"]["A_PUBLIC_CALLER"]
        self.assertEqual(label["comparable_items"], 2)
        self.assertEqual(label["missing_pairs"], 2)
        self.assertEqual(label["state_counts"]["rater_1"]["missing"], 1)
        self.assertEqual(label["state_counts"]["rater_2"]["missing"], 1)
        self.assertEqual(result["exact_set_agreement"]["roles"]["comparable_items"], 2)

    def test_exact_set_agreement_is_secondary_known_answer(self) -> None:
        result = agreement.analyze(fixture())
        exact = result["exact_set_agreement"]["causes"]
        self.assertEqual(exact["comparable_items"], 4)
        self.assertEqual(exact["matching_items"], 2)
        self.assertEqual(exact["raw_exact_set_agreement"], 0.5)

    def test_rejects_ai_rater_and_duplicate_family(self) -> None:
        data = fixture()
        data["raters"][0]["kind"] = "ai"
        with self.assertRaisesRegex(ValueError, "AI systems cannot"):
            agreement.analyze(data)
        data = fixture()
        data["items"][1]["family_id"] = data["items"][0]["family_id"]
        with self.assertRaisesRegex(ValueError, "one scored item per family"):
            agreement.analyze(data)

    def test_fresh_study_rejects_exposed_item_and_adjudication(self) -> None:
        data = fixture()
        data["items"][0]["prior_exposure"] = "exposed_to_one_or_both"
        with self.assertRaisesRegex(ValueError, "fresh to both raters"):
            agreement.analyze(data)
        data = fixture()
        data["adjudication"] = []
        with self.assertRaisesRegex(ValueError, "original ratings only"):
            agreement.analyze(data)

    def test_protocol_is_frozen_and_contains_no_pilot_labels(self) -> None:
        protocol = json.loads(agreement.PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "FROZEN_PRE_ANNOTATION")
        self.assertEqual(protocol["version"], "0.3.0")
        self.assertEqual(protocol["research_verdict"], "UNKNOWN")
        self.assertNotIn("ratings", protocol["exposed_pilot"])

    def test_blank_artifacts_contain_no_judgment(self) -> None:
        root = Path(__file__).resolve().parents[1]
        form = json.loads((
            root / "docs/taxonomy/d2-blank-annotation-form-v1.json"
        ).read_text())
        self.assertIsNone(form["relevance"])
        for axis in ("causes", "consequences", "roles"):
            self.assertEqual(set(form[axis]), set(axes()[axis]))
            self.assertTrue(all(value is None for value in form[axis].values()))
        packet = json.loads((
            root / "docs/taxonomy/d2-primary-evidence-packet-template-v1.json"
        ).read_text())
        checks = packet["coordinator_blinding_check"]
        self.assertTrue(all(value is None for value in checks.values()))
        self.assertEqual(packet["primary_sources"], [])


if __name__ == "__main__":
    unittest.main()
