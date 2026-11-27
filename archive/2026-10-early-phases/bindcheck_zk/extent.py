"""E1 screening of a proof-committed array against a consumer's prefix loop.

This module recognizes a restricted Solidity source fragment. Circuit padding,
protocol obligations and verifier correspondence are separate evidence.
"""
from __future__ import annotations

import dataclasses
import re
from typing import Any

from .models import location, result
from .solidity import EFFECT_NAME, Call, Function, balanced, functions, mask_comments_and_strings, split_top_level


PATTERN = "P1-EXTENT"
NAME = r"[A-Za-z_]\w*"
WORD = r"(?:uint(?:256)?|bytes32)"
NUMBER = r"(?:0|[1-9][0-9]{0,77})"
LIMIT = rf"(?:{NAME}(?:\.length)?|{NUMBER})"
ARRAY = rf"{WORD}\[({NAME}|{NUMBER})\]calldata"
DECLARATION = rf"(uint(?:\d+)?|bytes32|address|bool)\s+({NAME})(?:\s*=\s*(.+))?"
VECTOR = rf"{WORD}\s*\[\s*({NAME}|{NUMBER})\s*\]\s+memory\s+({NAME})\s*=\s*(\[.+\])"
CONTRACT = re.compile(rf"\b(?:contract|library)\s+{NAME}\s*\{{")
LOOP = re.compile(
    rf"for\(uint(?:256)?({NAME})=({LIMIT});\1<({LIMIT});(?:\1\+\+|\+\+\1)\)"
)
WRITE = re.compile(rf"({NAME})(?:\[(.+?)\])?(\+=|-=|=(?!=))(.+)")
ASSEMBLY = re.compile(r"\bassembly\b")
ASSEMBLY_VERIFIER = re.compile(r"\bstaticcall\s*\(\s*gas\s*\(\s*\)\s*,\s*\w*verif\w*\b", re.I)
LOOP_HINT = re.compile(r"\b(?:for|while)\s*\(")
STATEMENT_TOKEN = re.compile(r"[(){\[\]};]")


@dataclasses.dataclass(frozen=True)
class Statement:
    text: str
    offset: int
    body: str | None = None


@dataclasses.dataclass(frozen=True)
class Scope:
    constants: dict[str, int]
    storage: dict[str, bool]  # True for mappings, False for scalar words
    helpers: dict[str, list[Function]]
    external_methods: dict[str, set[str]]


@dataclasses.dataclass(frozen=True)
class Commitment:
    arrays: frozenset[str]
    length: int


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _statements(body: str) -> list[Statement] | None:
    statements = []
    start = 0
    pos = 0
    while (token := STATEMENT_TOKEN.search(body, pos)) is not None:
        pos = token.start()
        char = body[pos]
        if char in "([":
            parsed = balanced(body, pos, char, ")" if char == "(" else "]")
            if parsed is None:
                return None
            _, pos = parsed
            continue
        if char == "{":
            parsed = balanced(body, pos, "{", "}")
            if parsed is None:
                return None
            content, end = parsed
        elif char == ";":
            content, end = None, pos + 1
        else:
            return None
        raw = body[start:pos]
        statements.append(Statement(raw.strip(), start + len(raw) - len(raw.lstrip()), content))
        start = pos = end
    return statements if not body[start:].strip() else None


def _scope(source: str, function: Function) -> Scope | None:
    masked = mask_comments_and_strings(source)
    contracts = list(CONTRACT.finditer(masked, 0, function.start))
    if not contracts:
        return None
    start = contracts[-1].end()
    parsed = balanced(masked, start - 1, "{", "}")
    if parsed is None or parsed[1] <= function.start:
        return None
    statements = _statements(parsed[0])
    if statements is None:
        return None
    constants = {}
    storage = {}
    receivers = {}
    for statement in statements:
        if statement.body is not None:
            continue
        if match := re.fullmatch(
            rf"{WORD}\s+(?:(?:public|private|internal)\s+)?constant\s+({NAME})\s*=\s*({NUMBER})",
            statement.text,
        ):
            constants[match[1]] = int(match[2])
        if match := re.fullmatch(
            rf"(mapping\s*\([^;]+\)|{WORD})(?:\s+(?:public|private|internal))*\s+({NAME})",
            statement.text,
        ):
            storage[match[2]] = match[1].startswith("mapping")
        if match := re.fullmatch(
            rf"({NAME})(?:\s+(?:public|private|internal|immutable))*\s+({NAME})",
            statement.text,
        ):
            receivers[match[2]] = match[1]
    helpers: dict[str, list[Function]] = {}
    for helper in functions(parsed[0]):
        helpers.setdefault(helper.name, []).append(helper)
    external_methods = {}
    for receiver, type_name in receivers.items():
        interfaces = list(re.finditer(rf"\binterface\s+{type_name}\s*\{{", masked))
        if len(interfaces) != 1:
            continue
        interface = balanced(masked, interfaces[0].end() - 1, "{", "}")
        if interface is None:
            continue
        declarations = list(re.finditer(rf"\bfunction\s+({NAME})\s*\([^;]*;", interface[0]))
        external_methods[receiver] = {
            method[1] for method in declarations if not re.search(r"\b(?:view|pure)\b", method[0])
        } - {method[1] for method in declarations if re.search(r"\b(?:view|pure)\b", method[0])}
    return Scope(constants, storage, helpers, external_methods)


def _number(expression: str, scope: Scope, arrays: dict[str, int] | None = None) -> int | None:
    if re.fullmatch(NUMBER, expression):
        return int(expression)
    if arrays is not None and expression.endswith(".length"):
        return arrays.get(expression.removesuffix(".length"))
    return scope.constants.get(expression)


def _array_lengths(function: Function, scope: Scope) -> dict[str, int]:
    arrays = {}
    for name, description in function.parameters.items():
        match = re.fullmatch(ARRAY, _compact(description))
        if match and (length := _number(match[1], scope)) is not None and length > 0:
            arrays[name] = length
    return arrays


def _arguments(expression: str, callee: str) -> list[str] | None:
    match = re.match(callee + r"\(", expression)
    if not match:
        return None
    parsed = balanced(expression, match.end() - 1)
    return split_top_level(parsed[0]) if parsed and parsed[1] == len(expression) else None


def _hash_inputs(expression: str) -> list[str] | None:
    # Limit encoding to ABI-framed word values and fixed arrays.
    if args := _arguments(expression, r"(?:keccak256|sha256)"):
        if len(args) == 1:
            return _arguments(args[0], r"abi\.encode")
    return None


def _digest_inputs(expression: str) -> list[str] | None:
    if inputs := _hash_inputs(expression):
        return inputs
    args = _arguments(expression, rf"{NAME}\.poseidon")
    if args and len(args) == 1:
        if args[0].startswith("[") and args[0].endswith("]"):
            return split_top_level(args[0][1:-1])
        return args
    return None


def _helper_commitment(helper: Function, scope: Scope) -> Commitment | None:
    header_end = balanced(helper.header, helper.header.index("("))
    if header_end is None or not re.fullmatch(
        rf"\s*(?:private|internal)\s+(?:pure|view)\s+returns\s*\(\s*{WORD}\s*\)\s*",
        helper.header[header_end[1]:],
    ):
        return None
    statements = _statements(mask_comments_and_strings(helper.body))
    if statements is None or len(statements) != 3:
        return None
    allocation, loop, returned = statements
    hashes = re.fullmatch(rf"{WORD}\s*\[\s*({NAME}|{NUMBER})\s*\]\s+memory\s+({NAME})", allocation.text)
    index = LOOP.fullmatch(_compact(loop.text))
    if not hashes or not index or index[2] != "0" or loop.body is None:
        return None
    arrays = _array_lengths(helper, scope)
    length = _number(index[3], scope, arrays)
    if length is None or length != _number(hashes[1], scope):
        return None
    assignment = WRITE.fullmatch(_compact(loop.body).removesuffix(";"))
    if not assignment or assignment[1] != hashes[2] or assignment[2] != index[1] or assignment[3] != "=":
        return None
    inputs = _digest_inputs(assignment[4])
    if not inputs or not returned.text.startswith("return "):
        return None
    if _digest_inputs(_compact(returned.text[7:])) != [hashes[2]]:
        return None
    row_arrays = set()
    for value in inputs:
        element = re.fullmatch(rf"({NAME})\[{index[1]}\]", value)
        if not element or arrays.get(element[1]) != length:
            return None
        row_arrays.add(element[1])
    return Commitment(frozenset(row_arrays), length)


def _commitment(expression: str, scope: Scope, arrays: dict[str, int]) -> Commitment | None:
    casts = _arguments(expression, r"uint256")
    if casts and len(casts) == 1:
        expression = casts[0]
    if inputs := _hash_inputs(expression):
        lengths = {arrays.get(value) for value in inputs}
        if len(lengths) == 1 and None not in lengths:
            return Commitment(frozenset(inputs), arrays[inputs[0]])
        return None
    call = re.match(rf"({NAME})\(", expression)
    if not call or len(scope.helpers.get(call[1], [])) != 1:
        return None
    helper = scope.helpers[call[1]][0]
    arguments = _arguments(expression, call[1])
    if arguments is None or len(arguments) != len(helper.parameters):
        return None
    summary = _helper_commitment(helper, scope)
    if summary is None:
        return None
    parameter_lengths = _array_lengths(helper, scope)
    for parameter, argument in zip(helper.parameters, arguments):
        if argument not in arrays or arrays[argument] != parameter_lengths.get(parameter):
            return None
    bindings = dict(zip(helper.parameters, arguments))
    return Commitment(frozenset(bindings[name] for name in summary.arrays), summary.length)


def _atom(expression: str) -> str | None:
    """Peel explicit conversions for row dependency only."""
    while args := _arguments(expression, r"(?:address|uint(?:8|16|32|64|128|160|256)?|bytes32)"):
        if len(args) != 1:
            return None
        expression = args[0]
    if re.fullmatch(rf"{NAME}(?:\[(?:{NAME}|{NUMBER})\])?|{NUMBER}", expression):
        return expression
    return None


def _state_write(expression: str, scope: Scope, locals_: dict[str, str]) -> tuple[str, ...] | None:
    write = WRITE.fullmatch(expression)
    if not write or write[1] in locals_ or scope.storage.get(write[1]) != (write[2] is not None):
        return None
    values = tuple(value for value in (write[2], write[4]) if value is not None)
    return values if all(_atom(value) is not None for value in values) else None


def _condition(expression: str, index: str, arrays: frozenset[str]) -> tuple[str, str] | None:
    found = re.fullmatch(rf"({NAME})\[{index}\]==({NUMBER})", expression)
    if found and found[1] in arrays:
        return found[1], found[2]
    return None


def _external_arguments(expression: str, scope: Scope) -> list[str] | None:
    call = re.match(rf"({NAME})\.({NAME})\(", expression)
    if not call:
        return None
    receiver, method = call.groups()
    methods = scope.external_methods.get(receiver)
    if methods is not None:
        supported = method in methods
    else:
        supported = EFFECT_NAME.fullmatch(f"{method}(") is not None
    return _arguments(expression, re.escape(f"{receiver}.{method}")) if supported else None


def _effects(
    body: str, index: str, arrays: frozenset[str], scope: Scope, locals_: dict[str, str],
    guard: tuple[str, str] | None = None,
) -> list[tuple[str, str] | None] | None:
    local = {**locals_, index: index}
    row_values = {f"{array}[{index}]" for array in arrays}
    effects = []
    statements = _statements(body)
    if statements is None:
        return None
    for statement in statements:
        expression = _compact(statement.text)
        if statement.body is not None:
            args = _arguments(expression, "if")
            condition = _condition(args[0], index, arrays) if args and len(args) == 1 else None
            if guard is not None or condition is None:
                return None
            nested = _effects(statement.body, index, arrays, scope, local, condition)
            if nested is None:
                return None
            effects.extend(nested)
            continue
        if declaration := re.fullmatch(DECLARATION, statement.text, re.S):
            _, name, value = declaration.groups()
            if value is None or name in local:
                return None
            value = _atom(_compact(value))
            if value is None:
                return None
            local[name] = local.get(value, value)
            continue
        values = _state_write(expression, scope, local)
        if values is None:
            required = _arguments(expression, "require")
            call = required[0] if required else expression
            values = _external_arguments(call, scope)
        atoms = [_atom(value) for value in values] if values is not None else None
        if atoms is None or None in atoms:
            return None
        if not any(local.get(atom, atom) in row_values for atom in atoms):
            # Other state effects in the same loop still need the tail guard.
            if guard is None:
                return None
        effects.append(guard)
    return effects


def _tail_conditions(
    tail: Statement, bound: str, commitment: Commitment, scope: Scope, arrays: dict[str, int],
) -> list[tuple[str, str]]:
    loop = LOOP.fullmatch(_compact(tail.text))
    if not loop or tail.body is None or loop[2] != bound or _number(loop[3], scope, arrays) != commitment.length:
        return []
    statements = _statements(tail.body)
    if not statements:
        return []
    conditions = []
    for statement in statements:
        args = _arguments(_compact(statement.text), "require")
        if not args or statement.body is not None:
            return []
        for term in args[0].split("&&"):
            condition = _condition(term, loop[1], commitment.arrays)
            if condition is None:
                return []
            conditions.append(condition)
    return conditions


def _verifier_vector(statement: Statement, call: Call, locals_: dict[str, str]) -> list[str] | None:
    if statement.body is not None or not call.receiver or not call.args:
        return None
    required = _arguments(_compact(statement.text), "require")
    if not required:
        return None
    arguments = _arguments(required[0], rf"{re.escape(call.receiver)}\.{re.escape(call.name)}")
    if arguments != [_compact(arg) for arg in call.args]:
        return None
    if any(not re.fullmatch(NAME, arg) for arg in arguments[:-1]):
        return None
    expression = locals_.get(arguments[-1], arguments[-1])
    if expression.startswith("[") and expression.endswith("]"):
        return split_top_level(expression[1:-1])
    return None


def _depends_on(expression: str, source: str, aliases: dict[str, str]) -> bool:
    pending = re.findall(NAME, expression)
    seen = set()
    while pending:
        name = pending.pop()
        if name == source:
            return True
        if name not in seen and name in aliases:
            seen.add(name)
            pending.extend(re.findall(NAME, aliases[name]))
    return False


def _interval(
    conditions: list[str], bound: str, scope: Scope, arrays: dict[str, int],
    aliases: dict[str, str], type_maximum: int,
) -> tuple[int, int] | None:
    low, high = 0, type_maximum
    for condition in conditions:
        match = re.fullmatch(rf"({LIMIT})(==|<=|>=|<|>)({LIMIT})", condition)
        if not match:
            return None
        left, right = aliases.get(match[1], match[1]), aliases.get(match[3], match[3])
        if bound not in (left, right):
            return None
        operator = match[2]
        other = right
        if bound == right:
            operator = operator.translate(str.maketrans("<>", "><"))
            other = left
        number = _number(other, scope, arrays)
        if number is None:
            return None
        if operator in ("==", ">=", ">"):
            low = max(low, number + (operator == ">"))
        if operator in ("==", "<=", "<"):
            high = min(high, number - (operator == "<"))
    return (low, high) if low <= high else None


def _finding(path: str, line: int, function: Function, reason: str, message: str, *,
             verdict: str = "UNKNOWN", facts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        **result(
            PATTERN, verdict, reason, message, where=location(path, line), facts=facts,
            grade="E0" if verdict == "UNKNOWN" else "E1",
            assumptions=[
                "Matched verifier authenticates its public-input vector.",
                "Recognized hash operations bind complete encoded rows under collision resistance.",
            ] if facts else [],
            limitations=[
                "Checks consumer extent in the supported Solidity subset. Circuit padding, "
                "reachable effects, and protocol-required obligations need separate evidence."
            ],
        ),
        "function": function.name,
    }


def analyze_consumer(path: str, source: str, function: Function, calls: list[Call]) -> dict[str, Any] | None:
    body = mask_comments_and_strings(function.body)
    loop_hint = LOOP_HINT.search(body)
    if not loop_hint:
        return None

    def report(reason: str, message: str, *, offset: int = loop_hint.start(),
               verdict: str = "UNKNOWN", facts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        line = function.line + function.header.count("\n") + body.count("\n", 0, offset)
        return _finding(path, line, function, reason, message, verdict=verdict, facts=facts)

    if ASSEMBLY.search(body):
        return report("EXTENT_INLINE_ASSEMBLY_UNSUPPORTED", "Assembly can affect verifier inputs or loop bounds.")
    header_end = balanced(function.header, function.header.index("("))
    if header_end is None or not re.fullmatch(
        r"\s*(?:external|public)(?:\s+payable)?\s*", function.header[header_end[1]:],
    ):
        return report("EXTENT_ENTRY_CONTEXT_UNSUPPORTED", "Could not resolve the consumer entry point or its modifiers.")
    statements = _statements(body)
    scope = _scope(source, function)
    if statements is None or scope is None:
        return report("EXTENT_STRUCTURE_PARSE_INCOMPLETE", "Could not recover the enclosing contract or consumer statements.")
    if len(calls) != 1:
        return report("EXTENT_VERIFIER_CORRESPONDENCE_UNRESOLVED", "Expected one recovered verifier call.")

    call = calls[0]
    arrays = _array_lengths(function, scope)
    locals_ = {name: name for name in function.parameters}
    unmodeled_initializers = set()
    conditions = []
    loops = []
    public_values = []
    verifier_aliases = {}
    checked = False
    unsupported = False
    for statement in statements:
        text = _compact(statement.text)
        if statement.body is not None:
            if LOOP.fullmatch(text) and checked:
                loops.append(statement)
            else:
                unsupported = True
            continue
        if statement.offset <= call.offset < statement.offset + len(statement.text):
            vector = _verifier_vector(statement, call, locals_)
            verifier_aliases = locals_.copy()
            public_values = [verifier_aliases.get(value, value) for value in vector or []]
            checked = True
            continue
        if args := _arguments(text, "require"):
            conditions.extend(args[0].split("&&"))
        elif declared := re.fullmatch(VECTOR, statement.text, re.S):
            length, name, value = declared.groups()
            values = split_top_level(value[1:-1])
            if name in locals_ or _number(length, scope) != len(values):
                unsupported = True
                continue
            locals_[name] = _compact(value)
        elif scalar := re.fullmatch(DECLARATION, statement.text, re.S):
            kind, name, value = scalar.groups()
            if value is None or name in locals_ or name in scope.constants:
                unsupported = True
                continue
            # Resolve copies of full-width scalar values without peeling casts.
            value = _compact(value)
            if kind in ("uint", "uint256", "bytes32"):
                value = locals_.get(value, value)
            locals_[name] = value
            if _atom(value) is None and _number(value, scope, arrays) is None and not _commitment(value, scope, arrays):
                unmodeled_initializers.add(name)
        elif _state_write(text, scope, locals_) is None:
            unsupported = True

    if not public_values:
        return report("EXTENT_PUBLIC_VECTOR_UNSUPPORTED", "Could not recover a checked verifier vector with fixed item positions.")
    committed = [_commitment(value, scope, arrays) for value in public_values]
    commitments = [summary for summary in committed if summary is not None]
    if len(commitments) != 1:
        return report("EXTENT_COMMITMENT_CORRESPONDENCE_UNRESOLVED", "Could not recover one full-array commitment in the verifier vector.")
    commitment = commitments[0]
    if unsupported:
        return report("EXTENT_CONTROL_FLOW_UNSUPPORTED", "An unmodeled statement may affect proof coverage, settlement, or reachability.")

    prefixes = []
    tails = []
    for statement in loops:
        loop = LOOP.fullmatch(_compact(statement.text))
        assert loop is not None and statement.body is not None
        if loop[1] in locals_ or loop[1] in scope.constants or loop[1] in scope.storage:
            return report("EXTENT_LOOP_SCOPE_UNSUPPORTED", "The loop counter shadows an enclosing declaration.")
        if loop[2] == "0":
            prefixes.append((statement, loop[1], loop[3]))
        else:
            tails.append(statement)
    if len(prefixes) != 1:
        return report("EXTENT_SETTLEMENT_LOOP_UNSUPPORTED", "Expected one zero-based settlement loop after verification.")
    prefix, index, bound = prefixes[0]
    effect_guards = _effects(prefix.body, index, commitment.arrays, scope, locals_)
    if not effect_guards:
        return report("EXTENT_EFFECT_UNSUPPORTED", "Could not recover an effect over the committed rows.", offset=prefix.offset)

    origin = locals_.get(bound, bound)
    bound_type = function.parameters.get(origin, "")
    width = re.fullmatch(r"uint(8|16|32|64|128|160|256)?", bound_type)
    length = commitment.length
    if width:
        interval = _interval(conditions, origin, scope, arrays, locals_, 2 ** int(width[1] or 256) - 1)
    elif (number := _number(origin, scope, arrays)) is not None and not conditions:
        interval = (number, number)
    else:
        interval = None
    if interval is None:
        return report("EXTENT_BOUND_SOURCE_UNSUPPORTED", "Could not resolve the loop bound or its reachable range.", offset=prefix.offset)
    if unmodeled_initializers:
        return report("EXTENT_CONTROL_FLOW_UNSUPPORTED", "An unmodeled initializer may affect consumer reachability.")

    verifier_line = function.line + function.header.count("\n") + call.line - 1
    facts = [
        {"kind": "commitment", "arrays": sorted(commitment.arrays), "length": length,
         "verifier_location": location(path, verifier_line)},
        {"kind": "settlement_prefix", "bound": bound, "source": origin, "range": list(interval)},
    ]
    tail_facts = [_tail_conditions(tail, bound, commitment, scope, arrays) for tail in tails]
    if any(not terms for terms in tail_facts):
        return report("EXTENT_TAIL_CONTROL_UNSUPPORTED", "Another loop may affect the omitted extent.", offset=prefix.offset)
    if interval == (length, length):
        return report("EXTENT_BOUND_EQUALS_COMMITMENT", "The settlement bound equals the committed array length.",
                      offset=prefix.offset, verdict="VERIFIED_WITHIN_SCOPE", facts=facts)

    neutral_conditions = {condition for terms in tail_facts for condition in terms}
    if len({array for array, _ in neutral_conditions}) < len(neutral_conditions):
        return report("EXTENT_TAIL_FEASIBILITY_UNRESOLVED", "Tail checks impose contradictory conditions on an omitted row.",
                      offset=prefix.offset)
    if all(guard and any(array == guard[0] and value != guard[1] for array, value in neutral_conditions)
           for guard in effect_guards):
        return report("EXTENT_TAIL_CHECKED_NEUTRAL", "Consumer checks exclude every recognized settlement effect on skipped rows.",
                      offset=prefix.offset, verdict="VERIFIED_WITHIN_SCOPE", facts=facts)

    public_words = [value for value, summary in zip(public_values, committed) if summary is None]
    if not width or any(
        _atom(value) is None or _depends_on(value, origin, verifier_aliases)
        for value in [*public_words, *(_compact(arg) for arg in call.args[:-1])]
    ):
        return report("EXTENT_BOUND_BINDING_UNRESOLVED", "Could not establish a calldata bound independent of the verifier inputs.",
                      offset=prefix.offset)
    if neutral_conditions or interval[0] >= length:
        return report("EXTENT_SHORT_PREFIX_UNRESOLVED", "Could not establish a shorter prefix with an unchecked omitted effect.",
                      offset=prefix.offset)
    return report(
        "EXTENT_CALLDATA_PREFIX_SHORTER_THAN_COMMITMENT",
        "A calldata bound outside the verifier vector can settle a shorter prefix than the committed array.",
        offset=prefix.offset, verdict="VIOLATION", facts=facts,
    )


def assembly_findings(path: str, source: str) -> list[dict[str, Any]]:
    """Give explicit-source analysis a diagnostic when no verify call was recovered."""
    findings = []
    for function in functions(source):
        body = mask_comments_and_strings(function.body)
        assembly_call = ASSEMBLY_VERIFIER.search(body)
        if assembly_call is None or not ASSEMBLY.search(body, 0, assembly_call.start()):
            continue
        line = function.line + function.header.count("\n") + body.count("\n", 0, assembly_call.start())
        findings.append(_finding(
            path, line, function, "EXTENT_ASSEMBLY_VERIFIER_INPUT_UNSUPPORTED",
            "Inline-assembly staticcall prevents recovery of the verifier input and its committed region.",
        ))
    return findings
