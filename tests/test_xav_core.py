"""Unit tests for the validation-harness core (no external inputs)."""

import unittest

from bindcheck_d1.xav_core import (
    E1,
    E1_MOCK,
    E3,
    E4,
    E4_PRESERVED,
    check_ledger,
    corrected_grade,
    ledger_counts,
    mint_successes,
    revert_reasons,
)


def row(mutant, warning, e, rule="R-BIND"):
    return {"mutant": mutant, "warning": warning, "rule": rule, "E": e}


class CoreGradingTests(unittest.TestCase):
    def test_mock_rows_are_not_e2(self):
        grade, _ = corrected_grade(row("PY-S01", "W002", "E2 (mock-verifier-scoped)"))
        self.assertEqual(grade, E1_MOCK)

    def test_overrides(self):
        self.assertEqual(corrected_grade(row("PY-C02", "W001", "E4"))[0], E3)
        self.assertEqual(corrected_grade(row("PY-C02", "W002", "E4"))[0], E1)
        self.assertEqual(corrected_grade(row("WT-S02", "W001", "E4"))[0], E4)

    def test_driver_grade_stands_otherwise(self):
        self.assertEqual(corrected_grade(row("WT-C01", "W001", "E4"))[0], E4)
        self.assertEqual(
            corrected_grade(row("WT-C03", "W001", "E4-preserved"))[0], E4_PRESERVED)
        self.assertEqual(corrected_grade(row("WT-C02", "W001", "E3"))[0], E3)
        self.assertEqual(corrected_grade(row("PY-C01", "W001", "E1"))[0], E1)

    def test_counts_and_length_gate(self):
        results = [row("WT-C01", "W001", "E4"), row("WT-C03", "W001", "E4-preserved"),
                   row("WT-C02", "W001", "E3"),
                   row("PY-S01", "W002", "E2 (mock-verifier-scoped)"),
                   row("PY-C01", "W001", "E1")]
        counts = ledger_counts(results)
        self.assertEqual(counts[E4], 1)
        self.assertEqual(counts[E1_MOCK], 1)
        with self.assertRaises(AssertionError):
            check_ledger(results)  # not 53 rows

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            ledger_counts([row("X", "W1", "E9")])


class EffectPredicateTests(unittest.TestCase):
    def test_mint_successes(self):
        rep = {"steps": [{"mint_0": {"status": "success"}}, {"mint_1": "REVERT"}]}
        self.assertEqual(mint_successes(rep), [True])

    def test_revert_reasons(self):
        rep = {"reverts": [{"mint_0": "nullifier already exists"}],
               "revert_tag": "Mint value invalid"}
        reasons = revert_reasons(rep)
        self.assertIn("nullifier already exists", list(reasons.values())[0])
        self.assertTrue(reasons["revert_tag"].startswith("Mint value"))


if __name__ == "__main__":
    unittest.main()
