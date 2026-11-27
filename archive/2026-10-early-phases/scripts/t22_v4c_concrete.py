#!/usr/bin/env python3
"""Exact ACIR specialization for one constructive non-vacuity branch."""
import argparse
import hashlib
import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t22_v3_tailspec as T


def scalar_witness(expr):
    n = T.norm_terms(expr)
    if len(n) != 1: raise ValueError(f"not a scalar witness: {expr}")
    (key, coef), = n.items()
    if len(key) != 1 or coef != 1: raise ValueError(f"not a unit witness: {expr}")
    return key[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acir", type=Path, required=True)
    ap.add_argument("--abi", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=300)
    args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    args.outdir.mkdir(parents=True, exist_ok=True)
    acir = T.Acir(args.acir.read_text())
    spec = json.loads(args.spec.read_text())
    abi = json.loads(args.abi.read_text())
    if "abi" in abi: abi = abi["abi"]
    M, streams = T.build(spec, acir, abi)
    if len(streams) != 2 or any(len(words) != 8 for words, _ in streams):
        raise ValueError("expected two N=8 streams")
    fixed = {}
    pattern = [2] + [0] * 7
    for t, (words, act) in enumerate(streams):
        fixed[scalar_witness(act)] = 1 if t == 0 else 0
        for e, value in zip(words, pattern): fixed[scalar_witness(e)] = value
    seeds = set()
    for e in M: seeds |= T.expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= T.expr_wits(e)
        seeds |= T.expr_wits(act)
    selected, _ = T.cone(acir, seeds)
    reduced, _, _, implied = T._specialize_probe_component(acir, selected, fixed, seeds)
    # All surviving selected constraints are retained, including disconnected
    # components split by substitution; only exact dangling definitions were
    # dropped by the v3 reduction.
    ff = T.FF(args.seconds * 1000)
    T.encode(ff, reduced, list(range(len(reduced.ops))))
    mvals = [ff.expr(T._sub_constants(e, implied)) for e in M]
    smt = args.outdir / "concrete_nonvacuous.smt2"
    status, out, elapsed = ff.solve(mvals, str(smt))
    details = {"status": status, "seconds": round(elapsed, 3),
               "fixed_witness_values": {str(k): v for k, v in sorted(fixed.items())},
               "implied_constants": len(implied), "original_cone_opcodes": len(selected),
               "surviving_opcodes": len(reduced.ops), "messages": ff.parse_vals(out) if status == "sat" else [],
               "smt_sha256": hashlib.sha256(smt.read_bytes()).hexdigest(),
               "solver_record": ff.solver_record,
               "assumption": "components outside original cone are satisfiable; recursive proofs not checked"}
    (args.outdir / "concrete_nonvacuous.json").write_text(json.dumps(details, indent=2) + "\n")
    print(json.dumps({k: details[k] for k in ("status", "seconds", "implied_constants", "original_cone_opcodes", "surviving_opcodes", "messages", "smt_sha256")}, indent=2))


if __name__ == "__main__": main()
