"""Solver-free controls for the D1P-04 SMT specializer."""

from pathlib import Path
import tempfile
import unittest

from scripts import d1p_04_specialize as S


class SpecializerTests(unittest.TestCase):
    def test_all_frozen_parents_and_family_boundaries(self):
        parsed = {key: S.parse_parent(*key) for key in S.EXPECTED_PARENTS}
        for family in ("check_added", "running_flag"):
            members = [parsed[(family, query)] for query in ("nonvacuous", "prefix", "tail")]
            self.assertEqual(len({item["producer_prefix_hash"] for item in members}), 1)
            self.assertEqual(len({item["walk_hash"] for item in members}), 1)

    def test_25_cells_and_payload_rank_mapping(self):
        cells = list(S.cell_pairs())
        self.assertEqual(len(cells), 25)
        self.assertEqual(len({cell["id"] for cell in cells}), 25)
        cell = next(cell for cell in cells
                    if cell["left"] == "length_4" and cell["right"] == "length_5")
        payload = S.payload_map(cell)
        self.assertEqual([(x["rank"], x["stream"], x["offset"]) for x in payload],
                         [(i, 0, i) for i in range(4)] + [(4+i, 1, i) for i in range(5)])
        self.assertTrue(payload[-1]["overflow"])

    def test_specialized_goal_edges(self):
        cells = list(S.cell_pairs())
        zero = cells[0]
        eight = next(c for c in cells if c["left_length"] == 0 and c["right_length"] == 8)
        overflow = next(c for c in cells if c["total_length"] == 9)
        self.assertEqual(S.specialized_goal("nonvacuous", zero), "false")
        self.assertEqual(S.specialized_goal("nonvacuous", eight), "true")
        self.assertEqual(S.specialized_goal("nonvacuous", overflow), "false")
        self.assertEqual(S.specialized_goal("prefix", overflow), "true")
        self.assertEqual(S.specialized_goal("tail", eight), "false")

    def test_output_preserves_complete_producer_prefix(self):
        parent = S.parse_parent("check_added", "prefix")
        cell = next(S.cell_pairs())
        output = S.specialized_text(parent, cell)
        n = parent["producer_prefix_bytes"]
        self.assertEqual(output[:n], parent["producer_prefix"])
        self.assertEqual(S.sha256_bytes(output[:n]), parent["producer_prefix_hash"])

    def test_equivalence_query_excludes_producer_assertions_and_goal_premise(self):
        parent = S.parse_parent("running_flag", "tail")
        data = S.equivalence_text(parent, next(S.cell_pairs())).decode("ascii")
        self.assertEqual(data.count("(assert "), 1)
        self.assertIn("d1p04_original_not_specialized", data)
        self.assertIn("d1p04_specialized_not_original", data)
        self.assertNotIn(parent["producer_prefix"].decode("ascii")[3:], data)

    def test_parent_tamper_rejected(self):
        parent = S.PARENT_ROOT / "check_added/nonvacuous.smt2"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.smt2"
            changed.write_bytes(parent.read_bytes() + b"; changed\n")
            with self.assertRaises(ValueError):
                S.parse_parent("check_added", "nonvacuous", changed)


if __name__ == "__main__":
    unittest.main()
