#!/usr/bin/env python3
"""Bounded Solidity-AST relation extractor for the D1P-16 mint scope.

The implementation deliberately contains no WarpToad mint equations or public
input list.  It interprets the archived solc AST, follows internal calls, and
models Solidity checked arithmetic and transactional rollback.  The only
domain boundary is an external verifier call, represented as an uninterpreted
producer relation over the proof and the recovered public-word vector.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

UINT256_MAX = 2**256 - 1
EXPECTED_SOURCE_SHA256 = "323a1cf26c7449f67cf277ff0a46c31e12f725c555f9fa165d5a60011e122c39"
EXPECTED_SOLC = "0.8.29+commit.ab55807c"
EXPECTED_OPT_RUNS = 1
EXPECTED_EVM = "cancun"
DEFAULT_MODEL_TABLE = Path(__file__).with_name("library_effect_models.v1.json")


class UnsupportedConstruct(RuntimeError):
    """Named fail-closed rejection with a source location."""

    def __init__(self, kind: str, location: str, detail: str):
        self.code = f"UNSUPPORTED_{kind.upper()}"
        self.location = location
        self.detail = detail
        super().__init__(f"{self.code} at {location}: {detail}")


def E(op: str, *args: Any) -> dict[str, Any]:
    return {"op": op, "args": list(args)}


def C(value: Any) -> dict[str, Any]:
    return E("const", value)


def S(name: str) -> dict[str, Any]:
    return E("symbol", name)


def is_const(expr: Any, value: Any | None = None) -> bool:
    return isinstance(expr, dict) and expr.get("op") == "const" and (
        value is None or expr["args"][0] == value
    )


def const_value(expr: dict[str, Any]) -> Any:
    return expr["args"][0]


def simplify(op: str, *args: Any) -> dict[str, Any]:
    # Casts preserve provenance but constants may be folded for path pruning.
    if op == "cast" and is_const(args[1]):
        return C(const_value(args[1]))
    if op == "not" and is_const(args[0]):
        return C(not const_value(args[0]))
    if len(args) == 2 and is_const(args[0]) and is_const(args[1]):
        a, b = const_value(args[0]), const_value(args[1])
        table = {
            "eq": lambda: a == b,
            "neq": lambda: a != b,
            "lt": lambda: a < b,
            "le": lambda: a <= b,
            "gt": lambda: a > b,
            "ge": lambda: a >= b,
            "add": lambda: a + b,
            "sub": lambda: a - b,
            "mul": lambda: a * b,
        }
        if op in table:
            return C(table[op]())
    return E(op, *args)


def render(expr: Any) -> str:
    if isinstance(expr, list):
        return "[" + ", ".join(render(x) for x in expr) + "]"
    if not isinstance(expr, dict) or "op" not in expr:
        return repr(expr)
    op, args = expr["op"], expr["args"]
    if op == "const":
        value = args[0]
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)
    if op == "symbol":
        return str(args[0])
    if op == "storage":
        return f"pre.{args[0]}"
    if op == "map_read":
        return f"pre.{args[0]}[{render(args[1])}]"
    if op == "select":
        return f"select({render(args[0])}, {render(args[1])})"
    if op == "store":
        return f"store({render(args[0])}, {render(args[1])}, {render(args[2])})"
    if op == "cast":
        return f"{args[0]}({render(args[1])})"
    if op == "not":
        return f"not({render(args[0])})"
    infix = {
        "eq": "==", "neq": "!=", "lt": "<", "le": "<=", "gt": ">",
        "ge": ">=", "add": "+", "sub": "-", "mul": "*",
        "add_mod": "+%", "sub_mod": "-%", "mul_mod": "*%",
    }
    if op in infix:
        return f"({render(args[0])} {infix[op]} {render(args[1])})"
    if op == "relation":
        return f"{args[0]}({', '.join(render(x) for x in args[1:])})"
    return f"{op}({', '.join(render(x) for x in args)})"


def strip_casts(expr: Any) -> Any:
    while isinstance(expr, dict) and expr.get("op") == "cast":
        expr = expr["args"][1]
    return expr


@dataclass
class EvalResult:
    value: Any
    checks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecState:
    env: dict[int, Any] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)
    guards: list[dict[str, Any]] = field(default_factory=list)
    tentative_writes: list[dict[str, Any]] = field(default_factory=list)
    tentative_mints: list[dict[str, Any]] = field(default_factory=list)
    tentative_burns: list[dict[str, Any]] = field(default_factory=list)
    tentative_transfers: list[dict[str, Any]] = field(default_factory=list)
    tentative_events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"
    reason: str | None = None
    location: str | None = None

    def branch(self) -> "ExecState":
        return copy.deepcopy(self)


class Extractor:
    def __init__(
        self,
        meta_path: Path,
        output_path: Path,
        source_path: Path,
        model_path: Path = DEFAULT_MODEL_TABLE,
        expected_source_sha256: str = EXPECTED_SOURCE_SHA256,
    ):
        self.meta_path = meta_path.resolve()
        self.output_path = output_path.resolve()
        self.source_path = source_path.resolve()
        self.model_path = model_path.resolve()
        self.expected_source_sha256 = expected_source_sha256
        self.meta = json.loads(self.meta_path.read_text())
        self.output_wrapper = json.loads(self.output_path.read_text())
        self.output = self.output_wrapper["output"]
        self.effect_models = json.loads(self.model_path.read_text())
        self.nodes: dict[int, dict[str, Any]] = {}
        self.source_names: dict[int, str] = {}
        self.source_text: dict[int, str] = {}
        self.node_source: dict[int, str] = {}
        self.node_contract: dict[int, str | None] = {}
        self.call_stack: list[int] = []
        self._load_effect_models()
        self._index_sources()
        self._validate_pins()

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _load_effect_models(self) -> None:
        if self.effect_models.get("schema") != "bindcheck.library-effect-models.v1":
            raise ValueError("unsupported library effect-model schema")
        if self.effect_models.get("case_specific_entries") is not False:
            raise ValueError("case-specific library effect models are forbidden in the automatic route")
        self.call_models: dict[str, dict[str, Any]] = {}
        self.storage_models: dict[str, dict[str, Any]] = {}
        self.event_models: dict[str, dict[str, Any]] = {}
        self.library_prefixes: list[str] = []
        for library in self.effect_models.get("libraries", {}).values():
            self.library_prefixes.append(library["source_prefix"])
            for key, model in library.get("declarations", {}).items():
                self.call_models[key] = model
            for key, model in library.get("storage_declarations", {}).items():
                self.storage_models[key] = model
            for key, model in library.get("event_declarations", {}).items():
                self.event_models[key] = model
        self.external_boundaries = self.effect_models.get("external_boundaries", {})

    @staticmethod
    def _parameter_type(parameter: dict[str, Any]) -> str:
        return parameter.get("typeDescriptions", {}).get("typeString", "unknown")

    def declaration_key(self, ref: int) -> str:
        node = self.nodes.get(ref)
        if node is None:
            return f"unresolved#{ref}"
        source = self.node_source.get(ref, "unknown-source")
        contract = self.node_contract.get(ref) or "<free>"
        name = node.get("name") or node.get("nodeType", f"decl#{ref}")
        if node.get("nodeType") in {"FunctionDefinition", "EventDefinition", "ErrorDefinition"}:
            params = node.get("parameters", {}).get("parameters", [])
            signature = ",".join(self._parameter_type(param) for param in params)
            return f"{source}::{contract}::{name}({signature})"
        return f"{source}::{contract}::{name}"

    def is_library_declaration(self, ref: int) -> bool:
        source = self.node_source.get(ref, "")
        return any(source.startswith(prefix) for prefix in self.library_prefixes)

    def reject(self, kind: str, node: dict[str, Any], detail: str) -> UnsupportedConstruct:
        return UnsupportedConstruct(kind, self.location(node), detail)

    def _index_sources(self) -> None:
        inputs = self.meta["input"]["sources"]
        for name, record in self.output["sources"].items():
            source_id = record["id"]
            self.source_names[source_id] = name
            if name in inputs and "content" in inputs[name]:
                self.source_text[source_id] = inputs[name]["content"]
            self._walk_index(record["ast"], source_id, None)

    def _walk_index(self, node: Any, source_id: int, contract: str | None) -> None:
        if isinstance(node, dict):
            if node.get("nodeType") == "ContractDefinition":
                contract = node.get("name")
            if "id" in node and "nodeType" in node:
                self.nodes[node["id"]] = node
                self.node_source[node["id"]] = self.source_names[source_id]
                self.node_contract[node["id"]] = contract
            for value in node.values():
                self._walk_index(value, source_id, contract)
        elif isinstance(node, list):
            for value in node:
                self._walk_index(value, source_id, contract)

    def _validate_pins(self) -> None:
        actual_source = self.sha256(self.source_path)
        settings = self.meta["input"]["settings"]
        source_record = self.meta["input"]["sources"]["project/contracts/core/WarpToadCore.sol"]
        embedded_source_sha256 = hashlib.sha256(source_record["content"].encode()).hexdigest()
        assertions = {
            "source_sha256": actual_source == self.expected_source_sha256,
            "source_matches_build_input": actual_source == embedded_source_sha256,
            "solc": self.meta.get("solcLongVersion") == EXPECTED_SOLC,
            "optimizer_enabled": settings["optimizer"]["enabled"] is True,
            "optimizer_runs": settings["optimizer"]["runs"] == EXPECTED_OPT_RUNS,
            "evm_version": settings["evmVersion"] == EXPECTED_EVM,
            "compiler_output_id": self.meta["id"] == self.output_wrapper["id"],
            "effect_model_version": self.effect_models.get("version") == "1.0.0",
        }
        failed = [name for name, passed in assertions.items() if not passed]
        if failed:
            raise ValueError(f"pin validation failed: {', '.join(failed)}")
        self.pin_assertions = assertions

    def location(self, node: dict[str, Any]) -> str:
        start, _, source_id = map(int, node["src"].split(":"))
        text = self.source_text[source_id]
        line = text.count("\n", 0, start) + 1
        return f"{Path(self.source_names[source_id]).name}:{line}"

    def declaration_name(self, ref: int) -> str:
        node = self.nodes.get(ref, {})
        return node.get("name") or node.get("nodeType", f"decl#{ref}")

    def state_key(self, base: str, index: Any | None = None) -> str:
        return base if index is None else f"{base}[{render(index)}]"

    def read_storage(self, state: ExecState, base: str, index: Any | None = None) -> Any:
        current = state.storage.get(base, E("storage", base))
        return current if index is None else E("select", current, index)

    def eval_expr(self, node: dict[str, Any], state: ExecState, checked: bool = True) -> EvalResult:
        kind = node["nodeType"]
        if kind == "Literal":
            value: Any = node.get("value")
            if node.get("kind") == "number":
                value = int(value)
            elif node.get("kind") == "bool":
                value = value == "true" if isinstance(value, str) else bool(value)
            return EvalResult(C(value))
        if kind == "Identifier":
            ref = node.get("referencedDeclaration")
            if ref in state.env:
                return EvalResult(state.env[ref])
            decl = self.nodes.get(ref, {})
            name = node["name"]
            if decl.get("stateVariable"):
                return EvalResult(self.read_storage(state, name))
            if name in {"block", "msg"}:
                return EvalResult(S(name))
            raise self.reject("identifier", node, f"unresolved identifier {name!r}")
        if kind == "MemberAccess":
            base = self.eval_expr(node["expression"], state, checked)
            member = node["memberName"]
            if member == "length" and isinstance(base.value, list):
                return EvalResult(C(len(base.value)), base.checks)
            if render(base.value) == "block" and member in {"basefee", "chainid"}:
                return EvalResult(S(f"{render(base.value)}.{member}"), base.checks)
            if render(base.value) == "msg" and member == "sender":
                return EvalResult(S("msg.sender"), base.checks)
            raise self.reject(
                "member_access", node,
                f"no semantics for member {member!r} on {render(base.value)}",
            )
        if kind == "IndexAccess":
            base_node = node["baseExpression"]
            index = self.eval_expr(node["indexExpression"], state, checked)
            if base_node["nodeType"] == "Identifier":
                ref = base_node.get("referencedDeclaration")
                if ref in state.env and isinstance(state.env[ref], list):
                    base = state.env[ref]
                    if not is_const(index.value):
                        raise self.reject("symbolic_memory_index", node, "symbolic memory-array read")
                    return EvalResult(base[int(const_value(index.value))], index.checks)
                decl = self.nodes.get(ref, {})
                if decl.get("stateVariable"):
                    return EvalResult(
                        self.read_storage(state, base_node["name"], index.value), index.checks
                    )
            base = self.eval_expr(base_node, state, checked)
            if isinstance(base.value, list) and is_const(index.value):
                return EvalResult(base.value[int(const_value(index.value))], base.checks + index.checks)
            raise self.reject(
                "index_access", node,
                f"no semantics for index into {render(base.value)}",
            )
        if kind == "TupleExpression":
            values, checks = [], []
            for component in node["components"]:
                if component is None:
                    values.append(None)
                else:
                    item = self.eval_expr(component, state, checked)
                    values.append(item.value)
                    checks += item.checks
            if len(values) == 1:
                return EvalResult(values[0], checks)
            return EvalResult(values, checks)
        if kind == "BinaryOperation":
            left = self.eval_expr(node["leftExpression"], state, checked)
            right = self.eval_expr(node["rightExpression"], state, checked)
            a, b, token = left.value, right.value, node["operator"]
            op_map = {"==": "eq", "!=": "neq", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}
            checks = left.checks + right.checks
            if token in op_map:
                return EvalResult(simplify(op_map[token], a, b), checks)
            arithmetic = {"+": "add", "-": "sub", "*": "mul"}
            if token in arithmetic:
                op = arithmetic[token]
                value = simplify(op if checked else f"{op}_mod", a, b)
                if checked and not (is_const(a) and is_const(b)):
                    check_op = {"+": "no_overflow_add", "-": "no_underflow_sub", "*": "no_overflow_mul"}[token]
                    checks.append(E(check_op, a, b))
                return EvalResult(value, checks)
            raise self.reject("binary_operator", node, token)
        if kind == "UnaryOperation":
            sub = self.eval_expr(node["subExpression"], state, checked)
            if node["operator"] == "!":
                return EvalResult(simplify("not", sub.value), sub.checks)
            if node["operator"] == "++":
                return EvalResult(simplify("add", sub.value, C(1)), sub.checks)
            raise self.reject("unary_operator", node, node["operator"])
        if kind == "NewExpression":
            raise self.reject("new_expression", node, "standalone new expression")
        if kind == "ElementaryTypeNameExpression":
            raise self.reject("type_expression", node, node["typeName"]["name"])
        if kind == "FunctionCall":
            call_kind = node.get("kind")
            if call_kind == "typeConversion":
                if len(node.get("arguments", [])) != 1:
                    raise self.reject("type_conversion_arity", node, "expected one argument")
                conversion = node["expression"]
                target = (
                    conversion.get("typeName", {}).get("name")
                    or conversion.get("name")
                    or conversion.get("typeDescriptions", {}).get("typeString", "cast")
                )
                arg = self.eval_expr(node["arguments"][0], state, checked)
                return EvalResult(simplify("cast", target, arg.value), arg.checks)
            if node["expression"].get("nodeType") == "NewExpression":
                size = self.eval_expr(node["arguments"][0], state, checked)
                if not is_const(size.value):
                    raise self.reject("symbolic_memory_allocation", node, "array size is symbolic")
                return EvalResult([C(0) for _ in range(int(const_value(size.value)))], size.checks)
            callee_ref = node["expression"].get("referencedDeclaration")
            callee = self.nodes.get(callee_ref, {})
            args = [self.eval_expr(a, state, checked) for a in node.get("arguments", [])]
            checks = [c for item in args for c in item.checks]
            values = [item.value for item in args]
            if callee.get("nodeType") == "FunctionDefinition" and callee.get("visibility") in {"internal", "private", "public"}:
                if callee.get("stateMutability") in {"pure", "view"}:
                    value = self.eval_returning_function(callee, values, state)
                    return EvalResult(value, checks)
                raise self.reject(
                    "stateful_call_in_expression", node,
                    f"{self.declaration_key(callee_ref)} is not pure/view",
                )
            # Only the declared verifier boundary may remain relational.
            if callee.get("nodeType") == "FunctionDefinition" and callee.get("visibility") == "external":
                key = self.declaration_key(callee_ref)
                boundary = self.external_boundaries.get(key)
                if not boundary or boundary.get("semantic") != "producer_verifier_relation":
                    raise self.reject("external_call", node, f"unmodeled external callee {key}")
                target_node = node["expression"].get("expression")
                target = self.eval_expr(target_node, state, checked).value if target_node else S("external")
                flattened = []
                for value in values:
                    flattened.extend(value if isinstance(value, list) else [value])
                return EvalResult(E("relation", f"{callee.get('name')}@{render(target)}", *flattened), checks)
            if callee.get("nodeType") != "FunctionDefinition":
                raise self.reject(
                    "unresolved_callee", node,
                    f"referenced declaration {callee_ref!r} is not a function",
                )
            raise self.reject("call_expression", node, self.declaration_key(callee_ref))
        raise self.reject("expression_node", node, kind)

    def bind_params(self, function: dict[str, Any], args: list[Any], state: ExecState) -> None:
        params = function["parameters"]["parameters"]
        if len(params) != len(args):
            raise self.reject(
                "call_arity", function,
                f"{function.get('name')} expects {len(params)} arguments, got {len(args)}",
            )
        for param, value in zip(params, args):
            state.env[param["id"]] = value

    def eval_returning_function(self, function: dict[str, Any], args: list[Any], caller: ExecState) -> Any:
        state = ExecState(env=copy.deepcopy(caller.env), storage=copy.deepcopy(caller.storage))
        self.bind_params(function, args, state)
        result = self.exec_pure_block(function["body"], state)
        if result is None:
            raise self.reject(
                "missing_return", function,
                f"function {function.get('name')} produced no return",
            )
        return result

    def exec_pure_block(self, block: dict[str, Any], state: ExecState, checked: bool = True) -> Any | None:
        for stmt in block["statements"]:
            kind = stmt["nodeType"]
            if kind == "VariableDeclarationStatement":
                initial = self.eval_expr(stmt["initialValue"], state, checked).value
                declarations = [d for d in stmt["declarations"] if d is not None]
                if len(declarations) != 1:
                    raise self.reject("tuple_declaration", stmt, "pure function tuple declaration")
                state.env[declarations[0]["id"]] = initial
            elif kind == "ExpressionStatement":
                self.exec_assignment(stmt["expression"], state, checked)
            elif kind == "ForStatement":
                self.exec_pure_statement(stmt["initializationExpression"], state, checked)
                iterations = 0
                while True:
                    cond = self.eval_expr(stmt["condition"], state, checked).value
                    if not is_const(cond):
                        raise self.reject("symbolic_loop_bound", stmt, "pure loop condition is symbolic")
                    if not const_value(cond):
                        break
                    result = self.exec_pure_block(stmt["body"], state, checked)
                    if result is not None:
                        return result
                    self.exec_pure_statement(stmt["loopExpression"], state, checked)
                    iterations += 1
                    if iterations > 1024:
                        raise self.reject("loop_bound", stmt, "more than 1024 iterations")
            elif kind == "Return":
                return self.eval_expr(stmt["expression"], state, checked).value
            elif kind == "UncheckedBlock":
                result = self.exec_pure_block(stmt, state, checked=False)
                if result is not None:
                    return result
            else:
                raise self.reject("pure_statement", stmt, kind)
        return None

    def exec_pure_statement(self, stmt: dict[str, Any], state: ExecState, checked: bool) -> None:
        if stmt["nodeType"] == "VariableDeclarationStatement":
            value = self.eval_expr(stmt["initialValue"], state, checked).value
            decl = next(d for d in stmt["declarations"] if d is not None)
            state.env[decl["id"]] = value
        elif stmt["nodeType"] == "ExpressionStatement":
            expr = stmt["expression"]
            if expr["nodeType"] == "UnaryOperation" and expr["operator"] == "++":
                target = expr["subExpression"]
                ref = target["referencedDeclaration"]
                state.env[ref] = simplify("add", state.env[ref], C(1))
            else:
                self.exec_assignment(expr, state, checked)
        else:
            raise self.reject("pure_statement", stmt, stmt["nodeType"])

    def exec_assignment(self, expr: dict[str, Any], state: ExecState, checked: bool) -> None:
        if expr["nodeType"] != "Assignment":
            raise self.reject("assignment_expression", expr, expr["nodeType"])
        lhs, op = expr["leftHandSide"], expr["operator"]
        rhs = self.eval_expr(expr["rightHandSide"], state, checked).value
        if lhs["nodeType"] == "Identifier":
            ref = lhs["referencedDeclaration"]
            old = state.env.get(ref)
            if old is None and self.nodes.get(ref, {}).get("stateVariable"):
                old = self.read_storage(state, lhs["name"])
                value = self.assignment_value(op, old, rhs, checked, expr)
                self.write_storage(state, lhs["name"], None, value, expr, ref)
            else:
                state.env[ref] = self.assignment_value(op, old, rhs, checked, expr)
            return
        if lhs["nodeType"] == "IndexAccess":
            base = lhs["baseExpression"]
            index = self.eval_expr(lhs["indexExpression"], state, checked).value
            ref = base.get("referencedDeclaration")
            if ref in state.env and isinstance(state.env[ref], list):
                if not is_const(index):
                    raise self.reject("symbolic_memory_index", lhs, "symbolic memory-array write")
                state.env[ref][int(const_value(index))] = rhs
                return
            if self.nodes.get(ref, {}).get("stateVariable"):
                old = self.read_storage(state, base["name"], index)
                value = self.assignment_value(op, old, rhs, checked, expr)
                self.write_storage(state, base["name"], index, value, expr, ref)
                return
        raise self.reject("assignment_target", lhs, lhs["nodeType"])

    def assignment_value(
        self, op: str, old: Any, rhs: Any, checked: bool, node: dict[str, Any]
    ) -> Any:
        if op == "=":
            return rhs
        mapping = {"+=": "add", "-=": "sub", "*=": "mul"}
        if op not in mapping:
            raise self.reject("assignment_operator", node, op)
        base = mapping[op]
        return simplify(base if checked else f"{base}_mod", old, rhs)

    def assignment_checks(self, expr: dict[str, Any], state: ExecState, checked: bool) -> list[Any]:
        op = expr["operator"]
        if not checked or op == "=":
            return []
        lhs = expr["leftHandSide"]
        if lhs["nodeType"] == "Identifier":
            ref = lhs["referencedDeclaration"]
            old = state.env.get(ref)
            if old is None and self.nodes.get(ref, {}).get("stateVariable"):
                old = self.read_storage(state, lhs["name"])
        elif lhs["nodeType"] == "IndexAccess":
            base = lhs["baseExpression"]
            index = self.eval_expr(lhs["indexExpression"], state, checked).value
            ref = base.get("referencedDeclaration")
            if ref in state.env and isinstance(state.env[ref], list):
                old = state.env[ref][int(const_value(index))]
            elif self.nodes.get(ref, {}).get("stateVariable"):
                old = self.read_storage(state, base["name"], index)
            else:
                raise self.reject("assignment_target", lhs, "unresolved indexed assignment")
        else:
            raise self.reject("assignment_target", lhs, lhs["nodeType"])
        rhs = self.eval_expr(expr["rightHandSide"], state, checked).value
        check_ops = {"+=": "no_overflow_add", "-=": "no_underflow_sub", "*=": "no_overflow_mul"}
        if op not in check_ops:
            raise self.reject("assignment_operator", expr, op)
        check_op = check_ops[op]
        return [E(check_op, old, rhs)]

    def write_storage(
        self,
        state: ExecState,
        base: str,
        index: Any | None,
        value: Any,
        node: dict[str, Any],
        declaration_ref: int,
    ) -> None:
        declaration_key = self.declaration_key(declaration_ref)
        storage_model = self.storage_models.get(declaration_key)
        if self.is_library_declaration(declaration_ref) and storage_model is None:
            raise self.reject(
                "library_storage_write", node,
                f"no versioned storage model for {declaration_key}",
            )
        if storage_model is not None:
            supported_storage = {
                "erc20_balance_map": index is not None,
                "erc20_total_supply": index is None,
            }
            semantic = storage_model.get("semantic")
            if semantic not in supported_storage or not supported_storage[semantic]:
                raise self.reject(
                    "library_storage_model", node,
                    f"unsupported or shape-mismatched storage semantic {semantic!r}",
                )
        if index is None:
            state.storage[base] = value
        else:
            state.storage[base] = E("store", state.storage.get(base, E("storage", base)), index, value)
        record = {
            "slot": base,
            "key": None if index is None else render(index),
            "value": render(value),
            "value_ir": value,
            "location": self.location(node),
            "declaration": declaration_key,
            "effect_model": None if storage_model is None else storage_model["semantic"],
        }
        if index is not None:
            record["map_after"] = render(state.storage[base])
            record["map_after_ir"] = state.storage[base]
        state.tentative_writes.append(record)

    @staticmethod
    def _expr_key(expr: Any) -> str:
        return json.dumps(expr, sort_keys=True, separators=(",", ":"))

    def assume(self, state: ExecState, condition: Any) -> bool:
        """Add an assumption, rejecting direct syntactic contradictions."""
        if is_const(condition):
            return bool(const_value(condition))
        positive = condition
        negated = False
        if isinstance(condition, dict) and condition.get("op") == "not":
            positive = condition["args"][0]
            negated = True
        positive_key = self._expr_key(positive)
        for prior in state.guards:
            prior_positive = prior
            prior_negated = False
            if isinstance(prior, dict) and prior.get("op") == "not":
                prior_positive = prior["args"][0]
                prior_negated = True
            if self._expr_key(prior_positive) == positive_key:
                return prior_negated == negated
        state.guards.append(condition)
        return True

    def add_guard_or_revert(
        self, state: ExecState, condition: Any, reason: str, location: str
    ) -> tuple[list[ExecState], list[ExecState]]:
        if is_const(condition):
            if const_value(condition):
                return [state], []
            state.status, state.reason, state.location = "revert", reason, location
            return [], [state]
        success, failure = state.branch(), state.branch()
        success_ok = self.assume(success, condition)
        failure_ok = self.assume(failure, simplify("not", condition))
        if failure_ok:
            failure.status, failure.reason, failure.location = "revert", reason, location
        return ([success] if success_ok else []), ([failure] if failure_ok else [])

    def apply_checks(self, states: list[ExecState], checks: list[Any], location: str) -> list[ExecState]:
        current = states
        terminals: list[ExecState] = []
        for condition in checks:
            next_states: list[ExecState] = []
            for state in current:
                ok, bad = self.add_guard_or_revert(state, condition, "Panic(0x11)", location)
                next_states += ok
                terminals += bad
            current = next_states
        return current + terminals

    def exec_function_call(self, call: dict[str, Any], state: ExecState, checked: bool) -> list[ExecState]:
        callee_ref = call["expression"].get("referencedDeclaration")
        callee = self.nodes.get(callee_ref, {})
        args = [self.eval_expr(a, state, checked) for a in call.get("arguments", [])]
        checks = [check for item in args for check in item.checks]
        checked_states = self.apply_checks([state], checks, self.location(call))
        output: list[ExecState] = [s for s in checked_states if s.status != "active"]
        for active in [s for s in checked_states if s.status == "active"]:
            if callee.get("nodeType") != "FunctionDefinition":
                raise self.reject(
                    "unresolved_callee", call,
                    f"referenced declaration {callee_ref!r} is not a function",
                )
            if callee.get("visibility") == "external":
                raise self.reject(
                    "external_call_statement", call,
                    f"external call {self.declaration_key(callee_ref)} is not a checked verifier expression",
                )
            if callee.get("visibility") not in {"internal", "private", "public"}:
                raise self.reject(
                    "call_visibility", call,
                    f"{self.declaration_key(callee_ref)} visibility={callee.get('visibility')}",
                )
            key = self.declaration_key(callee_ref)
            model = self.call_models.get(key)
            if self.is_library_declaration(callee_ref) and model is None:
                raise self.reject("library_call", call, f"no versioned declaration model for {key}")
            if model is not None:
                semantic = model["semantic"]
                common = {
                    "location": self.location(call),
                    "declaration": key,
                    "effect_model": semantic,
                }
                if semantic == "erc20_mint":
                    active.tentative_mints.append({
                        **common,
                        "beneficiary": args[model["beneficiary_argument"]].value,
                        "amount": args[model["amount_argument"]].value,
                    })
                elif semantic == "erc20_burn":
                    active.tentative_burns.append({
                        **common,
                        "beneficiary": args[model["beneficiary_argument"]].value,
                        "amount": args[model["amount_argument"]].value,
                    })
                elif semantic == "erc20_transfer":
                    active.tentative_transfers.append({
                        **common,
                        "from": args[model["from_argument"]].value,
                        "to": args[model["to_argument"]].value,
                        "amount": args[model["amount_argument"]].value,
                    })
                elif semantic != "erc20_update":
                    raise self.reject("effect_model", call, f"unknown semantic {semantic!r}")
                if model.get("inline_body") is not True:
                    raise self.reject("effect_model", call, f"{key} does not permit body inlining")
            if callee_ref in self.call_stack:
                raise self.reject("recursive_call", call, key)
            if not callee.get("body"):
                raise self.reject("unimplemented_callee", call, key)
            saved_env = active.env
            active.env = copy.deepcopy(saved_env)
            self.bind_params(callee, [x.value for x in args], active)
            self.call_stack.append(callee_ref)
            try:
                called = self.exec_block([active], callee["body"], checked=True)
            finally:
                self.call_stack.pop()
            for result in called:
                result.env = copy.deepcopy(saved_env)
            output += called
        return output

    def exec_statement(self, state: ExecState, stmt: dict[str, Any], checked: bool) -> list[ExecState]:
        kind = stmt["nodeType"]
        if kind == "VariableDeclarationStatement":
            value = self.eval_expr(stmt["initialValue"], state, checked)
            states = self.apply_checks([state], value.checks, self.location(stmt))
            for active in [s for s in states if s.status == "active"]:
                decl = next(d for d in stmt["declarations"] if d is not None)
                active.env[decl["id"]] = value.value
            return states
        if kind == "ExpressionStatement":
            expr = stmt["expression"]
            if expr["nodeType"] == "FunctionCall":
                target = expr["expression"]
                if target.get("nodeType") == "Identifier" and target.get("name") == "require":
                    condition = self.eval_expr(expr["arguments"][0], state, checked)
                    states = self.apply_checks([state], condition.checks, self.location(stmt))
                    out: list[ExecState] = [s for s in states if s.status != "active"]
                    reason = expr["arguments"][1].get("value", "require") if len(expr["arguments"]) > 1 else "require"
                    for active in [s for s in states if s.status == "active"]:
                        ok, bad = self.add_guard_or_revert(active, condition.value, reason, self.location(stmt))
                        out += ok + bad
                    return out
                return self.exec_function_call(expr, state, checked)
            if expr["nodeType"] == "Assignment":
                rhs = self.eval_expr(expr["rightHandSide"], state, checked)
                checks = rhs.checks + self.assignment_checks(expr, state, checked)
                states = self.apply_checks([state], checks, self.location(stmt))
                for active in [s for s in states if s.status == "active"]:
                    # Re-evaluate on the branched state before writing.
                    self.exec_assignment(expr, active, checked)
                return states
            raise self.reject("expression_statement", expr, expr["nodeType"])
        if kind == "IfStatement":
            condition = self.eval_expr(stmt["condition"], state, checked)
            states = self.apply_checks([state], condition.checks, self.location(stmt))
            output: list[ExecState] = [s for s in states if s.status != "active"]
            for active in [s for s in states if s.status == "active"]:
                if is_const(condition.value):
                    chosen = stmt["trueBody"] if const_value(condition.value) else stmt.get("falseBody")
                    if chosen is None:
                        output.append(active)
                    else:
                        output += self.exec_block([active], chosen, checked)
                else:
                    yes, no = active.branch(), active.branch()
                    if self.assume(yes, condition.value):
                        output += self.exec_block([yes], stmt["trueBody"], checked)
                    if self.assume(no, simplify("not", condition.value)):
                        if stmt.get("falseBody") is not None:
                            output += self.exec_block([no], stmt["falseBody"], checked)
                        else:
                            output.append(no)
            return output
        if kind == "UncheckedBlock":
            return self.exec_block([state], stmt, checked=False)
        if kind == "RevertStatement":
            call = stmt["errorCall"]
            callee = call["expression"]
            state.status = "revert"
            state.reason = callee.get("name", "revert")
            state.location = self.location(stmt)
            return [state]
        if kind == "EmitStatement":
            call = stmt["eventCall"]
            event_ref = call["expression"].get("referencedDeclaration")
            event_declaration = self.nodes.get(event_ref, {})
            if event_declaration.get("nodeType") != "EventDefinition":
                raise self.reject(
                    "unresolved_event", stmt,
                    f"referenced declaration {event_ref!r} is not an event",
                )
            event_key = self.declaration_key(event_ref)
            event_model = self.event_models.get(event_key)
            if self.is_library_declaration(event_ref) and event_model is None:
                raise self.reject(
                    "library_event", stmt,
                    f"no versioned event model for {event_key}",
                )
            if event_model is not None and event_model.get("semantic") != "erc20_transfer_event":
                raise self.reject(
                    "library_event_model", stmt,
                    f"unsupported event semantic {event_model.get('semantic')!r}",
                )
            evaluated = [self.eval_expr(a, state, checked) for a in call["arguments"]]
            checks = [check for item in evaluated for check in item.checks]
            states = self.apply_checks([state], checks, self.location(stmt))
            for active in [candidate for candidate in states if candidate.status == "active"]:
                active.tentative_events.append({
                    "event": call["expression"].get("name", "event"),
                    "arguments": [render(item.value) for item in evaluated],
                    "location": self.location(stmt),
                    "declaration": event_key,
                    "effect_model": None if event_model is None else event_model["semantic"],
                })
            return states
        raise self.reject("statement_node", stmt, kind)

    def exec_block(self, states: list[ExecState], block: dict[str, Any], checked: bool) -> list[ExecState]:
        current = states
        for stmt in block["statements"]:
            next_states: list[ExecState] = [s for s in current if s.status != "active"]
            for state in [s for s in current if s.status == "active"]:
                next_states += self.exec_statement(state, stmt, checked)
            current = next_states
        return current

    def find_function(self, source_name: str, contract_name: str, function_name: str) -> dict[str, Any]:
        ast = self.output["sources"][source_name]["ast"]
        for contract in ast["nodes"]:
            if contract.get("nodeType") == "ContractDefinition" and contract.get("name") == contract_name:
                matches = [
                    n for n in contract["nodes"]
                    if n.get("nodeType") == "FunctionDefinition" and n.get("name") == function_name
                ]
                if len(matches) != 1:
                    raise ValueError(f"expected one {contract_name}.{function_name}, found {len(matches)}")
                return matches[0]
        raise ValueError(f"contract {contract_name} not found")

    def extract(self) -> dict[str, Any]:
        source_name = "project/contracts/core/WarpToadCore.sol"
        mint = self.find_function(source_name, "WarpToadCore", "mint")
        initial = ExecState()
        params = mint["parameters"]["parameters"]
        for param in params:
            initial.env[param["id"]] = S(f"calldata.{param['name']}")
        paths = self.exec_block([initial], mint["body"], checked=True)
        for state in paths:
            if state.status == "active":
                state.status = "success"

        verifier_relations = []
        for state in paths:
            for guard in state.guards:
                if guard.get("op") == "relation":
                    verifier_relations.append(guard)
        if not verifier_relations:
            raise ValueError("no verifier boundary recovered")
        first = verifier_relations[0]
        public_words = first["args"][2:]
        if len(public_words) != 11:
            raise ValueError(f"expected source-derived 11 public words, got {len(public_words)}")

        def path_record(index: int, state: ExecState) -> dict[str, Any]:
            committed = state.status == "success"
            enriched_mints = [
                {
                    "beneficiary": render(mint["beneficiary"]),
                    "amount": render(mint["amount"]),
                    "location": mint["location"],
                    "beneficiary_ir": mint["beneficiary"],
                    "amount_ir": mint["amount"],
                    "declaration": mint["declaration"],
                    "effect_model": mint["effect_model"],
                }
                for mint in state.tentative_mints
            ]
            enriched_burns = [
                {
                    "beneficiary": render(burn["beneficiary"]),
                    "amount": render(burn["amount"]),
                    "location": burn["location"],
                    "beneficiary_ir": burn["beneficiary"],
                    "amount_ir": burn["amount"],
                    "declaration": burn["declaration"],
                    "effect_model": burn["effect_model"],
                }
                for burn in state.tentative_burns
            ]
            enriched_transfers = [
                {
                    "from": render(transfer["from"]),
                    "to": render(transfer["to"]),
                    "amount": render(transfer["amount"]),
                    "location": transfer["location"],
                    "from_ir": transfer["from"],
                    "to_ir": transfer["to"],
                    "amount_ir": transfer["amount"],
                    "declaration": transfer["declaration"],
                    "effect_model": transfer["effect_model"],
                }
                for transfer in state.tentative_transfers
            ]
            return {
                "id": f"p{index:02d}",
                "status": state.status,
                "guards": [render(x) for x in state.guards],
                "guards_ir": state.guards,
                "revert": None if committed else {"reason": state.reason, "location": state.location},
                "tentative": {
                    "storage_writes": state.tentative_writes,
                    "mints": enriched_mints,
                    "burns": enriched_burns,
                    "transfers": enriched_transfers,
                    "events": state.tentative_events,
                },
                "committed": {
                    "storage_writes": state.tentative_writes if committed else [],
                    "mints": enriched_mints if committed else [],
                    "burns": enriched_burns if committed else [],
                    "transfers": enriched_transfers if committed else [],
                    "events": state.tentative_events if committed else [],
                    "post_state_ir": state.storage if committed else {},
                },
                "rollback": not committed,
            }

        return {
            "schema": "bindcheck.d1p18.extracted-consumer-relation.v2",
            "scope": "WarpToadCore.mint",
            "method": "solc AST bounded symbolic execution; internal-call inlining",
            "pins": {
                "source": str(self.source_path),
                "source_sha256": self.sha256(self.source_path),
                "build_info": str(self.meta_path),
                "build_info_sha256": self.sha256(self.meta_path),
                "compiler_output": str(self.output_path),
                "compiler_output_sha256": self.sha256(self.output_path),
                "solc": self.meta["solcLongVersion"],
                "optimizer": self.meta["input"]["settings"]["optimizer"],
                "evm_version": self.meta["input"]["settings"]["evmVersion"],
                "assertions": self.pin_assertions,
                "library_effect_models": str(self.model_path),
                "library_effect_models_sha256": self.sha256(self.model_path),
                "library_effect_models_version": self.effect_models["version"],
                "case_specific_effect_models": self.effect_models["case_specific_entries"],
            },
            "verifier_boundary": {
                "kind": "uninterpreted producer relation; never assumed true",
                "declaration": self.declaration_key(
                    next(
                        ref for ref, node in self.nodes.items()
                        if node.get("nodeType") == "FunctionDefinition"
                        and node.get("visibility") == "external"
                        and self.declaration_key(ref) in self.external_boundaries
                    )
                ),
                "expression": render(first),
                "proof": render(first["args"][1]),
                "public_words": [
                    {
                        "index": i,
                        "expression": render(word),
                        "origin": render(strip_casts(word)),
                        "expression_ir": word,
                    }
                    for i, word in enumerate(public_words)
                ],
            },
            "paths": [path_record(i, state) for i, state in enumerate(paths)],
            "summary": {
                "path_count": len(paths),
                "success_paths": sum(s.status == "success" for s in paths),
                "revert_paths": sum(s.status == "revert" for s in paths),
                "all_reverts_commit_nothing": all(
                    not path_record(i, s)["committed"]["storage_writes"]
                    and not path_record(i, s)["committed"]["mints"]
                    and not path_record(i, s)["committed"]["burns"]
                    and not path_record(i, s)["committed"]["transfers"]
                    and not path_record(i, s)["committed"]["events"]
                    for i, s in enumerate(paths) if s.status == "revert"
                ),
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-info", type=Path, required=True)
    parser.add_argument("--compiler-output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--effect-models", type=Path, default=DEFAULT_MODEL_TABLE)
    parser.add_argument("--expected-source-sha256", default=EXPECTED_SOURCE_SHA256)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true", help="omit evaluator IR and verbose map snapshots")
    args = parser.parse_args()
    relation = Extractor(
        args.build_info,
        args.compiler_output,
        args.source,
        model_path=args.effect_models,
        expected_source_sha256=args.expected_source_sha256,
    ).extract()
    if args.compact:
        def compact(value: Any) -> Any:
            if isinstance(value, list):
                return [compact(item) for item in value]
            if isinstance(value, dict):
                return {
                    key: compact(item)
                    for key, item in value.items()
                    if not key.endswith("_ir") and key != "map_after"
                }
            return value
        relation = compact(relation)
    encoded = json.dumps(relation, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
