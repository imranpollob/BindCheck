"""Prospectively declared source-shape controls for Lane C."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.p4 import SCALAR_FIELD, analyze_source


def p1(prefix: str, declaration: str, body: str, *, import_line: str = "") -> str:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "Main.nr").write_text("fn main(recipient: pub Field, amount: pub Field) {}\n")
        (root / "Verifier.sol").write_text(
            "contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) "
            "public view returns (bool) { return true; }}"
        )
        (root / "Consumer.sol").write_text(
            import_line + "\n" + prefix + "\n" + declaration + " {\n" + body + "\n}"
        )
        output = analyze(root)
        entries = [t["patterns"]["P1"] for t in output["triples"]
                   if t["consumer"]["function"] == "submit"]
        assert len(entries) == 1, entries
        return entries[0]["verdict"]


def p1_with_verifier(verifier_body: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "Main.nr").write_text("fn main(recipient: pub Field, amount: pub Field) {}\n")
        (root / "Verifier.sol").write_text(
            "contract Groth16Verifier { function verifyProof(bytes memory proof, uint256[2] memory input) "
            "public view returns (bool) { " + verifier_body + " }}"
        )
        (root / "Consumer.sol").write_text("contract Consumer { " + TRANSFER + " }")
        output = analyze(root)
        entries = [t["patterns"]["P1"] for t in output["triples"]
                   if t["consumer"]["function"] == "submit"]
        assert len(entries) == 1, entries
        return entries[0]["verdict"]


TRANSFER = (
    "function submit(bytes memory proof, address recipient, uint256 amount) public { "
    "verifier.verifyProof(proof, [recipient, amount]); token.transfer(recipient, amount); }"
)


class CoverageRules(unittest.TestCase):
    def test_exact_oz_pausable_positive(self) -> None:
        self.assertEqual(p1("", "contract Consumer is Pausable", TRANSFER.replace(" public {", " public whenNotPaused {"),
                            import_line='import "@openzeppelin/contracts/utils/Pausable.sol";'), "VERIFIED_WITHIN_SCOPE")

    def test_oz_pausable_negative_missing_import(self) -> None:
        self.assertEqual(p1("", "contract Consumer is Pausable", TRANSFER.replace(" public {", " public whenNotPaused {")), "UNKNOWN")

    def test_oz_pausable_named_import_positive_and_wrong_package_negative(self) -> None:
        body = TRANSFER.replace(" public {", " public whenNotPaused {")
        self.assertEqual(p1("", "contract Consumer is Pausable", body,
                            import_line='import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";'),
                         "VERIFIED_WITHIN_SCOPE")
        self.assertEqual(p1("", "contract Consumer is Pausable", body,
                            import_line='import {Pausable} from "other/Pausable.sol";'), "UNKNOWN")

    def test_oz_pausable_negative_local_override(self) -> None:
        override = "modifier whenNotPaused() { target.call(\"\"); _; }"
        self.assertEqual(p1("", "contract Consumer is Pausable", override + TRANSFER.replace(" public {", " public whenNotPaused {"),
                            import_line='import "@openzeppelin/contracts/utils/Pausable.sol";'), "UNKNOWN")

    def test_local_lock_positive(self) -> None:
        lock = ("uint256 constant NOT_ENTERED = 1; uint256 constant ENTERED = 2; uint256 _status; "
                "modifier nonReentrant() { require(_status != ENTERED); _status = ENTERED; _; _status = NOT_ENTERED; }")
        self.assertEqual(p1("", "contract Consumer", lock + TRANSFER.replace(" public {", " public nonReentrant {")),
                         "VERIFIED_WITHIN_SCOPE")

    def test_local_lock_negative_shapes(self) -> None:
        head = "uint256 constant NOT_ENTERED = 1; uint256 constant ENTERED = 2; uint256 _status; "
        bodies = [
            "require(_status != ENTERED); _status = ENTERED; _;",
            "require(_status != ENTERED); _status = ENTERED; if (enabled) _; _status = NOT_ENTERED;",
            "require(_status != ENTERED); _status = ENTERED; _; _; _status = NOT_ENTERED;",
            "require(_status != ENTERED); target.call(\"\"); _status = ENTERED; _; _status = NOT_ENTERED;",
            "require(_status != ENTERED); _status = ENTERED; _; _status = ENTERED;",
        ]
        for body in bodies:
            with self.subTest(body=body):
                lock = head + "modifier nonReentrant() { " + body + " }"
                self.assertEqual(p1("", "contract Consumer", lock + TRANSFER.replace(" public {", " public nonReentrant {")),
                                 "UNKNOWN")

    def test_erc721_enumerable_positive(self) -> None:
        mint = ("function submit(bytes memory proof, address recipient, uint256 tokenId) public { "
                "verifier.verifyProof(proof, [recipient, tokenId]); _mint(recipient, tokenId); }")
        self.assertEqual(p1("", "contract Consumer is ERC721Enumerable", mint,
                            import_line='import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";'),
                         "VERIFIED_WITHIN_SCOPE")

    def test_erc721_enumerable_negative_override(self) -> None:
        mint = ("function _mint(address to, uint256 id) internal { target.call(\"\"); } "
                "function submit(bytes memory proof, address recipient, uint256 tokenId) public { "
                "verifier.verifyProof(proof, [recipient, tokenId]); _mint(recipient, tokenId); }")
        self.assertEqual(p1("", "contract Consumer is ERC721Enumerable", mint,
                            import_line='import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";'),
                         "UNKNOWN")

    def test_fail_closed_verifier_cannot_support_p1_positive(self) -> None:
        self.assertEqual(p1_with_verifier("return false;"), "UNKNOWN")
        self.assertEqual(p1_with_verifier("return true;"), "VERIFIED_WITHIN_SCOPE")

    def test_dynamic_wrapper_p4_scalar_guard(self) -> None:
        constants = (
            f"uint256 constant r = {SCALAR_FIELD}; "
            "uint256 constant GAMMAX1=11; uint256 constant GAMMAX2=12; uint256 constant GAMMAY1=13; uint256 constant GAMMAY2=14; "
            "uint256 constant DELTAX1=21; uint256 constant DELTAX2=22; uint256 constant DELTAY1=23; uint256 constant DELTAY2=24; "
        )
        raw = """function _verifyProofRaw(uint256[2] calldata _pubSignals) public view returns (bool) {
 assembly { function checkField(v) { if iszero(lt(v, r)) { mstore(0,0) return(0,0x20) } }
 checkField(calldataload(add(_pubSignals,0))) checkField(calldataload(add(_pubSignals,32))) } return true; }
"""
        wrapper = """function verifyProof(bytes calldata proof, bytes32[] calldata publicInputs) external view returns (bool) {
 if (publicInputs.length != 2) return false;
 try this._decodeAndVerify(proof, publicInputs) returns (bool ok) { return ok; } catch { return false; }}
function _decodeAndVerify(bytes calldata proof, bytes32[] calldata publicInputs) external view returns (bool) {
 uint256[2] memory pub; pub[0] = uint256(publicInputs[0]);
 pub[1] = uint256(publicInputs[1]); return this._verifyProofRaw(pub); }
"""
        self.assertEqual(analyze_source(constants + raw + wrapper, "Verifier.sol")["finding"]["verdict"],
                         "VERIFIED_WITHIN_SCOPE")
        self.assertEqual(analyze_source(constants + raw + wrapper.replace("publicInputs[1]", "publicInputs[0]"),
                                        "Verifier.sol")["finding"]["verdict"], "UNKNOWN")
        self.assertEqual(analyze_source(constants + raw + wrapper.replace("publicInputs.length != 2", "publicInputs.length > 2"),
                                        "Verifier.sol")["finding"]["verdict"], "UNKNOWN")
        self.assertEqual(analyze_source(constants.replace(str(SCALAR_FIELD),
                             "21888242871839275222246405745257275088696311157297823662689037894645226208583")
                             + raw + wrapper, "Verifier.sol")["finding"]["verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
