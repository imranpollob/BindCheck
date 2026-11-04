from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import Any, Iterator


IDENT = re.compile(r"\b[A-Za-z_]\w*\b")
TYPE_WORDS = {
    "address", "bool", "bytes", "bytes32", "calldata", "contract", "external",
    "false", "internal", "memory", "payable", "private", "public", "returns",
    "storage", "this", "true", "uint", "uint256", "view", "pure", "virtual",
}
VERIFY_NAME = re.compile(r"\b(verifyProof|verifyTx|verify|validateProof|verifyPlonk)\s*\(", re.I)
EFFECT_NAME = re.compile(
    r"(?<![A-Za-z0-9_])(safeTransferFrom|transferFrom|safeTransfer|handleTransfer|"
    r"_safeMint|safeMint|_mint|mint|transfer|burn)\s*\(", re.I
)


def mask_comments_and_strings(text: str) -> str:
    output = list(text)
    index = 0
    while index < len(text):
        if text.startswith("//", index):
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            for pos in range(index, end):
                output[pos] = " "
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = len(text) - 2 if end < 0 else end
            for pos in range(index, end + 2):
                if output[pos] != "\n":
                    output[pos] = " "
            index = end + 2
        elif text[index] in {'"', "'"}:
            quote = text[index]
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    if output[index] != "\n":
                        output[index] = " "
                    if index + 1 < len(text) and output[index + 1] != "\n":
                        output[index + 1] = " "
                    index += 2
                    continue
                if text[index] == quote:
                    index += 1
                    break
                if output[index] != "\n":
                    output[index] = " "
                index += 1
        else:
            index += 1
    return "".join(output)


def balanced(text: str, opening: int, left: str = "(", right: str = ")") -> tuple[str, int] | None:
    if opening < 0 or opening >= len(text) or text[opening] != left:
        return None
    depth = 0
    for index in range(opening, len(text)):
        char = text[index]
        if char == left:
            depth += 1
        elif char == right:
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    return None


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    start = 0
    for index, char in enumerate(text):
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if stack and stack[-1] == pairs[char]:
                stack.pop()
        elif char == "," and not stack:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [item for item in parts if item]


def normalize_expression(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    previous = None
    while value != previous:
        previous = value
        value = re.sub(r"^(?:address|payable|uint(?:\d+)?|bytes\d*)\((.*)\)$", r"\1", value)
    return value


def identifiers(value: str) -> set[str]:
    return {
        token for token in IDENT.findall(value)
        if token.lower() not in TYPE_WORDS and not re.fullmatch(r"u?int\d*", token, re.I)
    }


@dataclasses.dataclass
class Function:
    name: str
    line: int
    header: str
    body: str
    parameters: dict[str, str]
    start: int


@dataclasses.dataclass
class Call:
    name: str
    receiver: str | None
    args: list[str]
    line: int
    offset: int


@dataclasses.dataclass
class PublicVector:
    expression: str
    base: str | None
    items: list[str]
    declared_count: int | None
    dynamic: bool
    length_guard: int | None
    unresolved: list[str]

    @property
    def normalized_items(self) -> set[str]:
        return {normalize_expression(item) for item in self.items}

    @property
    def sources(self) -> set[str]:
        found: set[str] = set()
        for item in self.items:
            found |= identifiers(item)
        if self.base:
            found.add(self.base)
        return found


def parse_parameters(header: str) -> dict[str, str]:
    opening = header.find("(")
    parsed = balanced(header, opening)
    if parsed is None:
        return {}
    result: dict[str, str] = {}
    for raw in split_top_level(parsed[0]):
        tokens = IDENT.findall(raw)
        candidates = [token for token in tokens if token.lower() not in TYPE_WORDS]
        if not candidates:
            continue
        name = candidates[-1]
        type_text = raw[: raw.rfind(name)].strip()
        result[name] = type_text
    return result


def functions(text: str) -> Iterator[Function]:
    masked = mask_comments_and_strings(text)
    for match in re.finditer(r"\bfunction\s+([A-Za-z_]\w*)\s*\(", masked):
        params = balanced(masked, masked.find("(", match.start()))
        if params is None:
            continue
        body_open = masked.find("{", params[1])
        semicolon = masked.find(";", params[1], body_open if body_open >= 0 else len(masked))
        if body_open < 0 or semicolon >= 0:
            continue
        parsed_body = balanced(masked, body_open, "{", "}")
        if parsed_body is None:
            continue
        header = text[match.start():body_open]
        yield Function(
            name=match.group(1),
            line=text.count("\n", 0, match.start()) + 1,
            header=header,
            body=text[body_open + 1:parsed_body[1] - 1],
            parameters=parse_parameters(header),
            start=match.start(),
        )


def calls(body: str, pattern: re.Pattern[str]) -> list[Call]:
    masked = mask_comments_and_strings(body)
    output: list[Call] = []
    for match in pattern.finditer(masked):
        opening = masked.find("(", match.start())
        parsed = balanced(masked, opening)
        if parsed is None:
            continue
        prefix = masked[max(0, match.start() - 100):match.start()]
        receiver_match = re.search(r"([A-Za-z_]\w*)\s*\.\s*$", prefix)
        name_match = IDENT.findall(match.group(0))
        name = name_match[-1] if name_match else match.group(0).split("(")[0]
        output.append(Call(
            name=name,
            receiver=receiver_match.group(1) if receiver_match else None,
            args=split_top_level(body[opening + 1:parsed[1] - 1]),
            line=body.count("\n", 0, match.start()) + 1,
            offset=match.start(),
        ))
    return output


def verification_calls(body: str) -> list[Call]:
    return calls(body, VERIFY_NAME)


def effect_calls(body: str) -> list[Call]:
    return calls(body, EFFECT_NAME)


def assignments(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    masked = mask_comments_and_strings(body)
    pattern = re.compile(
        r"(?:\b(?:uint(?:256)?|bytes32|address|bool)\b(?:\s*\[[^;=]*\])?\s+)?"
        r"\b([A-Za-z_]\w*)\s*=\s*([^;]+);"
    )
    for match in pattern.finditer(masked):
        if "==" in match.group(0) or "!=" in match.group(0):
            continue
        result[match.group(1)] = body[match.start(2):match.end(2)].strip()
    return result


def public_vector(body: str, call: Call) -> PublicVector:
    expression = call.args[-1].strip() if call.args else ""
    base = expression if re.fullmatch(r"[A-Za-z_]\w*", expression) else None
    items: list[str] = []
    declared_count: int | None = None
    dynamic = False
    unresolved: list[str] = []
    if expression.startswith("[") and expression.endswith("]"):
        items = split_top_level(expression[1:-1])
        declared_count = len(items)
    elif base:
        decl = re.search(
            rf"\b(?:uint(?:256)?|bytes32)\s*\[\s*(\d*)\s*\]\s+"
            rf"(?:memory|calldata|storage)?\s*{re.escape(base)}\b",
            body,
        )
        if decl:
            dynamic = decl.group(1) == ""
            declared_count = int(decl.group(1)) if decl.group(1) else None
        initializer = re.search(rf"\b{re.escape(base)}\s*=\s*\[", body)
        if initializer:
            opening = body.find("[", initializer.end() - 1)
            parsed = balanced(body, opening, "[", "]")
            if parsed:
                items = split_top_level(parsed[0])
                declared_count = len(items)
        indexed = {
            int(index): value.strip()
            for index, value in re.findall(
                rf"\b{re.escape(base)}\s*\[\s*(\d+)\s*\]\s*(?<![=!<>])=(?!=)\s*([^;]+);", body
            )
        }
        if indexed:
            maximum = max(indexed)
            items = [indexed.get(index, f"<unresolved:{base}[{index}]>") for index in range(maximum + 1)]
            unresolved.extend(item for item in items if item.startswith("<unresolved:"))
            if declared_count is None and not dynamic:
                declared_count = maximum + 1
    else:
        cast_array = re.search(r"\[(\d+)\]", expression)
        if cast_array:
            declared_count = int(cast_array.group(1))
    guard_match = None
    if base:
        guard_match = re.search(
            rf"(?:require\s*\(\s*{re.escape(base)}\.length\s*==\s*(\d+)|"
            rf"if\s*\(\s*{re.escape(base)}\.length\s*!=\s*(\d+)\s*\)\s*revert)",
            body,
        )
    length_guard = int(next(group for group in guard_match.groups() if group)) if guard_match else None
    return PublicVector(expression, base, items, declared_count, dynamic, length_guard, unresolved)


def effect_roles(call: Call) -> list[tuple[str, str]]:
    name = call.name.lower()
    args = call.args
    if name in {"safemint", "_safemint"} and len(args) == 2:
        return [("recipient", args[0])]
    if name in {"transfer", "safetransfer", "handletransfer", "mint", "_mint", "safemint", "_safemint"} and len(args) >= 2:
        return [("recipient", args[0]), ("amount", args[1])]
    if name in {"transferfrom", "safetransferfrom"} and len(args) >= 3:
        return [("recipient", args[1]), ("amount", args[2])]
    if name == "burn" and args:
        return [("amount", args[-1])]
    return []


def verifier_declarations(text: str) -> list[dict[str, Any]]:
    masked = mask_comments_and_strings(text)
    output: list[dict[str, Any]] = []
    declaration_pattern = re.compile(
        r"\bfunction\s+(verifyProof|verifyTx|verify|validateProof|verifyPlonk)\s*\(",
        re.I,
    )
    for match in declaration_pattern.finditer(masked):
        opening = masked.find("(", match.start())
        parsed = balanced(masked, opening)
        if parsed is None:
            continue
        args = split_top_level(text[opening + 1:parsed[1] - 1])
        final = args[-1] if args else ""
        fixed = re.search(r"(?:uint(?:256)?|bytes32)\s*\[\s*(\d+)\s*\]", final)
        dynamic = bool(re.search(r"(?:uint(?:256)?|bytes32)\s*\[\s*\]", final))
        output.append({
            "name": match.group(1),
            "line": text.count("\n", 0, match.start()) + 1,
            "arity": int(fixed.group(1)) if fixed else None,
            "dynamic": dynamic,
            "signature": text[match.start():parsed[1]],
        })
    for constant in re.finditer(r"\bNUMBER_OF_PUBLIC_INPUTS\s*=\s*(\d+)", masked):
        output.append({"name": "constant", "line": text.count("\n", 0, constant.start()) + 1,
                       "arity": int(constant.group(1)), "dynamic": True, "signature": constant.group(0)})
    return output


def has_unsupported_construct(body: str) -> str | None:
    masked = mask_comments_and_strings(body)
    if re.search(r"\bassembly\s*\{", masked):
        return "UNSUPPORTED_CONSUMER_ASSEMBLY"
    if ".delegatecall" in masked:
        return "UNSUPPORTED_DELEGATECALL_CONTEXT"
    if re.search(r"\bselfdestruct\s*\(", masked):
        return "UNSUPPORTED_SELFDESTRUCT"
    return None
