"""Focused controls for the solver-free D1P-03 partition checker."""
import ast
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import d1p_03_partition_check as check


class PartitionControls(unittest.TestCase):
    def setUp(self):
        self.records = check.load_records()

    def test_five_classes_cover_boundary_examples(self):
        examples = (
            (False, (2,) * 8, "inactive"),
            (True, (0,) * 8, "active_empty"),
            (True, (2, 1, 1, 1, 0, 1, 1, 1), "length_4"),
            (True, (3, 1, 1, 1, 1, 0, 1, 1), "length_5"),
            (True, (4, 1, 1, 1, 1, 2, 1, 1), "truncated_8"),
        )
        for active, words, expected in examples:
            with self.subTest(expected=expected):
                self.assertEqual(check.classify(words, active, self.records), expected)
                self.assertEqual(
                    check.specialized_walk(expected),
                    check.reference_walk(words, active, self.records),
                )

    def test_truncated_records_include_exact_and_overflow_lengths(self):
        for words, expected in (
            ((2, 0, 0, 0, 2, 0, 0, 0), 8),
            ((2, 0, 0, 0, 3, 0, 0, 0), 9),
            ((3, 0, 0, 0, 0, 4, 0, 0), 10),
        ):
            self.assertEqual(check.classify(words, True, self.records), "truncated_8")
            self.assertEqual(check.logical_truncated_length(words, self.records), expected)

    def test_goal_edges_at_eight_and_overflow(self):
        for total in (0, 4, 5, 8, 9, 10, 12, 13, 16):
            for bits in (0, 1, 0x80, 0x55, 0xFF):
                self.assertEqual(
                    check.reference_goals(total, bits),
                    check.specialized_goals(total, bits),
                )

    def test_checker_has_no_process_launch_import(self):
        tree = ast.parse((ROOT / "scripts/d1p_03_partition_check.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue({"subprocess", "multiprocessing"}.isdisjoint(imported))


if __name__ == "__main__":
    unittest.main()
