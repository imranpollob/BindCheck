from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/d2_step9_authorization_boundary.py"
SPEC = importlib.util.spec_from_file_location("d2_step9_authorization_boundary", SCRIPT)
assert SPEC and SPEC.loader
D2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2)

from bindcheck_d1.core.authorization_boundary_v1 import (  # noqa: E402
    BoundaryInputError,
    BoundedQuery,
    evaluate_boundary,
    evaluate_equal_input_arms,
    validate_boundary_input,
)


class D2Step9AuthorizationBoundaryTest(unittest.TestCase):
    def _result(self, variant: str) -> dict:
        return evaluate_equal_input_arms(D2.build_fixture(variant))

    @staticmethod
    def _ref_for(boundary, *, slot: str, domain: str) -> dict[str, str]:
        for item in boundary.identity_bundle["identities"]:
            payload = item["canonical_payload"]
            if (
                payload["object"]["logical_slot"] == slot
                and payload["context"]["domain"] == domain
            ):
                return {
                    "schema": "bindcheck.compiler-object-context-identity-ref/v1",
                    "semantic_hash": item["semantic_hash"],
                    "canonical_bytes_sha256": item["canonical_bytes_sha256"],
                }
        raise AssertionError(f"missing fixture identity: {slot} / {domain}")

    @staticmethod
    def _swap_authorization_ref(boundary, ref):
        obligation = replace(boundary.obligations[0], authorization_identity_ref=ref)
        permission = replace(
            boundary.policy.permissions[0], authorizing_identity_ref=ref
        )
        policy = replace(boundary.policy, permissions=(permission,))
        return replace(boundary, obligations=(obligation,), policy=policy)

    def test_all_development_fixtures_fail_closed_and_share_exact_inputs(self) -> None:
        rows, _ = D2.exercise_fixtures()
        self.assertEqual(len(rows), len(D2.VARIANTS))
        for row in rows:
            result = self._result(row["variant"])
            self.assertTrue(result["semantic_parity"])
            self.assertFalse(result["score_eligible"])
            self.assertEqual(result["research_verdict"], "UNKNOWN")
            self.assertEqual(len(set(result["arm_input_sha256"].values())), 1)
            self.assertEqual(len(set(result["arm_policy_sha256"].values())), 1)
            self.assertEqual(len(set(result["arm_fact_set_sha256"].values())), 1)
            for arm_result in result["results"].values():
                self.assertEqual(arm_result["state"], "UNKNOWN")
                self.assertEqual(arm_result["policy_gate"], "FAIL_CLOSED")
                self.assertEqual(arm_result["evidence_grade"], "E0")
                self.assertFalse(arm_result["score_eligible"])

    def test_private_equality_has_adjustable_attacker_counterexample(self) -> None:
        result = self._result("private-equality-counterexample")
        obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
        self.assertEqual(obligation["mechanical_state"], "MISMATCH_CANDIDATE")
        self.assertEqual(obligation["state"], "UNKNOWN")
        self.assertEqual(
            obligation["counterexample"]["assignment"],
            {"authorized_x": 0, "p": 1, "private_x": 1},
        )
        self.assertEqual(
            obligation["counterexample"]["attacker_choices"],
            {"p": 1, "private_x": 1},
        )
        self.assertFalse(obligation["counterexample"]["matching_permission_exists"])
        self.assertIn("BOUNDED_POLICY_COUNTEREXAMPLE", obligation["reason_codes"])

    def test_matched_relation_is_nonvacuous_mechanical_control_only(self) -> None:
        result = self._result("matched-positive-control")
        obligation = result["results"]["strong-simple-composition"][
            "obligation_results"
        ][0]
        self.assertEqual(obligation["mechanical_state"], "ESTABLISHED")
        self.assertEqual(obligation["state"], "UNKNOWN")
        self.assertEqual(obligation["relying_assignment_count"], 2)
        self.assertIsNone(obligation["counterexample"])
        self.assertIn(
            "BOUNDED_IMPLICATION_EXHAUSTIVE_WITHIN_DECLARED_DOMAIN",
            obligation["reason_codes"],
        )

    def test_may_underapprox_unknown_and_annotation_never_discharge_must(self) -> None:
        expected_reasons = {
            "may-producer-negative-control": "PRODUCER_QUANTIFIER_NOT_MUST",
            "underapprox-producer-negative-control": (
                "PRODUCER_APPROXIMATION_NOT_EXACT"
            ),
            "unknown-producer-negative-control": "PRODUCER_SUPPORT_NOT_SUPPORTED",
            "unsupported-condition-negative-control": (
                "PRODUCER_CONDITION_UNSUPPORTED"
            ),
            "annotation-only-negative-control": (
                "PRODUCER_DERIVATION_CLASS_NOT_DERIVED"
            ),
        }
        for variant, reason in expected_reasons.items():
            with self.subTest(variant=variant):
                result = self._result(variant)
                obligation = result["results"]["full-bindcheck"][
                    "obligation_results"
                ][0]
                self.assertEqual(obligation["mechanical_state"], "UNKNOWN")
                self.assertIn(reason, obligation["reason_codes"])
                producer = next(
                    item for item in obligation["fact_assessments"]
                    if item["role"] == "producer"
                )
                self.assertFalse(producer["eligible_for_role"])

    def test_may_overapprox_reliance_covers_path_but_does_not_discharge(self) -> None:
        result = self._result("matched-positive-control")
        obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
        reliance = next(
            item for item in obligation["fact_assessments"]
            if item["role"] == "reliance"
        )
        producer = next(
            item for item in obligation["fact_assessments"]
            if item["role"] == "producer"
        )
        self.assertEqual(reliance["quantifier"], "MAY")
        self.assertEqual(reliance["approximation"], "OVER_APPROXIMATION")
        self.assertTrue(reliance["eligible_for_role"])
        self.assertEqual(producer["quantifier"], "MUST")
        self.assertEqual(producer["approximation"], "EXACT")

    def test_absent_policy_is_unknown_not_a_candidate(self) -> None:
        boundary = replace(D2.build_fixture("matched-positive-control"), policy=None)
        result = evaluate_boundary(boundary, arm="full-bindcheck")
        obligation = result.obligation_results[0]
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(obligation.mechanical_state, "UNKNOWN")
        self.assertIn("HUMAN_POLICY_ABSENT", obligation.reason_codes)
        self.assertIn("POLICY_SEMANTICS_UNAVAILABLE", obligation.reason_codes)

    def test_review_label_without_human_roles_fails_closed(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        mislabeled = replace(
            boundary,
            policy=replace(boundary.policy, review_status="HUMAN_REVIEWED"),
        )
        result = evaluate_boundary(mislabeled, arm="full-bindcheck")
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(result.policy_gate, "FAIL_CLOSED")
        self.assertIn("HUMAN_POLICY_AUTHOR_OR_ADOPTION_MISSING", result.reason_codes)

    def test_query_limit_and_inactive_paths_do_not_establish(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        capped = replace(
            boundary,
            query=BoundedQuery(
                variable_domains=boundary.query.variable_domains,
                attacker_controlled=boundary.query.attacker_controlled,
                fixed_authenticated_context=boundary.query.fixed_authenticated_context,
                max_assignments=3,
            ),
        )
        capped_result = evaluate_boundary(capped, arm="full-bindcheck")
        self.assertEqual(capped_result.obligation_results[0].mechanical_state, "UNKNOWN")
        self.assertIn(
            "QUERY_ASSIGNMENT_LIMIT_EXCEEDED",
            capped_result.obligation_results[0].reason_codes,
        )
        inactive = self._result("inactive-path-negative-control")
        inactive_obligation = inactive["results"]["full-bindcheck"][
            "obligation_results"
        ][0]
        self.assertEqual(inactive_obligation["mechanical_state"], "UNKNOWN")
        self.assertIn("NONVACUITY_NOT_ESTABLISHED", inactive_obligation["reason_codes"])

    def test_alternative_authorization_is_not_inferred_two_sided(self) -> None:
        result = self._result("alternative-authorization-negative-control")
        obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
        self.assertEqual(obligation["mechanical_state"], "UNKNOWN")
        self.assertIn("ALTERNATIVE_AUTHORIZATION_UNREVIEWED", obligation["reason_codes"])

    def test_identity_reference_must_be_exact_step8_opaque_reference(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        obligation = boundary.obligations[0]
        bad_ref = dict(obligation.authorization_identity_ref)
        bad_ref["canonical_bytes_sha256"] = "0" * 64
        changed = replace(
            boundary,
            obligations=(replace(obligation, authorization_identity_ref=bad_ref),),
        )
        with self.assertRaisesRegex(BoundaryInputError, "unknown or noncanonical"):
            validate_boundary_input(changed)

    def test_same_display_name_different_object_cannot_swap_authorization(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        original = self._ref_for(
            boundary,
            slot="authenticated-authorized-x",
            domain="fixture-settlement-domain",
        )
        other = self._ref_for(
            boundary,
            slot="other-logical-authorized-x",
            domain="fixture-settlement-domain",
        )
        self.assertNotEqual(original, other)
        by_hash = {
            item["semantic_hash"]: item for item in boundary.identity_bundle["identities"]
        }
        self.assertEqual(
            by_hash[original["semantic_hash"]]["provenance"]["display_hints"][
                "fixture_name"
            ],
            by_hash[other["semantic_hash"]]["provenance"]["display_hints"][
                "fixture_name"
            ],
        )
        changed = self._swap_authorization_ref(boundary, other)
        validation = validate_boundary_input(changed)
        self.assertEqual(validation["identity_chain_status"], "UNKNOWN")
        self.assertIn(
            "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
            {item["reason_code"] for item in validation["identity_chain_issues"]},
        )
        result = evaluate_boundary(changed, arm="full-bindcheck")
        self.assertEqual(result.obligation_results[0].mechanical_state, "UNKNOWN")

    def test_same_object_different_context_cannot_swap_authorization(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        original = self._ref_for(
            boundary,
            slot="authenticated-authorized-x",
            domain="fixture-settlement-domain",
        )
        other_context = self._ref_for(
            boundary,
            slot="authenticated-authorized-x",
            domain="other-settlement-domain",
        )
        by_hash = {
            item["semantic_hash"]: item for item in boundary.identity_bundle["identities"]
        }
        self.assertEqual(
            by_hash[original["semantic_hash"]]["canonical_payload"]["object"],
            by_hash[other_context["semantic_hash"]]["canonical_payload"]["object"],
        )
        self.assertNotEqual(original, other_context)
        changed = self._swap_authorization_ref(boundary, other_context)
        result = evaluate_boundary(changed, arm="strong-simple-composition")
        obligation = result.obligation_results[0]
        self.assertEqual(obligation.mechanical_state, "UNKNOWN")
        self.assertIn(
            "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH", obligation.reason_codes
        )

    def test_swapped_effect_identity_breaks_reliance_chain(self) -> None:
        boundary = D2.build_fixture("matched-positive-control")
        wrong_effect_ref = self._ref_for(
            boundary,
            slot="authenticated-authorized-x",
            domain="fixture-settlement-domain",
        )
        obligation = replace(
            boundary.obligations[0],
            protected_effect_identity_ref=wrong_effect_ref,
        )
        effect = replace(
            boundary.effects[0],
            protected_effect_identity_ref=wrong_effect_ref,
        )
        permission = replace(
            boundary.policy.permissions[0],
            protected_effect_identity_ref=wrong_effect_ref,
        )
        changed = replace(
            boundary,
            obligations=(obligation,),
            effects=(effect,),
            policy=replace(boundary.policy, permissions=(permission,)),
        )
        validation = validate_boundary_input(changed)
        self.assertIn(
            "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH",
            {item["reason_code"] for item in validation["identity_chain_issues"]},
        )
        result = evaluate_boundary(changed, arm="full-bindcheck")
        obligation_result = result.obligation_results[0]
        self.assertEqual(obligation_result.mechanical_state, "UNKNOWN")
        self.assertIn(
            "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH",
            obligation_result.reason_codes,
        )

    def test_empty_obligation_set_is_unknown(self) -> None:
        boundary = replace(D2.build_fixture("matched-positive-control"), obligations=())
        result = evaluate_boundary(boundary, arm="full-bindcheck")
        self.assertEqual(result.state, "UNKNOWN")
        self.assertIn("EMPTY_OBLIGATION_SET", result.reason_codes)


if __name__ == "__main__":
    unittest.main()
