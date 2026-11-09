from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from typing import Any

from .common import finding


PUBLIC_VECTOR_RE = re.compile(r"\b(?:publicInputs?|pubSignals?|signals?|input)\s*\[\s*(\d+)\s*\]")
VERIFY_CALL_RE = re.compile(r"\b(?:verifyProof|verify|validateProof)\s*\(")
SCALAR_FIELD = "21888242871839275222246405745257275088548364400416034343698204186575808495617"


@dataclass
class FunctionSlice:
    name: str
    signature: str
    body: str
    start: int
    body_start: int


def _balanced_end(text: str, opening: int) -> int | None:
    depth = 0
    string_quote: str | None = None
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if string_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_quote:
                string_quote = None
            continue
        if char in {'"', "'"}:
            string_quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def extract_functions(text: str) -> list[FunctionSlice]:
    functions: list[FunctionSlice] = []
    pattern = re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\((.*?)\)([^;{]*)\{", re.S)
    for match in pattern.finditer(text):
        opening = match.end() - 1
        closing = _balanced_end(text, opening)
        if closing is None:
            continue
        functions.append(FunctionSlice(
            name=match.group(1),
            signature=match.group(0)[:-1],
            body=text[opening + 1:closing],
            start=match.start(),
            body_start=opening + 1,
        ))
    return functions


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def solidity_files(root: pathlib.Path, cap: int = 2500) -> tuple[list[pathlib.Path], bool]:
    excluded = {".git", "node_modules", "vendor", "target", "build", "dist", "out", "artifacts", "cache", "test", "tests"}
    files: list[pathlib.Path] = []
    capped = False
    for path in sorted(root.rglob("*.sol")):
        if any(part in excluded for part in path.parts) or not path.is_file():
            continue
        if path.stat().st_size > 5_000_000:
            continue
        if len(files) >= cap:
            capped = True
            break
        files.append(path)
    return files, capped


def _normalize(expression: str) -> str:
    value = re.sub(r"\s+", "", expression)
    wrappers = ("address", "uint160", "uint256", "bytes32", "payable")
    changed = True
    while changed:
        changed = False
        for wrapper in wrappers:
            prefix = wrapper + "("
            if value.startswith(prefix) and value.endswith(")"):
                value = value[len(prefix):-1]
                changed = True
    return value


def public_aliases(body: str) -> dict[str, int]:
    aliases: dict[str, int] = {}
    assignment = re.compile(
        r"(?:\b(?:address|uint(?:8|16|32|64|128|160|256)?|bytes32|bool)\s+)?"
        r"([A-Za-z_]\w*)\s*(?<![=!<>])=(?!=)\s*([^;]+);"
    )
    changed = True
    while changed:
        changed = False
        for match in assignment.finditer(body):
            name, expression = match.group(1), match.group(2)
            public = PUBLIC_VECTOR_RE.search(expression)
            index: int | None = int(public.group(1)) if public else None
            if index is None:
                for alias, alias_index in aliases.items():
                    if re.search(rf"\b{re.escape(alias)}\b", expression):
                        index = alias_index
                        break
            if index is not None and aliases.get(name) != index:
                aliases[name] = index
                changed = True
    return aliases


def expression_public_index(expression: str, aliases: dict[str, int]) -> int | None:
    direct = PUBLIC_VECTOR_RE.search(expression)
    if direct:
        return int(direct.group(1))
    normalized = _normalize(expression)
    if normalized in aliases:
        return aliases[normalized]
    for alias, index in aliases.items():
        if re.fullmatch(rf"(?:{re.escape(alias)})", normalized):
            return index
    return None


def _guard_relation(body: str, expression: str, effect_offset: int, aliases: dict[str, int]) -> tuple[str | None, int | None]:
    """Return the strongest recognized equality relation and public index."""
    normalized = _normalize(expression)
    token = re.escape(normalized)
    equality = re.compile(
        rf"(?:{token}\s*==\s*([^;,)]+)|([^;,(]+)\s*==\s*{token})"
    )
    best: tuple[str | None, int | None] = (None, None)
    for match in equality.finditer(body):
        other = match.group(1) or match.group(2) or ""
        index = expression_public_index(other, aliases)
        if index is None:
            continue
        prefix = body[max(0, match.start() - 80):match.start()]
        if re.search(r"(?:require|assert)\s*\([^)]*$", prefix):
            if match.start() < effect_offset:
                return "dominating-revert", index
            best = ("after-effect", index)
        elif re.search(r"if\s*\([^)]*$", prefix):
            best = ("non-enforcing-branch", index)
    return best


def _split_args(text: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        args.append("".join(current).strip())
    return args


def _call_effects(body: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    patterns = [
        ("mint", re.compile(r"\b(?:_?mint|_?safeMint)\s*\(([^;]+?)\)")),
        ("burn", re.compile(r"\b(?:_?burn|burnFrom)\s*\(([^;]+?)\)")),
        ("transferFrom", re.compile(r"\.transferFrom\s*\(([^;]+?)\)")),
        ("transfer", re.compile(r"\.safeTransfer\s*\(([^;]+?)\)")),
        ("transfer", re.compile(r"\.transfer\s*\(([^;]+?)\)")),
    ]
    for kind, pattern in patterns:
        for match in pattern.finditer(body):
            args = _split_args(match.group(1))
            if kind == "transferFrom" and len(args) >= 3:
                roles = [("identity", args[0]), ("recipient", args[1]), ("amount", args[2])]
            elif len(args) >= 2:
                roles = [("recipient" if kind != "burn" else "identity", args[0]), ("amount", args[1])]
            elif len(args) == 1:
                roles = [("amount", args[0])]
            else:
                continue
            output.append({"kind": kind, "offset": match.start(), "roles": roles, "text": match.group(0)})
    for match in re.finditer(r"((?:payable\s*\([^)]*\)|[A-Za-z_]\w*))\.call\s*\{\s*value\s*:\s*([^}]+)\}", body):
        output.append({
            "kind": "native-call", "offset": match.start(),
            "roles": [("recipient", match.group(1)), ("call_value", match.group(2))],
            "text": match.group(0),
        })
    state_pattern = re.compile(
        r"\b(?:balances?|credits?|claims?|withdrawals?)\s*\[\s*([^\]]+)\s*\]\s*(?:\+?=)\s*([^;]+);",
        re.I,
    )
    for match in state_pattern.finditer(body):
        output.append({
            "kind": "state-write", "offset": match.start(),
            "roles": [("recipient", match.group(1)), ("state_value", match.group(2))],
            "text": match.group(0),
        })
    return sorted(output, key=lambda item: item["offset"])


def scan_effects(text: str, relative: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    findings: list[dict[str, Any]] = []
    stats = {"functions": 0, "verifier_consumers": 0, "effects": 0, "bound_effect_roles": 0, "unknown_effect_roles": 0}
    for function in extract_functions(text):
        stats["functions"] += 1
        if not VERIFY_CALL_RE.search(function.body):
            continue
        stats["verifier_consumers"] += 1
        aliases = public_aliases(function.body)
        effects = _call_effects(function.body)
        stats["effects"] += len(effects)
        for effect in effects:
            for role, expression in effect["roles"]:
                index = expression_public_index(expression, aliases)
                if index is not None:
                    stats["bound_effect_roles"] += 1
                    continue
                relation, guarded_index = _guard_relation(function.body, expression, effect["offset"], aliases)
                if relation == "dominating-revert":
                    stats["bound_effect_roles"] += 1
                    continue
                stats["unknown_effect_roles"] += 1
                line = line_at(text, function.body_start + effect["offset"])
                facts = {
                    "function": function.name,
                    "effect_kind": effect["kind"],
                    "role": role,
                    "expression": expression.strip(),
                    "guard_public_index": guarded_index,
                    "source_excerpt": effect["text"].strip(),
                }
                if relation == "after-effect":
                    code = "A_GUARD_AFTER_EFFECT"
                    message = "An equality guard occurs after the protected effect and does not dominate it."
                elif relation == "non-enforcing-branch":
                    code = "A_GUARD_NOT_DOMINATING"
                    message = "An equality appears only in a non-enforcing branch and does not dominate the protected effect."
                elif _normalize(expression) == "msg.sender" and role in {"recipient", "identity"}:
                    code = "A_CALLER_NOT_PROVED_IDENTITY"
                    message = "The caller receives or owns a protected effect without an equality to a proved identity."
                elif role == "recipient":
                    code = "A_EFFECT_RECIPIENT_UNBOUND"
                    message = "A protected-effect recipient is not a public input and lacks a dominating equality to one."
                elif role == "identity":
                    code = "A_EFFECT_IDENTITY_UNBOUND"
                    message = "A protected-effect identity is not a public input and lacks a dominating equality to one."
                elif role == "call_value":
                    code = "A_CALL_VALUE_UNBOUND"
                    message = "A native call value is not a public input and lacks a dominating equality to one."
                elif role == "state_value":
                    code = "A_STATE_WRITE_VALUE_UNBOUND"
                    message = "A protected state-write value is not a public input and lacks a dominating equality to one."
                elif re.search(r"alias|decoded|beneficiary", expression, re.I):
                    code = "A_EFFECT_ALIAS_UNBOUND"
                    message = "A consumer alias used by the protected effect is not tied to a public input."
                else:
                    code = "A_EFFECT_AMOUNT_UNBOUND"
                    message = "A protected-effect amount is not a public input and lacks a dominating equality to one."
                findings.append(finding(code, message, path=relative, line=line, facts=facts))
    return findings, stats


def _verifier_field_guards(texts: list[tuple[str, str]]) -> dict[int, list[dict[str, Any]]]:
    guards: dict[int, list[dict[str, Any]]] = {}
    pattern = re.compile(
        r"(?:require|if)\s*\(\s*(?:publicInputs?|input)\s*\[\s*(\d+)\s*\]\s*<\s*"
        r"(?:SNARK_SCALAR_FIELD|PRIME_Q|2188824287\d+)",
        re.I,
    )
    for relative, text in texts:
        for match in pattern.finditer(text):
            guards.setdefault(int(match.group(1)), []).append({
                "path": relative,
                "line": line_at(text, match.start()),
            })
    return guards


def scan_replay(texts: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    findings: list[dict[str, Any]] = []
    stats = {"replay_writes": 0, "bound_replay_keys": 0, "guarded_replay_positions": 0}
    guards = _verifier_field_guards(texts)
    replay_write = re.compile(r"\b([A-Za-z_]\w*)\s*((?:\[\s*[^\]]+\s*\])+?)\s*=\s*(?:true|1)", re.I)
    for relative, text in texts:
        for function in extract_functions(text):
            if not VERIFY_CALL_RE.search(function.body):
                continue
            aliases = public_aliases(function.body)
            for match in replay_write.finditer(function.body):
                if not re.search(r"nullifier|spent|used|consumed", match.group(1), re.I):
                    continue
                stats["replay_writes"] += 1
                keys = re.findall(r"\[\s*([^\]]+)\s*\]", match.group(2))
                if not keys:
                    continue
                key = keys[-1].strip()
                index = expression_public_index(key, aliases)
                line = line_at(text, function.body_start + match.start())
                if index is None:
                    findings.append(finding(
                        "A_REPLAY_KEY_UNBOUND",
                        "The consumed replay key is not derived from a verifier public input.",
                        path=relative, line=line,
                        facts={"function": function.name, "mapping": match.group(1), "mapping_keys": keys, "key": key, "source_excerpt": match.group(0).strip()},
                    ))
                    continue
                stats["bound_replay_keys"] += 1
                if index not in guards:
                    findings.append(finding(
                        "A_REPLAY_POSITION_FIELD_GUARD_MISSING",
                        "The exact public-input position used as the replay key lacks a scalar-field guard.",
                        path=relative, line=line,
                        facts={"function": function.name, "mapping_keys": keys, "key": key, "public_index": index, "guarded_positions": sorted(guards), "source_excerpt": match.group(0).strip()},
                    ))
                else:
                    stats["guarded_replay_positions"] += 1
    return findings, stats


def _ic_lengths(texts: list[tuple[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    patterns = [
        re.compile(r"\bIC_LENGTH\s*=\s*(\d+)"),
        re.compile(r"\bIC\s*=\s*new\s+[A-Za-z0-9_.]+\[\]\s*\(\s*(\d+)\s*\)"),
    ]
    for relative, text in texts:
        for pattern in patterns:
            for match in pattern.finditer(text):
                output.append({"path": relative, "line": line_at(text, match.start()), "length": int(match.group(1))})
        indices = [int(value) for value in re.findall(r"\bIC\s*\[\s*(\d+)\s*\]\s*=", text)]
        if indices:
            output.append({"path": relative, "line": 1, "length": max(indices) + 1})
    unique: dict[tuple[str, int], dict[str, Any]] = {}
    for item in output:
        unique[(item["path"], item["length"])] = item
    return list(unique.values())


def scan_interface(texts: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    ic = _ic_lengths(texts)
    vectors: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    for relative, text in texts:
        for match in re.finditer(r"new\s+uint(?:256)?\[\]\s*\(\s*(\d+)\s*\)", text):
            vectors.append({"path": relative, "line": line_at(text, match.start()), "length": int(match.group(1))})
        order_match = re.search(r"\bPUBLIC_ORDER\s*=\s*\"([^\"]+)\"", text)
        if order_match:
            orders.append({"path": relative, "order": [item.strip() for item in order_match.group(1).split(",")]})
    expected_counts = sorted({item["length"] - 1 for item in ic if item["length"] > 0})
    observed_counts = sorted({item["length"] for item in vectors})
    if expected_counts and observed_counts and not set(expected_counts).intersection(observed_counts):
        item = vectors[0]
        findings.append(finding(
            "A_VERIFIER_ARITY_MISMATCH",
            "The consumer public-vector length disagrees with the generated verifier IC length.",
            path=item["path"], line=item["line"],
            facts={"consumer_lengths": observed_counts, "verifier_public_counts": expected_counts},
        ))
    assignments: dict[int, str] = {}
    assignment_location: dict[int, tuple[str, int]] = {}
    for relative, text in texts:
        for match in re.finditer(r"(?:publicInputs?|input)\s*\[\s*(\d+)\s*\]\s*=\s*([A-Za-z_]\w*)", text):
            index = int(match.group(1))
            assignments[index] = match.group(2)
            assignment_location[index] = (relative, line_at(text, match.start()))
    for declared in orders:
        for index, name in enumerate(declared["order"]):
            if index in assignments and assignments[index].lower() != name.lower():
                relative, line = assignment_location[index]
                findings.append(finding(
                    "A_VERIFIER_ORDER_MISMATCH",
                    "The consumer assignment order disagrees with the generated verifier public order.",
                    path=relative, line=line,
                    facts={"index": index, "consumer_name": assignments[index], "verifier_name": name},
                ))
    return findings, {
        "ic_lengths": ic,
        "verifier_public_counts": expected_counts,
        "consumer_vector_lengths": observed_counts,
        "declared_orders": orders,
    }


def scan_repository(root: pathlib.Path) -> dict[str, Any]:
    files, capped = solidity_files(root)
    texts: list[tuple[str, str]] = []
    findings: list[dict[str, Any]] = []
    effect_stats = {"functions": 0, "verifier_consumers": 0, "effects": 0, "bound_effect_roles": 0, "unknown_effect_roles": 0}
    failures: list[dict[str, str]] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            failures.append({"path": relative, "error": str(exc)})
            continue
        texts.append((relative, text))
        local_findings, local_stats = scan_effects(text, relative)
        findings.extend(local_findings)
        for key, value in local_stats.items():
            effect_stats[key] += value
    replay_findings, replay_stats = scan_replay(texts)
    interface_findings, interface_stats = scan_interface(texts)
    findings.extend(replay_findings)
    findings.extend(interface_findings)
    return {
        "findings": findings,
        "coverage": {
            "solidity_files": len(files),
            "inventory_capped": capped,
            "read_failures": failures,
            "effect_analysis": effect_stats,
            "replay_analysis": replay_stats,
            "interface_analysis": interface_stats,
        },
    }
