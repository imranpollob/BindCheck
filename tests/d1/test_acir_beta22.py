"""Focused beta.22 decoder and component-semantic controls."""

import unittest

from bindcheck_d1.frontends.acir_binary_beta22 import MessagePackReader, _brillig_function, _opcode
from bindcheck_d1.frontends.acir_semantics_beta22 import check_supported
from bindcheck_d1.model_v2 import FIELD_MODULUS as P, Unsupported


def expression(*, linear=(), mul=(), constant=0):
    return {"linear": [list(term) for term in linear],
            "mul": [list(term) for term in mul], "constant": constant}


class MessagePackTests(unittest.TestCase):
    def test_minimal_supported_values(self):
        self.assertEqual(MessagePackReader(b"\x94\x01\xff\xc3\xa1x").one(), [1, -1, True, "x"])

    def test_every_truncation_fails_closed(self):
        encoded = b"\x82\xa1a\x92\x01\x02\xa1b\xc4\x02xy"
        self.assertEqual(MessagePackReader(encoded).one(), {"a": [1, 2], "b": b"xy"})
        for size in range(len(encoded)):
            with self.subTest(size=size), self.assertRaises(Unsupported):
                MessagePackReader(encoded[:size]).one()

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(Unsupported) as caught:
            MessagePackReader(b"\x01\x02").one()
        self.assertEqual(caught.exception.reason, "BETA22_TRAILING_MSGPACK_BYTES")


class OpcodeFailClosedTests(unittest.TestCase):
    def test_unknown_opcode_is_named(self):
        with self.assertRaises(Unsupported) as caught:
            _opcode({"FutureOpcode": []}, 7)
        self.assertEqual(caught.exception.reason, "BETA22_OPCODE_UNSUPPORTED")
        self.assertEqual(str(caught.exception), "FutureOpcode")

    def test_unknown_blackbox_is_named(self):
        with self.assertRaises(Unsupported) as caught:
            _opcode({"BlackBoxFuncCall": {"FutureHash": []}}, 9)
        self.assertEqual(caught.exception.reason, "BETA22_BLACKBOX_UNSUPPORTED")
        self.assertEqual(str(caught.exception), "FutureHash")

    def test_uninterpreted_brillig_blackbox_is_named(self):
        with self.assertRaises(Unsupported) as caught:
            _brillig_function(["hint", [{"BlackBox": {"FutureHash": []}}]], 0)
        self.assertEqual(caught.exception.reason, "BETA22_BRILLIG_BLACKBOX_UNSUPPORTED")
        self.assertEqual(str(caught.exception), "FutureHash")


class SemanticTests(unittest.TestCase):
    def test_supported_constraints_and_unsupported_inventory_are_separate(self):
        circuit = {"opcodes": [
            {"kind": "AssertZero", "opcode_index": 0,
             "expression": expression(linear=((1, 1), (P - 1, 2)))},
            {"kind": "RANGE", "opcode_index": 1, "input": {"witness": 1}, "num_bits": 4},
            {"kind": "Poseidon2Permutation", "opcode_index": 2, "inputs": [], "outputs": []},
            {"kind": "BrilligCall", "opcode_index": 3},
        ]}
        result = check_supported(circuit, {1: 7, 2: 7})
        self.assertTrue(result["all_supported_constraints_satisfied"])
        self.assertEqual(result["supported_proof_constraint_total"], 2)
        self.assertEqual(result["unsupported_proof_enforced_counts"]["Poseidon2Permutation"], 1)
        self.assertEqual(result["witness_generation_acir_counts"]["BrilligCall"], 1)
        self.assertTrue(result["no_skipped_opcodes"])

    def test_arithmetic_and_range_mutations_fail_as_expected(self):
        circuit = {"opcodes": [
            {"kind": "AssertZero", "opcode_index": 0,
             "expression": expression(linear=((1, 1), (P - 1, 2)))},
            {"kind": "RANGE", "opcode_index": 1, "input": {"witness": 1}, "num_bits": 3},
        ]}
        arithmetic = check_supported(circuit, {1: 6, 2: 5})
        self.assertEqual(arithmetic["supported_failures"][0]["opcode_index"], 0)
        ranged = check_supported(circuit, {1: 8, 2: 8})
        self.assertEqual(ranged["supported_failures"][0]["opcode_index"], 1)


if __name__ == "__main__":
    unittest.main()
