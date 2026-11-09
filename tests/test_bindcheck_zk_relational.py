from __future__ import annotations

import collections
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from bindcheck_zk.relational import analyze_relational
from tests.relational.fixtures import write_fixture


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "tests" / "relational" / "expected.json").read_text(encoding="utf-8"))


class RelationalControls(unittest.TestCase):
    def require_circom(self) -> str:
        configured = os.environ.get("BINDCHECK_CIRCOM")
        if not configured or not pathlib.Path(configured).is_file():
            self.skipTest("BINDCHECK_CIRCOM must name the pinned Circom binary")
        return configured

    def test_expectations_are_balanced_and_frozen(self) -> None:
        self.assertTrue(EXPECTED["frozen_before_case_or_rule_implementation"])
        counts = collections.Counter(
            (case["dimension"], case["expected_verdict"])
            for case in EXPECTED["cases"]
        )
        self.assertEqual(40, len(EXPECTED["cases"]))
        for dimension in EXPECTED["dimensions"]:
            self.assertEqual(4, counts[(dimension, "VIOLATION")])
            self.assertEqual(4, counts[(dimension, "VERIFIED_WITHIN_SCOPE")])

    def test_all_relational_outcomes(self) -> None:
        self.require_circom()
        for case in EXPECTED["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temp_name:
                root = pathlib.Path(temp_name)
                write_fixture(root, case["fixture"])
                output = analyze_relational(root, dimensions={case["dimension"]})
                self.assertIsNone(output["run"]["fatal_reason"], output)
                self.assertEqual(1, output["coverage"]["compiled_relations"], output)
                self.assertEqual(1, output["coverage"]["paired_paths"], output)
                finding = output["pairs"][0]["dimensions"][case["dimension"]]
                self.assertEqual(case["expected_verdict"], finding["verdict"], finding)
                self.assertEqual(case["expected_reason"], finding["reason"], finding)

    def test_cli_dimension_switch_selects_only_extent(self) -> None:
        self.require_circom()
        with tempfile.TemporaryDirectory() as temp_name:
            root = pathlib.Path(temp_name)
            write_fixture(root, "extent_bridge_withdrawal_vulnerable")
            completed = subprocess.run(
                [str(ROOT / "bindcheck-zk"), "analyze", str(root), "--relational", "--relational-extent"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
                env=os.environ.copy(),
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(["EXTENT"], payload["relational"]["inputs"]["enabled_dimensions"])
            self.assertEqual("VIOLATION", payload["relational"]["dimensions"]["EXTENT"]["verdict"])


if __name__ == "__main__":
    unittest.main()
