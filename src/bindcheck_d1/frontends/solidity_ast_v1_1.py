"""Application-neutral Solidity consumer extraction for BindCheck v1.1.

The frontend consumes a solc combined-json AST.  It recognizes a verifier
boundary from the declared function type (``bytes``, ``bytes32[]`` and a
boolean-or-reverting result), follows the public array through internal calls,
and emits guards and committed effects.  Contract, function, field, and
application names are deliberately not part of recognition.

This is a bounded static frontend, not a Solidity equivalence proof.  Shapes
outside the supported AST subset fail closed or are listed as limitations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


SCHEMA = "bindcheck.consumer-ast.v1.1"


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _src_start(node: dict[str, Any]) -> int:
    return int(node.get("src", "0:0:-1").split(":", 1)[0])


def _line(source: str, node: dict[str, Any]) -> int:
    return source.count("\n", 0, _src_start(node)) + 1


def _type(node: dict[str, Any]) -> str:
    return str(node.get("typeDescriptions", {}).get("typeString", ""))


def _literal_int(node: dict[str, Any] | None) -> int | None:
    if not isinstance(node, dict) or node.get("nodeType") != "Literal":
        return None
    value = node.get("value")
    try:
        return int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError):
        return None


def _literal_bool(node: dict[str, Any] | None) -> bool | None:
    if not isinstance(node, dict) or node.get("nodeType") != "Literal":
        return None
    value = node.get("value")
    if value == "true":
        return True
    if value == "false":
        return False
    return None


@dataclass(frozen=True)
class Value:
    words: frozenset[int] = frozenset()
    array_start: int | None = None
    integer: int | None = None

    @staticmethod
    def merge(*values: "Value") -> "Value":
        words: set[int] = set()
        starts = []
        for value in values:
            words.update(value.words)
            if value.array_start is not None:
                starts.append(value.array_start)
        return Value(frozenset(words), min(starts) if starts else None, None)


@dataclass
class Trace:
    guards: list[dict[str, Any]] = field(default_factory=list)
    effects: list[dict[str, Any]] = field(default_factory=list)
    writes: list[dict[str, Any]] = field(default_factory=list)
    verifier_calls: list[dict[str, Any]] = field(default_factory=list)
    unsupported: set[str] = field(default_factory=set)


class Extractor:
    def __init__(self, combined: dict[str, Any], source_key: str, source: Path,
                 public_leaves: list[dict[str, Any]]):
        self.combined = combined
        self.source_key = source_key
        self.source_path = source
        self.source_text = source.read_text()
        self.public_leaves = public_leaves
        self.public_count = len(public_leaves)
        self.array_lower_bounds: set[int] = set()
        effect_table_path = Path(__file__).resolve().parents[3] / "protocols/d1/bindcheck-v1.1-effect-models.json"
        self.effect_table = json.loads(effect_table_path.read_text())
        source_record = combined.get("sources", {}).get(source_key)
        if not source_record or "AST" not in source_record:
            raise ValueError(f"SOLIDITY_AST_SOURCE_MISSING:{source_key}")
        self.root = source_record["AST"]
        self.nodes_by_id: dict[int, dict[str, Any]] = {}
        for record in combined.get("sources", {}).values():
            for node in _walk(record.get("AST", {})):
                if isinstance(node.get("id"), int):
                    self.nodes_by_id[node["id"]] = node
        self.functions = {
            node["id"]: node for node in _walk(self.root)
            if node.get("nodeType") == "FunctionDefinition" and isinstance(node.get("id"), int)
        }
        self.trace = Trace()
        self.active: set[tuple[int, tuple[tuple[int, tuple[int, ...], int | None, int | None], ...]]] = set()

    @staticmethod
    def _is_verifier_declaration(node: dict[str, Any]) -> bool:
        if node.get("nodeType") != "FunctionDefinition":
            return False
        params = node.get("parameters", {}).get("parameters", [])
        returns = node.get("returnParameters", {}).get("parameters", [])
        if len(params) != 2:
            return False
        first, second = (_type(item) for item in params)
        proof = first.startswith("bytes ") or first == "bytes" or first.startswith("bytes calldata")
        words = "bytes32[]" in second
        result = not returns or (len(returns) == 1 and _type(returns[0]).startswith("bool"))
        return proof and words and result

    def _call_declaration(self, call: dict[str, Any]) -> dict[str, Any] | None:
        expression = call.get("expression", {})
        declaration = expression.get("referencedDeclaration")
        if not isinstance(declaration, int) and expression.get("nodeType") == "MemberAccess":
            declaration = expression.get("referencedDeclaration")
        return self.nodes_by_id.get(declaration) if isinstance(declaration, int) else None

    def _words_for_array_index(self, array: Value, index: Value) -> frozenset[int]:
        if array.array_start is None:
            return frozenset()
        if index.integer is not None and 0 <= index.integer < self.public_count:
            return frozenset({index.integer})
        start = max(0, array.array_start)
        return frozenset(range(start, self.public_count))

    def _storage_signature(self, node: Any, env: dict[int, Value] | None = None) -> tuple[tuple[int, ...], frozenset[int]] | None:
        """Return declaration-id path and public-word key dependencies."""
        if not isinstance(node, dict):
            return None
        kind = node.get("nodeType")
        if kind == "Identifier":
            declaration = node.get("referencedDeclaration")
            target = self.nodes_by_id.get(declaration, {}) if isinstance(declaration, int) else {}
            if target.get("stateVariable"):
                return ((declaration,), frozenset())
            return None
        if kind == "MemberAccess":
            base = self._storage_signature(node.get("expression"), env)
            declaration = node.get("referencedDeclaration")
            if base is None:
                return None
            suffix = (declaration,) if isinstance(declaration, int) else ()
            return (base[0] + suffix, base[1])
        if kind == "IndexAccess":
            base = self._storage_signature(node.get("baseExpression"), env)
            if base is None:
                return None
            index = self._eval(node.get("indexExpression"), env or {})
            return (base[0], base[1] | index.words)
        return None

    def _eval(self, node: Any, env: dict[int, Value]) -> Value:
        if not isinstance(node, dict):
            return Value()
        kind = node.get("nodeType")
        if kind == "Identifier":
            declaration = node.get("referencedDeclaration")
            return env.get(declaration, Value()) if isinstance(declaration, int) else Value()
        if kind == "Literal":
            return Value(integer=_literal_int(node))
        if kind == "IndexAccess":
            base = self._eval(node.get("baseExpression"), env)
            index = self._eval(node.get("indexExpression"), env)
            return Value(self._words_for_array_index(base, index))
        if kind == "FunctionCall":
            values = [self._eval(arg, env) for arg in node.get("arguments", [])]
            declaration = self._call_declaration(node)
            if declaration is not None and self._is_verifier_declaration(declaration):
                self.trace.verifier_calls.append({
                    "location": f"{self.source_path.name}:{_line(self.source_text, node)}",
                    "declaration_id": declaration.get("id"),
                    "signature": _type(node.get("expression", {})),
                    "argument_words": sorted(Value.merge(*values).words),
                })
                return Value()
            if declaration is not None and declaration.get("id") in self.functions:
                self._run_function(declaration, values)
            # Standard token effects are signature-based, never name/path based.
            signature = _type(node.get("expression", {}))
            candidate_signatures = [signature]
            for item in _walk(node.get("arguments", [])):
                declaration_id = item.get("referencedDeclaration")
                declaration_node = self.nodes_by_id.get(declaration_id, {})
                if declaration_node.get("nodeType") == "FunctionDefinition":
                    parameters = declaration_node.get("parameters", {}).get("parameters", [])
                    candidate_signatures.append(
                        "function (" + ",".join(_type(parameter).split(" ", 1)[0]
                                                 for parameter in parameters) + ")"
                    )
            effect_model = next((model for model in self.effect_table["models"]
                                 if any(model["function_type_contains"] in candidate
                                        for candidate in candidate_signatures)), None)
            if effect_model is not None:
                words = sorted(Value.merge(*values).words)
                self.trace.effects.append({
                    "kind": effect_model["effect"], "words": words,
                    "location": f"{self.source_path.name}:{_line(self.source_text, node)}",
                    "signature": signature,
                })
            return Value.merge(*values)
        values = []
        for key, child in node.items():
            if key in {"typeDescriptions", "src", "id", "referencedDeclaration"}:
                continue
            if isinstance(child, dict):
                values.append(self._eval(child, env))
            elif isinstance(child, list):
                values.extend(self._eval(item, env) for item in child if isinstance(item, dict))
        merged = Value.merge(*values)
        if kind == "BinaryOperation":
            left = self._eval(node.get("leftExpression"), env)
            right = self._eval(node.get("rightExpression"), env)
            operator = node.get("operator")
            if operator in {"+", "-"}:
                if left.integer is not None and right.integer is not None:
                    number = left.integer + right.integer if operator == "+" else left.integer - right.integer
                    return Value(left.words | right.words, integer=number)
        return merged

    def _guard(self, expression: dict[str, Any], env: dict[int, Value]) -> None:
        value = self._eval(expression, env)
        storage = []
        for node in _walk(expression):
            signature = self._storage_signature(node, env)
            if signature and signature not in storage:
                storage.append(signature)
        self.trace.guards.append({
            "words": sorted(value.words),
            "storage": [{"declarations": list(item[0]), "key_words": sorted(item[1])}
                        for item in storage],
            "location": f"{self.source_path.name}:{_line(self.source_text, expression)}",
            "requires_false": any(_literal_bool(node) is False for node in _walk(expression)),
        })

    def _assign(self, left: dict[str, Any], right: dict[str, Any], env: dict[int, Value]) -> None:
        value = self._eval(right, env)
        if left.get("nodeType") == "Identifier":
            declaration = left.get("referencedDeclaration")
            if isinstance(declaration, int) and declaration in env:
                env[declaration] = value
                return
        storage = self._storage_signature(left, env)
        if storage:
            record = {
                "kind": "storage-write",
                "declarations": list(storage[0]),
                "key_words": sorted(storage[1]),
                "value_words": sorted(value.words),
                "value_bool": _literal_bool(right),
                "words": sorted(storage[1] | value.words),
                "location": f"{self.source_path.name}:{_line(self.source_text, left)}",
            }
            self.trace.writes.append(record)
            self.trace.effects.append(record)

    def _run_statement(self, node: Any, env: dict[int, Value]) -> None:
        if not isinstance(node, dict):
            return
        kind = node.get("nodeType")
        if kind == "Block" or kind == "UncheckedBlock":
            for statement in node.get("statements", []):
                self._run_statement(statement, env)
            return
        if kind == "VariableDeclarationStatement":
            value = self._eval(node.get("initialValue"), env)
            for declaration in node.get("declarations", []):
                if isinstance(declaration, dict) and isinstance(declaration.get("id"), int):
                    env[declaration["id"]] = value
            return
        if kind == "ExpressionStatement":
            expression = node.get("expression", {})
            if expression.get("nodeType") == "Assignment":
                self._assign(expression.get("leftHandSide", {}), expression.get("rightHandSide", {}), env)
            else:
                call_decl = self._call_declaration(expression) if expression.get("nodeType") == "FunctionCall" else None
                if (expression.get("nodeType") == "FunctionCall" and call_decl is None
                        and expression.get("expression", {}).get("name") in {"require", "assert"}):
                    arguments = expression.get("arguments", [])
                    if arguments:
                        self._guard(arguments[0], env)
                else:
                    self._eval(expression, env)
            return
        if kind in {"IfStatement", "WhileStatement", "ForStatement", "DoWhileStatement"}:
            condition = node.get("condition")
            if isinstance(condition, dict):
                self._guard(condition, env)
            if kind == "ForStatement":
                self._run_statement(node.get("initializationExpression"), env)
            body_env = dict(env)
            if kind in {"WhileStatement", "ForStatement", "DoWhileStatement"}:
                # A loop-carried integer index is widened. Its lower bound is
                # retained on the array value propagated into this function.
                for item in _walk(condition or {}):
                    declaration = item.get("referencedDeclaration")
                    if item.get("nodeType") == "Identifier" and declaration in body_env:
                        old = body_env[declaration]
                        body_env[declaration] = Value(old.words, old.array_start, None)
            self._run_statement(node.get("trueBody") or node.get("body"), body_env)
            self._run_statement(node.get("falseBody"), dict(env))
            return
        if kind == "Return":
            self._eval(node.get("expression"), env)
            return
        # Modifier-like, emit, try/catch and revert subtrees are conservatively
        # evaluated for dependencies; unsupported control semantics are named.
        if kind not in {"Break", "Continue", "PlaceholderStatement", "EmitStatement", "RevertStatement"}:
            self.trace.unsupported.add(f"AST_STATEMENT_{kind or 'UNKNOWN'}")
        self._eval(node, env)

    def _run_function(self, function: dict[str, Any], arguments: list[Value]) -> None:
        params = function.get("parameters", {}).get("parameters", [])
        scalar_lower = min((item.integer for item in arguments if item.integer is not None), default=None)
        if scalar_lower is not None:
            arguments = [
                Value(item.words, max(item.array_start, scalar_lower), item.integer)
                if item.array_start is not None else item
                for item in arguments
            ]
        self.array_lower_bounds.update(item.array_start for item in arguments
                                       if item.array_start is not None)
        env = {param["id"]: value for param, value in zip(params, arguments)
               if isinstance(param.get("id"), int)}
        key = (function["id"], tuple(sorted(
            (identifier, tuple(sorted(value.words)), value.array_start, value.integer)
            for identifier, value in env.items()
        )))
        if key in self.active:
            self.trace.unsupported.add("AST_RECURSIVE_INTERNAL_CALL")
            return
        self.active.add(key)
        self._run_statement(function.get("body"), env)
        self.active.remove(key)

    def extract(self) -> dict[str, Any]:
        candidates = []
        for function in self.functions.values():
            for call in (node for node in _walk(function.get("body", {}))
                         if node.get("nodeType") == "FunctionCall"):
                declaration = self._call_declaration(call)
                if declaration is not None and self._is_verifier_declaration(declaration):
                    candidates.append((function, call))
        if len(candidates) != 1:
            raise ValueError(f"SOLIDITY_VERIFIER_BOUNDARY_COUNT:{len(candidates)}")
        entry, call = candidates[0]
        args = call.get("arguments", [])
        if len(args) != 2 or args[1].get("nodeType") != "Identifier":
            raise ValueError("SOLIDITY_VERIFIER_PUBLIC_ARRAY_NOT_DIRECT_IDENTIFIER")
        array_id = args[1].get("referencedDeclaration")
        if not isinstance(array_id, int):
            raise ValueError("SOLIDITY_VERIFIER_PUBLIC_ARRAY_DECLARATION_MISSING")
        params = entry.get("parameters", {}).get("parameters", [])
        initial = []
        for param in params:
            initial.append(Value(array_start=0) if param.get("id") == array_id else Value())
        self._run_function(entry, initial)
        if len(self.trace.verifier_calls) != 1:
            raise ValueError(f"SOLIDITY_TRACED_VERIFIER_BOUNDARY_COUNT:{len(self.trace.verifier_calls)}")

        # Map the verifier's direct public array into the producer ABI. A
        # recursive verifier selector may account for a public prefix outside
        # the bytes32[] argument. The mapping is derived from the dynamic-array
        # header bound and the largest declared public ABI array, not names.
        groups: dict[str, set[int]] = {}
        for leaf in self.public_leaves:
            match = re.match(r"^(.*)\[(\d+)\]$", leaf["path"])
            if match:
                groups.setdefault(match.group(1), set()).add(int(match.group(2)))
        largest_array = max((len(indices) for indices in groups.values()), default=0)
        header = max(self.array_lower_bounds, default=0)
        direct_width = header + largest_array if largest_array else self.public_count
        if direct_width > self.public_count:
            raise ValueError("SOLIDITY_PUBLIC_ARRAY_ABI_WIDTH_OVERFLOW")
        producer_prefix = self.public_count - direct_width

        def mapped(indices: Iterable[int]) -> list[int]:
            return sorted(producer_prefix + index for index in indices
                          if 0 <= index < direct_width)

        for guard in self.trace.guards:
            guard["words"] = mapped(guard["words"])
            for slot in guard["storage"]:
                slot["key_words"] = mapped(slot["key_words"])
        for effect in self.trace.effects:
            effect["words"] = mapped(effect.get("words", []))
            if "key_words" in effect:
                effect["key_words"] = mapped(effect["key_words"])
            if "value_words" in effect:
                effect["value_words"] = mapped(effect["value_words"])
        guard_words = set().union(*(set(item["words"]) for item in self.trace.guards), set())
        effect_words = set().union(*(set(item["words"]) for item in self.trace.effects), set())
        consumer_words = guard_words | effect_words

        replay_records = []
        for write in self.trace.writes:
            if write["value_bool"] is not True:
                continue
            matching = [guard for guard in self.trace.guards
                        if guard["requires_false"] and any(
                            slot["declarations"] == write["declarations"]
                            and set(slot["key_words"]) == set(write["key_words"])
                            for slot in guard["storage"])]
            replay_records.append({"write": write, "guarded_absent": bool(matching),
                                   "guards": matching})

        anchor_words = []
        for guard in self.trace.guards:
            if not guard["storage"]:
                continue
            for index in guard["words"]:
                anchor_words.append({
                    "public_index": index,
                    "origin": (f"public_inputs[{index - producer_prefix}]"
                               if index >= producer_prefix else f"verifier_selector_part[{index}]"),
                    "must_be_in": True, "evidence": [guard["location"]],
                })
        unique_anchors = {item["public_index"]: item for item in anchor_words}
        return {
            "schema": SCHEMA,
            "source": str(self.source_path.resolve()),
            "source_sha256": _sha256(self.source_path),
            "source_key": self.source_key,
            "scope": "solc AST type-directed verifier boundary, guards, storage writes, and standard token calls",
            "verifier_boundary": {**self.trace.verifier_calls[0],
                                  "direct_array_width": direct_width,
                                  "producer_prefix_width": producer_prefix},
            "public_words": ([
                {"index": index, "origin": f"verifier_selector_part[{index}]",
                 "source_class": "calldata", "consumer_used": True,
                 "guard_used": True, "effect_used": False}
                for index in range(producer_prefix)
            ] + [
                {"index": producer_prefix + index, "origin": f"public_inputs[{index}]",
                 "source_class": "calldata", "consumer_used": producer_prefix + index in consumer_words,
                 "guard_used": producer_prefix + index in guard_words,
                 "effect_used": producer_prefix + index in effect_words}
                for index in range(direct_width)
            ]),
            "anchor_words": [unique_anchors[index] for index in sorted(unique_anchors)],
            "effects": self.trace.effects,
            "effect_word_indices": sorted(effect_words),
            "guards": self.trace.guards,
            "replay_records": replay_records,
            "limitations": sorted(self.trace.unsupported | {
                "AST_LOOP_INDEX_WIDENED_TO_PUBLIC_ARRAY_TAIL",
                "AST_FRONTEND_IS_NOT_SOLIDITY_SEMANTIC_EQUIVALENCE",
                "AST_VERIFIER_SELECTOR_PREFIX_WIDTH_DERIVED_FROM_ABI_AND_ARRAY_HEADER",
            }),
        }


def extract(combined_ast: Path, source_key: str, source: Path,
            public_leaves: list[dict[str, Any]]) -> dict[str, Any]:
    return Extractor(json.loads(combined_ast.read_text()), source_key, source, public_leaves).extract()
