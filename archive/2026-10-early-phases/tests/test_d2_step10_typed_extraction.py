from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import unittest

from bindcheck_d1.core.authorization_boundary_v1 import (
    AuthorizationObligation,
    BoundaryInput,
    BoundedQuery,
    PermissionRecord,
    PolicyRecord,
    ProtectedEffect,
    evaluate_equal_input_arms,
    validate_boundary_input,
)
from bindcheck_d1.roles.compiler_identity_v1 import (
    CompilerProvenance,
    ContextIdentity,
    FIXTURE_LABEL,
    IdentityBundle,
    IdentityFact,
    IdentityRecord,
    MappingCertificate,
    MappingEntry,
    ObjectIdentity,
    sha256_json,
)
from bindcheck_d1.typed_extraction_v1 import (
    TypedExtractionError,
    _validate_condition,
    audit_d1p40_regressions,
    build_inventory,
    validate_inventory,
)


def _identity(
    slot: str,
    kind: str,
    node: str,
    *,
    abi_index: int | None = None,
    domain: str = "fixture-domain",
    display_name: str | None = None,
) -> IdentityRecord:
    provenance = CompilerProvenance(
        artifact_sha256=sha256_json({"fixture": "d2-step10", "artifact": "v1"}),
        compiler_id="synthetic-step10-fixture",
        compiler_version="1.0.0",
        artifact_schema="bindcheck.synthetic-step10/v1",
        evidence_kind="COMPILER_ABI" if abi_index is not None else "COMPILER_NODE",
        node_id=node,
        abi_index=abi_index,
        source_sha256=sha256_json({"fixture": "d2-step10", "source": "v1"}),
        display_path="synthetic/d2-step10.fixture",
        display_span=f"node:{node}",
    )
    return IdentityRecord(
        object_identity=ObjectIdentity(
            kind=kind,
            logical_slot=slot,
            representation="bounded-integer",
            state_scope="single-transition",
            encoding="unsigned-canonical",
            value_type="u8",
        ),
        context_identity=ContextIdentity(
            kind="synthetic-execution-context",
            domain=domain,
            deployment="fixture-deployment",
            state_version="state-v1",
            actor="fixture-actor",
            epoch="fixture-epoch-0",
        ),
        provenance=(provenance,),
        derivation_class="DERIVED",
        display_hints=(("fixture_name", display_name or slot),),
    )


def _fixture_bundle(*, inherited_fact: bool = False) -> tuple[IdentityBundle, dict[str, IdentityRecord]]:
    identities = {
        "value": _identity("public-value-0", "producer-public-value", "value-0", abi_index=0),
        "auth": _identity("authorized-object-0", "authenticated-policy-value", "auth-0"),
        "effect": _identity("effect-occurrence-0", "protected-effect-occurrence", "effect-0"),
        "same_name_other_object": _identity(
            "other-authorized-object",
            "authenticated-policy-value",
            "auth-other-object",
            display_name="authorized-object-0",
        ),
        "same_object_other_context": _identity(
            "authorized-object-0",
            "authenticated-policy-value",
            "auth-other-context",
            domain="other-domain",
            display_name="authorized-object-0",
        ),
    }
    facts: tuple[IdentityFact, ...] = ()
    if inherited_fact:
        value = identities["value"]
        facts = (
            IdentityFact(
                fact_kind="COMPILER_ABI_POSITION",
                subject_identity_ref=value.reference(),
                object_identity_ref=None,
                quantifier="MUST",
                condition={"kind": "UNCONDITIONAL_WITHIN_COMPILED_INTERFACE"},
                approximation="EXACT",
                derivation_class="DERIVED",
                support="SUPPORTED",
                provenance_refs=(value.provenance_hash,),
                mapping_refs=("external:step8-compiler-position",),
            ),
        )
    bundle = IdentityBundle(
        bundle_name="d2-step10-fixture",
        identities=tuple(identities.values()),
        facts=facts,
        input_sha256=(sha256_json({"fixture": "d2-step10", "input": "v1"}),),
        limitations=("UNREVIEWED_DEVELOPMENT_FIXTURE_ONLY",),
    )
    return bundle, identities


def _static_analysis() -> dict:
    return {
        "schema": "bindcheck.static-analysis.v1.4-dev",
        "producer": {
            "public_leaves": [
                {
                    "public_index": 0,
                    "path": "amount",
                    "witness": 7,
                    "occurrence_count": 1,
                    "witness_generation_occurrence_count": 0,
                    "memory_definition_occurrence_count": 0,
                    "memory_dependency_status": "none",
                    "binding_status": "EXACT",
                    "binding_condition": {"kind": "always"},
                    "binding_evidence": {"occurrence_locations": ["opcode:0"]},
                }
            ]
        },
        "consumer": {
            "public_words": [
                {
                    "index": 0,
                    "origin": "calldata.amount",
                    "source_class": "calldata",
                    "source_classes": ["calldata"],
                    "consumer_used": True,
                    "guard_used": False,
                    "effect_used": True,
                    "reliance_status": "EXACT",
                    "reliance_condition": {"kind": "always"},
                }
            ],
            "effect_word_indices": [0],
        },
        "extent_facts": {
            "coverage": [
                {
                    "public_index": 0,
                    "path": "amount",
                    "status": "EXACT",
                    "covered": True,
                }
            ]
        },
        "warnings": [],
    }


def _exported_facts(inventory: dict) -> dict[str, dict]:
    ids = set(inventory["exported_fact_ids"])
    return {
        item["fact_kind"]: item
        for item in inventory["identity_bundle"]["facts"]
        if item["fact_id"] in ids
    }


def _build(
    *,
    analysis: dict | None = None,
    auth_key: str = "auth",
    effect_key: str = "effect",
    inherited_fact: bool = False,
    mappings: tuple[dict, ...] = (),
    condition_variables: dict[str, str] | None = None,
) -> tuple[dict, dict[str, IdentityRecord]]:
    bundle, identities = _fixture_bundle(inherited_fact=inherited_fact)
    inventory = build_inventory(
        analysis or _static_analysis(),
        bundle,
        mappings=mappings,
        condition_variables=condition_variables,
        authorization_identity_by_index={0: identities[auth_key].reference()},
        effect_identity_by_index={0: identities[effect_key].reference()},
    )
    return inventory, identities


def _fields() -> dict[str, dict]:
    return {
        "action": {"const": "transfer"},
        "asset": {"const": "fixture-token"},
        "quantity": {"const": 1},
        "beneficiary": {"const": "fixture-beneficiary"},
        "domain": {"const": "fixture-domain"},
        "state_version": {"const": "state-v1"},
    }


def _boundary(
    inventory: dict,
    identities: dict[str, IdentityRecord],
    *,
    auth_key: str = "auth",
    effect_key: str = "effect",
) -> BoundaryInput:
    facts = _exported_facts(inventory)
    producer_id = facts["producer_binding_candidate"]["fact_id"]
    reliance_id = facts["consumer_reliance_candidate"]["fact_id"]
    auth_ref = identities[auth_key].reference()
    effect_ref = identities[effect_key].reference()
    permission = PermissionRecord(
        permission_id="permission-0",
        authorizing_identity_ref=auth_ref,
        protected_effect_identity_ref=effect_ref,
        fields=_fields(),
    )
    policy = PolicyRecord(
        policy_id="unreviewed-step10-fixture-policy",
        version="1",
        review_status=FIXTURE_LABEL,
        permissions=(permission,),
        source_sha256=(sha256_json({"policy": "unreviewed-step10-fixture"}),),
        limitations=("NOT_HUMAN_REVIEWED",),
    )
    effect = ProtectedEffect(
        effect_id="effect-0",
        protected_effect_identity_ref=effect_ref,
        fields=_fields(),
        path_condition={"kind": "ALWAYS"},
        source_fact_ids=(reliance_id,),
    )
    obligation = AuthorizationObligation(
        obligation_id="obligation-0",
        protected_effect_id=effect.effect_id,
        authorization_identity_ref=auth_ref,
        protected_effect_identity_ref=effect_ref,
        producer_fact_ids=(producer_id,),
        reliance_fact_ids=(reliance_id,),
        fields=_fields(),
        activation={"kind": "ALWAYS"},
        discharge={"kind": "ALWAYS"},
    )
    return BoundaryInput(
        case_id="d2-step10-unreviewed-fixture",
        identity_bundle=inventory["identity_bundle"],
        policy=policy,
        obligations=(obligation,),
        effects=(effect,),
        query=BoundedQuery(
            variable_domains={},
            attacker_controlled=(),
            fixed_authenticated_context={},
            max_assignments=1,
        ),
        limitations=("NO_RESEARCH_OR_SECURITY_VERDICT",),
    )


class D2Step10TypedExtractionTest(unittest.TestCase):
    def test_candidates_use_the_step9_identity_chain_but_cannot_discharge(self) -> None:
        inventory, identities = _build()
        check = validate_inventory(inventory)
        facts = _exported_facts(inventory)
        producer = facts["producer_binding_candidate"]
        reliance = facts["consumer_reliance_candidate"]
        self.assertEqual(check["status"], "PASS")
        self.assertEqual(producer["subject_identity_ref"], identities["auth"].reference())
        self.assertEqual(producer["object_identity_ref"], identities["value"].reference())
        self.assertEqual(producer["quantifier"], "MAY")
        self.assertEqual(producer["approximation"], "OVER_APPROXIMATION")
        self.assertEqual(producer["derivation_class"], "ANNOTATED")
        self.assertEqual(producer["reason"], "AUTHORIZATION_RELATION_NOT_DERIVED")
        self.assertEqual(reliance["subject_identity_ref"], identities["effect"].reference())
        self.assertEqual(reliance["object_identity_ref"], identities["value"].reference())
        self.assertEqual(reliance["quantifier"], "MAY")
        self.assertEqual(reliance["approximation"], "OVER_APPROXIMATION")
        self.assertEqual(reliance["derivation_class"], "ANNOTATED")
        self.assertEqual(reliance["reason"], "PROTECTED_EFFECT_RELATION_NOT_DERIVED")

        boundary = _boundary(inventory, identities)
        self.assertEqual(validate_boundary_input(boundary)["identity_chain_status"], "PASS")
        result = evaluate_equal_input_arms(boundary)
        self.assertTrue(result["semantic_parity"])
        self.assertFalse(result["score_eligible"])
        self.assertEqual(result["research_verdict"], "UNKNOWN")
        for arm in result["results"].values():
            self.assertEqual(arm["state"], "UNKNOWN")
            self.assertEqual(
                arm["obligation_results"][0]["mechanical_state"], "UNKNOWN"
            )

    def test_missing_identity_links_and_dynamic_memory_remain_unknown(self) -> None:
        bundle, _ = _fixture_bundle()
        analysis = _static_analysis()
        analysis["producer"]["public_leaves"][0]["memory_dependency_status"] = (
            "unresolved-dynamic"
        )
        inventory = build_inventory(analysis, bundle)
        check = validate_inventory(inventory)
        facts = _exported_facts(inventory)
        producer = facts["producer_binding_candidate"]
        reliance = facts["consumer_reliance_candidate"]
        self.assertEqual(check["unknown_count"], 2)
        self.assertEqual(producer["quantifier"], "MAY")
        self.assertEqual(producer["approximation"], "OVER_APPROXIMATION")
        self.assertEqual(producer["support"], "UNKNOWN")
        self.assertEqual(reliance["support"], "UNKNOWN")
        self.assertEqual(inventory["research_verdict"], "UNKNOWN")

    def test_prefix_requires_compiler_backed_condition_identity(self) -> None:
        analysis = _static_analysis()
        analysis["producer"]["public_leaves"][0]["binding_condition"] = {
            "kind": "prefix",
            "extent": "surface_name_n",
        }
        unresolved, _ = _build(analysis=deepcopy(analysis))
        producer = _exported_facts(unresolved)["producer_binding_candidate"]
        self.assertEqual(producer["condition"]["kind"], "UNKNOWN")
        self.assertEqual(producer["reason"], "EXTENT_IDENTITY_NOT_COMPILER_BACKED")

        resolved, _ = _build(
            analysis=analysis,
            condition_variables={"surface_name_n": "authenticated_extent"},
        )
        producer = _exported_facts(resolved)["producer_binding_candidate"]
        self.assertEqual(producer["condition"]["kind"], "PREDICATE")
        self.assertEqual(
            producer["condition"]["predicate"]["right"],
            {"var": "authenticated_extent"},
        )

    def test_inherited_step8_fact_keeps_wider_vocabulary(self) -> None:
        inventory, _ = _build(inherited_fact=True)
        self.assertEqual(validate_inventory(inventory)["status"], "PASS")
        inherited = next(
            fact
            for fact in inventory["identity_bundle"]["facts"]
            if fact["fact_id"] not in inventory["exported_fact_ids"]
        )
        self.assertEqual(
            inherited["condition"]["kind"],
            "UNCONDITIONAL_WITHIN_COMPILED_INTERFACE",
        )

    def test_identifier_roles_are_annotations_not_must_guarantees(self) -> None:
        integrated = {
            "schema": "bindcheck.integrated-analysis.v1",
            "components": {"static": {"status": "SUPPORTED"}},
            "static_analysis": _static_analysis(),
            "role_binding": {
                "status": "SUPPORTED",
                "words": [
                    {
                        "public_index": 0,
                        "boundary_correspondence": "same-role-label",
                        "producer": {"role": "amount"},
                        "consumer": {"role": "amount"},
                    }
                ],
            },
        }
        inventory, _ = _build(analysis=integrated)
        role = _exported_facts(inventory)["role_correspondence:same-role-label"]
        self.assertEqual(role["derivation_class"], "ANNOTATED")
        self.assertEqual(role["quantifier"], "MAY")
        self.assertEqual(role["approximation"], "UNKNOWN")
        self.assertIn("IDENTIFIER_DERIVED_ROLE_VOCABULARY", role["annotation_refs"])

    def test_semantic_mapping_is_retained_but_not_silently_discharged(self) -> None:
        bundle, identities = _fixture_bundle()
        value = identities["value"]
        mapping = MappingCertificate(
            transformation_id="TR-IDENTITY-CONTROL",
            source_bundle_id="fixture-source-bundle",
            target_bundle_id="fixture-target-bundle",
            entries=(
                MappingEntry(
                    logical_slot="public-value-0",
                    from_identity_ref=value.reference(),
                    to_identity_ref=value.reference(),
                    from_abi_index=0,
                    to_abi_index=0,
                ),
            ),
            source_identity_count=1,
            target_identity_count=1,
            evidence_sha256=(sha256_json({"mapping": "identity-control"}),),
            mapping_source_refs=("external:d2-step10-identity-control",),
        ).to_dict()
        inventory = build_inventory(
            _static_analysis(),
            bundle,
            mappings=(mapping,),
            authorization_identity_by_index={0: identities["auth"].reference()},
            effect_identity_by_index={0: identities["effect"].reference()},
        )
        self.assertEqual(validate_inventory(inventory)["status"], "PASS")
        for fact in _exported_facts(inventory).values():
            self.assertEqual(fact["mapping_refs"], [mapping["mapping_id"]])
        result = evaluate_equal_input_arms(_boundary(inventory, identities))
        obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
        self.assertEqual(obligation["mechanical_state"], "UNKNOWN")
        self.assertIn("PRODUCER_MAPPING_CERTIFICATE_NOT_BOUND", obligation["reason_codes"])

        tampered = deepcopy(inventory)
        tampered["mappings"] = []
        payload = {
            key: value for key, value in tampered.items() if key != "inventory_sha256"
        }
        tampered["inventory_sha256"] = sha256_json(payload)
        with self.assertRaisesRegex(TypedExtractionError, "MAPPING_ID_REPLAY_MISMATCH"):
            validate_inventory(tampered)

    def test_condition_validator_replays_exact_step9_shapes(self) -> None:
        _validate_condition({
            "kind": "PREDICATE",
            "predicate": {
                "op": "and",
                "args": [
                    {"op": "lt", "left": {"var": "i"}, "right": {"const": 4}},
                    {"op": "const", "value": True},
                ],
            },
        })
        malformed = (
            {"kind": "PREDICATE", "predicate": {"op": "lt"}},
            {"kind": "PREDICATE", "predicate": {"op": "const", "value": 1}},
            {"kind": "PREDICATE", "predicate": {"op": "and", "args": []}},
        )
        for value in malformed:
            with self.subTest(value=value):
                with self.assertRaises(TypedExtractionError):
                    _validate_condition(value)

    def test_pre_result_identity_chain_defect_is_a_permanent_regression(self) -> None:
        cases = (
            (
                "same-display-name-different-object",
                "same_name_other_object",
                "effect",
                "auth",
                "effect",
                "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
            ),
            (
                "same-object-different-context",
                "same_object_other_context",
                "effect",
                "auth",
                "effect",
                "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
            ),
            (
                "swapped-effect",
                "auth",
                "auth",
                "auth",
                "effect",
                "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH",
            ),
        )
        for label, export_auth, export_effect, expected_auth, expected_effect, reason in cases:
            with self.subTest(label=label):
                inventory, identities = _build(
                    auth_key=export_auth,
                    effect_key=export_effect,
                )
                boundary = _boundary(
                    inventory,
                    identities,
                    auth_key=expected_auth,
                    effect_key=expected_effect,
                )
                validation = validate_boundary_input(boundary)
                self.assertEqual(validation["identity_chain_status"], "UNKNOWN")
                self.assertIn(
                    reason,
                    {item["reason_code"] for item in validation["identity_chain_issues"]},
                )
                result = evaluate_equal_input_arms(boundary)
                obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
                self.assertEqual(obligation["mechanical_state"], "UNKNOWN")
                self.assertIn(reason, obligation["reason_codes"])

    def test_observation_and_inventory_hashes_are_replayed(self) -> None:
        inventory, _ = _build()
        tampered = deepcopy(inventory)
        tampered["observations"][0]["source_fields"]["display_path"] = "tampered"
        payload = {key: value for key, value in tampered.items() if key != "inventory_sha256"}
        tampered["inventory_sha256"] = sha256_json(payload)
        with self.assertRaisesRegex(TypedExtractionError, "OBSERVATION_HASH_MISMATCH"):
            validate_inventory(tampered)

        undeclared = deepcopy(inventory)
        undeclared["external_reference_registry"]["annotation_refs"] = []
        payload = {
            key: value for key, value in undeclared.items() if key != "inventory_sha256"
        }
        undeclared["inventory_sha256"] = sha256_json(payload)
        with self.assertRaisesRegex(TypedExtractionError, "ANNOTATION_REFS_UNDECLARED"):
            validate_inventory(undeclared)

    def test_d1p40_five_defects_and_payy_dispositions_are_permanent(self) -> None:
        result = audit_d1p40_regressions()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["rows"]), 5)
        self.assertEqual({row["status"] for row in result["rows"]}, {"PASS"})
        self.assertEqual(
            set(result["payy_disposition_regressions"]),
            {"PY-C02", "PY-C04", "PY-C06", "PY-S01", "PY-S02"},
        )
        self.assertEqual(result["research_verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
