"""Component semantic checker for decoded beta.22 ACIR.

Supported proof-enforced semantics are arithmetic ``AssertZero`` constraints
and ``RANGE`` black boxes.  Everything else is inventoried explicitly; no
unsupported proof-enforced element is treated as satisfied.
"""

from __future__ import annotations

from collections import Counter

from ..model_v2 import FIELD_MODULUS, Unsupported


def parse_witnesses(payload: dict) -> dict[int, int]:
    result = {}
    for raw_index, raw_value in payload["witnesses"].items():
        try:
            index = int(raw_index)
            value = int(raw_value, 0)
        except (TypeError, ValueError) as exc:
            raise Unsupported("BETA22_WITNESS_VALUE_ENCODING", f"{raw_index}: {raw_value}") from exc
        if index < 0 or value < 0 or value >= FIELD_MODULUS:
            raise Unsupported("BETA22_WITNESS_VALUE_NONCANONICAL", f"{index}: {value}")
        if index in result:
            raise Unsupported("BETA22_DUPLICATE_WITNESS", str(index))
        result[index] = value
    return result


def witness_value(witnesses: dict[int, int], index: int) -> int:
    try:
        return witnesses[index]
    except KeyError as exc:
        raise Unsupported("BETA22_WITNESS_MISSING", str(index)) from exc


def evaluate_expression(expression: dict, witnesses: dict[int, int]) -> int:
    value = expression["constant"]
    for coefficient, lhs, rhs in expression["mul"]:
        value += coefficient * witness_value(witnesses, lhs) * witness_value(witnesses, rhs)
    for coefficient, index in expression["linear"]:
        value += coefficient * witness_value(witnesses, index)
    return value % FIELD_MODULUS


def function_input_value(function_input: dict, witnesses: dict[int, int]) -> int:
    if "constant" in function_input:
        return function_input["constant"]
    if "witness" in function_input:
        return witness_value(witnesses, function_input["witness"])
    raise Unsupported("BETA22_FUNCTION_INPUT_INTERNAL_SHAPE", repr(function_input))


def check_supported(circuit: dict, witnesses: dict[int, int]) -> dict:
    supported_counts = Counter()
    satisfied_counts = Counter()
    failures = []
    proof_unsupported = Counter()
    witness_generation = Counter()
    all_counts = Counter()

    for opcode in circuit["opcodes"]:
        kind = opcode["kind"]
        all_counts[kind] += 1
        if kind == "AssertZero":
            supported_counts[kind] += 1
            residual = evaluate_expression(opcode["expression"], witnesses)
            if residual == 0:
                satisfied_counts[kind] += 1
            else:
                failures.append({"opcode_index": opcode["opcode_index"], "kind": kind,
                                 "residual": str(residual)})
        elif kind == "RANGE":
            supported_counts[kind] += 1
            value = function_input_value(opcode["input"], witnesses)
            if value < (1 << opcode["num_bits"]):
                satisfied_counts[kind] += 1
            else:
                failures.append({"opcode_index": opcode["opcode_index"], "kind": kind,
                                 "value": str(value), "num_bits": opcode["num_bits"]})
        elif kind == "BrilligCall":
            witness_generation[kind] += 1
        elif kind in ("Poseidon2Permutation", "MemoryOp", "MemoryInit", "Call"):
            proof_unsupported[kind] += 1
        else:
            # The decoder should already reject this; keep the checker fail-closed too.
            raise Unsupported("BETA22_SEMANTIC_OPCODE_UNCLASSIFIED", kind)

    return {
        "all_constrained_function_opcode_counts": dict(sorted(all_counts.items())),
        "supported_proof_constraint_counts": dict(sorted(supported_counts.items())),
        "satisfied_supported_constraint_counts": dict(sorted(satisfied_counts.items())),
        "supported_proof_constraint_total": sum(supported_counts.values()),
        "satisfied_supported_constraint_total": sum(satisfied_counts.values()),
        "supported_failures": failures,
        "all_supported_constraints_satisfied": not failures and supported_counts == satisfied_counts,
        "unsupported_proof_enforced_counts": {
            kind: proof_unsupported.get(kind, 0)
            for kind in ("Poseidon2Permutation", "MemoryOp", "MemoryInit", "Call")
        },
        "unsupported_proof_enforced_total": sum(proof_unsupported.values()),
        "witness_generation_acir_counts": {"BrilligCall": witness_generation.get("BrilligCall", 0)},
        "classified_opcode_total": sum(supported_counts.values()) + sum(proof_unsupported.values()) + sum(witness_generation.values()),
        "decoded_opcode_total": len(circuit["opcodes"]),
        "no_skipped_opcodes": (
            sum(supported_counts.values()) + sum(proof_unsupported.values()) + sum(witness_generation.values())
            == len(circuit["opcodes"])
        ),
    }


def expression_witnesses(expression: dict) -> set[int]:
    result = set()
    for _coefficient, lhs, rhs in expression["mul"]:
        result.update((lhs, rhs))
    for _coefficient, index in expression["linear"]:
        result.add(index)
    return result
