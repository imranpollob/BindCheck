"""Compiler-backed object/context identity and provenance records.

The semantic identity hash is deliberately narrower than provenance. It is a
canonical digest of an explicit logical object and execution context. Compiler
artifact hashes, ABI indices, AST node IDs, surface identifiers, source paths,
and source spans are retained in the separate provenance record. This lets a
mapping certificate establish that a source-preserving transformation moved
the same logical identity without pretending that the two compiler artifacts
are byte-identical.

These types do not decide authorization, emit a security verdict, or establish
semantic equivalence. All D2-08 evidence is mechanical development evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


IDENTITY_SCHEMA = "bindcheck.compiler-object-context-identity/v1"
IDENTITY_REFERENCE_SCHEMA = "bindcheck.compiler-object-context-identity-ref/v1"
PROVENANCE_SCHEMA = "bindcheck.compiler-identity-provenance/v1"
FACT_SCHEMA = "bindcheck.compiler-identity-fact/v1"
MAPPING_SCHEMA = "bindcheck.compiler-identity-mapping/v1"
BUNDLE_SCHEMA = "bindcheck.compiler-identity-bundle/v1"
FIXTURE_LABEL = "UNREVIEWED_DEVELOPMENT_FIXTURE"

DERIVATION_CLASSES = frozenset({"DERIVED", "ANNOTATED", "ASSUMED", "UNKNOWN"})
SUPPORT_STATES = frozenset({"SUPPORTED", "UNKNOWN"})
QUANTIFIERS = frozenset({"MUST", "MAY"})
APPROXIMATIONS = frozenset({"EXACT", "OVER_APPROXIMATION", "UNDER_APPROXIMATION", "UNKNOWN"})
HEX_64 = re.compile(r"[0-9a-f]{64}")
SEMANTIC_HASH = re.compile(r"OCI-[0-9A-F]{24}")
EXTERNAL_PARENT_PREFIX = "external:"
REFERENCE_RESOLUTION_BOUNDARY = MappingProxyType({
    "provenance_refs": "BUNDLE_IDENTITY_PROVENANCE_HASH_OR_EXTERNAL_HASH_BOUND_REGISTRY",
    "parent_fact_ids": "INTERNAL_FACT_ID_OR_external_NAMESPACE",
    "assumption_refs": "EXTERNAL_HASH_BOUND_ASSUMPTION_REGISTRY",
    "annotation_refs": "EXTERNAL_HASH_BOUND_ANNOTATION_REGISTRY",
    "mapping_refs": "EXTERNAL_HASH_BOUND_MAPPING_REGISTRY",
})


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hash-bearing structures."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _require_text(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string")
    return value


def _require_sha256(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not HEX_64.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _pairs(value: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    normalized = tuple(sorted((str(key), str(item)) for key, item in value))
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("attribute keys must be unique")
    return normalized


def _string_tuple(value: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_require_text("reference", item) for item in value}))


def _json_value(value: Any) -> Any:
    """Validate and normalize a structured JSON value."""
    encoded = canonical_json_bytes(value)
    return json.loads(encoded.decode("utf-8"))


def _identity_reference(value: Mapping[str, str]) -> dict[str, str]:
    """Copy and validate the exact opaque object/context identity reference."""
    if not isinstance(value, Mapping) or set(value) != {
        "schema", "semantic_hash", "canonical_bytes_sha256",
    }:
        raise ValueError("identity reference must have exactly the three opaque fields")
    schema = value.get("schema")
    semantic_hash = value.get("semantic_hash")
    canonical_digest = value.get("canonical_bytes_sha256")
    if schema != IDENTITY_REFERENCE_SCHEMA:
        raise ValueError(f"unsupported identity reference schema: {schema!r}")
    if not isinstance(semantic_hash, str) or not SEMANTIC_HASH.fullmatch(semantic_hash):
        raise ValueError("invalid semantic identity hash")
    if not isinstance(canonical_digest, str):
        raise ValueError("canonical identity digest must be a string")
    _require_sha256("canonical_bytes_sha256", canonical_digest)
    if semantic_hash != f"OCI-{canonical_digest[:24].upper()}":
        raise ValueError("semantic identity hash does not match canonical digest")
    return {
        "schema": schema,
        "semantic_hash": semantic_hash,
        "canonical_bytes_sha256": canonical_digest,
    }


def _identity_reference_key(value: Mapping[str, str]) -> tuple[str, str, str]:
    normalized = _identity_reference(value)
    return (
        normalized["schema"],
        normalized["semantic_hash"],
        normalized["canonical_bytes_sha256"],
    )


@dataclass(frozen=True)
class ObjectIdentity:
    """A logical object independent of identifier spelling and source layout."""

    kind: str
    logical_slot: str
    representation: str
    state_scope: str
    encoding: str
    value_type: str
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "kind", "logical_slot", "representation", "state_scope",
            "encoding", "value_type",
        ):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "attributes", _pairs(self.attributes))

    def canonical(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "logical_slot": self.logical_slot,
            "representation": self.representation,
            "state_scope": self.state_scope,
            "encoding": self.encoding,
            "value_type": self.value_type,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class ContextIdentity:
    """The domain/context in which an object is interpreted or consumed."""

    kind: str
    domain: str
    deployment: str
    state_version: str
    actor: str
    epoch: str
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "kind", "domain", "deployment", "state_version", "actor", "epoch",
        ):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "attributes", _pairs(self.attributes))

    def canonical(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "domain": self.domain,
            "deployment": self.deployment,
            "state_version": self.state_version,
            "actor": self.actor,
            "epoch": self.epoch,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class CompilerProvenance:
    """Compiler/artifact evidence kept outside the semantic identity hash."""

    artifact_sha256: str
    compiler_id: str
    compiler_version: str
    artifact_schema: str
    evidence_kind: str
    node_id: str | None = None
    abi_index: int | None = None
    logical_mapping_id: str | None = None
    source_sha256: str | None = None
    support: str = "SUPPORTED"
    reason: str | None = None
    display_path: str | None = None
    display_span: str | None = None

    def __post_init__(self) -> None:
        _require_sha256("artifact_sha256", self.artifact_sha256)
        for name in (
            "compiler_id", "compiler_version", "artifact_schema", "evidence_kind",
        ):
            _require_text(name, getattr(self, name))
        if self.node_id is None and self.abi_index is None:
            raise ValueError("compiler provenance requires a node_id or abi_index")
        if self.abi_index is not None and self.abi_index < 0:
            raise ValueError("abi_index must be nonnegative")
        if self.source_sha256 is not None:
            _require_sha256("source_sha256", self.source_sha256)
        if self.support not in SUPPORT_STATES:
            raise ValueError(f"unsupported provenance support state: {self.support}")
        if self.support == "UNKNOWN" and not self.reason:
            raise ValueError("UNKNOWN provenance requires a reason")

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": PROVENANCE_SCHEMA,
            "artifact_sha256": self.artifact_sha256,
            "compiler_id": self.compiler_id,
            "compiler_version": self.compiler_version,
            "artifact_schema": self.artifact_schema,
            "evidence_kind": self.evidence_kind,
            "node_id": self.node_id,
            "abi_index": self.abi_index,
            "logical_mapping_id": self.logical_mapping_id,
            "source_sha256": self.source_sha256,
            "support": self.support,
            "reason": self.reason,
            "display": {
                "path": self.display_path,
                "span": self.display_span,
            },
        }


@dataclass(frozen=True)
class IdentityRecord:
    """A semantic object/context identity with independently hashed provenance."""

    object_identity: ObjectIdentity
    context_identity: ContextIdentity
    provenance: tuple[CompilerProvenance, ...]
    derivation_class: str
    support: str = "SUPPORTED"
    reason: str | None = None
    assumption_refs: tuple[str, ...] = ()
    annotation_refs: tuple[str, ...] = ()
    mapping_refs: tuple[str, ...] = ()
    display_hints: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("identity requires compiler or mapping provenance")
        if self.derivation_class not in DERIVATION_CLASSES:
            raise ValueError(f"unsupported derivation class: {self.derivation_class}")
        if self.support not in SUPPORT_STATES:
            raise ValueError(f"unsupported identity support state: {self.support}")
        if self.support == "UNKNOWN" and not self.reason:
            raise ValueError("UNKNOWN identity requires a reason")
        object.__setattr__(self, "assumption_refs", _string_tuple(self.assumption_refs))
        object.__setattr__(self, "annotation_refs", _string_tuple(self.annotation_refs))
        object.__setattr__(self, "mapping_refs", _string_tuple(self.mapping_refs))
        object.__setattr__(self, "display_hints", _pairs(self.display_hints))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": IDENTITY_SCHEMA,
            "object": self.object_identity.canonical(),
            "context": self.context_identity.canonical(),
        }

    @property
    def canonical_bytes_sha256(self) -> str:
        return sha256_json(self.canonical_payload())

    @property
    def semantic_hash(self) -> str:
        return f"OCI-{self.canonical_bytes_sha256[:24].upper()}"

    def provenance_payload(self) -> dict[str, Any]:
        return {
            "schema": PROVENANCE_SCHEMA,
            "identity": self.semantic_hash,
            "derivation_class": self.derivation_class,
            "support": self.support,
            "reason": self.reason,
            "compiler_records": [item.canonical() for item in self.provenance],
            "assumption_refs": list(self.assumption_refs),
            "annotation_refs": list(self.annotation_refs),
            "mapping_refs": list(self.mapping_refs),
            "display_hints": dict(self.display_hints),
        }

    @property
    def provenance_hash(self) -> str:
        return sha256_json(self.provenance_payload())

    def reference(self) -> dict[str, str]:
        return identity_reference(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": IDENTITY_SCHEMA,
            "semantic_hash": self.semantic_hash,
            "canonical_bytes_sha256": self.canonical_bytes_sha256,
            "canonical_payload": self.canonical_payload(),
            "provenance_hash": self.provenance_hash,
            "provenance": self.provenance_payload(),
        }


def identity_reference(identity: IdentityRecord) -> dict[str, str]:
    """Return the opaque value consumed by the common P/O/E interface."""
    return {
        "schema": IDENTITY_REFERENCE_SCHEMA,
        "semantic_hash": identity.semantic_hash,
        "canonical_bytes_sha256": identity.canonical_bytes_sha256,
    }


@dataclass(frozen=True)
class IdentityFact:
    """A typed extraction fact referencing semantic identities, not names."""

    fact_kind: str
    subject_identity_ref: Mapping[str, str]
    object_identity_ref: Mapping[str, str] | None
    quantifier: str
    condition: Mapping[str, Any]
    approximation: str
    derivation_class: str
    support: str
    reason: str | None = None
    provenance_refs: tuple[str, ...] = ()
    parent_fact_ids: tuple[str, ...] = ()
    assumption_refs: tuple[str, ...] = ()
    annotation_refs: tuple[str, ...] = ()
    mapping_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text("fact_kind", self.fact_kind)
        object.__setattr__(
            self,
            "subject_identity_ref",
            MappingProxyType(_identity_reference(self.subject_identity_ref)),
        )
        if self.object_identity_ref is not None:
            object.__setattr__(
                self,
                "object_identity_ref",
                MappingProxyType(_identity_reference(self.object_identity_ref)),
            )
        if self.quantifier not in QUANTIFIERS:
            raise ValueError(f"unsupported quantifier: {self.quantifier}")
        if self.approximation not in APPROXIMATIONS:
            raise ValueError(f"unsupported approximation: {self.approximation}")
        if self.derivation_class not in DERIVATION_CLASSES:
            raise ValueError(f"unsupported derivation class: {self.derivation_class}")
        if self.support not in SUPPORT_STATES:
            raise ValueError(f"unsupported fact support state: {self.support}")
        if self.support == "UNKNOWN" and not self.reason:
            raise ValueError("UNKNOWN fact requires a reason")
        condition = _json_value(dict(self.condition))
        if not isinstance(condition.get("kind"), str) or not condition["kind"].strip():
            raise ValueError("identity fact condition requires a nonempty kind")
        object.__setattr__(self, "condition", condition)
        for name in (
            "provenance_refs", "parent_fact_ids", "assumption_refs",
            "annotation_refs", "mapping_refs",
        ):
            object.__setattr__(self, name, _string_tuple(getattr(self, name)))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": FACT_SCHEMA,
            "fact_kind": self.fact_kind,
            "subject_identity_ref": dict(self.subject_identity_ref),
            "object_identity_ref": (
                None if self.object_identity_ref is None
                else dict(self.object_identity_ref)
            ),
            "quantifier": self.quantifier,
            "condition": self.condition,
            "approximation": self.approximation,
            "derivation_class": self.derivation_class,
            "support": self.support,
            "reason": self.reason,
            "provenance_refs": list(self.provenance_refs),
            "parent_fact_ids": list(self.parent_fact_ids),
            "assumption_refs": list(self.assumption_refs),
            "annotation_refs": list(self.annotation_refs),
            "mapping_refs": list(self.mapping_refs),
        }

    @property
    def fact_id(self) -> str:
        return f"IF-{sha256_json(self.canonical_payload())[:24].upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {"fact_id": self.fact_id, **self.canonical_payload()}


@dataclass(frozen=True)
class MappingEntry:
    logical_slot: str
    from_identity_ref: Mapping[str, str]
    to_identity_ref: Mapping[str, str]
    from_abi_index: int
    to_abi_index: int

    def __post_init__(self) -> None:
        _require_text("logical_slot", self.logical_slot)
        object.__setattr__(
            self,
            "from_identity_ref",
            MappingProxyType(_identity_reference(self.from_identity_ref)),
        )
        object.__setattr__(
            self,
            "to_identity_ref",
            MappingProxyType(_identity_reference(self.to_identity_ref)),
        )
        if self.from_abi_index < 0 or self.to_abi_index < 0:
            raise ValueError("mapping ABI indices must be nonnegative")

    def canonical(self) -> dict[str, Any]:
        return {
            "logical_slot": self.logical_slot,
            "from_identity_ref": dict(self.from_identity_ref),
            "to_identity_ref": dict(self.to_identity_ref),
            "from_abi_index": self.from_abi_index,
            "to_abi_index": self.to_abi_index,
        }


@dataclass(frozen=True)
class MappingCertificate:
    transformation_id: str
    source_bundle_id: str
    target_bundle_id: str
    entries: tuple[MappingEntry, ...]
    source_identity_count: int
    target_identity_count: int
    evidence_sha256: tuple[str, ...]
    mapping_source_refs: tuple[str, ...]
    support: str = "SUPPORTED"
    reason: str | None = None
    fixture_label: str = FIXTURE_LABEL

    def __post_init__(self) -> None:
        for name in ("transformation_id", "source_bundle_id", "target_bundle_id"):
            _require_text(name, getattr(self, name))
        if self.fixture_label != FIXTURE_LABEL:
            raise ValueError("D2-08 mapping must remain an unreviewed development fixture")
        if self.support not in SUPPORT_STATES:
            raise ValueError(f"unsupported mapping support state: {self.support}")
        if self.support == "UNKNOWN" and not self.reason:
            raise ValueError("UNKNOWN mapping requires a reason")
        if self.source_identity_count < 0 or self.target_identity_count < 0:
            raise ValueError("identity counts must be nonnegative")
        if not self.evidence_sha256:
            raise ValueError("mapping certificate requires hash-bound evidence")
        for digest in self.evidence_sha256:
            _require_sha256("evidence_sha256", digest)
        if not self.mapping_source_refs:
            raise ValueError("mapping certificate requires an external mapping source ref")
        object.__setattr__(
            self, "mapping_source_refs", _string_tuple(self.mapping_source_refs)
        )
        slots = [entry.logical_slot for entry in self.entries]
        if len(slots) != len(set(slots)):
            raise ValueError("mapping logical slots must be unique")

    @property
    def properties(self) -> dict[str, bool]:
        from_refs = [
            _identity_reference_key(entry.from_identity_ref) for entry in self.entries
        ]
        to_refs = [
            _identity_reference_key(entry.to_identity_ref) for entry in self.entries
        ]
        from_indices = [entry.from_abi_index for entry in self.entries]
        to_indices = [entry.to_abi_index for entry in self.entries]
        unique_sources = (
            len(from_refs) == len(set(from_refs))
            and len(from_indices) == len(set(from_indices))
        )
        unique_targets = (
            len(to_refs) == len(set(to_refs))
            and len(to_indices) == len(set(to_indices))
        )
        return {
            "total": len(self.entries) == self.source_identity_count
            and unique_sources,
            "injective": unique_targets,
            "surjective": len(self.entries) == self.target_identity_count
            and unique_targets,
            "order_preserving": all(
                left.to_abi_index < right.to_abi_index
                for left, right in zip(
                    sorted(self.entries, key=lambda item: item.from_abi_index),
                    sorted(self.entries, key=lambda item: item.from_abi_index)[1:],
                )
            ),
            "semantic_identity_preserving": all(
                _identity_reference_key(entry.from_identity_ref)
                == _identity_reference_key(entry.to_identity_ref)
                for entry in self.entries
            ),
        }

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": MAPPING_SCHEMA,
            "fixture_label": self.fixture_label,
            "transformation_id": self.transformation_id,
            "source_bundle_id": self.source_bundle_id,
            "target_bundle_id": self.target_bundle_id,
            "entries": [
                item.canonical()
                for item in sorted(self.entries, key=lambda item: item.logical_slot)
            ],
            "source_identity_count": self.source_identity_count,
            "target_identity_count": self.target_identity_count,
            "properties": self.properties,
            "evidence_sha256": sorted(self.evidence_sha256),
            "mapping_source_refs": list(self.mapping_source_refs),
            "support": self.support,
            "reason": self.reason,
        }

    @property
    def mapping_id(self) -> str:
        return f"MAP-{sha256_json(self.canonical_payload())[:24].upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {"mapping_id": self.mapping_id, **self.canonical_payload()}


@dataclass(frozen=True)
class IdentityBundle:
    """A reproducible set of identities and facts for one compiler artifact."""

    bundle_name: str
    identities: tuple[IdentityRecord, ...]
    facts: tuple[IdentityFact, ...]
    input_sha256: tuple[str, ...]
    fixture_label: str = FIXTURE_LABEL
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_text("bundle_name", self.bundle_name)
        if self.fixture_label != FIXTURE_LABEL:
            raise ValueError("D2-08 bundle must remain an unreviewed development fixture")
        for digest in self.input_sha256:
            _require_sha256("input_sha256", digest)
        semantic_hashes = [item.semantic_hash for item in self.identities]
        if len(semantic_hashes) != len(set(semantic_hashes)):
            raise ValueError("bundle semantic identities must be unique")
        known = {
            _identity_reference_key(item.reference()) for item in self.identities
        }
        known_provenance = {item.provenance_hash for item in self.identities}
        fact_ids = [item.fact_id for item in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("bundle fact IDs must be unique")
        known_facts = set(fact_ids)
        for fact in self.facts:
            if _identity_reference_key(fact.subject_identity_ref) not in known:
                raise ValueError(f"fact has unknown subject identity: {fact.fact_id}")
            if (
                fact.object_identity_ref is not None
                and _identity_reference_key(fact.object_identity_ref) not in known
            ):
                raise ValueError(f"fact has unknown object identity: {fact.fact_id}")
            for provenance_ref in fact.provenance_refs:
                if (
                    provenance_ref not in known_provenance
                    and not provenance_ref.startswith(EXTERNAL_PARENT_PREFIX)
                ):
                    raise ValueError(
                        f"fact has unresolved provenance reference: {fact.fact_id}"
                    )
            for parent in fact.parent_fact_ids:
                if parent not in known_facts and not parent.startswith(EXTERNAL_PARENT_PREFIX):
                    raise ValueError(f"fact has unresolved parent fact: {fact.fact_id}")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_SCHEMA,
            "fixture_label": self.fixture_label,
            "bundle_name": self.bundle_name,
            "identity_refs": [
                list(item)
                for item in sorted(
                    (
                        item.semantic_hash,
                        item.canonical_bytes_sha256,
                        item.provenance_hash,
                    )
                    for item in self.identities
                )
            ],
            "fact_ids": sorted(item.fact_id for item in self.facts),
            "input_sha256": sorted(self.input_sha256),
            "limitations": sorted(self.limitations),
            "reference_resolution_boundary": dict(REFERENCE_RESOLUTION_BOUNDARY),
        }

    @property
    def bundle_id(self) -> str:
        return f"BUNDLE-{sha256_json(self.canonical_payload())[:24].upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            **self.canonical_payload(),
            "identities": [
                item.to_dict()
                for item in sorted(self.identities, key=lambda item: item.semantic_hash)
            ],
            "facts": [
                item.to_dict() for item in sorted(self.facts, key=lambda item: item.fact_id)
            ],
        }


def _identity_record_from_dict(item: Mapping[str, Any]) -> IdentityRecord:
    canonical = item.get("canonical_payload")
    provenance = item.get("provenance")
    if not isinstance(canonical, Mapping) or not isinstance(provenance, Mapping):
        raise ValueError("identity canonical payload/provenance must be objects")
    if canonical.get("schema") != IDENTITY_SCHEMA:
        raise ValueError("identity canonical schema mismatch")
    if provenance.get("schema") != PROVENANCE_SCHEMA:
        raise ValueError("identity provenance schema mismatch")
    object_value = canonical.get("object")
    context_value = canonical.get("context")
    if not isinstance(object_value, Mapping) or not isinstance(context_value, Mapping):
        raise ValueError("identity object/context must be objects")
    object_attributes = object_value.get("attributes")
    context_attributes = context_value.get("attributes")
    if not isinstance(object_attributes, Mapping) or not isinstance(
        context_attributes, Mapping
    ):
        raise ValueError("identity attributes must be objects")
    object_identity = ObjectIdentity(
        kind=object_value["kind"],
        logical_slot=object_value["logical_slot"],
        representation=object_value["representation"],
        state_scope=object_value["state_scope"],
        encoding=object_value["encoding"],
        value_type=object_value["value_type"],
        attributes=tuple(object_attributes.items()),
    )
    context_identity = ContextIdentity(
        kind=context_value["kind"],
        domain=context_value["domain"],
        deployment=context_value["deployment"],
        state_version=context_value["state_version"],
        actor=context_value["actor"],
        epoch=context_value["epoch"],
        attributes=tuple(context_attributes.items()),
    )
    compiler_records = provenance.get("compiler_records")
    if not isinstance(compiler_records, list) or not compiler_records:
        raise ValueError("identity provenance requires compiler records")
    parsed_provenance: list[CompilerProvenance] = []
    for record in compiler_records:
        if not isinstance(record, Mapping) or record.get("schema") != PROVENANCE_SCHEMA:
            raise ValueError("compiler provenance record schema mismatch")
        display = record.get("display")
        if not isinstance(display, Mapping):
            raise ValueError("compiler provenance display field must be an object")
        parsed_provenance.append(CompilerProvenance(
            artifact_sha256=record["artifact_sha256"],
            compiler_id=record["compiler_id"],
            compiler_version=record["compiler_version"],
            artifact_schema=record["artifact_schema"],
            evidence_kind=record["evidence_kind"],
            node_id=record.get("node_id"),
            abi_index=record.get("abi_index"),
            logical_mapping_id=record.get("logical_mapping_id"),
            source_sha256=record.get("source_sha256"),
            support=record.get("support"),
            reason=record.get("reason"),
            display_path=display.get("path"),
            display_span=display.get("span"),
        ))
    display_hints = provenance.get("display_hints")
    if not isinstance(display_hints, Mapping):
        raise ValueError("identity display hints must be an object")
    rebuilt = IdentityRecord(
        object_identity=object_identity,
        context_identity=context_identity,
        provenance=tuple(parsed_provenance),
        derivation_class=provenance["derivation_class"],
        support=provenance["support"],
        reason=provenance.get("reason"),
        assumption_refs=tuple(provenance.get("assumption_refs", [])),
        annotation_refs=tuple(provenance.get("annotation_refs", [])),
        mapping_refs=tuple(provenance.get("mapping_refs", [])),
        display_hints=tuple(display_hints.items()),
    )
    if rebuilt.to_dict() != dict(item):
        raise ValueError("identity serialized value is noncanonical or hash-inconsistent")
    return rebuilt


def _identity_fact_from_dict(item: Mapping[str, Any]) -> IdentityFact:
    rebuilt = IdentityFact(
        fact_kind=item["fact_kind"],
        subject_identity_ref=item["subject_identity_ref"],
        object_identity_ref=item.get("object_identity_ref"),
        quantifier=item["quantifier"],
        condition=item["condition"],
        approximation=item["approximation"],
        derivation_class=item["derivation_class"],
        support=item["support"],
        reason=item.get("reason"),
        provenance_refs=tuple(item.get("provenance_refs", [])),
        parent_fact_ids=tuple(item.get("parent_fact_ids", [])),
        assumption_refs=tuple(item.get("assumption_refs", [])),
        annotation_refs=tuple(item.get("annotation_refs", [])),
        mapping_refs=tuple(item.get("mapping_refs", [])),
    )
    if rebuilt.to_dict() != dict(item):
        raise ValueError("fact serialized value is noncanonical or hash-inconsistent")
    return rebuilt


def _bundle_from_dict(bundle: Mapping[str, Any]) -> IdentityBundle:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError(f"unsupported bundle schema: {bundle.get('schema')!r}")
    if bundle.get("fixture_label") != FIXTURE_LABEL:
        raise ValueError("bundle fixture label changed")
    if bundle.get("reference_resolution_boundary") != REFERENCE_RESOLUTION_BOUNDARY:
        raise ValueError("bundle reference-resolution boundary changed")
    identities = bundle.get("identities")
    facts = bundle.get("facts")
    if not isinstance(identities, list) or not isinstance(facts, list):
        raise ValueError("bundle identities/facts must be lists")
    rebuilt = IdentityBundle(
        bundle_name=bundle["bundle_name"],
        identities=tuple(_identity_record_from_dict(item) for item in identities),
        facts=tuple(_identity_fact_from_dict(item) for item in facts),
        input_sha256=tuple(bundle.get("input_sha256", [])),
        fixture_label=bundle["fixture_label"],
        limitations=tuple(bundle.get("limitations", [])),
    )
    if rebuilt.to_dict() != dict(bundle):
        raise ValueError("bundle serialized value is noncanonical or hash-inconsistent")
    return rebuilt


def validate_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Replay all hashes, exact opaque refs, and internal fact references."""
    rebuilt = _bundle_from_dict(bundle)
    return {
        "status": "PASS",
        "bundle_id": rebuilt.bundle_id,
        "identity_count": len(rebuilt.identities),
        "fact_count": len(rebuilt.facts),
        "fixture_label": FIXTURE_LABEL,
    }


def validate_mapping_certificate(
    value: Mapping[str, Any],
    *,
    source_bundle: Mapping[str, Any] | None = None,
    target_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay a serialized mapping and optionally bind it to both bundles."""
    if value.get("schema") != MAPPING_SCHEMA:
        raise ValueError(f"unsupported mapping schema: {value.get('schema')!r}")
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise ValueError("mapping entries must be a list")
    rebuilt = MappingCertificate(
        transformation_id=value["transformation_id"],
        source_bundle_id=value["source_bundle_id"],
        target_bundle_id=value["target_bundle_id"],
        entries=tuple(MappingEntry(
            logical_slot=entry["logical_slot"],
            from_identity_ref=entry["from_identity_ref"],
            to_identity_ref=entry["to_identity_ref"],
            from_abi_index=entry["from_abi_index"],
            to_abi_index=entry["to_abi_index"],
        ) for entry in entries),
        source_identity_count=value["source_identity_count"],
        target_identity_count=value["target_identity_count"],
        evidence_sha256=tuple(value.get("evidence_sha256", [])),
        mapping_source_refs=tuple(value.get("mapping_source_refs", [])),
        support=value["support"],
        reason=value.get("reason"),
        fixture_label=value["fixture_label"],
    )
    if rebuilt.to_dict() != dict(value):
        raise ValueError("mapping serialized value is noncanonical or hash-inconsistent")

    for label, serialized, expected_id, ref_field, index_field in (
        (
            "source", source_bundle, rebuilt.source_bundle_id,
            "from_identity_ref", "from_abi_index",
        ),
        (
            "target", target_bundle, rebuilt.target_bundle_id,
            "to_identity_ref", "to_abi_index",
        ),
    ):
        if serialized is None:
            continue
        bundle = _bundle_from_dict(serialized)
        if bundle.bundle_id != expected_id:
            raise ValueError(f"mapping {label} bundle ID mismatch")
        bundle_refs = {
            _identity_reference_key(identity.reference()): identity
            for identity in bundle.identities
        }
        entry_refs = {
            _identity_reference_key(getattr(entry, ref_field)): entry
            for entry in rebuilt.entries
        }
        if set(entry_refs) != set(bundle_refs):
            raise ValueError(f"mapping does not exhaust {label} bundle identities")
        for ref, identity in bundle_refs.items():
            abi_indices = {
                record.abi_index for record in identity.provenance
                if record.abi_index is not None
            }
            if len(abi_indices) != 1:
                raise ValueError(f"{label} identity lacks one compiler ABI index")
            if getattr(entry_refs[ref], index_field) != next(iter(abi_indices)):
                raise ValueError(f"mapping {label} ABI index mismatch")
    return {
        "status": "PASS",
        "mapping_id": rebuilt.mapping_id,
        "entry_count": len(rebuilt.entries),
        "properties": rebuilt.properties,
        "fixture_label": FIXTURE_LABEL,
    }
