#!/usr/bin/env python3
"""Independently audit a saved T22-v5 ACIR-bearing SMT reduction."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t22_v3_tailspec as T
import t22_v5_reduce as R


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--primary", type=Path, required=True)
    ap.add_argument("--reduced", type=Path, required=True)
    ap.add_argument("--acir", type=Path, required=True)
    ap.add_argument("--abi", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    source = args.source.read_text()
    primary = json.loads(args.primary.read_text())
    record = json.loads(args.reduced.with_suffix(args.reduced.suffix + ".json").read_text())
    indices = record["retained_acir_assertion_indices_0_based"]
    rebuilt, expected = R.render(source, indices)
    assert rebuilt == args.reduced.read_text(), "reduced SMT differs from byte-preserved rebuild"
    assert primary["smt_sha256"] == sha(source.encode()), "primary SMT hash mismatch"
    for key in ("source_sha256", "reduced_sha256", "source_assertions",
                "retained_acir_assertion_indices_0_based", "retained_acir_assertions",
                "shared_goal_witnesses_through_definitions", "reduced_bytes",
                "retained_definitions", "retained_declarations"):
        assert expected[key] == record[key], f"metadata mismatch: {key}"
    assert indices == list(range(len(indices))) and indices, "expected nonempty ACIR prefix"
    assert any(record["shared_goal_witnesses_through_definitions"].values()), "blocker disconnected from goal"

    acir = T.Acir(args.acir.read_text())
    spec = json.loads(args.spec.read_text())
    abi = json.loads(args.abi.read_text())
    if "abi" in abi: abi = abi["abi"]
    M, streams = T.build(spec, acir, abi)
    seeds = set()
    for e in M: seeds |= T.expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= T.expr_wits(e)
        if act: seeds |= T.expr_wits(act)
    selected, witnesses = T.cone(acir, seeds)
    n_asserts = 0
    last_opcode = None
    for oi in selected:
        op = acir.ops[oi]
        kind = op[0]
        contribution = (1 if kind == "assert" else op[2] + 1 if kind == "range" else
                        2 if kind == "read" else 1 if kind == "write" else 0)
        if n_asserts <= indices[-1] < n_asserts + contribution:
            last_opcode = oi
        n_asserts += contribution
    assert last_opcode is not None
    assert n_asserts == expected["source_assertions"] - 1, "ACIR assertion count mismatch"
    result = {
        "status": "pass", "source_sha256": sha(source.encode()),
        "reduced_sha256": sha(rebuilt.encode()),
        "retained_acir_assertions": len(indices),
        "selected_acir_opcodes": len(selected), "selected_witnesses": len(witnesses),
        "total_acir_smt_assertions": n_asserts,
        "last_retained_acir_opcode_0_based": last_opcode,
        "goal_connected_assertions": sum(bool(v) for v in
                                          record["shared_goal_witnesses_through_definitions"].values()),
        "unmodeled_blackboxes_in_original_cone": sorted(n for n, outs in acir.unmodeled
                                                           if set(outs) & witnesses),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
