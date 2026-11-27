#!/usr/bin/env python3
"""Deterministic synthetic regression tests for the three feasibility checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from feasibility.scan_candidates import analyze_repo, parse_circuit
from feasibility.solc_ast_probe import probe


CIRCUIT = """
pragma circom 2.1.6;
template Withdraw() {
  signal input secret;
  signal output recipient;
  signal output amount;
  signal output nullifierHash;
  recipient <-- secret;
  amount <== secret * secret;
  nullifierHash <== secret + 1;
}
component main = Withdraw();
"""

VERIFIER = """
pragma solidity ^0.8.20;
// Generated with snarkjs. Markers: verifyingKey, SNARK_SCALAR_FIELD.
contract WithdrawVerifier {
  function verifyProof(
    uint256[2] calldata, uint256[2][2] calldata, uint256[2] calldata,
    uint256[2] calldata input
  ) external pure returns (bool) { return input.length == 2; }
}
"""

CONSUMER = """
pragma solidity ^0.8.20;
interface IVerifier {
  function verifyProof(uint256[2] calldata, uint256[2][2] calldata,
    uint256[2] calldata, uint256[3] calldata) external returns (bool);
}
contract WithdrawPool {
  IVerifier verifier;
  function withdraw(uint256 recipient, uint256 amount, uint256 nullifierHash) external {
    verifier.verifyProof([uint256(0),0], [[uint256(0),0],[uint256(0),0]],
      [uint256(0),0], [recipient, amount, nullifierHash]);
    payable(address(uint160(recipient))).transfer(amount);
  }
}
"""


class FeasibilityChecks(unittest.TestCase):
    def test_a_b_and_c_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "withdraw.circom").write_text(CIRCUIT, encoding="utf-8")
            (root / "WithdrawVerifier.sol").write_text(VERIFIER, encoding="utf-8")
            (root / "WithdrawPool.sol").write_text(CONSUMER, encoding="utf-8")
            candidate = analyze_repo("synthetic/regression", "owned-fixture", root)
            self.assertTrue(candidate.checks["A"], candidate)
            self.assertTrue(candidate.checks["B"], candidate)
            self.assertTrue(candidate.checks["C"], candidate)

    def test_field_alias_is_reported_despite_spent_mapping(self) -> None:
        verifier = VERIFIER.replace("uint256[2] calldata input", "uint256[3] calldata input").replace(
            "input.length == 2", "input.length == 3"
        )
        consumer = CONSUMER.replace(
            "IVerifier verifier;",
            "IVerifier verifier; mapping(uint256 => bool) spent;",
        ).replace(
            "verifier.verifyProof(",
            "require(!spent[nullifierHash]); spent[nullifierHash] = true; verifier.verifyProof(",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "withdraw.circom").write_text(CIRCUIT, encoding="utf-8")
            (root / "WithdrawVerifier.sol").write_text(verifier, encoding="utf-8")
            (root / "WithdrawPool.sol").write_text(consumer, encoding="utf-8")
            candidate = analyze_repo("synthetic/field-alias", "owned-fixture", root)
            self.assertTrue(
                any("canonical" in finding for finding in candidate.checks["B"]),
                candidate,
            )

    def test_solc_ast_extracts_cross_layer_consumer_facts(self) -> None:
        consumer = CONSUMER.replace(
            "IVerifier verifier;",
            "IVerifier verifier; mapping(uint256 => bool) spent;",
        ).replace(
            "verifier.verifyProof(",
            "require(!spent[nullifierHash]); spent[nullifierHash] = true; verifier.verifyProof(",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "WithdrawVerifier.sol").write_text(VERIFIER, encoding="utf-8")
            (root / "WithdrawPool.sol").write_text(consumer, encoding="utf-8")
            result = probe(
                "solc", root, ["WithdrawVerifier.sol", "WithdrawPool.sol"]
            )
            self.assertEqual(result["status"], "ast", result)
            facts = result["facts"]
            self.assertIn(3, facts["consumer_public_input_arities"])
            self.assertIn("spent", facts["replay_index_reads"])
            self.assertIn("spent", facts["replay_index_writes"])
            self.assertIn("transfer", facts["effect_calls"])

    def test_compile_time_false_branch_does_not_add_public_outputs(self) -> None:
        circuit = """
        pragma circom 2.1.5;
        template Conditional(exposeExtra) {
          signal input address;
          signal output first;
          signal output second;
          first <== address;
          second <== address + 1;
          if (exposeExtra) {
            signal output extra[9];
          }
        }
        component main { public [address] } = Conditional(0);
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "conditional.circom"
            path.write_text(circuit, encoding="utf-8")
            fact = parse_circuit(path, root)
            self.assertEqual(fact.public_signals, ["first", "second", "address"])
            self.assertEqual(fact.signal_count, 3)
            self.assertIn("pruned-static-if:exposeExtra=0", fact.parse_notes)


if __name__ == "__main__":
    unittest.main()
