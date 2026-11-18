from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.circuits import _circom_binary


FIXTURES = pathlib.Path(__file__).with_name("fixtures")
KIRA_CONSUMER = "hardhat/contracts/Tazza.sol"


class ResidualP5Tests(unittest.TestCase):
    def findings_at(self, output, path, line):
        self.assertEqual(output["run"]["status"], "completed")
        findings = [
            triple["patterns"]["P5"]
            for triple in output["triples"]
            if triple["patterns"]["P5"]["location"] == {"path": path, "line": line}
        ]
        self.assertTrue(findings, f"No P5 findings at {path}:{line}")
        self.assertEqual({finding["verdict"] for finding in findings}, {"UNKNOWN"})
        return {finding["reason"] for finding in findings}

    def test_pinned_residuals_remain_unknown(self):
        correspondence = "CIRCUIT_VERIFIER_CORRESPONDENCE_UNRESOLVED"
        vector = "PUBLIC_INPUT_VECTOR_UNRESOLVED"
        cases = [
            ("W0016", "on-chain/contracts/GovernorL1.sol", 155, {correspondence}),
            ("W0220", "contracts/hackergroup.sol", 175, {vector}),
            ("W0253", "contracts/hackergroup.sol", 109, {vector}),
            ("W0333", "HZKA/contracts/ordinary_chain/TransferContract.sol", 296, {correspondence}),
            ("W0349", "contracts/src/AutoBattler.sol", 81, {correspondence, "PUBLIC_INPUT_MEANING_UNRESOLVED"}),
        ]
        for card, path, line, reasons in cases:
            with self.subTest(card=card):
                self.assertEqual(self.findings_at(analyze(FIXTURES / card), path, line), reasons)

    def test_same_basename_artifact_is_not_reused_between_circuits(self):
        circom = _circom_binary()
        if circom is None:
            self.skipTest("Circom is required to generate the real sibling artifact")
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary) / "checkout"
            shutil.copytree(FIXTURES / "W0461", root)
            key_generation = root / "circuits/key_generation"
            subprocess.run(
                [circom, str(key_generation / "circuit.circom"), "--r1cs", "--sym", "-o", str(key_generation)],
                check=True, capture_output=True, text=True, timeout=30,
            )
            output = analyze(root)
            self.assertEqual(
                self.findings_at(output, KIRA_CONSUMER, 61), {"PUBLIC_INPUT_ORDER_UNRESOLVED"},
            )
            deck = next(
                triple["circuit"] for triple in output["triples"]
                if triple["consumer"]["path"] == KIRA_CONSUMER and triple["consumer"]["line"] == 61
            )
            self.assertEqual(deck["public_count"], 18)
            self.assertEqual(deck["compiled_relation"]["build"]["kind"], "compile")

    def test_symbolic_output_extent_without_compiler_is_unknown(self):
        with patch("bindcheck_zk.circuits._circom_binary", return_value=None):
            output = analyze(FIXTURES / "W0461")
        self.assertEqual(
            self.findings_at(output, KIRA_CONSUMER, 61), {"CIRCUIT_INTERFACE_INCOMPLETE"},
        )
