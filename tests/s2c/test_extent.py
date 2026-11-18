import pathlib
import tempfile
import unittest

from bindcheck_zk.analyzer import analyze
from bindcheck_zk.extent import PATTERN


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = """
pragma solidity ^0.8.11;

interface ProofCheck {
    function verifyProof(bytes calldata proof, uint256[2] calldata words)
        external view returns (bool);
}

interface Sink {
    function record(uint256 value) external;
}

contract Consumer {
    ProofCheck private verifier;
    Sink private sink;
    mapping(uint256 => uint256) private settled;

    function submit(bytes calldata proof, uint256[4] calldata rows, uint256 count, uint256 tag)
        external
    {
        GUARD
        uint256 commitment = uint256(keccak256(abi.encode(rows)));
        require(verifier.verifyProof(proof, [commitment, PUBLIC_WORD]), "proof");
        for (uint256 i = 0; i < BOUND; ++i) {
            EFFECT
        }
    }

    function readLimit() internal view returns (uint256) {
        return settled[0];
    }
}
"""


class ExtentRuleTests(unittest.TestCase):
    def check_source(self, *, guard="", bound="count", word="tag",
                     effect="settled[rows[i]] += 1;", substitute=None):
        text = (
            FIXTURE.replace("GUARD", guard)
            .replace("BOUND", bound)
            .replace("PUBLIC_WORD", word)
            .replace("EFFECT", effect)
        )
        if substitute:
            text = text.replace(*substitute)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "Batch.sol").write_text(text, encoding="utf-8")
            output = analyze(root, explicit_consumers=["Batch.sol"])
        self.assertEqual(output["run"]["status"], "completed")
        finding, = output["extent_findings"]
        self.assertEqual(finding["verdict"], output["patterns"][PATTERN]["verdict"])
        return finding

    def test_az1_faulty_and_fixed(self):
        for variant, verdict, reason in (
            ("Faulty", "VIOLATION", "EXTENT_CALLDATA_PREFIX_SHORTER_THAN_COMMITMENT"),
            ("Fixed", "VERIFIED_WITHIN_SCOPE", "EXTENT_TAIL_CHECKED_NEUTRAL"),
        ):
            with self.subTest(variant=variant):
                path = f"contracts/Settlement{variant}.sol"
                output = analyze(ROOT / "prototypes" / "az1", explicit_consumers=[path])
                finding, = output["extent_findings"]
                self.assertEqual(output["patterns"][PATTERN]["verdict"], verdict)
                self.assertEqual(finding["reason"], reason)
                self.assertEqual(finding["evidence_grade"], "E1")
                self.assertEqual(finding["location"]["path"], path)
                line = (ROOT / "prototypes" / "az1" / path).read_text().splitlines()
                self.assertIn("i < numRealRows", line[finding["location"]["line"] - 1])
                self.assertEqual(finding["facts"][0]["length"], 4)

    def test_bound_equality(self):
        for guard in ("require(count == 4);", "require(count >= 4 && count <= rows.length);"):
            with self.subTest(guard=guard):
                finding = self.check_source(guard=guard)
                self.assertEqual(finding["reason"], "EXTENT_BOUND_EQUALS_COMMITMENT")
                self.assertEqual(finding["verdict"], "VERIFIED_WITHIN_SCOPE")

    def test_fixed_array_length_bound(self):
        finding = self.check_source(bound="rows.length")
        self.assertEqual(finding["verdict"], "VERIFIED_WITHIN_SCOPE")

    def test_opaque_bound(self):
        finding = self.check_source(guard="uint256 limit = readLimit();", bound="limit")
        self.assertEqual(finding["reason"], "EXTENT_BOUND_SOURCE_UNSUPPORTED")
        self.assertEqual(finding["unknown_reason_code"], "UNSUPPORTED_CONSTRUCT")

    def test_calldata_copy_and_interface_effect(self):
        finding = self.check_source(
            guard="uint256 limit = count; require(limit <= 4);",
            bound="limit",
            effect="sink.record(rows[i]);",
            substitute=(
                'require(verifier.verifyProof(proof, [commitment, tag]), "proof");',
                'uint256[2] memory words = [commitment, tag];\n'
                '        require(verifier.verifyProof(proof, words), "proof");',
            ),
        )
        self.assertEqual(finding["verdict"], "VIOLATION")
        self.assertEqual(finding["facts"][1]["source"], "count")

    def test_authenticated_count_is_not_an_unbound_prefix(self):
        finding = self.check_source(word="count")
        self.assertEqual(finding["reason"], "EXTENT_BOUND_BINDING_UNRESOLVED")

    def test_public_count_derived_through_cast_aliases(self):
        finding = self.check_source(
            guard="require(count <= 4); uint8 smaller = uint8(count);",
            word="uint256(smaller)",
        )
        self.assertEqual(finding["reason"], "EXTENT_BOUND_BINDING_UNRESOLVED")

    def test_opaque_verifier_argument_is_unresolved(self):
        finding = self.check_source(substitute=("verifyProof(proof, [", "verifyProof(bytes.concat(proof), ["))
        self.assertEqual(finding["reason"], "EXTENT_PUBLIC_VECTOR_UNSUPPORTED")

    def test_conditional_equality_is_not_verified(self):
        finding = self.check_source(guard="if (tag == 1) { require(count == 4); }")
        self.assertEqual(finding["verdict"], "UNKNOWN")

    def test_contradictory_guard_is_not_verified(self):
        finding = self.check_source(guard="require(count == 4 && count < 4);")
        self.assertEqual(finding["verdict"], "UNKNOWN")

    def test_partial_tail_guard_is_not_verified(self):
        finding = self.check_source(
            guard="",
            effect="if (rows[i] == 1) { settled[rows[i]] += 1; }",
            substitute=(
                "for (uint256 i = 0; i < count; ++i)",
                "for (uint256 j = count; j < 3; ++j) { require(rows[j] == 0); }\n"
                "        for (uint256 i = 0; i < count; ++i)",
            ),
        )
        self.assertEqual(finding["reason"], "EXTENT_TAIL_CONTROL_UNSUPPORTED")

    def test_mutated_bound_is_unresolved(self):
        finding = self.check_source(
            guard="uint256 limit = count; require(limit == 4); limit = 1;",
            bound="limit",
        )
        self.assertEqual(finding["verdict"], "UNKNOWN")
