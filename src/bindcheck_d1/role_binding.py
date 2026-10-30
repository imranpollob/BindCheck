"""Typed producer/consumer role correspondence over checked BindCheck facts.

The public entry point is :func:`analyze_role_binding`.  It consumes a
successful ``static_analyzer_v1.analyze`` result, reopens the exact checked
consumer relation named (and hashed) by that result, and supplements those
facts with bounded semantic facts extracted from the matching Noir source and
the explicitly supplied Noir support sources.

This is deliberately a separate rule module.  It neither imports nor changes a
frontend and it does not weaken analyzer fail-closed gates.  Callers must run
the analyzer first; if the analyzer cannot establish a public-input mapping,
there is no role result to compute.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "bindcheck.role-binding.v1"
RULE = "R-ROLE"


class RoleBindingUnsupported(ValueError):
    """The checked facts do not support a sound typed-role comparison."""


@dataclass(frozen=True)
class FunctionCall:
    name: str
    parameters: tuple[str, ...]
    arguments: tuple[str, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    raise RoleBindingUnsupported(f"UNBALANCED_SOURCE:{opening}{closing}@{start}")


def _split_top_level(value: str) -> list[str]:
    result: list[str] = []
    start = 0
    depths = {"(": 0, "[": 0, "{": 0, "<": 0}
    closing = {")": "(", "]": "[", "}": "{", ">": "<"}
    for index, character in enumerate(value):
        if character in depths:
            depths[character] += 1
        elif character in closing and depths[closing[character]]:
            depths[closing[character]] -= 1
        elif character == "," and not any(depths.values()):
            result.append(value[start:index].strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        result.append(tail)
    return result


def _function_declarations(text: str) -> dict[str, tuple[str, ...]]:
    declarations: dict[str, tuple[str, ...]] = {}
    pattern = re.compile(r"\b(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)[^({;]*\(")
    for match in pattern.finditer(text):
        opening = text.find("(", match.start())
        closing = _matching(text, opening, "(", ")")
        parameters = []
        for declaration in _split_top_level(text[opening + 1:closing]):
            parameter = declaration.split(":", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", parameter):
                parameters.append(parameter)
        declarations[match.group(1)] = tuple(parameters)
    return declarations


def _main_signature_and_body(text: str) -> tuple[tuple[str, ...], str]:
    match = re.search(r"\bfn\s+main[^({;]*\(", text)
    if not match:
        raise RoleBindingUnsupported("NO_NOIR_MAIN_FUNCTION")
    opening = text.find("(", match.start())
    closing = _matching(text, opening, "(", ")")
    public_parameters = []
    for declaration in _split_top_level(text[opening + 1:closing]):
        if re.search(r":\s*pub\b", declaration):
            name = declaration.split(":", 1)[0].strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                raise RoleBindingUnsupported(f"UNSUPPORTED_PUBLIC_PARAMETER:{name}")
            public_parameters.append(name)
    body_open = text.find("{", closing)
    if body_open < 0:
        raise RoleBindingUnsupported("NO_NOIR_MAIN_BODY")
    body_close = _matching(text, body_open, "{", "}")
    return tuple(public_parameters), text[body_open + 1:body_close]


def _calls(body: str, declarations: Mapping[str, tuple[str, ...]]) -> list[FunctionCall]:
    calls: list[FunctionCall] = []
    for name, parameters in declarations.items():
        pattern = re.compile(rf"\b{re.escape(name)}\s*(?:<[^;{{}}()]*>)?\s*\(")
        for match in pattern.finditer(body):
            opening = body.find("(", match.start())
            closing = _matching(body, opening, "(", ")")
            arguments = tuple(_split_top_level(body[opening + 1:closing]))
            if len(arguments) == len(parameters):
                calls.append(FunctionCall(name, parameters, arguments))
    return calls


def _tokens(value: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.findall(r"[a-z0-9]+", value.lower())


def canonical_role(value: str) -> str:
    """Return the bounded semantic role carried by an identifier/expression."""
    tokens = _tokens(value)
    token_set = set(tokens)
    if "nullifier" in token_set or "nullifiers" in token_set:
        return "replay:nullifier"
    if "recipient" in token_set or "beneficiary" in token_set:
        return "party:recipient"
    if "relayer" in token_set:
        return "party:relayer"
    if "max" in token_set and "fee" in token_set:
        return "value:max-fee"
    if "priority" in token_set and "fee" in token_set:
        return "value:priority-fee"
    if "fee" in token_set and "factor" in token_set:
        return "value:fee-factor"
    if "amount" in token_set:
        return "value:amount"
    if "chainid" in token_set or ("chain" in token_set and "id" in token_set):
        return "domain:chain"
    if "root" in token_set:
        if token_set.intersection({"giga", "global"}):
            return "state-root:giga"
        if "local" in token_set:
            return "state-root:local"
        return "state-root:unspecified"
    if "address" in token_set and token_set.intersection(
        {"app", "application", "contract", "warptoad", "aztec"}
    ):
        return "domain:application"
    if token_set.intersection({"domain", "application"}):
        return "domain:application"
    return "unknown"


def semantic_identity(value: str, role: str) -> list[str]:
    """Return stable identity atoms inside a typed state/domain role."""
    tokens = set(_tokens(value))
    if role == "state-root:giga":
        return ["giga"]
    if role == "state-root:local":
        return ["local"]
    if role == "domain:chain":
        return ["chain"]
    if role == "domain:application":
        generic = {
            "address", "app", "application", "calldata", "contract", "domain",
            "pre", "public", "storage",
        }
        return sorted(tokens - generic)
    return []


def _simple_identifier(value: str) -> str | None:
    value = value.strip()
    return value if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) else None


def _ir_symbols(value: Any, op: str = "symbol") -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        args = value.get("args", [])
        if value.get("op") == op and args and isinstance(args[0], str):
            result.add(args[0])
        for child in args:
            result.update(_ir_symbols(child, op))
    elif isinstance(value, list):
        for child in value:
            result.update(_ir_symbols(child, op))
    return result


def _const_bool(value: Any) -> bool | None:
    if not isinstance(value, dict) or value.get("op") != "const":
        return None
    args = value.get("args", [])
    return args[0] if args and isinstance(args[0], bool) else None


def _ir_bools(value: Any) -> set[bool]:
    result: set[bool] = set()
    if isinstance(value, dict):
        constant = _const_bool(value)
        if constant is not None:
            result.add(constant)
        for child in value.get("args", []):
            result.update(_ir_bools(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_ir_bools(child))
    return result


def _select(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict) or value.get("op") != "select":
        return None
    args = value.get("args", [])
    if len(args) < 2:
        return None
    storages = _ir_symbols(args[0], "storage")
    symbols = _ir_symbols(args[1], "symbol")
    if len(storages) == 1 and len(symbols) == 1:
        return next(iter(storages)), next(iter(symbols))
    return None


def _admission(value: Any) -> tuple[str, str, str] | None:
    selected = _select(value)
    if selected:
        return (*selected, "must-be-in")
    if not isinstance(value, dict):
        return None
    op = value.get("op")
    args = value.get("args", [])
    if op == "not" and len(args) == 1 and _select(args[0]):
        return (*_select(args[0]), "must-not-be-in")  # type: ignore[arg-type]
    if op in {"eq", "neq"} and len(args) == 2:
        for selected_value, constant_value in ((args[0], args[1]), (args[1], args[0])):
            selected = _select(selected_value)
            constant = _const_bool(constant_value)
            if selected is not None and constant is not None:
                present = constant if op == "eq" else not constant
                return (*selected, "must-be-in" if present else "must-not-be-in")
    return None


def _word_index(words: Sequence[Mapping[str, Any]], symbol: str) -> int | None:
    for word in words:
        if symbol == word.get("origin"):
            return int(word["index"])
    return None


def _successful_paths(relation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = [path for path in relation.get("paths", []) if path.get("status") == "success"]
    if not paths:
        raise RoleBindingUnsupported("NO_SUCCESS_PATH_IN_CHECKED_RELATION")
    return paths


def _relation_words(relation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    boundary = relation.get("verifier_boundary")
    if not isinstance(boundary, dict) or not isinstance(boundary.get("public_words"), list):
        raise RoleBindingUnsupported("RELATION_HAS_NO_TYPED_VERIFIER_BOUNDARY")
    return sorted(boundary["public_words"], key=lambda item: item["index"])


def _warning(
    warnings: list[dict[str, Any]],
    *,
    kind: str,
    location: str,
    explanation: str,
    suggested_fix: str,
    evidence: dict[str, Any],
    producer_sha256: str,
    consumer_sha256: str,
    confidence: str = "high",
) -> None:
    warnings.append({
        "id": f"ROLE{len(warnings) + 1:03d}",
        "rule": RULE,
        "severity": "warning",
        "confidence": confidence,
        "location": location,
        "explanation": explanation,
        "suggested_fix": suggested_fix,
        "evidence": {"kind": kind, **evidence},
        "target_identity": {
            "artifact_sha256": producer_sha256,
            "consumer_sha256": consumer_sha256,
            "rule": RULE,
        },
    })


def _producer_facts(
    public_leaves: Sequence[Mapping[str, Any]],
    source_text: str,
    support_texts: Iterable[str],
) -> tuple[list[dict[str, Any]], list[FunctionCall], set[tuple[str, str]]]:
    clean_source = _strip_comments(source_text)
    public_parameters, body = _main_signature_and_body(clean_source)
    leaf_names = tuple(str(leaf["path"]) for leaf in public_leaves)
    if any("[" in name or "." in name for name in leaf_names):
        raise RoleBindingUnsupported("ROLE_SOURCE_INTERFACE_SUPPORTS_SCALAR_PUBLIC_ABI_ONLY")
    if public_parameters != leaf_names:
        raise RoleBindingUnsupported(
            "PRODUCER_SOURCE_ARTIFACT_ABI_MISMATCH:"
            f"source={public_parameters!r}:artifact={leaf_names!r}"
        )
    declarations: dict[str, tuple[str, ...]] = {}
    for text in support_texts:
        declarations.update(_function_declarations(_strip_comments(text)))
    calls = _calls(body, declarations)
    index_by_name = {str(leaf["path"]): int(leaf["public_index"]) for leaf in public_leaves}
    facts = [{
        "public_index": int(leaf["public_index"]),
        "path": str(leaf["path"]),
        "boundary_role": canonical_role(str(leaf["path"])),
        "identity": semantic_identity(
            str(leaf["path"]), canonical_role(str(leaf["path"]))
        ),
        "computations": [],
    } for leaf in public_leaves]
    computation_pairs: set[tuple[str, str]] = set()
    for call in calls:
        call_arguments = dict(zip(call.parameters, call.arguments))
        tree_root_parameter = next(
            (parameter for parameter in call.parameters
             if canonical_role(parameter).startswith("state-root:")),
            None,
        )
        tree_root_argument = (
            _simple_identifier(call_arguments[tree_root_parameter])
            if tree_root_parameter is not None else None
        )
        for parameter, argument in zip(call.parameters, call.arguments):
            identifier = _simple_identifier(argument)
            if identifier not in index_by_name:
                continue
            index = index_by_name[identifier]
            parameter_role = canonical_role(parameter)
            relationship = "call-input"
            if "commitment" in call.name.lower():
                relationship = "commitment-input"
            elif parameter.lower() in {"leaf", "member", "value"} and "merkle" in call.name.lower():
                relationship = "tree-member"
            elif parameter_role.startswith("state-root:") and "merkle" in call.name.lower():
                relationship = "tree-root"
            elif parameter_role.startswith("domain:"):
                relationship = "domain-input"
            facts[index]["computations"].append({
                "operation": call.name,
                "parameter": parameter,
                "parameter_role": parameter_role,
                "argument": identifier,
                "relationship": relationship,
                "tree_root": tree_root_argument if relationship == "tree-member" else None,
            })
            computation_pairs.add((call.name, parameter_role))

    # Record public words equated to a named output of a semantic computation,
    # such as ``_nullifier == nullifier`` after destructuring a commitment call.
    produced_locals: dict[str, dict[str, Any]] = {}
    for match in re.finditer(
        r"\blet\s*\(([^)]*)\)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", body
    ):
        operation = match.group(2)
        call_open = body.find("(", match.start(2) + len(operation))
        call_close = _matching(body, call_open, "(", ")")
        computation_inputs = _split_top_level(body[call_open + 1:call_close])
        for output_index, local in enumerate(_split_top_level(match.group(1))):
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", local):
                produced_locals[local] = {
                    "operation": operation,
                    "output_index": output_index,
                    "computation_inputs": computation_inputs,
                }
    for left, right in re.findall(
        r"\bassert\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*==\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)", body
    ):
        for public_name, local_name in ((left, right), (right, left)):
            if public_name in index_by_name and local_name in produced_locals:
                facts[index_by_name[public_name]]["computations"].append({
                    **produced_locals[local_name],
                    "relationship": "computed-output-equality",
                    "local_output": local_name,
                    "argument": public_name,
                })

    # Preserve explicit public guards and root-equality branch roles even when
    # they are not function-call arguments.
    for match in re.finditer(r"\bassert\s*\(", body):
        assert_open = body.find("(", match.start())
        assert_close = _matching(body, assert_open, "(", ")")
        arguments = _split_top_level(body[assert_open + 1:assert_close])
        expression = arguments[0] if arguments else ""
        for name, index in index_by_name.items():
            if not re.search(rf"\b{re.escape(name)}\b", expression):
                continue
            guard_fact = {
                "relationship": "constraint-guard",
                "argument": name,
                "expression": expression,
            }
            if guard_fact not in facts[index]["computations"]:
                facts[index]["computations"].append(guard_fact)
    for left, right in re.findall(
        r"\bif\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*==\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*\)", body
    ):
        for public_name, alternate in ((left, right), (right, left)):
            if public_name in index_by_name:
                facts[index_by_name[public_name]]["computations"].append({
                    "relationship": "state-equality-branch",
                    "argument": public_name,
                    "alternate": alternate,
                    "alternate_role": canonical_role(alternate),
                })
    return facts, calls, computation_pairs


def analyze_role_binding(
    analysis: Mapping[str, Any],
    *,
    producer_source: Path,
    producer_support_sources: Sequence[Path] = (),
) -> dict[str, Any]:
    """Infer typed roles and return correspondence warnings.

    Preconditions are intentionally strict:

    * ``analysis`` is a successful current static-analyzer result;
    * its consumer is an extracted checked relation;
    * the relation on disk still has the hash recorded in ``analysis``;
    * the Noir source public declaration agrees exactly with the decoded
      scalar producer ABI; and
    * the relation has an explicit verifier boundary and successful paths.

    ``RoleBindingUnsupported`` means the role result is ``UNKNOWN``.  It must
    never be converted to a no-warning result.
    """
    if not str(analysis.get("schema", "")).startswith("bindcheck.static-analysis.v1."):
        raise RoleBindingUnsupported(f"UNSUPPORTED_ANALYSIS_SCHEMA:{analysis.get('schema')}")
    producer = analysis.get("producer", {})
    consumer = analysis.get("consumer", {})
    if consumer.get("kind") != "extracted-relation":
        raise RoleBindingUnsupported("CHECKED_EXTRACTED_RELATION_REQUIRED")
    relation_path = Path(str(consumer.get("relation", ""))).resolve()
    if not relation_path.is_file():
        raise RoleBindingUnsupported(f"CHECKED_RELATION_MISSING:{relation_path}")
    if _sha256(relation_path) != consumer.get("relation_sha256"):
        raise RoleBindingUnsupported("CHECKED_RELATION_HASH_MISMATCH")
    producer_source = producer_source.resolve()
    if not producer_source.is_file():
        raise RoleBindingUnsupported(f"PRODUCER_SOURCE_MISSING:{producer_source}")
    support_sources = [path.resolve() for path in producer_support_sources]
    for path in support_sources:
        if not path.is_file():
            raise RoleBindingUnsupported(f"PRODUCER_SUPPORT_SOURCE_MISSING:{path}")

    relation = json.loads(relation_path.read_text())
    relation_words = _relation_words(relation)
    normalized_words = consumer.get("public_words", [])
    public_leaves = producer.get("public_leaves", [])
    if not (len(relation_words) == len(normalized_words) == len(public_leaves)):
        raise RoleBindingUnsupported(
            "ROLE_WORD_WIDTH_MISMATCH:"
            f"relation={len(relation_words)}:consumer={len(normalized_words)}:"
            f"producer={len(public_leaves)}"
        )
    for relation_word, normalized_word in zip(relation_words, normalized_words):
        if (relation_word.get("index"), relation_word.get("origin")) != (
            normalized_word.get("index"), normalized_word.get("origin")
        ):
            raise RoleBindingUnsupported("ROLE_RELATION_NORMALIZATION_MISMATCH")

    producer_facts, calls, computation_pairs = _producer_facts(
        public_leaves,
        producer_source.read_text(),
        [path.read_text() for path in support_sources],
    )
    success_paths = _successful_paths(relation)
    consumer_facts = [{
        "public_index": int(word["index"]),
        "origin": str(word["origin"]),
        "boundary_role": canonical_role(str(word["origin"])),
        "identity": semantic_identity(
            str(word["origin"]), canonical_role(str(word["origin"]))
        ),
        "guards": [],
        "state_checks": [],
        "effects": [],
    } for word in relation_words]
    warnings: list[dict[str, Any]] = []
    verifier_location = str(consumer.get("verifier_location") or relation.get("scope") or relation_path.name)
    producer_hash = str(producer.get("sha256"))
    consumer_hash = str(consumer.get("source_sha256"))

    # Boundary position correspondence.
    for producer_word, consumer_word in zip(producer_facts, consumer_facts):
        producer_role = producer_word["boundary_role"]
        consumer_role = consumer_word["boundary_role"]
        if producer_role != "unknown" and consumer_role != "unknown" and producer_role != consumer_role:
            index = producer_word["public_index"]
            _warning(
                warnings,
                kind="boundary-role",
                location=verifier_location,
                explanation=(
                    f"Verifier word {index} is {producer_role} in the producer ABI but "
                    f"{consumer_role} at the consumer verifier boundary."
                ),
                suggested_fix="Use the same typed word order on both sides and rebuild the circuit, key, and verifier together.",
                evidence={
                    "public_index": index,
                    "public_indices": [index],
                    "producer_path": producer_word["path"],
                    "producer_role": producer_role,
                    "consumer_origin": consumer_word["origin"],
                    "consumer_role": consumer_role,
                },
                producer_sha256=producer_hash,
                consumer_sha256=consumer_hash,
            )
        elif producer_role.startswith("domain:") and producer_role == consumer_role:
            producer_identity = set(producer_word["identity"])
            consumer_identity = set(consumer_word["identity"])
            if (producer_identity and consumer_identity
                    and producer_identity.isdisjoint(consumer_identity)):
                index = producer_word["public_index"]
                _warning(
                    warnings,
                    kind="domain-identity",
                    location=verifier_location,
                    explanation=(
                        f"Verifier word {index} is typed {producer_role} on both sides, but "
                        f"producer identity {sorted(producer_identity)} does not correspond to "
                        f"consumer identity {sorted(consumer_identity)}."
                    ),
                    suggested_fix="Bind and check the same application or chain domain identity on both sides.",
                    evidence={
                        "public_index": index,
                        "public_indices": [index],
                        "producer_path": producer_word["path"],
                        "producer_role": producer_role,
                        "producer_identity": sorted(producer_identity),
                        "consumer_origin": consumer_word["origin"],
                        "consumer_role": consumer_role,
                        "consumer_identity": sorted(consumer_identity),
                    },
                    producer_sha256=producer_hash,
                    consumer_sha256=consumer_hash,
                )

    # Consumer state identity and admission polarity, path by path.
    admissions: dict[int, set[tuple[str, str, str]]] = {}
    path_admissions: dict[int, set[str]] = {}
    for path in success_paths:
        authorized_effects = sorted({
            (
                kind[:-1],
                str(effect.get("location")),
            )
            for kind in ("mints", "transfers", "burns")
            for effect in path.get("committed", {}).get(kind, [])
        })
        raw_guards = path.get("guards", [])
        for guard_index, guard in enumerate(path.get("guards_ir", [])):
            if guard.get("op") != "relation":
                for symbol in sorted(_ir_symbols(guard, "symbol")):
                    index = _word_index(relation_words, symbol)
                    if index is None:
                        continue
                    guard_fact = {
                        "operation": guard.get("op"),
                        "expression": (
                            raw_guards[guard_index]
                            if guard_index < len(raw_guards) else None
                        ),
                        "path": str(path.get("id")),
                        "authorizes_effects": [
                            {"kind": kind, "location": location}
                            for kind, location in authorized_effects
                        ],
                    }
                    if guard_fact not in consumer_facts[index]["guards"]:
                        consumer_facts[index]["guards"].append(guard_fact)
            admission = _admission(guard)
            if not admission:
                continue
            storage, symbol, polarity = admission
            index = _word_index(relation_words, symbol)
            if index is None:
                continue
            admissions.setdefault(index, set()).add((storage, symbol, polarity))
            path_admissions.setdefault(index, set()).add(str(path.get("id")))
    for index, relationships in admissions.items():
        role = consumer_facts[index]["boundary_role"]
        expected_polarity = (
            "must-not-be-in" if role == "replay:nullifier"
            else "must-be-in" if role.startswith("state-root:")
            else None
        )
        for storage, symbol, polarity in sorted(relationships):
            state_role = canonical_role(storage)
            item = {
                "storage_identity": storage,
                "state_role": state_role,
                "polarity": polarity,
                "paths": sorted(path_admissions.get(index, set())),
            }
            consumer_facts[index]["state_checks"].append(item)
            if (role.startswith("state-root:") and state_role.startswith("state-root:")
                    and role != state_role):
                _warning(
                    warnings,
                    kind="state-identity",
                    location=verifier_location,
                    explanation=(
                        f"Verifier word {index} has role {role} but successful admission checks "
                        f"state identity {storage} ({state_role})."
                    ),
                    suggested_fix="Check each authenticated root against the state set with the same typed identity.",
                    evidence={
                        "public_index": index,
                        "public_indices": [index],
                        "consumer_origin": symbol,
                        "word_role": role,
                        "storage_identity": storage,
                        "storage_role": state_role,
                        "polarity": polarity,
                    },
                    producer_sha256=producer_hash,
                    consumer_sha256=consumer_hash,
                )
            if expected_polarity is not None and polarity != expected_polarity:
                _warning(
                    warnings,
                    kind="polarity",
                    location=verifier_location,
                    explanation=(
                        f"Verifier word {index} has role {role}, which requires {expected_polarity}, "
                        f"but the successful path uses {polarity}."
                    ),
                    suggested_fix="Use presence admission for roots and absence-plus-success-write admission for replay keys.",
                    evidence={
                        "public_index": index,
                        "public_indices": [index],
                        "word_role": role,
                        "storage_identity": storage,
                        "expected_polarity": expected_polarity,
                        "observed_polarity": polarity,
                    },
                    producer_sha256=producer_hash,
                    consumer_sha256=consumer_hash,
                )

    # A nullifier role also requires a matching true write on every success path.
    for word in consumer_facts:
        if word["boundary_role"] != "replay:nullifier":
            continue
        index = word["public_index"]
        origin = word["origin"]
        missing_paths = []
        for path in success_paths:
            writes = path.get("committed", {}).get("storage_writes", [])
            matched = any(
                canonical_role(str(write.get("slot", ""))) == "replay:nullifier"
                and origin in _ir_symbols(write.get("map_after_ir", {}), "symbol")
                and True in _ir_bools(write.get("value_ir", {}))
                for write in writes
            )
            # Boolean constants are not symbols; inspect the explicit normalized value too.
            if not matched:
                matched = any(
                    canonical_role(str(write.get("slot", ""))) == "replay:nullifier"
                    and origin in _ir_symbols(write.get("map_after_ir", {}), "symbol")
                    and (write.get("value") is True or str(write.get("value")).lower() == "true")
                    for write in writes
                )
            if not matched:
                missing_paths.append(str(path.get("id")))
        if missing_paths and index in admissions:
            _warning(
                warnings,
                kind="polarity",
                location=verifier_location,
                explanation=(
                    f"Replay word {index} is checked for absence but is not written true on "
                    f"successful path(s) {', '.join(missing_paths)}."
                ),
                suggested_fix="Atomically write the same authenticated replay key after successful verification.",
                evidence={
                    "public_index": index,
                    "public_indices": [index],
                    "word_role": "replay:nullifier",
                    "expected_polarity": "must-not-be-in-and-write",
                    "observed_polarity": "missing-success-write",
                    "missing_success_paths": missing_paths,
                },
                producer_sha256=producer_hash,
                consumer_sha256=consumer_hash,
            )

    # Producer tree membership typed against branch equality.  If an else-path
    # membership authenticates the public side of a public/private root
    # equality rather than the alternate root, its producer state role does not
    # correspond to the consumer's admitted state identity.
    source_body = _main_signature_and_body(_strip_comments(producer_source.read_text()))[1]
    equality_pairs = {
        frozenset((left, right))
        for left, right in re.findall(
            r"\bif\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*==\s*"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\)",
            source_body,
        )
    }
    index_by_path = {str(item["path"]): int(item["public_index"]) for item in producer_facts}
    for call in calls:
        if "merkle" not in call.name.lower():
            continue
        arguments = dict(zip(call.parameters, call.arguments))
        root_parameter = next((name for name in call.parameters if canonical_role(name).startswith("state-root:")), None)
        leaf_parameter = next((name for name in call.parameters if name.lower() in {"leaf", "member", "value"}), None)
        if root_parameter is None or leaf_parameter is None:
            continue
        root = _simple_identifier(arguments[root_parameter])
        leaf = _simple_identifier(arguments[leaf_parameter])
        if root is None or leaf not in index_by_path:
            continue
        alternate = None
        for pair in equality_pairs:
            if leaf in pair:
                candidate = next(iter(pair - {leaf}), None)
                if candidate and canonical_role(candidate) == canonical_role(leaf):
                    alternate = candidate
                    break
        if alternate is None:
            continue
        index = index_by_path[leaf]
        _warning(
            warnings,
            kind="producer-state-membership",
            location=producer_source.name,
            explanation=(
                f"Producer word {index} ({leaf}) is used as the {call.name} member under {root}, "
                f"although the branch distinguishes it from alternate root {alternate}."
            ),
            suggested_fix="Authenticate the branch's origin/member root and keep the consumer-admitted destination root in its distinct state role.",
            evidence={
                "public_index": index,
                "public_indices": [index],
                "producer_path": leaf,
                "operation": call.name,
                "tree_root": root,
                "observed_member": leaf,
                "expected_alternate_member": alternate,
            },
            producer_sha256=producer_hash,
            consumer_sha256=consumer_hash,
        )

    # Effects: amount-bearing mints are principal effects; the authenticated
    # recipient authorizes their beneficiary, and their amount must be part of
    # a producer commitment computation when that computation is available.
    effect_keys: set[tuple[str, str, str, str]] = set()
    effects: list[Mapping[str, Any]] = []
    for path in success_paths:
        for kind in ("mints", "transfers", "burns"):
            for effect in path.get("committed", {}).get(kind, []):
                key = (
                    kind,
                    str(effect.get("location")),
                    str(effect.get("amount")),
                    str(effect.get("beneficiary")),
                )
                if key not in effect_keys:
                    effect_keys.add(key)
                    effects.append({"kind": kind[:-1], **effect})
    recipient_indices = [
        word["public_index"] for word in consumer_facts
        if word["boundary_role"] == "party:recipient"
    ]
    commitment_amount_supported = any(
        "commitment" in call.name.lower()
        and any(canonical_role(parameter) == "value:amount" for parameter in call.parameters)
        for call in calls
    )
    warned_amount_indices: set[int] = set()
    for effect in effects:
        amount_symbols = _ir_symbols(effect.get("amount_ir", {}), "symbol")
        beneficiary_symbols = _ir_symbols(effect.get("beneficiary_ir", {}), "symbol")
        for dependency_role, symbols in (
            ("amount-operand", amount_symbols),
            ("beneficiary-operand", beneficiary_symbols),
        ):
            for symbol in sorted(symbols):
                dependency_index = _word_index(relation_words, symbol)
                if dependency_index is None:
                    continue
                dependency = {
                    "kind": effect.get("kind"),
                    "location": effect.get("location"),
                    "role": dependency_role,
                    "expression": (
                        effect.get("amount") if dependency_role == "amount-operand"
                        else effect.get("beneficiary")
                    ),
                }
                if dependency not in consumer_facts[dependency_index]["effects"]:
                    consumer_facts[dependency_index]["effects"].append(dependency)
        amount_indices = sorted({
            index for symbol in amount_symbols
            if (index := _word_index(relation_words, symbol)) is not None
            and consumer_facts[index]["boundary_role"] == "value:amount"
        })
        if not amount_indices:
            continue
        beneficiary_indices = sorted({
            index for symbol in beneficiary_symbols
            if (index := _word_index(relation_words, symbol)) is not None
        })
        for index in amount_indices:
            principal_dependency = {
                "kind": effect.get("kind"),
                "location": effect.get("location"),
                "role": "principal-amount",
            }
            if principal_dependency not in consumer_facts[index]["effects"]:
                consumer_facts[index]["effects"].append(principal_dependency)
            producer_has_authorization = any(
                "commitment" in str(computation.get("operation", "")).lower()
                and computation.get("parameter_role") == "value:amount"
                for computation in producer_facts[index]["computations"]
            )
            if (commitment_amount_supported and not producer_has_authorization
                    and index not in warned_amount_indices):
                warned_amount_indices.add(index)
                _warning(
                    warnings,
                    kind="effect-authorization",
                    location=str(effect.get("location") or verifier_location),
                    explanation=(
                        f"Consumer word {index} controls a principal {effect.get('kind')} amount, "
                        "but that verifier position is not the producer commitment's amount input."
                    ),
                    suggested_fix="Bind the same public amount into the note commitment that authorizes the principal effect.",
                    evidence={
                        "public_index": index,
                        "public_indices": [index],
                        "word_role": "value:amount",
                        "effect_kind": effect.get("kind"),
                        "effect_location": effect.get("location"),
                        "producer_computations": producer_facts[index]["computations"],
                    },
                    producer_sha256=producer_hash,
                    consumer_sha256=consumer_hash,
                )
        beneficiary_roles = {consumer_facts[index]["boundary_role"] for index in beneficiary_indices}
        if recipient_indices and "party:recipient" not in beneficiary_roles:
            related_indices = sorted(set(amount_indices + beneficiary_indices + recipient_indices))
            _warning(
                warnings,
                kind="effect-beneficiary",
                location=str(effect.get("location") or verifier_location),
                explanation=(
                    f"Principal {effect.get('kind')} beneficiary {effect.get('beneficiary')} is not "
                    "the authenticated recipient role."
                ),
                suggested_fix="Direct the principal effect to the proof-bound recipient; reserve relayer/sender roles for explicitly authorized fees.",
                evidence={
                    "public_indices": related_indices,
                    "amount_public_indices": amount_indices,
                    "beneficiary_public_indices": beneficiary_indices,
                    "expected_recipient_public_indices": recipient_indices,
                    "effect_kind": effect.get("kind"),
                    "effect_location": effect.get("location"),
                    "observed_beneficiary": effect.get("beneficiary"),
                    "observed_beneficiary_roles": sorted(beneficiary_roles),
                    "expected_beneficiary_role": "party:recipient",
                },
                producer_sha256=producer_hash,
                consumer_sha256=consumer_hash,
            )

    return {
        "schema": SCHEMA,
        "status": "SUPPORTED",
        "rule": RULE,
        "interface": {
            "analysis_schema": analysis.get("schema"),
            "producer_source": str(producer_source),
            "producer_source_sha256": _sha256(producer_source),
            "producer_support_sources": [
                {"path": str(path), "sha256": _sha256(path)} for path in support_sources
            ],
            "checked_relation": str(relation_path),
            "checked_relation_sha256": _sha256(relation_path),
        },
        "words": [
            {
                "public_index": producer_word["public_index"],
                "producer": producer_word,
                "consumer": consumer_word,
                "boundary_correspondence": (
                    "match" if producer_word["boundary_role"] == consumer_word["boundary_role"]
                    else "unknown" if "unknown" in {
                        producer_word["boundary_role"], consumer_word["boundary_role"]
                    }
                    else "mismatch"
                ),
            }
            for producer_word, consumer_word in zip(producer_facts, consumer_facts)
        ],
        "warnings": warnings,
        "warning_count": len(warnings),
        "limitations": [
            "Identifier-derived role vocabulary is bounded and may return unknown; unknown roles never produce a mismatch warning.",
            "Producer computation roles require exact scalar ABI/source agreement and explicitly supplied support-function signatures.",
            "Consumer roles are limited to the checked relation's verifier boundary, success guards, committed state writes, and modeled effects.",
            "R-ROLE is an E1 diagnostic and does not establish reachability, exploitability, or a VIOLATION verdict.",
        ],
    }
