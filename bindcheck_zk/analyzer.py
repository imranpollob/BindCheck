from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from typing import Any

from . import __version__
from .circuits import Circuit, attach_or_build, discover as discover_circuits, is_entry_circuit, named_path, parse_r1cs
from .freeze import freeze_manifest
from .models import Budget, aggregate, location, result, sha256_file
from .p4 import SCALAR_FIELD, analyze_runtime, analyze_source, canonical_guard, fail_closed_verifier, runtime_values_from_bundle
from .solidity import (
    Call,
    Function,
    PublicVector,
    assignments,
    balanced,
    calls,
    effect_calls,
    effect_roles,
    functions,
    has_unsupported_construct,
    identifiers,
    mask_comments_and_strings,
    normalize_expression,
    public_vector,
    split_top_level,
    unresolved_function_context,
    verification_calls,
    verifier_declarations,
)
from .subprocesses import run


PATTERNS = ("P1", "P2", "P3", "P4", "P5")


@dataclasses.dataclass
class Source:
    path: pathlib.Path
    relative_path: str
    text: str
    sha256: str


@dataclasses.dataclass
class Verifier:
    source: Source
    declarations: list[dict[str, Any]]
    interface_only: bool
    family: str
    p4: dict[str, Any]
    contract_names: set[str]

    @property
    def arities(self) -> set[int]:
        return {item["arity"] for item in self.declarations if item.get("arity") is not None}


@dataclasses.dataclass
class Consumer:
    source: Source
    function: Function
    verify_calls: list[Any]
    effect_calls: list[Any]
    vectors: list[PublicVector]
    receiver_types: dict[str, str]
    repository_contracts: dict[str, tuple[str, pathlib.Path]]


def load_config() -> dict[str, Any]:
    path = pathlib.Path(__file__).with_name("config.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _git_revision(root: pathlib.Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, timeout=2, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _safe_explicit(root: pathlib.Path, raw: str) -> pathlib.Path:
    path = pathlib.Path(raw)
    path = path if path.is_absolute() else root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"explicit path escapes repository root: {raw}") from exc
    if not resolved.is_file():
        raise ValueError(f"explicit path is not a file: {raw}")
    return resolved


def inventory(
    root: pathlib.Path, config: dict[str, Any], budget: Budget
) -> tuple[list[pathlib.Path], list[dict[str, Any]], list[dict[str, Any]]]:
    excluded = set(config["excluded_directories"])
    candidates: list[pathlib.Path] = []
    skipped: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    manifest_names = {
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "foundry.toml", "hardhat.config.js", "hardhat.config.ts", "nargo.toml",
        "makefile", "justfile", "cargo.toml",
    }
    for directory, dirnames, filenames in os.walk(root):
        budget.check()
        base = pathlib.Path(directory)
        kept: list[str] = []
        for name in sorted(dirnames):
            child = base / name
            if name in excluded:
                excluded_records.append({
                    "path": child.relative_to(root).as_posix(),
                    "reason": "EXCLUDED_DIRECTORY",
                    "category": name,
                })
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            candidates.append(base / name)

    def priority(path: pathlib.Path) -> tuple[int, str]:
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix in {".circom", ".nr"}:
            rank = 0
        elif path.name.lower() in manifest_names or suffix in {".lock", ".toml"}:
            rank = 1
        elif suffix == ".sol":
            rank = 2
        elif suffix in {".sh", ".js", ".ts", ".mjs", ".cjs"}:
            rank = 3
        else:
            rank = 4
        return rank, relative

    output: list[pathlib.Path] = []
    for path in sorted(candidates, key=priority):
        budget.check()
        relative = path.relative_to(root)
        try:
            size = path.stat().st_size
        except OSError as exc:
            skipped.append({"path": relative.as_posix(), "reason": "STAT_FAILED", "detail": str(exc)})
            continue
        if size > int(config["max_file_bytes"]):
            skipped.append({"path": relative.as_posix(), "reason": "FILE_TOO_LARGE", "bytes": size})
            continue
        if len(output) >= int(config["max_files"]):
            skipped.append({"path": relative.as_posix(), "reason": "MAX_FILES_EXCEEDED"})
            continue
        output.append(path)
    return output, skipped, excluded_records


def read_sources(root: pathlib.Path, files: list[pathlib.Path], coverage: dict[str, Any]) -> list[Source]:
    output: list[Source] = []
    for path in files:
        if path.suffix.lower() != ".sol":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            coverage["skipped"].append({"path": path.relative_to(root).as_posix(), "reason": "READ_FAILED", "detail": str(exc)})
            continue
        output.append(Source(path, path.relative_to(root).as_posix(), text, sha256_file(path)))
    return output


def _semantic_excluded(relative_path: str, config: dict[str, Any]) -> bool:
    path = pathlib.PurePosixPath(relative_path)
    parts = {part.lower() for part in path.parts}
    excluded = set(config.get("semantic_test_directories", [])) | set(config.get("semantic_script_directories", []))
    return bool(parts & excluded) or path.name.lower().endswith((".t.sol", ".s.sol"))


def classify_verifier(source: Source) -> Verifier | None:
    declarations = verifier_declarations(source.text)
    contract_names = set(re.findall(
        r"\b(?:contract|library|interface)\s+([A-Za-z_]\w*)",
        mask_comments_and_strings(source.text),
    ))
    named = any(re.search(r"(?:verifier|groth16|plonk|honk|ultra|snark)", name, re.I) for name in contract_names)
    strong = any(item["name"].lower() != "verify" and item["name"] != "constant" for item in declarations)
    generic_array = any(item["name"].lower() == "verify" and item.get("public_input_like") for item in declarations)
    if not declarations or not named or not (strong or generic_array):
        return None
    interface_only = bool(re.search(r"\binterface\s+[A-Za-z_]\w*", source.text)) and not bool(
        re.search(r"\bfunction\s+(?:verifyProof|verifyTx|verify)\b[^{;]*\{", source.text, re.S | re.I)
    )
    lower = source.text.lower()
    if "honk" in lower or "ultra" in lower:
        family = "Honk"
    elif "plonk" in lower:
        family = "PLONK"
    elif "pairing" in lower or "groth16" in lower:
        family = "Groth16"
    else:
        family = "unknown"
    p4 = analyze_source(source.text, source.relative_path)
    if family not in {"Groth16", "PLONK"}:
        p4["finding"] = result(
            "P4",
            "UNKNOWN",
            "UNSUPPORTED_VERIFIER_KEY_LAYOUT",
            f"{family} verifier-key layout is outside the supported Groth16/PLONK source-key subset.",
            where=location(source.relative_path, 1),
            limitations=["No Groth16 gamma/delta or canonical-input-guard conclusion is drawn for this verifier family."],
        )
    return Verifier(source, declarations, interface_only, family, p4, contract_names)


def _receiver_types(text: str) -> dict[str, str]:
    output: dict[str, str] = {}
    masked = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.S)
    for type_name, variable in re.findall(
        r"\b([A-Za-z_]\w*)\s+(?:(?:public|private|internal|external|immutable|constant)\s+)*([A-Za-z_]\w*)\s*(?:[;=,])",
        masked,
    ):
        output[variable] = type_name
    return output


def _supported_verification_call(call: Call) -> bool:
    if call.name.lower() != "verify":
        return True
    return bool(call.receiver and re.search(r"(?:verifier|groth|plonk|honk|snark|zkp|circuit)", call.receiver, re.I))


def discover_consumers(sources: list[Source]) -> list[Consumer]:
    output: list[Consumer] = []
    declarations = [
        (name, source.text, source.path)
        for source in sources
        for name in re.findall(r"\b(?:abstract\s+)?contract\s+([A-Za-z_]\w*)\b", mask_comments_and_strings(source.text))
    ]
    declaration_counts: dict[str, int] = defaultdict(int)
    for name, _, _ in declarations:
        declaration_counts[name] += 1
    repository_contracts = {
        name: (source_text, path) for name, source_text, path in declarations
        if declaration_counts[name] == 1
    }
    for source in sources:
        parsed_functions = list(functions(source.text))
        local_function_names = {item.name for item in parsed_functions}
        helper_vector_parameters: dict[str, list[int]] = defaultdict(list)
        for helper in parsed_functions:
            parameter_names = list(helper.parameters)
            for direct_call in filter(_supported_verification_call, verification_calls(helper.body)):
                vector = public_vector(helper.body, direct_call)
                if vector.base in helper.parameters:
                    helper_vector_parameters[helper.name].append(parameter_names.index(vector.base))
                    continue
                if vector.base:
                    copy_pattern = re.compile(
                        rf"\b{re.escape(vector.base)}\s*\[\s*([^\]]+)\s*\]\s*(?<![=!<>])=(?!=)\s*"
                        r"([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]"
                    )
                    for destination_index, source_name, source_index in copy_pattern.findall(helper.body):
                        if source_name in helper.parameters and normalize_expression(destination_index) == normalize_expression(source_index):
                            helper_vector_parameters[helper.name].append(parameter_names.index(source_name))
        for function in parsed_functions:
            verify = [
                call for call in verification_calls(function.body)
                if _supported_verification_call(call)
                and not (call.receiver is None and call.name in local_function_names)
            ]
            if not verify:
                for helper_name, vector_indices in helper_vector_parameters.items():
                    helper_calls = calls(
                        function.body,
                        re.compile(rf"\b{re.escape(helper_name)}\s*\("),
                    )
                    for helper_call in helper_calls:
                        for vector_index in vector_indices:
                            if vector_index >= len(helper_call.args):
                                continue
                            verify.append(Call(
                                name=helper_name,
                                receiver=helper_call.receiver,
                                args=[helper_call.args[vector_index]],
                                line=helper_call.line,
                                offset=helper_call.offset,
                            ))
            if not verify:
                continue
            effects = effect_calls(function.body, source.text)
            vectors = [public_vector(function.body, call) for call in verify]
            for vector in vectors:
                if vector.base and vector.base in function.parameters:
                    parameter_type = function.parameters[vector.base]
                    fixed = re.search(r"(?:uint(?:256)?|bytes32)\s*\[\s*(\d+)\s*\]", parameter_type)
                    dynamic = re.search(r"(?:uint(?:256)?|bytes32)\s*\[\s*\]", parameter_type)
                    if fixed and vector.declared_count is None:
                        vector.declared_count = int(fixed.group(1))
                    if dynamic:
                        vector.dynamic = True
                        if not vector.items:
                            vector.unresolved.append("parameter-vector-elements")
            output.append(Consumer(source, function, verify, effects, vectors, _receiver_types(source.text), repository_contracts))
    return output


def _tokens(path: str) -> set[str]:
    expanded = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", path)
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", expanded)
    ignored = {
        "main", "circuit", "circuits", "contract", "contracts", "verifier", "verifiers",
        "consumer", "src", "source", "sources", "package", "packages", "sol", "circom", "nr", "js",
    }
    return {
        token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9]*", expanded)
        if token.lower() not in ignored and len(token) > 1
    }


def _match_score(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer) -> tuple[float, list[str]]:
    score = 0.2
    reasons = ["consumer contains verifier call and protected effect"]
    consumer_tokens = _tokens(consumer.source.relative_path) | {consumer.function.name.lower()}
    if verifier:
        receiver_names = {call.receiver for call in consumer.verify_calls if call.receiver}
        receiver_types = {consumer.receiver_types.get(name, "") for name in receiver_names}
        verifier_names = {name.lower() for name in verifier.contract_names}
        if any(value.lower() in verifier_names for value in receiver_types if value):
            score += 0.45
            reasons.append("verifier contract matches the declared receiver type")
        elif any(
            receiver.lower() in name.lower() or name.lower() in receiver.lower()
            for receiver in receiver_names for name in verifier.contract_names
            if receiver.lower() not in {"verifier", "zkverifier"}
        ):
            score += 0.3
            reasons.append("verifier contract matches the call receiver name")
        overlap = consumer_tokens & _tokens(verifier.source.relative_path)
        if overlap:
            score += min(0.2, 0.05 * len(overlap))
            reasons.append("consumer/verifier name tokens overlap")
        if verifier.source.path.parent == consumer.source.path.parent:
            score += 0.1
            reasons.append("consumer and verifier share a source directory")
        path_tokens = {part.lower() for part in pathlib.PurePosixPath(verifier.source.relative_path).parts}
        if path_tokens & {"test", "tests", "mock", "mocks"} or "mock" in verifier.source.path.stem.lower():
            score -= 0.3
            reasons.append("test/mock verifier candidate is de-prioritized")
    if circuit:
        overlap = consumer_tokens & _tokens(circuit.relative_path)
        if overlap:
            score += min(0.2, 0.05 * len(overlap))
            reasons.append("consumer/circuit name tokens overlap")
        if consumer.function.name.lower() in pathlib.Path(circuit.relative_path).stem.lower():
            score += 0.25
            reasons.append("consumer function name matches the circuit entry name")
        vector_counts = {item.declared_count or item.length_guard for item in consumer.vectors}
        if circuit.public_count and circuit.public_count in vector_counts:
            score += 0.2
            reasons.append("circuit public count matches recovered consumer vector")
        if verifier and circuit.public_count and circuit.public_count in verifier.arities:
            score += 0.15
            reasons.append("circuit public count matches verifier arity")
        if verifier:
            verifier_tokens = _tokens(verifier.source.relative_path)
            for name in verifier.contract_names:
                verifier_tokens |= _tokens(name)
            overlap = verifier_tokens & _tokens(circuit.relative_path)
            if overlap:
                score += min(0.35, 0.15 + 0.05 * len(overlap))
                reasons.append("circuit/verifier name tokens overlap")
    if circuit is None:
        reasons.append("circuit artifact missing")
    if verifier is None:
        reasons.append("verifier implementation artifact missing")
    # Keep the raw score for ranking and ambiguity pruning.  Capping here
    # collapses materially different candidates (for example, 1.25 and 0.90)
    # into the same apparent near-perfect score and retains wrong circuits.
    return max(0.0, score), reasons


def make_triples(
    circuits: list[Circuit], verifiers: list[Verifier], consumers: list[Consumer], max_triples: int
) -> list[dict[str, Any]]:
    triples: list[dict[str, Any]] = []
    for consumer in consumers:
        verifier_options: list[Verifier | None] = verifiers or [None]
        circuit_options: list[Circuit | None] = circuits or [None]
        candidates: list[tuple[float, list[str], Circuit | None, Verifier | None]] = []
        for verifier in verifier_options:
            for circuit in circuit_options:
                score, reasons = _match_score(circuit, verifier, consumer)
                candidates.append((score, reasons, circuit, verifier))
        candidates.sort(key=lambda item: (-item[0], item[2].relative_path if item[2] else "", item[3].source.relative_path if item[3] else ""))
        best = candidates[0][0] if candidates else 0.0
        for score, reasons, circuit, verifier in candidates:
            if score + 0.19 < best:
                continue
            triples.append({
                "id": f"T{len(triples) + 1:03d}",
                "circuit_obj": circuit,
                "verifier_obj": verifier,
                "consumer_obj": consumer,
                "match": {
                    "score": round(min(score, 0.99), 3),
                    "confidence": "high" if score >= 0.75 else "medium" if score >= 0.5 else "low",
                    "reasons": reasons,
                },
            })
            if len(triples) >= max_triples:
                return triples
    return triples


def _resolve_alias(expression: str, aliases: dict[str, str], depth: int = 4) -> str:
    value = expression.strip()
    for _ in range(depth):
        normalized = normalize_expression(value)
        if normalized in aliases:
            value = aliases[normalized]
            continue
        changed = False
        for name, replacement in aliases.items():
            if re.fullmatch(r"[A-Za-z_]\w*", name) and re.search(rf"\b{re.escape(name)}\b", value):
                value = re.sub(rf"\b{re.escape(name)}\b", f"({replacement})", value)
                changed = True
        if not changed:
            break
    return value


def _direct_bound(expression: str, vector: PublicVector, aliases: dict[str, str]) -> bool:
    resolved = normalize_expression(_resolve_alias(expression, aliases))
    if resolved in vector.normalized_items:
        return True
    for item in vector.items:
        if normalize_expression(_resolve_alias(item, aliases)) == resolved:
            return True
    if vector.base and (resolved == vector.base or resolved.startswith(vector.base + "[")):
        return True
    return False


def _brace_intervals(masked: str) -> list[tuple[int, int]]:
    stack: list[int] = []
    output: list[tuple[int, int]] = []
    for index, character in enumerate(masked):
        if character == "{":
            stack.append(index)
        elif character == "}" and stack:
            output.append((stack.pop(), index + 1))
    return output


def _guard_scope_dominates(
    guard_offset: int,
    effect_offset: int,
    intervals: list[tuple[int, int]],
) -> bool:
    containing = [interval for interval in intervals if interval[0] < guard_offset < interval[1]]
    if not containing:
        return guard_offset < effect_offset
    innermost = max(containing, key=lambda interval: interval[0])
    return guard_offset < effect_offset < innermost[1]


def _binding_equality(
    predicate: str,
    resolved: str,
    vector: PublicVector,
    aliases: dict[str, str],
    *,
    equality_required: bool,
) -> bool:
    operator = "==" if equality_required else "!="
    if operator not in predicate:
        return False
    left, right = predicate.split(operator, 1)
    left_norm = normalize_expression(_resolve_alias(left.strip(), aliases))
    right_norm = normalize_expression(_resolve_alias(right.strip(), aliases))
    vector_refs = {
        normalize_expression(_resolve_alias(value, aliases))
        for value in (vector.base, vector.expression, *vector.items)
        if value
    }

    def is_vector_member(value: str) -> bool:
        return any(value == ref or value.startswith(ref + "[") for ref in vector_refs)

    return (left_norm == resolved and is_vector_member(right_norm)) or (
        right_norm == resolved and is_vector_member(left_norm)
    )


def _guard_bound(
    expression: str,
    vector: PublicVector,
    aliases: dict[str, str],
    body: str,
    effect_offset: int,
) -> bool:
    """Recognize equality enforced before/on every path reaching one effect."""
    resolved = normalize_expression(_resolve_alias(expression, aliases))
    masked = mask_comments_and_strings(body)
    intervals = _brace_intervals(masked)
    for match in re.finditer(r"\b(?:require|assert)\s*\(", masked):
        opening = masked.find("(", match.start())
        condition = balanced(body, opening)
        if condition is None or condition[1] > effect_offset:
            continue
        arguments = split_top_level(condition[0])
        predicate = arguments[0] if arguments else ""
        if not _binding_equality(predicate, resolved, vector, aliases, equality_required=True):
            continue
        if _guard_scope_dominates(match.start(), effect_offset, intervals):
            return True
    for match in re.finditer(r"\bif\s*\(", masked):
        opening = masked.find("(", match.start())
        condition = balanced(body, opening)
        if condition is None:
            continue
        cursor = condition[1]
        while cursor < len(masked) and masked[cursor].isspace():
            cursor += 1
        if _binding_equality(condition[0], resolved, vector, aliases, equality_required=True):
            if cursor < len(masked) and masked[cursor] == "{":
                branch = next((interval for interval in intervals if interval[0] == cursor), None)
                if branch and branch[0] < effect_offset < branch[1]:
                    return True
            else:
                statement_end = masked.find(";", cursor)
                if cursor <= effect_offset <= statement_end:
                    return True
        if condition[1] > effect_offset or not _guard_scope_dominates(match.start(), effect_offset, intervals):
            continue
        if not _binding_equality(condition[0], resolved, vector, aliases, equality_required=False):
            continue
        if cursor < len(masked) and masked[cursor] == "{":
            branch = next((interval for interval in intervals if interval[0] == cursor), None)
            branch_text = masked[branch[0]:branch[1]] if branch else ""
        else:
            statement_end = masked.find(";", cursor)
            branch_text = masked[cursor:statement_end + 1]
        if re.search(r"\b(?:revert|return\s+false)\b", branch_text):
            return True
    return False


def _hash_preimage_order(body: str) -> list[str] | None:
    masked = mask_comments_and_strings(body)
    for match in re.finditer(r"\b(?:poseidon(?:\.[A-Za-z_]\w*)?|compute[A-Za-z_]*hash|keccak256)\s*\(", masked, re.I):
        opening = masked.find("(", match.start())
        parsed = balanced(body, opening)
        if parsed is None:
            continue
        arguments = split_top_level(parsed[0])
        if len(arguments) == 1:
            nested = re.search(r"\babi\s*\.\s*encode(?:Packed)?\s*\(", arguments[0], re.I)
            if nested:
                nested_open = arguments[0].find("(", nested.start())
                nested_parsed = balanced(arguments[0], nested_open)
                if nested_parsed:
                    arguments = split_top_level(nested_parsed[0])
        if arguments:
            return [normalize_expression(argument) for argument in arguments]
    return None


def _commitment_binding(
    expression: str,
    vector: PublicVector,
    circuit: Circuit,
    consumer: Consumer,
    effect_offset: int,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    expression_names = identifiers(expression)
    for component in circuit.components:
        commitment = component["commitment"]
        input_names = set().union(*(identifiers(item) for item in component["inputs"]))
        if not expression_names & input_names:
            continue
        public_has_commitment = any(commitment in identifiers(item) for item in vector.items) or commitment in vector.sources
        if not public_has_commitment:
            continue
        consumer_assignments = assignments(consumer.function.body)
        computed_name = next(
            (
                name for name, value in consumer_assignments.items()
                if re.search(r"\b(?:poseidon|compute[A-Za-z_]*hash|keccak256)\b", value, re.I)
            ),
            commitment,
        )
        guard = _guard_bound(
            computed_name,
            vector,
            {normalize_expression(name): value for name, value in consumer_assignments.items()},
            consumer.function.body,
            effect_offset,
        )
        preimage_order = _hash_preimage_order(consumer.function.body)
        if not (guard and preimage_order):
            return False, None, "LOCAL_COMMITMENT_GUARD_UNESTABLISHED"
        circuit_order = [normalize_expression(value) for value in component["inputs"]]
        if preimage_order != circuit_order:
            return False, {
                "component": component,
                "circuit_preimage_order": circuit_order,
                "consumer_preimage_order": preimage_order,
                "status": "SCREEN_ONLY",
            }, "COMMITMENT_PREIMAGE_ORDER_UNRESOLVED"
        if not circuit.compiled or circuit.r1cs is None or circuit.sym is None:
            return False, None, "COMPILED_RELATION_UNAVAILABLE"
        signal = next((name for name in input_names if name in expression_names), None)
        if signal is None:
            continue
        try:
            path = named_path(circuit.r1cs, circuit.sym, signal, commitment, component["name"])
        except (OSError, ValueError) as exc:
            return False, {"error": str(exc)}, "COMPILED_RELATION_PARSE_FAILED"
        if path and path["namespace_ok"]:
            return False, {
                "component": component,
                "compiled_path": path,
                "consumer_guard": True,
                "algorithm_evidence": "hash invocation and ordered arguments recovered in consumer function",
                "order_evidence": circuit_order,
                "circuit_source_sha256": circuit.sha256,
                "r1cs_sha256": sha256_file(circuit.r1cs),
                "status": "SCREEN_ONLY",
                "does_not_establish": "algebraic or cryptographic commitment binding",
            }, "COMMITMENT_BINDING_SCREEN_ONLY"
        return False, {
            "component": component,
            "compiled_path": path,
            "status": "SCREEN_ONLY",
        }, "COMMITMENT_BINDING_SCREEN_ONLY"
    return False, None, None


def analyze_p1(
    circuit: Circuit | None,
    verifier: Verifier | None,
    consumer: Consumer,
    policy: dict[str, bool] | None = None,
) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    unsupported = has_unsupported_construct(consumer.function.body)
    if unsupported:
        return result("P1", "UNKNOWN", unsupported, "Consumer function uses a construct outside the supported dataflow subset.", where=where)
    if not consumer.effect_calls:
        return result(
            "P1", "UNKNOWN", "PROTECTED_EFFECT_NOT_RECOVERED",
            "No supported protected effect is committed on the recovered verifier-accepting function path.",
            where=where, applicability="NOT_APPLICABLE",
        )
    unresolved_context = unresolved_function_context(consumer.function, consumer.source.text, consumer.repository_contracts, consumer.source.path)
    if unresolved_context:
        return result(
            "P1", "UNKNOWN", unresolved_context,
            "The effect-bearing consumer path depends on modifier or inherited semantics outside the supported frontend.",
            where=where,
        )
    if verifier is None or verifier.interface_only:
        return result("P1", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "Consumer is analyzed, but the verifier implementation artifact is absent.", where=where)
    if fail_closed_verifier(verifier.source.text):
        return result("P1", "UNKNOWN", "FAIL_CLOSED_VERIFIER_PLACEHOLDER", "A verifier that unconditionally rejects proofs cannot establish a non-vacuous protected-effect binding.", where=where)
    if circuit is None:
        return result("P1", "UNKNOWN", "CIRCUIT_ARTIFACT_MISSING", "Consumer/verifier artifacts are present but no circuit artifact was matched.", where=where)
    aliases = {normalize_expression(name): value for name, value in assignments(consumer.function.body).items()}
    role_facts: list[dict[str, Any]] = []
    violations: list[str] = []
    unknown_reasons: list[str] = []
    verify_argument_names = set().union(*(
        identifiers(_resolve_alias(argument, aliases))
        for call in consumer.verify_calls for argument in call.args
    )) if consumer.verify_calls else set()
    vector_sources = set().union(*(vector.sources for vector in consumer.vectors)) if consumer.vectors else set()
    for call in consumer.effect_calls:
        roles = effect_roles(call, consumer.source.text)
        resolved_recipients = [
            normalize_expression(_resolve_alias(value, aliases))
            for name, value in roles if name == "recipient"
        ]
        for role, expression in roles:
            fact: dict[str, Any] = {"provenance": "EXTRACTED", "role": role, "expression": expression, "bound_by": []}
            resolved_expression = normalize_expression(_resolve_alias(expression, aliases))
            if (
                role == "recipient"
                and resolved_expression == "msg.sender"
                and (policy or {}).get("any_caller_may_receive", False)
            ):
                fact["bound_by"].append("policy:any-caller-may-receive")
            if role == "recipient" and resolved_expression == "this":
                fact["bound_by"].append("contract-self")
            if any(_direct_bound(expression, vector, aliases) for vector in consumer.vectors):
                fact["bound_by"].append("direct-public-input")
            guard_bound = any(
                _guard_bound(expression, vector, aliases, consumer.function.body, call.offset)
                for vector in consumer.vectors
            )
            if guard_bound:
                fact["bound_by"].append("local-public-vector-guard")
            elif any(
                _guard_bound(expression, vector, aliases, consumer.function.body, len(consumer.function.body) + 1)
                for vector in consumer.vectors
            ):
                reason = "POST_EFFECT_GUARD_SEMANTICS_UNRESOLVED"
                unknown_reasons.append(reason)
                fact.setdefault("unresolved", []).append({"reason": reason})
            if (
                role == "amount"
                and "msg.sender" in resolved_recipients
                and re.search(r"\bmsg\s*\.\s*value\b", _resolve_alias(expression, aliases))
            ):
                fact["bound_by"].append("caller-funded-refund")
            if not fact["bound_by"]:
                for vector in consumer.vectors:
                    bound, evidence, reason = _commitment_binding(
                        expression, vector, circuit, consumer, call.offset
                    )
                    if bound:
                        fact["bound_by"].append("compiled-commitment")
                        fact["commitment_evidence"] = evidence
                        break
                    if reason:
                        unknown_reasons.append(reason)
                        fact.setdefault("unresolved", []).append({"reason": reason, "evidence": evidence})
            if not fact["bound_by"]:
                expression_names = identifiers(_resolve_alias(expression, aliases))
                if fact.get("unresolved"):
                    pass
                elif expression_names & vector_sources:
                    reason = "EFFECT_TRANSFORMATION_UNRESOLVED"
                    unknown_reasons.append(reason)
                    fact.setdefault("unresolved", []).append({"reason": reason})
                elif expression_names & verify_argument_names:
                    reason = "PUBLIC_INPUT_VECTOR_UNRESOLVED"
                    unknown_reasons.append(reason)
                    fact.setdefault("unresolved", []).append({"reason": reason})
                else:
                    caller_controlled = bool(expression_names & set(consumer.function.parameters)) or bool(
                        re.search(r"\b(?:msg\.(?:sender|value)|tx\.origin)\b", _resolve_alias(expression, aliases))
                    )
                    if not caller_controlled:
                        reason = "CALLER_INDEPENDENCE_UNRESOLVED"
                        unknown_reasons.append(reason)
                        fact.setdefault("unresolved", []).append({"reason": reason})
                    elif role == "recipient":
                        violations.append("UNBOUND_EFFECT_RECIPIENT")
                    elif role == "amount":
                        violations.append("UNBOUND_EFFECT_AMOUNT")
                    elif role == "identity":
                        violations.append("UNBOUND_EFFECT_IDENTITY")
            role_facts.append(fact)
    if violations:
        reason = sorted(set(violations))[0]
        return result(
            "P1", "VIOLATION", reason,
            "At least one protected effect role is attacker-selectable independently of the recovered verifier public vector.",
            where=where, facts=role_facts,
            limitations=["E1 static violation; real-proof/effect validation is a separate evidence grade."],
        )
    if any(not fact["bound_by"] for fact in role_facts):
        reason = sorted(set(unknown_reasons))[0] if unknown_reasons else "EFFECT_BINDING_UNRESOLVED"
        return result("P1", "UNKNOWN", reason, "A protected effect role could not be proved bound or unbound in the supported subset.", where=where, facts=role_facts)
    if not role_facts:
        return result("P1", "UNKNOWN", "EFFECT_BINDING_UNRESOLVED", "A protected effect was recovered but its semantic roles were not.", where=where)
    reason = (
        "RECIPIENT_ALLOWED_BY_ANY_CALLER_POLICY"
        if any("policy:any-caller-may-receive" in fact["bound_by"] for fact in role_facts)
        else "EFFECT_VALUES_DIRECT_PUBLIC_INPUTS"
    )
    if any("contract-self" in fact["bound_by"] for fact in role_facts):
        reason = "RECIPIENT_BOUND_TO_CONTRACT_SELF"
    return result(
        "P1", "VERIFIED_WITHIN_SCOPE", reason,
        "Every recovered protected effect role is bound by a direct verifier input, an enforcing local guard, contract self, or an explicit recipient policy.",
        where=where, facts=role_facts,
        limitations=["Result is limited to the recovered function, effects, matched artifacts, and supported dataflow forms."],
    )


def analyze_p2(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    unsupported = has_unsupported_construct(consumer.function.body)
    if unsupported == "UNSUPPORTED_DELEGATECALL_CONTEXT":
        return result("P2", "UNKNOWN", unsupported, "Delegatecall makes address/domain context semantics unsupported.", where=where)
    replay_uses = _mapping_uses(consumer.function.body, consumer.source.text)
    if not consumer.effect_calls and not replay_uses:
        return result(
            "P2", "UNKNOWN", "PROTECTED_EFFECT_NOT_RECOVERED",
            "No protected effect or replay-relevant state mutation was recovered on the verifier-accepting function path.",
            where=where, applicability="NOT_APPLICABLE",
        )
    if verifier is None or verifier.interface_only:
        return result("P2", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "Execution-context binding cannot be decided without a matched verifier implementation.", where=where)
    if circuit is None:
        return result("P2", "UNKNOWN", "CIRCUIT_ARTIFACT_MISSING", "Execution-context binding cannot be decided without a matched circuit artifact.", where=where)
    source_aliases = {
        normalize_expression(name): value
        for name, value in assignments(consumer.source.text).items()
    }
    body_aliases = {
        normalize_expression(name): value
        for name, value in assignments(consumer.function.body).items()
    }
    aliases = {**source_aliases, **body_aliases}
    vector_parts = [
        _resolve_alias(part, aliases)
        for vector in consumer.vectors
        for part in [vector.expression, *vector.items]
    ]
    vector_text = " ".join(vector_parts)
    body = consumer.function.body
    context_pattern = r"block\s*\.\s*chainid|address\s*\(\s*this\s*\)|\b(?:domain(?:Separator)?|DOMAIN_SEPARATOR|eip712Domain|chain_id|chainId|appId|verifyingContract)\b"
    has_context = bool(re.search(context_pattern, vector_text, re.I))
    committed = has_context and bool(re.search(r"\b(?:keccak256|sha256|poseidon|hash)\b", vector_text, re.I))
    direct = has_context and not committed
    context_expressions = re.findall(
        r"block\s*\.\s*chainid|address\s*\(\s*this\s*\)|\b(?:domain|chain_id|chainId|appId)\b",
        body,
        re.I,
    )
    guarded = bool(consumer.effect_calls) and all(
        any(
            _guard_bound(context, vector, aliases, body, effect.offset)
            for context in context_expressions
            for vector in consumer.vectors
        )
        for effect in consumer.effect_calls
    )
    computed = bool(re.search(context_pattern, body, re.I))
    facts = [
        {"provenance": "EXTRACTED", "name": "context_in_public_vector", "value": direct},
        {"provenance": "EXTRACTED", "name": "context_in_public_commitment", "value": committed},
        {"provenance": "EXTRACTED", "name": "context_local_guard", "value": guarded},
        {"provenance": "EXTRACTED", "name": "context_computation_present", "value": computed},
    ]
    if committed:
        return result("P2", "VERIFIED_WITHIN_SCOPE", "CONTEXT_BOUND_IN_PUBLIC_COMMITMENT", "A supported chain or contract context is hashed into a value supplied to the verifier public statement.", where=where, facts=facts)
    if direct:
        return result("P2", "VERIFIED_WITHIN_SCOPE", "CONTEXT_BOUND_IN_PUBLIC_INPUTS", "A supported chain, contract, or explicit domain value is included in the verifier public vector.", where=where, facts=facts)
    if guarded:
        return result("P2", "VERIFIED_WITHIN_SCOPE", "CONTEXT_BOUND_BY_LOCAL_GUARD", "A local guard equates a supported execution context value with the proof-consuming path.", where=where, facts=facts)
    if computed:
        return result("P2", "UNKNOWN", "CONTEXT_COMPUTATION_NOT_GUARDED", "Context is computed but no supported binding to the verifier statement was recovered.", where=where, facts=facts)
    return result(
        "P2", "UNKNOWN", "NO_CONTEXT_BINDING_RECOVERED",
        "No chain ID, contract address, or explicit application domain binding was recovered; policy/deployment uniqueness may still prevent replay.",
        where=where, facts=facts,
    )


def _mapping_uses(body: str, source_text: str) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    declared = set(re.findall(
        r"\bmapping\s*\([^;]+?\)\s*(?:(?:public|private|internal|external)\s+)*([A-Za-z_]\w*)\s*;",
        source_text,
        re.S,
    ))
    for name in declared:
        if not any(word in name.lower() for word in ("nullifier", "spent", "used", "replay", "claimed")):
            continue
        for match in re.finditer(rf"\b{re.escape(name)}\s*\[", body):
            opening = body.find("[", match.start())
            depth = 0
            for index in range(opening, len(body)):
                if body[index] == "[":
                    depth += 1
                elif body[index] == "]":
                    depth -= 1
                    if depth == 0:
                        parts = [body[opening + 1:index].strip()]
                        cursor = index + 1
                        while cursor < len(body):
                            while cursor < len(body) and body[cursor].isspace():
                                cursor += 1
                            if cursor >= len(body) or body[cursor] != "[":
                                break
                            nested_open = cursor
                            nested_depth = 0
                            for nested_end in range(nested_open, len(body)):
                                if body[nested_end] == "[":
                                    nested_depth += 1
                                elif body[nested_end] == "]":
                                    nested_depth -= 1
                                    if nested_depth == 0:
                                        parts.append(body[nested_open + 1:nested_end].strip())
                                        cursor = nested_end + 1
                                        break
                            else:
                                break
                        output.append((name, "][".join(parts)))
                        break
    return output


def _key_passed_to_internal_helper(body: str, key: str) -> bool:
    key_pattern = re.escape(key).replace(r"\ ", r"\s*")
    for match in re.finditer(r"(?<!\.)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*;", body, re.S):
        name, arguments = match.groups()
        if name.lower() in {"require", "assert", "revert", "if", "while", "for", "return"}:
            continue
        if re.search(key_pattern, arguments):
            return True
    return False


def _replay_key_binding_to_verifier(
    consumer: Consumer,
    resolved_key: str,
) -> tuple[bool, set[int] | None]:
    ignored = {"msg", "sender", "block", "timestamp", "chainid", "abi", "encode", "encodepacked", "keccak256", "sha256"}
    key_ids = {name for name in identifiers(resolved_key) if name.lower() not in ignored}
    vector_ids: set[str] = set()
    vector_refs: set[str] = set()
    aliases = assignments(consumer.function.body)
    positions: set[int] = set()
    for vector in consumer.vectors:
        resolved_vector = _resolve_alias(vector.expression, aliases)
        vector_ids |= vector.sources | identifiers(vector.expression) | identifiers(resolved_vector)
        for index, item in enumerate(vector.items):
            resolved_item = _resolve_alias(item, aliases)
            item_ids = {name for name in identifiers(resolved_item) if name.lower() not in ignored}
            if normalize_expression(resolved_item) == normalize_expression(resolved_key) or key_ids & item_ids:
                positions.add(index)
        if vector.base:
            vector_refs.add(vector.base)
        if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", vector.expression.strip()):
            vector_refs.add(vector.expression.strip())
    for call in consumer.verify_calls:
        for argument in call.args:
            vector_ids |= identifiers(_resolve_alias(argument, aliases))
    proof_bound = bool(key_ids & vector_ids)
    key_pattern = re.escape(resolved_key).replace(r"\ ", r"\s*")
    for base in vector_refs:
        base_pattern = re.escape(base).replace(r"\.", r"\s*\.\s*")
        equality = rf"(?:{base_pattern}\s*\[\s*(\d+)\s*\][^;]*(?:==)[^;]*{key_pattern}|{key_pattern}[^;]*(?:==)[^;]*{base_pattern}\s*\[\s*(\d+)\s*\])"
        for match in re.finditer(equality, consumer.function.body, re.S):
            positions.add(int(next(group for group in match.groups() if group is not None)))
            proof_bound = True
        direct = re.fullmatch(rf"{base_pattern}\s*\[\s*(\d+)\s*\]", resolved_key)
        if direct:
            positions.add(int(direct.group(1)))
            proof_bound = True
    return proof_bound, positions or None


def analyze_p3(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    if re.search(r"\b(?:view|pure)\b", consumer.function.header):
        return result(
            "P3", "UNKNOWN", "PROTECTED_EFFECT_NOT_RECOVERED",
            "Replay-key safety is not decided for a read-only verifier utility with no state effect.",
            where=where, applicability="NOT_APPLICABLE",
        )
    uses = _mapping_uses(consumer.function.body, consumer.source.text)
    replay_helper = bool(re.search(
        r"\b[A-Za-z_]\w*(?:nullifier|spent|replay|claim|nonce)[A-Za-z_]*\s*\(",
        consumer.function.body,
        re.I,
    ))
    if not uses and not consumer.effect_calls:
        return result(
            "P3", "UNKNOWN", "PROTECTED_EFFECT_NOT_RECOVERED",
            "Replay-key safety is not decided because neither a replay-state access nor a supported protected effect was recovered.",
            where=where, applicability="NOT_APPLICABLE",
        )
    if not uses:
        if replay_helper:
            return result("P3", "UNKNOWN", "REPLAY_BARRIER_HELPER_UNRESOLVED", "Replay-relevant handling may be delegated to an unsupported helper.", where=where)
        return result(
            "P3", "UNKNOWN", "REPLAY_KEY_NOT_RECOVERED",
            "No replay-relevant state access was recovered; the replay-barrier pattern is not applicable to this function.",
            where=where, applicability="NOT_APPLICABLE",
        )
    if verifier is None or verifier.interface_only:
        return result("P3", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "Replay-key canonicality cannot be decided without a matched verifier implementation.", where=where)
    if circuit is None:
        return result("P3", "UNKNOWN", "CIRCUIT_ARTIFACT_MISSING", "Replay-key canonicality cannot be decided without a matched circuit artifact.", where=where)
    facts: list[dict[str, Any]] = []
    aliases = {normalize_expression(name): value for name, value in assignments(consumer.function.body).items()}
    for mapping, key in uses:
        key_pattern = re.escape(key).replace(r"\ ", r"\s*")
        read = bool(re.search(rf"(?:require|if)\s*\([^;]*{re.escape(mapping)}\s*\[\s*{key_pattern}\s*\]", consumer.function.body, re.S))
        write = bool(re.search(rf"{re.escape(mapping)}\s*\[\s*{key_pattern}\s*\]\s*=\s*(?:true|1)\b", consumer.function.body, re.S))
        resolved_key = _resolve_alias(key, aliases)
        resolved_key = re.sub(r"\[\(([^()]+)\)\]", r"[\1]", resolved_key)
        proof_bound, proof_positions = _replay_key_binding_to_verifier(consumer, resolved_key)
        raw = bool(re.fullmatch(
            r"[A-Za-z_]\w*(?:(?:\s*\.\s*[A-Za-z_]\w*)|(?:\s*\[\s*[A-Za-z_0-9]+\s*\]))*",
            resolved_key,
        ))
        helper = _key_passed_to_internal_helper(consumer.function.body, key)
        fact = {"provenance": "EXTRACTED", "mapping": mapping, "key": key, "resolved_key": resolved_key,
                "read": read, "write": write, "raw": raw, "helper": helper, "proof_bound": proof_bound,
                "proof_positions": sorted(proof_positions) if proof_positions is not None else None}
        facts.append(fact)
        if helper and (not read or not write):
            return result("P3", "UNKNOWN", "REPLAY_BARRIER_HELPER_UNRESOLVED", "Replay handling is delegated to a helper outside the supported local mapping subset.", where=where, facts=facts)
        if not read:
            return result("P3", "VIOLATION", "REPLAY_KEY_NOT_CHECKED", "A recovered replay key is written or used without a prior spent check.", where=where, facts=facts)
        if not write:
            return result("P3", "VIOLATION", "REPLAY_KEY_NOT_CONSUMED", "A recovered replay key is checked but not consumed on the accepted path.", where=where, facts=facts)
        if not proof_bound:
            return result(
                "P3", "VIOLATION", "REPLAY_KEY_NOT_BOUND_TO_PROOF",
                "The consumed replay key is caller-controlled but no supported binding to the verifier public inputs was recovered.",
                where=where, facts=facts,
            )
        if not raw and not re.search(r"(?:keccak256|sha256|%|mod)", resolved_key, re.I):
            return result("P3", "UNKNOWN", "REPLAY_KEY_EXPRESSION_UNRESOLVED", "Replay-key expression is outside supported raw/canonicalized forms.", where=where, facts=facts)
        if raw and verifier is not None and proof_positions is None:
            return result(
                "P3", "UNKNOWN", "REPLAY_KEY_POSITION_UNRESOLVED",
                "The replay key is proof-related, but its exact public-input position was not recovered.",
                where=where, facts=facts,
            )
        verifier_guard = (
            verifier is not None
            and proof_positions is not None
            and canonical_guard(verifier.source.text, proof_positions)
        )
        local_guard = _local_scalar_guard(consumer, key) if raw else True
        reduces = verifier is not None and bool(re.search(r"\b(?:mod|addmod|mulmod)\b|%\s*(?:q|r|FIELD|SCALAR)", verifier.source.text, re.I))
        if raw and not (verifier_guard or local_guard) and (reduces or verifier is not None):
            return result("P3", "VIOLATION", "FIELD_ALIAS_REPLAY_KEY", "The verifier accepts field representatives while Solidity keys replay state by an unguarded raw integer.", where=where, facts=facts)
    return result("P3", "VERIFIED_WITHIN_SCOPE", "REPLAY_KEY_CANONICAL_AND_CONSUMED", "Recovered replay keys are checked, consumed, and canonicalized or domain-separated in the supported subset.", where=where, facts=facts)


def _local_scalar_guard(consumer: Consumer, key: str) -> bool:
    """Recognize a prior unconditional require on the exact replay-key value."""
    body = consumer.function.body
    source = consumer.source.text
    names = re.findall(rf"\b([A-Za-z_]\w*)\s*=\s*{SCALAR_FIELD}\s*;", source)
    modulus = rf"(?:{SCALAR_FIELD}|{'|'.join(re.escape(name) for name in names)})" if names else str(SCALAR_FIELD)
    key_expr = rf"(?:uint256\s*\(\s*{re.escape(key)}\s*\)|{re.escape(key)})"
    exact_condition = re.compile(rf"{key_expr}\s*<\s*{modulus}", re.I)
    for match in re.finditer(r"\brequire\s*\(", body):
        prefix = body[:match.start()]
        # A conditional single-statement require does not dominate the call.
        statement_start = max(prefix.rfind(";"), prefix.rfind("{"), prefix.rfind("}")) + 1
        if prefix[statement_start:].strip():
            continue
        if prefix.count("{") != prefix.count("}"):
            continue
        first_verify = min((call.offset for call in consumer.verify_calls), default=len(body))
        parsed = balanced(body, body.find("(", match.start()))
        if parsed is None:
            continue
        condition = split_top_level(parsed[0])[0]
        if match.start() < first_verify and exact_condition.fullmatch(condition.strip()):
            return True
    return False


def _semantic_name(expression: str) -> str:
    names = [name for name in identifiers(expression) if name.lower() not in {"uint160", "uint256", "address", "bytes32"}]
    return names[-1].lower() if names else normalize_expression(expression).lower()


def analyze_p5(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer, *, ambiguous: bool) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    if ambiguous:
        return result("P5", "UNKNOWN", "VERIFIER_MATCH_AMBIGUOUS", "Multiple plausible verifier artifacts expose incompatible public-input shapes.", where=where)
    if verifier is None or verifier.interface_only:
        return result("P5", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "Verifier arity/order cannot be checked without an implementation artifact.", where=where)
    if circuit is None:
        return result("P5", "UNKNOWN", "CIRCUIT_ARTIFACT_MISSING", "Circuit public order cannot be checked without a matched circuit artifact.", where=where)
    vector = consumer.vectors[0] if consumer.vectors else None
    if vector is None:
        return result("P5", "UNKNOWN", "PUBLIC_INPUT_VECTOR_UNRESOLVED", "No verifier public-input vector was recovered.", where=where)
    verifier_arities = verifier.arities
    expected = next(iter(verifier_arities)) if len(verifier_arities) == 1 else None
    observed = vector.declared_count or vector.length_guard
    facts = [
        {"provenance": "EXTRACTED", "name": "consumer_count", "value": observed},
        {"provenance": "EXTRACTED", "name": "consumer_order", "value": vector.items},
        {"provenance": "EXTRACTED", "name": "verifier_arities", "value": sorted(verifier_arities)},
        {"provenance": "EXTRACTED", "name": "circuit_order", "value": circuit.public_order},
    ]
    if vector.dynamic and vector.length_guard is None:
        return result("P5", "UNKNOWN", "DYNAMIC_PUBLIC_INPUT_LENGTH_UNRESOLVED", "Dynamic verifier inputs have no supported exact length guard.", where=where, facts=facts)
    if "public-vector-shape" in vector.unresolved and not vector.items and vector.declared_count is None and vector.length_guard is None:
        return result(
            "P5", "UNKNOWN", "PUBLIC_INPUT_VECTOR_UNRESOLVED",
            "A verifier call was recovered, but its public-signal vector shape could not be established.",
            where=where, facts=facts,
        )
    if expected is not None and observed is not None and expected != observed:
        return result("P5", "VIOLATION", "PUBLIC_INPUT_COUNT_MISMATCH", f"Consumer supplies {observed} public inputs but the matched verifier expects {expected}.", where=where, facts=facts)
    if circuit.public_count is not None and observed is not None and circuit.public_count != observed:
        if not circuit.order_complete and not circuit.compiled:
            return result(
                "P5", "UNKNOWN", "CIRCUIT_INTERFACE_INCOMPLETE",
                "The source-level circuit interface is incomplete and no compiled relation is available to establish its public-input count.",
                where=where, facts=facts,
            )
        return result("P5", "VIOLATION", "PUBLIC_INPUT_COUNT_MISMATCH", f"Consumer supplies {observed} public inputs but the circuit exposes {circuit.public_count}.", where=where, facts=facts)
    if vector.items and circuit.public_order and len(vector.items) == len(circuit.public_order):
        observed_order = [_semantic_name(item) for item in vector.items]
        circuit_order = [_semantic_name(item) for item in circuit.public_order]
        if observed_order != circuit_order:
            if sorted(observed_order) == sorted(circuit_order):
                return result("P5", "VIOLATION", "PUBLIC_INPUT_ORDER_MISMATCH", "Recovered consumer vector contains the circuit's named public signals in a different order.", where=where, facts=facts)
            return result(
                "P5", "UNKNOWN", "PUBLIC_INPUT_MEANING_UNRESOLVED",
                "Counts agree, but differing source-level names do not establish whether consumer and circuit elements have the same meaning.",
                where=where, facts=facts,
            )
    elif not vector.items or not circuit.order_complete:
        if vector.dynamic and vector.length_guard and expected == vector.length_guard:
            return result("P5", "VERIFIED_WITHIN_SCOPE", "DYNAMIC_PUBLIC_INPUT_LENGTH_GUARDED", "Dynamic public inputs have an exact length guard matching the verifier declaration.", where=where, facts=facts, limitations=["Element meaning/order was not independently named by the dynamic interface."])
        return result("P5", "UNKNOWN", "PUBLIC_INPUT_ORDER_UNRESOLVED", "Counts are compatible, but exact element order/meaning was not recovered.", where=where, facts=facts)
    return result("P5", "VERIFIED_WITHIN_SCOPE", "PUBLIC_INPUT_COUNT_AND_ORDER_MATCH", "Recovered circuit, verifier, and consumer public-input count/order agree.", where=where, facts=facts)


def _serialize_circuit(circuit: Circuit | None) -> dict[str, Any] | None:
    if circuit is None:
        return None
    return {
        "path": circuit.relative_path,
        "sha256": circuit.sha256,
        "language": circuit.language,
        "public_order": circuit.public_order,
        "public_count": circuit.public_count,
        "order_complete": circuit.order_complete,
        "compiled_relation": {
            "available": circuit.compiled,
            "r1cs_sha256": sha256_file(circuit.r1cs) if circuit.r1cs and circuit.r1cs.is_file() else None,
            "sym_sha256": sha256_file(circuit.sym) if circuit.sym and circuit.sym.is_file() else None,
            "build": circuit.build,
        },
    }


def _serialize_verifier(verifier: Verifier | None) -> dict[str, Any] | None:
    if verifier is None:
        return None
    return {
        "path": verifier.source.relative_path,
        "sha256": verifier.source.sha256,
        "family": verifier.family,
        "contract_names": sorted(verifier.contract_names),
        "interface_only": verifier.interface_only,
        "declarations": verifier.declarations,
    }


def _serialize_consumer(consumer: Consumer) -> dict[str, Any]:
    return {
        "path": consumer.source.relative_path,
        "sha256": consumer.source.sha256,
        "function": consumer.function.name,
        "line": consumer.function.line,
        "public_vectors": [dataclasses.asdict(vector) for vector in consumer.vectors],
        "effects": [
            {"call": call.name, "line": consumer.function.line + call.line - 1,
             "roles": [{"role": role, "expression": expression} for role, expression in effect_roles(call, consumer.source.text)]}
            for call in consumer.effect_calls
        ],
    }


def _generation_recipes(root: pathlib.Path, files: list[pathlib.Path]) -> list[dict[str, Any]]:
    """Find repository-authored fresh-zkey/verifier recipes without executing them."""
    grouped: dict[pathlib.Path, list[tuple[pathlib.Path, str]]] = defaultdict(list)
    for path in files:
        if path.suffix.lower() not in {".json", ".sh", ".js", ".ts", ".mjs", ".cjs"} and path.name.lower() not in {"makefile", "justfile"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not re.search(r"(?:snarkjs|zkey|powersoftau|solidityverifier)", text, re.I):
            continue
        grouped[path.parent].append((path, text))
    recipes: list[dict[str, Any]] = []
    for directory, records in grouped.items():
        combined = "\n".join(text for _, text in records)
        exports = bool(re.search(r"zkey\s+export\s+solidityverifier", combined, re.I))
        setup = bool(re.search(r"groth16\s+setup", combined, re.I))
        prepares = bool(re.search(r"powersoftau\s+prepare\s+phase2", combined, re.I))
        creates = bool(re.search(r"powersoftau\s+new\s+bn128\s+(\d+)", combined, re.I))
        powers = [int(value) for value in re.findall(r"powersoftau\s+new\s+bn128\s+(\d+)", combined, re.I)]
        if exports:
            recipes.append({
                "directory": directory.relative_to(root).as_posix() or ".",
                "sources": [path.relative_to(root).as_posix() for path, _ in records],
                "fresh_zkey_steps": {"powersoftau_new": creates, "prepare_phase2": prepares, "groth16_setup": setup, "solidity_export": exports},
                "power": max(powers) if powers else None,
                "complete": bool(creates and prepares and setup and exports and powers),
            })
    return recipes


def _regenerate_verifier(
    circuit: Circuit, recipe: dict[str, Any], budget: Budget, timeout: float
) -> tuple[Verifier | None, dict[str, Any]]:
    record: dict[str, Any] = {"kind": "fresh-local-zkey", "recipe": recipe, "steps": []}
    if circuit.r1cs is None or not circuit.r1cs.is_file():
        record["reason"] = "COMPILED_R1CS_UNAVAILABLE"
        return None, record
    power = recipe.get("power")
    if not recipe.get("complete") or not isinstance(power, int):
        record["reason"] = "REPOSITORY_GENERATION_RECIPE_INCOMPLETE"
        return None, record
    parsed = parse_r1cs(circuit.r1cs)
    required_power = max(1, math.ceil(math.log2(max(2, parsed["n_constraints"] + parsed["n_public_inputs"] + parsed["n_public_outputs"] + 1))))
    record["required_power"] = required_power
    if power < required_power:
        record["reason"] = "REPOSITORY_RECIPE_POWER_TOO_SMALL"
        return None, record
    if power > 18:
        record["reason"] = "REPOSITORY_RECIPE_EXCEEDS_LOCAL_POWER_BOUND"
        return None, record
    tool_root = pathlib.Path(__file__).resolve().parents[1]
    snarkjs = tool_root / "node_modules" / ".bin" / "snarkjs"
    if not snarkjs.is_file():
        record["reason"] = "SNARKJS_NOT_AVAILABLE"
        return None, record
    with tempfile.TemporaryDirectory(prefix="bindcheck-zk-verifier-") as temp_name:
        temp = pathlib.Path(temp_name)
        pot0, pot_final = temp / "pot_0000.ptau", temp / "pot_final.ptau"
        zkey0, verifier_path = temp / "circuit_0000.zkey", temp / "Verifier.sol"
        commands = [
            [str(snarkjs), "powersoftau", "new", "bn128", str(power), str(pot0)],
            [str(snarkjs), "powersoftau", "prepare", "phase2", str(pot0), str(pot_final)],
            [str(snarkjs), "groth16", "setup", str(circuit.r1cs), str(pot_final), str(zkey0)],
            [str(snarkjs), "zkey", "export", "solidityverifier", str(zkey0), str(verifier_path)],
        ]
        started = time.monotonic()
        for argv in commands:
            remaining = min(timeout - (time.monotonic() - started), budget.remaining)
            if remaining <= 0.05:
                record["reason"] = "VERIFIER_REGENERATION_TIMEOUT"
                return None, record
            step = run(argv, cwd=temp, timeout=remaining)
            record["steps"].append(step)
            if step["timed_out"] or step["exit_status"] != 0:
                record["reason"] = "VERIFIER_REGENERATION_TIMEOUT" if step["timed_out"] else "VERIFIER_REGENERATION_FAILED"
                return None, record
        if not verifier_path.is_file():
            record["reason"] = "GENERATED_VERIFIER_MISSING"
            return None, record
        text = verifier_path.read_text(encoding="utf-8", errors="replace")
        source = Source(
            verifier_path,
            f"<generated-from-fresh-zkey>/{circuit.path.stem}Verifier.sol",
            text,
            sha256_file(verifier_path),
        )
        verifier = classify_verifier(source)
        if verifier is None:
            record["reason"] = "GENERATED_VERIFIER_UNSUPPORTED"
            return None, record
        record["reason"] = "GENERATED_VERIFIER_READY"
        record["verifier_sha256"] = source.sha256
        return verifier, record


def analyze(
    root: pathlib.Path,
    *,
    explicit_circuits: list[str] | None = None,
    explicit_consumers: list[str] | None = None,
    bundle: bool = False,
    policy: dict[str, bool] | None = None,
) -> dict[str, Any]:
    started_utc = dt.datetime.now(dt.UTC).isoformat()
    started = time.monotonic()
    config = load_config()
    budget = Budget(float(config["run_timeout_seconds"]))
    root = root.resolve()
    coverage: dict[str, Any] = {
        "files_inventoried": 0, "solidity_files_parsed": 0, "circuit_files_parsed": 0,
        "compiled_relations_built_or_loaded": 0, "skipped": [], "builds": [],
        "timeouts": [], "failures": [], "unsupported": [], "excluded": [],
        "generated_verifier": [],
    }
    fatal: str | None = None
    triples_output: list[dict[str, Any]] = []
    runtime_results: list[dict[str, Any]] = []
    circuits: list[Circuit] = []
    inputs: dict[str, Any] = {
        "root": str(root), "mode": "verified-source-bundle" if bundle else "repository",
        "git_revision": _git_revision(root), "network_policy": "offline/no RPC",
        "explicit_circuits": explicit_circuits or [], "explicit_consumers": explicit_consumers or [],
        "policy": {"any_caller_may_receive": bool((policy or {}).get("any_caller_may_receive", False))},
    }
    try:
        if not root.is_dir():
            raise ValueError(f"analysis root is not a directory: {root}")
        files, skipped, excluded = inventory(root, config, budget)
        coverage["files_inventoried"] = len(files)
        coverage["skipped"].extend(skipped)
        coverage["excluded"].extend(excluded)
        if explicit_circuits:
            circuit_paths = [_safe_explicit(root, raw) for raw in explicit_circuits]
        else:
            all_circuit_paths = [path for path in files if path.suffix.lower() in {".circom", ".nr"}]
            circuit_paths = [path for path in all_circuit_paths if is_entry_circuit(path)]
            coverage["skipped"].extend({
                "path": path.relative_to(root).as_posix(),
                "reason": "NON_ENTRY_CIRCUIT_SOURCE",
            } for path in all_circuit_paths if path not in circuit_paths)
        explicit_consumer_paths = {_safe_explicit(root, raw) for raw in explicit_consumers or []}
        for explicit_path in [*circuit_paths, *explicit_consumer_paths]:
            if explicit_path not in files:
                files.append(explicit_path)
        files.sort()
        sources = read_sources(root, files, coverage)
        pin_suffixes = {".sol", ".circom", ".nr", ".json", ".runtime", ".hex"}
        pinned_files: list[dict[str, Any]] = []
        for path in files:
            if path.suffix.lower() not in pin_suffixes and not path.name.lower().endswith(".bin-runtime"):
                continue
            try:
                pinned_files.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
            except OSError as exc:
                coverage["skipped"].append({
                    "path": path.relative_to(root).as_posix(), "reason": "HASH_FAILED", "detail": str(exc)
                })
        inputs["files"] = pinned_files
        coverage["solidity_files_parsed"] = len(sources)
        semantic_sources = [source for source in sources if not _semantic_excluded(source.relative_path, config)]
        circuits = discover_circuits(root, circuit_paths)
        coverage["circuit_files_parsed"] = len(circuits)
        verifiers = [item for source in semantic_sources if (item := classify_verifier(source)) is not None]
        consumers = discover_consumers(semantic_sources)
        verifier_source_paths = {item.source.path for item in verifiers}
        consumers = [
            item for item in consumers
            if item.source.path not in verifier_source_paths
            or item.effect_calls
            or (
                "verifier" not in item.source.path.stem.lower()
                and not re.match(r"^_?(?:verify|validate)(?:proof|tx|plonk|andconsume)?$", item.function.name, re.I)
            )
        ]
        if explicit_consumer_paths:
            consumers = [item for item in consumers if item.source.path in explicit_consumer_paths]
        circuit_ranked = sorted(circuits, key=lambda circuit: (
            -max((
                _match_score(circuit, verifier, consumer)[0]
                for verifier in (verifiers or [None]) for consumer in consumers
            ), default=0.0),
            circuit.relative_path,
        ))
        for circuit in [item for item in circuit_ranked if item.language == "circom"][: int(config["max_circuit_builds"])]:
            attach_or_build(circuit, root, budget, float(config["build_timeout_seconds"]))
            coverage["builds"].append({"path": circuit.relative_path, "record": circuit.build})
            if circuit.compiled:
                coverage["compiled_relations_built_or_loaded"] += 1
            elif circuit.build and circuit.build.get("timed_out"):
                coverage["timeouts"].append({"phase": "circom-build", "path": circuit.relative_path})
            elif circuit.build and circuit.build.get("exit_status") not in (None, 0):
                coverage["failures"].append({"phase": "circom-build", "path": circuit.relative_path, "record": circuit.build})
        implementation_verifiers = [item for item in verifiers if not item.interface_only]
        if consumers and not implementation_verifiers:
            recipes = _generation_recipes(root, files)
            if not recipes:
                coverage["generated_verifier"].append({"reason": "REPOSITORY_GENERATION_RECIPE_NOT_FOUND"})
            else:
                complete = next((item for item in recipes if item["complete"]), None)
                compiled = next((item for item in circuit_ranked if item.compiled), None)
                if complete is None:
                    coverage["generated_verifier"].append({
                        "reason": "REPOSITORY_GENERATION_RECIPE_INCOMPLETE", "recipes": recipes,
                    })
                elif compiled is None:
                    coverage["generated_verifier"].append({
                        "reason": "COMPILED_R1CS_UNAVAILABLE", "recipes": recipes,
                    })
                else:
                    regenerated, generation_record = _regenerate_verifier(
                        compiled, complete, budget, float(config["verifier_generation_timeout_seconds"])
                    )
                    coverage["generated_verifier"].append(generation_record)
                    if regenerated is not None:
                        verifiers.append(regenerated)
        runtime_values = runtime_values_from_bundle(root, files) if bundle else runtime_values_from_bundle(root, [path for path in files if path.name.lower().endswith((".bin-runtime", ".runtime.hex"))])
        source_has_p2 = any(item.p4.get("p2") for item in verifiers)
        for path, value in runtime_values:
            runtime_results.append({"path": path, **analyze_runtime(value, path, source_has_p2=source_has_p2)})
        triples = make_triples(circuits, [item for item in verifiers if not item.interface_only] or verifiers, consumers, int(config["max_triples"]))
        arities_by_consumer: dict[str, set[tuple[int, ...]]] = defaultdict(set)
        for item in triples:
            verifier = item["verifier_obj"]
            if verifier:
                arities_by_consumer[item["consumer_obj"].source.relative_path + ":" + item["consumer_obj"].function.name].add(tuple(sorted(verifier.arities)))
        for item in triples:
            budget.check()
            circuit: Circuit | None = item.pop("circuit_obj")
            verifier: Verifier | None = item.pop("verifier_obj")
            consumer: Consumer = item.pop("consumer_obj")
            key = consumer.source.relative_path + ":" + consumer.function.name
            if verifier is None:
                p4_result = result("P4", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "No verifier implementation artifact was matched.", grade="E0", where=location(consumer.source.relative_path, consumer.function.line))
            elif verifier.interface_only:
                p4_result = result("P4", "UNKNOWN", "VERIFIER_IMPLEMENTATION_ARTIFACT_MISSING", "Only a verifier interface was matched; verification-key implementation checks are unavailable.", grade="E0", where=location(verifier.source.relative_path, 1))
            else:
                p4_result = verifier.p4["finding"]
            significant_runtime = next((entry["finding"] for entry in runtime_results if entry["finding"]["reason"] in {"DEFAULT_G2_RUNTIME_SIGNATURE", "PAIRING_LIBRARY_GENERATOR_EXCLUDED", "RUNTIME_BYTECODE_PARSE_INCOMPLETE"}), None)
            if significant_runtime is not None:
                p4_result = significant_runtime
            pattern_results = {
                "P1": analyze_p1(circuit, verifier, consumer, policy),
                "P2": analyze_p2(circuit, verifier, consumer),
                "P3": analyze_p3(circuit, verifier, consumer),
                "P4": p4_result,
                "P5": analyze_p5(circuit, verifier, consumer, ambiguous=len(arities_by_consumer[key]) > 1),
            }
            item.update({
                "circuit": _serialize_circuit(circuit),
                "verifier": _serialize_verifier(verifier),
                "consumer": _serialize_consumer(consumer),
                "patterns": pattern_results,
                "aggregate": aggregate(list(pattern_results.values())),
            })
            triples_output.append(item)
        if not triples_output:
            coverage["unsupported"].append({"reason": "NO_CIRCUIT_VERIFIER_CONSUMER_TRIPLE_DISCOVERED"})
    except TimeoutError as exc:
        fatal = "RUN_TIMEOUT"
        coverage["timeouts"].append({"phase": "analysis", "detail": str(exc)})
    except Exception as exc:  # fail closed: malformed/unknown input is JSON UNKNOWN, never a crash/pass
        fatal = "ANALYSIS_FAILED"
        coverage["failures"].append({"phase": "analysis", "type": type(exc).__name__, "detail": str(exc)})
    for circuit in circuits:
        if circuit.temporary_artifacts is not None:
            shutil.rmtree(circuit.temporary_artifacts, ignore_errors=True)
    pattern_summary: dict[str, Any] = {}
    for pattern in PATTERNS:
        results = [triple["patterns"][pattern] for triple in triples_output]
        if not results:
            results = [result(
                pattern, "UNKNOWN", fatal or "NO_APPLICABLE_TRIPLE",
                "The analyzer could not establish whether an applicable circuit/verifier/consumer triple exists.",
                grade="E0", applicability="UNKNOWN",
            )]
        summary = aggregate(results)
        applicable_unknowns = [
            item for item in results
            if item["verdict"] == "UNKNOWN" and item.get("applicability", "APPLICABLE") == "APPLICABLE"
        ]
        if summary["applicability"] != "APPLICABLE":
            applicable_unknowns = [item for item in results if item["verdict"] == "UNKNOWN"]
        pattern_summary[pattern] = {
            **summary,
            "results": len(results),
            "reasons": sorted({item["reason"] for item in results}),
            "unknown_reason_codes": sorted({
                item["unknown_reason_code"] for item in applicable_unknowns
                if item.get("unknown_reason_code")
            }),
        }
    tool_hash, _ = freeze_manifest(pathlib.Path(__file__).resolve().parents[1])
    return {
        "schema": "bindcheck-zk.result/v1",
        "tool": {"name": "bindcheck-zk", "version": __version__, "content_sha256": tool_hash, "dependencies": "Python standard library only"},
        "run": {
            "started_utc": started_utc, "elapsed_seconds": round(time.monotonic() - started, 6),
            "budget_seconds": config["run_timeout_seconds"], "status": "UNKNOWN" if fatal else "completed",
            "fatal_reason": fatal,
        },
        "inputs": inputs,
        "discovery": {
            "circuits": len({triple["circuit"]["path"] for triple in triples_output if triple["circuit"]}),
            "verifiers": len({triple["verifier"]["path"] for triple in triples_output if triple["verifier"]}),
            "consumers": len({(triple["consumer"]["path"], triple["consumer"]["function"]) for triple in triples_output}),
            "triples": len(triples_output),
        },
        "triples": triples_output,
        "runtime_bytecode_checks": runtime_results,
        "patterns": pattern_summary,
        "coverage": coverage,
        "limitations": [
            "E1 static/compiler-backed results are not E2 models, E3 proofs, or E4 committed-effect validations.",
            "Unsupported constructs, build failures, timeouts, missing artifacts, and ambiguous matches remain UNKNOWN.",
            "No network, RPC, deployed-contract call, or transaction is performed by this tool.",
        ],
    }
