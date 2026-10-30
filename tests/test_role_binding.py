"""Unit tests for the separate D1P-43 typed role-binding interface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bindcheck_d1.role_binding import RoleBindingUnsupported, analyze_role_binding


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbol(name: str) -> dict:
    return {"op": "symbol", "args": [name]}


class RoleBindingTests(unittest.TestCase):
    def make_fixture(
        self,
        directory: Path,
        *,
        producer_call: str = "hash_commitment(secret, amount);",
        public_names: tuple[str, ...] = ("amount", "recipient_address"),
        consumer_origins: tuple[str, ...] = ("calldata._amount", "calldata._recipient"),
        guards: list[dict] | None = None,
        beneficiary: str = "calldata._recipient",
    ) -> tuple[dict, Path, Path]:
        source = directory / "main.nr"
        source.write_text(
            "fn main("
            + ", ".join(f"{name}: pub Field" for name in public_names)
            + ", secret: Field) { " + producer_call + " }\n"
        )
        support = directory / "hashing.nr"
        support.write_text(
            "pub fn hash_commitment(secret: Field, amount: Field) -> Field { secret + amount }\n"
        )
        words = [
            {
                "index": index,
                "origin": origin,
                "expression": origin,
                "expression_ir": symbol(origin),
            }
            for index, origin in enumerate(consumer_origins)
        ]
        relation = {
            "schema": "test.checked-relation/v1",
            "scope": "Test.consume",
            "verifier_boundary": {"public_words": words},
            "paths": [{
                "id": "success",
                "status": "success",
                "guards_ir": guards or [],
                "committed": {
                    "storage_writes": [],
                    "transfers": [],
                    "burns": [],
                    "mints": [{
                        "location": "Test.sol:1",
                        "amount": consumer_origins[0],
                        "amount_ir": symbol(consumer_origins[0]),
                        "beneficiary": beneficiary,
                        "beneficiary_ir": symbol(beneficiary),
                    }],
                },
            }],
        }
        relation_path = directory / "relation.json"
        relation_path.write_text(json.dumps(relation))
        analysis = {
            "schema": "bindcheck.static-analysis.v1.3",
            "producer": {
                "sha256": "producer-hash",
                "public_leaves": [
                    {"path": name, "public_index": index}
                    for index, name in enumerate(public_names)
                ],
            },
            "consumer": {
                "kind": "extracted-relation",
                "source_sha256": "consumer-hash",
                "relation": str(relation_path),
                "relation_sha256": sha256(relation_path),
                "verifier_location": "Test.sol:verify",
                "public_words": words,
            },
        }
        return analysis, source, support

    def test_matching_amount_commitment_and_recipient_effect_are_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(Path(temporary))
            result = analyze_role_binding(
                analysis,
                producer_source=source,
                producer_support_sources=[support],
            )
        self.assertEqual(result["warning_count"], 0)
        self.assertEqual(
            [word["boundary_correspondence"] for word in result["words"]],
            ["match", "match"],
        )

    def test_principal_amount_not_in_commitment_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(
                Path(temporary), producer_call="hash_commitment(secret, 0);"
            )
            result = analyze_role_binding(
                analysis,
                producer_source=source,
                producer_support_sources=[support],
            )
        self.assertEqual(
            [(warning["evidence"]["kind"], warning["evidence"]["public_index"])
             for warning in result["warnings"]],
            [("effect-authorization", 0)],
        )

    def test_state_identity_and_principal_beneficiary_are_typed(self) -> None:
        guards = [{
            "op": "select",
            "args": [
                {"op": "storage", "args": ["gigaRootHistory"]},
                symbol("calldata._localRoot"),
            ],
        }]
        names = ("amount", "destination_local_root", "relayer_address", "recipient_address")
        origins = (
            "calldata._amount", "calldata._localRoot",
            "calldata._relayer", "calldata._recipient",
        )
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(
                Path(temporary),
                public_names=names,
                consumer_origins=origins,
                guards=guards,
                beneficiary="calldata._relayer",
            )
            result = analyze_role_binding(
                analysis,
                producer_source=source,
                producer_support_sources=[support],
            )
        kinds = {warning["evidence"]["kind"] for warning in result["warnings"]}
        self.assertEqual(kinds, {"state-identity", "effect-beneficiary"})

    def test_source_artifact_public_order_mismatch_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(Path(temporary))
            analysis["producer"]["public_leaves"][0]["path"] = "different_amount"
            with self.assertRaisesRegex(
                RoleBindingUnsupported, "PRODUCER_SOURCE_ARTIFACT_ABI_MISMATCH"
            ):
                analyze_role_binding(
                    analysis,
                    producer_source=source,
                    producer_support_sources=[support],
                )

    def test_application_domain_identity_mismatch_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(
                Path(temporary),
                producer_call="",
                public_names=("aztec_warptoad_address",),
                consumer_origins=("pre.other_app_address",),
                beneficiary="external.account",
            )
            result = analyze_role_binding(
                analysis,
                producer_source=source,
                producer_support_sources=[support],
            )
        self.assertEqual(
            [warning["evidence"]["kind"] for warning in result["warnings"]],
            ["domain-identity"],
        )


if __name__ == "__main__":
    unittest.main()
