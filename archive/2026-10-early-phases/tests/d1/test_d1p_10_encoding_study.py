import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def load_study():
    path = ROOT / "scripts/d1p_10_encoding_study.py"
    spec = importlib.util.spec_from_file_location("d1p10_study_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class D1P10EncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = load_study()
        (cls.tail, cls.specializer, cls.offline, cls.acir,
         cls.indexed, cls.witnesses) = cls.study.selected_cone()

    def test_selected_cone_identity_is_not_full_relation(self):
        self.assertEqual(len(self.indexed), 620)
        self.assertEqual(len(self.witnesses), 540)
        self.assertEqual(
            self.study.Counter(opcode[0] for _, opcode in self.indexed),
            self.study.Counter({"assert": 546, "range": 58, "read": 15, "init": 1}),
        )

    def test_range_inventory_does_not_assert_bottleneck(self):
        bits = self.study.Counter(
            opcode[2] for _, opcode in self.indexed if opcode[0] == "range"
        )
        self.assertEqual(bits, {32: 50, 1: 8})

    def test_radix_expansion_is_exact_for_complete_eight_bit_domain(self):
        # Finite enumeration supplements, but does not replace, the field/root
        # argument frozen in the protocol.
        for base in (4, 16, 256):
            width = base.bit_length() - 1
            count = 8 // width
            for value in range(256):
                digits = [(value // (base ** index)) % base for index in range(count)]
                self.assertEqual(sum(digit * base ** index
                                     for index, digit in enumerate(digits)), value)
                self.assertTrue(all(0 <= digit < base for digit in digits))

    def test_range_encodings_have_expected_auxiliary_counts(self):
        expected = {"bits": 32, "radix4": 16, "radix16": 8, "radix256": 4}
        for mode, count in expected.items():
            encoder = self.study.ComponentEncoder([1], mode, "test")
            constraints = encoder.range_constraints(5, [(1, [1])], 32)
            self.assertEqual(len(encoder.auxiliary), count)
            self.assertEqual(len(constraints), count + 1)

    def test_all_complete_cell_predicates_and_original_goals_are_retained(self):
        ranges = [(source, opcode) for source, opcode in self.indexed
                  if opcode[0] == "range"]
        parents = {obligation: self.study.parent_for(self.specializer, obligation)
                   for obligation in self.study.OBLIGATIONS}
        for cell in self.specializer.cell_pairs():
            fixed, basis, _ = self.study.cell_facts(self.offline, cell)
            state = self.study.State(self.indexed, fixed, basis).run()
            for obligation in self.study.OBLIGATIONS:
                encoder = self.study.ComponentEncoder(self.witnesses, "bits", "test")
                groups = encoder.groups_from_state(state, ranges)
                reconstruction = [
                    f"(= w{witness} {self.study.ff_const(value)})"
                    for witness, value in sorted(state.values.items())
                ]
                data = self.study.component_script(
                    encoder, groups, [cell["predicate"], *reconstruction],
                    self.study.original_suffix(parents[obligation], obligation),
                    self.witnesses,
                ).decode("ascii")
                self.assertIn(f"(assert {cell['predicate']})", data)
                self.assertEqual(len(groups["ranges"]), 1666)
                if obligation != "cone":
                    self.assertIn(parents[obligation]["goal_line"].strip(), data)
                    self.assertIn(parents[obligation]["walk"].strip(), data)

    def test_t22_lost_equality_reconstruction_is_present(self):
        text = self.study.lost_equality_script().decode("ascii")
        self.assertIn("(define-fun original () Bool (= w9 w1))", text)
        self.assertIn(f"(define-fun residual () Bool (= w9 {self.study.ff_const(7)}))", text)
        self.assertIn("(assert (or (and original (not residual))", text)

    def test_baseline_changes_only_model_projection(self):
        for obligation in self.study.OBLIGATIONS:
            parent = self.study.parent_for(self.specializer, obligation)
            data, core_hash = self.study.baseline_instrumented(
                parent, self.witnesses, obligation == "cone"
            )
            self.assertTrue(data.endswith(b"))\n"))
            if obligation == "cone":
                expected = parent["producer_prefix"] + b"(check-sat)\n"
            else:
                expected = b"".join(parent["raw"].splitlines(keepends=True)[:-1])
            self.assertEqual(core_hash, self.study.sha256_bytes(expected))
            self.assertTrue(data.startswith(expected))

    def test_triviality_classes_cover_cells_without_changing_goal(self):
        counts = self.study.Counter()
        for cell in self.specializer.cell_pairs():
            for obligation in self.study.OBLIGATIONS:
                counts[(obligation, self.study.triviality(obligation, cell))] += 1
        self.assertEqual(counts[("cone", "no_goal")], 25)
        self.assertEqual(sum(value for (obligation, _), value in counts.items()
                             if obligation == "nonvacuous"), 25)
        self.assertEqual(sum(value for (obligation, _), value in counts.items()
                             if obligation == "prefix"), 25)
        self.assertEqual(sum(value for (obligation, _), value in counts.items()
                             if obligation == "tail"), 25)

    def test_original_model_checker_accepts_a_small_valid_component(self):
        indexed = [
            (1, ("assert", [(1, [1]), (-1, [])])),
            (2, ("range", [(1, [1])], 1)),
            (3, ("init", 0, [[(1, [1])]])),
            (4, ("read", 0, [(1, [2])], [(0, [])])),
        ]
        self.assertEqual(self.study.check_original_cone(indexed, {1: 1, 2: 1}), [])
        self.assertIn("read:4", self.study.check_original_cone(indexed, {1: 1, 2: 0}))

    def test_profile_and_main_schedules_match_frozen_budgets(self):
        self.assertEqual(2 * (1 + len(self.study.CANDIDATES)), 8)
        self.assertEqual(len(self.study.OBLIGATIONS) * 3 * 300, 3600)
        self.assertEqual(25 * self.study.CELL_SECONDS, 300)


if __name__ == "__main__":
    unittest.main()

