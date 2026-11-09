#!/usr/bin/env python3
"""Explain every DEV UNKNOWN from a retained unhinted result set.

Reads only the caller-supplied DEV raw directory and the pinned DEV checkout
root. It never opens the combined source-corpus or evaluation namespaces.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re

from bindcheck_zk.solidity import functions, mask_comments_and_strings


PATTERNS = ("P1", "P2", "P3", "P4", "P5")
NO_TRIPLE = {
    "DEV-F05": ("verifier and effect in separate diamond facets", "eth/contracts/Verifier.sol:266;eth/contracts/facets/DFAdminFacet.sol"),
    "DEV-F13": ("selector-driven verifier dispatch through inherited helper", "sdk/src/contracts/ZKRollup.sol:22"),
    "DEV-F17": ("verifier source without a consuming contract", "contracts/Verifier.sol:65"),
    "DEV-F18": ("same-function verifier call and nonce roll not discovered", "ZTIZEN/smart-contracts/contracts/ZTIZENCircom.sol:281"),
    "DEV-F21": ("bridge effects with no recovered Groth16 call", "contracts/ethereum/ChronosVault.sol"),
    "DEV-F22": ("bridge effects with no recovered Groth16 call", "contracts/ethereum/ChronosVault.sol"),
    "DEV-F23": ("verifier and token effects in separate contracts", "code/blockchain/contracts/zk/Groth16Verifier.sol:231"),
    "DEV-F26": ("mock internal proof helper outside verifier-call recognizer", "backend/contracts/ZKCredentialVerifier.sol:128"),
    "DEV-F37": ("low-level ABI-encoded verifier call", "contracts/CredentialRegistry.sol:315"),
    "DEV-F43": ("verifier source without a consuming contract", "beacon-light-client/solidity/contracts/bridge/src/utils/Verifier.sol:62"),
}


def code_shape(reason: str, triple: dict, source_root: pathlib.Path) -> str:
    consumer = triple.get("consumer") or {}
    vector = (consumer.get("public_vectors") or [{}])[0]
    expression = vector.get("expression", "")
    if reason == "PROTECTED_EFFECT_NOT_RECOVERED":
        path = consumer.get("path")
        if path:
            try:
                source = (source_root / path).read_text(errors="replace")
                parsed = next((item for item in functions(source)
                               if item.name == consumer.get("function") and item.line == consumer.get("line")), None)
            except OSError:
                parsed = None
            if parsed:
                body = mask_comments_and_strings(parsed.body)
                if re.search(r"\b(?:view|pure)\b", parsed.header):
                    return "read-only verifier utility"
                if re.search(r"\bemit\s+\w+\s*\(", body) and not re.search(r"(?<![=!<>])=(?!=)|\+=|-=", body):
                    return "event-only verifier path"
                if re.search(r"\b\w+\s*\[[^]]+\]\s*(?:=|\+=|-=)|\b\w+\.\w+\s*(?:=|\+=|-=)", body):
                    return "indexed/member assignment with unresolved storage semantics"
                other_calls = re.sub(r"\b\w+\s*\.\s*(?:verifyProof|verifyTx|verify|validateProof|verifyPlonk)\s*\(", "", body)
                if re.search(r"\b(?:_\w+|\w+\.\w+)\s*\(", other_calls):
                    return "effect delegated beyond verifier-call function"
        return "no inline protected effect on verifier-call path"
    if reason == "UNRESOLVED_CONSUMER_MODIFIER":
        path = consumer.get("path")
        if path:
            try:
                source = (source_root / path).read_text(errors="replace")
                parsed = next((item for item in functions(source)
                               if item.name == consumer.get("function") and item.line == consumer.get("line")), None)
            except OSError:
                parsed = None
            if parsed:
                header = parsed.header
                if "whenNotPaused" in header or "whenPaused" in header:
                    return "OpenZeppelin Pausable modifier"
                if "nonReentrant" in header:
                    return "local reentrancy lock modifier"
                return "custom modifier: " + re.sub(r"\s+", " ", header.split(")", 1)[-1].strip())[:90]
        return "unresolved modifier"
    if reason == "UNRESOLVED_CONSUMER_INHERITANCE":
        path = consumer.get("path")
        if path:
            try:
                source = (source_root / path).read_text(errors="replace")
            except OSError:
                source = ""
            if "ERC721Enumerable" in source:
                return "ERC721Enumerable inherited token effect"
            if "ERC20" in source or "ERC721" in source:
                return "token inheritance or override unresolved"
        return "custom/ambiguous inherited call path"
    if reason == "PUBLIC_INPUT_VECTOR_UNRESOLVED":
        if "." in expression:
            return "struct/member public vector"
        if "[" in expression:
            return "indexed public vector expression"
        return "public vector alias or type unresolved"
    if reason == "PUBLIC_INPUT_ORDER_UNRESOLVED":
        if not vector.get("items") and vector.get("declared_count") is not None:
            return "fixed public array passed without named elements"
        return "circuit or consumer element order incomplete"
    if reason == "PUBLIC_INPUT_MEANING_UNRESOLVED":
        return "circuit/consumer public names differ"
    if reason == "DYNAMIC_PUBLIC_INPUT_LENGTH_UNRESOLVED":
        return "dynamic public array without exact length guard"
    if reason == "VERIFIER_MATCH_AMBIGUOUS":
        return "multiple verifier shapes retained for consumer"
    if reason == "NO_CONTEXT_BINDING_RECOVERED":
        return "no live chain/contract/domain value in statement"
    if reason == "CONTEXT_COMPUTATION_NOT_GUARDED":
        return "context computed without dominating statement binding"
    if reason == "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND":
        return "verifier scalar guard absent or unsupported"
    if reason == "UNSUPPORTED_VERIFIER_KEY_LAYOUT":
        return "non-Groth16/PLONK verifier layout"
    if reason == "REPLAY_KEY_EXPRESSION_UNRESOLVED":
        return "computed replay mapping key"
    if reason == "REPLAY_BARRIER_HELPER_UNRESOLVED":
        return "replay read/write delegated to helper"
    if reason == "REPLAY_KEY_POSITION_UNRESOLVED":
        return "replay key position in vector unresolved"
    if reason == "CALLER_INDEPENDENCE_UNRESOLVED":
        return "fixed/state-derived effect amount, caller independence unresolved"
    if reason == "CIRCUIT_INTERFACE_INCOMPLETE":
        return "source-only circuit public schema incomplete"
    if reason in {"CIRCUIT_ARTIFACT_MISSING", "VERIFIER_ARTIFACT_MISSING", "VERIFIER_IMPLEMENTATION_ARTIFACT_MISSING"}:
        return "matched circuit/verifier implementation missing"
    if reason in {"VERIFICATION_KEY_PARSE_INCOMPLETE", "VERIFIER_HELPER_GUARD_UNRESOLVED"}:
        return "key or delegated verifier guard unparsed"
    if reason == "FAIL_CLOSED_VERIFIER_PLACEHOLDER":
        return "fail-closed placeholder verifier"
    if reason == "DUPLICATE_IC_SOURCE_WARNING":
        return "duplicate IC source warning without full semantics"
    if reason == "REPLAY_KEY_NOT_RECOVERED":
        return "no replay mapping key on recovered function"
    return reason.lower().replace("_", " ")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=pathlib.Path, required=True)
    parser.add_argument("--checkouts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(args.raw.glob("DEV-*--result.json")):
        row_id = path.name.split("--", 1)[0]
        source_roots = list(args.checkouts.glob(row_id + "--*"))
        if len(source_roots) != 1:
            raise ValueError(f"pinned checkout missing or ambiguous: {row_id}")
        payload = json.loads(path.read_text())
        for pattern in PATTERNS:
            summary = payload["patterns"][pattern]
            if summary["verdict"] != "UNKNOWN":
                continue
            details = []
            for triple in payload["triples"]:
                finding = triple["patterns"][pattern]
                if finding["verdict"] != "UNKNOWN":
                    continue
                consumer = triple.get("consumer") or {}
                verifier = triple.get("verifier") or {}
                circuit = triple.get("circuit") or {}
                details.append({
                    "reason": finding["reason"],
                    "shape": code_shape(finding["reason"], triple, source_roots[0]),
                    "consumer": f"{consumer.get('path', 'MISSING')}:{consumer.get('line', 'MISSING')}:{consumer.get('function', 'MISSING')}",
                    "verifier": verifier.get("path", "MISSING"),
                    "circuit": circuit.get("path", "MISSING"),
                })
            if details:
                # Retain every distinct source/reason shape, including those
                # suppressed by the aggregate reason's alphabetical ordering.
                unique = list(dict.fromkeys((d["shape"], d["reason"], d["consumer"], d["verifier"], d["circuit"])
                                            for d in details))
                shapes = sorted({d[0] for d in unique})
                evidence = json.dumps(unique, separators=(",", ":"))
            else:
                build = payload["coverage"].get("builds", [])
                build_failed = [b["path"] for b in build if (b.get("record") or {}).get("exit_status") not in (None, 0)]
                shape, source = NO_TRIPLE.get(row_id, ("no verifier-consuming function triple discovered", "MISSING"))
                shapes = [shape]
                evidence = json.dumps({"build_paths_failed": build_failed,
                                       "unsupported": payload["coverage"].get("unsupported", []),
                                       "source": source}, separators=(",", ":"))
            rows.append({
                "row": row_id, "pattern": pattern, "applicability": summary["applicability"],
                "verdict": summary["verdict"], "reasons": ";".join(summary["reasons"]),
                "shapes": ";".join(shapes), "triple_count": len(details),
                "source_evidence": evidence, "raw_result": str(path),
            })
    if len({r["row"] for r in rows}) != 56:
        raise ValueError("expected 56 DEV rows")
    fields = list(rows[0])
    with (args.out / "unknown-inventory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    shape_rows = collections.defaultdict(set)
    shape_cells = collections.Counter()
    for row in rows:
        for shape in row["shapes"].split(";"):
            shape_rows[shape].add(row["row"])
            shape_cells[shape] += 1
    ranked = sorted(shape_rows, key=lambda shape: (-len(shape_rows[shape]), -shape_cells[shape], shape))
    with (args.out / "shape-counts.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["shape", "rows_affected", "unknown_cells", "rows"])
        for shape in ranked:
            writer.writerow([shape, len(shape_rows[shape]), shape_cells[shape], ";".join(sorted(shape_rows[shape]))])
    print(json.dumps({"unknown_cells": len(rows), "rows": len({r["row"] for r in rows}),
                      "shapes": len(shape_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
