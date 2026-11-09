"""Predeclared follow-up oracle for exact field guards and consumer context."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.p4 import SCALAR_FIELD, canonical_guard


Q = 21888242871839275222246405745257275088696311157297823662689037894645226208583


class FollowupTests(unittest.TestCase):
    def test_position_exact_guards(self) -> None:
        cases = [
            ("function checkField(uint x) pure { if (x >= " + str(SCALAR_FIELD) + ") revert(); } function verify(uint[] calldata _pubSignals) view { checkField(calldataload(add(_pubSignals, 32))); }", {1}, True),
            ("function checkField(uint x) pure { if (x >= " + str(SCALAR_FIELD) + ") revert(); } function verify(uint[] calldata _pubSignals) view { checkField(calldataload(add(_pubSignals, 0))); }", {1}, False),
            ("function checkField(uint x) pure { if (x >= " + str(SCALAR_FIELD) + ") revert(); } function verify(uint[] calldata _pubSignals) view { checkField(calldataload(add(_pubSignals, 64))); }", {2}, True),
            ("function checkField(uint x) pure { if (x >= " + str(Q) + ") revert(); } function verify(uint[] calldata _pubSignals) view { checkField(calldataload(add(_pubSignals, 32))); }", {1}, False),
            ("function checkField(uint x) pure { if (x >= " + str(SCALAR_FIELD) + ") revert(); } function verify(uint[] calldata _pubSignals) view { checkField(42) } function unrelated() { let x := _pubSignals }", {0}, False),
            ("uint256 constant BASE_FIELD = " + str(Q) + "; function verify(uint[] calldata input) view { require(input[1] < BASE_FIELD); }", {1}, False),
            ("uint256 constant SNARK_FIELD = " + str(SCALAR_FIELD) + "; function verify(uint[] calldata input) view { require(input[1] < SNARK_FIELD); }", {1}, True),
        ]
        for source, positions, expected in cases:
            with self.subTest(source=source[:90]):
                self.assertEqual(canonical_guard(source, positions), expected)

    def test_missing_verifier_never_verifies_p3(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Main.nr").write_text("fn main(nullifier: pub Field) {}\n")
            (root / "Consumer.sol").write_text("""
contract Consumer { mapping(uint256 => bool) spent;
function useProof(bytes memory proof, uint256 nullifier) external {
 require(!spent[nullifier]); verifier.verifyProof(proof, [nullifier]);
 spent[nullifier] = true; token.transfer(msg.sender, 1);
}}
""")
            output = analyze(root)
            for triple in output["triples"]:
                p3 = triple["patterns"]["P3"]
                self.assertEqual((p3["verdict"], p3["reason"]), ("UNKNOWN", "VERIFIER_ARTIFACT_MISSING"))

    def test_local_context_and_overrides(self) -> None:
        cases = [
            ("modifier gate() { require(msg.sender != address(0)); _; }", "gate", "VERIFIED_WITHIN_SCOPE"),
            ("modifier gate() { require(msg.sender != address(0)); }", "gate", "UNKNOWN"),
            ("modifier gate() { if (enabled) _; }", "gate", "UNKNOWN"),
            ("modifier gate() { externalTarget.call(\"\"); _; }", "gate", "UNKNOWN"),
            ("contract Base {}", "inherit", "VERIFIED_WITHIN_SCOPE"),
            ("contract Base { function _safeMint(address to, uint256 id) internal virtual {} }", "inherit", "UNKNOWN"),
        ]
        for prefix, mode, expected in cases:
            with self.subTest(prefix=prefix):
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    (root / "Main.nr").write_text("fn main(recipient: pub Field, amount: pub Field) {}\n")
                    (root / "Verifier.sol").write_text("contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) public view returns (bool) { require(input[0] < " + str(SCALAR_FIELD) + "); return true; }}")
                    inheritance = " is Base" if mode == "inherit" else ""
                    suffix = " gate" if mode == "gate" else ""
                    (root / "Consumer.sol").write_text(prefix + f"contract Consumer{inheritance} {{ function submit(bytes memory proof, address recipient, uint256 amount) public{suffix} {{ verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]); _safeMint(recipient, amount); }} }}")
                    result = analyze(root)
                    p1 = next(t["patterns"]["P1"] for t in result["triples"] if t["consumer"]["function"] == "submit")
                    self.assertEqual(p1["verdict"], expected)


if __name__ == "__main__":
    unittest.main()
