#!/usr/bin/env python3
"""Solver-free validation of the D1P-03 N=8 producer-walk partition.

This checker deliberately contains no solver or process-launch interface.  It
validates a five-class specialization of each eight-word producer stream
against an independently implemented transition for the frozen walk spec, and
then checks the closed-form goals against a rank-state reference evaluator.
It does not inspect or solve ACIR constraints.
"""

import argparse
import hashlib
import itertools
import json
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "scripts/t22_specs/payy_agg_agg.json"
BUILDER_PATH = ROOT / "scripts/t22_v5_compact.py"
ALPHABET = (0, 1, 2, 3, 4)
CELLS = ("inactive", "active_empty", "length_4", "length_5", "truncated_8")
CELL_LENGTH = {
    "inactive": 0,
    "active_empty": 0,
    "length_4": 4,
    "length_5": 5,
    "truncated_8": 8,
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records():
    spec = json.loads(SPEC_PATH.read_text())
    expected = {"mode": "walk", "records": {"2": 4, "3": 5, "4": 5}}
    if spec.get("derivation") != expected or len(spec.get("streams", ())) != 2:
        raise AssertionError("frozen N=8/two-stream walk specification changed")
    return {int(kind): length for kind, length in expected["records"].items()}


def reference_walk(words, active, records):
    """Literal transition interpretation of the frozen producer walk."""
    if not active:
        return (False,) * len(words)
    ended = False
    remaining = 0
    emitted = []
    for word in words:
        record_length = records.get(word, 0)
        flag = not ended and (remaining != 0 or record_length != 0)
        if remaining == 0 and record_length == 0:
            ended = True
        if ended:
            remaining = 0
        elif remaining:
            remaining -= 1
        else:
            remaining = record_length - 1
        emitted.append(flag)
    return tuple(emitted)


def cell_predicates(words, active, records):
    valid = frozenset(records)
    first = words[0]
    return {
        "inactive": not active,
        "active_empty": active and first not in valid,
        "length_4": active and first == 2 and words[4] not in valid,
        "length_5": active and first in (3, 4) and words[5] not in valid,
        "truncated_8": active and (
            (first == 2 and words[4] in valid)
            or (first in (3, 4) and words[5] in valid)
        ),
    }


def classify(words, active, records):
    matches = tuple(name for name, value in cell_predicates(words, active, records).items() if value)
    if len(matches) != 1:
        raise AssertionError((words, active, matches))
    return matches[0]


def specialized_walk(cell):
    length = CELL_LENGTH[cell]
    return tuple(index < length for index in range(8))


def compact_walk(words, active, records):
    if not active or words[0] not in records:
        length = 0
    else:
        length = records[words[0]]
        if words[length] in records:
            length = 8
    return tuple(index < length for index in range(8))


def logical_truncated_length(words, records):
    first_length = records[words[0]]
    return first_length + records[words[first_length]]


def reference_goals(total, message_bits):
    """Rank-state interpretation of the v5 nonvacuous/prefix/tail goals."""
    rank = 0
    prefix = False
    for _ in range(total):
        if rank >= 8:
            prefix = True
        elif message_bits & (1 << rank):
            prefix = True
        rank += 1
    nonvacuous = 1 <= rank <= 8
    tail = any(rank <= index and message_bits & (1 << index) for index in range(8))
    return nonvacuous, prefix, tail


def specialized_goals(total, message_bits):
    nonvacuous = 1 <= total <= 8
    prefix = total > 8 or any(
        message_bits & (1 << index) for index in range(min(total, 8))
    )
    tail = total <= 8 and any(
        message_bits & (1 << index) for index in range(total, 8)
    )
    return nonvacuous, prefix, tail


def validate():
    records = load_records()
    cell_counts = Counter()
    truncated_lengths = Counter()
    stream_cases = 0
    predicate_matches = 0
    for active in (False, True):
        for words in itertools.product(ALPHABET, repeat=8):
            predicates = cell_predicates(words, active, records)
            matches = sum(predicates.values())
            if matches != 1:
                raise AssertionError((words, active, predicates))
            predicate_matches += matches
            cell = classify(words, active, records)
            expected = reference_walk(words, active, records)
            specialized = specialized_walk(cell)
            compact = compact_walk(words, active, records)
            if specialized != expected or compact != expected:
                raise AssertionError((words, active, cell, expected, specialized, compact))
            cell_counts[cell] += 1
            if cell == "truncated_8":
                truncated_lengths[logical_truncated_length(words, records)] += 1
            stream_cases += 1

    expected_counts = {
        "inactive": 390625,
        "active_empty": 156250,
        "length_4": 31250,
        "length_5": 62500,
        "truncated_8": 140625,
    }
    if dict(cell_counts) != expected_counts:
        raise AssertionError((cell_counts, expected_counts))
    if dict(truncated_lengths) != {8: 15625, 9: 62500, 10: 62500}:
        raise AssertionError(truncated_lengths)

    goal_cases = 0
    pair_totals = Counter()
    overflow_cells = []
    for left, right in itertools.product(CELLS, repeat=2):
        total = CELL_LENGTH[left] + CELL_LENGTH[right]
        pair_totals[total] += 1
        if total > 8:
            overflow_cells.append((left, right, total))
        # Non-vacuity is message-independent but is still one checked case.
        if reference_goals(total, 0)[0] != specialized_goals(total, 0)[0]:
            raise AssertionError((left, right, "nonvacuous"))
        goal_cases += 1
        # A bit means mismatch at an emitted rank for prefix, and nonzero at
        # an outer-message index for tail.  Enumerating all 2^8 patterns is
        # exhaustive for both Boolean goal abstractions.
        for bits in range(1 << 8):
            reference = reference_goals(total, bits)
            specialized = specialized_goals(total, bits)
            if reference[1:] != specialized[1:]:
                raise AssertionError((left, right, bits, reference, specialized))
            goal_cases += 2

    return {
        "task": "D1P-03",
        "status": "PASS",
        "security_verdict": "UNKNOWN",
        "solver_processes_launched": 0,
        "scope": "offline producer-walk partition and Boolean-goal equivalence only",
        "source_sha256": {
            str(SPEC_PATH.relative_to(ROOT)): sha256(SPEC_PATH),
            str(BUILDER_PATH.relative_to(ROOT)): sha256(BUILDER_PATH),
            str(Path(__file__).resolve().relative_to(ROOT)): sha256(Path(__file__).resolve()),
        },
        "enumeration": {
            "word_equivalence_classes": {
                "0": "zero / producer-invalid / consumer padding",
                "1": "representative nonzero unsupported kind",
                "2": "producer 4-word record",
                "3": "producer 5-word record",
                "4": "producer 5-word record; consumer-invalid",
            },
            "stream_cases": stream_cases,
            "predicate_matches": predicate_matches,
            "cell_counts": {name: cell_counts[name] for name in CELLS},
            "truncated_logical_length_counts": {
                str(length): truncated_lengths[length] for length in sorted(truncated_lengths)
            },
            "pair_cells": len(CELLS) ** 2,
            "pair_total_length_cell_counts": {
                str(length): pair_totals[length] for length in sorted(pair_totals)
            },
            "overflow_pair_cells": [
                {"left": left, "right": right, "observed_length": total}
                for left, right, total in overflow_cells
            ],
            "goal_cases": goal_cases,
        },
        "claims": {
            "single_stream_partition_exhaustive": True,
            "single_stream_partition_mutually_exclusive": True,
            "pair_partition_exhaustive_by_cartesian_product": True,
            "pair_partition_mutually_exclusive_by_cartesian_product": True,
            "specialized_walk_equivalent_on_all_enumerated_classes": True,
            "specialized_goals_equivalent_on_all_cell_pairs_and_boolean_patterns": True,
        },
        "does_not_establish": [
            "ACIR satisfiability or cone soundness",
            "SMT serialization or solver behavior",
            "equivalence for a different stream bound or record grammar",
            "consumer decoding, successful execution, rollback, or committed effects",
            "proof feasibility, reachability, or a D1 security verdict",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    result = validate()
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
