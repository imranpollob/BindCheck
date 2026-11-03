#!/usr/bin/env python3
"""Source-level census of Groth16 verification-key hazards (P4).

The scanner is deliberately read-only and deployment-agnostic. A warning is
E1/UNKNOWN until artifact correspondence and deployment status are established.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
from collections import Counter


SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617
BN254_G2 = (
    11559732032986387107991004021392285783925812861821192530917403151452391805634,
    10857046999023057135944570762232829481370756359578518086990519993285655852781,
    4082367875863433681332203403145435568316851327593401208105741076214120093531,
    8495653923123431417604973247489272438418190587263600148770280649306958101930,
)
EXCLUDED = {".git", "node_modules", "out", "cache", "artifacts", "build", "vendor"}
LARGE_NUMBER = re.compile(r"0x[0-9a-fA-F]{20,}|\b\d{20,}\b")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def named_constants(text: str) -> dict[str, int]:
    constants: dict[str, int] = {}
    patterns = (
        r"\b(?:uint256|bytes32)\s+constant\s+([A-Za-z_]\w*)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;",
        r"\b([A-Za-z_]\w*)\s*:\s*(?:uint256|bytes32)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;",
    )
    for pattern in patterns:
        for name, value in re.findall(pattern, text):
            constants[re.sub(r"[^a-z0-9]", "", name.lower())] = parse_int(value)
    return constants


def constant_g2(constants: dict[str, int], prefix: str) -> tuple[int, int, int, int] | None:
    candidates = (
        (f"{prefix}x1", f"{prefix}x2", f"{prefix}y1", f"{prefix}y2"),
        (f"vk{prefix}x1", f"vk{prefix}x2", f"vk{prefix}y1", f"vk{prefix}y2"),
        (f"{prefix}2x0", f"{prefix}2x1", f"{prefix}2y0", f"{prefix}2y1"),
    )
    for names in candidates:
        if all(name in constants for name in names):
            return tuple(constants[name] for name in names)  # type: ignore[return-value]
    return None


def assignment_g2(text: str, prefix: str) -> tuple[int, int, int, int] | None:
    patterns = (
        rf"\b(?:vk\.)?{prefix}(?:2|_g2|G2)?\s*=\s*(?:Pairing\.)?G2Point\s*\((.*?)\)\s*;",
        rf"\b(?:vk\.)?{prefix}(?:2|_g2|G2)?\s*=\s*\[(.*?)\]\s*;",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.S | re.I)
        if not match:
            continue
        values = [parse_int(value) for value in LARGE_NUMBER.findall(match.group(1))]
        if len(values) >= 4:
            return tuple(values[:4])  # type: ignore[return-value]
    return None


def extract_g2(text: str, constants: dict[str, int], prefix: str) -> tuple[int, int, int, int] | None:
    return constant_g2(constants, prefix) or assignment_g2(text, prefix)


def extract_ic_points(text: str, constants: dict[str, int]) -> dict[int, tuple[int, int]]:
    points: dict[int, tuple[int, int]] = {}
    for key, x in constants.items():
        match = re.fullmatch(r"(?:vk)?ic(\d+)x", key)
        if not match:
            continue
        index = int(match.group(1))
        y = constants.get(re.sub(r"x$", "y", key))
        if y is not None:
            points[index] = (x, y)
    for index, body in re.findall(
        r"\b(?:vk\.)?IC\s*\[\s*(\d+)\s*\]\s*=\s*(?:Pairing\.)?G1Point\s*\((.*?)\)\s*;",
        text,
        flags=re.S | re.I,
    ):
        values = [parse_int(value) for value in LARGE_NUMBER.findall(body)]
        if len(values) >= 2:
            points[int(index)] = (values[0], values[1])
    return points


def canonical_guard(text: str, constants: dict[str, int]) -> bool:
    scalar_names = [
        name for name, value in re.findall(
            rf"\b(?:uint256|bytes32)\s+constant\s+([A-Za-z_]\w*)\s*=\s*({SCALAR_FIELD})\s*;",
            text,
        )
    ]
    if str(SCALAR_FIELD) not in text and not scalar_names:
        return False
    aliases = [re.escape(name) for name in scalar_names]
    aliases.append(re.escape(str(SCALAR_FIELD)))
    modulus = "(?:" + "|".join(aliases) + ")"
    compare_patterns = (
        rf"\b(?:input|pubSignal|publicInputs?)\s*\[[^\]]+\]\s*<\s*{modulus}\b",
        rf"\b{modulus}\s*<=\s*(?:input|pubSignal|publicInputs?)\s*\[",
        rf"\blt\s*\(\s*(?:calldataload|mload)\s*\([^\n;]{{0,180}}(?:input|pubSignals?|publicInputs?)[^\n;]{{0,180}},\s*{modulus}\s*\)",
        rf"\bge\s*\(\s*(?:calldataload|mload)\s*\([^\n;]{{0,180}}(?:input|pubSignals?|publicInputs?)[^\n;]{{0,180}},\s*{modulus}\s*\)",
        rf"\bcheckField\s*\([^\n;]{{0,180}}(?:input|pubSignals?|publicInputs?)",
    )
    return any(re.search(pattern, text, flags=re.I) for pattern in compare_patterns)


def git_head(repo: pathlib.Path) -> str | None:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True)
    return completed.stdout.strip() if completed.returncode == 0 else None


def analyze_file(path: pathlib.Path, repo: pathlib.Path, repository: str, commit: str | None) -> dict[str, object] | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = strip_comments(raw)
    constants = named_constants(text)
    gamma = extract_g2(text, constants, "gamma")
    delta = extract_g2(text, constants, "delta")
    verifier_markers = bool(re.search(r"\bverify(?:Tx|Proof)\s*\(", text, flags=re.I))
    key_markers = gamma is not None or delta is not None
    pairing_markers = "pairing" in text.lower() and ("G2Point" in text or "pairingProd" in text or "staticcall" in text)
    if not key_markers or not (verifier_markers or pairing_markers):
        return None

    ic_points = extract_ic_points(text, constants)
    reverse: dict[tuple[int, int], list[int]] = {}
    for index, point in ic_points.items():
        reverse.setdefault(point, []).append(index)
    duplicates = sorted(indices for indices in reverse.values() if len(indices) > 1)

    warnings: list[str] = []
    if gamma is not None and delta is not None and gamma == delta:
        warnings.append("gamma-equals-delta")
    if delta == BN254_G2:
        warnings.append("delta-is-default-bn254-g2")
    if duplicates:
        warnings.append("duplicate-ic-points")
    guard = canonical_guard(text, constants)
    if verifier_markers and not guard:
        warnings.append("no-public-input-canonicality-guard-detected")
    if gamma is None or delta is None:
        warnings.append("g2-key-parse-incomplete")

    return {
        "repository": repository,
        "commit": commit,
        "path": path.relative_to(repo).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "has_verify_function": verifier_markers,
        "gamma": list(gamma) if gamma is not None else None,
        "delta": list(delta) if delta is not None else None,
        "gamma_equals_delta": gamma is not None and delta is not None and gamma == delta,
        "delta_is_default_bn254_g2": delta == BN254_G2,
        "ic_points_parsed": len(ic_points),
        "duplicate_ic_indices": duplicates,
        "canonical_public_input_guard_detected": guard,
        "warnings": warnings,
        "evidence_grade": "E1" if warnings else "E0",
        "verdict": "UNKNOWN",
    }


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", type=pathlib.Path, default=root / "feasibility/work/v2/repos")
    parser.add_argument("--output-json", type=pathlib.Path, default=here / "p4-census.json")
    parser.add_argument("--output-csv", type=pathlib.Path, default=here / "p4-census.csv")
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    repo_count = 0
    for repo in sorted(path for path in args.repos.iterdir() if (path / ".git").exists()):
        repo_count += 1
        repository = repo.name.replace("__", "/", 1)
        commit = git_head(repo)
        for path in sorted(repo.rglob("*.sol")):
            if not path.is_file():
                continue
            if EXCLUDED & set(path.relative_to(repo).parts):
                continue
            if path.stat().st_size > 5_000_000:
                continue
            record = analyze_file(path, repo, repository, commit)
            if record is not None:
                records.append(record)

    warning_counts = Counter(
        warning for record in records for warning in record["warnings"]  # type: ignore[index]
    )
    summary = {
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "scope": "public repository source at frozen commits; no deployment correspondence",
        "repositories": repo_count,
        "key_bearing_solidity_files": len(records),
        "unique_key_source_hashes": len({record["sha256"] for record in records}),
        "files_with_gamma_equal_delta": sum(bool(record["gamma_equals_delta"]) for record in records),
        "files_with_default_delta": sum(bool(record["delta_is_default_bn254_g2"]) for record in records),
        "files_with_duplicate_ic": sum(bool(record["duplicate_ic_indices"]) for record in records),
        "verify_files_without_detected_canonical_guard": sum(
            bool(record["has_verify_function"]) and not bool(record["canonical_public_input_guard_detected"])
            for record in records
        ),
        "warning_counts": dict(sorted(warning_counts.items())),
    }
    payload = {"summary": summary, "records": records}
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "repository", "commit", "path", "sha256", "has_verify_function",
            "gamma_equals_delta", "delta_is_default_bn254_g2", "ic_points_parsed",
            "duplicate_ic_indices", "canonical_public_input_guard_detected", "warnings",
            "evidence_grade", "verdict",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {key: record[key] for key in fieldnames}
            row["duplicate_ic_indices"] = json.dumps(row["duplicate_ic_indices"])
            row["warnings"] = "|".join(row["warnings"])  # type: ignore[arg-type]
            writer.writerow(row)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
