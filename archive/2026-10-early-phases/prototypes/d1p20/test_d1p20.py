#!/usr/bin/env python3
"""Focused D1P-20 extracted-consumer adapter regressions."""

import copy
import json
from pathlib import Path
import sys
import unittest

from bindcheck_d1 import joint_warptoad as manual

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "d1p16"))
from extract_relation import UnsupportedConstruct  # noqa: E402

from joint_extracted import (  # noqa: E402
    SMTTranslator,
    build_omega,
    encode_query,
)


LANE = HERE.parents[1]
PAPER = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper")
ARTIFACT = PAPER / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
RELATION = LANE / "results/raw/D1P-18/relation.json"
RESULTS = LANE / "results/raw/D1P-20"
IDENTITIES = {"openzeppelin": {"version": "5.6.1", "status": "test identity"}}
S0 = {
    "giga_root_history": ["1"],
    "local_root_history": ["2"],
    "nullifiers": [],
    "total_supply": "0",
    "balances": {},
}


class D1P20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manual = build_omega(
            ARTIFACT, goal="AUTH-1", s0=S0, identities=IDENTITIES
        )
        cls.extracted = build_omega(
            ARTIFACT,
            goal="AUTH-1",
            s0=S0,
            identities=IDENTITIES,
            consumer_model="EXTRACTED",
            relation_path=RELATION,
        )

    def test_manual_is_default_and_byte_identical(self):
        direct = manual.build_omega(
            ARTIFACT, goal="AUTH-1", s0=S0, identities=IDENTITIES
        )
        self.assertEqual(manual.canonical_bytes(direct), manual.canonical_bytes(self.manual))
        direct_query, direct_certificate = manual.encode_query(direct, drop_producer=True)
        wrapped_query, wrapped_certificate = encode_query(self.manual, drop_producer=True)
        self.assertEqual(direct_query, wrapped_query)
        self.assertEqual(direct_certificate, wrapped_certificate)

    def test_extracted_serializes_paths_bridges_rollback_and_policy_order(self):
        query, certificate = encode_query(
            self.extracted, consumer_model="EXTRACTED", drop_producer=True
        )
        text = query.decode()
        self.assertEqual(22, text.count("; PATH p"))
        self.assertEqual(11, text.count("; CONSUMER_VERIFIER_ARGUMENT "))
        self.assertIn("rollback_holds", text)
        self.assertLess(
            text.index("; IMPLEMENTATION_RELATION EXTRACTED end"),
            text.index("; POLICY_EVALUATION begin"),
        )
        self.assertNotIn("IMPLEMENTATION_SUMMARY MANUAL_ASSUMED", text)
        self.assertEqual(22, certificate["path_families_serialized"])

    def test_t_arith_has_identical_single_fresh_fee_transform(self):
        manual_query, manual_certificate = encode_query(
            self.manual, drop_producer=True, backend_option="T-ARITH"
        )
        extracted_query, extracted_certificate = encode_query(
            self.extracted,
            consumer_model="EXTRACTED",
            drop_producer=True,
            backend_option="T-ARITH",
        )
        needle = b"(declare-const fee_amount (_ BitVec 256))"
        self.assertEqual(1, manual_query.count(needle))
        self.assertEqual(1, extracted_query.count(needle))
        self.assertNotIn(b"(define-fun fee_amount", manual_query)
        self.assertNotIn(b"(define-fun fee_amount", extracted_query)
        self.assertEqual("T-ARITH", manual_certificate["backend_option"])
        self.assertEqual("T-ARITH", extracted_certificate["backend_option"])

    def test_unsupported_ir_operator_uses_existing_named_rejection(self):
        translator = SMTTranslator(self.extracted, "BASE")
        with self.assertRaises(UnsupportedConstruct) as caught:
            translator.expr({"op": "unmodeled", "args": []})
        self.assertEqual("UNSUPPORTED_IR_OPERATOR", caught.exception.code)
        self.assertIn("D1P-20:extracted-relation", caught.exception.location)
        with self.assertRaises(UnsupportedConstruct) as boundary:
            translator.expr({"op": "relation", "args": ["other_boundary"]})
        self.assertEqual("UNSUPPORTED_VERIFIER_RELATION", boundary.exception.code)

    def test_generated_validation_covers_five_executions_and_eight_controls(self):
        concrete = json.loads((RESULTS / "concrete-executions.json").read_text())
        controls = json.loads((RESULTS / "d1p14d-controls.json").read_text())
        validation = json.loads((RESULTS / "validation.json").read_text())
        self.assertTrue(concrete["all_checks_pass"])
        self.assertEqual(5, len(concrete["cases"]))
        self.assertTrue(controls["all_checks_pass"])
        self.assertEqual(8, len(controls["results"]))
        self.assertEqual(4, controls["positive_sat"])
        self.assertEqual(4, controls["negative_unsat"])
        self.assertEqual(0, validation["solver_accounting"]["primary_solver_calls"])

    def test_manual_differences_are_preserved_not_normalized(self):
        record = json.loads((RESULTS / "manual-differences.json").read_text())
        self.assertEqual(
            ["revert precedence and tentative trace", "producer/consumer boundary placement"],
            [item["kind"] for item in record["differences"]],
        )
        self.assertEqual([], record["five_archived_execution_disagreements"])


if __name__ == "__main__":
    unittest.main()
