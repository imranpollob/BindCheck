"""Fair composition baselines over BindCheck's already extracted fact records.

The module does not run extraction and does not call the integrated analyzer.
It consumes a versioned integrated-analysis record and an optional reviewed
policy.  This makes the information budget explicit: extraction is shared and
only the composition step is compared.

Every emitted item is a *candidate*.  Structural items are navigation signals;
policy candidates still require adjudication and validation.  This module
never returns ``VIOLATION`` or ``VERIFIED_WITHIN_SCOPE``.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import re
import time
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "bindcheck.composition-baselines/v1"
POLICY_SCHEMA = "bindcheck.composition-policy/v1"
UNION_RULES = frozenset({"R-BIND", "R-CONSUMER", "R-POLARITY", "R-ANCHOR"})
PRODUCER_ONLY_RULES = frozenset({"R-BIND"})
CONSUMER_ONLY_RULES = frozenset({"R-CONSUMER", "R-POLARITY", "R-ANCHOR"})
BASELINE_NAMES = (
    "producer-only",
    "consumer-only",
    "unjoined-union",
    "basic-structural-composition",
    "strong-simple-composition",
    "full-bindcheck",
)


class CompositionInputError(ValueError):
    """Raised when an input record cannot support an honest comparison."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Any, length: int = 20) -> str:
    return f"{prefix}-{hashlib.sha256(_canonical_bytes(value)).hexdigest()[:length].upper()}"


def _strip_locations(value: Any) -> Any:
    """Remove unstable coordinates/identifiers from semantic comparison data."""
    ignored = {
        "id",
        "legacy_id",
        "stable_id",
        "candidate_id",
        "location",
        "locations",
        "occurrence_locations",
        "memory_definition_occurrence_locations",
        "witness_generation_occurrence_locations",
        "source_location",
        "generated_at_utc",
        "runtime_seconds",
    }
    if isinstance(value, Mapping):
        return {
            str(key): _strip_locations(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if key not in ignored
        }
    if isinstance(value, (list, tuple)):
        return [_strip_locations(item) for item in value]
    return value


def _policy_or_default(policy: Mapping[str, Any] | None, target: str) -> dict[str, Any]:
    result = deepcopy(dict(policy or {}))
    if result and result.get("schema") != POLICY_SCHEMA:
        raise CompositionInputError(
            f"policy schema must be {POLICY_SCHEMA!r}, got {result.get('schema')!r}"
        )
    result.setdefault("schema", POLICY_SCHEMA)
    result.setdefault("policy_id", "no-reviewed-policy-supplied")
    result.setdefault("version", "none")
    result.setdefault("review_status", "NOT_SUPPLIED")
    result.setdefault("policy_author", None)
    result.setdefault("policy_reviewer", None)
    result.setdefault("comparison_group", target)
    result.setdefault("word_identities", {})
    result.setdefault("term_aliases", {})
    result.setdefault("obligations", [])
    if not isinstance(result["word_identities"], Mapping):
        raise CompositionInputError("policy.word_identities must be an object")
    if not isinstance(result["obligations"], list):
        raise CompositionInputError("policy.obligations must be a list")
    if not isinstance(result["term_aliases"], Mapping):
        raise CompositionInputError("policy.term_aliases must be an object")
    if result["review_status"] not in {"NOT_SUPPLIED", "UNREVIEWED", "HUMAN_REVIEWED"}:
        raise CompositionInputError(f"invalid policy review_status: {result['review_status']!r}")
    if result["review_status"] == "HUMAN_REVIEWED" and (
        not result["policy_author"] or not result["policy_reviewer"]
    ):
        raise CompositionInputError(
            "HUMAN_REVIEWED policy needs policy_author and policy_reviewer"
        )
    normalized_identities: dict[int, str] = {}
    for raw_index, identity in result["word_identities"].items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise CompositionInputError(
                f"policy word identity index is not an integer: {raw_index!r}"
            ) from exc
        if index < 0 or not isinstance(identity, str) or not identity:
            raise CompositionInputError(
                f"invalid policy word identity {raw_index!r}: {identity!r}"
            )
        if identity in normalized_identities.values():
            raise CompositionInputError(f"duplicate semantic word identity: {identity}")
        normalized_identities[index] = identity
    result["word_identities"] = normalized_identities
    aliases: dict[str, str] = {}
    for surface, semantic in result["term_aliases"].items():
        if not isinstance(surface, str) or not surface:
            raise CompositionInputError("policy term alias keys must be non-empty strings")
        if not isinstance(semantic, str) or not semantic:
            raise CompositionInputError("policy term alias values must be non-empty strings")
        aliases[surface] = semantic
    result["term_aliases"] = aliases
    obligation_ids = [item.get("id") for item in result["obligations"]]
    if any(not isinstance(item, str) or not item for item in obligation_ids):
        raise CompositionInputError("every policy obligation needs a non-empty string id")
    if len(obligation_ids) != len(set(obligation_ids)):
        raise CompositionInputError("policy obligation ids must be unique")
    return result


def _component_status(record: Mapping[str, Any], component: str) -> str:
    value = record.get("components", {}).get(component, {})
    if isinstance(value, Mapping):
        return str(value.get("status", "UNKNOWN"))
    return "UNKNOWN"


def _target_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    inputs = record.get("inputs", {})
    identity: dict[str, Any] = {"target": record.get("target")}
    for name in (
        "producer_artifact",
        "consumer_source",
        "checked_consumer_relation",
        "producer_semantic_source",
        "recursive_mapping_bridge",
    ):
        item = inputs.get(name)
        if isinstance(item, Mapping) and item.get("sha256"):
            identity[f"{name}_sha256"] = item["sha256"]
    if len(identity) == 1:
        static = record.get("static_analysis", {})
        producer = static.get("producer", {}) if isinstance(static, Mapping) else {}
        consumer = static.get("consumer", {}) if isinstance(static, Mapping) else {}
        if producer.get("sha256"):
            identity["producer_artifact_sha256"] = producer["sha256"]
        if consumer.get("source_sha256"):
            identity["consumer_source_sha256"] = consumer["source_sha256"]
    return identity


def _logical_words(indices: Iterable[int], policy: Mapping[str, Any]) -> list[str]:
    identities = policy["word_identities"]
    return [identities.get(index, f"physical-index:{index}") for index in sorted(set(indices))]


def _normalize_term(value: str, policy: Mapping[str, Any]) -> str:
    aliases = policy["term_aliases"]
    for surface in sorted(aliases, key=len, reverse=True):
        value = re.sub(rf"\b{re.escape(surface)}\b", aliases[surface], value)
    return value


def _semantic_evidence(value: Any, policy: Mapping[str, Any]) -> Any:
    """Replace physical index fields with reviewed semantic identities."""
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        surface_only = {"producer_path", "consumer_origin", "paths"}
        for key, item in value.items():
            if key in surface_only:
                continue
            if key == "public_index" and isinstance(item, int):
                normalized["word_identity"] = _logical_words([item], policy)[0]
            elif key == "public_indices" and isinstance(item, Sequence):
                indices = [index for index in item if isinstance(index, int)]
                normalized["word_identities"] = _logical_words(indices, policy)
            elif key in {"witness", "witnesses"}:
                # Witness numbers are serialization coordinates, not semantics.
                continue
            else:
                normalized[str(key)] = _semantic_evidence(item, policy)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_semantic_evidence(item, policy) for item in value]
    if isinstance(value, str):
        return _normalize_term(value, policy)
    return value


def _candidate(
    *,
    baseline: str,
    kind: str,
    classification: str,
    indices: Iterable[int],
    target_identity: Mapping[str, Any],
    policy: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source_rule: str | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    physical_indices = sorted(set(indices))
    logical_words = _logical_words(physical_indices, policy)
    physical_semantics = {
        "baseline": baseline,
        "kind": kind,
        "physical_indices": physical_indices,
        "evidence": _strip_locations(evidence),
    }
    comparison_semantics = {
        "comparison_group": policy["comparison_group"],
        "kind": kind,
        "logical_words": logical_words,
        "evidence": _strip_locations(_semantic_evidence(evidence, policy)),
    }
    return {
        "candidate_id": _digest(
            "CB",
            {"target_identity": target_identity, **physical_semantics},
        ),
        "semantic_id": _digest("CBS", comparison_semantics),
        "baseline": baseline,
        "kind": kind,
        "classification": classification,
        "public_indices": physical_indices,
        "logical_words": logical_words,
        "source_rule": source_rule,
        "source_id": source_id,
        "evidence": deepcopy(dict(evidence)),
        "interpretation": (
            "Candidate only. This output is not an authorization failure, "
            "research verdict, or validated committed effect."
        ),
    }


def _warning_indices(warning: Mapping[str, Any]) -> list[int]:
    evidence = warning.get("evidence", {})
    indices: list[int] = []
    if isinstance(evidence, Mapping):
        if isinstance(evidence.get("public_index"), int):
            indices.append(evidence["public_index"])
        for value in evidence.get("public_indices", []):
            if isinstance(value, int):
                indices.append(value)
    return sorted(set(indices))


def _component_candidate(
    warning: Mapping[str, Any],
    *,
    baseline: str,
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    rule = warning.get("rule")
    return _candidate(
        baseline=baseline,
        kind=f"component-warning:{rule}",
        classification="component_candidate",
        indices=_warning_indices(warning),
        target_identity=target_identity,
        policy=policy,
        evidence={
            "source_evidence": warning.get("evidence", {}),
            "target_rule": rule,
        },
        source_rule=rule,
        source_id=warning.get("source_id", warning.get("id")),
    )


def _component_baseline(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
    *,
    baseline: str,
    allowed_rules: frozenset[str],
) -> dict[str, Any]:
    if _component_status(record, "static") != "SUPPORTED":
        return {
            "status": "UNKNOWN",
            "reason": "STATIC_COMPONENT_NOT_SUPPORTED",
            "candidates": [],
        }
    static = record.get("static_analysis")
    if not isinstance(static, Mapping):
        raise CompositionInputError("supported static component has no static_analysis")
    return {
        "status": "SUPPORTED",
        "reason": None,
        "candidates": [
            _component_candidate(
                warning,
                baseline=baseline,
                policy=policy,
                target_identity=target_identity,
            )
            for warning in static.get("warnings", [])
            if warning.get("rule") in allowed_rules
        ],
        "information_budget": {
            "source": "existing static warning outputs",
            "allowed_rules": sorted(allowed_rules),
            "cross_layer_synthesis": False,
            "output_limit": (
                "Producer-side candidate only; no effect authorization claim."
                if baseline == "producer-only"
                else "Consumer-side candidate only; no proof relation claim."
            ),
        },
        "scoring_readiness": "DRAFT_UNSEALED",
    }


def _union_baseline(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if _component_status(record, "static") != "SUPPORTED":
        return {
            "status": "UNKNOWN",
            "reason": "STATIC_COMPONENT_NOT_SUPPORTED",
            "candidates": [],
        }
    static = record.get("static_analysis")
    if not isinstance(static, Mapping):
        raise CompositionInputError("supported static component has no static_analysis")
    candidates = []
    for warning in static.get("warnings", []):
        rule = warning.get("rule")
        if rule not in UNION_RULES:
            continue
        origin = "producer-only" if rule in PRODUCER_ONLY_RULES else "consumer-only"
        candidate = _component_candidate(
            warning,
            baseline="unjoined-union",
            policy=policy,
            target_identity=target_identity,
        )
        candidate["evidence"]["origin_arm"] = origin
        candidates.append(candidate)
    return {
        "status": "SUPPORTED",
        "reason": None,
        "candidates": candidates,
        "information_budget": {
            "source": "existing static warning outputs",
            "producer_rules": sorted(PRODUCER_ONLY_RULES),
            "consumer_rules": sorted(CONSUMER_ONLY_RULES),
            "cross_layer_synthesis": False,
            "note": (
                "This is the existing D1P-41/D1P-43 output-mask ablation, "
                "not an independent re-extraction or independent tool."
            ),
        },
        "scoring_readiness": "DRAFT_UNSEALED",
    }


def _full_adapter(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if record.get("support_status") != "SUPPORTED":
        return {
            "status": "UNKNOWN",
            "reason": "INTEGRATED_ANALYSIS_NOT_SUPPORTED",
            "candidates": [],
        }
    candidates = []
    for warning in record.get("warnings", []):
        rule = warning.get("rule")
        candidates.append(
            _candidate(
                baseline="full-bindcheck",
                kind=f"integrated-warning:{rule}",
                classification="integrated_candidate",
                indices=_warning_indices(warning),
                target_identity=target_identity,
                policy=policy,
                evidence={
                    "analysis_component": warning.get("analysis_component"),
                    "source_evidence": warning.get("evidence", {}),
                    "target_rule": rule,
                },
                source_rule=rule,
                source_id=warning.get("source_id", warning.get("id")),
            )
        )
    return {
        "status": "SUPPORTED",
        "reason": None,
        "candidates": candidates,
        "outcome": deepcopy(record.get("outcome")),
        "information_budget": {
            "source": "frozen integrated-analysis output",
            "shared_policy_hash_recorded": True,
            "policy_consumed_by_current_analyzer": False,
            "limit": (
                "The current integrated analyzer consumes its frozen rule/policy "
                "configuration, not the generic Step-6a P/O/E obligation object. "
                "Step 7 must not claim equal-policy authorization scoring unless "
                "this interface mismatch is resolved prospectively."
            ),
        },
        "scoring_readiness": "UNRESOLVED_EQUAL_POLICY_INTERFACE",
    }


def _word_tables(static: Mapping[str, Any]) -> tuple[dict[int, Any], dict[int, Any]]:
    producer_words: dict[int, Any] = {}
    for word in static.get("producer", {}).get("public_leaves", []):
        index = word.get("public_index")
        if not isinstance(index, int) or index in producer_words:
            raise CompositionInputError(f"invalid or duplicate producer public index: {index!r}")
        producer_words[index] = word
    consumer_words: dict[int, Any] = {}
    for word in static.get("consumer", {}).get("public_words", []):
        index = word.get("index")
        if not isinstance(index, int) or index in consumer_words:
            raise CompositionInputError(f"invalid or duplicate consumer public index: {index!r}")
        consumer_words[index] = word
    return producer_words, consumer_words


def _basic_candidates(
    static: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
    *,
    baseline: str,
) -> list[dict[str, Any]]:
    producer_words, consumer_words = _word_tables(static)
    effect_indices = {
        value
        for value in static.get("consumer", {}).get("effect_word_indices", [])
        if isinstance(value, int)
    }
    candidates: list[dict[str, Any]] = []
    for index in sorted(set(producer_words) | set(consumer_words)):
        producer = producer_words.get(index)
        consumer = consumer_words.get(index)
        if producer is None or consumer is None:
            candidates.append(
                _candidate(
                    baseline=baseline,
                    kind="public-input-mapping-gap",
                    classification="structural_candidate",
                    indices=[index],
                    target_identity=target_identity,
                    policy=policy,
                    evidence={
                        "producer_word_present": producer is not None,
                        "consumer_word_present": consumer is not None,
                    },
                )
            )
            continue
        occurrence_count = producer.get("occurrence_count")
        consumer_used = consumer.get("consumer_used")
        effect_relevant = index in effect_indices
        if occurrence_count == 0 and (consumer_used is True or effect_relevant):
            candidates.append(
                _candidate(
                    baseline=baseline,
                    kind="consumer-reliance-without-producer-occurrence",
                    classification="structural_candidate",
                    indices=[index],
                    target_identity=target_identity,
                    policy=policy,
                    evidence={
                        "producer_path": producer.get("path"),
                        "producer_occurrence_count": 0,
                        "producer_binding_condition": producer.get("binding_condition"),
                        "consumer_origin": consumer.get("origin"),
                        "consumer_used": consumer_used,
                        "effect_relevant": effect_relevant,
                    },
                )
            )
        elif isinstance(occurrence_count, int) and occurrence_count > 0 and consumer_used is False:
            candidates.append(
                _candidate(
                    baseline=baseline,
                    kind="producer-word-without-consumer-dataflow",
                    classification="structural_candidate",
                    indices=[index],
                    target_identity=target_identity,
                    policy=policy,
                    evidence={
                        "producer_path": producer.get("path"),
                        "producer_occurrence_count": occurrence_count,
                        "consumer_origin": consumer.get("origin"),
                        "consumer_used": False,
                        "effect_relevant": effect_relevant,
                    },
                )
            )
    return candidates


def _basic_baseline(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if _component_status(record, "static") != "SUPPORTED":
        return {
            "status": "UNKNOWN",
            "reason": "STATIC_COMPONENT_NOT_SUPPORTED",
            "candidates": [],
        }
    static = record.get("static_analysis")
    if not isinstance(static, Mapping):
        raise CompositionInputError("supported static component has no static_analysis")
    return {
        "status": "SUPPORTED",
        "reason": None,
        "candidates": _basic_candidates(
            static,
            policy,
            target_identity,
            baseline="basic-structural-composition",
        ),
        "information_budget": {
            "shared_extracted_fields": [
                "producer.public_leaves[].public_index",
                "producer.public_leaves[].occurrence_count",
                "producer.public_leaves[].binding_condition",
                "consumer.public_words[].index",
                "consumer.public_words[].consumer_used",
                "consumer.effect_word_indices",
            ],
            "policy_fields": ["word_identities", "comparison_group"],
            "conditional_extent_facts": False,
            "role_annotations": False,
            "classification": "structural candidates only",
        },
        "scoring_readiness": "DRAFT_UNSEALED",
    }


def _extent_candidates(
    static: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for coverage in static.get("extent_facts", {}).get("coverage", []):
        if coverage.get("status") != "EXACT" or coverage.get("covered") is not False:
            continue
        key = (
            str(coverage.get("producer_condition")),
            str(coverage.get("consumer_condition")),
            str(coverage.get("uncovered_region")),
        )
        groups[key].append(coverage)
    result = []
    for (producer_condition, consumer_condition, uncovered_region), items in sorted(groups.items()):
        indices = [item["public_index"] for item in items if isinstance(item.get("public_index"), int)]
        result.append(
            _candidate(
                baseline="strong-simple-composition",
                kind="conditional-extent-gap",
                classification="semantic_candidate",
                indices=indices,
                target_identity=target_identity,
                policy=policy,
                evidence={
                    "producer_condition": producer_condition,
                    "consumer_condition": consumer_condition,
                    "uncovered_region": uncovered_region,
                    "public_indices": indices,
                    "paths": [item.get("path") for item in items],
                },
            )
        )
    return result


def _role_candidates(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    role = record.get("role_binding")
    if not isinstance(role, Mapping) or role.get("status") != "SUPPORTED":
        return [], "ROLE_COMPONENT_NOT_SUPPORTED"
    result = []
    for word in role.get("words", []):
        correspondence = word.get("boundary_correspondence")
        if correspondence == "match":
            continue
        index = word.get("public_index")
        if not isinstance(index, int):
            raise CompositionInputError("role word has no integer public_index")
        producer = word.get("producer", {})
        consumer = word.get("consumer", {})
        result.append(
            _candidate(
                baseline="strong-simple-composition",
                kind="role-correspondence-gap",
                classification="semantic_candidate",
                indices=[index],
                target_identity=target_identity,
                policy=policy,
                evidence={
                    "boundary_correspondence": correspondence,
                    "producer_role": producer.get("boundary_role"),
                    "producer_identity": producer.get("identity", []),
                    "consumer_role": consumer.get("boundary_role"),
                    "consumer_identity": consumer.get("identity", []),
                    "consumer_effect_roles": sorted(
                        {
                            str(effect.get("role"))
                            for effect in consumer.get("effects", [])
                            if effect.get("role")
                        }
                    ),
                    "consumer_state_polarities": sorted(
                        {
                            str(check.get("polarity"))
                            for check in consumer.get("state_checks", [])
                            if check.get("polarity")
                        }
                    ),
                },
            )
        )
    return result, None


def _indices_for_obligation(
    obligation: Mapping[str, Any], policy: Mapping[str, Any]
) -> list[int]:
    indices = [value for value in obligation.get("public_indices", []) if isinstance(value, int)]
    word_ids = obligation.get("word_ids", [])
    if word_ids:
        reverse = {identity: index for index, identity in policy["word_identities"].items()}
        for word_id in word_ids:
            if word_id not in reverse:
                raise CompositionInputError(
                    f"obligation {obligation.get('id')} names unknown word identity {word_id!r}"
                )
            indices.append(reverse[word_id])
    if not indices:
        raise CompositionInputError(
            f"obligation {obligation.get('id')} needs public_indices or word_ids"
        )
    return sorted(set(indices))


def _policy_obligations(
    record: Mapping[str, Any],
    static: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    producer_words, consumer_words = _word_tables(static)
    coverage = {
        item.get("public_index"): item
        for item in static.get("extent_facts", {}).get("coverage", [])
        if isinstance(item.get("public_index"), int)
    }
    role = record.get("role_binding", {})
    role_words = {
        item.get("public_index"): item
        for item in role.get("words", [])
        if isinstance(item.get("public_index"), int)
    } if isinstance(role, Mapping) and role.get("status") == "SUPPORTED" else {}
    candidates: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    supported_checks = {
        "producer_binding",
        "consumer_dataflow",
        "extent_coverage",
        "role_correspondence",
    }
    for obligation in policy["obligations"]:
        checks = obligation.get("checks", [])
        if not isinstance(checks, list) or not checks:
            raise CompositionInputError(
                f"obligation {obligation['id']} needs at least one check"
            )
        unsupported = sorted(set(checks) - supported_checks)
        if unsupported:
            raise CompositionInputError(
                f"obligation {obligation['id']} has unsupported checks: {unsupported}"
            )
        indices = _indices_for_obligation(obligation, policy)
        failed: list[str] = []
        missing: list[str] = []
        for check in checks:
            for index in indices:
                if check == "producer_binding":
                    word = producer_words.get(index)
                    if word is None:
                        missing.append(f"producer_binding:{index}")
                    elif word.get("binding_condition", {}).get("kind") == "never":
                        failed.append(f"producer_binding:{index}")
                elif check == "consumer_dataflow":
                    word = consumer_words.get(index)
                    if word is None:
                        missing.append(f"consumer_dataflow:{index}")
                    elif word.get("consumer_used") is not True:
                        failed.append(f"consumer_dataflow:{index}")
                elif check == "extent_coverage":
                    item = coverage.get(index)
                    if item is None or item.get("status") != "EXACT":
                        missing.append(f"extent_coverage:{index}")
                    elif item.get("covered") is not True:
                        failed.append(f"extent_coverage:{index}")
                elif check == "role_correspondence":
                    item = role_words.get(index)
                    if item is None:
                        missing.append(f"role_correspondence:{index}")
                    elif item.get("boundary_correspondence") != "match":
                        failed.append(f"role_correspondence:{index}")
        status = "UNKNOWN" if missing else ("CANDIDATE" if failed else "SATISFIED")
        result = {
            "obligation_id": obligation["id"],
            "status": status,
            "public_indices": indices,
            "logical_words": _logical_words(indices, policy),
            "checks": checks,
            "failed_checks": sorted(set(failed)),
            "missing_facts": sorted(set(missing)),
        }
        results.append(result)
        if failed and not missing:
            candidates.append(
                _candidate(
                    baseline="strong-simple-composition",
                    kind="policy-obligation-gap",
                    classification="policy_candidate",
                    indices=indices,
                    target_identity=target_identity,
                    policy=policy,
                    evidence={
                        "obligation_id": obligation["id"],
                        "checks": checks,
                        "failed_checks": sorted(
                            {item.split(":", 1)[0] for item in failed}
                        ),
                        "public_indices": indices,
                    },
                )
            )
    return candidates, results


def _strong_baseline(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    target_identity: Mapping[str, Any],
) -> dict[str, Any]:
    if _component_status(record, "static") != "SUPPORTED":
        return {
            "status": "UNKNOWN",
            "reason": "STATIC_COMPONENT_NOT_SUPPORTED",
            "candidates": [],
            "obligation_results": [],
        }
    static = record.get("static_analysis")
    if not isinstance(static, Mapping):
        raise CompositionInputError("supported static component has no static_analysis")
    candidates = _basic_candidates(
        static,
        policy,
        target_identity,
        baseline="strong-simple-composition",
    )
    candidates.extend(_extent_candidates(static, policy, target_identity))
    role_candidates, role_limit = _role_candidates(record, policy, target_identity)
    candidates.extend(role_candidates)
    policy_candidates, obligation_results = _policy_obligations(
        record, static, policy, target_identity
    )
    candidates.extend(policy_candidates)
    return {
        "status": "SUPPORTED",
        "reason": None,
        "candidates": candidates,
        "obligation_results": obligation_results,
        "component_limits": [role_limit] if role_limit else [],
        "information_budget": {
            "shared_extracted_fields": [
                "all basic-structural fields",
                "extent_facts.coverage",
                "role_binding.words when supported",
            ],
            "policy_fields": [
                "comparison_group",
                "word_identities",
                "obligations[].id",
                "obligations[].word_ids/public_indices",
                "obligations[].checks",
            ],
            "straightforward_operations": [
                "positional joins",
                "condition coverage lookup",
                "role equality",
                "direct obligation checks",
            ],
            "withheld_from_baseline": [],
            "cost_scope": "composition only; extraction and annotations are shared",
        },
        "scoring_readiness": (
            "DRAFT_UNSEALED"
            if policy["review_status"] == "HUMAN_REVIEWED"
            else "UNRESOLVED_POLICY_NOT_HUMAN_REVIEWED"
        ),
    }


def compose(
    record: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Run all three construction baselines over one integrated record."""
    started = time.perf_counter()
    schema = record.get("schema")
    if not isinstance(schema, str) or not schema.startswith("bindcheck.integrated-analysis"):
        raise CompositionInputError(f"unsupported integrated record schema: {schema!r}")
    target = record.get("target")
    if not isinstance(target, str) or not target:
        raise CompositionInputError("integrated record needs a non-empty target")
    normalized_policy = _policy_or_default(policy, target)
    target_identity = _target_identity(record)
    def timed(call: Any) -> dict[str, Any]:
        arm_started = time.perf_counter()
        result = call()
        result["composition_runtime_seconds"] = time.perf_counter() - arm_started
        return result

    baselines = {
        "producer-only": timed(lambda: _component_baseline(
            record,
            normalized_policy,
            target_identity,
            baseline="producer-only",
            allowed_rules=PRODUCER_ONLY_RULES,
        )),
        "consumer-only": timed(lambda: _component_baseline(
            record,
            normalized_policy,
            target_identity,
            baseline="consumer-only",
            allowed_rules=CONSUMER_ONLY_RULES,
        )),
        "unjoined-union": timed(lambda: _union_baseline(
            record, normalized_policy, target_identity
        )),
        "basic-structural-composition": timed(lambda: _basic_baseline(
            record, normalized_policy, target_identity
        )),
        "strong-simple-composition": timed(lambda: _strong_baseline(
            record, normalized_policy, target_identity
        )),
        "full-bindcheck": timed(lambda: _full_adapter(
            record, normalized_policy, target_identity
        )),
    }
    for arm in baselines.values():
        arm.setdefault("scoring_readiness", "DRAFT_UNSEALED")
    all_ids = [
        candidate["candidate_id"]
        for baseline in baselines.values()
        for candidate in baseline["candidates"]
    ]
    if len(all_ids) != len(set(all_ids)):
        raise CompositionInputError("duplicate candidate_id across composition baselines")
    return {
        "schema": SCHEMA,
        "status": "CONSTRUCTION_SMOKE_TEST",
        "research_verdict": "UNKNOWN",
        "target": target,
        "target_identity": target_identity,
        "policy": {
            "schema": normalized_policy["schema"],
            "policy_id": normalized_policy["policy_id"],
            "version": normalized_policy["version"],
            "review_status": normalized_policy["review_status"],
            "policy_author": normalized_policy["policy_author"],
            "policy_reviewer": normalized_policy["policy_reviewer"],
            "comparison_group": normalized_policy["comparison_group"],
            "word_identity_count": len(normalized_policy["word_identities"]),
            "term_alias_count": len(normalized_policy["term_aliases"]),
            "obligation_count": len(normalized_policy["obligations"]),
            "sha256": hashlib.sha256(_canonical_bytes(normalized_policy)).hexdigest(),
        },
        "shared_input": {
            "integrated_schema": schema,
            "static_component_status": _component_status(record, "static"),
            "role_component_status": _component_status(record, "role_binding"),
            "extraction_cost_accounting": "shared; not re-run by this module",
        },
        "baselines": baselines,
        "composition_runtime_seconds": time.perf_counter() - started,
        "claim_limits": [
            "Construction/smoke-test output only; no final Gate A scoring occurred.",
            "All outputs are candidates. Structural candidates are not authorization failures.",
            "UNKNOWN, absence of a candidate, or a satisfied direct obligation is not safety evidence.",
            "The union is an output-mask ablation; structural and strong-simple baselines share extraction with BindCheck.",
        ],
    }


def _warning_signature(warning: Mapping[str, Any]) -> Any:
    return _strip_locations(
        {
            "rule": warning.get("rule"),
            "evidence": warning.get("evidence", {}),
            "target_identity": warning.get("target_identity", {}),
        }
    )


def audit_existing_union(result: Mapping[str, Any]) -> dict[str, Any]:
    """Verify that each D1P-43 union arm is exactly producer ∪ consumer."""
    examples = result.get("ablation_examples")
    if not isinstance(examples, list):
        raise CompositionInputError("D1P-43 result has no ablation_examples list")
    rows = []
    for example in examples:
        arms = example.get("arms", {})
        producer = arms.get("producer-only", {})
        consumer = arms.get("consumer-only", {})
        union = arms.get("unjoined-union", {})
        statuses = {arm.get("status") for arm in (producer, consumer, union)}
        if statuses == {"UNKNOWN"}:
            rows.append({"id": example.get("id"), "status": "UNKNOWN", "matches": True})
            continue
        if statuses != {"SUPPORTED"}:
            rows.append(
                {
                    "id": example.get("id"),
                    "status": "MIXED_OR_INVALID",
                    "matches": False,
                    "arm_statuses": sorted(str(status) for status in statuses),
                }
            )
            continue
        expected = {
            json.dumps(_warning_signature(warning), sort_keys=True)
            for warning in [*producer.get("warnings", []), *consumer.get("warnings", [])]
        }
        actual = {
            json.dumps(_warning_signature(warning), sort_keys=True)
            for warning in union.get("warnings", [])
        }
        rows.append(
            {
                "id": example.get("id"),
                "status": "SUPPORTED",
                "matches": expected == actual,
                "producer_candidate_count": len(producer.get("warnings", [])),
                "consumer_candidate_count": len(consumer.get("warnings", [])),
                "expected_union_count": len(expected),
                "observed_union_count": len(actual),
            }
        )
    return {
        "schema": "bindcheck.composition-union-audit/v1",
        "status": "PASS" if all(row["matches"] for row in rows) else "FAIL",
        "examples": len(rows),
        "supported_examples": sum(row["status"] == "SUPPORTED" for row in rows),
        "unknown_examples": sum(row["status"] == "UNKNOWN" for row in rows),
        "rows": rows,
        "interpretation": (
            "This verifies set composition only. It does not establish an "
            "independent baseline, detection correctness, or a research verdict."
        ),
    }
