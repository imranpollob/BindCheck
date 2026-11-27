"""Offline controls for the solver-neutral symbolic consumer transition."""

from dataclasses import replace
from hashlib import sha256
import unittest

from bindcheck_d1.frontends.consumer_execution_v1 import Token
from bindcheck_d1.model_v2 import Policy
from bindcheck_d1.symbolic_consumer_v2 import (
    MAX_V2_AMOUNT,
    ConsumerAssignment,
    GuardBoundary,
    MintEntry,
    VerifierBoundary,
    build_transition,
    policy_occurrence,
)


class SymbolicConsumerTests(unittest.TestCase):
    CONTRACT = 0xC0
    TOKEN = 0x70
    SENDER = 0xA0
    RECIPIENT = 0xDEAD
    POLICY_SHA = "0" * 64

    def setUp(self):
        self.plans = {}

    def plan(self, n=8):
        if n not in self.plans:
            self.plans[n] = build_transition(n)
        return self.plans[n]

    def assignment(self, messages, *, n=8, funds=None, mints=None,
                   guards=None, verifier=None, token_map=None, height=2,
                   current_height=1, substitutions=None):
        if len(messages) != n:
            raise ValueError("test message length")
        funds = n * MAX_V2_AMOUNT if funds is None else funds
        guards = guards or GuardBoundary(
            True, True,
            "ASSUMED_OWNED_REGISTERED_PROVER",
            "ASSUMED_OWNED_VALIDATOR_QUORUM",
            ("registered prover caller", "validator quorum signatures"),
            7,
        )
        verifier = verifier or VerifierBoundary(
            1, 0xB0, n, True, True, 1,
            "payy-B-agg-final", "FULL_PRODUCER_RELATION", b"proof", True,
        )
        return ConsumerAssignment(
            (0x11, 0x12, 0x13, *messages),
            height,
            0x11,
            current_height,
            self.SENDER,
            self.CONTRACT,
            guards,
            verifier,
            0,
            Token(self.TOKEN, {self.CONTRACT: funds}, funds),
            mints or {},
            {0x4B: self.TOKEN} if token_map is None else token_map,
            substitutions or {},
        )

    def occurrence(self, index, kind, amount, note_hash, recipient=None, note_kind=0x4B):
        return policy_occurrence(
            ("producer", index), domain="payy-rollup-v2", kind=kind,
            note_kind=note_kind, amount=amount, note_hash=note_hash,
            recipient=recipient, rationale_path="policy:test",
            rationale_sha256=self.POLICY_SHA, location="test-only policy",
        )

    def policy(self, permissions=(), obligations=()):
        return Policy(tuple(permissions), tuple(obligations), "test policy kept independent")

    @staticmethod
    def mint(note_kind=0x4B, amount=100, note_hash=42):
        return [2, note_kind, amount, note_hash]

    @staticmethod
    def burn(amount=7, note_hash=42, recipient=0xDEAD, note_kind=0x4B):
        return [3, note_kind, amount, note_hash, recipient]

    def test_expression_graph_is_configurable_and_inspectable(self):
        stats = self.plan(8).expression_stats()
        self.assertEqual(stats["length"], 8)
        self.assertEqual(stats["effect_templates"], 16)
        self.assertIn("public_inputs", stats["input_symbols"])
        self.assertIn("verifier_accepts", stats["input_symbols"])
        self.assertGreater(stats["root_expression_node_sum"], 0)

    def test_normal_burn_low160_and_exact_policy_match(self):
        high_recipient = (1 << 160) + self.RECIPIENT
        words = self.burn(recipient=high_recipient) + [0] * 3
        permission = self.occurrence(0, "burn", 7, 42, self.RECIPIENT)
        result = self.plan().evaluate(
            self.assignment(words), self.policy((permission,), (permission,)))
        self.assertEqual(result.outcome, "RETURN")
        self.assertEqual(result.token.balances[self.RECIPIENT], 7)
        self.assertEqual(len(result.effects), 1)
        self.assertEqual(result.effects[0].key.recipient, self.RECIPIENT)
        self.assertEqual(result.trace_assessment.authorization_deficits, ())
        self.assertEqual(result.trace_assessment.coverage_deficits, ())
        self.assertTrue(result.admission.admitted)
        self.assertEqual(result.validator_set_index, 7)
        self.assertTrue(result.verifier_claim.sound_binding_established)

    def test_zero_value_default_mint_is_a_protected_spent_write(self):
        words = self.mint(note_kind=0, amount=0, note_hash=43) + [0] * 4
        permission = self.occurrence(0, "mint", 0, 43, None, note_kind=0)
        result = self.plan().evaluate(
            self.assignment(words), self.policy((permission,), (permission,)))
        self.assertEqual(result.outcome, "RETURN")
        self.assertTrue(result.mints[43].spent)
        self.assertEqual((result.effects[0].key.kind, result.effects[0].key.amount), ("mint", 0))
        self.assertEqual(result.trace_assessment.authorization_deficits, ())

    def test_duplicate_mint_rolls_back_first_spent_write(self):
        words = self.mint() + self.mint()
        registry = {42: MintEntry(0x4B, 100, False)}
        result = self.plan().evaluate(
            self.assignment(words, mints=registry), self.policy())
        self.assertEqual(result.outcome, "REVERT")
        self.assertEqual(result.reason, "MINT_REGISTRY_REJECT_AT_STEP_1")
        self.assertFalse(result.mints[42].spent)
        self.assertEqual(result.effects, ())

    def test_late_truncated_record_rolls_back_prior_transfer(self):
        words = self.burn() + [0, 0, 2]
        before = 8 * MAX_V2_AMOUNT
        result = self.plan().evaluate(self.assignment(words), self.policy())
        self.assertEqual(result.outcome, "REVERT")
        self.assertEqual(result.reason, "TRUNCATED_MINT_AT_STEP_3")
        self.assertEqual(result.token.balances, {self.CONTRACT: before})
        self.assertEqual(result.effects, ())

    def test_invalid_kind_and_false_caller_guard_revert(self):
        invalid = self.plan().evaluate(self.assignment([4] + [0] * 7), self.policy())
        self.assertEqual((invalid.outcome, invalid.reason), ("REVERT", "INVALID_KIND_AT_STEP_0"))
        guards = GuardBoundary(False, True, "", "ASSUMED_VALIDATOR_QUORUM",
                               ("validator quorum signatures",), 7)
        caller = self.plan().evaluate(self.assignment([0] * 8, guards=guards), self.policy())
        self.assertEqual((caller.outcome, caller.reason), ("REVERT", "PROVER_GUARD_REVERT"))

    def test_later_verifier_and_height_guards_roll_back(self):
        registry = {42: MintEntry(0x4B, 100, False)}
        words = self.mint() + [0] * 4
        base = self.assignment(words, mints=registry)
        rejected = self.plan().evaluate(
            replace(base, verifier=replace(base.verifier, accepted=False)), self.policy())
        self.assertEqual((rejected.outcome, rejected.reason), ("REVERT", "PROOF_VERIFIER_REVERT"))
        self.assertFalse(rejected.mints[42].spent)
        self.assertEqual(rejected.validator_set_index, 0)
        stale = self.plan().evaluate(replace(base, height=1), self.policy())
        self.assertEqual((stale.outcome, stale.reason), ("REVERT", "HEIGHT_GUARD_REVERT"))
        self.assertFalse(stale.mints[42].spent)
        self.assertEqual(stale.validator_set_index, 0)

    def test_sequential_transfer_failure_is_explicit_and_not_an_effect(self):
        n = 10
        words = self.burn() + self.burn()
        result = self.plan(n).evaluate(
            self.assignment(words, n=n, funds=10), self.policy())
        self.assertEqual(result.outcome, "RETURN")
        self.assertEqual([item["success"] for item in result.burn_attempts], [True, False])
        self.assertEqual(len(result.effects), 1)
        self.assertEqual(result.token.balances[self.CONTRACT], 3)
        self.assertEqual(result.token.balances[self.RECIPIENT], 7)
        self.assertEqual(result.trace_assessment.reason, "DEFERRAL_UNSUPPORTED")
        self.assertIn("MESSAGE_BOUND_OUTSIDE_V2", result.admission.reasons)
        self.assertIn("INITIAL_FUNDING_OUTSIDE_V2", result.admission.reasons)

    def test_zero_and_self_burns_remain_occurrences(self):
        zero = self.plan().evaluate(
            self.assignment(self.burn(amount=0) + [0] * 3), self.policy())
        self.assertEqual((zero.outcome, len(zero.effects)), ("RETURN", 1))
        self.assertEqual(zero.effects[0].key.amount, 0)
        self.assertEqual(zero.token.balances[self.CONTRACT], 8 * MAX_V2_AMOUNT)
        self_transfer = self.plan().evaluate(
            self.assignment(self.burn(recipient=self.CONTRACT) + [0] * 3), self.policy())
        self.assertEqual((self_transfer.outcome, len(self_transfer.effects)), ("RETURN", 1))
        self.assertEqual(self_transfer.token.balances[self.CONTRACT], 8 * MAX_V2_AMOUNT)

    def test_unsupported_boundaries_are_unknown_not_safe(self):
        unresolved = GuardBoundary(None, True, "", "ASSUMED_VALIDATOR_QUORUM",
                                   ("validator quorum signatures",), 7)
        result = self.plan().evaluate(self.assignment([0] * 8, guards=unresolved), self.policy())
        self.assertEqual(result.outcome, "UNKNOWN")
        self.assertIn("PROVER_GUARD_UNRESOLVED", result.unsupported_reasons)
        target = self.plan().evaluate(
            self.assignment(self.burn() + [0] * 3, token_map={0x4B: 0x999}), self.policy())
        self.assertEqual(target.outcome, "UNKNOWN")
        self.assertEqual(target.reason, "TOKEN_TARGET_UNSUPPORTED_AT_STEP_0")
        substitution = self.plan().evaluate(
            self.assignment([0] * 8, substitutions={1: self.SENDER}), self.policy())
        self.assertEqual(substitution.outcome, "UNKNOWN")
        self.assertIn("SUBSTITUTION_UNSUPPORTED", substitution.unsupported_reasons)

    def test_selected_cone_never_becomes_full_verifier_binding(self):
        boundary = VerifierBoundary(
            1, 0xB0, 8, True, True, 1,
            "historical-selected-cone", "SELECTED_CONE_ABSTRACTION", b"proof", True,
        )
        result = self.plan().evaluate(
            self.assignment([0] * 8, verifier=boundary), self.policy())
        self.assertEqual(result.outcome, "RETURN")
        self.assertFalse(result.verifier_claim.sound_binding_established)
        self.assertIn("SELECTED_CONE_IS_NOT_FULL_RELATION", result.verifier_claim.reasons)
        self.assertEqual(result.security_verdict, "UNKNOWN")

    def test_verifier_claim_binds_exact_key_and_public_input_vector(self):
        assignment = self.assignment([0] * 8)
        result = self.plan().evaluate(assignment, self.policy())
        claim = result.verifier_claim
        expected_bytes = b"".join(word.to_bytes(32, "big") for word in assignment.public_inputs)
        self.assertTrue(claim.call_reached)
        self.assertTrue(claim.accepted)
        self.assertEqual(claim.verification_key_hash, assignment.verifier.requested_key_hash)
        self.assertEqual(claim.public_inputs, assignment.public_inputs)
        self.assertEqual(claim.public_inputs_sha256, sha256(expected_bytes).hexdigest())

        mismatch = replace(
            assignment,
            verifier=replace(assignment.verifier, relation_key_hash=2),
        )
        mismatch_result = self.plan().evaluate(mismatch, self.policy())
        self.assertFalse(mismatch_result.verifier_claim.sound_binding_established)
        self.assertIn(
            "VERIFICATION_KEY_RELATION_MISMATCH",
            mismatch_result.verifier_claim.reasons,
        )

    def test_occurrence_multiplicity_is_injective_not_membership(self):
        n = 10
        words = self.burn(amount=0) + self.burn(amount=0)
        one = self.occurrence(0, "burn", 0, 42, self.RECIPIENT)
        result = self.plan(n).evaluate(
            self.assignment(words, n=n), self.policy((one,), (one,)))
        self.assertEqual(len(result.effects), 2)
        self.assertEqual(result.trace_assessment.authorization_deficits[0][1], 1)
        two = self.occurrence(1, "burn", 0, 42, self.RECIPIENT)
        matched = self.plan(n).evaluate(
            self.assignment(words, n=n), self.policy((one, two), (one, two)))
        self.assertEqual(matched.trace_assessment.authorization_deficits, ())
        self.assertEqual(matched.trace_assessment.coverage_deficits, ())


if __name__ == "__main__":
    unittest.main()
