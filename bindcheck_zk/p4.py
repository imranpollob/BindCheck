from __future__ import annotations

import json
import pathlib
import re
from collections import defaultdict
from typing import Any

from .models import location, result


SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617
BN254_G2 = (
    11559732032986387107991004021392285783925812861821192530917403151452391805634,
    10857046999023057135944570762232829481370756359578518086990519993285655852781,
    4082367875863431332203403145435568316851327593401208105741076214120093531,
    8495653923123431417604973247489272438418190587263600148770280649306958101930,
)
LARGE_NUMBER = re.compile(r"0x[0-9a-fA-F]{20,}|\b\d{20,}\b")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def named_constants(text: str) -> dict[str, int]:
    output: dict[str, int] = {}
    for pattern in (
        r"\b(?:uint256|bytes32)\s+(?:internal\s+|public\s+|private\s+)?constant\s+([A-Za-z_]\w*)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;",
        r"\b([A-Za-z_]\w*)\s*:\s*(?:uint256|bytes32)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;",
    ):
        for name, value in re.findall(pattern, text):
            output[re.sub(r"[^a-z0-9]", "", name.lower())] = parse_int(value)
    return output


def _constant_g2(constants: dict[str, int], prefix: str) -> tuple[int, int, int, int] | None:
    for names in (
        (f"{prefix}x1", f"{prefix}x2", f"{prefix}y1", f"{prefix}y2"),
        (f"vk{prefix}x1", f"vk{prefix}x2", f"vk{prefix}y1", f"vk{prefix}y2"),
        (f"{prefix}2x0", f"{prefix}2x1", f"{prefix}2y0", f"{prefix}2y1"),
    ):
        if all(name in constants for name in names):
            return tuple(constants[name] for name in names)  # type: ignore[return-value]
    return None


def _assignment_g2(text: str, prefix: str) -> tuple[int, int, int, int] | None:
    default_call = re.search(
        rf"\b(?:vk\.)?{prefix}(?:2|_g2|G2)?\s*=\s*(?:Pairing\.)?P2\s*\(\s*\)\s*;",
        text,
        re.I,
    )
    if default_call:
        return BN254_G2
    for pattern in (
        rf"\b(?:vk\.)?{prefix}(?:2|_g2|G2)?\s*=\s*(?:Pairing\.)?G2Point\s*\((.*?)\)\s*;",
        rf"\b(?:vk\.)?{prefix}(?:2|_g2|G2)?\s*=\s*\[(.*?)\]\s*;",
    ):
        match = re.search(pattern, text, re.S | re.I)
        if match:
            values = [parse_int(value) for value in LARGE_NUMBER.findall(match.group(1))]
            if len(values) >= 4:
                return tuple(values[:4])  # type: ignore[return-value]
    return None


def extract_g2(text: str, constants: dict[str, int], prefix: str) -> tuple[int, int, int, int] | None:
    return _constant_g2(constants, prefix) or _assignment_g2(text, prefix)


def extract_ic(text: str, constants: dict[str, int]) -> dict[int, tuple[int, int]]:
    output: dict[int, tuple[int, int]] = {}
    for key, x in constants.items():
        match = re.fullmatch(r"(?:vk)?ic(\d+)x", key)
        if match:
            y = constants.get(re.sub(r"x$", "y", key))
            if y is not None:
                output[int(match.group(1))] = (x, y)
    for index, body in re.findall(
        r"\b(?:vk\.)?IC\s*\[\s*(\d+)\s*\]\s*=\s*(?:Pairing\.)?G1Point\s*\((.*?)\)\s*;",
        text,
        re.S | re.I,
    ):
        values = [parse_int(value) for value in LARGE_NUMBER.findall(body)]
        if len(values) >= 2:
            output[int(index)] = (values[0], values[1])
    return output


def canonical_guard(text: str) -> bool:
    modulus = rf"(?:{SCALAR_FIELD}|[A-Za-z_]\w*(?:SNARK|SCALAR|FIELD)[A-Za-z_]*)"
    return any(re.search(pattern, text, re.I) for pattern in (
        rf"(?:input|pubSignals?|publicInputs?)\s*\[[^\]]+\]\s*<\s*{modulus}",
        rf"{modulus}\s*<=\s*(?:input|pubSignals?|publicInputs?)\s*\[",
        rf"\bcheckField\s*\([^;]*(?:input|pubSignals?|publicInputs?)",
        rf"\b(?:require|assert)\s*\([^;]*(?:input|pubSignals?|publicInputs?)[^;]*<\s*{modulus}",
    ))


def has_pairing_p2(text: str) -> bool:
    match = re.search(r"\bfunction\s+P2\s*\([^)]*\)[^{]*\{(.*?)\n?\s*\}", text, re.S | re.I)
    if not match:
        return False
    values = {parse_int(value) for value in LARGE_NUMBER.findall(match.group(1))}
    return all(value in values for value in BN254_G2)


def analyze_source(text: str, relative_path: str) -> dict[str, Any]:
    cleaned = strip_comments(text)
    constants = named_constants(cleaned)
    gamma = extract_g2(cleaned, constants, "gamma")
    delta = extract_g2(cleaned, constants, "delta")
    points = extract_ic(cleaned, constants)
    reverse: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, point in points.items():
        reverse[point].append(index)
    duplicates = sorted(indices for indices in reverse.values() if len(indices) > 1)
    guard = canonical_guard(cleaned)
    p2 = has_pairing_p2(cleaned)
    verify = bool(re.search(r"\b(?:verifyProof|verifyTx|verify)\s*\(", cleaned, re.I))
    parsed = gamma is not None and delta is not None
    facts = [
        {"provenance": "EXTRACTED", "name": "gamma_g2", "value": list(gamma) if gamma else None},
        {"provenance": "EXTRACTED", "name": "delta_g2", "value": list(delta) if delta else None},
        {"provenance": "EXTRACTED", "name": "pairing_library_p2", "value": p2},
        {"provenance": "EXTRACTED", "name": "duplicate_ic_indices", "value": duplicates},
        {"provenance": "EXTRACTED", "name": "canonical_guard", "value": guard},
    ]
    where = location(relative_path, 1)
    if gamma == BN254_G2 and delta == BN254_G2:
        finding = result(
            "P4", "UNKNOWN", "DEFAULT_G2_GAMMA_DELTA_SOURCE_WARNING",
            "Gamma and delta both resolve to the default BN254 G2 generator; source correspondence is E1 only.",
            where=where, facts=facts,
            limitations=["No proof-generation, key-ceremony, deployment, or exploit claim follows from source constants."],
        )
    elif duplicates:
        finding = result(
            "P4", "UNKNOWN", "DUPLICATE_IC_SOURCE_WARNING",
            "Two or more parsed IC entries are identical.", where=where, facts=facts,
        )
    elif p2 and not parsed:
        finding = result(
            "P4", "VERIFIED_WITHIN_SCOPE", "PAIRING_LIBRARY_GENERATOR_EXCLUDED",
            "Default G2 constants occur only in the recognized Pairing.P2 generator helper; no gamma/delta key assignment was parsed.",
            where=where, facts=facts,
        )
    elif verify and not guard:
        finding = result(
            "P4", "UNKNOWN", "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND",
            "No supported canonical public-input field guard was recovered.", where=where, facts=facts,
        )
    elif parsed and (not verify or guard):
        finding = result(
            "P4", "VERIFIED_WITHIN_SCOPE", "VERIFICATION_KEY_CHECKS_PASS",
            "Parsed gamma/delta are distinct from the default-equal-key pattern and no duplicate IC point was found.",
            where=where, facts=facts,
            limitations=["This verifies only parsed source-key invariants, not key/circuit or deployment correspondence."],
        )
    else:
        finding = result(
            "P4", "UNKNOWN", "VERIFICATION_KEY_PARSE_INCOMPLETE",
            "A complete supported gamma/delta verification-key representation was not recovered.", where=where, facts=facts,
        )
    return {"finding": finding, "gamma": gamma, "delta": delta, "p2": p2, "guard": guard, "duplicates": duplicates}


def _push32_positions(raw: bytes) -> tuple[dict[int, list[int]], bool]:
    output: dict[int, list[int]] = defaultdict(list)
    offset = 0
    complete = True
    while offset < len(raw):
        opcode = raw[offset]
        if 0x60 <= opcode <= 0x7f:
            width = opcode - 0x5f
            if offset + 1 + width > len(raw):
                complete = False
                break
            if width == 32:
                output[int.from_bytes(raw[offset + 1:offset + 33], "big")].append(offset)
            offset += 1 + width
        else:
            offset += 1
    return output, complete


def _g2_groups(positions: dict[int, list[int]], window: int = 384) -> list[list[int]]:
    events = sorted((position, coordinate) for coordinate in BN254_G2 for position in positions.get(coordinate, []))
    groups: list[list[int]] = []
    used: set[int] = set()
    for start_index, (start, _) in enumerate(events):
        if start_index in used:
            continue
        selected: list[int] = []
        coordinates: set[int] = set()
        for index in range(start_index, len(events)):
            position, coordinate = events[index]
            if position - start > window:
                break
            if coordinate not in coordinates:
                selected.append(index)
                coordinates.add(coordinate)
        if len(coordinates) == 4:
            groups.append([events[index][0] for index in selected])
            used.update(selected)
    return groups


def analyze_runtime(hex_value: str, relative_path: str, *, source_has_p2: bool = False) -> dict[str, Any]:
    value = hex_value.strip()
    if value.startswith("0x"):
        value = value[2:]
    where = location(relative_path, 1)
    if not value or len(value) % 2 or re.search(r"[^0-9a-fA-F]", value):
        return {"finding": result(
            "P4", "UNKNOWN", "RUNTIME_BYTECODE_PARSE_INCOMPLETE",
            "Runtime bytecode is empty, odd-length, or non-hexadecimal.", where=where,
        ), "groups": []}
    raw = bytes.fromhex(value)
    positions, complete = _push32_positions(raw)
    if not complete:
        return {"finding": result(
            "P4", "UNKNOWN", "RUNTIME_BYTECODE_PARSE_INCOMPLETE",
            "Runtime bytecode ends inside a PUSH immediate.", where=where,
        ), "groups": []}
    groups = _g2_groups(positions)
    facts = [
        {"provenance": "EXTRACTED", "name": "runtime_bytes", "value": len(raw)},
        {"provenance": "EXTRACTED", "name": "default_g2_push_groups", "value": groups},
        {"provenance": "EXTRACTED", "name": "source_pairing_p2", "value": source_has_p2},
    ]
    key_groups = len(groups) - (1 if source_has_p2 and groups else 0)
    if key_groups >= 2:
        finding = result(
            "P4", "UNKNOWN", "DEFAULT_G2_RUNTIME_SIGNATURE",
            "After excluding one recognized Pairing.P2 generator group, at least two default-G2 groups remain in runtime bytecode.",
            where=where, facts=facts,
            limitations=["Runtime signature is E1 triage; source/key correspondence remains required."],
        )
    elif source_has_p2 and len(groups) == 1:
        finding = result(
            "P4", "VERIFIED_WITHIN_SCOPE", "PAIRING_LIBRARY_GENERATOR_EXCLUDED",
            "The only complete default-G2 runtime group corresponds to the source Pairing.P2 generator helper.",
            where=where, facts=facts,
        )
    elif not groups:
        finding = result(
            "P4", "VERIFIED_WITHIN_SCOPE", "RUNTIME_DEFAULT_G2_SIGNATURE_ABSENT",
            "No complete default-G2 PUSH32 group was recovered from runtime bytecode.",
            where=where, facts=facts,
            limitations=["Absence of this signature does not establish verifier correctness."],
        )
    else:
        finding = result(
            "P4", "UNKNOWN", "RUNTIME_DEFAULT_G2_ROLE_AMBIGUOUS",
            "Default-G2 runtime constants were recovered, but their library/key role is ambiguous.", where=where, facts=facts,
        )
    return {"finding": finding, "groups": groups, "complete": complete}


def runtime_values_from_bundle(root: pathlib.Path, files: list[pathlib.Path]) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in files:
        relative = path.relative_to(root).as_posix()
        lower = path.name.lower()
        if lower.endswith((".bin-runtime", ".runtime", ".runtime.hex")):
            value = path.read_text(encoding="utf-8", errors="replace").strip()
            if value and value not in seen:
                seen.add(value)
                output.append((relative, value))
        elif path.suffix.lower() == ".json" and path.stat().st_size <= 10_000_000:
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (json.JSONDecodeError, OSError):
                continue
            stack: list[tuple[str, Any]] = [("", payload)]
            while stack:
                key, value = stack.pop()
                if isinstance(value, dict):
                    for child_key, child in value.items():
                        stack.append((str(child_key), child))
                elif isinstance(value, list):
                    stack.extend((key, child) for child in value)
                elif isinstance(value, str) and key.lower() in {
                    "deployedbytecode", "runtimebytecode", "deployed_bytecode", "runtime_bytecode"
                }:
                    candidate = value.removeprefix("0x")
                    if len(candidate) >= 20 and not re.search(r"[^0-9a-fA-F]", candidate) and candidate not in seen:
                        seen.add(candidate)
                        output.append((relative + "#" + key, value))
    return output
