from __future__ import annotations

import unittest

from bindcheck_d1.frontends.solidity_ast_v1_1 import (
    _anchor_candidates,
    _resolve_direct_width,
    _select_effect_model,
    Extractor,
    Value,
)
from bindcheck_d1.static_analyzer_v1 import _memory_dependency_facts


class D1P40MemoryTests(unittest.TestCase):
    def test_constant_read_selects_only_the_exact_memory_initializer(self):
        opcodes = [
            {"kind": "MemoryInit", "block_id": 7, "init": [10, 11]},
            {"kind": "MemoryOp", "block_id": 7,
             "operation": {"mul": [], "linear": [], "constant": 0},
             "index": {"mul": [], "linear": [], "constant": 1},
             "value": {"mul": [], "linear": [[1, 12]], "constant": 0}},
        ]
        exact, unresolved = _memory_dependency_facts(opcodes)
        self.assertEqual(exact, {11: 1})
        self.assertEqual(unresolved, set())

    def test_dynamic_read_is_unknown_instead_of_used_or_unused(self):
        opcodes = [
            {"kind": "MemoryInit", "block_id": 7, "init": [10, 11]},
            {"kind": "MemoryOp", "block_id": 7, "operation": "read",
             "index": 12, "value": 13},
        ]
        exact, unresolved = _memory_dependency_facts(opcodes)
        self.assertEqual(exact, {})
        self.assertEqual(unresolved, {10, 11})

    def test_dynamic_write_keeps_a_later_constant_read_unknown(self):
        opcodes = [
            {"kind": "MemoryInit", "block_id": 7, "init": [10, 11]},
            {"kind": "MemoryOp", "block_id": 7,
             "operation": {"mul": [], "linear": [], "constant": 1},
             "index": {"mul": [], "linear": [[1, 12]], "constant": 0},
             "value": {"mul": [], "linear": [[1, 13]], "constant": 0}},
            {"kind": "MemoryOp", "block_id": 7,
             "operation": {"mul": [], "linear": [], "constant": 0},
             "index": {"mul": [], "linear": [], "constant": 0},
             "value": {"mul": [], "linear": [[1, 14]], "constant": 0}},
        ]
        exact, unresolved = _memory_dependency_facts(opcodes)
        self.assertEqual(exact, {})
        self.assertEqual(unresolved, {10, 11, 13})


class D1P40MappingAndEffectTests(unittest.TestCase):
    def test_short_consumer_array_does_not_infer_a_selector_prefix(self):
        with self.assertRaisesRegex(ValueError, "SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS"):
            _resolve_direct_width(5, {3}, 3)
        self.assertEqual(_resolve_direct_width(5, {5}, 2), 5)

    def test_loop_interval_excludes_unreachable_tail_words(self):
        extractor = object.__new__(Extractor)
        extractor.public_count = 4
        words = extractor._words_for_array_index(
            Value(array_start=0), Value(lower=0, upper=1)
        )
        self.assertEqual(words, {0, 1})

    def test_token_effect_requires_standard_method_identity_and_signature(self):
        models = [{"effect": "token-transfer", "function_name": "transfer",
                   "function_type_contains": "function (address,uint256)"}]
        self.assertIsNotNone(_select_effect_model(
            models, [("transfer", "function (address,uint256) external returns (bool)")]
        ))
        self.assertIsNone(_select_effect_model(
            models, [("helper", "function (address,uint256)")]
        ))


class D1P40AnchorTests(unittest.TestCase):
    def test_anchor_candidate_exists_before_positive_guard_is_found(self):
        read = {"declarations": [1], "key_words": [0], "location": "C.sol:10"}
        negative = _anchor_candidates([read], [], [])
        self.assertEqual(negative, [{
            "public_index": 0, "origin": "public_inputs[0]", "must_be_in": False,
            "evidence": ["C.sol:10"],
        }])
        guard = {"requires_false": False, "location": "C.sol:11",
                 "storage": [{"declarations": [1], "key_words": [0]}]}
        positive = _anchor_candidates([read], [guard], [])
        self.assertTrue(positive[0]["must_be_in"])
        self.assertEqual(positive[0]["evidence"], ["C.sol:11"])


if __name__ == "__main__":
    unittest.main()
