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
    r"(?<![A-Za-z0-9_])(safeBatchTransferFrom|safeTransferFrom|transferFrom|safeTransfer|handleTransfer|"
    r"_safeMint|safeMint|_mint|mint|_safeTransfer|_transfer|transfer|send|_burn|burn)\s*\(", re.I
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


def _mapping_effect_writes(body: str, source_text: str) -> list[Call]:
    declared = set(re.findall(
        r"\bmapping\s*\([^;]+?\)\s*(?:(?:public|private|internal|external)\s+)*([A-Za-z_]\w*)\s*;",
        source_text,
        re.S,
    ))
    protected = {
        name for name in declared
        if any(token in name.lower() for token in ("balance", "claim", "mint"))
    }
    masked = mask_comments_and_strings(body)
    output: list[Call] = []
    for name in sorted(protected):
        for match in re.finditer(rf"\b{re.escape(name)}\s*\[", masked):
            opening = masked.find("[", match.start())
            parsed = balanced(masked, opening, "[", "]")
            if parsed is None:
                continue
            tail = masked[parsed[1]:]
            operator = re.match(r"\s*(\+=|-=|=)\s*", tail)
            if operator is None:
                continue
            rhs_start = parsed[1] + operator.end()
            rhs_end = masked.find(";", rhs_start)
            if rhs_end < 0:
                continue
            output.append(Call(
                name="__state_write__",
                receiver=name,
                args=[body[opening + 1:parsed[1] - 1].strip(), body[rhs_start:rhs_end].strip(), operator.group(1)],
                line=body.count("\n", 0, match.start()) + 1,
                offset=match.start(),
            ))
    return output


def _value_calls(body: str) -> list[Call]:
    masked = mask_comments_and_strings(body)
    pattern = re.compile(
        r"(?P<receiver>payable\s*\([^;{}]+?\)|address\s*\([^;{}]+?\)|[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
        r"\s*\.\s*[A-Za-z_]\w*\s*\{\s*value\s*:\s*(?P<value>[^,}]+)",
        re.S,
    )
    return [
        Call(
            name="__value_call__",
            receiver=match.group("receiver").strip(),
            args=[body[match.start("receiver"):match.end("receiver")].strip(), body[match.start("value"):match.end("value")].strip()],
            line=body.count("\n", 0, match.start()) + 1,
            offset=match.start(),
        )
        for match in pattern.finditer(masked)
    ]


def effect_calls(body: str, source_text: str = "") -> list[Call]:
    output = calls(body, EFFECT_NAME)
    output.extend(_value_calls(body))
    output.extend(_mapping_effect_writes(body, source_text))
    return sorted(output, key=lambda item: item.offset)


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
    custom_declaration = re.compile(
        r"\b[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)?(?:\s*\[[^;=]*\])?\s+"
        r"(?:calldata|memory|storage)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);"
    )
    for match in custom_declaration.finditer(masked):
        result[match.group(1)] = body[match.start(2):match.end(2)].strip()
    return result


def public_vector(body: str, call: Call) -> PublicVector:
    expression = call.args[-1].strip() if call.args else ""
    base = expression if re.fullmatch(r"[A-Za-z_]\w*", expression) else None
    items: list[str] = []
    declared_count: int | None = None
    dynamic = False
    unresolved: list[str] = []
    recovered_shape = False
    if expression.startswith("[") and expression.endswith("]"):
        items = split_top_level(expression[1:-1])
        declared_count = len(items)
        recovered_shape = True
    elif base:
        decl = re.search(
            rf"\b(?:uint(?:256)?|bytes32)\s*\[\s*(\d*)\s*\]\s+"
            rf"(?:memory|calldata|storage)?\s*{re.escape(base)}\b",
            body,
        )
        if decl:
            dynamic = decl.group(1) == ""
            declared_count = int(decl.group(1)) if decl.group(1) else None
            recovered_shape = True
        initializer = re.search(rf"\b{re.escape(base)}\s*=\s*\[", body)
        if initializer:
            opening = body.find("[", initializer.end() - 1)
            parsed = balanced(body, opening, "[", "]")
            if parsed:
                items = split_top_level(parsed[0])
                declared_count = len(items)
                recovered_shape = True
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
            recovered_shape = True
        allocation = re.search(
            rf"\b{re.escape(base)}\s*=\s*new\s+(?:uint(?:256)?|bytes32)\s*\[\s*\]\s*\(\s*(\d+)\s*\)",
            body,
        )
        if allocation:
            declared_count = int(allocation.group(1))
            recovered_shape = True
    else:
        cast_array = re.search(r"\[(\d+)\]", expression)
        if cast_array:
            declared_count = int(cast_array.group(1))
            recovered_shape = True
    guard_match = None
    if base:
        guard_match = re.search(
            rf"(?:require\s*\(\s*{re.escape(base)}\.length\s*==\s*(\d+)|"
            rf"if\s*\(\s*{re.escape(base)}\.length\s*!=\s*(\d+)\s*\)\s*revert)",
            body,
        )
    length_guard = int(next(group for group in guard_match.groups() if group)) if guard_match else None
    if base and length_guard is None:
        allocation = re.search(
            rf"\b{re.escape(base)}\s*=\s*new\s+(?:uint(?:256)?|bytes32)\s*\[\s*\]\s*\(\s*(\d+)\s*\)",
            body,
        )
        if allocation:
            length_guard = int(allocation.group(1))
    if not recovered_shape:
        unresolved.append("public-vector-shape")
    return PublicVector(expression, base, items, declared_count, dynamic, length_guard, unresolved)


def effect_roles(call: Call, source_text: str = "") -> list[tuple[str, str]]:
    name = call.name.lower()
    args = call.args
    erc721_base = bool(re.search(r"\bcontract\s+[A-Za-z_]\w*\s+is\s+[^\{;]*\bERC721\w*\b", source_text, re.I))
    erc20_base = bool(re.search(r"\bcontract\s+[A-Za-z_]\w*\s+is\s+[^\{;]*\bERC20\w*\b", source_text, re.I))
    if name in {"_transfer", "_safetransfer"} and len(args) >= 3:
        if erc721_base:
            return [("recipient", args[1])]
        if erc20_base:
            return [("recipient", args[1]), ("amount", args[2])]
        return []
    if name == "_burn" and args:
        if erc20_base and len(args) >= 2:
            return [("identity", args[0]), ("amount", args[1])]
        if erc721_base:
            return [("identity", args[0])]
        return []
    if name == "__value_call__" and len(args) == 2:
        return [("recipient", args[0]), ("amount", args[1])]
    if name == "__state_write__" and len(args) == 3:
        key, value, operator = args
        roles = [("identity", key)]
        if operator in {"+=", "-="} or normalize_expression(value).lower() not in {"true", "false"}:
            roles.append(("amount", value))
        return roles
    if name in {"transfer", "send"} and len(args) == 1 and call.receiver:
        return [("recipient", call.receiver), ("amount", args[0])]
    if name in {"safemint", "_safemint"} and len(args) == 2:
        return [("recipient", args[0])]
    if name in {"mint", "_mint"} and len(args) == 2 and re.search(
        r"\bcontract\s+[A-Za-z_]\w*\s+is\s+[^\{;]*\bERC721[A-Za-z_0-9]*\b", source_text, re.I
    ):
        return [("recipient", args[0])]
    if name in {"mint", "_mint"} and len(args) >= 3:
        return [("recipient", args[0]), ("amount", args[2])]
    if name in {"transfer", "safetransfer", "handletransfer", "mint", "_mint", "safemint", "_safemint"} and len(args) >= 2:
        return [("recipient", args[0]), ("amount", args[1])]
    if name == "safebatchtransferfrom" and len(args) >= 4:
        return [("recipient", args[1]), ("amount", args[3])]
    if name == "safetransferfrom" and len(args) >= 5:
        return [("recipient", args[1]), ("amount", args[3])]
    erc721_source = bool(re.search(
        r"\b(?:is\s+[^\{;]*\bERC721\w*|(?:I?ERC721\w*)\s+" + re.escape(call.receiver or "") + r"\b)",
        source_text,
        re.I,
    ))
    if name in {"transferfrom", "safetransferfrom"} and len(args) >= 3 and erc721_source:
        return [("recipient", args[1])]
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
            "public_input_like": bool(fixed or dynamic),
            "opaque": not bool(fixed or dynamic),
            "signature": text[match.start():parsed[1]],
        })
    for constant in re.finditer(r"\bNUMBER_OF_PUBLIC_INPUTS\s*=\s*(\d+)", masked):
        output.append({"name": "constant", "line": text.count("\n", 0, constant.start()) + 1,
                       "arity": int(constant.group(1)), "dynamic": True, "public_input_like": True,
                       "opaque": False, "signature": constant.group(0)})
    ic_counts = {
        int(value) for value in re.findall(
            r"\b(?:vk\s*\.\s*)?IC\s*=\s*new\s+[^;()]+\(\s*(\d+)\s*\)",
            masked,
            re.I,
        )
    }
    ic_indices = {int(value) for value in re.findall(r"\bvk\s*\.\s*IC\s*\[\s*(\d+)\s*\]\s*=", masked, re.I)}
    if ic_indices and ic_indices == set(range(max(ic_indices) + 1)):
        ic_counts.add(max(ic_indices) + 1)
    for count in sorted(ic_counts):
        if count > 0:
            output.append({
                "name": "generated_verifier_ic_count",
                "line": 1,
                "arity": count - 1,
                "dynamic": True,
                "public_input_like": True,
                "opaque": False,
                "signature": f"IC[{count}]",
            })
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


def _exact_oz_import(source: str, symbol: str, path: str) -> bool:
    """Recognize bare or exact named imports, excluding aliases and lookalikes."""
    prefix = rf'import\s+(?:\{{\s*{re.escape(symbol)}\s*\}}\s+from\s+)?["\']'
    return bool(re.search(prefix + rf'@openzeppelin/contracts/{re.escape(path)}["\']\s*;', source))


def unresolved_function_context(
    function: Function, source_text: str,
    repository_contracts: dict[str, tuple[str, pathlib.Path]] | None = None,
    source_path: pathlib.Path | None = None,
) -> str | None:
    """Fail closed on consumer context that this frontend does not resolve."""
    masked_source = mask_comments_and_strings(source_text)
    enclosing_source = ""
    for declaration in re.finditer(r"\b(?:abstract\s+)?contract\s+[A-Za-z_]\w*[^\{]*\{", masked_source):
        opening = masked_source.find("{", declaration.start())
        parsed = balanced(masked_source, opening, "{", "}")
        if parsed is not None and opening < function.start < parsed[1]:
            enclosing_source = source_text[declaration.start():parsed[1]]
            break
    if not enclosing_source:
        return "UNRESOLVED_CONSUMER_INHERITANCE"
    masked_header = mask_comments_and_strings(function.header)
    opening = masked_header.find("(")
    parameters = balanced(masked_header, opening)
    suffix = masked_header[parameters[1]:] if parameters is not None else ""
    suffix = re.sub(r"\breturns\s*\([^)]*\)", " ", suffix, flags=re.I | re.S)
    suffix = re.sub(r"\boverride\s*(?:\([^)]*\))?", " ", suffix, flags=re.I | re.S)
    standard = {
        "public", "external", "internal", "private", "view", "pure",
        "payable", "virtual",
    }
    modifiers = [token for token in IDENT.findall(suffix) if token.lower() not in standard]
    for modifier in modifiers:
        modifier_scope = enclosing_source
        declarations = list(re.finditer(rf"\bmodifier\s+{re.escape(modifier)}\s*(?:\([^)]*\))?\s*\{{", modifier_scope))
        if not declarations:
            # Preserve the source-only control fixture's top-level modifier
            # declaration. Valid Solidity places modifiers in the contract.
            first_contract = re.search(r"\b(?:abstract\s+)?contract\s+", masked_source)
            preamble = source_text[:first_contract.start()] if first_contract else ""
            preamble_declarations = list(re.finditer(
                rf"\bmodifier\s+{re.escape(modifier)}\s*(?:\([^)]*\))?\s*\{{", preamble
            ))
            if len(preamble_declarations) == 1:
                modifier_scope = preamble
                declarations = preamble_declarations
        if not declarations:
            known_oz = bool(
                (modifier == "nonReentrant" and any(_exact_oz_import(source_text, "ReentrancyGuard", f"{directory}/ReentrancyGuard.sol")
                 for directory in ("utils", "security")) and re.search(r"\bis\s+[^\{;]*\bReentrancyGuard\b", enclosing_source))
                or (modifier in {"whenNotPaused", "whenPaused"} and any(_exact_oz_import(source_text, "Pausable", f"{directory}/Pausable.sol")
                 for directory in ("utils", "security")) and re.search(r"\bis\s+[^\{;]*\bPausable\b", enclosing_source))
            )
            if not known_oz:
                return "UNRESOLVED_CONSUMER_MODIFIER"
            continue
        if len(declarations) != 1:
            return "UNRESOLVED_CONSUMER_MODIFIER"
        opening = modifier_scope.find("{", declarations[0].start())
        parsed_modifier = balanced(modifier_scope, opening, "{", "}")
        if parsed_modifier is None:
            return "UNRESOLVED_CONSUMER_MODIFIER"
        modifier_body = mask_comments_and_strings(parsed_modifier[0])
        if len(re.findall(r"\b_\s*;", modifier_body)) != 1:
            return "UNRESOLVED_CONSUMER_MODIFIER"
        before, after = re.split(r"\b_\s*;", modifier_body, maxsplit=1)
        if after.strip():
            if not _local_status_lock_modifier(before, after, enclosing_source):
                return "UNRESOLVED_CONSUMER_MODIFIER"
        else:
            if re.search(r"\b(?:if|for|while|try|assembly|return|break|continue)\b|\b[A-Za-z_]\w*\s*\.\s*[A-Za-z_]\w*\s*\(", before):
                return "UNRESOLVED_CONSUMER_MODIFIER"
            statements = [item.strip() for item in before.split(";") if item.strip()]
            if any(not re.fullmatch(r"(?:require|assert)\s*\([^;]*\)", item, re.S) for item in statements):
                return "UNRESOLVED_CONSUMER_MODIFIER"

    for match in re.finditer(r"\b(?:abstract\s+)?contract\s+[A-Za-z_]\w*([^\{]*)\{", masked_source):
        opening = masked_source.find("{", match.start())
        parsed = balanced(masked_source, opening, "{", "}")
        if parsed is None or not (opening < function.start < parsed[1]):
            continue
        inherited = re.search(r"\bis\s+([^{}]+)", match.group(1))
        if inherited:
            bases = [re.match(r"\s*([A-Za-z_]\w*)", part) for part in inherited.group(1).split(",")]
            invoked = {call.name for call in effect_calls(function.body, source_text)}
            invoked |= {call.name for call in verification_calls(function.body)}
            for base_match in bases:
                if base_match is None:
                    return "UNRESOLVED_CONSUMER_INHERITANCE"
                base = base_match.group(1)
                oz_path = {
                    "ERC721": "token/ERC721/ERC721.sol",
                    "ERC721Enumerable": "token/ERC721/extensions/ERC721Enumerable.sol",
                    "ERC20": "token/ERC20/ERC20.sol",
                    "Ownable": "access/Ownable.sol",
                    "ReentrancyGuard": "utils/ReentrancyGuard.sol",
                    "Pausable": "utils/Pausable.sol",
                }.get(base)
                supported_oz = bool(oz_path and _exact_oz_import(source_text, base, oz_path))
                if base in {"ReentrancyGuard", "Pausable"}:
                    supported_oz = supported_oz or _exact_oz_import(source_text, base, f"security/{base}.sol")
                if supported_oz:
                    continue
                base_record = (repository_contracts or {}).get(base)
                if base_record is None:
                    return "UNRESOLVED_CONSUMER_INHERITANCE"
                else:
                    base_source, base_path = base_record
                    if source_path is None:
                        return "UNRESOLVED_CONSUMER_INHERITANCE"
                    imported_paths = re.findall(r'\bimport\s+(?:[^;]*?\bfrom\s+)?["\']([^"\']+)["\']\s*;', source_text)
                    imported = any(
                        item.startswith(".") and (source_path.parent / item).resolve() == base_path.resolve()
                        for item in imported_paths
                    )
                    if base_path.resolve() != source_path.resolve() and not imported:
                        return "UNRESOLVED_CONSUMER_INHERITANCE"
                    base_functions = {item.name for item in functions(base_source)}
                    if base_functions & invoked:
                        return "UNRESOLVED_CONSUMER_INHERITANCE"
            # An override in the derived source can replace a standard
            # internal token effect; do not apply the library summary then.
            local_functions = {item.name for item in functions(source_text) if item.start != function.start}
            if local_functions & {"_mint", "_safeMint", "_transfer", "_safeTransfer", "_update"} & invoked:
                return "UNRESOLVED_CONSUMER_INHERITANCE"
        break
    return None


def _local_status_lock_modifier(before: str, after: str, contract_source: str) -> bool:
    """Accept only the exact guard/set/body/reset local lock shape."""
    prefix = re.fullmatch(
        r"\s*require\s*\(\s*([A-Za-z_]\w*)\s*!=\s*([A-Za-z_]\w*)\s*(?:,\s*[^()]*)?\)\s*;"
        r"\s*\1\s*=\s*\2\s*;\s*", before, re.S,
    )
    if prefix is None:
        return False
    status, entered = prefix.group(1), prefix.group(2)
    reset = re.fullmatch(rf"\s*{re.escape(status)}\s*=\s*([A-Za-z_]\w*)\s*;\s*", after)
    if reset is None or reset.group(1) == entered:
        return False
    released = reset.group(1)
    declared_status = re.findall(
        rf"\buint256\s+(?:(?:private|internal|public)\s+)?{re.escape(status)}\s*;", contract_source
    )
    constant_pattern = r"\buint256\s+(?:(?:private|internal|public)\s+)?constant\s+{}\s*=\s*(\d+)\s*;"
    entered_values = re.findall(constant_pattern.format(re.escape(entered)), contract_source)
    released_values = re.findall(constant_pattern.format(re.escape(released)), contract_source)
    return (len(declared_status) == len(entered_values) == len(released_values) == 1
            and entered_values[0] != released_values[0])
