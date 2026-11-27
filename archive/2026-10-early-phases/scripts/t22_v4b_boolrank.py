#!/usr/bin/env python3
"""One-case T22 experiment: exact Boolean rank for spec-side walk positions."""
import argparse
import hashlib
import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t22_v3_tailspec as T


def bool_let(ff, term):
    ff.n += 1
    name = f"b{ff.n}"
    ff.lines.append(f"(define-fun {name} () Bool {term})")
    return name


def run_one(acir, M, streams, spec, q, outdir, seconds):
    seeds = set()
    for e in M: seeds |= T.expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= T.expr_wits(e)
        if act: seeds |= T.expr_wits(act)
    sel, wits = T.cone(acir, seeds)
    free = sorted(n for n, outs in acir.unmodeled if set(outs) & wits)
    ff = T.FF(seconds * 1000)
    T.encode(ff, acir, sel)
    mv = [ff.expr(e) for e in M]
    N = len(mv)
    D = spec["derivation"]
    if D["mode"] != "walk": raise T.Unsupported("v4b supports walk only")
    # count[0..N] records exactly that many emitted words; count[N+1]
    # records >N. Since there are at most 16 words, no field wrap is possible.
    count = [ff.T] + [ff.Fa] * (N + 1)
    prefix_cases = []
    all_words, act_terms = [], []
    for words, act in streams:
        actv = ff.expr(act) if act else None
        act_terms.append(actv)
        active = ff.NOT(ff.eq(actv, ff.zero)) if act else ff.T
        prev_end, prev_rem = ff.Fa, ff.zero
        current = []
        for e in words:
            s = ff.expr(e)
            current.append(s)
            ln = ff.zero
            for kd, length in sorted(D["records"].items(), reverse=True):
                ln = ff.ite(ff.eq(s, ff.c(int(kd))), ff.c(length), ln)
            lnz, remz = ff.ne(ln, ff.zero), ff.ne(prev_rem, ff.zero)
            emitted = ff.AND(ff.NOT(prev_end), ff.OR(remz, lnz))
            end = ff.OR(prev_end, ff.AND(ff.NOT(remz), ff.NOT(lnz)))
            rem = ff.ite(prev_end, ff.zero, ff.ite(remz, ff.sub(prev_rem, ff.one),
                                                   ff.ite(lnz, ff.sub(ln, ff.one), ff.zero)))
            prev_end, prev_rem = end, rem
            flag = bool_let(ff, ff.AND(active, emitted))
            if q == "prefix":
                for k in range(N):
                    prefix_cases.append(ff.AND(flag, count[k], ff.ne(mv[k], s)))
                prefix_cases.append(ff.AND(flag, ff.OR(count[N], count[N + 1])))
            neg = ff.NOT(flag)
            next_count = [bool_let(ff, ff.AND(count[0], neg))]
            for k in range(1, N + 1):
                next_count.append(bool_let(ff, ff.OR(ff.AND(count[k], neg),
                                                       ff.AND(count[k - 1], flag))))
            next_count.append(bool_let(ff, ff.OR(count[N + 1], ff.AND(count[N], flag))))
            count = next_count
        all_words.append(current)
    if q == "nonvacuous":
        goal = ff.OR(*count[1:N + 1])
    elif q == "prefix":
        goal = ff.OR(*prefix_cases)
    elif q == "tail":
        goal = ff.OR(*[ff.AND(ff.OR(*count[:k + 1]), ff.ne(mv[k], ff.zero)) for k in range(N)])
    else: raise ValueError(q)
    ff.A(goal)
    getv = mv + [a for a in act_terms if a is not None] + [x for words in all_words for x in words]
    smt_path = outdir / f"{q}.smt2"
    status, raw, elapsed = ff.solve(getv, str(smt_path))
    vals = ff.parse_vals(raw) if status == "sat" else []
    info = {"query": q, "status": status, "seconds": round(elapsed, 3),
            "selected_acir_opcodes": len(sel), "selected_witnesses": len(wits),
            "unmodeled_blackboxes": free, "solver_record": ff.solver_record,
            "smt_sha256": hashlib.sha256(smt_path.read_bytes()).hexdigest(),
            "model_values": vals, "model_value_count_expected": len(getv)}
    return info


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
    result = []
    for q in ("nonvacuous", "prefix", "tail"):
        info = run_one(acir, M, streams, spec, q, args.outdir, args.seconds)
        result.append(info)
        (args.outdir / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(q, info["status"], info["seconds"], flush=True)


if __name__ == "__main__": main()
