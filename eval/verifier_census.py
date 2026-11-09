"""Conservative, passive source classifier for Solidity proof verifiers.

The output is a source-template observation, never proof of verifier soundness.
Unrecognized guards, dynamic arity, and ambiguous templates remain UNKNOWN.
"""

from __future__ import annotations

import re
from typing import Any


R = 21888242871839275222246405745257275088548364400416034343698204186575808495617
Q = 21888242871839275222246405745257275088696311157297823662689037894645226208583


def _blank_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group())
    return re.sub(r"//[^\n]*|/\*.*?\*/", blank, source, flags=re.S)


def _matched_end(source: str, opening: int, left: str, right: str) -> int | None:
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == left:
            depth += 1
        elif source[position] == right:
            depth -= 1
            if depth == 0:
                return position
    return None


def _line(source: str, position: int) -> int:
    return source.count("\n", 0, position) + 1


def _evidence(source: str, position: int, kind: str) -> dict[str, Any]:
    line = _line(source, position)
    return {"kind": kind, "line": line, "text": source.splitlines()[line - 1].strip()[:300]}


def _constants(clean: str) -> dict[str, int]:
    output: dict[str, int] = {}
    for match in re.finditer(r"\b(?:uint(?:256)?\s+)?(?:constant\s+)?(r|q)\s*=\s*(\d+)\s*;", clean):
        output[match.group(1)] = int(match.group(2))
    return output


def _modulus(token: str, constants: dict[str, int]) -> str | None:
    value = constants.get(token)
    if token.isdigit():
        value = int(token)
    if value == R:
        return "R"
    if value == Q:
        return "Q"
    return None


def _input_schema(signature: str) -> tuple[str | None, int | None]:
    matches = list(re.finditer(r"\buint(?:256)?\s*\[\s*(\d*)\s*\]\s*(?:calldata|memory|storage)?\s*(\w+)", signature))
    if not matches:
        return None, None
    preferred = [m for m in matches if re.search(r"pub|input|signal", m.group(2), re.I)]
    match = (preferred or matches)[-1]
    return match.group(2), int(match.group(1)) if match.group(1) else None


def _classify_range(clean: str, body: str, body_offset: int, name: str | None,
                    arity: int | None, source: str) -> tuple[str, list[int], list[dict[str, Any]]]:
    if name is None:
        return "UNKNOWN", [], []
    constants = _constants(clean)
    evidence: list[dict[str, Any]] = []
    positions: dict[int, str] = {}
    helper = re.search(r"function\s+checkField\s*\(\s*\w+\s*\)\s*\{", body)
    helper_modulus = None
    body_without_helper = body
    if helper:
        helper_end = _matched_end(body, helper.end() - 1, "{", "}")
        if helper_end is not None:
            body_without_helper = body[:helper.start()] + body[helper_end + 1:]
            helper_body = body[helper.end():helper_end]
            guard = re.search(r"iszero\s*\(\s*lt\s*\(\s*\w+\s*,\s*(r|q|\d+)\s*\)\s*\)", helper_body)
            if guard and re.search(r"\breturn\s*\(", helper_body):
                helper_modulus = _modulus(guard.group(1), constants)
                evidence.append(_evidence(source, body_offset + helper.start(), "guard-helper"))
    for match in re.finditer(rf"\bcheckField\s*\(\s*calldataload\s*\(\s*add\s*\(\s*{re.escape(name)}\s*,\s*(\d+)\s*\)\s*\)\s*\)", body):
        byte_offset = int(match.group(1))
        if helper_modulus and byte_offset % 32 == 0:
            positions[byte_offset // 32] = helper_modulus
            evidence.append(_evidence(source, body_offset + match.start(), "guard-call"))
    for match in re.finditer(rf"\brequire\s*\(\s*{re.escape(name)}\s*\[\s*(\d+)\s*\]\s*<\s*(r|q|\d+)\s*\)", body):
        modulus = _modulus(match.group(2), constants)
        if modulus:
            positions[int(match.group(1))] = modulus
            evidence.append(_evidence(source, body_offset + match.start(), "direct-range-guard"))
    guarded = sorted(positions)
    if positions:
        values = set(positions.values())
        if arity is None:
            return "UNKNOWN", guarded, evidence
        covered = set(range(arity)) <= set(positions)
        if values == {"R"}:
            return ("R_ALL" if covered else "R_PARTIAL"), guarded, evidence
        if values == {"Q"}:
            return ("Q_ALL" if covered else "Q_PARTIAL"), guarded, evidence
        return "MIXED_PARTIAL", guarded, evidence
    if re.search(r"\b(checkField|checkRange|checkScalar|checkInputs|check)\s*\(", body_without_helper) or re.search(rf"\b{re.escape(name)}\s*\[.*?\]\s*[<>]", body_without_helper):
        return "UNKNOWN", [], evidence
    return "NONE", [], evidence


def classify_verifier(source: str) -> list[dict[str, Any]]:
    clean = _blank_comments(source)
    output: list[dict[str, Any]] = []
    for contract in re.finditer(r"\bcontract\s+(\w+)(?:\s+is\s+[^\{]+)?\s*\{", clean):
        contract_end = _matched_end(clean, contract.end() - 1, "{", "}")
        if contract_end is None:
            continue
        contract_body = clean[contract.end():contract_end]
        for function in re.finditer(r"\bfunction\s+(verify\w*Proof|verify|Verify)\s*\(", contract_body):
            start = contract.end() + function.start()
            open_paren = contract.end() + function.end() - 1
            close_paren = _matched_end(clean, open_paren, "(", ")")
            if close_paren is None:
                continue
            open_body = clean.find("{", close_paren, contract_end)
            if open_body < 0:
                continue
            close_body = _matched_end(clean, open_body, "{", "}")
            if close_body is None or close_body > contract_end:
                continue
            signature = clean[open_paren + 1:close_paren]
            body = clean[open_body + 1:close_body]
            name, arity = _input_schema(signature)
            if re.search(r"generated\s+by\s+gnark|gnark[ /]", source, re.I):
                generator = "GNARK"
            elif re.search(r"generated\s+with\s+\[?snarkjs|generated\s+by\s+snarkjs", source, re.I):
                generator = "SNARKJS_CURRENT_STYLE" if "function checkField" in body else "SNARKJS_LEGACY_STYLE"
            else:
                generator = "OTHER"
            range_class, positions, range_evidence = _classify_range(clean, body, open_body + 1, name, arity, source)
            stripped = body.strip()
            if re.fullmatch(r"return\s+true\s*;", stripped):
                behavior = "ACCEPT_ALL"
            elif re.fullmatch(r"return\s+false\s*;", stripped):
                behavior = "REJECT_ALL"
            elif re.search(r"\b(?:vk\w*|IC\d+[xy]?)\s*=\s*(?:0x1234\b|0x1234567890[0-9a-fA-F]*)", clean[contract.start():contract_end], re.I):
                behavior = "DUMMY_CONSTANTS"
            elif "return" not in stripped and re.search(r"\brevert\s+\w+(?:\([^;]*\))?\s*;\s*$", stripped):
                behavior = "REJECT_ALL"
            elif re.search(r"\b(mock|stub|simplified|stand[ -]?in)\b", source[max(0, contract.start()-1200):min(len(source), contract_end+1)], re.I) and not re.search(r"\bpairingProd\d*\s*\(|\bstaticcall\s*\([^\n]*?,\s*8\s*,", body):
                behavior = "SIMPLIFIED"
            elif re.search(r"\bpairingProd\d*\s*\(|\bstaticcall\s*\([^\n]*?,\s*8\s*,", body):
                behavior = "PAIRING_VERIFIER"
            else:
                behavior = "UNKNOWN"
            output.append({
                "contract": contract.group(1), "function": function.group(1),
                "line": _line(source, start), "generator": generator,
                "range_class": range_class, "public_input_arity": arity,
                "guarded_positions": positions, "behavior": behavior,
                "evidence": [_evidence(source, start, "verify-function"), *range_evidence],
            })
    return output
