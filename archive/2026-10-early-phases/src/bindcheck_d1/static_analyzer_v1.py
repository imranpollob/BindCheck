"""BindCheck v1.4-dev cross-layer static analyzer.

The rule engine is deliberately application-neutral.  It joins flattened
producer ABI leaves and ACIR witness use with either an extracted consumer
relation or a conservative Solidity source profile.  Target-specific paths
are inputs to the CLI, never conditions in these rules.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from .frontends import acir_binary_beta15_21, acir_binary_beta22, acir_binary_v1
from .frontends.recursive_public_mapping_v1 import verify_certificate as verify_mapping_certificate


SCHEMA = "bindcheck.static-analysis.v1.4-dev"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expression_witnesses(expr: dict[str, Any]) -> list[int]:
    result: list[int] = []
    for _coefficient, lhs, rhs in expr.get("mul", []):
        result.extend((lhs, rhs))
    for _coefficient, witness in expr.get("linear", []):
        result.append(witness)
    return result


def _nested_witnesses(value: Any, parent: str | None = None) -> list[int]:
    """Decode witness-bearing fields without mistaking metadata for witnesses."""
    result: list[int] = []
    if isinstance(value, dict):
        if set(value) == {"witness"}:
            result.append(value["witness"])
            return result
        if "mul" in value and "linear" in value and "constant" in value:
            return _expression_witnesses(value)
        for key, child in value.items():
            if key not in {"opcode_index", "byte_range", "block_id", "id", "num_bits",
                           "proof_type", "block_type", "call_data_id"}:
                result.extend(_nested_witnesses(child, key))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, int) and not isinstance(child, bool) and parent in {
                "outputs", "output", "init", "array", "simple", "single", "memory_array"
            }:
                result.append(child)
            else:
                result.extend(_nested_witnesses(child, parent))
    elif isinstance(value, int) and not isinstance(value, bool) and parent in {
        "outputs", "output", "init", "array", "simple", "single", "memory_array", "index", "value"
    }:
        result.append(value)
    return result


def _opcode_witnesses(opcode: dict[str, Any]) -> tuple[list[int], list[int], list[int]]:
    """Return (proof-enforced, witness-generation, memory-definition) uses."""
    kind = opcode["kind"]
    if kind == "AssertZero":
        return _expression_witnesses(opcode["expression"]), [], []
    if kind == "BrilligCall":
        # ACIR constrains downstream uses of Brillig outputs, but the call is a
        # witness generator.  Inventory both inputs and outputs without using
        # the call itself to discharge a public-input binding obligation.
        values = []
        for key in ("inputs", "outputs", "predicate"):
            values.extend(_nested_witnesses(opcode.get(key), key))
        return [], values, []
    if kind == "MemoryInit":
        # Defining a memory cell is not, alone, a constraint on that value.
        # MemoryOp address/value expressions are counted below when the block
        # is actually used.
        return [], [], list(opcode.get("init", []))
    return _nested_witnesses(opcode), [], []


def _constant_expression(value: Any) -> int | None:
    """Return an exact ACIR expression constant, or ``None`` if it has witnesses."""
    if isinstance(value, int) and not isinstance(value, bool):
        return None  # beta.22 MemoryOp integers are witness identifiers.
    if not isinstance(value, dict) or "mul" not in value or "linear" not in value:
        return None
    if value.get("mul") or value.get("linear"):
        return None
    constant = value.get("constant")
    return constant if isinstance(constant, int) and not isinstance(constant, bool) else None


def _memory_dependency_facts(opcodes: list[dict[str, Any]]) -> tuple[Counter[int], set[int]]:
    """Recover exact MemoryInit dependencies and flag unresolved dynamic ones.

    A constant-address read has an exact dependency on the current cell.  A
    dynamic read may select any current cell; without proving its address
    range, counting every initializer as used or every initializer as unused
    would both be unsound.  Those witnesses are therefore returned as
    unresolved and force the caller to fail closed when no other occurrence
    establishes their use.
    """
    blocks: dict[int, list[set[int]]] = {}
    tainted_blocks: set[int] = set()
    exact: Counter[int] = Counter()
    unresolved: set[int] = set()
    for opcode in opcodes:
        kind = opcode["kind"]
        block_id = opcode.get("block_id")
        if kind == "MemoryInit":
            blocks[block_id] = [{witness} for witness in opcode.get("init", [])]
            continue
        if kind != "MemoryOp" or block_id not in blocks:
            continue
        operation = opcode.get("operation")
        if isinstance(operation, str):
            operation_kind = operation
        else:
            operation_constant = _constant_expression(operation)
            operation_kind = "read" if operation_constant == 0 else (
                "write" if operation_constant == 1 else "unknown"
            )
        cells = blocks[block_id]
        index = _constant_expression(opcode.get("index"))
        value_witnesses = set(_nested_witnesses(opcode.get("value"), "value"))
        if operation_kind == "read":
            if index is not None and 0 <= index < len(cells) and block_id not in tainted_blocks:
                exact.update(cells[index])
            elif index is not None and 0 <= index < len(cells):
                unresolved.update(cells[index])
            else:
                for cell in cells:
                    unresolved.update(cell)
        elif operation_kind == "write":
            if index is not None and 0 <= index < len(cells):
                cells[index] = value_witnesses
            else:
                # A dynamic write may replace any cell.  Preserve both the old
                # and new dependencies and mark the selection unresolved.
                prior = set().union(*cells) if cells else set()
                unresolved.update(prior | value_witnesses)
                replacement = prior | value_witnesses
                blocks[block_id] = [set(replacement) for _ in cells]
                tainted_blocks.add(block_id)
        else:
            unresolved.update(set().union(*cells) if cells else set())
            unresolved.update(value_witnesses)
            tainted_blocks.add(block_id)
    return exact, unresolved


def _leaf_bindings(abi: dict[str, Any], bindings: dict[str, list[int]]) -> list[dict[str, Any]]:
    """Return scalar ABI paths in declaration order."""
    leaves: list[dict[str, Any]] = []

    def visit(typ: dict[str, Any], name: str, visibility: str) -> None:
        kind = typ["kind"]
        if kind in {"field", "integer", "boolean"}:
            leaves.append({"path": name, "visibility": visibility, "witness": bindings[name][0]})
        elif kind == "array":
            for index in range(typ["length"]):
                visit(typ["type"], f"{name}[{index}]", visibility)
        elif kind == "struct":
            for field in typ["fields"]:
                visit(field["type"], f"{name}.{field['name']}", visibility)
        else:
            raise ValueError(f"unsupported ABI type after decoder gate: {kind}")

    for parameter in abi["parameters"]:
        visit(parameter["type"], parameter["name"], parameter["visibility"])
    return leaves


def _canonical_symbol(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _line_for(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _producer_extent_profiles(source_path: Path | None, public_leaves: list[dict[str, Any]],
                              circuit: dict[str, Any],
                              bindings: dict[str, list[int]]) -> dict[str, dict[str, Any]]:
    """Extract two bounded Noir prefix idioms and check their ACIR memory shape.

    The recognized forms are (1) a loop-index prefix guard around an array
    assertion and (2) a monotonically incremented dynamic array address used
    by an equality assertion.  Any near miss remains UNKNOWN.
    """
    if source_path is None:
        return {}
    source = source_path.read_text()
    groups: dict[str, list[dict[str, Any]]] = {}
    for leaf in public_leaves:
        match = re.match(r"^(.*)\[(\d+)\]$", leaf["path"])
        if match:
            groups.setdefault(match.group(1), []).append(leaf)
    profiles: dict[str, dict[str, Any]] = {}
    for base, leaves in groups.items():
        short = base.rsplit(".", 1)[-1]
        escaped = re.escape(short)
        guarded = re.search(
            rf"if\s+([A-Za-z_]\w*)\s*<\s*([A-Za-z_]\w*)\s*\{{[\s\S]{{0,500}}?"
            rf"assert\s*\([^;]*\b{escaped}\s*\[\s*\1\s*\]",
            source,
        )
        dynamic = re.search(
            rf"(?:let\s+mut\s+)?([A-Za-z_]\w*)\s*=\s*0\s*;[\s\S]*?"
            rf"assert\s*\([^;]*\b{escaped}\s*\[\s*\1\s*\][^;]*\)\s*;"
            rf"[\s\S]{{0,180}}?\b\1\s*\+=\s*1\s*;",
            source,
        )
        tail = None
        if dynamic:
            counter = dynamic.group(1)
            tail = re.search(
                rf"if\s+([A-Za-z_]\w*)\s*>=\s*{re.escape(counter)}\s*\{{"
                rf"[\s\S]{{0,240}}?assert\s*\(\s*{escaped}\s*\[\s*\1\s*\]\s*==\s*0",
                source,
            )

        evidence: dict[str, Any] = {"source_sha256": sha256(source_path)}
        if dynamic:
            witnesses = set(bindings.get(base, []))
            memory_blocks = [opcode for opcode in circuit["opcodes"]
                             if opcode["kind"] == "MemoryInit"
                             and set(opcode.get("init", [])) == witnesses]
            if len(memory_blocks) != 1:
                profiles[base] = {"status": "UNKNOWN", "condition": {"kind": "unknown",
                    "reason": "PRODUCER_EXTENT_MEMORY_BLOCK_UNRESOLVED"}, "evidence": evidence}
                continue
            block_id = memory_blocks[0]["block_id"]
            operations = [opcode for opcode in circuit["opcodes"]
                          if opcode["kind"] == "MemoryOp" and opcode.get("block_id") == block_id]
            reads = [opcode for opcode in operations if _constant_expression(opcode["operation"]) == 0]
            writes = [opcode for opcode in operations if _constant_expression(opcode["operation"]) != 0]
            if not reads or writes:
                profiles[base] = {"status": "UNKNOWN", "condition": {"kind": "unknown",
                    "reason": "PRODUCER_EXTENT_MEMORY_ACCESS_UNRESOLVED"}, "evidence": evidence}
                continue
            evidence.update({"source_location": f"{source_path.name}:{_line_for(source, dynamic.start())}",
                             "memory_block": block_id, "dynamic_read_count": len(reads),
                             "dynamic_write_count": len(writes)})
            if tail:
                profiles[base] = {"status": "EXACT", "condition": {"kind": "always"},
                                  "evidence": evidence | {"tail_zero": True}}
            else:
                profiles[base] = {
                    "status": "EXACT",
                    "condition": {"kind": "prefix", "word_offset": "word_offset",
                                  "extent": f"active_{_canonical_symbol(short)}_count",
                                  "array_offset": 0, "limit_offset": 0},
                    "evidence": evidence | {"tail_zero": False},
                }
        elif guarded:
            profiles[base] = {
                "status": "EXACT",
                "condition": {"kind": "prefix", "word_offset": "word_offset",
                              "extent": _canonical_symbol(guarded.group(2)),
                              "array_offset": 0, "limit_offset": 0},
                "evidence": evidence | {
                    "source_location": f"{source_path.name}:{_line_for(source, guarded.start())}",
                    "guard_index": guarded.group(1),
                },
            }
    return profiles


def load_producer(path: Path, source_path: Path | None = None) -> dict[str, Any]:
    artifact = json.loads(path.read_text())
    version = artifact.get("noir_version", "")
    if version == acir_binary_beta22.VERSION:
        decoder = acir_binary_beta22
        decoder_name = "beta.22-msgpack"
    elif version in acir_binary_beta15_21.VERSIONS:
        decoder = acir_binary_beta15_21
        decoder_name = acir_binary_beta15_21.VERSIONS[version]
    elif version == acir_binary_v1.VERSION:
        decoder = acir_binary_v1
        decoder_name = "beta.14-bincode"
    else:
        raise ValueError(f"unsupported Noir compiler: {version!r}")

    decoded = decoder.decode(path)
    circuit = decoded["functions"][0]
    bindings = decoder.abi_bindings(decoded["abi"], circuit)
    occurrences: Counter[int] = Counter()
    witness_generation_occurrences: Counter[int] = Counter()
    memory_definition_occurrences: Counter[int] = Counter()
    locations: dict[int, list[str]] = {}
    witness_generation_locations: dict[int, list[str]] = {}
    memory_definition_locations: dict[int, list[str]] = {}
    kinds: Counter[str] = Counter()
    for ordinal, opcode in enumerate(circuit["opcodes"]):
        kind = opcode["kind"]
        kinds[kind] += 1
        witnesses, witness_generation, memory_definitions = _opcode_witnesses(opcode)
        for witness in witnesses:
            occurrences[witness] += 1
            if len(locations.setdefault(witness, [])) < 8:
                locations[witness].append(f"opcode[{opcode.get('opcode_index', ordinal)}]/{kind}")
        for witness in witness_generation:
            witness_generation_occurrences[witness] += 1
            if len(witness_generation_locations.setdefault(witness, [])) < 8:
                witness_generation_locations[witness].append(
                    f"opcode[{opcode.get('opcode_index', ordinal)}]/{kind}"
                )
        for witness in memory_definitions:
            memory_definition_occurrences[witness] += 1
            if len(memory_definition_locations.setdefault(witness, [])) < 8:
                memory_definition_locations[witness].append(
                    f"opcode[{opcode.get('opcode_index', ordinal)}]/{kind}"
                )

    exact_memory_occurrences, unresolved_memory_witnesses = _memory_dependency_facts(
        circuit["opcodes"]
    )
    for witness, count in exact_memory_occurrences.items():
        occurrences[witness] += count
        if len(locations.setdefault(witness, [])) < 8:
            locations[witness].append("memory/exact-constant-read")

    leaves = _leaf_bindings(decoded["abi"], bindings)
    public_leaves = []
    for public_index, leaf in enumerate(item for item in leaves if item["visibility"] == "public"):
        leaf = dict(leaf)
        leaf.update({
            "public_index": public_index,
            "occurrence_count": occurrences[leaf["witness"]],
            "occurrence_locations": locations.get(leaf["witness"], []),
            "witness_generation_occurrence_count": witness_generation_occurrences[leaf["witness"]],
            "witness_generation_occurrence_locations": witness_generation_locations.get(
                leaf["witness"], []
            ),
            "memory_definition_occurrence_count": memory_definition_occurrences[leaf["witness"]],
            "memory_definition_occurrence_locations": memory_definition_locations.get(
                leaf["witness"], []
            ),
            "memory_dependency_status": (
                "proof-enforced-exact" if exact_memory_occurrences[leaf["witness"]]
                else "unresolved-dynamic" if leaf["witness"] in unresolved_memory_witnesses
                else "none"
            ),
        })
        public_leaves.append(leaf)
    profiles = _producer_extent_profiles(source_path, public_leaves, circuit, bindings)
    for leaf in public_leaves:
        match = re.match(r"^(.*)\[(\d+)\]$", leaf["path"])
        profile = profiles.get(match.group(1)) if match else None
        if profile is not None:
            leaf["binding_status"] = profile["status"]
            leaf["binding_condition"] = profile["condition"]
            leaf["binding_evidence"] = profile["evidence"]
        elif leaf["occurrence_count"]:
            leaf["binding_status"] = "EXACT"
            leaf["binding_condition"] = {"kind": "always"}
            leaf["binding_evidence"] = {"occurrence_locations": leaf["occurrence_locations"]}
        elif leaf["memory_dependency_status"] == "unresolved-dynamic":
            leaf["binding_status"] = "UNKNOWN"
            leaf["binding_condition"] = {"kind": "unknown",
                                         "reason": "PRODUCER_DYNAMIC_MEMORY_ADDRESS_UNRESOLVED"}
            leaf["binding_evidence"] = {"memory_definition_locations":
                                         leaf["memory_definition_occurrence_locations"]}
        else:
            leaf["binding_status"] = "EXACT"
            leaf["binding_condition"] = {"kind": "never"}
            leaf["binding_evidence"] = {"occurrence_locations": []}
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "noir_version": version,
        "decoder": decoder_name,
        "opcode_count": len(circuit["opcodes"]),
        "opcode_counts": dict(sorted(kinds.items())),
        "occurrence_policy": {
            "proof_enforced": "assertions, black boxes (inputs and outputs), exact constant-address MemoryInit reads, memory-op address/value expressions, and constrained calls",
            "witness_generation_only": "Brillig call inputs, outputs, and predicates",
            "definition_only": "MemoryInit cell definitions; dynamic-address dependencies fail closed when no other proof-enforced occurrence exists",
        },
        "public_leaves": public_leaves,
        "public_witnesses": circuit["public_parameters"],
        "source": (str(source_path.resolve()) if source_path else None),
        "source_sha256": (sha256(source_path) if source_path else None),
    }


def _symbols(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        if value.get("op") == "symbol" and value.get("args"):
            result.add(str(value["args"][0]))
        for child in value.values():
            result.update(_symbols(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_symbols(child))
    return result


def _source_class(symbol: str) -> str:
    if symbol.startswith("calldata."):
        return "calldata"
    if symbol.startswith(("block.", "msg.", "tx.")):
        return "environment"
    return "consumer-supplied"


def _const_bool(value: Any) -> bool | None:
    if isinstance(value, dict) and value.get("op") == "const":
        args = value.get("args", [])
        if len(args) == 1 and isinstance(args[0], bool):
            return args[0]
    return None


def _selects(value: Any) -> list[tuple[str, frozenset[str]]]:
    result: list[tuple[str, frozenset[str]]] = []
    if isinstance(value, dict):
        if value.get("op") == "select" and len(value.get("args", [])) >= 2:
            base, key = value["args"][:2]
            if isinstance(base, dict) and base.get("op") == "storage" and base.get("args"):
                result.append((str(base["args"][0]), frozenset(_symbols(key))))
        for child in value.values():
            result.extend(_selects(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_selects(child))
    return result


def _false_selects(value: Any) -> list[tuple[str, frozenset[str]]]:
    result: list[tuple[str, frozenset[str]]] = []
    if isinstance(value, dict):
        op = value.get("op")
        args = value.get("args", [])
        if op in {"eq", "neq"} and len(args) == 2:
            false_side = _const_bool(args[0]) is False or _const_bool(args[1]) is False
            true_side = _const_bool(args[0]) is True or _const_bool(args[1]) is True
            select_side = args[1] if _const_bool(args[0]) is not None else args[0]
            if (op == "eq" and false_side) or (op == "neq" and true_side):
                result.extend(_selects(select_side))
        if op == "not" and args:
            result.extend(_selects(args[0]))
        for child in value.values():
            result.extend(_false_selects(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_false_selects(child))
    return result


def _reported_boundary_location(source: Path, relation: dict[str, Any]) -> str:
    """Recover a missing line from the relation's recorded call signature.

    This is reporting-only: ambiguity retains ``?`` and cannot affect any
    dependency, guard, effect, polarity, or warning predicate.
    """
    boundary = relation.get("verifier_boundary", {})
    recorded = boundary.get("location")
    if isinstance(recorded, str) and not recorded.endswith(":?"):
        return recorded
    names: list[str] = []
    declaration = boundary.get("declaration")
    if isinstance(declaration, str) and "::" in declaration:
        names.append(declaration.rsplit("::", 1)[-1].split("(", 1)[0])
    expression = boundary.get("expression")
    if isinstance(expression, str) and "@" in expression:
        names.append(expression.split("@", 1)[0])
    source_text = source.read_text()
    for name in dict.fromkeys(item for item in names if re.fullmatch(r"[A-Za-z_$][\w$]*", item)):
        matches = list(re.finditer(rf"\.\s*{re.escape(name)}\s*\(", source_text))
        if len(matches) == 1:
            line = source_text.count("\n", 0, matches[0].start()) + 1
            return f"{source.name}:{line}"
    return recorded if isinstance(recorded, str) else f"{source.name}:?"


def _effect_warning_location(consumer: dict[str, Any], indices: list[int]) -> str:
    """Select the reported committed-effect site that consumes the words.

    Effect recognition and dependency sets are inputs to this helper and are
    not changed here.  External effects are preferable to bookkeeping writes
    when both already carry the vulnerable public words.
    """
    vulnerable = set(indices)
    candidates = []
    for effect in consumer["effects"]:
        words = set(effect.get("words", []))
        if not words and isinstance(effect.get("raw"), dict):
            symbols = _symbols(effect["raw"])
            words = {
                word["index"] for word in consumer["public_words"]
                if word.get("origin") in symbols
            }
        if words.intersection(vulnerable) and effect.get("location"):
            candidates.append(effect)
    preferred = [effect for effect in candidates if effect.get("kind") != "storage-write"]
    selected = preferred[0] if preferred else (candidates[0] if candidates else None)
    return selected["location"] if selected else consumer["verifier_location"]


def load_relation_consumer(source: Path, relation_path: Path, public_count: int) -> dict[str, Any]:
    relation = json.loads(relation_path.read_text())
    expected_source = relation.get("source_sha256")
    if expected_source is not None and expected_source != sha256(source):
        raise ValueError("CONSUMER_RELATION_SOURCE_HASH_MISMATCH")
    if relation.get("schema") in {"bindcheck.consumer-ast.v1.1", "bindcheck.consumer-ast.v1.2",
                                  "bindcheck.consumer-ast.v1.3"}:
        if "AST_VERIFIER_SELECTOR_PREFIX_WIDTH_DERIVED_FROM_ABI_AND_ARRAY_HEADER" in relation.get(
            "limitations", []
        ):
            raise ValueError("CONSUMER_PUBLIC_INPUT_MAPPING_UNVERIFIED")
        words = relation["public_words"]
        if len(words) != public_count:
            raise ValueError(
                f"consumer/producer public-width mismatch: consumer {len(words)}, producer {public_count}"
            )
        replay_records = relation.get("replay_records", [])
        replay = {
            "applicable": bool(replay_records),
            "must_not_be_in": bool(replay_records) and all(
                item.get("guarded_absent", False) for item in replay_records
            ),
            "written": bool(replay_records),
            "evidence": [item["write"].get("location") for item in replay_records],
        }
        return {
            "kind": "compiler-ast-relation",
            "source": str(source.resolve()), "source_sha256": sha256(source),
            "relation": str(relation_path.resolve()), "relation_sha256": sha256(relation_path),
            "relation_schema": relation["schema"], "scope": relation.get("scope"),
            "verifier_location": _reported_boundary_location(source, relation),
            "public_words": words,
            "anchor_words": relation.get("anchor_words", []),
            "consumer_unused_indices": [item["index"] for item in words
                                         if not item.get("consumer_used", False)
                                         and item.get("source_class") == "calldata"],
            "effect_word_indices": relation.get("effect_word_indices", []),
            "effects": relation.get("effects", []),
            "replay": replay,
            "limitations": relation.get("limitations", []),
            "mapping_certificate": relation.get("mapping_certificate"),
        }

    boundary = relation["verifier_boundary"]
    words = boundary["public_words"]
    if len(words) != public_count:
        raise ValueError(
            f"consumer/producer public-width mismatch: consumer {len(words)}, producer {public_count}"
        )
    success = [path for path in relation["paths"] if path["status"] == "success"]
    effects: list[dict[str, Any]] = []
    effect_origins: set[str] = set()
    for path in success:
        committed = path["committed"]
        for kind in ("mints", "burns", "transfers"):
            for effect in committed.get(kind, []):
                record = {"kind": kind[:-1], "location": effect.get("location"), "raw": effect}
                effects.append(record)
                effect_origins.update(_symbols(effect))

    # All classification below is structural. Storage declaration identity and
    # data dependencies are compared exactly; identifier spelling has no role.
    guard_symbols = set()
    admitted: dict[int, list[str]] = {}
    absent_pairs: set[tuple[str, frozenset[str]]] = set()
    for path in success:
        for guard, guard_ir in zip(path.get("guards", []), path.get("guards_ir", [])):
            if isinstance(guard_ir, dict) and guard_ir.get("op") == "relation":
                # The verifier boundary authenticates the array; it is not an
                # independent consumer use of the words within that array.
                continue
            symbols = _symbols(guard_ir)
            guard_symbols.update(symbols)
            for pair in _selects(guard_ir):
                for word in words:
                    word_symbols = _symbols(word.get("expression_ir", {})) or {word["origin"]}
                    if word_symbols.intersection(pair[1]):
                        admitted.setdefault(word["index"], []).append(guard)
            absent_pairs.update(_false_selects(guard_ir))

    anchor_words = [{
        "public_index": index, "origin": words[index]["origin"], "must_be_in": True,
        "evidence": sorted(evidence),
    } for index, evidence in sorted(admitted.items())]

    write_pairs: set[tuple[str, frozenset[str]]] = set()
    write_evidence = []
    for path in success:
        for write in path["committed"].get("storage_writes", []):
            if _const_bool(write.get("value_ir")) is not True or not write.get("key"):
                continue
            pair = (str(write.get("slot")), frozenset(_symbols(write.get("map_after_ir", {}))
                                                    & _symbols({"op": "symbol", "args": [write["key"]]})))
            if not pair[1]:
                pair = (str(write.get("slot")), frozenset({str(write["key"])}))
            write_pairs.add(pair)
            write_evidence.append(write.get("location"))
    replay_pairs = write_pairs | absent_pairs
    replay = {
        "applicable": bool(replay_pairs),
        "must_not_be_in": bool(replay_pairs) and replay_pairs.issubset(absent_pairs),
        "written": bool(replay_pairs) and replay_pairs.issubset(write_pairs),
        "evidence": sorted(item for item in write_evidence if item),
    }

    effect_word_indices = sorted({
        word["index"] for word in words
        if word["origin"] in effect_origins
    })
    consumer_symbols = guard_symbols | effect_origins
    normalized_words = []
    for word in words:
        item = dict(word)
        symbols = _symbols(word.get("expression_ir", {})) or {word["origin"]}
        item["source_classes"] = sorted({_source_class(symbol) for symbol in symbols})
        item["consumer_used"] = bool(symbols.intersection(consumer_symbols))
        normalized_words.append(item)
    return {
        "kind": "extracted-relation",
        "source": str(source.resolve()),
        "source_sha256": sha256(source),
        "relation": str(relation_path.resolve()),
        "relation_sha256": sha256(relation_path),
        "relation_schema": relation.get("schema"),
        "scope": relation.get("scope"),
        "verifier_location": _reported_boundary_location(source, relation),
        "public_words": normalized_words,
        "anchor_words": anchor_words,
        "consumer_unused_indices": [word["index"] for word in normalized_words
                                     if not word["consumer_used"]
                                     and "calldata" in word["source_classes"]],
        "effect_word_indices": effect_word_indices,
        "effects": effects,
        "replay": replay,
        "limitations": ["RELATION_FRONTEND_IS_NOT_SOLIDITY_SEMANTIC_EQUIVALENCE"],
    }


def _ranges(leaves: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group adjacent array leaves while leaving scalars separate."""
    groups: list[list[dict[str, Any]]] = []
    for leaf in leaves:
        base = re.sub(r"\[\d+\]$", "", leaf["path"])
        if groups:
            previous = groups[-1][-1]
            previous_base = re.sub(r"\[\d+\]$", "", previous["path"])
            if (base == previous_base and "[" in leaf["path"]
                    and leaf["public_index"] == previous["public_index"] + 1):
                groups[-1].append(leaf)
                continue
        groups.append([leaf])
    return groups


def _condition_text(condition: dict[str, Any]) -> str:
    kind = condition.get("kind")
    if kind == "always":
        return "true"
    if kind == "never":
        return "false"
    if kind == "prefix":
        return f"word_offset < {condition.get('extent', 'unknown_extent')}"
    if kind == "any":
        return " OR ".join(_condition_text(item) for item in condition.get("conditions", []))
    return f"UNKNOWN({condition.get('reason', 'condition unresolved')})"


def _extent_coverage(producer_fact: dict[str, Any],
                     consumer_fact: dict[str, Any]) -> dict[str, Any]:
    """Stable extent-facts interface consumed by the prospective rule engine."""
    producer_condition = producer_fact["condition"]
    consumer_condition = consumer_fact["condition"]
    result = {
        "producer_condition": _condition_text(producer_condition),
        "consumer_condition": _condition_text(consumer_condition),
        "uncovered_region": None,
    }
    if producer_fact["status"] != "EXACT" or consumer_fact["status"] != "EXACT":
        return result | {"status": "UNKNOWN", "covered": None}
    producer_kind = producer_condition.get("kind")
    consumer_kind = consumer_condition.get("kind")
    if consumer_kind == "never" or producer_kind == "always":
        return result | {"status": "EXACT", "covered": True}
    if producer_kind == "unknown" or consumer_kind in {"unknown", "any"}:
        return result | {"status": "UNKNOWN", "covered": None}
    if producer_kind == "never":
        return result | {"status": "EXACT", "covered": False,
                         "uncovered_region": result["consumer_condition"]}
    if producer_kind == "prefix" and consumer_kind == "prefix":
        same_extent = (producer_condition.get("extent") == consumer_condition.get("extent")
                       and producer_condition.get("extent_value") == consumer_condition.get("extent_value"))
        if same_extent:
            return result | {"status": "EXACT", "covered": True}
        uncovered = (f"{producer_condition.get('extent')} <= word_offset < "
                     f"{consumer_condition.get('extent')}")
        return result | {"status": "EXACT", "covered": False,
                         "uncovered_region": uncovered}
    if producer_kind == "prefix" and consumer_kind == "always":
        return result | {"status": "EXACT", "covered": False,
                         "uncovered_region":
                         f"{producer_condition.get('extent')} <= word_offset < configured_length"}
    return result | {"status": "UNKNOWN", "covered": None}


def _word_extent_facts(producer: dict[str, Any], consumer: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    producer_facts = [{
        "public_index": leaf["public_index"], "path": leaf["path"],
        "status": leaf.get("binding_status", "UNKNOWN"),
        "condition": leaf.get("binding_condition", {"kind": "unknown", "reason": "MISSING"}),
        "evidence": leaf.get("binding_evidence", {}),
    } for leaf in producer["public_leaves"]]
    consumer_by_index = {word["index"]: word for word in consumer["public_words"]}
    consumer_facts = []
    for leaf in producer["public_leaves"]:
        word = consumer_by_index.get(leaf["public_index"])
        if word is None:
            consumer_facts.append({
                "public_index": leaf["public_index"], "path": leaf["path"],
                "status": "UNKNOWN", "condition": {"kind": "unknown", "reason": "CONSUMER_WORD_MISSING"},
                "evidence": {},
            })
            continue
        consumer_facts.append({
            "public_index": leaf["public_index"], "path": leaf["path"],
            "status": word.get("reliance_status", "UNKNOWN"),
            "condition": word.get("reliance_condition", {"kind": "unknown", "reason": "LEGACY_RELATION"}),
            "evidence": {"origin": word.get("origin"), "source_class": word.get("source_class")},
        })
    return producer_facts, consumer_facts


def analyze(artifact_path: Path, source_path: Path, relation_path: Path | None = None,
            label: str | None = None, *, producer_source: Path | None = None,
            mapping_bridge: Path | None = None) -> dict[str, Any]:
    started = time.monotonic()
    producer = load_producer(artifact_path, producer_source)
    if relation_path is None:
        raise ValueError("UNSUPPORTED_CONSUMER_AST_REQUIRED")
    consumer = load_relation_consumer(source_path, relation_path, len(producer["public_leaves"]))
    mapping_certificate = consumer.get("mapping_certificate")
    if mapping_certificate is not None:
        if mapping_bridge is None:
            raise ValueError("RECURSIVE_MAPPING_BRIDGE_ARTIFACT_REQUIRED")
        verify_mapping_certificate(mapping_certificate, artifact_path, mapping_bridge)
    warnings: list[dict[str, Any]] = []

    unresolved_memory = [
        leaf for leaf in producer["public_leaves"]
        if leaf.get("binding_status") == "UNKNOWN"
    ]
    if unresolved_memory:
        paths = ",".join(leaf["path"] for leaf in unresolved_memory[:8])
        suffix = "..." if len(unresolved_memory) > 8 else ""
        raise ValueError(f"UNSUPPORTED_DYNAMIC_MEMORY_DEPENDENCY:{paths}{suffix}")

    def warning(rule: str, location: str, explanation: str, suggested_fix: str,
                evidence: dict[str, Any], confidence: str = "high") -> None:
        warnings.append({
            "id": f"W{len(warnings) + 1:03d}", "rule": rule,
            "severity": "warning", "confidence": confidence,
            "location": location, "explanation": explanation,
            "suggested_fix": suggested_fix, "evidence": evidence,
        })

    producer_extent_facts, consumer_extent_facts = _word_extent_facts(producer, consumer)
    extent_rows = []
    for producer_fact, consumer_fact in zip(producer_extent_facts, consumer_extent_facts):
        coverage = _extent_coverage(producer_fact, consumer_fact)
        extent_rows.append({"public_index": producer_fact["public_index"],
                            "path": producer_fact["path"], **coverage})
    uncovered = [row for row in extent_rows
                 if row["status"] == "EXACT" and row["covered"] is False]
    grouped_uncovered: list[list[dict[str, Any]]] = []
    for row in uncovered:
        base = re.sub(r"\[\d+\]$", "", row["path"])
        if grouped_uncovered:
            previous = grouped_uncovered[-1][-1]
            previous_base = re.sub(r"\[\d+\]$", "", previous["path"])
            if (base == previous_base
                    and row["public_index"] == previous["public_index"] + 1
                    and (row["producer_condition"], row["consumer_condition"], row["uncovered_region"])
                    == (previous["producer_condition"], previous["consumer_condition"],
                        previous["uncovered_region"])):
                grouped_uncovered[-1].append(row)
                continue
        grouped_uncovered.append([row])
    for group in grouped_uncovered:
        first, last = group[0], group[-1]
        label_paths = first["path"] if len(group) == 1 else f"{first['path']}..{last['path']}"
        warning(
            "R-EXTENT",
            _effect_warning_location(consumer, [row["public_index"] for row in group]),
            f"The consumer relies on {label_paths} when {first['consumer_condition']}, but the producer "
            f"binds those words only when {first['producer_condition']}. Uncovered region: "
            f"{first['uncovered_region']}.",
            "Make the producer bind every consumer-relied word, or limit the consumer to the producer's "
            "proof-enforced extent and rebuild the checked boundary artifacts together.",
            {"public_indices": [row["public_index"] for row in group],
             "paths": [row["path"] for row in group],
             "producer_condition": first["producer_condition"],
             "consumer_condition": first["consumer_condition"],
             "uncovered_region": first["uncovered_region"]},
        )

    unused = [leaf for leaf in producer["public_leaves"]
              if leaf.get("binding_status") == "EXACT"
              and leaf.get("binding_condition", {}).get("kind") == "never"]
    for group in _ranges(unused):
        paths = [leaf["path"] for leaf in group]
        indices = [leaf["public_index"] for leaf in group]
        witnesses = [leaf["witness"] for leaf in group]
        label_paths = paths[0] if len(paths) == 1 else f"{paths[0]}..{paths[-1]}"
        warning(
            "R-BIND",
            f"{artifact_path.name}:abi.{label_paths}",
            f"Consumer-constructed verifier argument(s) {label_paths} have no occurrence in the decoded "
            "proof-enforced ACIR. Their values can vary without directly constraining the producer relation.",
            "Constrain every exposed verifier argument in the producer, or remove it from the consumer-visible "
            "effect surface; rebuild the artifact, key, and verifier together.",
            {"public_indices": indices, "witnesses": witnesses, "occurrence_counts": [0] * len(group)},
        )

    unused_indices = {leaf["public_index"] for leaf in unused}
    vulnerable_effect = sorted(unused_indices.intersection(consumer["effect_word_indices"]))
    if vulnerable_effect:
        effect_leaves = [producer["public_leaves"][index] for index in vulnerable_effect]
        warning(
            "R-EFFECT",
            _effect_warning_location(consumer, vulnerable_effect),
            "The consumer interprets producer public words as effect amount, beneficiary, or message data, but "
            "one or more of those words are absent from all proof-enforced ACIR opcodes.",
            "Bind every effect-decoded public word in the producer and keep the consumer effect derived only from "
            "those bound public inputs.",
            {"public_indices": vulnerable_effect, "paths": [leaf["path"] for leaf in effect_leaves],
             "effect_kinds": sorted({effect["kind"] for effect in consumer["effects"]})},
        )

    for index in consumer.get("consumer_unused_indices", []):
        leaf = producer["public_leaves"][index]
        warning(
            "R-CONSUMER",
            consumer["verifier_location"],
            f"Verifier public word {index} ({leaf['path']}) is constructed at the boundary but has no "
            "guard, committed-state, or modeled effect dependency in the extracted consumer relation.",
            "Consume the authenticated word in the corresponding state admission, replay, or effect "
            "operation, and regenerate the checked consumer relation.",
            {"public_index": index, "path": leaf["path"], "consumer_origin":
             consumer["public_words"][index].get("origin"), "source_classes":
             consumer["public_words"][index].get("source_classes",
                                                  [consumer["public_words"][index].get("source_class")])},
        )

    for anchor in consumer["anchor_words"]:
        if not anchor["must_be_in"]:
            leaf = producer["public_leaves"][anchor["public_index"]]
            warning(
                "R-ANCHOR",
                consumer["verifier_location"],
                f"Producer anchor {leaf['path']} (consumer origin {anchor['origin']}) is proof-visible but no "
                "must-be-in check against consumer chain state was found on every successful path.",
                "Before accepting the proof, require this root/anchor to be admitted by the appropriate on-chain "
                "history or current-state mapping.",
                {"public_index": anchor["public_index"], "path": leaf["path"],
                 "polarity": "must-be-in", "observed_guard_evidence": anchor["evidence"]},
            )

    replay = consumer["replay"]
    if replay["applicable"] and (not replay["must_not_be_in"] or not replay["written"]):
        missing = []
        if not replay["must_not_be_in"]:
            missing.append("pre-state must-not-be-in guard")
        if not replay["written"]:
            missing.append("successful nullifier/spent-key write")
        warning(
            "R-POLARITY",
            consumer["verifier_location"],
            "Replay protection is incomplete across two transactions: missing " + " and ".join(missing) + ".",
            "Check the replay key is absent before verification and write the same key atomically on success.",
            {"polarity": "must-not-be-in", "guard": replay["must_not_be_in"],
             "write": replay["written"], "evidence": replay["evidence"]},
        )

    for item in warnings:
        item["target_identity"] = {
            "artifact_sha256": producer["sha256"], "consumer_sha256": consumer["source_sha256"],
            "rule": item["rule"],
        }
    elapsed = time.monotonic() - started
    return {
        "schema": SCHEMA,
        "generated_at_utc": utc_now(),
        "target": label or f"{artifact_path.stem}+{source_path.name}",
        "producer": producer,
        "consumer": consumer,
        "rules": {
            "R-BIND": "consumer-constructed verifier arguments occur in proof-enforced producer opcodes",
            "R-ANCHOR": "producer roots/anchors have must-be-in consumer state checks",
            "R-EFFECT": "effect amount/beneficiary/message words are producer-bound public inputs",
            "R-POLARITY": "anchors are must-be-in; replay keys are must-not-be-in and written on success",
            "R-CONSUMER": "each verifier public word reaches a guard, committed state, or modeled effect",
            "R-EXTENT": "consumer reliance implies the producer's proof-enforced binding condition",
        },
        "extent_facts": {"schema": "bindcheck.extent-facts.v1",
                         "producer": producer_extent_facts,
                         "consumer": consumer_extent_facts,
                         "coverage": extent_rows},
        "polarity": {"anchors": consumer["anchor_words"], "replay": replay},
        "warnings": warnings,
        "warning_count": len(warnings),
        "manual_inputs": [{"kind": "checked_consumer_relation", "path": consumer["relation"]}],
        "limitations": consumer["limitations"] + [
            "ACIR occurrence establishes syntactic proof-enforced use, not cryptographic injectivity or intent",
            "Brillig is inventoried as witness-generation machinery; it does not by itself discharge a binding",
            "single-target analysis uses no reference-version oracle",
        ],
        "runtime_seconds": round(elapsed, 6),
    }


def readable(result: dict[str, Any]) -> str:
    lines = [f"BindCheck v1.4-dev: {result['target']}",
             f"  producer: {result['producer']['sha256']} ({result['producer']['decoder']})",
             f"  consumer: {result['consumer']['source_sha256']} ({result['consumer']['kind']})",
             f"  warnings: {result['warning_count']}  runtime: {result['runtime_seconds']:.3f}s"]
    for warning in result["warnings"]:
        lines.extend([
            "",
            f"{warning['id']} {warning['rule']} at {warning['location']}",
            f"  {warning['explanation']}",
            f"  Fix: {warning['suggested_fix']}",
        ])
    if not result["warnings"]:
        lines.append("  No warning in the supported static scope.")
    return "\n".join(lines)
