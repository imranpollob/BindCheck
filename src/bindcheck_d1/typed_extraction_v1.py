"""Typed extraction inventory over existing BindCheck development records.

This Step-10 adapter does not change extraction, infer policy, or emit a
security verdict. It translates existing static/integrated facts into the
public Step-8 identity/fact interface and retains source details in a separate
hash-bound observation ledger. Name-derived roles remain annotations and
unsupported extraction remains UNKNOWN.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence

from .roles.compiler_identity_v1 import (
    APPROXIMATIONS,
    BUNDLE_SCHEMA,
    FACT_SCHEMA,
    FIXTURE_LABEL,
    MAPPING_SCHEMA,
    IdentityBundle,
    IdentityFact,
    IdentityRecord,
    canonical_json_bytes,
    sha256_json,
    validate_bundle,
    validate_mapping_certificate,
)


SCHEMA = "bindcheck.typed-extraction-inventory/v2"
OBSERVATION_SCHEMA = "bindcheck.typed-extraction-observation/v1"
D1P40_SCHEMA = "bindcheck.d2.step10-d1p40-regressions/v1"


class TypedExtractionError(ValueError):
    """The supplied records cannot support an honest typed inventory."""


def _json(value: Any) -> Any:
    return json.loads(canonical_json_bytes(value).decode("utf-8"))


def _strings(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


def _ref_key(value: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        str(value.get("schema")),
        str(value.get("semantic_hash")),
        str(value.get("canonical_bytes_sha256")),
    )


def _unknown(reason: str) -> dict[str, str]:
    return {"kind": "UNKNOWN", "reason_code": reason}


def _condition(
    raw: Mapping[str, Any] | None,
    condition_variables: Mapping[str, str],
) -> tuple[dict[str, Any], str | None]:
    """Normalize a condition without placing a source spelling in identity."""
    if not isinstance(raw, Mapping):
        reason = "EXTRACTION_CONDITION_MISSING"
        return _unknown(reason), reason
    kind = raw.get("kind")
    if kind == "always":
        return {"kind": "ALWAYS"}, None
    if kind == "never":
        return {"kind": "NEVER"}, None
    if kind == "unknown":
        reason = str(raw.get("reason") or "EXTRACTION_CONDITION_UNKNOWN")
        return _unknown(reason), reason
    if kind == "any":
        reason = "DISJUNCTIVE_RELIANCE_NOT_NORMALIZED"
        return _unknown(reason), reason
    if kind == "prefix":
        extent_value = raw.get("extent_value")
        if isinstance(extent_value, int) and not isinstance(extent_value, bool):
            right: dict[str, Any] = {"const": extent_value}
        else:
            surface = raw.get("extent")
            stable = condition_variables.get(str(surface)) if surface is not None else None
            if not stable:
                reason = "EXTENT_IDENTITY_NOT_COMPILER_BACKED"
                return _unknown(reason), reason
            right = {"var": stable}
        return {
            "kind": "PREDICATE",
            "predicate": {
                "op": "lt",
                "left": {"var": condition_variables.get("word_offset", "word_offset")},
                "right": right,
            },
        }, None
    reason = "EXTRACTION_CONDITION_KIND_UNSUPPORTED"
    return _unknown(reason), reason


def _validate_term(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise TypedExtractionError("condition term must be an object")
    if set(value) == {"var"}:
        if not isinstance(value.get("var"), str) or not value["var"].strip():
            raise TypedExtractionError("condition variable must be nonempty")
        return
    if set(value) == {"const"}:
        _json(value["const"])
        return
    raise TypedExtractionError("condition term must be exactly var or const")


def _validate_predicate(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise TypedExtractionError("condition predicate must be an object")
    op = value.get("op")
    if op == "const":
        if set(value) != {"op", "value"} or not isinstance(value.get("value"), bool):
            raise TypedExtractionError("boolean predicate constant is malformed")
        return
    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        if set(value) != {"op", "left", "right"}:
            raise TypedExtractionError(f"predicate {op} requires left and right")
        _validate_term(value["left"])
        _validate_term(value["right"])
        return
    if op in {"and", "or"}:
        args = value.get("args")
        if set(value) != {"op", "args"} or not isinstance(args, list) or not args:
            raise TypedExtractionError(f"predicate {op} requires nonempty args")
        for item in args:
            _validate_predicate(item)
        return
    if op == "not":
        if set(value) != {"op", "arg"}:
            raise TypedExtractionError("predicate not requires one arg")
        _validate_predicate(value["arg"])
        return
    raise TypedExtractionError(f"condition predicate operator unsupported: {op!r}")


def _validate_condition(value: Mapping[str, Any]) -> None:
    kind = value.get("kind")
    if kind in {"ALWAYS", "NEVER"} and set(value) == {"kind"}:
        return
    if (
        kind == "UNKNOWN"
        and set(value) == {"kind", "reason_code"}
        and isinstance(value.get("reason_code"), str)
        and value["reason_code"]
    ):
        return
    if kind == "PREDICATE" and set(value) == {"kind", "predicate"}:
        _validate_predicate(value.get("predicate"))
        return
    raise TypedExtractionError(f"condition is not Step-9 compatible: {value!r}")


def _static_record(analysis: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    schema = str(analysis.get("schema", ""))
    if schema.startswith("bindcheck.integrated-analysis"):
        component = analysis.get("components", {}).get("static", {})
        if not isinstance(component, Mapping) or component.get("status") != "SUPPORTED":
            raise TypedExtractionError("STATIC_COMPONENT_NOT_SUPPORTED")
        static = analysis.get("static_analysis")
        if not isinstance(static, Mapping):
            raise TypedExtractionError("INTEGRATED_STATIC_RECORD_MISSING")
        return static, schema
    if schema.startswith("bindcheck.static-analysis"):
        return analysis, schema
    raise TypedExtractionError(f"UNSUPPORTED_ANALYSIS_SCHEMA:{schema}")


def _identity_indices(bundle: IdentityBundle) -> tuple[dict[int, IdentityRecord], list[str]]:
    result: dict[int, IdentityRecord] = {}
    collisions: list[str] = []
    for identity in bundle.identities:
        for provenance in identity.provenance:
            index = provenance.abi_index
            if index is None or provenance.support != "SUPPORTED":
                continue
            previous = result.get(index)
            if previous is None or previous.reference() == identity.reference():
                result[index] = identity
            else:
                collisions.append(
                    f"abi_index={index}:{previous.semantic_hash}:{identity.semantic_hash}"
                )
    return result, sorted(set(collisions))


def _resolve_identity(
    value: Mapping[str, str] | None,
    known: Mapping[tuple[str, str, str], IdentityRecord],
) -> IdentityRecord | None:
    if value is None:
        return None
    return known.get(_ref_key(value))


def _fact(
    *,
    fact_kind: str,
    subject: IdentityRecord,
    object_identity: IdentityRecord | None,
    quantifier: str,
    condition: Mapping[str, Any],
    approximation: str,
    derivation_class: str,
    support: str,
    reason: str | None,
    assumption_refs: Iterable[str],
    annotation_refs: Iterable[str],
    mapping_refs: Iterable[str],
) -> IdentityFact:
    _validate_condition(condition)
    provenance_refs = {subject.provenance_hash}
    if object_identity is not None:
        provenance_refs.add(object_identity.provenance_hash)
    return IdentityFact(
        fact_kind=fact_kind,
        subject_identity_ref=subject.reference(),
        object_identity_ref=(object_identity.reference() if object_identity else None),
        quantifier=quantifier,
        condition=condition,
        approximation=approximation,
        derivation_class=derivation_class,
        support=support,
        reason=reason,
        provenance_refs=tuple(sorted(provenance_refs)),
        assumption_refs=tuple(assumption_refs),
        annotation_refs=tuple(annotation_refs),
        mapping_refs=tuple(mapping_refs),
    )


def _observation(
    fact: IdentityFact, source_kind: str, source_fields: Mapping[str, Any]
) -> dict[str, Any]:
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "exported_fact_id": fact.fact_id,
        "source_kind": source_kind,
        "source_fields": _json(dict(source_fields)),
    }
    return {"observation_id": f"XO-{sha256_json(payload)[:24].upper()}", **payload}


def _mapping_ids(mappings: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    result = []
    for mapping in mappings:
        if mapping.get("schema") != MAPPING_SCHEMA:
            raise TypedExtractionError("IDENTITY_MAPPING_SCHEMA_UNSUPPORTED")
        check = validate_mapping_certificate(mapping)
        if not all(check["properties"].get(name) is True for name in (
            "total", "injective", "surjective", "semantic_identity_preserving"
        )):
            raise TypedExtractionError("IDENTITY_MAPPING_NOT_SEMANTIC_BIJECTION")
        result.append(check["mapping_id"])
    return _strings(result)


def build_inventory(
    analysis: Mapping[str, Any],
    identity_bundle: IdentityBundle,
    *,
    mappings: Sequence[Mapping[str, Any]] = (),
    condition_variables: Mapping[str, str] | None = None,
    authorization_identity_by_index: Mapping[int, Mapping[str, str]] | None = None,
    effect_identity_by_index: Mapping[int, Mapping[str, str]] | None = None,
    assumption_refs: Iterable[str] = (),
    annotation_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Translate one current analysis using the frozen Step-8 identity chain."""
    validate_bundle(identity_bundle.to_dict())
    static, source_schema = _static_record(analysis)
    by_index, collisions = _identity_indices(identity_bundle)
    if collisions:
        raise TypedExtractionError("ABI_IDENTITY_COLLISION:" + ",".join(collisions))
    known = {_ref_key(item.reference()): item for item in identity_bundle.identities}
    auth_refs = dict(authorization_identity_by_index or {})
    effect_refs = dict(effect_identity_by_index or {})
    variables = dict(condition_variables or {})
    assumptions = _strings(assumption_refs)
    annotations = _strings(annotation_refs)
    mapping_ids = _mapping_ids(mappings)

    facts: list[IdentityFact] = []
    observations: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    unmapped: set[int] = set()

    for leaf in static.get("producer", {}).get("public_leaves", []):
        index = leaf.get("public_index")
        if not isinstance(index, int) or index not in by_index:
            if isinstance(index, int):
                unmapped.add(index)
            continue
        value_identity = by_index[index]
        authorization = _resolve_identity(auth_refs.get(index), known)
        condition, condition_reason = _condition(leaf.get("binding_condition"), variables)
        reason = None
        if authorization is None:
            reason = "AUTHORIZATION_IDENTITY_NOT_COMPILER_BACKED"
        elif leaf.get("memory_dependency_status") == "unresolved-dynamic":
            reason = "PRODUCER_DYNAMIC_MEMORY_ADDRESS_UNRESOLVED"
        elif leaf.get("binding_status") != "EXACT":
            reason = "PRODUCER_BINDING_NOT_EXACT"
        elif condition_reason:
            reason = condition_reason
        supported = reason is None
        subject = authorization or value_identity
        # The current static analyzer establishes a proof-enforced occurrence
        # or bounded dependency, not the relational authorization guarantee
        # required by Step 9. The supplied authorization identity therefore
        # creates only an annotated candidate and is never promoted here to a
        # MUST producer_guarantee.
        fact = _fact(
            fact_kind="producer_binding_candidate",
            subject=subject,
            object_identity=value_identity,
            quantifier="MAY",
            condition=condition if supported else _unknown(str(reason)),
            approximation=("OVER_APPROXIMATION" if supported else (
                "OVER_APPROXIMATION"
                if leaf.get("memory_dependency_status") == "unresolved-dynamic"
                else "UNKNOWN"
            )),
            derivation_class="ANNOTATED" if supported else "UNKNOWN",
            support="SUPPORTED" if supported else "UNKNOWN",
            reason=(reason or "AUTHORIZATION_RELATION_NOT_DERIVED"),
            assumption_refs=assumptions,
            annotation_refs=(*annotations, "EXTERNAL_AUTHORIZATION_IDENTITY_LINK"),
            mapping_refs=mapping_ids,
        )
        facts.append(fact)
        observations.append(_observation(fact, "producer-public-leaf", {
            "public_index": index,
            "display_path": leaf.get("path"),
            "witness": leaf.get("witness"),
            "occurrence_count": leaf.get("occurrence_count"),
            "witness_generation_occurrence_count": leaf.get(
                "witness_generation_occurrence_count"
            ),
            "memory_definition_occurrence_count": leaf.get(
                "memory_definition_occurrence_count"
            ),
            "memory_dependency_status": leaf.get("memory_dependency_status"),
            "binding_status": leaf.get("binding_status"),
            "binding_condition": leaf.get("binding_condition"),
            "binding_evidence": leaf.get("binding_evidence"),
        }))
        if not supported:
            unknowns.append({"public_index": index, "fact_id": fact.fact_id, "reason": reason})

    consumer = static.get("consumer", {})
    for word in consumer.get("public_words", []):
        index = word.get("index")
        if not isinstance(index, int) or index not in by_index:
            if isinstance(index, int):
                unmapped.add(index)
            continue
        value_identity = by_index[index]
        effect = _resolve_identity(effect_refs.get(index), known)
        condition, condition_reason = _condition(word.get("reliance_condition"), variables)
        reason = None
        if effect is None:
            reason = "PROTECTED_EFFECT_IDENTITY_NOT_COMPILER_BACKED"
        elif word.get("reliance_status") != "EXACT":
            reason = "CONSUMER_RELIANCE_NOT_EXACT"
        elif condition_reason:
            reason = condition_reason
        supported = reason is None
        subject = effect or value_identity
        # The static record supplies a conservative use/reachability summary,
        # but the caller-provided protected-effect identity is not itself
        # proven to correspond to that AST occurrence. Keep the joined record
        # as an annotated candidate until a mapping/provenance checker binds it.
        fact = _fact(
            fact_kind="consumer_reliance_candidate",
            subject=subject,
            object_identity=value_identity,
            quantifier="MAY",
            condition=condition if supported else _unknown(str(reason)),
            approximation="OVER_APPROXIMATION" if supported else "UNKNOWN",
            derivation_class="ANNOTATED" if supported else "UNKNOWN",
            support="SUPPORTED" if supported else "UNKNOWN",
            reason=(reason or "PROTECTED_EFFECT_RELATION_NOT_DERIVED"),
            assumption_refs=assumptions,
            annotation_refs=(*annotations, "EXTERNAL_PROTECTED_EFFECT_IDENTITY_LINK"),
            mapping_refs=mapping_ids,
        )
        facts.append(fact)
        observations.append(_observation(fact, "consumer-public-word", {
            "public_index": index,
            "display_origin": word.get("origin"),
            "source_class": word.get("source_class"),
            "source_classes": word.get("source_classes"),
            "consumer_used": word.get("consumer_used"),
            "guard_used": word.get("guard_used"),
            "effect_used": word.get("effect_used"),
            "reliance_status": word.get("reliance_status"),
            "reliance_condition": word.get("reliance_condition"),
            "effect_relevant": index in consumer.get("effect_word_indices", []),
        }))
        if not supported:
            unknowns.append({"public_index": index, "fact_id": fact.fact_id, "reason": reason})

    for row in static.get("extent_facts", {}).get("coverage", []):
        index = row.get("public_index")
        if not isinstance(index, int) or index not in by_index:
            if isinstance(index, int):
                unmapped.add(index)
            continue
        exact = row.get("status") == "EXACT" and isinstance(row.get("covered"), bool)
        reason = None if exact else "EXTENT_COVERAGE_NOT_EXACT"
        fact = _fact(
            fact_kind=("extent_coverage" if row.get("covered") is True else "extent_gap"),
            subject=by_index[index],
            object_identity=None,
            quantifier="MUST",
            condition={"kind": "ALWAYS"} if exact else _unknown(str(reason)),
            approximation="EXACT" if exact else "UNKNOWN",
            derivation_class="DERIVED" if exact else "UNKNOWN",
            support="SUPPORTED" if exact else "UNKNOWN",
            reason=reason,
            assumption_refs=assumptions,
            annotation_refs=annotations,
            mapping_refs=mapping_ids,
        )
        facts.append(fact)
        observations.append(_observation(fact, "extent-coverage", dict(row)))
        if not exact:
            unknowns.append({"public_index": index, "fact_id": fact.fact_id, "reason": reason})

    role = analysis.get("role_binding") if str(analysis.get("schema", "")).startswith(
        "bindcheck.integrated-analysis"
    ) else None
    if isinstance(role, Mapping) and role.get("status") == "SUPPORTED":
        for word in role.get("words", []):
            index = word.get("public_index")
            if not isinstance(index, int) or index not in by_index:
                continue
            correspondence = str(word.get("boundary_correspondence", "unknown"))
            fact = _fact(
                fact_kind=f"role_correspondence:{correspondence}",
                subject=by_index[index],
                object_identity=None,
                quantifier="MAY",
                condition={"kind": "ALWAYS"},
                approximation="UNKNOWN",
                derivation_class="ANNOTATED",
                support="SUPPORTED",
                reason=None,
                assumption_refs=assumptions,
                annotation_refs=(*annotations, "IDENTIFIER_DERIVED_ROLE_VOCABULARY"),
                mapping_refs=mapping_ids,
            )
            facts.append(fact)
            observations.append(_observation(fact, "role-correspondence", {
                "public_index": index,
                "boundary_correspondence": correspondence,
                "producer": word.get("producer"),
                "consumer": word.get("consumer"),
            }))

    all_facts = (*identity_bundle.facts, *facts)
    if len({item.fact_id for item in all_facts}) != len(all_facts):
        raise TypedExtractionError("DUPLICATE_TYPED_FACT_ID")
    augmented = IdentityBundle(
        bundle_name=f"{identity_bundle.bundle_name}:typed-extraction",
        identities=identity_bundle.identities,
        facts=all_facts,
        input_sha256=(*identity_bundle.input_sha256, sha256_json(analysis)),
        fixture_label=FIXTURE_LABEL,
        limitations=tuple(sorted(set(identity_bundle.limitations) | {
            "EXTRACTION_INVENTORY_ONLY_NO_SECURITY_VERDICT",
            "ROLE_FACTS_ARE_IDENTIFIER_DERIVED_ANNOTATIONS",
        })),
    )
    bundle_dict = augmented.to_dict()
    validate_bundle(bundle_dict)
    payload = {
        "schema": SCHEMA,
        "fixture_label": FIXTURE_LABEL,
        "status": "COMPLETE_WITH_UNKNOWNS" if unknowns or unmapped else "COMPLETE",
        "research_verdict": "UNKNOWN",
        "source_analysis_schema": source_schema,
        "source_analysis_sha256": sha256_json(analysis),
        "identity_bundle": bundle_dict,
        "exported_fact_ids": sorted(item.fact_id for item in facts),
        "mapping_ids": list(mapping_ids),
        "mappings": [_json(dict(item)) for item in mappings],
        "external_reference_registry": {
            "assumption_refs": list(assumptions),
            "annotation_refs": sorted(set(annotations) | {
                "EXTERNAL_AUTHORIZATION_IDENTITY_LINK",
                "EXTERNAL_PROTECTED_EFFECT_IDENTITY_LINK",
                *( {"IDENTIFIER_DERIVED_ROLE_VOCABULARY"} if isinstance(role, Mapping)
                   and role.get("status") == "SUPPORTED" else set() ),
            }),
            "mapping_refs": list(mapping_ids),
            "resolution_boundary": (
                "Reference names are declared and hash-bound by this inventory; "
                "their external source records remain caller-owned."
            ),
        },
        "observations": sorted(observations, key=lambda item: item["observation_id"]),
        "unknowns": sorted(unknowns, key=lambda item: (item["public_index"], item["fact_id"])),
        "unmapped_public_indices": sorted(unmapped),
        "summary": {
            "exported_fact_count": len(facts),
            "producer_guarantee_count": 0,
            "producer_binding_candidate_count": sum(
                item.fact_kind == "producer_binding_candidate" for item in facts
            ),
            "consumer_reliance_count": 0,
            "consumer_reliance_candidate_count": sum(
                item.fact_kind == "consumer_reliance_candidate" for item in facts
            ),
            "derived_supported_count": sum(
                item.derivation_class == "DERIVED" and item.support == "SUPPORTED" for item in facts
            ),
            "annotated_count": sum(item.derivation_class == "ANNOTATED" for item in facts),
            "unknown_count": sum(item.support == "UNKNOWN" for item in facts),
        },
        "claim_limits": [
            "This is an unreviewed development-fixture extraction inventory.",
            "A syntactic occurrence is not by itself an authorization guarantee.",
            "MAY, ANNOTATED, ASSUMED, or UNKNOWN facts cannot discharge a MUST obligation.",
            "No policy correctness, security verdict, Gate A score, or safe result is asserted.",
        ],
    }
    return {"inventory_sha256": sha256_json(payload), **payload}


def validate_inventory(inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Replay inventory, observation, fact, provenance, and parent integrity."""
    if inventory.get("schema") != SCHEMA:
        raise TypedExtractionError("TYPED_EXTRACTION_SCHEMA_UNSUPPORTED")
    if inventory.get("fixture_label") != FIXTURE_LABEL:
        raise TypedExtractionError("TYPED_EXTRACTION_FIXTURE_LABEL_CHANGED")
    if inventory.get("research_verdict") != "UNKNOWN":
        raise TypedExtractionError("TYPED_EXTRACTION_RESEARCH_VERDICT_CHANGED")
    payload = {key: value for key, value in inventory.items() if key != "inventory_sha256"}
    if inventory.get("inventory_sha256") != sha256_json(payload):
        raise TypedExtractionError("TYPED_EXTRACTION_INVENTORY_HASH_MISMATCH")
    bundle = inventory.get("identity_bundle")
    if not isinstance(bundle, Mapping) or bundle.get("schema") != BUNDLE_SCHEMA:
        raise TypedExtractionError("TYPED_EXTRACTION_BUNDLE_MISSING")
    bundle_check = validate_bundle(bundle)
    facts = {item["fact_id"]: item for item in bundle.get("facts", [])}
    if len(facts) != len(bundle.get("facts", [])):
        raise TypedExtractionError("DUPLICATE_TYPED_FACT_ID")
    exported_ids = inventory.get("exported_fact_ids")
    if (
        not isinstance(exported_ids, list)
        or exported_ids != sorted(exported_ids)
        or len(exported_ids) != len(set(exported_ids))
        or not set(exported_ids).issubset(facts)
    ):
        raise TypedExtractionError("EXPORTED_TYPED_FACT_SET_INVALID")
    source_sha256 = inventory.get("source_analysis_sha256")
    if source_sha256 not in bundle.get("input_sha256", []):
        raise TypedExtractionError("SOURCE_ANALYSIS_HASH_NOT_BOUND_TO_BUNDLE")
    serialized_mappings = inventory.get("mappings")
    listed_mapping_ids = inventory.get("mapping_ids")
    if not isinstance(serialized_mappings, list) or not isinstance(listed_mapping_ids, list):
        raise TypedExtractionError("TYPED_EXTRACTION_MAPPING_LIST_INVALID")
    replayed_mapping_ids = _mapping_ids(serialized_mappings)
    if listed_mapping_ids != list(replayed_mapping_ids):
        raise TypedExtractionError("TYPED_EXTRACTION_MAPPING_ID_REPLAY_MISMATCH")
    provenance_hashes = {item.get("provenance_hash") for item in bundle.get("identities", [])}
    mapping_ids = set(replayed_mapping_ids)
    registry = inventory.get("external_reference_registry")
    if not isinstance(registry, Mapping):
        raise TypedExtractionError("EXTERNAL_REFERENCE_REGISTRY_MISSING")
    declared_refs: dict[str, set[str]] = {}
    for name in ("assumption_refs", "annotation_refs", "mapping_refs"):
        values = registry.get(name)
        if (
            not isinstance(values, list)
            or values != sorted(values)
            or len(values) != len(set(values))
            or not all(isinstance(item, str) and item for item in values)
        ):
            raise TypedExtractionError(f"EXTERNAL_REFERENCE_{name.upper()}_INVALID")
        declared_refs[name] = set(values)
    if declared_refs["mapping_refs"] != mapping_ids:
        raise TypedExtractionError("EXTERNAL_MAPPING_REGISTRY_REPLAY_MISMATCH")
    # The Step-8 envelope intentionally permits a wider condition vocabulary
    # for structural/compiler facts.  Only facts exported by this adapter are
    # promised to satisfy Step 9's stricter authorization vocabulary.
    for fact_id in exported_ids:
        fact = facts[fact_id]
        _validate_condition(fact.get("condition", {}))
        if fact.get("schema") != FACT_SCHEMA or fact.get("approximation") not in APPROXIMATIONS:
            raise TypedExtractionError("TYPED_FACT_SCHEMA_OR_APPROXIMATION_UNSUPPORTED")
        if fact.get("support") == "UNKNOWN" and not fact.get("reason"):
            raise TypedExtractionError("UNKNOWN_TYPED_FACT_REASON_MISSING")
        if (
            fact.get("quantifier") == "MUST"
            and fact.get("approximation") == "EXACT"
            and fact.get("derivation_class") == "DERIVED"
            and fact.get("support") == "SUPPORTED"
            and not fact.get("provenance_refs")
        ):
            raise TypedExtractionError("DERIVED_MUST_FACT_PROVENANCE_MISSING")
        if not set(fact.get("provenance_refs", [])).issubset(provenance_hashes):
            raise TypedExtractionError("TYPED_FACT_PROVENANCE_REFERENCE_UNKNOWN")
        if not all(
            parent in facts or str(parent).startswith("external:")
            for parent in fact.get("parent_fact_ids", [])
        ):
            raise TypedExtractionError("TYPED_FACT_PARENT_REFERENCE_UNKNOWN")
        if not set(fact.get("mapping_refs", [])).issubset(mapping_ids):
            raise TypedExtractionError("TYPED_FACT_MAPPING_REFERENCE_UNKNOWN")
        for name in ("assumption_refs", "annotation_refs", "mapping_refs"):
            if not set(fact.get(name, [])).issubset(declared_refs[name]):
                raise TypedExtractionError(
                    f"TYPED_FACT_{name.upper()}_UNDECLARED"
                )
    observation_ids: set[str] = set()
    for observation in inventory.get("observations", []):
        if observation.get("schema") != OBSERVATION_SCHEMA:
            raise TypedExtractionError("TYPED_OBSERVATION_SCHEMA_UNSUPPORTED")
        value = {key: item for key, item in observation.items() if key != "observation_id"}
        expected = f"XO-{sha256_json(value)[:24].upper()}"
        if observation.get("observation_id") != expected:
            raise TypedExtractionError("TYPED_OBSERVATION_HASH_MISMATCH")
        if expected in observation_ids:
            raise TypedExtractionError("DUPLICATE_TYPED_OBSERVATION_ID")
        observation_ids.add(expected)
        if observation.get("exported_fact_id") not in facts:
            raise TypedExtractionError("OBSERVATION_FACT_REFERENCE_UNKNOWN")
    if {
        observation.get("exported_fact_id")
        for observation in inventory.get("observations", [])
    } != set(exported_ids):
        raise TypedExtractionError("EXPORTED_FACT_OBSERVATION_COVERAGE_MISMATCH")
    unknowns = inventory.get("unknowns")
    if not isinstance(unknowns, list):
        raise TypedExtractionError("TYPED_EXTRACTION_UNKNOWNS_INVALID")
    for item in unknowns:
        if (
            not isinstance(item, Mapping)
            or item.get("fact_id") not in set(exported_ids)
            or facts[item["fact_id"]].get("support") != "UNKNOWN"
            or item.get("reason") != facts[item["fact_id"]].get("reason")
        ):
            raise TypedExtractionError("TYPED_EXTRACTION_UNKNOWN_ROW_INVALID")
    unmapped = inventory.get("unmapped_public_indices")
    if (
        not isinstance(unmapped, list)
        or unmapped != sorted(unmapped)
        or len(unmapped) != len(set(unmapped))
        or not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0
                   for item in unmapped)
    ):
        raise TypedExtractionError("UNMAPPED_PUBLIC_INDEX_SET_INVALID")
    exported_facts = [facts[fact_id] for fact_id in exported_ids]
    expected_summary = {
        "exported_fact_count": len(exported_facts),
        "producer_guarantee_count": 0,
        "producer_binding_candidate_count": sum(
            item.get("fact_kind") == "producer_binding_candidate"
            for item in exported_facts
        ),
        "consumer_reliance_count": 0,
        "consumer_reliance_candidate_count": sum(
            item.get("fact_kind") == "consumer_reliance_candidate"
            for item in exported_facts
        ),
        "derived_supported_count": sum(
            item.get("derivation_class") == "DERIVED"
            and item.get("support") == "SUPPORTED"
            for item in exported_facts
        ),
        "annotated_count": sum(
            item.get("derivation_class") == "ANNOTATED"
            for item in exported_facts
        ),
        "unknown_count": sum(
            item.get("support") == "UNKNOWN" for item in exported_facts
        ),
    }
    if inventory.get("summary") != expected_summary:
        raise TypedExtractionError("TYPED_EXTRACTION_SUMMARY_REPLAY_MISMATCH")
    expected_status = "COMPLETE_WITH_UNKNOWNS" if unknowns or unmapped else "COMPLETE"
    if inventory.get("status") != expected_status:
        raise TypedExtractionError("TYPED_EXTRACTION_STATUS_REPLAY_MISMATCH")
    return {
        "status": "PASS",
        "schema": SCHEMA,
        "inventory_sha256": inventory["inventory_sha256"],
        "bundle": bundle_check,
        "fact_count": len(facts),
        "observation_count": len(observation_ids),
        "unknown_count": len(unknowns),
        "unmapped_public_index_count": len(unmapped),
        "research_verdict": "UNKNOWN",
    }


def audit_d1p40_regressions() -> dict[str, Any]:
    """Replay the five cheap, compiler-free D1P-40 permanent regressions."""
    from .frontends.solidity_ast_v1_1 import (
        Extractor, Value, _anchor_candidates, _resolve_direct_width, _select_effect_model,
    )
    from .static_analyzer_v1 import _memory_dependency_facts

    rows: list[dict[str, Any]] = []
    dynamic = [
        {"kind": "MemoryInit", "block_id": 7, "init": [10, 11]},
        {"kind": "MemoryOp", "block_id": 7, "operation": "read", "index": 12, "value": 13},
    ]
    exact, unresolved = _memory_dependency_facts(dynamic)
    rows.append({
        "id": "D1P40-DYNAMIC-MEMORY",
        "status": "PASS" if exact == {} and unresolved == {10, 11} else "FAIL",
        "expected_semantics": "MAY_OVERAPPROXIMATION_UNKNOWN",
        "observed": {"exact": dict(exact), "unresolved": sorted(unresolved)},
    })
    mapping_reason = None
    try:
        _resolve_direct_width(5, {3}, 3)
    except ValueError as error:
        mapping_reason = str(error).split(":", 1)[0]
    rows.append({
        "id": "D1P40-AMBIGUOUS-MAPPING",
        "status": "PASS" if mapping_reason == "SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS" else "FAIL",
        "expected_semantics": "UNKNOWN_NO_INVENTED_PREFIX",
        "observed": {"reason_code": mapping_reason},
    })
    models = [{"effect": "token-transfer", "function_name": "transfer",
               "function_type_contains": "function (address,uint256)"}]
    real = _select_effect_model(models, [("transfer", "function (address,uint256) external returns (bool)")])
    helper = _select_effect_model(models, [("helper", "function (address,uint256)")])
    rows.append({
        "id": "D1P40-TOKEN-EFFECT-IDENTITY",
        "status": "PASS" if real is not None and helper is None else "FAIL",
        "expected_semantics": "STANDARD_METHOD_AND_SIGNATURE_REQUIRED",
        "observed": {"transfer_recognized": real is not None, "helper_recognized": helper is not None},
    })
    extractor = object.__new__(Extractor)
    extractor.public_count = 4
    words = extractor._words_for_array_index(Value(array_start=0), Value(lower=0, upper=1))
    rows.append({
        "id": "D1P40-LOOP-TAIL",
        "status": "PASS" if words == {0, 1} else "FAIL",
        "expected_semantics": "EXACT_LITERAL_INTERVAL",
        "observed": {"public_indices": sorted(words)},
    })
    read = {"declarations": [1], "key_words": [0], "location": "C.sol:10"}
    anchors = _anchor_candidates([read], [], [])
    rows.append({
        "id": "D1P40-ANCHOR-CANDIDATE",
        "status": "PASS" if len(anchors) == 1 and anchors[0]["must_be_in"] is False else "FAIL",
        "expected_semantics": "CANDIDATE_EXISTS_WITHOUT_POSITIVE_GUARD",
        "observed": {"anchors": anchors},
    })
    return {
        "schema": D1P40_SCHEMA,
        "fixture_label": FIXTURE_LABEL,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "research_verdict": "UNKNOWN",
        "rows": rows,
        "payy_disposition_regressions": {
            "PY-C02": "UNSUPPORTED_MAPPING_AND_DYNAMIC_MEMORY_UNKNOWN",
            "PY-C04": "UNSUPPORTED_MAPPING",
            "PY-C06": "UNSUPPORTED_MAPPING",
            "PY-S01": "UNSUPPORTED_MAPPING",
            "PY-S02": "UNSUPPORTED_MAPPING",
        },
        "claim_limit": "Extraction regressions only; no vulnerability or safety verdict.",
    }
