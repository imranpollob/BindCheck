#!/usr/bin/env python3

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_relation import Extractor  # noqa: E402


LANE = HERE.parents[1]
PAPER = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper")
BUILD = PAPER / "results/raw/D1P-12R/workspace/source/backend/artifacts/build-info/solc-0_8_29-a52609323fd0bce65aec2ea493681a10c5c96cfa.json"
OUTPUT = BUILD.with_suffix(".output.json")
SOURCE = PAPER / "results/raw/D1P-12R/workspace/source/backend/contracts/core/WarpToadCore.sol"


class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.relation = Extractor(BUILD, OUTPUT, SOURCE).extract()

    def test_pin_and_boundary(self):
        self.assertTrue(all(self.relation["pins"]["assertions"].values()))
        boundary = self.relation["verifier_boundary"]
        self.assertEqual(11, len(boundary["public_words"]))
        self.assertIn("uninterpreted producer relation", boundary["kind"])

    def test_public_word_origins(self):
        self.assertEqual(
            [
                "calldata._nullifier", "block.chainid", "calldata._amount",
                "calldata._gigaRoot", "calldata._localRoot",
                "pre.aztecWarptoadAddress", "calldata._feeFactor",
                "calldata._priorityFee", "calldata._maxFee",
                "calldata._relayer", "calldata._recipient",
            ],
            [word["origin"] for word in self.relation["verifier_boundary"]["public_words"]],
        )

    def test_paths_and_rollback(self):
        self.assertEqual(3, self.relation["summary"]["success_paths"])
        self.assertEqual(19, self.relation["summary"]["revert_paths"])
        self.assertTrue(self.relation["summary"]["all_reverts_commit_nothing"])
        for path in self.relation["paths"]:
            if path["status"] == "revert":
                self.assertTrue(path["rollback"])
                self.assertEqual([], path["committed"]["storage_writes"])
                self.assertEqual([], path["committed"]["mints"])

    def test_five_execution_comparison(self):
        command = [
            sys.executable, str(HERE / "compare_executions.py"),
            "--paper-root", str(PAPER), "--build-info", str(BUILD),
            "--compiler-output", str(OUTPUT), "--source", str(SOURCE),
        ]
        completed = subprocess.run(command, cwd=LANE, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        self.assertTrue(report["all_checks_pass"], report["disagreements"])
        self.assertEqual(5, len(report["cases"]))

    def test_manual_comparison_tracks_known_differences(self):
        command = [
            sys.executable, str(HERE / "compare_manual.py"),
            "--paper-root", str(PAPER), "--build-info", str(BUILD),
            "--compiler-output", str(OUTPUT), "--source", str(SOURCE),
        ]
        completed = subprocess.run(command, cwd=LANE, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        self.assertTrue(report["agreements"]["public_word_order"])
        self.assertEqual([], report["comparison_errors"])
        self.assertEqual(
            ["revert precedence and tentative trace", "producer/consumer boundary placement"],
            [item["kind"] for item in report["disagreements"]],
        )


if __name__ == "__main__":
    unittest.main()
