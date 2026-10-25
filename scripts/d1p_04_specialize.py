#!/usr/bin/env python3
"""Generate and audit the D1P-04 25-cell T22-v5 specializations.

This module is serialization-only.  It contains no solver or process-launch
interface.  The frozen producer prefix is copied byte-for-byte from each
parent; only the v5 walk/goal suffix is replaced under an explicit cell.
"""

import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT / "results/raw/D1P-02/generated"
CELLS = ("inactive", "active_empty", "length_4", "length_5", "truncated_8")
CELL_LENGTH = {"inactive": 0, "active_empty": 0, "length_4": 4,
               "length_5": 5, "truncated_8": 8}
OUTER = tuple(f"w{i}" for i in range(1275, 1283))
STREAMS = (
    {"activation": "w508", "words": tuple(f"w{i}" for i in range(511, 519))},
    {"activation": "w1143", "words": tuple(f"w{i}" for i in range(2293, 2301))},
)
EXPECTED_PARENTS = {
    ("check_added", "nonvacuous"): "c0312431ed84da5b55094fc4b27212f607789d143ad56b54db52359235b794b3",
    ("check_added", "prefix"): "4ae2be7bcedcfe992966dc406d4cd8f2b43f1823fa49efd8fbfa14044631e781",
    ("check_added", "tail"): "3621cdfca8269e404aca638a24aa852da0406be1013f2c29511df47b6ff0a7a1",
    ("running_flag", "nonvacuous"): "af1ae83aafa43b9dbb06e110270dda0bff11c90371c2666143916fb067b21ff8",
    ("running_flag", "prefix"): "6ac4b20422b09c0deea148b977159919d1542b7d587cdde38a9e9583671b82b4",
    ("running_flag", "tail"): "4d80a119dfe1f781eb2a47cb60490143afc930eb150dec2b4da980370d900a3c",
}
WALK_START = re.compile(
    r"^\(define-fun b\d+ \(\) Bool \(and \(not \(= w508 \(as ff0 F\)\)\) "
    r"\(or \(= w511 \(as ff2 F\)\)"
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def smt_or(terms):
    terms = tuple(terms)
    if not terms:
        return "false"
    if len(terms) == 1:
        return terms[0]
    return f"(or {' '.join(terms)})"


def smt_and(terms):
    terms = tuple(terms)
    if not terms:
        return "true"
    if len(terms) == 1:
        return terms[0]
    return f"(and {' '.join(terms)})"


def eq_const(symbol, value):
    return f"(= {symbol} (as ff{value} F))"


def active(symbol):
    return f"(not {eq_const(symbol, 0)})"


def valid_kind(symbol):
    return smt_or(eq_const(symbol, value) for value in (2, 3, 4))


def cell_term(cell, stream):
    activation = stream["activation"]
    words = stream["words"]
    if cell == "inactive":
        return eq_const(activation, 0)
    if cell == "active_empty":
        return smt_and((active(activation), f"(not {valid_kind(words[0])})"))
    if cell == "length_4":
        return smt_and((active(activation), eq_const(words[0], 2),
                        f"(not {valid_kind(words[4])})"))
    if cell == "length_5":
        return smt_and((active(activation),
                        smt_or((eq_const(words[0], 3), eq_const(words[0], 4))),
                        f"(not {valid_kind(words[5])})"))
    if cell == "truncated_8":
        second_after_4 = smt_and((eq_const(words[0], 2), valid_kind(words[4])))
        second_after_5 = smt_and((
            smt_or((eq_const(words[0], 3), eq_const(words[0], 4))),
            valid_kind(words[5]),
        ))
        return smt_and((active(activation), smt_or((second_after_4, second_after_5))))
    raise ValueError(cell)


def cell_pairs():
    for index, (left, right) in enumerate(itertools.product(CELLS, repeat=2)):
        yield {
            "index": index,
            "id": f"{index:02d}_{left}__{right}",
            "left": left,
            "right": right,
            "left_length": CELL_LENGTH[left],
            "right_length": CELL_LENGTH[right],
            "total_length": CELL_LENGTH[left] + CELL_LENGTH[right],
            "predicate": smt_and((cell_term(left, STREAMS[0]), cell_term(right, STREAMS[1]))),
        }


def payload_map(cell):
    payload = []
    for stream_index, (stream, length) in enumerate(zip(
            STREAMS, (cell["left_length"], cell["right_length"]))):
        for offset in range(length):
            rank = len(payload)
            payload.append({
                "rank": rank,
                "stream": stream_index,
                "offset": offset,
                "payload_witness": stream["words"][offset],
                "outer_witness": OUTER[rank] if rank < len(OUTER) else None,
                "overflow": rank >= len(OUTER),
            })
    return payload


def specialized_goal(query, cell):
    total = cell["total_length"]
    payload = payload_map(cell)
    if query == "nonvacuous":
        return "true" if 1 <= total <= 8 else "false"
    if query == "prefix":
        if total > 8:
            return "true"
        return smt_or(
            f"(not (= {item['outer_witness']} {item['payload_witness']}))"
            for item in payload
        )
    if query == "tail":
        if total >= 8:
            return "false"
        return smt_or(f"(not {eq_const(OUTER[index], 0)})" for index in range(total, 8))
    raise ValueError(query)


def extract_assert_term(line):
    stripped = line.strip()
    if not stripped.startswith("(assert ") or not stripped.endswith(")"):
        raise ValueError("parent goal line is not one assertion")
    return stripped[len("(assert "):-1]


def parse_parent(family, query, path=None):
    path = Path(path or (PARENT_ROOT / family / f"{query}.smt2"))
    raw = path.read_bytes()
    actual_hash = sha256_bytes(raw)
    expected_hash = EXPECTED_PARENTS[(family, query)]
    if actual_hash != expected_hash:
        raise ValueError(f"parent hash mismatch: {family}/{query}: {actual_hash}")
    text = raw.decode("ascii")
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if WALK_START.match(line)]
    if len(starts) != 1:
        raise ValueError(f"walk boundary count {len(starts)}: {family}/{query}")
    start = starts[0]
    if len(lines) < 4 or lines[-2].strip() != "(check-sat)" or not lines[-1].startswith("(get-value "):
        raise ValueError(f"unexpected parent trailer: {family}/{query}")
    if any(line.startswith("(assert ") for line in lines[start:-3]):
        raise ValueError(f"walk block unexpectedly asserts: {family}/{query}")
    prefix = "".join(lines[:start]).encode("ascii")
    walk = "".join(lines[start:-3])
    goal_line = lines[-3]
    required = OUTER + tuple(x for stream in STREAMS for x in (stream["activation"], *stream["words"]))
    declarations = []
    for symbol in required:
        expected = f"(declare-const {symbol} F)\n"
        matches = [line for line in lines[:start] if line == expected]
        if len(matches) != 1:
            raise ValueError(f"declaration count for {symbol}: {len(matches)}")
        declarations.append(expected)
    return {
        "family": family,
        "query": query,
        "path": path,
        "raw": raw,
        "hash": actual_hash,
        "lines": lines,
        "producer_prefix": prefix,
        "producer_prefix_hash": sha256_bytes(prefix),
        "producer_prefix_bytes": len(prefix),
        "producer_prefix_lines": start,
        "producer_assertions": sum(line.startswith("(assert ") for line in lines[:start]),
        "walk": walk,
        "walk_hash": sha256_bytes(walk.encode("ascii")),
        "goal_line": goal_line,
        "goal": extract_assert_term(goal_line),
        "goal_hash": sha256_bytes(extract_assert_term(goal_line).encode("ascii")),
        "header": "".join(lines[:3]),
        "declarations": "".join(declarations),
        "get_value": lines[-1],
    }


def specialized_text(parent, cell):
    suffix = (
        "; D1P-04: producer prefix above is byte-identical to the frozen parent.\n"
        f"; cell {cell['id']}\n"
        f"(define-fun d1p04_cell () Bool {cell['predicate']})\n"
        f"(define-fun d1p04_specialized_goal () Bool {specialized_goal(parent['query'], cell)})\n"
        "(assert d1p04_cell)\n"
        "(assert d1p04_specialized_goal)\n"
        "(check-sat)\n"
        + parent["get_value"]
    ).encode("ascii")
    return parent["producer_prefix"] + suffix


def equivalence_text(parent, cell):
    common = parent["header"] + parent["declarations"] + parent["walk"]
    return (
        common
        + f"(define-fun d1p04_cell () Bool {cell['predicate']})\n"
        + f"(define-fun d1p04_original_goal () Bool {parent['goal']})\n"
        + f"(define-fun d1p04_specialized_goal () Bool {specialized_goal(parent['query'], cell)})\n"
        + "(define-fun d1p04_original_not_specialized () Bool "
          "(and d1p04_original_goal (not d1p04_specialized_goal)))\n"
        + "(define-fun d1p04_specialized_not_original () Bool "
          "(and d1p04_specialized_goal (not d1p04_original_goal)))\n"
        + "(assert (and d1p04_cell (or d1p04_original_not_specialized "
          "d1p04_specialized_not_original)))\n"
        + "(check-sat)\n"
    ).encode("ascii")


def control_text(mismatch=False):
    right = 1 if mismatch else 0
    return (
        "(set-logic QF_FF)\n"
        "(define-sort F () (_ FiniteField 21888242871839275222246405745257275088548364400416034343698204186575808495617))\n"
        "(declare-const control_x F)\n"
        "(define-fun control_original () Bool (= control_x (as ff0 F)))\n"
        f"(define-fun control_specialized () Bool (= control_x (as ff{right} F)))\n"
        "(assert (or (and control_original (not control_specialized)) "
        "(and control_specialized (not control_original))))\n"
        "(check-sat)\n"
    ).encode("ascii")


def build(output_root, manifest_path):
    output_root = Path(output_root).resolve()
    manifest_path = Path(manifest_path).resolve()
    if output_root.exists():
        raise FileExistsError(f"fresh output required: {output_root}")
    if manifest_path.exists():
        raise FileExistsError(f"fresh manifest required: {manifest_path}")

    parents = {}
    for family, query in EXPECTED_PARENTS:
        parents[(family, query)] = parse_parent(family, query)
    for family in ("check_added", "running_flag"):
        family_parents = [parents[(family, query)] for query in ("nonvacuous", "prefix", "tail")]
        if len({p["producer_prefix_hash"] for p in family_parents}) != 1:
            raise ValueError(f"producer prefix differs within {family}")
        if len({p["walk_hash"] for p in family_parents}) != 1:
            raise ValueError(f"walk definitions differ within {family}")

    output_root.mkdir(parents=True)
    controls_dir = output_root / "controls"
    controls_dir.mkdir()
    controls = []
    for name, mismatch, expected in (("known_equivalence", False, "unsat"),
                                     ("deliberate_mismatch", True, "sat")):
        path = controls_dir / f"{name}.smt2"
        data = control_text(mismatch)
        path.write_bytes(data)
        controls.append({"name": name, "path": str(path.relative_to(ROOT)),
                         "sha256": sha256_bytes(data), "bytes": len(data),
                         "expected": expected})

    generator_hash = sha256(Path(__file__).resolve())
    artifacts = []
    for family in ("check_added", "running_flag"):
        for query in ("nonvacuous", "prefix", "tail"):
            parent = parents[(family, query)]
            for cell in cell_pairs():
                cell_dir = output_root / family / query
                eq_dir = output_root / "equivalence" / family / query
                cell_dir.mkdir(parents=True, exist_ok=True)
                eq_dir.mkdir(parents=True, exist_ok=True)
                out_path = cell_dir / f"{cell['id']}.smt2"
                eq_path = eq_dir / f"{cell['id']}.smt2"
                out_data = specialized_text(parent, cell)
                eq_data = equivalence_text(parent, cell)
                if out_data[:parent["producer_prefix_bytes"]] != parent["producer_prefix"]:
                    raise AssertionError("producer prefix byte audit failed")
                if b"(assert " in eq_data.split(b"(define-fun d1p04_cell", 1)[0].split(
                        parent["walk"].encode("ascii"), 1)[0]:
                    raise AssertionError("producer assertion leaked into equivalence query")
                out_path.write_bytes(out_data)
                eq_path.write_bytes(eq_data)
                artifacts.append({
                    "slot": f"{family}/{query}/{cell['id']}",
                    "family": family,
                    "query": query,
                    "cell": cell,
                    "cell_predicate": cell["predicate"],
                    "payload_by_rank": payload_map(cell),
                    "specialized_goal": specialized_goal(query, cell),
                    "parent": {
                        "path": str(parent["path"].relative_to(ROOT)),
                        "sha256": parent["hash"],
                        "goal_sha256": parent["goal_hash"],
                    },
                    "producer_prefix_audit": {
                        "parent_byte_range": [0, parent["producer_prefix_bytes"]],
                        "output_byte_range": [0, parent["producer_prefix_bytes"]],
                        "bytes": parent["producer_prefix_bytes"],
                        "lines": parent["producer_prefix_lines"],
                        "assertions": parent["producer_assertions"],
                        "parent_sha256": parent["producer_prefix_hash"],
                        "output_sha256": sha256_bytes(out_data[:parent["producer_prefix_bytes"]]),
                        "ordered_bytes_identical": True,
                    },
                    "output": {"path": str(out_path.relative_to(ROOT)),
                               "sha256": sha256_bytes(out_data), "bytes": len(out_data)},
                    "equivalence": {
                        "path": str(eq_path.relative_to(ROOT)),
                        "sha256": sha256_bytes(eq_data),
                        "bytes": len(eq_data),
                        "producer_constraints_excluded": True,
                        "original_goal_asserted_as_premise": False,
                        "directions": ["original_implies_specialized",
                                       "specialized_implies_original"],
                    },
                    "generator_sha256": generator_hash,
                })

    manifest = {
        "task": "D1P-04",
        "status": "GENERATED_NOT_SOLVED",
        "research_verdict": "UNKNOWN",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                      "sha256": generator_hash},
        "parent_root": str(PARENT_ROOT.relative_to(ROOT)),
        "output_root": str(output_root.relative_to(ROOT)),
        "counts": {"parents": 6, "cells_per_parent": 25,
                   "specialized_queries": len(artifacts),
                   "equivalence_queries": len(artifacts), "controls": len(controls)},
        "witness_mapping": {"outer": OUTER, "streams": STREAMS},
        "controls": controls,
        "artifacts": artifacts,
        "limitations": [
            "serialization and transformation audit only",
            "producer-prefix equality does not prove cone or ACIR soundness",
            "equivalence has not been solved at generation time",
            "no consumer, proof, or D1 verdict follows",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": manifest["status"], **manifest["counts"],
                      "manifest": str(manifest_path)}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    build(args.output_root, args.manifest)


if __name__ == "__main__":
    main()
