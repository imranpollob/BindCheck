"""Prospectively declared source-shape controls for Lane C."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze


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


if __name__ == "__main__":
    unittest.main()
