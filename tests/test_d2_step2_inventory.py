from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/d2_step2_inventory.py"
SPEC = importlib.util.spec_from_file_location("d2_step2_inventory", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
D2_STEP2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2_STEP2)


class D2Step2InventoryTests(unittest.TestCase):
    def test_tracked_inventory_matches_preserved_evidence(self) -> None:
        checks = D2_STEP2.validate()
        self.assertIn("eligible-population-counts", checks)
        self.assertIn("current-mutant-ledger", checks)
        self.assertIn("historical-attempt-vs-project-reconciliation", checks)

    def test_statuses_are_explicit_and_exhaustive(self) -> None:
        ledger = D2_STEP2._load(D2_STEP2.DEFAULT_LEDGER)
        self.assertEqual(
            set(ledger["compatibility_status_taxonomy"]),
            D2_STEP2.EXPECTED_STATUSES,
        )
        self.assertEqual(sum(ledger["eligible_population"]["status_counts"].values()), 3)


if __name__ == "__main__":
    unittest.main()
