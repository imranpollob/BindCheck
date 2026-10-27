#!/usr/bin/env python3
"""Plan and execute D1P-13 component semantic checks; invokes no solver/prover."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from bindcheck_d1.frontends.acir_binary_beta22 import decode
from bindcheck_d1.frontends.acir_semantics_beta22 import (
    check_supported,
    evaluate_expression,
    expression_witnesses,
    parse_witnesses,
)
from bindcheck_d1.model_v2 import FIELD_MODULUS


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load(artifact: Path, witness_path: Path):
    decoded = decode(artifact)
    witness_payload = json.loads(witness_path.read_text())
    return decoded, parse_witnesses(witness_payload)


def plan(artifact: Path, witness_path: Path, output: Path) -> None:
    if output.exists():
        raise SystemExit(f"mutation plan already exists; refusing to overwrite: {output}")
    decoded, witnesses = load(artifact, witness_path)
    circuit = decoded["functions"][0]
    mutations = []

    for opcode in circuit["opcodes"]:
        if opcode["kind"] != "AssertZero":
            continue
        if evaluate_expression(opcode["expression"], witnesses) != 0:
            raise SystemExit(f"cannot plan from unsatisfied baseline opcode {opcode['opcode_index']}")
        for index in sorted(expression_witnesses(opcode["expression"])):
            original = witnesses[index]
            replacement = (original + 1) % FIELD_MODULUS
            changed = dict(witnesses)
            changed[index] = replacement
            residual = evaluate_expression(opcode["expression"], changed)
            if residual:
                mutations.append({
                    "id": "assert-zero-single-witness-plus-one",
                    "witness": index,
                    "original": str(original),
                    "replacement": str(replacement),
                    "dependency_provenance": {
                        "opcode_index": opcode["opcode_index"], "kind": "AssertZero",
                        "decoded_expression": opcode["expression"],
                    },
                    "expected": {
                        "target_constraint_fails": True,
                        "expected_residual": str(residual),
                        "justification": "Holding every other solved witness fixed, direct field evaluation of the decoded polynomial is nonzero after the stated replacement.",
                    },
                })
                break
        if mutations:
            break
    if not mutations:
        raise SystemExit("no justified AssertZero mutation found")

    for opcode in circuit["opcodes"]:
        if opcode["kind"] != "RANGE" or "witness" not in opcode["input"]:
            continue
        if opcode["num_bits"] >= 253:
            continue
        index = opcode["input"]["witness"]
        replacement = 1 << opcode["num_bits"]
        if replacement >= FIELD_MODULUS or replacement == witnesses[index]:
            continue
        mutations.append({
            "id": "range-upper-bound",
            "witness": index,
            "original": str(witnesses[index]),
            "replacement": str(replacement),
            "dependency_provenance": {
                "opcode_index": opcode["opcode_index"], "kind": "RANGE",
                "num_bits": opcode["num_bits"], "decoded_input": opcode["input"],
            },
            "expected": {
                "target_constraint_fails": True,
                "justification": f"The replacement equals 2^{opcode['num_bits']}, outside the decoded RANGE requirement value < 2^{opcode['num_bits']}.",
            },
        })
        break
    if len(mutations) != 2:
        raise SystemExit("no justified RANGE mutation found")

    write_json(output, {
        "schema": "bindcheck.d1p13.mutation-plan/v1",
        "frozen_at_utc": utc_now(),
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "witness": {"path": str(witness_path), "sha256": sha256(witness_path)},
        "freeze_rule": "This file is written before any mutation is evaluated and must not be overwritten.",
        "mutations": mutations,
    })


def check(artifact: Path, witness_path: Path, plan_path: Path, output: Path) -> None:
    decoded, witnesses = load(artifact, witness_path)
    circuit = decoded["functions"][0]
    frozen = json.loads(plan_path.read_text())
    if frozen["artifact"]["sha256"] != sha256(artifact) or frozen["witness"]["sha256"] != sha256(witness_path):
        raise SystemExit("mutation plan input identity mismatch")
    honest = check_supported(circuit, witnesses)
    mutation_results = []
    for mutation in frozen["mutations"]:
        changed = dict(witnesses)
        index = mutation["witness"]
        if str(changed[index]) != mutation["original"]:
            raise SystemExit(f"mutation original mismatch: {mutation['id']}")
        changed[index] = int(mutation["replacement"])
        result = check_supported(circuit, changed)
        target = mutation["dependency_provenance"]
        target_failure = next((failure for failure in result["supported_failures"]
                               if failure["opcode_index"] == target["opcode_index"]
                               and failure["kind"] == target["kind"]), None)
        mutation_results.append({
            "id": mutation["id"], "witness": index,
            "expected": mutation["expected"],
            "observed": {
                "target_constraint_failed": target_failure is not None,
                "target_failure": target_failure,
                "supported_failure_count": len(result["supported_failures"]),
                "supported_failure_kind_counts": {
                    kind: sum(1 for failure in result["supported_failures"] if failure["kind"] == kind)
                    for kind in sorted({failure["kind"] for failure in result["supported_failures"]})
                },
            },
            "expectation_matched": target_failure is not None,
        })

    brillig_counts = {}
    brillig_total = 0
    for function in decoded["unconstrained_functions"]:
        brillig_total += function["opcode_count"]
        for kind, count in function["opcode_kind_counts"].items():
            brillig_counts[kind] = brillig_counts.get(kind, 0) + count
    write_json(output, {
        "schema": "bindcheck.d1p13.semantic-check/v1",
        "created_at_utc": utc_now(),
        "artifact": {"path": str(artifact), "sha256": sha256(artifact)},
        "witness": {"path": str(witness_path), "sha256": sha256(witness_path)},
        "decoder_identity": decoded["identity"],
        "honest_supported_check": honest,
        "unsupported_semantic_elements": {
            "proof_enforced": honest["unsupported_proof_enforced_counts"],
            "witness_generation_only": {
                "BrilligCall": honest["witness_generation_acir_counts"]["BrilligCall"],
                "unconstrained_function_count": len(decoded["unconstrained_functions"]),
                "brillig_opcode_total": brillig_total,
                "brillig_opcode_kind_counts": dict(sorted(brillig_counts.items())),
            },
        },
        "semantic_boundary": "Poseidon2Permutation remains uninterpreted; therefore this is not a whole-circuit satisfaction or security result.",
        "mutation_plan": {"path": str(plan_path), "sha256": sha256(plan_path)},
        "mutation_results": mutation_results,
        "all_mutation_expectations_matched": all(item["expectation_matched"] for item in mutation_results),
        "solver_calls": 0,
        "prover_calls": 0,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--witness", required=True, type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--check", dest="check_output", type=Path)
    args = parser.parse_args()
    if bool(args.plan) == bool(args.check_output):
        raise SystemExit("choose exactly one of --plan or --check")
    plan_path = args.plan if args.plan else args.check_output.parent / "mutation-plan.json"
    if args.plan:
        plan(args.artifact, args.witness, args.plan)
    else:
        check(args.artifact, args.witness, plan_path, args.check_output)


if __name__ == "__main__":
    main()
