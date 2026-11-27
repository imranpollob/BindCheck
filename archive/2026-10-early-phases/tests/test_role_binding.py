"""Unit tests for the separate D1P-43 typed role-binding interface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from bindcheck_d1.role_binding import (
    LEGACY_SURFACE_ROLE_STATUS,
    RoleBindingUnsupported,
    analyze_role_binding,
    canonical_role,
)
from bindcheck_d1.roles.compiler_identity_v1 import (
    CompilerProvenance,
    ContextIdentity,
    IdentityBundle,
    IdentityRecord,
    ObjectIdentity,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbol(name: str) -> dict:
    return {"op": "symbol", "args": [name]}


class RoleBindingTests(unittest.TestCase):
    def identity_bundle(self) -> dict:
        identity = IdentityRecord(
            object_identity=ObjectIdentity(
                kind="PUBLIC_STATEMENT_WORD",
                logical_slot="fixture.word[0]",
                representation="FIELD_ELEMENT",
                state_scope="TRANSITION_INPUT",
                encoding="ACIR_PUBLIC_INPUT",
                value_type="Field",
            ),
            context_identity=ContextIdentity(
                kind="PROGRAM_INTERFACE",
                domain="fixture-domain",
                deployment="UNSPECIFIED",
                state_version="fixture-v1",
                actor="UNSPECIFIED",
                epoch="UNSPECIFIED",
            ),
            provenance=(CompilerProvenance(
                artifact_sha256="0" * 64,
                compiler_id="nargo",
                compiler_version="fixture",
                artifact_schema="fixture",
                evidence_kind="COMPILER_ABI",
                abi_index=0,
            ),),
            derivation_class="ANNOTATED",
            annotation_refs=("UNREVIEWED_DEVELOPMENT_FIXTURE",),
        )
        return IdentityBundle(
            bundle_name="fixture",
            identities=(identity,),
            facts=(),
            input_sha256=("0" * 64,),
        ).to_dict()

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
        directory.mkdir(parents=True, exist_ok=True)
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

    def test_surface_names_cannot_produce_a_public_security_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(Path(temporary))
            with self.assertRaisesRegex(
                RoleBindingUnsupported, "COMPILER_BACKED_IDENTITY_REQUIRED"
            ):
                analyze_role_binding(
                    analysis,
                    producer_source=source,
                    producer_support_sources=[support],
                )
        self.assertEqual(LEGACY_SURFACE_ROLE_STATUS, "ANNOTATION_ONLY_QUARANTINED")

    def test_different_surface_names_have_the_same_fail_closed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.make_fixture(root / "first")
            second = self.make_fixture(
                root / "second",
                public_names=("looks_like_root", "looks_like_recipient"),
                consumer_origins=("calldata.foo", "calldata.bar"),
            )
            for analysis, source, support in (first, second):
                with self.assertRaisesRegex(
                    RoleBindingUnsupported, "COMPILER_BACKED_IDENTITY_REQUIRED"
                ):
                    analyze_role_binding(
                        analysis,
                        producer_source=source,
                        producer_support_sources=[support],
                    )

    def test_valid_compiler_identities_still_require_step9_policy_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(Path(temporary))
            with self.assertRaisesRegex(
                RoleBindingUnsupported, "AUTHORIZATION_BOUNDARY_CHECK_REQUIRED_STEP9"
            ):
                analyze_role_binding(
                    analysis,
                    producer_source=source,
                    producer_support_sources=[support],
                    compiler_identity_bundle=self.identity_bundle(),
                )

    def test_invalid_identity_bundle_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis, source, support = self.make_fixture(Path(temporary))
            with self.assertRaisesRegex(
                RoleBindingUnsupported, "COMPILER_IDENTITY_BUNDLE_INVALID"
            ):
                analyze_role_binding(
                    analysis,
                    producer_source=source,
                    producer_support_sources=[support],
                    compiler_identity_bundle={"schema": "wrong"},
                )

    def test_legacy_role_parser_is_explicitly_annotation_only(self) -> None:
        self.assertEqual(canonical_role("gigaRoot"), "state-root:giga")
        self.assertEqual(canonical_role("unrelated_name"), "unknown")
        self.assertEqual(LEGACY_SURFACE_ROLE_STATUS, "ANNOTATION_ONLY_QUARANTINED")


if __name__ == "__main__":
    unittest.main()
