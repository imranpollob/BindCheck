from __future__ import annotations

import dataclasses
import datetime as dt
import json
import pathlib
import re
import subprocess
import time
from collections import defaultdict
from typing import Any

from . import __version__
from .circuits import Circuit, attach_or_build, discover as discover_circuits, named_path
from .freeze import freeze_manifest
from .models import Budget, aggregate, location, result, sha256_file
from .p4 import analyze_runtime, analyze_source, canonical_guard, runtime_values_from_bundle
from .solidity import (
    Call,
    Function,
    PublicVector,
    assignments,
    calls,
    effect_calls,
    effect_roles,
    functions,
    has_unsupported_construct,
    identifiers,
    normalize_expression,
    public_vector,
    verification_calls,
    verifier_declarations,
)


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


def inventory(root: pathlib.Path, config: dict[str, Any], budget: Budget) -> tuple[list[pathlib.Path], list[dict[str, Any]]]:
    excluded = set(config["excluded_directories"])
    output: list[pathlib.Path] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        budget.check()
        relative = path.relative_to(root)
        if excluded & set(relative.parts):
            continue
        if not path.is_file():
            continue
        if len(output) >= int(config["max_files"]):
            skipped.append({"path": relative.as_posix(), "reason": "MAX_FILES_EXCEEDED"})
            continue
        try:
            size = path.stat().st_size
        except OSError as exc:
            skipped.append({"path": relative.as_posix(), "reason": "STAT_FAILED", "detail": str(exc)})
            continue
        if size > int(config["max_file_bytes"]):
            skipped.append({"path": relative.as_posix(), "reason": "FILE_TOO_LARGE", "bytes": size})
            continue
        output.append(path)
    return output, skipped


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


def classify_verifier(source: Source) -> Verifier | None:
    declarations = verifier_declarations(source.text)
    named = bool(re.search(
        r"\b(?:contract|library|interface)\s+[A-Za-z_]\w*(?:Verifier|Groth16|Plonk|Honk|Ultra)[A-Za-z_]*\b"
        r"|\b(?:Pairing|Groth16|Plonk|Honk|Ultra|IVerifier)\b",
        source.text,
        re.I,
    ))
    if not declarations or not named:
        return None
    interface_only = bool(re.search(r"\binterface\s+[A-Za-z_]\w*", source.text)) and not bool(
        re.search(r"\bfunction\s+(?:verifyProof|verifyTx|verify)\b[^{;]*\{", source.text, re.S | re.I)
    )
    lower = source.text.lower()
    if "honk" in lower or "ultra" in lower:
        family = "Honk"
    elif "plonk" in lower or "verifyproof(bytes" in re.sub(r"\s+", "", lower):
        family = "PLONK"
    elif "pairing" in lower or "groth16" in lower:
        family = "Groth16"
    else:
        family = "unknown"
    return Verifier(source, declarations, interface_only, family, analyze_source(source.text, source.relative_path))


def discover_consumers(sources: list[Source]) -> list[Consumer]:
    output: list[Consumer] = []
    for source in sources:
        parsed_functions = list(functions(source.text))
        helper_vector_parameters: dict[str, list[int]] = defaultdict(list)
        for helper in parsed_functions:
            parameter_names = list(helper.parameters)
            for direct_call in verification_calls(helper.body):
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
            verify = verification_calls(function.body)
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
            effects = effect_calls(function.body)
            if not effects:
                continue
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
            output.append(Consumer(source, function, verify, effects, vectors))
    return output


def _tokens(path: str) -> set[str]:
    return {
        token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", pathlib.Path(path).stem)
        if token.lower() not in {"main", "circuit", "circuits", "contract", "contracts", "verifier", "consumer"}
    }


def _match_score(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer) -> tuple[float, list[str]]:
    score = 0.2
    reasons = ["consumer contains verifier call and protected effect"]
    consumer_tokens = _tokens(consumer.source.relative_path) | {consumer.function.name.lower()}
    if verifier:
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
        vector_counts = {item.declared_count or item.length_guard for item in consumer.vectors}
        if circuit.public_count and circuit.public_count in vector_counts:
            score += 0.2
            reasons.append("circuit public count matches recovered consumer vector")
        if verifier and circuit.public_count and circuit.public_count in verifier.arities:
            score += 0.15
            reasons.append("circuit public count matches verifier arity")
    if circuit is None:
        reasons.append("circuit artifact missing")
    if verifier is None:
        reasons.append("verifier implementation artifact missing")
    return max(0.0, min(score, 0.99)), reasons


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
            if score + 0.25 < best:
                continue
            triples.append({
                "id": f"T{len(triples) + 1:03d}",
                "circuit_obj": circuit,
                "verifier_obj": verifier,
                "consumer_obj": consumer,
                "match": {
                    "score": round(score, 3),
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


def _commitment_binding(
    expression: str,
    vector: PublicVector,
    circuit: Circuit,
    consumer: Consumer,
    repository_solidity: str,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    expression_names = identifiers(expression)
    circuit_source = circuit.path.read_text(encoding="utf-8", errors="replace")
    for component in circuit.components:
        commitment = component["commitment"]
        input_names = set().union(*(identifiers(item) for item in component["inputs"]))
        if not expression_names & input_names:
            continue
        public_has_commitment = any(commitment in identifiers(item) for item in vector.items) or commitment in vector.sources
        if not public_has_commitment:
            continue
        guard = bool(re.search(
            rf"(?:require\s*\((?=[^;]*\b{re.escape(commitment)}\b)(?=[^;]*(?:==|!=))|"
            rf"if\s*\((?=[^;]*\b{re.escape(commitment)}\b)(?=[^;]*(?:==|!=))[^;]*\)\s*revert)",
            consumer.function.body,
            re.S,
        ))
        has_hash = bool(re.search(r"poseidon|compute\w*hash|keccak256", repository_solidity, re.I))
        order_ok = all(name in repository_solidity for name in input_names if name.lower() not in {"domain", "ds"})
        if not (guard and has_hash and order_ok):
            return False, None, "LOCAL_COMMITMENT_GUARD_UNESTABLISHED"
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
            return True, {
                "component": component,
                "compiled_path": path,
                "consumer_guard": True,
                "algorithm_evidence": "hash helper recovered in consumer sources",
                "order_evidence": sorted(input_names),
                "circuit_source_sha256": circuit.sha256,
                "r1cs_sha256": sha256_file(circuit.r1cs),
            }, None
        return False, path, "COMPILED_COMMITMENT_PATH_UNESTABLISHED"
    return False, None, None


def analyze_p1(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer, repository_solidity: str) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    unsupported = has_unsupported_construct(consumer.function.body)
    if unsupported:
        return result("P1", "UNKNOWN", unsupported, "Consumer function uses a construct outside the supported dataflow subset.", where=where)
    if verifier is None:
        return result("P1", "UNKNOWN", "VERIFIER_ARTIFACT_MISSING", "Consumer is analyzed, but the verifier implementation artifact is absent.", where=where)
    if circuit is None:
        return result("P1", "UNKNOWN", "CIRCUIT_ARTIFACT_MISSING", "Consumer/verifier artifacts are present but no circuit artifact was matched.", where=where)
    aliases = {normalize_expression(name): value for name, value in assignments(consumer.function.body).items()}
    role_facts: list[dict[str, Any]] = []
    violations: list[str] = []
    unknown_reasons: list[str] = []
    for call in consumer.effect_calls:
        for role, expression in effect_roles(call):
            fact: dict[str, Any] = {"provenance": "EXTRACTED", "role": role, "expression": expression, "bound_by": []}
            resolved_expression = normalize_expression(_resolve_alias(expression, aliases))
            if role == "recipient" and resolved_expression == "msg.sender":
                fact["bound_by"].append("msg.sender")
            if role == "recipient" and resolved_expression == "this":
                fact["bound_by"].append("contract-self")
            if any(_direct_bound(expression, vector, aliases) for vector in consumer.vectors):
                fact["bound_by"].append("direct-public-input")
            if not fact["bound_by"]:
                for vector in consumer.vectors:
                    bound, evidence, reason = _commitment_binding(expression, vector, circuit, consumer, repository_solidity)
                    if bound:
                        fact["bound_by"].append("compiled-commitment")
                        fact["commitment_evidence"] = evidence
                        break
                    if reason:
                        unknown_reasons.append(reason)
                        fact.setdefault("unresolved", []).append({"reason": reason, "evidence": evidence})
            if not fact["bound_by"]:
                if unknown_reasons:
                    pass
                elif role == "recipient":
                    violations.append("UNBOUND_EFFECT_RECIPIENT")
                elif role == "amount":
                    violations.append("UNBOUND_EFFECT_AMOUNT")
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
        return result("P1", "UNKNOWN", "PROTECTED_EFFECT_NOT_RECOVERED", "No supported protected effect role was recovered.", where=where)
    reason = "RECIPIENT_BOUND_TO_MSG_SENDER" if any("msg.sender" in fact["bound_by"] for fact in role_facts) else "EFFECT_VALUES_DIRECT_PUBLIC_INPUTS"
    if any("contract-self" in fact["bound_by"] for fact in role_facts):
        reason = "RECIPIENT_BOUND_TO_CONTRACT_SELF"
    if any("compiled-commitment" in fact["bound_by"] for fact in role_facts):
        reason = "EFFECT_VALUES_BOUND_BY_COMPILED_COMMITMENT"
    return result(
        "P1", "VERIFIED_WITHIN_SCOPE", reason,
        "Every recovered protected effect role is bound by a direct verifier input, msg.sender, or a checked compiled commitment path.",
        where=where, facts=role_facts,
        limitations=["Result is limited to the recovered function, effects, matched artifacts, and supported dataflow forms."],
    )


def analyze_p2(circuit: Circuit | None, consumer: Consumer) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    unsupported = has_unsupported_construct(consumer.function.body)
    if unsupported == "UNSUPPORTED_DELEGATECALL_CONTEXT":
        return result("P2", "UNKNOWN", unsupported, "Delegatecall makes address/domain context semantics unsupported.", where=where)
    vector_text = " ".join(vector.expression + " " + " ".join(vector.items) for vector in consumer.vectors)
    body = consumer.function.body
    direct = bool(re.search(r"block\s*\.\s*chainid|address\s*\(\s*this\s*\)|\b(?:domain|chain_id|chainId|appId|verifyingContract)\b", vector_text, re.I))
    guarded = bool(re.search(
        r"(?:require|if)\s*\((?=[^;]*(?:block\s*\.\s*chainid|address\s*\(\s*this\s*\)|\b(?:domain|chain_id|chainId|appId)\b))(?=[^;]*(?:==|!=))",
        body,
        re.I | re.S,
    ))
    computed = bool(re.search(r"block\s*\.\s*chainid|address\s*\(\s*this\s*\)|\b(?:domain|chain_id|chainId|appId)\b", body, re.I))
    facts = [
        {"provenance": "EXTRACTED", "name": "context_in_public_vector", "value": direct},
        {"provenance": "EXTRACTED", "name": "context_local_guard", "value": guarded},
        {"provenance": "EXTRACTED", "name": "context_computation_present", "value": computed},
    ]
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
    pattern = re.compile(
        r"\b([A-Za-z_]\w*)\s*\[\s*((?:[A-Za-z_]\w*\s*\[[^\]\n]+\])|[^\]\n]+)\s*\]"
    )
    for name, key in pattern.findall(body):
        if name in declared and any(word in name.lower() for word in ("nullifier", "spent", "used", "replay", "claimed")):
            output.append((name, key.strip()))
    return output


def analyze_p3(verifier: Verifier | None, consumer: Consumer) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    uses = _mapping_uses(consumer.function.body, consumer.source.text)
    if not uses:
        return result("P3", "UNKNOWN", "REPLAY_KEY_NOT_RECOVERED", "No supported replay-key mapping access was recovered.", where=where)
    facts: list[dict[str, Any]] = []
    aliases = {normalize_expression(name): value for name, value in assignments(consumer.function.body).items()}
    for mapping, key in uses:
        key_pattern = re.escape(key).replace(r"\ ", r"\s*")
        read = bool(re.search(rf"(?:require|if)\s*\([^;]*{re.escape(mapping)}\s*\[\s*{key_pattern}\s*\]", consumer.function.body, re.S))
        write = bool(re.search(rf"{re.escape(mapping)}\s*\[\s*{key_pattern}\s*\]\s*=\s*(?:true|1)\b", consumer.function.body, re.S))
        resolved_key = _resolve_alias(key, aliases)
        resolved_key = re.sub(r"\[\(([^()]+)\)\]", r"[\1]", resolved_key)
        raw = bool(re.fullmatch(r"[A-Za-z_]\w*(?:\s*\[\s*[A-Za-z_0-9]+\s*\])?", resolved_key))
        helper = bool(re.search(r"\b(?:check|consume|mark|use)(?:Nullifier|Spent|Replay)\s*\(", consumer.function.body, re.I))
        fact = {"provenance": "EXTRACTED", "mapping": mapping, "key": key, "resolved_key": resolved_key,
                "read": read, "write": write, "raw": raw, "helper": helper}
        facts.append(fact)
        if helper and not (read or write):
            return result("P3", "UNKNOWN", "REPLAY_BARRIER_HELPER_UNRESOLVED", "Replay handling is delegated to a helper outside the supported local mapping subset.", where=where, facts=facts)
        if not read:
            return result("P3", "VIOLATION", "REPLAY_KEY_NOT_CHECKED", "A recovered replay key is written or used without a prior spent check.", where=where, facts=facts)
        if not write:
            return result("P3", "VIOLATION", "REPLAY_KEY_NOT_CONSUMED", "A recovered replay key is checked but not consumed on the accepted path.", where=where, facts=facts)
        if not raw and not re.search(r"(?:keccak256|sha256|%|mod)", resolved_key, re.I):
            return result("P3", "UNKNOWN", "REPLAY_KEY_EXPRESSION_UNRESOLVED", "Replay-key expression is outside supported raw/canonicalized forms.", where=where, facts=facts)
        verifier_guard = verifier is not None and canonical_guard(verifier.source.text)
        local_guard = bool(re.search(rf"\b{re.escape(key)}\b\s*<\s*(?:{load_config()['scalar_field']}|[A-Za-z_]\w*(?:FIELD|SCALAR|SNARK))", consumer.function.body, re.I)) if raw else True
        reduces = verifier is not None and bool(re.search(r"\b(?:mod|addmod|mulmod)\b|%\s*(?:q|r|FIELD|SCALAR)", verifier.source.text, re.I))
        if raw and not (verifier_guard or local_guard) and (reduces or verifier is not None):
            return result("P3", "VIOLATION", "FIELD_ALIAS_REPLAY_KEY", "The verifier accepts field representatives while Solidity keys replay state by an unguarded raw integer.", where=where, facts=facts)
    return result("P3", "VERIFIED_WITHIN_SCOPE", "REPLAY_KEY_CANONICAL_AND_CONSUMED", "Recovered replay keys are checked, consumed, and canonicalized or domain-separated in the supported subset.", where=where, facts=facts)


def _semantic_name(expression: str) -> str:
    names = [name for name in identifiers(expression) if name.lower() not in {"uint160", "uint256", "address", "bytes32"}]
    return names[-1].lower() if names else normalize_expression(expression).lower()


def analyze_p5(circuit: Circuit | None, verifier: Verifier | None, consumer: Consumer, *, ambiguous: bool) -> dict[str, Any]:
    where = location(consumer.source.relative_path, consumer.function.line)
    if ambiguous:
        return result("P5", "UNKNOWN", "VERIFIER_MATCH_AMBIGUOUS", "Multiple plausible verifier artifacts expose incompatible public-input shapes.", where=where)
    if verifier is None:
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
    if expected is not None and observed is not None and expected != observed:
        return result("P5", "VIOLATION", "PUBLIC_INPUT_COUNT_MISMATCH", f"Consumer supplies {observed} public inputs but the matched verifier expects {expected}.", where=where, facts=facts)
    if circuit.public_count is not None and observed is not None and circuit.public_count != observed:
        return result("P5", "VIOLATION", "PUBLIC_INPUT_COUNT_MISMATCH", f"Consumer supplies {observed} public inputs but the circuit exposes {circuit.public_count}.", where=where, facts=facts)
    if vector.items and circuit.public_order and len(vector.items) == len(circuit.public_order):
        observed_order = [_semantic_name(item) for item in vector.items]
        circuit_order = [_semantic_name(item) for item in circuit.public_order]
        if observed_order != circuit_order:
            return result("P5", "VIOLATION", "PUBLIC_INPUT_ORDER_MISMATCH", "Recovered consumer vector order differs from the circuit public-signal order.", where=where, facts=facts)
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
             "roles": [{"role": role, "expression": expression} for role, expression in effect_roles(call)]}
            for call in consumer.effect_calls
        ],
    }


def analyze(
    root: pathlib.Path,
    *,
    explicit_circuits: list[str] | None = None,
    explicit_consumers: list[str] | None = None,
    bundle: bool = False,
) -> dict[str, Any]:
    started_utc = dt.datetime.now(dt.UTC).isoformat()
    started = time.monotonic()
    config = load_config()
    budget = Budget(float(config["run_timeout_seconds"]))
    root = root.resolve()
    coverage: dict[str, Any] = {
        "files_inventoried": 0, "solidity_files_parsed": 0, "circuit_files_parsed": 0,
        "compiled_relations_built_or_loaded": 0, "skipped": [], "builds": [],
        "timeouts": [], "failures": [], "unsupported": [],
    }
    fatal: str | None = None
    triples_output: list[dict[str, Any]] = []
    runtime_results: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {
        "root": str(root), "mode": "verified-source-bundle" if bundle else "repository",
        "git_revision": _git_revision(root), "network_policy": "offline/no RPC",
        "explicit_circuits": explicit_circuits or [], "explicit_consumers": explicit_consumers or [],
    }
    try:
        if not root.is_dir():
            raise ValueError(f"analysis root is not a directory: {root}")
        files, skipped = inventory(root, config, budget)
        coverage["files_inventoried"] = len(files)
        coverage["skipped"].extend(skipped)
        if explicit_circuits:
            circuit_paths = [_safe_explicit(root, raw) for raw in explicit_circuits]
        else:
            circuit_paths = [path for path in files if path.suffix.lower() in {".circom", ".nr"}]
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
        circuits = discover_circuits(root, circuit_paths)
        coverage["circuit_files_parsed"] = len(circuits)
        for circuit in circuits[: int(config["max_circuit_builds"])]:
            if circuit.language == "circom":
                attach_or_build(circuit, root, budget, float(config["build_timeout_seconds"]))
                coverage["builds"].append({"path": circuit.relative_path, "record": circuit.build})
                if circuit.compiled:
                    coverage["compiled_relations_built_or_loaded"] += 1
                elif circuit.build and circuit.build.get("timed_out"):
                    coverage["timeouts"].append({"phase": "circom-build", "path": circuit.relative_path})
                elif circuit.build and circuit.build.get("exit_status") not in (None, 0):
                    coverage["failures"].append({"phase": "circom-build", "path": circuit.relative_path, "record": circuit.build})
        verifiers = [item for source in sources if (item := classify_verifier(source)) is not None]
        consumers = discover_consumers(sources)
        if explicit_consumer_paths:
            consumers = [item for item in consumers if item.source.path in explicit_consumer_paths]
        repository_solidity = "\n".join(source.text for source in sources)
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
                "P1": analyze_p1(circuit, verifier, consumer, repository_solidity),
                "P2": analyze_p2(circuit, consumer),
                "P3": analyze_p3(verifier, consumer),
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
    pattern_summary: dict[str, Any] = {}
    for pattern in PATTERNS:
        results = [triple["patterns"][pattern] for triple in triples_output]
        if not results:
            results = [result(pattern, "UNKNOWN", fatal or "NO_APPLICABLE_TRIPLE", "The pattern had no completed applicable triple.", grade="E0")]
        pattern_summary[pattern] = {**aggregate(results), "results": len(results), "reasons": sorted({item["reason"] for item in results})}
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
