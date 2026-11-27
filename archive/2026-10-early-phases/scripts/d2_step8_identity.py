#!/usr/bin/env python3
"""Build and seal the D2-08 compiler-backed identity prototype evidence.

The run consumes only exposed Step 6a transformation artifacts. It creates
mechanical object/context identity, provenance, fact, mapping, and negative-
fixture records. It runs no analyzer or policy checker and emits no score or
security verdict.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import d2_foundation as foundation  # noqa: E402
from bindcheck_d1.role_binding import (  # noqa: E402
    LEGACY_SURFACE_ROLE_STATUS,
)
from bindcheck_d1.roles.compiler_identity_v1 import (  # noqa: E402
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


DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-08-compiler-identity-v1.json"
DEFAULT_LEDGER = ROOT / "results/raw/D2-06A/construction-03/transformation-ledger.json"
DEFAULT_OUT = ROOT / "results/raw/D2-08"
STEP6_MANIFEST = ROOT / "results/raw/D2-06A/construction-03/run-manifest.json"
STEP7_SEAL = ROOT / "results/raw/D2-07-recovery-01/content-seal-v1.json"
STEP7_REPORT = ROOT / "reports/D2-07.md"
ROLE_BINDING = ROOT / "src/bindcheck_d1/role_binding.py"
TRANSFORMATION_IDS = (
    "TR-IDENTIFIER-RENAME",
    "TR-HELPER-EXTRACTION",
    "TR-EQUIVALENT-EXPRESSION",
    "TR-MATCHED-PUBLIC-REORDER",
)
LOGICAL_SLOTS = (
    "d1p42.batch.element[0]",
    "d1p42.batch.element[1]",
    "d1p42.batch.element[2]",
    "d1p42.batch.element[3]",
    "d1p42.batch.extent",
)
LOGICAL_ANNOTATION = "ANNOTATION:D1P42_LOGICAL_SLOT_MAP_V1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_new_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def resolve(path_text: str, *, root: Path = ROOT) -> Path:
    path = Path(path_text)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"path outside repository: {path_text}") from error
    return resolved


def file_record(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(f"expected regular file: {path}")
    return {
        "path": resolved.relative_to(root.resolve()).as_posix(),
        "sha256": sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def verify_record(record: Mapping[str, Any]) -> Path:
    path = resolve(str(record["path"]))
    observed = file_record(path)
    if observed["sha256"] != record["sha256"]:
        raise ValueError(f"input hash mismatch: {record['path']}")
    if "size_bytes" in record and observed["size_bytes"] != record["size_bytes"]:
        raise ValueError(f"input size mismatch: {record['path']}")
    return path


def flatten_public_abi(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten the public Noir ABI without assigning roles from parameter names."""
    words: list[dict[str, Any]] = []
    for parameter in artifact.get("abi", {}).get("parameters", []):
        if parameter.get("visibility") != "public":
            continue
        name = str(parameter.get("name"))
        value_type = parameter.get("type", {})
        if value_type.get("kind") == "array":
            length = int(value_type["length"])
            element_type = value_type["type"]
            for index in range(length):
                words.append({
                    "abi_index": len(words),
                    "display_name": f"{name}[{index}]",
                    "type": element_type,
                })
        else:
            words.append({
                "abi_index": len(words),
                "display_name": name,
                "type": value_type,
            })
    return words


def solidity_index_anchor(ast_document: Mapping[str, Any]) -> tuple[str, str | None]:
    nodes: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("nodeType") == "IndexAccess":
                nodes.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ast_document)
    if len(nodes) != 1:
        raise ValueError(f"expected one checked public-input IndexAccess, found {len(nodes)}")
    return f"IndexAccess:{nodes[0]['id']}", nodes[0].get("src")


def type_string(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def identity_context(domain: str = "d1p42.bound-prefix.mechanical") -> ContextIdentity:
    return ContextIdentity(
        kind="PROGRAM_INTERFACE",
        domain=domain,
        deployment="UNSPECIFIED_MECHANICAL_FIXTURE",
        state_version="D2-06A-CONSTRUCTION-03",
        actor="UNSPECIFIED_MECHANICAL_FIXTURE",
        epoch="UNSPECIFIED_MECHANICAL_FIXTURE",
        attributes=(("policy_status", "NOT_REVIEWED_NOT_EVALUATED"),),
    )


def records_for_variant(
    *,
    variant_id: str,
    artifact_path: Path,
    consumer_ast_path: Path,
    producer_source_path: Path,
    consumer_source_path: Path,
    original_to_variant: Mapping[int, int],
    mapping_id: str,
) -> tuple[IdentityRecord, ...]:
    artifact = read_json(artifact_path)
    consumer_ast = read_json(consumer_ast_path)
    public_words = flatten_public_abi(artifact)
    if len(public_words) != len(LOGICAL_SLOTS):
        raise ValueError(f"{variant_id}: expected five public ABI words")
    if set(original_to_variant) != set(range(len(LOGICAL_SLOTS))):
        raise ValueError(f"{variant_id}: mapping source indices are not total")
    if set(original_to_variant.values()) != set(range(len(LOGICAL_SLOTS))):
        raise ValueError(f"{variant_id}: mapping target indices are not bijective")

    noir_artifact_hash = sha256(artifact_path)
    consumer_ast_hash = sha256(consumer_ast_path)
    producer_source_hash = sha256(producer_source_path)
    consumer_source_hash = sha256(consumer_source_path)
    consumer_node_id, consumer_span = solidity_index_anchor(consumer_ast)
    compiler_version = str(artifact.get("noir_version") or "UNKNOWN")
    solc_version = str(consumer_ast.get("version") or "UNKNOWN")

    records: list[IdentityRecord] = []
    for original_index, logical_slot in enumerate(LOGICAL_SLOTS):
        target_index = int(original_to_variant[original_index])
        word = public_words[target_index]
        representation = (
            "NOIR_FIELD"
            if word["type"].get("kind") == "field"
            else "NOIR_INTEGER"
        )
        record = IdentityRecord(
            object_identity=ObjectIdentity(
                kind="PUBLIC_STATEMENT_WORD",
                logical_slot=logical_slot,
                representation=representation,
                state_scope="TRANSITION_INPUT",
                encoding="ACIR_PUBLIC_INPUT",
                value_type=type_string(word["type"]),
                attributes=(("fixture_lineage", "D1P42_BOUND_PREFIX"),),
            ),
            context_identity=identity_context(),
            provenance=(
                CompilerProvenance(
                    artifact_sha256=noir_artifact_hash,
                    compiler_id="noir/nargo",
                    compiler_version=compiler_version,
                    artifact_schema="noir-program-artifact/beta.22",
                    evidence_kind="COMPILER_ABI",
                    abi_index=target_index,
                    logical_mapping_id=mapping_id,
                    source_sha256=producer_source_hash,
                    display_path=artifact_path.relative_to(ROOT).as_posix(),
                    display_span=None,
                ),
                CompilerProvenance(
                    artifact_sha256=consumer_ast_hash,
                    compiler_id="solc",
                    compiler_version=solc_version,
                    artifact_schema="solc-combined-json/ast",
                    evidence_kind="COMPILER_AST_INDEX_ACCESS",
                    node_id=consumer_node_id,
                    abi_index=target_index,
                    logical_mapping_id=mapping_id,
                    source_sha256=consumer_source_hash,
                    display_path=consumer_ast_path.relative_to(ROOT).as_posix(),
                    display_span=consumer_span,
                ),
            ),
            derivation_class="ANNOTATED",
            annotation_refs=(FIXTURE_LABEL, LOGICAL_ANNOTATION),
            mapping_refs=(mapping_id,),
            display_hints=(
                ("producer_abi_name", word["display_name"]),
                ("variant_id", variant_id),
            ),
        )
        records.append(record)
    return tuple(records)


def facts_for_records(records: Iterable[IdentityRecord]) -> tuple[IdentityFact, ...]:
    facts: list[IdentityFact] = []
    for record in records:
        compiler_records = record.provenance_payload()["compiler_records"]
        abi_indices = sorted({
            item["abi_index"] for item in compiler_records if item["abi_index"] is not None
        })
        facts.append(IdentityFact(
            fact_kind="COMPILER_ABI_POSITION",
            subject_identity_ref=record.reference(),
            object_identity_ref=None,
            quantifier="MUST",
            condition={"kind": "UNCONDITIONAL_WITHIN_COMPILED_INTERFACE"},
            approximation="EXACT",
            derivation_class="DERIVED",
            support="SUPPORTED",
            provenance_refs=(record.provenance_hash,),
            annotation_refs=(FIXTURE_LABEL,),
            mapping_refs=record.mapping_refs,
        ))
        facts.append(IdentityFact(
            fact_kind="ANNOTATED_LOGICAL_SLOT_MAPPING",
            subject_identity_ref=record.reference(),
            object_identity_ref=None,
            quantifier="MUST",
            condition={
                "kind": "MAPPING_CERTIFICATE_PRECONDITION",
                "physical_abi_indices": abi_indices,
            },
            approximation="EXACT",
            derivation_class="ANNOTATED",
            support="SUPPORTED",
            provenance_refs=(record.provenance_hash,),
            annotation_refs=(FIXTURE_LABEL, LOGICAL_ANNOTATION),
            mapping_refs=record.mapping_refs,
        ))
    return tuple(facts)


def variant_inputs(
    ledger: Mapping[str, Any], variant_id: str
) -> tuple[Mapping[str, Any], dict[int, int], Path | None, str]:
    if variant_id == "ORIGINAL":
        return (
            ledger["original"],
            {index: index for index in range(len(LOGICAL_SLOTS))},
            None,
            LOGICAL_ANNOTATION,
        )
    row = next(item for item in ledger["rows"] if item["id"] == variant_id)
    if not row.get("attempted") or row.get("status") != "SEMANTICALLY_CONTROLLED":
        raise ValueError(f"variant not available as a bounded control: {variant_id}")
    mapping_path = verify_record(row["mapping"])
    mapping = read_json(mapping_path)
    physical = {int(source): int(target) for source, target in mapping["physical_public_word_map"].items()}
    return (
        row["output"],
        physical,
        mapping_path,
        f"SOURCE-MAPPING-SHA256:{sha256(mapping_path)}",
    )


def build_bundle(
    ledger: Mapping[str, Any], variant_id: str
) -> tuple[IdentityBundle, Path | None, dict[int, int]]:
    output, physical_map, mapping_path, mapping_id = variant_inputs(ledger, variant_id)
    artifact_path = verify_record(output["build"]["producer_artifact"])
    consumer_ast_path = verify_record(output["build"]["consumer_ast"])
    producer_source_path = verify_record(output["source"]["producer"])
    consumer_source_path = verify_record(output["source"]["consumer"])
    records = records_for_variant(
        variant_id=variant_id,
        artifact_path=artifact_path,
        consumer_ast_path=consumer_ast_path,
        producer_source_path=producer_source_path,
        consumer_source_path=consumer_source_path,
        original_to_variant=physical_map,
        mapping_id=mapping_id,
    )
    inputs = [
        artifact_path, consumer_ast_path, producer_source_path, consumer_source_path,
    ]
    if mapping_path is not None:
        inputs.append(mapping_path)
    bundle = IdentityBundle(
        bundle_name=variant_id,
        identities=records,
        facts=facts_for_records(records),
        input_sha256=tuple(sha256(path) for path in inputs),
        limitations=(
            "Logical slots are an explicit unreviewed fixture annotation, not an inferred policy.",
            "No stable Noir SSA node identifier is exposed; producer anchoring uses the compiled public ABI index.",
            "The Solidity AST exposes one checked public-input IndexAccess; per-word interpretation uses the explicit mapping certificate.",
            "Identity records do not establish authorization, semantic equivalence, or a security verdict.",
        ),
    )
    validate_bundle(bundle.to_dict())
    return bundle, mapping_path, physical_map


def mapping_certificate(
    *,
    transformation_id: str,
    original: IdentityBundle,
    transformed: IdentityBundle,
    physical_map: Mapping[int, int],
    evidence_paths: Iterable[Path],
) -> MappingCertificate:
    original_by_slot = {
        item.object_identity.logical_slot: item for item in original.identities
    }
    transformed_by_slot = {
        item.object_identity.logical_slot: item for item in transformed.identities
    }
    entries = tuple(
        MappingEntry(
            logical_slot=slot,
            from_identity_ref=original_by_slot[slot].reference(),
            to_identity_ref=transformed_by_slot[slot].reference(),
            from_abi_index=index,
            to_abi_index=int(physical_map[index]),
        )
        for index, slot in enumerate(LOGICAL_SLOTS)
    )
    certificate = MappingCertificate(
        transformation_id=transformation_id,
        source_bundle_id=original.bundle_id,
        target_bundle_id=transformed.bundle_id,
        entries=entries,
        source_identity_count=len(original.identities),
        target_identity_count=len(transformed.identities),
        evidence_sha256=tuple(sha256(path) for path in evidence_paths),
        mapping_source_refs=tuple(sorted({
            ref
            for identity in transformed.identities
            for ref in identity.mapping_refs
        })),
    )
    properties = certificate.properties
    if not all(properties[name] for name in (
        "total", "injective", "surjective", "semantic_identity_preserving",
    )):
        raise ValueError(f"mapping certificate failed: {transformation_id}: {properties}")
    validate_mapping_certificate(
        certificate.to_dict(),
        source_bundle=original.to_dict(),
        target_bundle=transformed.to_dict(),
    )
    return certificate


def validate_external_reference_inventory(
    *,
    bundles: Mapping[str, IdentityBundle],
    mappings: Mapping[str, MappingCertificate],
    inventory: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Require every external bundle/certificate ref to have a run registry row."""
    known_annotations = set(inventory.get("annotation_refs", {}))
    known_mappings = set(inventory.get("mapping_refs", {}))
    known_assumptions = set(inventory.get("assumption_refs", {}))
    known_parents = set(inventory.get("parent_fact_refs", {}))
    known_provenance = set(inventory.get("provenance_refs", {}))
    unresolved: list[str] = []
    for bundle in bundles.values():
        for identity in bundle.identities:
            unresolved.extend(
                f"annotation:{ref}" for ref in identity.annotation_refs
                if ref not in known_annotations
            )
            unresolved.extend(
                f"mapping:{ref}" for ref in identity.mapping_refs
                if ref not in known_mappings
            )
            unresolved.extend(
                f"assumption:{ref}" for ref in identity.assumption_refs
                if ref not in known_assumptions
            )
        for fact in bundle.facts:
            unresolved.extend(
                f"annotation:{ref}" for ref in fact.annotation_refs
                if ref not in known_annotations
            )
            unresolved.extend(
                f"mapping:{ref}" for ref in fact.mapping_refs
                if ref not in known_mappings
            )
            unresolved.extend(
                f"assumption:{ref}" for ref in fact.assumption_refs
                if ref not in known_assumptions
            )
            unresolved.extend(
                f"parent:{ref}" for ref in fact.parent_fact_ids
                if ref.startswith("external:") and ref not in known_parents
            )
            unresolved.extend(
                f"provenance:{ref}" for ref in fact.provenance_refs
                if ref.startswith("external:") and ref not in known_provenance
            )
    for certificate in mappings.values():
        unresolved.extend(
            f"mapping:{ref}" for ref in certificate.mapping_source_refs
            if ref not in known_mappings
        )
    if unresolved:
        raise ValueError(f"unresolved external reference inventory: {sorted(set(unresolved))}")
    return {
        "status": "PASS",
        "annotation_ref_count": len(known_annotations),
        "mapping_ref_count": len(known_mappings),
        "assumption_ref_count": len(known_assumptions),
        "external_parent_ref_count": len(known_parents),
        "external_provenance_ref_count": len(known_provenance),
    }


def build_external_reference_inventory(
    mapping_paths: Iterable[Path | None],
) -> dict[str, Any]:
    mapping_refs: dict[str, dict[str, Any]] = {
        LOGICAL_ANNOTATION: {
            "kind": "UNREVIEWED_FIXTURE_ANNOTATION",
            "logical_slots": list(LOGICAL_SLOTS),
        }
    }
    for path in mapping_paths:
        if path is None:
            continue
        mapping_refs[f"SOURCE-MAPPING-SHA256:{sha256(path)}"] = {
            "kind": "HASH_BOUND_STEP6_MAPPING_SOURCE",
            "file": file_record(path),
        }
    return {
        "mapping_refs": mapping_refs,
        "annotation_refs": {
            FIXTURE_LABEL: {
                "kind": "EXECUTION_SCOPE_LABEL",
                "status": "MECHANICAL_ONLY",
            },
            LOGICAL_ANNOTATION: {
                "kind": "UNREVIEWED_FIXTURE_ANNOTATION",
                "status": "NOT_POLICY",
            },
        },
        "assumption_refs": {},
        "parent_fact_refs": {},
        "provenance_refs": {},
        "unlisted_external_refs": "INVALID_FOR_THIS_RUN",
    }


def negative_fixtures(original: IdentityBundle, reorder: MappingCertificate) -> dict[str, Any]:
    base = original.identities[0]
    second = original.identities[1]
    same_display_first = IdentityRecord(
        object_identity=base.object_identity,
        context_identity=base.context_identity,
        provenance=base.provenance,
        derivation_class="ANNOTATED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:SAME_NAME_DIFFERENT_OBJECT"),
        display_hints=(("surface_name", "root"),),
    )
    same_display_second = IdentityRecord(
        object_identity=second.object_identity,
        context_identity=second.context_identity,
        provenance=second.provenance,
        derivation_class="ANNOTATED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:SAME_NAME_DIFFERENT_OBJECT"),
        display_hints=(("surface_name", "root"),),
    )
    alternate_context = IdentityRecord(
        object_identity=base.object_identity,
        context_identity=identity_context("d1p42.alternate-context-negative"),
        provenance=base.provenance,
        derivation_class="ANNOTATED",
        support="UNKNOWN",
        reason="SYNTHETIC_CONTEXT_NEGATIVE_NOT_COMPILER_DERIVED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:SAME_OBJECT_DIFFERENT_CONTEXT"),
        display_hints=(("surface_name", "root"),),
    )
    pair_b = IdentityRecord(
        object_identity=second.object_identity,
        context_identity=alternate_context.context_identity,
        provenance=second.provenance,
        derivation_class="ANNOTATED",
        support="UNKNOWN",
        reason="SYNTHETIC_CONTEXT_NEGATIVE_NOT_COMPILER_DERIVED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:OBJECT_CONTEXT_SWAP"),
    )
    crossed_a = IdentityRecord(
        object_identity=base.object_identity,
        context_identity=alternate_context.context_identity,
        provenance=base.provenance,
        derivation_class="ANNOTATED",
        support="UNKNOWN",
        reason="SYNTHETIC_CONTEXT_NEGATIVE_NOT_COMPILER_DERIVED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:OBJECT_CONTEXT_SWAP"),
    )
    crossed_b = IdentityRecord(
        object_identity=second.object_identity,
        context_identity=base.context_identity,
        provenance=second.provenance,
        derivation_class="ANNOTATED",
        support="UNKNOWN",
        reason="SYNTHETIC_CONTEXT_NEGATIVE_NOT_COMPILER_DERIVED",
        annotation_refs=(FIXTURE_LABEL, "NEGATIVE:OBJECT_CONTEXT_SWAP"),
    )
    renamed_display = IdentityRecord(
        object_identity=base.object_identity,
        context_identity=base.context_identity,
        provenance=base.provenance,
        derivation_class="ANNOTATED",
        annotation_refs=(FIXTURE_LABEL, "CONTROL:DISPLAY_NAME_IGNORED"),
        display_hints=(("surface_name", "deliberately_different_label"),),
    )
    rows = [
        {
            "id": "NEG-SAME-NAME-DIFFERENT-OBJECT",
            "fixture_label": FIXTURE_LABEL,
            "left": same_display_first.to_dict(),
            "right": same_display_second.to_dict(),
            "expected": "MISMATCH",
            "observed": (
                "MATCH" if same_display_first.semantic_hash == same_display_second.semantic_hash
                else "MISMATCH"
            ),
            "claim_limit": "Equal display names do not establish equal objects.",
        },
        {
            "id": "NEG-SAME-OBJECT-DIFFERENT-CONTEXT",
            "fixture_label": FIXTURE_LABEL,
            "left": same_display_first.to_dict(),
            "right": alternate_context.to_dict(),
            "expected": "MISMATCH",
            "observed": (
                "MATCH" if same_display_first.semantic_hash == alternate_context.semantic_hash
                else "MISMATCH"
            ),
            "claim_limit": "Equal object structure does not erase context identity.",
        },
        {
            "id": "NEG-OBJECT-CONTEXT-CROSS-SWAP",
            "fixture_label": FIXTURE_LABEL,
            "original_hashes": sorted((base.semantic_hash, pair_b.semantic_hash)),
            "crossed_hashes": sorted((crossed_a.semantic_hash, crossed_b.semantic_hash)),
            "expected": "MISMATCH",
            "observed": (
                "MATCH"
                if {base.semantic_hash, pair_b.semantic_hash}
                == {crossed_a.semantic_hash, crossed_b.semantic_hash}
                else "MISMATCH"
            ),
            "claim_limit": "Cross-pairing an object with another context changes identity.",
        },
        {
            "id": "CONTROL-MATCHED-REORDER",
            "fixture_label": FIXTURE_LABEL,
            "mapping_id": reorder.mapping_id,
            "properties": reorder.properties,
            "expected": "SEMANTIC_IDENTITY_PRESERVED_WITH_EXPLICIT_NON_ORDER_PRESERVING_MAPPING",
            "observed": (
                "SEMANTIC_IDENTITY_PRESERVED_WITH_EXPLICIT_NON_ORDER_PRESERVING_MAPPING"
                if reorder.properties["semantic_identity_preserving"]
                and not reorder.properties["order_preserving"]
                else "CONTROL_FAILURE"
            ),
            "claim_limit": "The explicit mapping supports this bounded fixture only.",
        },
        {
            "id": "CONTROL-DISPLAY-NAME-IGNORED",
            "fixture_label": FIXTURE_LABEL,
            "left": same_display_first.to_dict(),
            "right": renamed_display.to_dict(),
            "expected": "MATCH",
            "observed": (
                "MATCH"
                if same_display_first.semantic_hash == renamed_display.semantic_hash
                else "MISMATCH"
            ),
            "claim_limit": "Display-label stability is a hash-domain check, not a policy conclusion.",
        },
    ]
    if any(row["observed"] != row["expected"] for row in rows):
        raise ValueError("negative fixture known-answer mismatch")
    return {
        "schema": "bindcheck.d2.step8-negative-identity-fixtures/v1",
        "fixture_label": FIXTURE_LABEL,
        "status": "PASS",
        "rows": rows,
        "security_verdict": None,
        "scored": False,
    }


def name_influence_audit(valid_bundle: Mapping[str, Any]) -> dict[str, Any]:
    source = ROLE_BINDING.read_text()
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def call_count(function_name: str, callee: str) -> int:
        return sum(
            1
            for node in ast.walk(functions[function_name])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == callee
        )

    def symbol_reference_count(function_name: str, symbol: str) -> int:
        return sum(
            1
            for node in ast.walk(functions[function_name])
            if isinstance(node, ast.Name) and node.id == symbol
        )

    public_name_calls = {
        name: call_count("analyze_role_binding", name)
        for name in ("canonical_role", "semantic_identity", "_analyze_legacy_name_roles")
    }
    public_legacy_symbol_references = {
        name: symbol_reference_count("analyze_role_binding", name)
        for name in ("canonical_role", "semantic_identity", "_analyze_legacy_name_roles")
    }
    legacy_name_calls = {
        name: call_count("_analyze_legacy_name_roles", name)
        for name in ("canonical_role", "semantic_identity")
    }
    del valid_bundle
    public_string_literals = {
        node.value
        for node in ast.walk(functions["analyze_role_binding"])
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    required_unknown_literals = {
        "COMPILER_BACKED_IDENTITY_REQUIRED": any(
            value.startswith("COMPILER_BACKED_IDENTITY_REQUIRED:")
            for value in public_string_literals
        ),
        "AUTHORIZATION_BOUNDARY_CHECK_REQUIRED_STEP9": any(
            value.startswith("AUTHORIZATION_BOUNDARY_CHECK_REQUIRED_STEP9:")
            for value in public_string_literals
        ),
    }
    status = "PASS" if (
        LEGACY_SURFACE_ROLE_STATUS == "ANNOTATION_ONLY_QUARANTINED"
        and not any(public_name_calls.values())
        and not any(public_legacy_symbol_references.values())
        and any(legacy_name_calls.values())
        and all(required_unknown_literals.values())
    ) else "FAIL"
    if status != "PASS":
        raise ValueError("name-influence quarantine audit failed")
    return {
        "schema": "bindcheck.d2.step8-name-influence-audit/v1",
        "fixture_label": FIXTURE_LABEL,
        "status": status,
        "public_entry_name_dependent_call_counts": public_name_calls,
        "public_entry_legacy_symbol_reference_counts": public_legacy_symbol_references,
        "quarantined_legacy_name_dependent_call_counts": legacy_name_calls,
        "legacy_surface_role_status": LEGACY_SURFACE_ROLE_STATUS,
        "required_unknown_reason_literals_present": required_unknown_literals,
        "runtime_behavior_covered_by_focused_tests_not_dispatched_in_raw_run": True,
        "conclusion": "Surface names and legacy semantic tokens cannot reach the public security-warning path; the boundary remains UNKNOWN pending Step 9.",
        "scored": False,
        "security_verdict": None,
    }


def validate_protocol(protocol: Mapping[str, Any]) -> None:
    if protocol.get("status") != "AUTHORIZED_MECHANICAL_PROTOTYPE_UNSCORED":
        raise ValueError("Step 8 protocol status is not authorized mechanical scope")
    if protocol.get("fixture_label") != FIXTURE_LABEL:
        raise ValueError("Step 8 fixture label mismatch")
    boundary = protocol.get("execution_boundary", {})
    if boundary.get("scored") is not False:
        raise ValueError("Step 8 cannot score")
    if boundary.get("security_verdict_authorized") is not False:
        raise ValueError("Step 8 cannot emit a security verdict")
    if protocol.get("step_7_authority", {}).get("seal_sha256") != sha256(STEP7_SEAL):
        raise ValueError("Step 7 authority seal hash mismatch")
    if protocol.get("step_7_authority", {}).get("report_sha256") != sha256(STEP7_REPORT):
        raise ValueError("Step 7 authority report hash mismatch")
    if protocol.get("inputs", {}).get("construction_run_manifest_sha256") != sha256(
        STEP6_MANIFEST
    ):
        raise ValueError("Step 6 construction run-manifest hash mismatch")
    authority_verification = foundation.verify_seal(root=ROOT, manifest=STEP7_SEAL)
    if authority_verification["status"] != "PASS":
        raise ValueError("Step 7 authority seal no longer verifies")


def run(*, protocol_path: Path, ledger_path: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise FileExistsError(f"refusing to reuse output namespace: {out}")
    protocol = read_json(protocol_path)
    validate_protocol(protocol)
    ledger = read_json(ledger_path)
    if sha256(ledger_path) != protocol["inputs"]["transformation_ledger_sha256"]:
        raise ValueError("transformation ledger hash mismatch")
    if ledger.get("status") != "CONSTRUCTION_SMOKE_ONLY":
        raise ValueError("unexpected transformation ledger status")

    started = time.monotonic()
    bundles: dict[str, IdentityBundle] = {}
    mapping_paths: dict[str, Path | None] = {}
    physical_maps: dict[str, dict[int, int]] = {}
    for variant_id in ("ORIGINAL", *TRANSFORMATION_IDS):
        bundle, mapping_path, physical_map = build_bundle(ledger, variant_id)
        bundles[variant_id] = bundle
        mapping_paths[variant_id] = mapping_path
        physical_maps[variant_id] = physical_map

    original = bundles["ORIGINAL"]
    mappings: dict[str, MappingCertificate] = {}
    for variant_id in TRANSFORMATION_IDS:
        output, _physical, _path, _mapping_id = variant_inputs(ledger, variant_id)
        evidence_paths = [
            mapping_paths[variant_id],
            verify_record(output["build"]["producer_artifact"]),
            verify_record(output["build"]["consumer_ast"]),
        ]
        mappings[variant_id] = mapping_certificate(
            transformation_id=variant_id,
            original=original,
            transformed=bundles[variant_id],
            physical_map=physical_maps[variant_id],
            evidence_paths=[path for path in evidence_paths if path is not None],
        )

    reorder = mappings["TR-MATCHED-PUBLIC-REORDER"]
    negatives = negative_fixtures(original, reorder)
    name_audit = name_influence_audit(original.to_dict())

    out.mkdir(parents=True)
    run_manifest_path = out / "run-manifest.json"
    foundation.prepare_run_manifest(
        root=ROOT,
        output=run_manifest_path,
        run_id="D2-08-compiler-identity-01",
        experiment="compiler-backed-object-context-identity-mechanical-prototype",
        inputs=[ledger_path, STEP6_MANIFEST, STEP7_SEAL, STEP7_REPORT],
        configurations=[protocol_path],
        seeds=[],
        wall_seconds=protocol["resource_budget"]["wall_seconds"],
        memory_mib=protocol["resource_budget"]["memory_mib"],
        max_calls=protocol["resource_budget"]["subprocess_calls"],
    )

    bundle_records: dict[str, dict[str, Any]] = {}
    for variant_id, bundle in bundles.items():
        path = out / "identity-bundles" / f"{variant_id}.json"
        write_new_json(path, bundle.to_dict())
        bundle_records[variant_id] = file_record(path)
    mapping_records: dict[str, dict[str, Any]] = {}
    for variant_id, certificate in mappings.items():
        path = out / "mapping-certificates" / f"{variant_id}.json"
        write_new_json(path, certificate.to_dict())
        mapping_records[variant_id] = file_record(path)

    negative_path = out / "negative-fixtures.json"
    write_new_json(negative_path, negatives)
    audit_path = out / "name-influence-audit.json"
    write_new_json(audit_path, name_audit)

    input_files: set[Path] = {
        ledger_path.resolve(),
        STEP6_MANIFEST.resolve(),
        STEP7_SEAL.resolve(),
        STEP7_REPORT.resolve(),
    }
    for variant_id in ("ORIGINAL", *TRANSFORMATION_IDS):
        output, _mapping, mapping_path, _mapping_id = variant_inputs(ledger, variant_id)
        for key in ("producer_artifact", "consumer_ast"):
            input_files.add(verify_record(output["build"][key]))
        for key in ("producer", "consumer"):
            input_files.add(verify_record(output["source"][key]))
        if mapping_path is not None:
            input_files.add(mapping_path)
    external_reference_inventory = build_external_reference_inventory(
        mapping_paths.values()
    )
    reference_resolution = validate_external_reference_inventory(
        bundles=bundles,
        mappings=mappings,
        inventory=external_reference_inventory,
    )
    input_manifest = {
        "schema": "bindcheck.d2.step8-input-manifest/v1",
        "created_at_utc": utc_now(),
        "fixture_label": FIXTURE_LABEL,
        "files": [file_record(path) for path in sorted(input_files)],
        "logical_slot_annotation": {
            "id": LOGICAL_ANNOTATION,
            "slots": list(LOGICAL_SLOTS),
            "status": "ANNOTATED_UNREVIEWED_MECHANICAL_FIXTURE",
        },
        "external_reference_inventory": external_reference_inventory,
        "external_reference_resolution": reference_resolution,
    }
    input_manifest_path = out / "input-manifest.json"
    write_new_json(input_manifest_path, input_manifest)

    elapsed = round(time.monotonic() - started, 6)
    summary = {
        "schema": "bindcheck.d2.step8-compiler-identity-summary/v1",
        "created_at_utc": utc_now(),
        "status": "PASS_MECHANICAL_ONLY",
        "fixture_label": FIXTURE_LABEL,
        "scored": False,
        "score_rows": [],
        "security_verdict": None,
        "research_verdict": "UNKNOWN",
        "analyzer_or_policy_checker_dispatched": False,
        "proof_calls": 0,
        "network_calls": 0,
        "scientific_retries": 0,
        "bundle_count": len(bundle_records),
        "identities_per_bundle": len(LOGICAL_SLOTS),
        "facts_per_bundle": len(original.facts),
        "mapping_count": len(mapping_records),
        "mapping_properties": {
            key: value.properties for key, value in sorted(mappings.items())
        },
        "negative_fixture_count": len(negatives["rows"]),
        "name_influence_audit": name_audit["status"],
        "external_reference_resolution": reference_resolution["status"],
        "outputs": {
            "bundles": bundle_records,
            "mappings": mapping_records,
            "negative_fixtures": file_record(negative_path),
            "name_influence_audit": file_record(audit_path),
            "input_manifest": file_record(input_manifest_path),
        },
        "effort": {
            "runner_wall_seconds": elapsed,
            "subprocess_calls": 7,
            "subprocess_call_breakdown": {
                "foundation_git_metadata_calls": 7,
                "analyzer_compiler_policy_proof_or_score_calls": 0,
            },
            "human_minutes": None,
            "human_minutes_reason": "No independently timed human session; zero is not imputed.",
        },
        "limitations": [
            "Mechanical unreviewed development fixture only.",
            "Logical slot annotations are not independently reviewed policy or automatic semantic recovery.",
            "No authorization, P/O/E check, analyzer score, proof, or security verdict ran.",
            "Mapping controls are bounded source/mapping/compiler checks, not formal or general semantic-equivalence proofs.",
            "No stable Noir SSA node identifier was available in the preserved artifact.",
        ],
    }
    summary_path = out / "run-summary.json"
    write_new_json(summary_path, summary)

    # Enumerate every pre-seal raw file without relying on mutable indexes.
    checksum_members = sorted(path for path in out.rglob("*") if path.is_file())
    checksum_path = out / "checksums.sha256"
    checksum_path.write_text("".join(
        f"{sha256(path)}  {path.relative_to(out).as_posix()}\n"
        for path in checksum_members
    ))

    seal_entries = [resolve(path) for path in protocol["seal_plan"]["entries"]]
    seal_path = out / "content-seal-v1.json"
    seal = foundation.create_seal(
        root=ROOT,
        output=seal_path,
        version=protocol["seal_plan"]["version"],
        entries=[
            *seal_entries,
            run_manifest_path,
            *bundle_records_paths(out),
            *mapping_records_paths(out),
            negative_path,
            audit_path,
            input_manifest_path,
            summary_path,
            checksum_path,
        ],
    )
    verification = foundation.verify_seal(root=ROOT, manifest=seal_path)
    if verification["status"] != "PASS":
        raise RuntimeError(f"new Step 8 seal failed: {verification}")
    sealed_index = {record["path"]: record for record in seal["files"]}
    input_mismatches = [
        record["path"]
        for record in input_manifest["files"]
        if sealed_index.get(record["path"]) != record
    ]
    if input_mismatches:
        raise RuntimeError(
            f"input manifest does not match final seal: {input_mismatches}"
        )
    verification.update({
        "created_at_utc": utc_now(),
        "post_seal_record_not_sealed_due_to_hash_dependency": True,
        "scored": False,
        "security_verdict": None,
        "input_manifest_matches_final_seal": True,
    })
    write_new_json(out / "seal-verification.json", verification)
    return summary


def bundle_records_paths(out: Path) -> list[Path]:
    return sorted((out / "identity-bundles").glob("*.json"))


def mapping_records_paths(out: Path) -> list[Path]:
    return sorted((out / "mapping-certificates").glob("*.json"))


def validate_only(protocol_path: Path, ledger_path: Path) -> dict[str, Any]:
    protocol = read_json(protocol_path)
    validate_protocol(protocol)
    ledger = read_json(ledger_path)
    if sha256(ledger_path) != protocol["inputs"]["transformation_ledger_sha256"]:
        raise ValueError("transformation ledger hash mismatch")
    built = {
        variant_id: build_bundle(ledger, variant_id)
        for variant_id in ("ORIGINAL", *TRANSFORMATION_IDS)
    }
    bundles = {variant_id: value[0] for variant_id, value in built.items()}
    mappings: dict[str, MappingCertificate] = {}
    for variant_id in TRANSFORMATION_IDS:
        output, _physical, _mapping_path, _mapping_id = variant_inputs(
            ledger, variant_id
        )
        evidence_paths = [
            built[variant_id][1],
            verify_record(output["build"]["producer_artifact"]),
            verify_record(output["build"]["consumer_ast"]),
        ]
        mappings[variant_id] = mapping_certificate(
            transformation_id=variant_id,
            original=bundles["ORIGINAL"],
            transformed=bundles[variant_id],
            physical_map=built[variant_id][2],
            evidence_paths=[path for path in evidence_paths if path is not None],
        )
    negatives = negative_fixtures(
        bundles["ORIGINAL"], mappings["TR-MATCHED-PUBLIC-REORDER"]
    )
    name_audit = name_influence_audit(bundles["ORIGINAL"].to_dict())
    reference_resolution = validate_external_reference_inventory(
        bundles=bundles,
        mappings=mappings,
        inventory=build_external_reference_inventory(
            value[1] for value in built.values()
        ),
    )
    return {
        "status": "PASS",
        "fixture_label": FIXTURE_LABEL,
        "bundle_count": len(bundles),
        "identity_count": sum(len(bundle.identities) for bundle in bundles.values()),
        "mapping_count": len(mappings),
        "negative_fixture_count": len(negatives["rows"]),
        "name_influence_audit": name_audit["status"],
        "external_reference_resolution": reference_resolution["status"],
        "scored": False,
        "security_verdict": None,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate_only:
        print(json.dumps(
            validate_only(args.protocol.resolve(), args.ledger.resolve()),
            indent=2,
            sort_keys=True,
        ))
        return 0
    summary = run(
        protocol_path=args.protocol.resolve(),
        ledger_path=args.ledger.resolve(),
        out=args.out.resolve(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
