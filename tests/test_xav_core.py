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
    warning_key,
)


def row(mutant, warning, e, rule="R-BIND"):
    return {"mutant": mutant, "warning": warning, "rule": rule, "E": e}


class CoreGradingTests(unittest.TestCase):
    def test_mock_rows_are_not_e2(self):
        grade, _ = corrected_grade(
            row("PY-S04", "W002", "E2 (mock-verifier-scoped)"))
        self.assertEqual(grade, E1_MOCK)

    def test_lifted_rows_grade_e4(self):
        for mutant, wid, exp in (("PY-S01", "W002", E4),
                                 ("PY-S01", "W004", E4),
                                 ("PY-S03", "W002", E4)):
            grade, _ = corrected_grade(
                row(mutant, wid, "E2 (mock-verifier-scoped)"))
            self.assertEqual(grade, exp)

    def test_s02_pair_grade_e3(self):
        for mutant, wid in (("PY-S02", "W002"), ("PY-S02", "W004")):
            grade, basis = corrected_grade(
                row(mutant, wid, "E2 (mock-verifier-scoped)"))
            self.assertEqual(grade, E3)
            self.assertIn("circuit", basis)

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
                   row("PY-S04", "W002", "E2 (mock-verifier-scoped)"),
                   row("PY-C01", "W001", "E1")]
        counts = ledger_counts(results)
        self.assertEqual(counts[E4], 1)
        self.assertEqual(counts[E1_MOCK], 1)
        with self.assertRaises(AssertionError):
            check_ledger(results)  # not 53 rows

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            ledger_counts([row("X", "W1", "E9")])


class WarningKeyTests(unittest.TestCase):
    def test_rbind_key(self):
        w = {"rule": "R-BIND", "location": "withdraw.json:abi.nullifier",
             "evidence": {}}
        self.assertEqual(warning_key("WT-C01", w),
                         ("WT-C01", "R-BIND", "nullifier", "unbound"))

    def test_reffect_key_ranges_paths(self):
        w = {"rule": "R-EFFECT", "location": "RollupV1.sol:850",
             "evidence": {"paths": ["messages[0]", "messages[999]"],
                          "effect_kinds": ["token-transfer", "storage-write"]}}
        self.assertEqual(
            warning_key("PY-C02", w),
            ("PY-C02", "R-EFFECT", "messages[0..999]",
             "storage-write+token-transfer"))

    def test_rconsumer_key(self):
        w = {"rule": "R-CONSUMER", "location": "WarpToadCore.sol:?",
             "evidence": {"path": "giga_root"}}
        self.assertEqual(warning_key("WT-S02", w),
                         ("WT-S02", "R-CONSUMER", "giga_root",
                          "no-downstream-use"))

    def test_rpolarity_key(self):
        w = {"rule": "R-POLARITY", "location": "RollupV1.sol:357",
             "evidence": {"polarity": "must-not-be-in"}}
        self.assertEqual(warning_key("PY-S01", w),
                         ("PY-S01", "R-POLARITY", "single-use",
                          "must-not-be-in"))

    def test_keyed_override_ignores_warning_id(self):
        # v2.0 renumbering must not break adjudication: same semantic key,
        # different id.
        w = {"id": "W007", "rule": "R-BIND",
             "location": "agg_agg.json:abi.messages[0]..messages[999]",
             "evidence": {}}
        grade, _ = corrected_grade(
            {"mutant": "PY-C02", "warning": "W007", "E": "E4"}, w)
        self.assertEqual(grade, E3)


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
