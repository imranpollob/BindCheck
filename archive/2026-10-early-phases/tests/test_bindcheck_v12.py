from __future__ import annotations

import json
from pathlib import Path
import unittest

from bindcheck_d1.static_analyzer_v1 import (
    _effect_warning_location,
    _reported_boundary_location,
    load_producer,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "results/raw/D1P-35/version-fixtures"


class BindCheckV12VersionTests(unittest.TestCase):
    def test_development_fixture_matches_beta14_and_beta22(self):
        signatures = {}
        for version in range(14, 23):
            artifact = (FIXTURES / f"beta{version}/target/bindcheck_version_fixture.json")
            with self.subTest(version=version):
                self.assertTrue(artifact.is_file())
                result = load_producer(artifact)
                signatures[version] = {
                    "opcode_counts": result["opcode_counts"],
                    "public_leaves": [
                        (item["path"], item["public_index"], item["witness"],
                         item["occurrence_count"])
                        for item in result["public_leaves"]
                    ],
                }
        reference = {
            "opcode_counts": {"AssertZero": 1},
            "public_leaves": [("left", 0, 0, 1), ("right", 1, 1, 1)],
        }
        self.assertEqual(signatures[14], reference)
        self.assertEqual(signatures[22], reference)
        self.assertTrue(all(item == reference for item in signatures.values()))

    def test_beta3_development_fixture_remains_unsupported(self):
        artifact = FIXTURES / "beta3/target/bindcheck_version_fixture.json"
        with self.assertRaisesRegex(ValueError, "unsupported Noir compiler"):
            load_producer(artifact)


class BindCheckV12LocationTests(unittest.TestCase):
    def test_missing_boundary_line_is_recovered_from_recorded_signature(self):
        source = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol"
        relation = json.loads((ROOT / "results/raw/D1P-18/relation.json").read_text())
        self.assertEqual(_reported_boundary_location(source, relation), "WarpToadCore.sol:161")

    def test_ambiguous_boundary_call_fails_closed_to_unknown_line(self):
        relation = {"verifier_boundary": {
            "declaration": "source.sol::IProof::check(bytes,bytes32[])",
        }}
        source = ROOT / "tests/d1/fixtures/noir_versions/src/main.nr"
        self.assertEqual(_reported_boundary_location(source, relation), "main.nr:?")

    def test_effect_location_prefers_existing_external_effect_dependency(self):
        consumer = {
            "verifier_location": "Consumer.sol:10",
            "public_words": [{"index": 2, "origin": "calldata.amount"}],
            "effects": [
                {"kind": "storage-write", "words": [2], "location": "Consumer.sol:20"},
                {"kind": "token-transfer", "words": [2], "location": "Consumer.sol:30"},
            ],
        }
        self.assertEqual(_effect_warning_location(consumer, [2]), "Consumer.sol:30")


if __name__ == "__main__":
    unittest.main()
