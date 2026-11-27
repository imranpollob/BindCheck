import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

from bindcheck_d1.conservative_propagation_v1 import (  # noqa: E402
    State,
    UnsupportedOpcode,
)
from bindcheck_d1.n8_consumer_shapes_v1 import (  # noqa: E402
    decode_shape,
    shapes,
    validate_exhaustively,
)


def load_offline_script():
    path = ROOT / "scripts/d1p_09_offline.py"
    spec = importlib.util.spec_from_file_location("d1p09_offline_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConservativePropagationTests(unittest.TestCase):
    def test_t22_lost_equality_regression_retains_interface_reconstruction(self):
        # T22-v2's failure mode was dropping an equality after learning the
        # goal/interface value.  The reduced relation may drop this assertion
        # only while retaining an explicit w9=7 reconstruction equality.
        state = State(
            [(41, ("assert", [(1, [9]), (-1, [1])]))],
            {1: 7},
            {1: "test case fixes source"},
            {9},
        ).run()
        audit = state.audit({1, 9}, {1}, "w1 == 7")
        self.assertEqual(audit["residual"]["original_opcodes"], 0)
        self.assertEqual(
            audit["residual"]["with_case_and_reconstruction_witnesses"], 2
        )
        self.assertEqual(
            audit["residual"]["retained_interface_equalities"],
            [{
                "witness": 9,
                "value": "7",
                "reason": {
                    "rule": "unique_affine_field_solution",
                    "source": 41,
                    "coefficient": "1",
                    "constant": str(-7 % (21888242871839275222246405745257275088548364400416034343698204186575808495617)),
                },
            }],
        )

    def test_nonlinear_single_witness_is_not_linearized(self):
        state = State(
            [(1, ("assert", [(1, [2, 2]), (-1, [1])]))],
            {1: 4},
            {1: "case"},
        ).run()
        audit = state.audit({1, 2}, {1}, "w1 == 4")
        self.assertEqual(audit["residual"]["original_opcodes"], 1)
        self.assertNotIn(2, state.values)

    def test_zero_multiplier_keeps_interface_as_free_extension(self):
        state = State(
            [(1, ("assert", [(1, [1, 2])]))],
            {1: 0},
            {1: "case"},
            {2},
        ).run()
        audit = state.audit({1, 2}, {1}, "w1 == 0")
        self.assertEqual(audit["residual"]["retained_interface_free_witnesses"], [2])
        self.assertEqual(audit["residual"]["with_case_and_reconstruction_witnesses"], 2)

    def test_known_memory_read_has_reconstruction(self):
        opcodes = [
            (10, ("init", 0, [[(1, [1])], [(1, [2])]])),
            (11, ("read", 0, [(1, [3])], [(0, [])])),
        ]
        state = State(opcodes, {1: 9}, {1: "case"}, {3}).run()
        audit = state.audit({1, 2, 3}, {1}, "w1 == 9")
        self.assertEqual(state.values[3], 9)
        self.assertEqual(audit["residual"]["memory_opcode_counts"], {"init": 1})
        self.assertEqual(audit["residual"]["retained_interface_equalities"][0]["witness"], 3)

    def test_symbolic_write_index_keeps_memory_suffix(self):
        opcodes = [
            (10, ("init", 0, [[(1, [1])]])),
            (11, ("write", 0, [(1, [4])], [(1, [5])])),
            (12, ("read", 0, [(1, [6])], [(0, [])])),
        ]
        state = State(opcodes, {}, {}, {6}).run()
        audit = state.audit({1, 4, 5, 6}, {4}, "w4 arbitrary")
        self.assertEqual(audit["residual"]["memory_opcode_counts"],
                         {"init": 1, "read": 1, "write": 1})
        self.assertEqual(audit["reduction_reason_counts"], {"retain_memory_suffix": 1})

    def test_unsupported_opcode_fails_closed(self):
        with self.assertRaises(UnsupportedOpcode):
            State([(0, ("blackbox", [9]))], {}, {})


class ConsumerShapeTests(unittest.TestCase):
    def test_exact_shape_inventory_and_all_padding(self):
        defined = shapes()
        self.assertEqual(len(defined), 11)
        padding = [shape for shape in defined if shape.kinds == (0,) * 8]
        self.assertEqual(len(padding), 1)
        self.assertEqual(padding[0].fixed_positions, dict(enumerate((0,) * 8)))

    def test_payload_positions_stay_symbolic(self):
        two_mints = next(shape for shape in shapes() if shape.kinds == (2, 2))
        self.assertEqual(two_mints.fixed_positions, {0: 2, 4: 2})
        payload = set(range(8)) - set(two_mints.fixed_positions)
        self.assertEqual(payload, {1, 2, 3, 5, 6, 7})

    def test_invalid_and_truncated_are_outside_shapes(self):
        invalid = (4, 0, 0, 0, 0, 0, 0, 0)
        truncated = (0, 0, 0, 0, 3, 11, 12, 13)
        self.assertEqual(decode_shape(invalid)[0], "invalid_kind")
        self.assertEqual(decode_shape(truncated)[0], "truncated")
        self.assertFalse(any(shape.matches(invalid) for shape in shapes()))
        self.assertFalse(any(shape.matches(truncated) for shape in shapes()))

    def test_exhaustive_coverage_and_disjointness(self):
        result = validate_exhaustively()
        self.assertEqual(result["assignments"], 390625)
        self.assertTrue(result["coverage_on_structurally_valid_decoding"])
        self.assertTrue(result["mutual_exclusion_on_structurally_valid_decoding"])
        self.assertTrue(result["invalid_and_truncated_outside_union"])


class ProducerCellFactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.offline = load_offline_script()
        cls.stream = {"activation": 100, "words": tuple(range(200, 208))}

    def test_only_literal_cell_constants_are_fixed(self):
        inactive, _, _ = self.offline.single_cell_facts("inactive", self.stream)
        length4, _, _ = self.offline.single_cell_facts("length_4", self.stream)
        self.assertEqual(inactive, {100: 0})
        self.assertEqual(length4, {200: 2})

    def test_nonzero_and_disjunctions_are_not_chosen(self):
        for cell in ("active_empty", "length_5", "truncated_8"):
            fixed, _, _ = self.offline.single_cell_facts(cell, self.stream)
            self.assertEqual(fixed, {})


if __name__ == "__main__":
    unittest.main()
