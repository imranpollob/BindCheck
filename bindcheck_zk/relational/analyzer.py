from __future__ import annotations

import datetime as dt
import pathlib
import re
import shutil
import time
from collections import defaultdict
from typing import Any, Callable

from ..circuits import Circuit, attach_or_build, discover, is_entry_circuit
from ..models import Budget, aggregate, result, sha256_file
from .compiled import CompiledRelation
from .extract import (
    ConsumerPath,
    array_reliance,
    canonical_identifier,
    conditional_array,
    consumer_paths,
    consumer_representation,
    nullifier_constraint,
    normalized_public_name,
    producer_representation,
    relied_identifier,
    role,
    scoped_replay,
    source_enforces_identity,
    vector_names,
)


DIMENSIONS = (
    "EXTENT",
    "MASK",
    "REPRESENTATION",
    "MULTIPLICITY_SCOPE",
    "ROLE_IDENTITY",
)

PATTERNS = {
    "EXTENT": "REL_EXTENT",
    "MASK": "REL_MASK",
    "REPRESENTATION": "REL_REPRESENTATION",
    "MULTIPLICITY_SCOPE": "REL_MULTIPLICITY_SCOPE",
    "ROLE_IDENTITY": "REL_ROLE_IDENTITY",
}

EXCLUDED_PARTS = {
    ".git", "node_modules", "vendor", "vendors", "dist", "build", "out",
    "cache", "target", "coverage", ".next", ".venv", "__pycache__",
}


def _finding(
    dimension: str,
    verdict: str,
    reason: str,
    message: str,
    *,
    facts: list[dict[str, Any]] | None = None,
    applicability: str = "APPLICABLE",
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    finding = result(
        PATTERNS[dimension], verdict, reason, message,
        facts=facts, applicability=applicability, limitations=limitations,
    )
    finding["dimension"] = dimension
    return finding


def _not_applicable(dimension: str, reason: str, message: str) -> dict[str, Any]:
    return _finding(
        dimension, "UNKNOWN", reason, message,
        applicability="NOT_APPLICABLE",
    )


def _source(circuit: Circuit) -> str:
    return circuit.path.read_text(encoding="utf-8", errors="replace")


def _compiled_condition_facts(
    relation: CompiledRelation, template: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    facts: list[dict[str, Any]] = []
    complete = True
    for index in range(template["count"]):
        selector = f"{template['selector']}[{index}]"
        value = f"{template['values']}[{index}]"
        witness = f"{template['witness']}[{index}]"
        selector_value = relation.shares_constraint(selector, value)
        value_witness = relation.shares_constraint(value, witness)
        complete &= selector_value and value_witness
        facts.append({
            "provenance": "PROVED",
            "public_value": value,
            "selector": selector,
            "private_value": witness,
            "selector_and_value_share_r1cs_constraint": selector_value,
            "value_and_private_share_r1cs_constraint": value_witness,
        })
    return complete, facts


def _analyze_extent(circuit: Circuit, relation: CompiledRelation, consumer: ConsumerPath) -> dict[str, Any]:
    template = conditional_array(_source(circuit))
    if template is None or not template["prefix_enforced"]:
        return _not_applicable(
            "EXTENT", "PRODUCER_PREFIX_ENFORCEMENT_NOT_RECOVERED",
            "No supported compiled selector/count prefix enforcement was recovered.",
        )
    complete, facts = _compiled_condition_facts(relation, template)
    if not complete:
        return _finding(
            "EXTENT", "UNKNOWN", "COMPILED_CONDITION_NOT_CONFIRMED",
            "The Circom source resembles a prefix template, but its selector/value constraints were not confirmed in R1CS/sym.",
            facts=facts,
        )
    reliance = array_reliance(consumer, template["values"])
    if reliance is None:
        return _not_applicable(
            "EXTENT", "CONSUMER_ARRAY_RELIANCE_NOT_RECOVERED",
            "No supported effect or state-write loop relies on the producer array.",
        )
    facts.extend([
        {
            "provenance": "EXTRACTED",
            "producer_condition": f"index < {template['extent_signal']}",
            "selector": template["selector"],
            "count": template["count"],
        },
        {
            "provenance": "EXTRACTED",
            "consumer_condition": f"index < {reliance['bound']}",
            "consumer": f"{consumer.relative_path}:{consumer.function.line}",
        },
    ])
    if reliance["bound"] == template["extent_signal"]:
        return _finding(
            "EXTENT", "VERIFIED_WITHIN_SCOPE", "RELIANCE_CONTAINED_IN_PRODUCER_ENFORCEMENT",
            "The recovered consumer loop uses the same active-prefix extent as the compiled producer condition.",
            facts=facts,
            limitations=["This conclusion covers the exact selector/count template and recovered loop only."],
        )
    if reliance["bound"].isdigit() and int(reliance["bound"]) == template["count"]:
        facts.append({
            "provenance": "PROVED",
            "uncovered_region": f"{template['extent_signal']} <= index < {template['count']}",
        })
        return _finding(
            "EXTENT", "VIOLATION", "CONSUMER_RELIANCE_EXCEEDS_PRODUCER_EXTENT",
            "The consumer commits effects for every configured slot, including slots outside the producer's active prefix.",
            facts=facts,
        )
    return _finding(
        "EXTENT", "UNKNOWN", "CONDITION_IMPLICATION_UNSUPPORTED",
        "Both extent conditions were recovered, but their implication is outside the supported exact-equality/full-width comparison.",
        facts=facts,
    )


def _analyze_mask(circuit: Circuit, relation: CompiledRelation, consumer: ConsumerPath) -> dict[str, Any]:
    template = conditional_array(_source(circuit))
    if template is None or template["prefix_enforced"]:
        return _not_applicable(
            "MASK", "PRODUCER_MASK_ENFORCEMENT_NOT_RECOVERED",
            "No supported non-prefix selector-mask enforcement was recovered.",
        )
    complete, facts = _compiled_condition_facts(relation, template)
    if not complete:
        return _finding(
            "MASK", "UNKNOWN", "COMPILED_CONDITION_NOT_CONFIRMED",
            "The Circom source resembles a mask template, but R1CS/sym did not confirm every selector/value constraint.",
            facts=facts,
        )
    reliance = array_reliance(consumer, template["values"], template["selector"])
    if reliance is None:
        return _not_applicable(
            "MASK", "CONSUMER_ARRAY_RELIANCE_NOT_RECOVERED",
            "No supported consumer effect or state update relies on the masked array.",
        )
    facts.extend([
        {"provenance": "EXTRACTED", "producer_condition": f"{template['selector']}[index] == 1"},
        {
            "provenance": "EXTRACTED",
            "consumer_condition": (
                f"{template['selector']}[index] == 1"
                if reliance["guarded_by_selector"] else "always"
            ),
            "consumer": f"{consumer.relative_path}:{consumer.function.line}",
        },
    ])
    if reliance["guarded_by_selector"]:
        return _finding(
            "MASK", "VERIFIED_WITHIN_SCOPE", "RELIANCE_CONTAINED_IN_PRODUCER_ENFORCEMENT",
            "The consumer effect is guarded by the same selector that conditions the compiled producer constraint.",
            facts=facts,
            limitations=["The conclusion is local to the recovered loop and equality-to-one guard."],
        )
    return _finding(
        "MASK", "VIOLATION", "CONSUMER_RELIANCE_OVERLAPS_UNENFORCED_MASK",
        "The consumer relies on every array slot although the producer constrains a slot only when its selector is enabled.",
        facts=facts,
    )


def _analyze_representation(circuit: Circuit, relation: CompiledRelation, consumer: ConsumerPath) -> dict[str, Any]:
    producer = producer_representation(_source(circuit))
    if producer is None:
        return _not_applicable(
            "REPRESENTATION", "PRODUCER_REPRESENTATION_NOT_RECOVERED",
            "No supported linear packed-value representation was recovered from the circuit.",
        )
    consumer_fact = consumer_representation(consumer, producer["array"])
    if consumer_fact is None:
        return _not_applicable(
            "REPRESENTATION", "CONSUMER_REPRESENTATION_NOT_RECOVERED",
            "No supported effect-bearing consumer decode of the circuit array was recovered.",
        )
    compiled = all(
        relation.shares_constraint(producer["packed"], f"{producer['array']}[{index}]")
        for index in producer["weights"]
    )
    facts = [
        {
            "provenance": "PROVED",
            "packed_signal": producer["packed"],
            "array": producer["array"],
            "all_limbs_share_packing_constraint": compiled,
        },
        {"provenance": "EXTRACTED", "producer_weights": producer["weights"]},
        {"provenance": "EXTRACTED", "consumer_weights": consumer_fact["weights"]},
    ]
    if not compiled:
        return _finding(
            "REPRESENTATION", "UNKNOWN", "COMPILED_REPRESENTATION_NOT_CONFIRMED",
            "Source-level weights were recovered, but the packed signal and every limb did not share a compiled constraint.",
            facts=facts,
        )
    if producer["weights"] != consumer_fact["weights"]:
        return _finding(
            "REPRESENTATION", "VIOLATION", "REPRESENTATION_MISMATCH",
            "The consumer assigns different positional weights to proof-constrained limbs.",
            facts=facts,
        )
    return _finding(
        "REPRESENTATION", "VERIFIED_WITHIN_SCOPE", "REPRESENTATION_COMPATIBLE",
        "Producer and consumer use the same recovered linear weights for every decoded limb.",
        facts=facts,
        limitations=["Range constraints and nonlinear encodings are outside this linear-representation result."],
    )


def _analyze_scope(circuit: Circuit, relation: CompiledRelation, consumer: ConsumerPath) -> dict[str, Any]:
    producer = nullifier_constraint(_source(circuit))
    consumer_fact = scoped_replay(consumer)
    if producer is None or consumer_fact is None:
        return _not_applicable(
            "MULTIPLICITY_SCOPE", "SCOPED_UNIQUENESS_PATTERN_NOT_RECOVERED",
            "A supported nullifier derivation and two-level consumer replay barrier were not both recovered.",
        )
    public_names = [normalized_public_name(name).split("[", 1)[0] for name in circuit.public_order]
    vector = vector_names(consumer.vector)
    mapped: dict[str, str] = {
        consumer_name: circuit_name
        for circuit_name, consumer_name in zip(public_names, vector)
        if consumer_name is not None
    }
    scope_public = mapped.get(consumer_fact["scope"])
    nullifier_public = mapped.get(consumer_fact["nullifier"])
    if scope_public is None or nullifier_public is None:
        return _finding(
            "MULTIPLICITY_SCOPE", "UNKNOWN", "PUBLIC_INPUT_CORRESPONDENCE_UNRESOLVED",
            "The consumer replay keys could not be mapped positionally to compiled circuit public signals.",
        )
    source_includes_scope = scope_public in producer["dependencies"]
    direct = relation.shares_constraint(producer["nullifier"], scope_public)
    connected = relation.connected(producer["nullifier"], scope_public)
    facts = [
        {
            "provenance": "EXTRACTED",
            "consumer_mapping": consumer_fact["mapping"],
            "consumer_scope": consumer_fact["scope"],
            "consumer_nullifier": consumer_fact["nullifier"],
        },
        {
            "provenance": "EXTRACTED",
            "producer_nullifier": producer["nullifier"],
            "producer_dependencies": producer["dependencies"],
            "mapped_scope_signal": scope_public,
        },
        {
            "provenance": "PROVED",
            "scope_and_nullifier_share_constraint": direct,
            "scope_and_nullifier_r1cs_connected": connected,
        },
    ]
    if source_includes_scope and direct:
        return _finding(
            "MULTIPLICITY_SCOPE", "VERIFIED_WITHIN_SCOPE", "UNIQUENESS_SCOPE_COMPATIBLE",
            "The nullifier's exact source expression and compiled constraint both include the entity that scopes consumer replay state.",
            facts=facts,
            limitations=["This establishes one-use compatibility only for the recovered two-level mapping update."],
        )
    if not source_includes_scope and not connected:
        return _finding(
            "MULTIPLICITY_SCOPE", "VIOLATION", "UNIQUENESS_SCOPE_MISMATCH",
            "Consumer replay state is partitioned by an entity that does not influence the circuit nullifier, permitting the same proof identity in another entity scope.",
            facts=facts,
        )
    return _finding(
        "MULTIPLICITY_SCOPE", "UNKNOWN", "UNIQUENESS_DEPENDENCE_UNRESOLVED",
        "Source and compiled dependency evidence disagree or require transitive algebraic reasoning beyond the supported template.",
        facts=facts,
    )


def _analyze_role(circuit: Circuit, relation: CompiledRelation, consumer: ConsumerPath) -> dict[str, Any]:
    public_names = [normalized_public_name(name) for name in circuit.public_order]
    consumer_names = vector_names(consumer.vector)
    if not public_names or len(public_names) != len(consumer_names):
        return _finding(
            "ROLE_IDENTITY", "UNKNOWN", "PUBLIC_INPUT_CORRESPONDENCE_UNRESOLVED",
            "Exact compiled producer and consumer vector widths are required for positional role comparison.",
        )
    facts: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    compared = 0
    source = _source(circuit)
    for index, (producer_name, consumer_name) in enumerate(zip(public_names, consumer_names)):
        if consumer_name is None or "[" in producer_name:
            continue
        producer_role, consumer_role = role(producer_name), role(consumer_name)
        if "unknown" in {producer_role, consumer_role}:
            continue
        producer_enforced = relation.participates(producer_name) and source_enforces_identity(source, producer_name)
        consumer_relied = relied_identifier(consumer, consumer_name)
        fact = {
            "provenance": "EXTRACTED",
            "public_index": index,
            "producer_signal": producer_name,
            "producer_role_annotation": producer_role,
            "consumer_expression": consumer.vector.items[index],
            "consumer_role_annotation": consumer_role,
            "compiled_producer_participation": relation.participates(producer_name),
            "source_identity_constraint": source_enforces_identity(source, producer_name),
            "consumer_guard_effect_or_state_reliance": consumer_relied,
            "confidence": "HEURISTIC_ROLE_ANNOTATION",
        }
        facts.append(fact)
        if not producer_enforced or not consumer_relied:
            continue
        compared += 1
        if producer_role != consumer_role:
            mismatches.append(fact)
    limitations = [
        "Role labels are bounded source-name annotations, not compiler-semantic identities or protocol policy.",
        "This stretch dimension is a screening heuristic and cannot carry an end-to-end authorization claim.",
    ]
    if mismatches:
        return _finding(
            "ROLE_IDENTITY", "VIOLATION", "ROLE_IDENTITY_MISMATCH",
            "A compiled, source-constrained public position is used under a different annotated role on a consumer guard/effect path.",
            facts=facts, limitations=limitations,
        )
    if compared:
        return _finding(
            "ROLE_IDENTITY", "VERIFIED_WITHIN_SCOPE", "ROLE_IDENTITY_COMPATIBLE",
            "All comparable compiled positions retain the same bounded role annotation at relied-on consumer uses.",
            facts=facts, limitations=limitations,
        )
    return _finding(
        "ROLE_IDENTITY", "UNKNOWN", "ROLE_IDENTITY_EVIDENCE_INSUFFICIENT",
        "No position had both a compiled/source identity constraint and a relied-on recognized consumer role.",
        facts=facts, limitations=limitations,
    )


ANALYZERS: dict[str, Callable[[Circuit, CompiledRelation, ConsumerPath], dict[str, Any]]] = {
    "EXTENT": _analyze_extent,
    "MASK": _analyze_mask,
    "REPRESENTATION": _analyze_representation,
    "MULTIPLICITY_SCOPE": _analyze_scope,
    "ROLE_IDENTITY": _analyze_role,
}


def _files(root: pathlib.Path, suffix: str) -> list[pathlib.Path]:
    output: list[pathlib.Path] = []
    for path in root.rglob(f"*{suffix}"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_file():
            output.append(path)
    return sorted(output)


def _pair_score(circuit: Circuit, consumer: ConsumerPath) -> tuple[int, dict[str, Any]]:
    vector_count = consumer.vector.declared_count or (len(consumer.vector.items) if consumer.vector.items else None)
    count_match = circuit.public_count is not None and vector_count == circuit.public_count
    circuit_names = {
        canonical_identifier(normalized_public_name(name))
        for name in circuit.public_order
    } - {None}
    consumer_names = set(vector_names(consumer.vector)) - {None}
    overlap = len(circuit_names & consumer_names)
    score = (20 if count_match else 0) + overlap
    return score, {"count_match": count_match, "name_overlap": overlap, "score": score}


def _pairs(circuits: list[Circuit], consumers: list[ConsumerPath]) -> tuple[list[tuple[Circuit, ConsumerPath, dict[str, Any]]], list[dict[str, Any]]]:
    output: list[tuple[Circuit, ConsumerPath, dict[str, Any]]] = []
    unresolved: list[dict[str, Any]] = []
    for consumer in consumers:
        ranked = sorted(
            ((*_pair_score(circuit, consumer), circuit) for circuit in circuits),
            key=lambda item: (-item[0], item[2].relative_path),
        )
        if not ranked or ranked[0][0] <= 0:
            unresolved.append({"consumer": consumer.relative_path, "function": consumer.function.name, "reason": "NO_COMPATIBLE_CIRCUIT"})
            continue
        if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
            unresolved.append({
                "consumer": consumer.relative_path,
                "function": consumer.function.name,
                "reason": "AMBIGUOUS_CIRCUIT_CORRESPONDENCE",
                "candidates": [ranked[0][2].relative_path, ranked[1][2].relative_path],
            })
            continue
        score, evidence, circuit = ranked[0]
        output.append((circuit, consumer, evidence))
    return output, unresolved


def analyze_relational(
    root: pathlib.Path,
    *,
    dimensions: set[str] | None = None,
    explicit_circuits: list[str] | None = None,
    explicit_consumers: list[str] | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    started = time.monotonic()
    started_utc = dt.datetime.now(dt.UTC).isoformat()
    root = root.resolve()
    selected = tuple(dimension for dimension in DIMENSIONS if not dimensions or dimension in dimensions)
    budget = Budget(timeout_seconds)
    build_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    pair_outputs: list[dict[str, Any]] = []
    unresolved_pairs: list[dict[str, Any]] = []
    circuits: list[Circuit] = []
    fatal: str | None = None
    try:
        if not root.is_dir():
            raise ValueError(f"relational analysis root is not a directory: {root}")
        circuit_paths = (
            [(root / value).resolve() for value in explicit_circuits]
            if explicit_circuits else [path for path in _files(root, ".circom") if is_entry_circuit(path)]
        )
        consumer_files = (
            [(root / value).resolve() for value in explicit_consumers]
            if explicit_consumers else _files(root, ".sol")
        )
        circuits = discover(root, circuit_paths)
        for circuit in circuits[:8]:
            budget.check()
            attach_or_build(circuit, root, budget, min(45.0, budget.remaining))
            build_records.append({"path": circuit.relative_path, "record": circuit.build})
        compiled_circuits = [
            circuit for circuit in circuits
            if circuit.compiled and circuit.r1cs is not None and circuit.sym is not None
        ]
        consumers = consumer_paths(root, consumer_files)
        pairs, unresolved_pairs = _pairs(compiled_circuits, consumers)
        relations = {
            circuit.relative_path: CompiledRelation.load(circuit.r1cs, circuit.sym)
            for circuit in compiled_circuits
            if circuit.r1cs is not None and circuit.sym is not None
        }
        for circuit, consumer, correspondence in pairs[:64]:
            budget.check()
            relation = relations[circuit.relative_path]
            findings = {
                dimension: ANALYZERS[dimension](circuit, relation, consumer)
                for dimension in selected
            }
            pair_outputs.append({
                "circuit": {
                    "path": circuit.relative_path,
                    "sha256": circuit.sha256,
                    "r1cs_sha256": sha256_file(circuit.r1cs),
                    "sym_sha256": sha256_file(circuit.sym),
                    "r1cs": relation.metadata,
                    "public_order": circuit.public_order,
                },
                "consumer": {
                    "path": consumer.relative_path,
                    "sha256": sha256_file(consumer.path),
                    "function": consumer.function.name,
                    "line": consumer.function.line,
                    "public_vector": consumer.vector.items,
                },
                "correspondence": correspondence,
                "dimensions": findings,
                "aggregate": aggregate(list(findings.values())),
            })
    except TimeoutError as exc:
        fatal = "RUN_TIMEOUT"
        failures.append({"reason": fatal, "detail": str(exc)})
    except Exception as exc:
        fatal = "RELATIONAL_ANALYSIS_FAILED"
        failures.append({"reason": fatal, "type": type(exc).__name__, "detail": str(exc)})
    finally:
        for circuit in circuits:
            if circuit.temporary_artifacts is not None:
                shutil.rmtree(circuit.temporary_artifacts, ignore_errors=True)

    summaries: dict[str, Any] = {}
    for dimension in selected:
        findings = [pair["dimensions"][dimension] for pair in pair_outputs]
        if not findings:
            reason = fatal or (
                "COMPILED_RELATION_UNAVAILABLE" if circuits else "NO_RELATIONAL_PAIR_RECOVERED"
            )
            findings = [_finding(
                dimension, "UNKNOWN", reason,
                "No supported compiled Circom/consumer pair was available for this dimension.",
                applicability="UNKNOWN",
            )]
        summary = aggregate(findings)
        summaries[dimension] = {
            **summary,
            "results": len(findings),
            "reasons": sorted({finding["reason"] for finding in findings}),
            "applicable_results": sum(finding["applicability"] == "APPLICABLE" for finding in findings),
            "decided_results": sum(
                finding["applicability"] == "APPLICABLE" and finding["verdict"] != "UNKNOWN"
                for finding in findings
            ),
            "violation_results": sum(finding["verdict"] == "VIOLATION" for finding in findings),
        }
    return {
        "schema": "bindcheck-zk.relational-result/v1",
        "property": "consumer reliance must imply producer enforcement under compatible conditions",
        "run": {
            "started_utc": started_utc,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "budget_seconds": timeout_seconds,
            "status": "UNKNOWN" if fatal else "completed",
            "fatal_reason": fatal,
        },
        "inputs": {
            "root": str(root),
            "enabled_dimensions": list(selected),
            "explicit_circuits": explicit_circuits or [],
            "explicit_consumers": explicit_consumers or [],
            "network_policy": "offline/no RPC",
        },
        "dimensions": summaries,
        "pairs": pair_outputs,
        "coverage": {
            "circom_entry_sources": len(circuits),
            "compiled_relations": sum(circuit.compiled for circuit in circuits),
            "consumer_paths": len({(pair["consumer"]["path"], pair["consumer"]["function"]) for pair in pair_outputs}),
            "paired_paths": len(pair_outputs),
            "builds": build_records,
            "unresolved_pairs": unresolved_pairs,
            "failures": failures,
        },
        "limitations": [
            "Results cover bounded exact source templates confirmed against R1CS/sym, not arbitrary Circom or Solidity semantics.",
            "R1CS connectivity is never treated by itself as algebraic equivalence or binding.",
            "Unsupported extraction, compilation, correspondence, or condition implication remains UNKNOWN.",
            "ROLE_IDENTITY is an isolated heuristic screen; its surface annotations are not protocol policy or an end-to-end authorization proof.",
            "All findings are E1 static/compiler-backed evidence unless separately validated at a higher evidence grade.",
        ],
    }
