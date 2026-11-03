from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from bindcheck_d1.roles.compiler_identity_v1 import (
    FIXTURE_LABEL,
    CompilerProvenance,
    ContextIdentity,
    IdentityBundle,
    IdentityFact,
    IdentityRecord,
    MappingCertificate,
    MappingEntry,
    ObjectIdentity,
    validate_bundle,
    validate_mapping_certificate,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/d2_step8_identity.py"
SPEC = importlib.util.spec_from_file_location("d2_step8_identity", SCRIPT)
assert SPEC and SPEC.loader
D2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2)


def provenance(
    digest: str = "0" * 64, *, abi_index: int = 0, display: str = "first.nr"
) -> CompilerProvenance:
    return CompilerProvenance(
        artifact_sha256=digest,
        compiler_id="nargo",
        compiler_version="beta.22",
        artifact_schema="fixture",
        evidence_kind="COMPILER_ABI",
        abi_index=abi_index,
        display_path=display,
    )


def object_identity(slot: str = "fixture.word[0]") -> ObjectIdentity:
    return ObjectIdentity(
        kind="PUBLIC_STATEMENT_WORD",
        logical_slot=slot,
        representation="NOIR_FIELD",
        state_scope="TRANSITION_INPUT",
        encoding="ACIR_PUBLIC_INPUT",
        value_type='{"kind":"field"}',
    )


def context(domain: str = "fixture.context") -> ContextIdentity:
    return ContextIdentity(
        kind="PROGRAM_INTERFACE",
        domain=domain,
        deployment="UNSPECIFIED",
        state_version="v1",
        actor="UNSPECIFIED",
        epoch="UNSPECIFIED",
    )


def identity(
    *,
    slot: str = "fixture.word[0]",
    domain: str = "fixture.context",
    digest: str = "0" * 64,
    abi_index: int = 0,
    display: str = "first.nr",
    display_name: str = "root",
) -> IdentityRecord:
    return IdentityRecord(
        object_identity=object_identity(slot),
        context_identity=context(domain),
        provenance=(provenance(digest, abi_index=abi_index, display=display),),
        derivation_class="ANNOTATED",
        annotation_refs=(FIXTURE_LABEL,),
        display_hints=(("surface_name", display_name),),
    )


class CompilerIdentityTypeTests(unittest.TestCase):
    def test_semantic_hash_excludes_provenance_names_lines_and_physical_index(self) -> None:
        first = identity()
        second = identity(
            digest="1" * 64,
            abi_index=99,
            display="renamed.nr:999",
            display_name="not_a_root",
        )
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertEqual(first.canonical_bytes_sha256, second.canonical_bytes_sha256)
        self.assertNotEqual(first.provenance_hash, second.provenance_hash)

    def test_object_and_context_are_distinct_hash_inputs(self) -> None:
        base = identity()
        other_object = identity(slot="fixture.word[1]")
        other_context = identity(domain="fixture.other-context")
        self.assertNotEqual(base.semantic_hash, other_object.semantic_hash)
        self.assertNotEqual(base.semantic_hash, other_context.semantic_hash)
        self.assertNotEqual(other_object.semantic_hash, other_context.semantic_hash)

    def test_opaque_reference_has_only_step9_fields(self) -> None:
        reference = identity().reference()
        self.assertEqual(
            set(reference),
            {"schema", "semantic_hash", "canonical_bytes_sha256"},
        )
        self.assertNotIn("display", json.dumps(reference))

    def test_fact_and_bundle_hashes_replay_and_detect_tamper(self) -> None:
        record = identity()
        fact = IdentityFact(
            fact_kind="COMPILER_ABI_POSITION",
            subject_identity_ref=record.reference(),
            object_identity_ref=None,
            quantifier="MUST",
            condition={"kind": "UNCONDITIONAL"},
            approximation="EXACT",
            derivation_class="DERIVED",
            support="SUPPORTED",
            provenance_refs=(record.provenance_hash,),
        )
        bundle = IdentityBundle(
            bundle_name="fixture",
            identities=(record,),
            facts=(fact,),
            input_sha256=("2" * 64,),
        ).to_dict()
        self.assertEqual(validate_bundle(bundle)["status"], "PASS")
        bundle["identities"][0]["canonical_payload"]["object"]["logical_slot"] = "tampered"
        with self.assertRaisesRegex(ValueError, "noncanonical|hash-inconsistent"):
            validate_bundle(bundle)

    def test_bundle_rejects_duplicate_facts_and_unresolved_internal_parent(self) -> None:
        record = identity()
        fact = IdentityFact(
            fact_kind="COMPILER_ABI_POSITION",
            subject_identity_ref=record.reference(),
            object_identity_ref=None,
            quantifier="MUST",
            condition={"kind": "UNCONDITIONAL"},
            approximation="EXACT",
            derivation_class="DERIVED",
            support="SUPPORTED",
            provenance_refs=(record.provenance_hash,),
        )
        with self.assertRaisesRegex(ValueError, "fact IDs must be unique"):
            IdentityBundle(
                bundle_name="duplicate",
                identities=(record,),
                facts=(fact, fact),
                input_sha256=("2" * 64,),
            )
        unresolved = IdentityFact(
            fact_kind="DERIVED_CHILD",
            subject_identity_ref=record.reference(),
            object_identity_ref=None,
            quantifier="MUST",
            condition={"kind": "UNCONDITIONAL"},
            approximation="EXACT",
            derivation_class="DERIVED",
            support="SUPPORTED",
            provenance_refs=(record.provenance_hash,),
            parent_fact_ids=("IF-NOT-IN-BUNDLE",),
        )
        with self.assertRaisesRegex(ValueError, "unresolved parent"):
            IdentityBundle(
                bundle_name="unresolved-parent",
                identities=(record,),
                facts=(unresolved,),
                input_sha256=("2" * 64,),
            )

    def test_mapping_properties_separate_order_from_semantic_identity(self) -> None:
        first = identity(slot="fixture.word[0]")
        second = identity(slot="fixture.word[1]", abi_index=1)
        certificate = MappingCertificate(
            transformation_id="reorder",
            source_bundle_id="source",
            target_bundle_id="target",
            entries=(
                MappingEntry(
                    logical_slot="fixture.word[0]",
                    from_identity_ref=first.reference(),
                    to_identity_ref=first.reference(),
                    from_abi_index=0,
                    to_abi_index=1,
                ),
                MappingEntry(
                    logical_slot="fixture.word[1]",
                    from_identity_ref=second.reference(),
                    to_identity_ref=second.reference(),
                    from_abi_index=1,
                    to_abi_index=0,
                ),
            ),
            source_identity_count=2,
            target_identity_count=2,
            evidence_sha256=("3" * 64,),
            mapping_source_refs=("external:fixture-map",),
        )
        self.assertTrue(certificate.properties["total"])
        self.assertTrue(certificate.properties["injective"])
        self.assertTrue(certificate.properties["surjective"])
        self.assertTrue(certificate.properties["semantic_identity_preserving"])
        self.assertFalse(certificate.properties["order_preserving"])
        self.assertEqual(
            validate_mapping_certificate(certificate.to_dict())["status"], "PASS"
        )

    def test_mapping_total_rejects_duplicate_source_identity(self) -> None:
        first = identity(slot="fixture.word[0]")
        second = identity(slot="fixture.word[1]", abi_index=1)
        certificate = MappingCertificate(
            transformation_id="bad-total",
            source_bundle_id="source",
            target_bundle_id="target",
            entries=(
                MappingEntry(
                    logical_slot="fixture.word[0]",
                    from_identity_ref=first.reference(),
                    to_identity_ref=first.reference(),
                    from_abi_index=0,
                    to_abi_index=0,
                ),
                MappingEntry(
                    logical_slot="fixture.word[1]",
                    from_identity_ref=first.reference(),
                    to_identity_ref=second.reference(),
                    from_abi_index=1,
                    to_abi_index=1,
                ),
            ),
            source_identity_count=2,
            target_identity_count=2,
            evidence_sha256=("3" * 64,),
            mapping_source_refs=("external:fixture-map",),
        )
        self.assertFalse(certificate.properties["total"])


class D2Step8RunnerTests(unittest.TestCase):
    def test_validate_only_covers_transformations_negatives_and_name_audit(self) -> None:
        result = D2.validate_only(D2.DEFAULT_PROTOCOL, D2.DEFAULT_LEDGER)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["fixture_label"], FIXTURE_LABEL)
        self.assertEqual(result["bundle_count"], 5)
        self.assertEqual(result["identity_count"], 25)
        self.assertEqual(result["mapping_count"], 4)
        self.assertEqual(result["negative_fixture_count"], 5)
        self.assertEqual(result["name_influence_audit"], "PASS")
        self.assertEqual(result["external_reference_resolution"], "PASS")
        self.assertFalse(result["scored"])
        self.assertIsNone(result["security_verdict"])

    def test_exact_step6_transformations_have_expected_mapping_properties(self) -> None:
        ledger = D2.read_json(D2.DEFAULT_LEDGER)
        built = {
            variant_id: D2.build_bundle(ledger, variant_id)
            for variant_id in ("ORIGINAL", *D2.TRANSFORMATION_IDS)
        }
        original = built["ORIGINAL"][0]
        for variant_id in D2.TRANSFORMATION_IDS:
            output, _physical, _path, _mapping_id = D2.variant_inputs(
                ledger, variant_id
            )
            certificate = D2.mapping_certificate(
                transformation_id=variant_id,
                original=original,
                transformed=built[variant_id][0],
                physical_map=built[variant_id][2],
                evidence_paths=[
                    built[variant_id][1],
                    D2.verify_record(output["build"]["producer_artifact"]),
                ],
            )
            self.assertTrue(certificate.properties["total"], variant_id)
            self.assertTrue(certificate.properties["injective"], variant_id)
            self.assertTrue(certificate.properties["surjective"], variant_id)
            self.assertTrue(
                certificate.properties["semantic_identity_preserving"], variant_id
            )
            self.assertEqual(
                certificate.properties["order_preserving"],
                variant_id != "TR-MATCHED-PUBLIC-REORDER",
            )

    def test_fresh_run_seals_zero_score_mechanical_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as temporary:
            out = Path(temporary) / "D2-08-test"
            summary = D2.run(
                protocol_path=D2.DEFAULT_PROTOCOL,
                ledger_path=D2.DEFAULT_LEDGER,
                out=out,
            )
            self.assertEqual(summary["status"], "PASS_MECHANICAL_ONLY")
            self.assertFalse(summary["scored"])
            self.assertEqual(summary["score_rows"], [])
            self.assertIsNone(summary["security_verdict"])
            self.assertFalse(summary["analyzer_or_policy_checker_dispatched"])
            self.assertEqual(summary["effort"]["subprocess_calls"], 7)
            verification = json.loads((out / "seal-verification.json").read_text())
            self.assertEqual(verification["status"], "PASS")
            self.assertTrue(verification["input_manifest_matches_final_seal"])
            negatives = json.loads((out / "negative-fixtures.json").read_text())
            self.assertEqual(negatives["status"], "PASS")
            self.assertTrue(all(row["observed"] == row["expected"] for row in negatives["rows"]))
            with self.assertRaises(FileExistsError):
                D2.run(
                    protocol_path=D2.DEFAULT_PROTOCOL,
                    ledger_path=D2.DEFAULT_LEDGER,
                    out=out,
                )


if __name__ == "__main__":
    unittest.main()
