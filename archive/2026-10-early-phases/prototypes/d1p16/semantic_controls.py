#!/usr/bin/env python3
"""Exercise D1P-18 semantic edge controls and emit 22-family coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compare_executions import eval_ir, map_value, selected_path
from extract_relation import Extractor, UINT256_MAX


def context(**updates: Any) -> dict[str, Any]:
    base = {
        "calldata._nullifier": 11,
        "block.chainid": 31337,
        "calldata._amount": 5,
        "calldata._gigaRoot": 22,
        "calldata._localRoot": 33,
        "pre.aztecWarptoadAddress": 0,
        "calldata._feeFactor": 1,
        "calldata._priorityFee": 0,
        "calldata._maxFee": 10,
        "calldata._relayer": 9,
        "calldata._recipient": 8,
        "calldata._poof": "synthetic-proof-symbol",
        "block.basefee": 1,
        "msg.sender": 7,
        "producer_relation": True,
        "pre.withdrawVerifier": 99,
        "pre.gigaRootHistory": map_value({22: True}, False),
        "pre.localRootHistory": map_value({33: True}, False),
        "pre.nullifiers": map_value({}, False),
        "pre._balances": map_value({}, 0),
        "pre._totalSupply": 0,
    }
    base.update(updates)
    return base


def select(relation: dict[str, Any], expected: str, **updates: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    values = context(**updates)
    path, errors = selected_path(relation, values)
    if errors or path is None or path["id"] != expected:
        raise AssertionError(f"expected {expected}, got {None if path is None else path['id']}: {errors}")
    return path, values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-info", type=Path, required=True)
    parser.add_argument("--compiler-output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--five-execution-comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    relation = Extractor(args.build_info, args.compiler_output, args.source).extract()
    paths = {path["id"]: path for path in relation["paths"]}
    if list(paths) != [f"p{i:02d}" for i in range(22)]:
        raise AssertionError("expected stable p00..p21 path-family enumeration")

    concrete: dict[str, list[str]] = {
        "checked_arithmetic": [],
        "storage_aliasing": [],
        "zero_value_effects": [],
        "revert_rollback": [],
    }

    arithmetic_cases = [
        ("p04", {"block.basefee": UINT256_MAX, "calldata._priorityFee": 1}),
        ("p05", {"block.basefee": UINT256_MAX, "calldata._feeFactor": 2, "calldata._maxFee": UINT256_MAX}),
        ("p10", {"pre._totalSupply": UINT256_MAX}),
        ("p15", {"calldata._amount": 0}),
    ]
    for expected, updates in arithmetic_cases:
        path, _ = select(relation, expected, **updates)
        if path["revert"]["reason"] != "Panic(0x11)":
            raise AssertionError(f"{expected} is not a checked-arithmetic panic")
        concrete["checked_arithmetic"].append(expected)

    alias_cases = [
        ("p14", {"calldata._relayer": 1, "msg.sender": 8, "calldata._recipient": 8}),
        ("p18", {"calldata._relayer": 8, "calldata._recipient": 8}),
    ]
    for expected, updates in alias_cases:
        path, values = select(relation, expected, **updates)
        balances = eval_ir(path["committed"]["post_state_ir"]["_balances"], values)
        if balances[8] != 5:
            raise AssertionError(f"{expected} lost sequential aliased balance stores: {balances[8]}")
        concrete["storage_aliasing"].append(expected)

    zero_cases = [
        ("p14", {"calldata._relayer": 1, "msg.sender": 8, "calldata._recipient": 8,
                 "block.basefee": 0, "calldata._amount": 0}),
        ("p18", {"calldata._relayer": 8, "calldata._recipient": 8,
                 "block.basefee": 0, "calldata._amount": 0}),
        ("p21", {"calldata._feeFactor": 0, "calldata._amount": 0}),
    ]
    for expected, updates in zero_cases:
        path, values = select(relation, expected, **updates)
        amounts = [eval_ir(mint["amount_ir"], values) for mint in path["committed"]["mints"]]
        if not amounts or any(amount != 0 for amount in amounts):
            raise AssertionError(f"{expected} did not retain zero-value mint occurrences: {amounts}")
        if len(path["committed"]["events"]) != len(path["committed"]["mints"]):
            raise AssertionError(f"{expected} dropped a zero-value Transfer event")
        concrete["zero_value_effects"].append(expected)

    revert_ids = [path_id for path_id, path in paths.items() if path["status"] == "revert"]
    for path_id in revert_ids:
        committed = paths[path_id]["committed"]
        if any(committed[name] for name in ["storage_writes", "mints", "burns", "transfers", "events"]):
            raise AssertionError(f"{path_id} committed an effect after revert")
    if not any(paths[path_id]["tentative"]["storage_writes"] for path_id in revert_ids):
        raise AssertionError("rollback control did not include a tentative write")
    if not any(paths[path_id]["tentative"]["mints"] for path_id in revert_ids):
        raise AssertionError("rollback control did not include a tentative library effect")
    concrete["revert_rollback"] = revert_ids

    arithmetic_families = {
        path_id for path_id, path in paths.items()
        if any("no_overflow_" in guard or "no_underflow_" in guard for guard in path["guards"])
        and path["status"] == "revert" and path["revert"]["reason"] == "Panic(0x11)"
    }
    coverage = {
        "checked_arithmetic": sorted(arithmetic_families),
        "storage_aliasing": ["p14", "p18"],
        "zero_value_effects": ["p14", "p18", "p21"],
        "revert_rollback": revert_ids,
    }

    five = json.loads(args.five_execution_comparison.read_text())
    execution_paths: dict[str, list[str]] = {path_id: [] for path_id in paths}
    for name, case in five["cases"].items():
        execution_paths[case["selected_path"]].append(name)

    matrix = []
    for path_id, path in paths.items():
        matrix.append({
            "path_family": path_id,
            "status": path["status"],
            "revert_reason": None if path["status"] == "success" else path["revert"]["reason"],
            "controls": [name for name, covered in coverage.items() if path_id in covered],
            "recorded_executions": execution_paths[path_id],
        })

    covered_union = set().union(*(set(items) for items in coverage.values())) | {
        path_id for path_id, names in execution_paths.items() if names
    }
    report = {
        "schema": "bindcheck.d1p18.semantic-controls.v1",
        "path_family_count": len(paths),
        "controls": {
            name: {"concretely_selected": concrete[name], "covered_path_families": coverage[name]}
            for name in coverage
        },
        "path_family_matrix": matrix,
        "recorded_execution_selected_paths": execution_paths,
        "uncovered_by_controls_and_recorded_executions": sorted(set(paths) - covered_union),
        "not_selected_by_five_recorded_executions": sorted(
            path_id for path_id, names in execution_paths.items() if not names
        ),
        "all_checks_pass": True,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
