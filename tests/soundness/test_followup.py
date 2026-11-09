"""Predeclared follow-up oracle for exact field guards and consumer context."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.p4 import SCALAR_FIELD, analyze_source, canonical_guard
from bindcheck_zk.solidity import effect_calls, effect_roles


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
            ("uint256 constant r = " + str(SCALAR_FIELD) + "; function verifyProof(uint[] calldata _pubSignals) view { assembly { function checkField(v) { if iszero(lt(v, r)) { } return(0, 0x20) } checkField(calldataload(add(_pubSignals, 0))) } }", {0}, False),
            ("uint256 constant r = " + str(SCALAR_FIELD) + "; function checkField(v) { if iszero(lt(v, r)) { return(0, 0x20) } } function unrelated(uint[] calldata _pubSignals) { checkField(calldataload(add(_pubSignals, 0))) } function verifyProof(uint[] calldata _pubSignals) { }", {0}, False),
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

    def test_missing_verifier_never_verifies_p2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Main.nr").write_text("fn main(domain: pub Field, amount: pub Field) {}\n")
            (root / "Consumer.sol").write_text("""
contract Consumer { function submit(bytes memory proof, uint256 domain, uint256 amount) external {
 verifier.verifyProof(proof, [domain, amount]); token.transfer(msg.sender, amount);
}}
""")
            output = analyze(root)
            for triple in output["triples"]:
                p2 = triple["patterns"]["P2"]
                self.assertEqual((p2["verdict"], p2["reason"]), ("UNKNOWN", "VERIFIER_ARTIFACT_MISSING"))

    def test_missing_circuit_or_verifier_implementation_never_verifies(self) -> None:
        for circuit_present, interface_only in [(False, False), (True, True)]:
            with self.subTest(circuit_present=circuit_present, interface_only=interface_only):
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    if circuit_present:
                        (root / "Main.nr").write_text("fn main(domain: pub Field, nullifier: pub Field) {}\n")
                    verifier = ("interface IVerifier { function verifyProof(bytes memory proof, uint256[2] memory input) external view returns (bool); }"
                                if interface_only else
                                "contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) public view returns (bool) { require(input[1] < " + str(SCALAR_FIELD) + "); return true; }}")
                    (root / "Verifier.sol").write_text(verifier)
                    (root / "Consumer.sol").write_text("""
contract Consumer { mapping(uint256 => bool) spent;
function submit(bytes memory proof, uint256 domain, uint256 nullifier) external {
 require(!spent[nullifier]); verifier.verifyProof(proof, [domain, nullifier]);
 spent[nullifier] = true; token.transfer(msg.sender, nullifier);
}}
""")
                    output = analyze(root)
                    for triple in output["triples"]:
                        for pattern in ("P1", "P2", "P3"):
                            self.assertEqual(triple["patterns"][pattern]["verdict"], "UNKNOWN")
                        if interface_only:
                            self.assertEqual(triple["patterns"]["P5"]["verdict"], "UNKNOWN")

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

    def test_standard_token_internal_effect_roles(self) -> None:
        cases = [
            ("contract T is ERC20 {}", "_transfer(sender, recipient, amount);", [("recipient", "recipient"), ("amount", "amount")]),
            ("contract T is ERC721 {}", "_transfer(sender, recipient, tokenId);", [("recipient", "recipient")]),
            ("contract T is ERC721 {}", "_safeMint(recipient, tokenId);", [("recipient", "recipient")]),
        ]
        for source, body, expected in cases:
            with self.subTest(body=body, source=source):
                found = effect_calls(body, source)
                self.assertEqual(len(found), 1)
                self.assertEqual(effect_roles(found[0], source), expected)

    def test_local_replay_guard_is_exact_and_unconditional(self) -> None:
        guards = [
            ("require(uint256(nullifierHash) < SNARK_FIELD);", "VERIFIED_WITHIN_SCOPE"),
            ("require(uint256(nullifierHash) < SNARK_FIELD || true);", "VIOLATION"),
            ("if (choose) require(uint256(nullifierHash) < SNARK_FIELD);", "VIOLATION"),
            ("require(uint256(nullifierHash) < BASE_FIELD);", "VIOLATION"),
        ]
        for guard, expected in guards:
            with self.subTest(guard=guard):
                with tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    (root / "Main.nr").write_text("fn main(nullifier: pub Field) {}\n")
                    (root / "Verifier.sol").write_text("contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[1] memory input) public view returns (bool) { return true; }}")
                    (root / "Consumer.sol").write_text(f"""
contract Consumer {{
 uint256 constant SNARK_FIELD = {SCALAR_FIELD}; uint256 constant BASE_FIELD = {Q};
 mapping(bytes32 => bool) nullifierSpent;
 function submit(bytes memory proof, bytes32 nullifierHash, bool choose) external {{
 {guard} require(!nullifierSpent[nullifierHash]);
 uint256[1] memory pubSignals; pubSignals[0] = uint256(nullifierHash);
 verifier.verifyProof(proof, pubSignals); nullifierSpent[nullifierHash] = true;
 token.transfer(msg.sender, 1);
 }}
}}
""")
                    output = analyze(root)
                    for triple in output["triples"]:
                        self.assertEqual(triple["patterns"]["P3"]["verdict"], expected)

    def test_key_constants_without_verifier_are_unknown(self) -> None:
        source = "uint256 constant GAMMAX1 = 1; uint256 constant GAMMAX2 = 2; uint256 constant GAMMAY1 = 3; uint256 constant GAMMAY2 = 4; uint256 constant DELTAX1 = 5; uint256 constant DELTAX2 = 6; uint256 constant DELTAY1 = 7; uint256 constant DELTAY2 = 8;"
        finding = analyze_source(source, "KeyConstants.sol")["finding"]
        self.assertEqual(finding["verdict"], "UNKNOWN")

    def test_ambiguous_repository_base_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Main.nr").write_text("fn main(recipient: pub Field, amount: pub Field) {}\n")
            (root / "Verifier.sol").write_text("contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) public view returns (bool) { return true; }}")
            (root / "BaseA.sol").write_text("contract Base {}")
            (root / "BaseB.sol").write_text("contract Base { function _safeMint(address to, uint256 id) internal {} }")
            (root / "Consumer.sol").write_text("contract Consumer is Base { function submit(bytes memory proof, address recipient, uint256 amount) public { verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]); _safeMint(recipient, amount); }}")
            output = analyze(root)
            for triple in output["triples"]:
                if triple["consumer"]["function"] == "submit":
                    self.assertEqual(triple["patterns"]["P1"]["verdict"], "UNKNOWN")

    def test_unimported_repository_base_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Main.nr").write_text("fn main(recipient: pub Field, amount: pub Field) {}\n")
            (root / "Verifier.sol").write_text("contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) public view returns (bool) { return true; }}")
            (root / "Base.sol").write_text("contract Base {}")
            (root / "Consumer.sol").write_text("contract Consumer is Base { function submit(bytes memory proof, address recipient, uint256 amount) public { verifier.verifyProof(proof, [uint256(uint160(recipient)), amount]); _safeMint(recipient, amount); }}")
            output = analyze(root)
            for triple in output["triples"]:
                if triple["consumer"]["function"] == "submit":
                    self.assertEqual(triple["patterns"]["P1"]["verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
