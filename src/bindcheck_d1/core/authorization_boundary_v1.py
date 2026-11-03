"""Bounded policy/obligation/effect authorization interface.

This module is a development prototype, not the scored analyzer.  It consumes
the semantic identity and typed-fact records exported by
``roles.compiler_identity_v1``.  Identifier spelling and source locations are
not authorization evidence.

The implementation deliberately separates a bounded mechanical state from the
effective research state.  An absent or unreviewed human policy always makes
the latter ``UNKNOWN``.  ``UNREVIEWED_DEVELOPMENT_FIXTURE`` enables mechanical
tests only and can never be score eligible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from bindcheck_d1.roles.compiler_identity_v1 import (
    FACT_SCHEMA,
    IDENTITY_REFERENCE_SCHEMA,
    canonical_json_bytes,
    sha256_json,
    validate_bundle,
)


POLICY_SCHEMA = "bindcheck.poe-policy/v1"
OBLIGATION_SCHEMA = "bindcheck.authorization-obligation/v1"
EFFECT_SCHEMA = "bindcheck.protected-effect/v1"
BOUNDARY_INPUT_SCHEMA = "bindcheck.authorization-boundary-input/v1"
BOUNDARY_RESULT_SCHEMA = "bindcheck.authorization-boundary-result/v1"
EQUAL_ARMS_SCHEMA = "bindcheck.authorization-boundary-equal-input-arms/v1"

FIXTURE_POLICY_STATUS = "UNREVIEWED_DEVELOPMENT_FIXTURE"
HUMAN_REVIEWED_STATUS = "HUMAN_REVIEWED"
STATES = frozenset({"ESTABLISHED", "MISMATCH_CANDIDATE", "UNKNOWN"})
SUPPORTED_MULTIPLICITY = "ONE_TO_ONE"
SUPPORTED_FIELDS = (
    "action",
    "asset",
    "quantity",
    "beneficiary",
    "domain",
    "state_version",
)
ARMS = ("full-bindcheck", "strong-simple-composition")


class BoundaryInputError(ValueError):
    """Raised when an input cannot support the declared bounded semantics."""


def _json_value(value: Any) -> Any:
    try:
        return json.loads(canonical_json_bytes(value).decode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise BoundaryInputError(f"value is not canonical JSON: {exc}") from exc


def _text(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BoundaryInputError(f"{field_name} must be a nonempty string")
    return value


def _strings(field_name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({_text(field_name, item) for item in values}))
    return normalized


def _sha256s(field_name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _strings(field_name, values)
    for value in normalized:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise BoundaryInputError(f"{field_name} must contain lowercase SHA-256 digests")
    return normalized


def _identity_ref(value: Mapping[str, Any]) -> dict[str, str]:
    expected = {"schema", "semantic_hash", "canonical_bytes_sha256"}
    if set(value) != expected:
        raise BoundaryInputError(
            "identity references must contain exactly schema, semantic_hash, "
            "and canonical_bytes_sha256"
        )
    result = {key: _text(f"identity_ref.{key}", value[key]) for key in expected}
    if result["schema"] != IDENTITY_REFERENCE_SCHEMA:
        raise BoundaryInputError(
            f"identity reference schema must be {IDENTITY_REFERENCE_SCHEMA!r}"
        )
    digest = result["canonical_bytes_sha256"]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise BoundaryInputError("identity reference digest must be lowercase SHA-256")
    return {key: result[key] for key in sorted(result)}


def _term(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _json_value(dict(value))
    if set(normalized) == {"var"}:
        _text("term.var", normalized["var"])
        return normalized
    if set(normalized) == {"const"}:
        return normalized
    raise BoundaryInputError("term must be exactly {'var': name} or {'const': value}")


def _predicate(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _json_value(dict(value))
    op = normalized.get("op")
    if op == "const" and set(normalized) == {"op", "value"}:
        if not isinstance(normalized["value"], bool):
            raise BoundaryInputError("predicate const value must be boolean")
        return normalized
    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        if set(normalized) != {"op", "left", "right"}:
            raise BoundaryInputError(f"predicate {op} needs left and right terms")
        _term(normalized["left"])
        _term(normalized["right"])
        return normalized
    if op in {"and", "or"}:
        if set(normalized) != {"op", "args"} or not isinstance(
            normalized["args"], list
        ) or not normalized["args"]:
            raise BoundaryInputError(f"predicate {op} needs a nonempty args list")
        for item in normalized["args"]:
            if not isinstance(item, Mapping):
                raise BoundaryInputError("predicate args must be objects")
            _predicate(item)
        return normalized
    if op == "not":
        if set(normalized) != {"op", "arg"} or not isinstance(
            normalized["arg"], Mapping
        ):
            raise BoundaryInputError("predicate not needs one object arg")
        _predicate(normalized["arg"])
        return normalized
    raise BoundaryInputError(f"unsupported predicate operator: {op!r}")


def _condition(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _json_value(dict(value))
    kind = normalized.get("kind")
    if kind in {"ALWAYS", "NEVER", "UNKNOWN"}:
        allowed = {"kind", "reason_code"} if kind == "UNKNOWN" else {"kind"}
        if set(normalized) != allowed:
            raise BoundaryInputError(f"condition {kind} has invalid fields")
        if kind == "UNKNOWN":
            _text("condition.reason_code", normalized.get("reason_code"))
        return normalized
    if kind == "PREDICATE" and set(normalized) == {"kind", "predicate"}:
        if not isinstance(normalized["predicate"], Mapping):
            raise BoundaryInputError("PREDICATE condition needs a predicate object")
        _predicate(normalized["predicate"])
        return normalized
    raise BoundaryInputError(f"unsupported condition kind: {kind!r}")


def _field_terms(value: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    if set(value) != set(SUPPORTED_FIELDS):
        raise BoundaryInputError(
            "P/O/E fields must be exactly " + ", ".join(SUPPORTED_FIELDS)
        )
    return {name: _term(value[name]) for name in SUPPORTED_FIELDS}


@dataclass(frozen=True)
class PermissionRecord:
    """One reviewed-policy permission over a protected occurrence."""

    permission_id: str
    authorizing_identity_ref: Mapping[str, str]
    protected_effect_identity_ref: Mapping[str, str]
    fields: Mapping[str, Mapping[str, Any]]
    condition: Mapping[str, Any] = field(default_factory=lambda: {"kind": "ALWAYS"})
    multiplicity: str = SUPPORTED_MULTIPLICITY

    def __post_init__(self) -> None:
        _text("permission_id", self.permission_id)
        object.__setattr__(
            self, "authorizing_identity_ref", _identity_ref(self.authorizing_identity_ref)
        )
        object.__setattr__(
            self,
            "protected_effect_identity_ref",
            _identity_ref(self.protected_effect_identity_ref),
        )
        object.__setattr__(self, "fields", _field_terms(self.fields))
        object.__setattr__(self, "condition", _condition(self.condition))
        if self.multiplicity != SUPPORTED_MULTIPLICITY:
            raise BoundaryInputError(
                "only occurrence-level ONE_TO_ONE multiplicity is supported"
            )

    def canonical(self) -> dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "authorizing_identity_ref": dict(self.authorizing_identity_ref),
            "protected_effect_identity_ref": dict(self.protected_effect_identity_ref),
            "fields": dict(self.fields),
            "condition": dict(self.condition),
            "multiplicity": self.multiplicity,
        }


@dataclass(frozen=True)
class PolicyRecord:
    """Versioned policy record with an explicit review gate."""

    policy_id: str
    version: str
    review_status: str
    permissions: tuple[PermissionRecord, ...]
    policy_author_ref: str | None = None
    policy_reviewer_ref: str | None = None
    source_sha256: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("policy_id", self.policy_id)
        _text("policy.version", self.version)
        if self.review_status not in {FIXTURE_POLICY_STATUS, HUMAN_REVIEWED_STATUS}:
            raise BoundaryInputError(f"unsupported policy review status: {self.review_status}")
        ids = [item.permission_id for item in self.permissions]
        if len(ids) != len(set(ids)):
            raise BoundaryInputError("policy permission ids must be unique")
        object.__setattr__(self, "source_sha256", _sha256s("source_sha256", self.source_sha256))
        object.__setattr__(self, "limitations", _strings("policy limitation", self.limitations))

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": POLICY_SCHEMA,
            "policy_id": self.policy_id,
            "version": self.version,
            "review_status": self.review_status,
            "policy_author_ref": self.policy_author_ref,
            "policy_reviewer_ref": self.policy_reviewer_ref,
            "source_sha256": list(self.source_sha256),
            "permissions": [
                item.canonical()
                for item in sorted(self.permissions, key=lambda item: item.permission_id)
            ],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class AuthorizationObligation:
    """A relying-path authorization obligation tied to typed identity facts."""

    obligation_id: str
    protected_effect_id: str
    authorization_identity_ref: Mapping[str, str]
    protected_effect_identity_ref: Mapping[str, str]
    producer_fact_ids: tuple[str, ...]
    reliance_fact_ids: tuple[str, ...]
    fields: Mapping[str, Mapping[str, Any]]
    activation: Mapping[str, Any]
    discharge: Mapping[str, Any]
    multiplicity: str = SUPPORTED_MULTIPLICITY
    requires_proof_authorization: bool = True
    assumption_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("obligation_id", self.obligation_id)
        _text("protected_effect_id", self.protected_effect_id)
        object.__setattr__(
            self, "authorization_identity_ref", _identity_ref(self.authorization_identity_ref)
        )
        object.__setattr__(
            self,
            "protected_effect_identity_ref",
            _identity_ref(self.protected_effect_identity_ref),
        )
        object.__setattr__(
            self, "producer_fact_ids", _strings("producer_fact_id", self.producer_fact_ids)
        )
        object.__setattr__(
            self, "reliance_fact_ids", _strings("reliance_fact_id", self.reliance_fact_ids)
        )
        if not self.producer_fact_ids:
            raise BoundaryInputError("obligation requires at least one producer fact")
        if not self.reliance_fact_ids:
            raise BoundaryInputError("obligation requires at least one reliance fact")
        object.__setattr__(self, "fields", _field_terms(self.fields))
        object.__setattr__(self, "activation", _condition(self.activation))
        object.__setattr__(self, "discharge", _condition(self.discharge))
        object.__setattr__(
            self, "assumption_refs", _strings("assumption_ref", self.assumption_refs)
        )
        if self.multiplicity != SUPPORTED_MULTIPLICITY:
            raise BoundaryInputError("aggregation, splitting, and deferral are unsupported")

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": OBLIGATION_SCHEMA,
            "obligation_id": self.obligation_id,
            "protected_effect_id": self.protected_effect_id,
            "authorization_identity_ref": dict(self.authorization_identity_ref),
            "protected_effect_identity_ref": dict(self.protected_effect_identity_ref),
            "producer_fact_ids": list(self.producer_fact_ids),
            "reliance_fact_ids": list(self.reliance_fact_ids),
            "fields": dict(self.fields),
            "activation": dict(self.activation),
            "discharge": dict(self.discharge),
            "multiplicity": self.multiplicity,
            "requires_proof_authorization": self.requires_proof_authorization,
            "assumption_refs": list(self.assumption_refs),
        }


@dataclass(frozen=True)
class ProtectedEffect:
    """A bounded consumer effect occurrence on one relying path."""

    effect_id: str
    protected_effect_identity_ref: Mapping[str, str]
    fields: Mapping[str, Mapping[str, Any]]
    path_condition: Mapping[str, Any]
    source_fact_ids: tuple[str, ...]
    alternative_authorization_refs: tuple[str, ...] = ()
    multiplicity: str = SUPPORTED_MULTIPLICITY

    def __post_init__(self) -> None:
        _text("effect_id", self.effect_id)
        object.__setattr__(
            self,
            "protected_effect_identity_ref",
            _identity_ref(self.protected_effect_identity_ref),
        )
        object.__setattr__(self, "fields", _field_terms(self.fields))
        object.__setattr__(self, "path_condition", _condition(self.path_condition))
        object.__setattr__(
            self, "source_fact_ids", _strings("source_fact_id", self.source_fact_ids)
        )
        object.__setattr__(
            self,
            "alternative_authorization_refs",
            _strings("alternative_authorization_ref", self.alternative_authorization_refs),
        )
        if self.multiplicity != SUPPORTED_MULTIPLICITY:
            raise BoundaryInputError("effect multiplicity is outside the supported fragment")

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": EFFECT_SCHEMA,
            "effect_id": self.effect_id,
            "protected_effect_identity_ref": dict(self.protected_effect_identity_ref),
            "fields": dict(self.fields),
            "path_condition": dict(self.path_condition),
            "source_fact_ids": list(self.source_fact_ids),
            "alternative_authorization_refs": list(self.alternative_authorization_refs),
            "multiplicity": self.multiplicity,
        }


@dataclass(frozen=True)
class BoundedQuery:
    """Finite-domain query declaration; no implicit or unbounded variables."""

    variable_domains: Mapping[str, Sequence[Any]]
    attacker_controlled: tuple[str, ...]
    fixed_authenticated_context: Mapping[str, Any]
    max_assignments: int

    def __post_init__(self) -> None:
        normalized_domains: dict[str, list[Any]] = {}
        for name, values in sorted(self.variable_domains.items()):
            _text("query variable", name)
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
                raise BoundaryInputError(f"domain for {name} must be a sequence")
            normalized = [_json_value(value) for value in values]
            if not normalized:
                raise BoundaryInputError(f"domain for {name} cannot be empty")
            if len({canonical_json_bytes(item) for item in normalized}) != len(normalized):
                raise BoundaryInputError(f"domain for {name} contains duplicates")
            normalized_domains[name] = normalized
        object.__setattr__(self, "variable_domains", normalized_domains)
        object.__setattr__(
            self,
            "attacker_controlled",
            _strings("attacker-controlled variable", self.attacker_controlled),
        )
        if not set(self.attacker_controlled).issubset(normalized_domains):
            raise BoundaryInputError("every attacker-controlled variable needs a domain")
        fixed = _json_value(dict(self.fixed_authenticated_context))
        if set(fixed).intersection(normalized_domains):
            raise BoundaryInputError("fixed context and quantified domains must be disjoint")
        object.__setattr__(self, "fixed_authenticated_context", fixed)
        if not isinstance(self.max_assignments, int) or self.max_assignments <= 0:
            raise BoundaryInputError("max_assignments must be a positive integer")

    def canonical(self) -> dict[str, Any]:
        return {
            "variable_domains": dict(self.variable_domains),
            "attacker_controlled": list(self.attacker_controlled),
            "fixed_authenticated_context": dict(self.fixed_authenticated_context),
            "max_assignments": self.max_assignments,
        }


@dataclass(frozen=True)
class BoundaryInput:
    """Common, hash-bearing input consumed without arm-specific enrichment."""

    case_id: str
    identity_bundle: Mapping[str, Any]
    policy: PolicyRecord | None
    obligations: tuple[AuthorizationObligation, ...]
    effects: tuple[ProtectedEffect, ...]
    query: BoundedQuery
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("case_id", self.case_id)
        object.__setattr__(self, "identity_bundle", _json_value(dict(self.identity_bundle)))
        ids = [item.obligation_id for item in self.obligations]
        if len(ids) != len(set(ids)):
            raise BoundaryInputError("obligation ids must be unique")
        effect_ids = [item.effect_id for item in self.effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise BoundaryInputError("effect ids must be unique")
        object.__setattr__(self, "assumptions", _strings("assumption", self.assumptions))
        object.__setattr__(self, "limitations", _strings("limitation", self.limitations))

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": BOUNDARY_INPUT_SCHEMA,
            "case_id": self.case_id,
            "identity_bundle": dict(self.identity_bundle),
            "policy": self.policy.canonical() if self.policy else None,
            "obligations": [
                item.canonical()
                for item in sorted(self.obligations, key=lambda item: item.obligation_id)
            ],
            "effects": [
                item.canonical()
                for item in sorted(self.effects, key=lambda item: item.effect_id)
            ],
            "query": self.query.canonical(),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }

    @property
    def input_sha256(self) -> str:
        return sha256_json(self.canonical())


@dataclass(frozen=True)
class ObligationResult:
    obligation_id: str
    state: str
    mechanical_state: str
    reason_codes: tuple[str, ...]
    fact_assessments: tuple[Mapping[str, Any], ...]
    assignment_count: int
    relying_assignment_count: int
    counterexample: Mapping[str, Any] | None

    def __post_init__(self) -> None:
        if self.state not in STATES or self.mechanical_state not in STATES:
            raise BoundaryInputError("obligation result contains an invalid state")

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "state": self.state,
            "mechanical_state": self.mechanical_state,
            "reason_codes": list(self.reason_codes),
            "fact_assessments": [dict(item) for item in self.fact_assessments],
            "assignment_count": self.assignment_count,
            "relying_assignment_count": self.relying_assignment_count,
            "counterexample": dict(self.counterexample) if self.counterexample else None,
        }


@dataclass(frozen=True)
class BoundaryResult:
    arm: str
    case_id: str
    state: str
    policy_gate: str
    reason_codes: tuple[str, ...]
    input_sha256: str
    policy_sha256: str | None
    identity_bundle_sha256: str
    fact_set_sha256: str
    obligation_results: tuple[ObligationResult, ...]
    score_eligible: bool = False
    evidence_grade: str = "E0"
    research_verdict: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BOUNDARY_RESULT_SCHEMA,
            "arm": self.arm,
            "case_id": self.case_id,
            "state": self.state,
            "policy_gate": self.policy_gate,
            "reason_codes": list(self.reason_codes),
            "input_sha256": self.input_sha256,
            "policy_sha256": self.policy_sha256,
            "identity_bundle_sha256": self.identity_bundle_sha256,
            "fact_set_sha256": self.fact_set_sha256,
            "obligation_results": [item.to_dict() for item in self.obligation_results],
            "score_eligible": self.score_eligible,
            "evidence_grade": self.evidence_grade,
            "research_verdict": self.research_verdict,
        }


def _known_identity_refs(bundle: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    return {
        item["semantic_hash"]: {
            "schema": IDENTITY_REFERENCE_SCHEMA,
            "semantic_hash": item["semantic_hash"],
            "canonical_bytes_sha256": item["canonical_bytes_sha256"],
        }
        for item in bundle["identities"]
    }


def _check_ref(ref: Mapping[str, str], known: Mapping[str, Mapping[str, str]]) -> None:
    semantic_hash = ref["semantic_hash"]
    if semantic_hash not in known or dict(ref) != known[semantic_hash]:
        raise BoundaryInputError(f"unknown or noncanonical identity reference: {semantic_hash}")


def _fact_ref(value: Any, field_name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise BoundaryInputError(f"{field_name} must be an exact opaque identity reference")
    return _identity_ref(value)


def _variables_in_term(term: Mapping[str, Any]) -> set[str]:
    return {term["var"]} if "var" in term else set()


def _variables_in_predicate(predicate: Mapping[str, Any]) -> set[str]:
    op = predicate["op"]
    if op == "const":
        return set()
    if op in {"eq", "ne", "lt", "le", "gt", "ge"}:
        return _variables_in_term(predicate["left"]) | _variables_in_term(predicate["right"])
    if op in {"and", "or"}:
        return set().union(*(_variables_in_predicate(item) for item in predicate["args"]))
    return _variables_in_predicate(predicate["arg"])


def _variables_in_condition(condition: Mapping[str, Any]) -> set[str]:
    if condition["kind"] != "PREDICATE":
        return set()
    return _variables_in_predicate(condition["predicate"])


def validate_boundary_input(boundary: BoundaryInput) -> dict[str, Any]:
    """Validate hashes, references, fact roles, and finite-query closure."""
    bundle_check = validate_bundle(boundary.identity_bundle)
    known_refs = _known_identity_refs(boundary.identity_bundle)
    facts = {item["fact_id"]: item for item in boundary.identity_bundle["facts"]}
    effects = {item.effect_id: item for item in boundary.effects}
    identity_chain_issues: list[dict[str, str]] = []
    fact_condition_issues: list[dict[str, str]] = []

    for effect in boundary.effects:
        _check_ref(effect.protected_effect_identity_ref, known_refs)
        for fact_id in effect.source_fact_ids:
            if fact_id not in facts:
                raise BoundaryInputError(f"effect references unknown fact: {fact_id}")
    for obligation in boundary.obligations:
        _check_ref(obligation.authorization_identity_ref, known_refs)
        _check_ref(obligation.protected_effect_identity_ref, known_refs)
        if obligation.protected_effect_id not in effects:
            raise BoundaryInputError(
                f"obligation references unknown effect: {obligation.protected_effect_id}"
            )
        effect = effects[obligation.protected_effect_id]
        if dict(effect.protected_effect_identity_ref) != dict(
            obligation.protected_effect_identity_ref
        ):
            raise BoundaryInputError("obligation/effect identity reference mismatch")
        for fact_id in (*obligation.producer_fact_ids, *obligation.reliance_fact_ids):
            if fact_id not in facts:
                raise BoundaryInputError(f"obligation references unknown fact: {fact_id}")
        producer_objects: list[dict[str, str]] = []
        reliance_objects: list[dict[str, str]] = []
        for fact_id in obligation.producer_fact_ids:
            fact = facts[fact_id]
            subject = _fact_ref(fact.get("subject_identity_ref"), "producer subject")
            object_ref = fact.get("object_identity_ref")
            if subject != dict(obligation.authorization_identity_ref):
                identity_chain_issues.append({
                    "obligation_id": obligation.obligation_id,
                    "fact_id": fact_id,
                    "reason_code": "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
                })
            if object_ref is None:
                identity_chain_issues.append({
                    "obligation_id": obligation.obligation_id,
                    "fact_id": fact_id,
                    "reason_code": "PRODUCER_VALUE_IDENTITY_MISSING",
                })
            else:
                producer_objects.append(_fact_ref(object_ref, "producer object"))
        for fact_id in obligation.reliance_fact_ids:
            fact = facts[fact_id]
            subject = _fact_ref(fact.get("subject_identity_ref"), "reliance subject")
            object_ref = fact.get("object_identity_ref")
            if subject != dict(obligation.protected_effect_identity_ref):
                identity_chain_issues.append({
                    "obligation_id": obligation.obligation_id,
                    "fact_id": fact_id,
                    "reason_code": "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH",
                })
            if fact_id not in effect.source_fact_ids:
                identity_chain_issues.append({
                    "obligation_id": obligation.obligation_id,
                    "fact_id": fact_id,
                    "reason_code": "RELIANCE_FACT_NOT_BOUND_TO_EFFECT",
                })
            if object_ref is None:
                identity_chain_issues.append({
                    "obligation_id": obligation.obligation_id,
                    "fact_id": fact_id,
                    "reason_code": "RELIANCE_VALUE_IDENTITY_MISSING",
                })
            else:
                reliance_objects.append(_fact_ref(object_ref, "reliance object"))
        chain_objects = producer_objects + reliance_objects
        if chain_objects and any(item != chain_objects[0] for item in chain_objects[1:]):
            identity_chain_issues.append({
                "obligation_id": obligation.obligation_id,
                "fact_id": "MULTIPLE",
                "reason_code": "PRODUCER_RELIANCE_VALUE_IDENTITY_MISMATCH",
            })

    if boundary.policy:
        for permission in boundary.policy.permissions:
            _check_ref(permission.authorizing_identity_ref, known_refs)
            _check_ref(permission.protected_effect_identity_ref, known_refs)

    declared = set(boundary.query.variable_domains) | set(
        boundary.query.fixed_authenticated_context
    )
    used: set[str] = set()
    for fact in facts.values():
        try:
            condition = _condition(fact["condition"])
        except BoundaryInputError:
            fact_condition_issues.append({
                "fact_id": fact["fact_id"],
                "reason_code": "FACT_CONDITION_UNSUPPORTED",
            })
        else:
            used.update(_variables_in_condition(condition))
    for obligation in boundary.obligations:
        for term in obligation.fields.values():
            used.update(_variables_in_term(term))
        used.update(_variables_in_condition(obligation.activation))
        used.update(_variables_in_condition(obligation.discharge))
    for effect in boundary.effects:
        for term in effect.fields.values():
            used.update(_variables_in_term(term))
        used.update(_variables_in_condition(effect.path_condition))
    if boundary.policy:
        for permission in boundary.policy.permissions:
            for term in permission.fields.values():
                used.update(_variables_in_term(term))
            used.update(_variables_in_condition(permission.condition))
    if not used.issubset(declared):
        raise BoundaryInputError(
            "undeclared variables in P/O/E input: " + ", ".join(sorted(used - declared))
        )

    assignment_space = math.prod(
        len(values) for values in boundary.query.variable_domains.values()
    )
    return {
        "status": "PASS",
        "schema": BOUNDARY_INPUT_SCHEMA,
        "case_id": boundary.case_id,
        "input_sha256": boundary.input_sha256,
        "identity_bundle": bundle_check,
        "identity_bundle_sha256": sha256_json(boundary.identity_bundle),
        "fact_set_sha256": sha256_json(sorted(facts)),
        "policy_sha256": sha256_json(boundary.policy.canonical()) if boundary.policy else None,
        "obligation_count": len(boundary.obligations),
        "effect_count": len(boundary.effects),
        "assignment_space": assignment_space,
        "identity_chain_status": "PASS" if not identity_chain_issues else "UNKNOWN",
        "identity_chain_issues": identity_chain_issues,
        "fact_condition_status": "PASS" if not fact_condition_issues else "UNKNOWN",
        "fact_condition_issues": fact_condition_issues,
    }


def _policy_gate(policy: PolicyRecord | None) -> tuple[str, tuple[str, ...]]:
    if policy is None:
        return "FAIL_CLOSED", ("HUMAN_POLICY_ABSENT",)
    if policy.review_status == FIXTURE_POLICY_STATUS:
        return "FAIL_CLOSED", ("HUMAN_POLICY_UNREVIEWED_DEVELOPMENT_FIXTURE",)
    if not policy.policy_author_ref:
        return "FAIL_CLOSED", ("HUMAN_POLICY_AUTHOR_OR_ADOPTION_MISSING",)
    if not policy.policy_reviewer_ref:
        return "FAIL_CLOSED", ("DISTINCT_HUMAN_POLICY_REVIEW_MISSING",)
    if policy.policy_author_ref == policy.policy_reviewer_ref:
        return "FAIL_CLOSED", ("POLICY_AUTHOR_REVIEWER_NOT_DISTINCT",)
    if not policy.source_sha256:
        return "FAIL_CLOSED", ("HUMAN_POLICY_SOURCE_PROVENANCE_MISSING",)
    return "HUMAN_REVIEWED", ()


def _fact_assessment(
    fact: Mapping[str, Any],
    role: str,
    *,
    expected_subject: Mapping[str, str],
    declared_assumptions: Sequence[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    eligible = True
    if fact.get("schema") != FACT_SCHEMA:
        reasons.append("FACT_SCHEMA_UNSUPPORTED")
        eligible = False
    if role == "producer":
        requirements = {
            "fact_kind": "producer_guarantee",
            "quantifier": "MUST",
            "approximation": "EXACT",
            "derivation_class": "DERIVED",
            "support": "SUPPORTED",
        }
    else:
        requirements = {
            "fact_kind": "consumer_used",
            "quantifier": "MAY",
            "derivation_class": "DERIVED",
            "support": "SUPPORTED",
        }
    for field_name, expected in requirements.items():
        if fact.get(field_name) != expected:
            reasons.append(f"{role.upper()}_{field_name.upper()}_NOT_{expected}")
            eligible = False
    if role == "reliance" and fact.get("approximation") not in {
        "EXACT", "OVER_APPROXIMATION"
    }:
        reasons.append("RELIANCE_APPROXIMATION_NOT_CONSERVATIVE_MAY")
        eligible = False
    try:
        subject_ref = _fact_ref(fact.get("subject_identity_ref"), f"{role} subject")
    except BoundaryInputError:
        subject_ref = None
        reasons.append(f"{role.upper()}_IDENTITY_REF_NOT_OPAQUE")
        eligible = False
    if subject_ref is not None and subject_ref != dict(expected_subject):
        reasons.append(
            "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH"
            if role == "producer"
            else "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH"
        )
        eligible = False
    object_ref = fact.get("object_identity_ref")
    if object_ref is None:
        reasons.append(f"{role.upper()}_VALUE_IDENTITY_MISSING")
        eligible = False
    else:
        try:
            _fact_ref(object_ref, f"{role} object")
        except BoundaryInputError:
            reasons.append(f"{role.upper()}_VALUE_IDENTITY_REF_NOT_OPAQUE")
            eligible = False
    if not fact.get("provenance_refs"):
        reasons.append(f"{role.upper()}_PROVENANCE_MISSING")
        eligible = False
    unresolved_assumptions = sorted(
        set(fact.get("assumption_refs", [])) - set(declared_assumptions)
    )
    if unresolved_assumptions:
        reasons.append(f"{role.upper()}_ASSUMPTION_UNDISCHARGED")
        eligible = False
    if fact.get("mapping_refs"):
        reasons.append(f"{role.upper()}_MAPPING_CERTIFICATE_NOT_BOUND")
        eligible = False
    try:
        condition = _condition(fact["condition"])
    except BoundaryInputError:
        condition = None
        reasons.append(f"{role.upper()}_CONDITION_UNSUPPORTED")
        eligible = False
    if condition is not None and condition["kind"] == "UNKNOWN":
        reasons.append(condition["reason_code"])
        eligible = False
    return {
        "fact_id": fact["fact_id"],
        "role": role,
        "fact_kind": fact.get("fact_kind"),
        "quantifier": fact.get("quantifier"),
        "approximation": fact.get("approximation"),
        "derivation_class": fact.get("derivation_class"),
        "support_status": fact.get("support"),
        "source_reason": fact.get("reason"),
        "subject_identity_ref": subject_ref,
        "object_identity_ref": object_ref,
        "unresolved_assumption_refs": unresolved_assumptions,
        "eligible_for_role": eligible,
        "reason_codes": reasons,
    }


def _eval_term(term: Mapping[str, Any], assignment: Mapping[str, Any]) -> Any:
    return assignment[term["var"]] if "var" in term else term["const"]


def _eval_predicate(predicate: Mapping[str, Any], assignment: Mapping[str, Any]) -> bool:
    op = predicate["op"]
    if op == "const":
        return predicate["value"]
    if op in {"and", "or"}:
        values = [_eval_predicate(item, assignment) for item in predicate["args"]]
        return all(values) if op == "and" else any(values)
    if op == "not":
        return not _eval_predicate(predicate["arg"], assignment)
    left = _eval_term(predicate["left"], assignment)
    right = _eval_term(predicate["right"], assignment)
    operations = {
        "eq": lambda: left == right,
        "ne": lambda: left != right,
        "lt": lambda: left < right,
        "le": lambda: left <= right,
        "gt": lambda: left > right,
        "ge": lambda: left >= right,
    }
    try:
        return bool(operations[op]())
    except TypeError as exc:
        raise BoundaryInputError(f"incomparable predicate terms for {op}") from exc


def _eval_condition(condition: Mapping[str, Any], assignment: Mapping[str, Any]) -> bool:
    kind = condition["kind"]
    if kind == "ALWAYS":
        return True
    if kind in {"NEVER", "UNKNOWN"}:
        return False
    return _eval_predicate(condition["predicate"], assignment)


def _assignments(query: BoundedQuery) -> Iterable[dict[str, Any]]:
    names = sorted(query.variable_domains)
    values = [query.variable_domains[name] for name in names]
    for combination in product(*values):
        assignment = dict(query.fixed_authenticated_context)
        assignment.update(dict(zip(names, combination)))
        yield assignment


def _permission_matches(
    permission: PermissionRecord,
    obligation: AuthorizationObligation,
    effect: ProtectedEffect,
    assignment: Mapping[str, Any],
) -> bool:
    if dict(permission.authorizing_identity_ref) != dict(
        obligation.authorization_identity_ref
    ):
        return False
    if dict(permission.protected_effect_identity_ref) != dict(
        effect.protected_effect_identity_ref
    ):
        return False
    if not _eval_condition(permission.condition, assignment):
        return False
    for name in SUPPORTED_FIELDS:
        actual = _eval_term(effect.fields[name], assignment)
        required = _eval_term(obligation.fields[name], assignment)
        allowed = _eval_term(permission.fields[name], assignment)
        if actual != required or actual != allowed:
            return False
    return True


def _evaluate_obligation(
    boundary: BoundaryInput,
    obligation: AuthorizationObligation,
    facts: Mapping[str, Mapping[str, Any]],
    policy_gate: str,
    policy_reasons: tuple[str, ...],
    assignment_space: int,
) -> ObligationResult:
    effect = next(
        item for item in boundary.effects if item.effect_id == obligation.protected_effect_id
    )
    producer_facts = [facts[fact_id] for fact_id in obligation.producer_fact_ids]
    reliance_facts = [facts[fact_id] for fact_id in obligation.reliance_fact_ids]
    assessment_list = (
        [
            _fact_assessment(
                item,
                "producer",
                expected_subject=obligation.authorization_identity_ref,
                declared_assumptions=boundary.assumptions,
            )
            for item in producer_facts
        ]
        + [
            _fact_assessment(
                item,
                "reliance",
                expected_subject=obligation.protected_effect_identity_ref,
                declared_assumptions=boundary.assumptions,
            )
            for item in reliance_facts
        ]
    )
    producer_objects = [item.get("object_identity_ref") for item in producer_facts]
    reliance_objects = [item.get("object_identity_ref") for item in reliance_facts]
    value_refs = [item for item in producer_objects + reliance_objects if item is not None]
    if value_refs and any(item != value_refs[0] for item in value_refs[1:]):
        for assessment in assessment_list:
            assessment["eligible_for_role"] = False
            assessment["reason_codes"] = sorted(set(
                [*assessment["reason_codes"], "PRODUCER_RELIANCE_VALUE_IDENTITY_MISMATCH"]
            ))
    if any(fact_id not in effect.source_fact_ids for fact_id in obligation.reliance_fact_ids):
        for assessment in assessment_list:
            if assessment["role"] == "reliance":
                assessment["eligible_for_role"] = False
                assessment["reason_codes"] = sorted(set(
                    [*assessment["reason_codes"], "RELIANCE_FACT_NOT_BOUND_TO_EFFECT"]
                ))
    assessments = tuple(assessment_list)
    reason_codes: list[str] = list(policy_reasons)

    if not obligation.requires_proof_authorization:
        reason_codes.append("INDEPENDENT_AUTHORIZATION_JUSTIFICATION_UNSUPPORTED")
    if effect.alternative_authorization_refs:
        reason_codes.append("ALTERNATIVE_AUTHORIZATION_UNREVIEWED")
    if boundary.policy is None:
        # There is no permission relation to query.  Do not turn absence of a
        # policy into either a counterexample or an apparent establishment.
        reason_codes.append("POLICY_SEMANTICS_UNAVAILABLE")
    for assessment in assessments:
        if not assessment["eligible_for_role"]:
            reason_codes.extend(assessment["reason_codes"])
    if assignment_space > boundary.query.max_assignments:
        reason_codes.append("QUERY_ASSIGNMENT_LIMIT_EXCEEDED")

    if reason_codes and any(
        code not in policy_reasons
        for code in reason_codes
    ):
        mechanical_state = "UNKNOWN"
        relying_count = 0
        counterexample = None
        assignment_count = 0
    else:
        relying_count = 0
        assignment_count = 0
        counterexample = None
        for assignment in _assignments(boundary.query):
            assignment_count += 1
            producer_holds = all(
                _eval_condition(_condition(item["condition"]), assignment)
                for item in producer_facts
            )
            reliance_holds = all(
                _eval_condition(_condition(item["condition"]), assignment)
                for item in reliance_facts
            )
            path_holds = _eval_condition(effect.path_condition, assignment)
            activation_holds = _eval_condition(obligation.activation, assignment)
            if not (producer_holds and reliance_holds and path_holds and activation_holds):
                continue
            relying_count += 1
            discharged = _eval_condition(obligation.discharge, assignment)
            permitted = bool(boundary.policy) and any(
                _permission_matches(permission, obligation, effect, assignment)
                for permission in boundary.policy.permissions
            )
            if not discharged or not permitted:
                counterexample = {
                    "assignment": dict(sorted(assignment.items())),
                    "attacker_choices": {
                        name: assignment[name]
                        for name in boundary.query.attacker_controlled
                    },
                    "discharge_condition_holds": discharged,
                    "matching_permission_exists": permitted,
                }
                break
        if relying_count == 0:
            mechanical_state = "UNKNOWN"
            reason_codes.append("NONVACUITY_NOT_ESTABLISHED")
        elif counterexample is not None:
            mechanical_state = "MISMATCH_CANDIDATE"
            reason_codes.append("BOUNDED_POLICY_COUNTEREXAMPLE")
        else:
            mechanical_state = "ESTABLISHED"
            reason_codes.append("BOUNDED_IMPLICATION_EXHAUSTIVE_WITHIN_DECLARED_DOMAIN")

    effective_state = mechanical_state if policy_gate == "HUMAN_REVIEWED" else "UNKNOWN"
    return ObligationResult(
        obligation_id=obligation.obligation_id,
        state=effective_state,
        mechanical_state=mechanical_state,
        reason_codes=tuple(sorted(set(reason_codes))),
        fact_assessments=assessments,
        assignment_count=assignment_count,
        relying_assignment_count=relying_count,
        counterexample=counterexample,
    )


def evaluate_boundary(boundary: BoundaryInput, *, arm: str) -> BoundaryResult:
    """Evaluate one arm through the common bounded P/O/E interpretation."""
    if arm not in ARMS:
        raise BoundaryInputError(f"unsupported comparison arm: {arm!r}")
    validation = validate_boundary_input(boundary)
    gate, policy_reasons = _policy_gate(boundary.policy)
    facts = {item["fact_id"]: item for item in boundary.identity_bundle["facts"]}
    obligation_results = tuple(
        _evaluate_obligation(
            boundary,
            obligation,
            facts,
            gate,
            policy_reasons,
            validation["assignment_space"],
        )
        for obligation in sorted(boundary.obligations, key=lambda item: item.obligation_id)
    )
    if not obligation_results:
        state = "UNKNOWN"
        reasons = ("EMPTY_OBLIGATION_SET", *policy_reasons)
    elif gate != "HUMAN_REVIEWED":
        state = "UNKNOWN"
        reasons = policy_reasons
    elif any(item.state == "MISMATCH_CANDIDATE" for item in obligation_results):
        state = "MISMATCH_CANDIDATE"
        reasons = ("AT_LEAST_ONE_OBLIGATION_HAS_BOUNDED_COUNTEREXAMPLE",)
    elif all(item.state == "ESTABLISHED" for item in obligation_results):
        state = "ESTABLISHED"
        reasons = ("ALL_NONVACUOUS_OBLIGATIONS_ESTABLISHED_WITHIN_BOUNDS",)
    else:
        state = "UNKNOWN"
        reasons = ("AT_LEAST_ONE_OBLIGATION_UNKNOWN",)
    return BoundaryResult(
        arm=arm,
        case_id=boundary.case_id,
        state=state,
        policy_gate=gate,
        reason_codes=tuple(sorted(set(reasons))),
        input_sha256=validation["input_sha256"],
        policy_sha256=validation["policy_sha256"],
        identity_bundle_sha256=validation["identity_bundle_sha256"],
        fact_set_sha256=validation["fact_set_sha256"],
        obligation_results=obligation_results,
    )


def evaluate_equal_input_arms(boundary: BoundaryInput) -> dict[str, Any]:
    """Run both named arms on the identical canonical input bytes.

    No arm-specific facts, policy fields, defaults, or transformations are
    admitted.  The prototype therefore tests interface parity, not comparative
    capability or a scored Gate A row.
    """
    canonical_input = canonical_json_bytes(boundary.canonical())
    input_sha256 = sha256_json(boundary.canonical())
    results = {
        arm: evaluate_boundary(boundary, arm=arm).to_dict()
        for arm in ARMS
    }
    semantic_views = []
    for arm in ARMS:
        view = dict(results[arm])
        view.pop("arm")
        semantic_views.append(view)
    return {
        "schema": EQUAL_ARMS_SCHEMA,
        "case_id": boundary.case_id,
        "common_input_byte_length": len(canonical_input),
        "common_input_sha256": input_sha256,
        "arm_input_sha256": {arm: results[arm]["input_sha256"] for arm in ARMS},
        "arm_policy_sha256": {arm: results[arm]["policy_sha256"] for arm in ARMS},
        "arm_fact_set_sha256": {arm: results[arm]["fact_set_sha256"] for arm in ARMS},
        "semantic_parity": semantic_views[0] == semantic_views[1],
        "score_eligible": False,
        "research_verdict": "UNKNOWN",
        "results": results,
    }
