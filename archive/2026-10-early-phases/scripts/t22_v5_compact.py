#!/usr/bin/env python3
"""T22-v5 exploratory N=8 walk encoding over the unchanged printed ACIR.

The compact walk is checked exhaustively over all relevant word categories by
--self-check. This file changes only the encoding of the analyst specification,
not the specification or circuit constraints.
"""
import argparse
import hashlib
import itertools
import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t22_v3_tailspec as T


def compact_emits(words):
    first = words[0]
    if first not in (2, 3, 4): return [False] * 8
    n = 4 if first == 2 else 5
    if words[n] in (2, 3, 4): n = 8
    return [j < n for j in range(8)]


def original_emits(words):
    ended, rem, result = False, 0, []
    for word in words:
        ln = {2: 4, 3: 5, 4: 5}.get(word, 0)
        emitted = not ended and (rem != 0 or ln != 0)
        ended = ended or (rem == 0 and ln == 0)
        rem = 0 if ended else rem - 1 if rem else ln - 1 if ln else 0
        result.append(emitted)
    return result


def self_check():
    # Only positions 0, 4 and 5 can be record starts. Enumerate all four
    # equivalence classes (2, 3, 4, other) at these positions and all 8
    # positions as a stronger check against the reference transition code.
    count = 0
    for words in itertools.product((0, 2, 3, 4), repeat=8):
        assert compact_emits(words) == original_emits(words), words
        count += 1
    return count


def bool_let(ff, term):
    ff.n += 1
    name = f"b{ff.n}"
    ff.lines.append(f"(define-fun {name} () Bool {term})")
    return name


def run_one(acir, M, streams, query, outdir, seconds, encode_acir):
    seeds = set()
    for e in M: seeds |= T.expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= T.expr_wits(e)
        if act: seeds |= T.expr_wits(act)
    sel, wits = T.cone(acir, seeds)
    free = sorted(n for n, outs in acir.unmodeled if set(outs) & wits)
    ff = T.FF(seconds * 1000)
    if encode_acir: T.encode(ff, acir, sel)
    mv = [ff.expr(e) for e in M]
    count = [ff.T] + [ff.Fa] * 16
    mismatch = []
    for words, act in streams:
        assert len(words) == 8 and act is not None
        ss = [ff.expr(e) for e in words]
        active = ff.ne(ff.expr(act), ff.zero)
        is2 = ff.eq(ss[0], ff.c(2))
        is34 = ff.OR(ff.eq(ss[0], ff.c(3)), ff.eq(ss[0], ff.c(4)))
        any4 = ff.OR(*[ff.eq(ss[4], ff.c(k)) for k in (2, 3, 4)])
        any5 = ff.OR(*[ff.eq(ss[5], ff.c(k)) for k in (2, 3, 4)])
        first = bool_let(ff, ff.AND(active, ff.OR(is2, is34)))
        fourth = bool_let(ff, ff.AND(active, ff.OR(is34, ff.AND(is2, any4))))
        rest = bool_let(ff, ff.AND(active, ff.OR(ff.AND(is2, any4), ff.AND(is34, any5))))
        for j, s in enumerate(ss):
            flag = first if j < 4 else fourth if j == 4 else rest
            if query == "prefix":
                for k in range(8):
                    mismatch.append(ff.AND(flag, count[k], ff.ne(mv[k], s)))
                mismatch.append(ff.AND(flag, ff.OR(*count[8:])))
            nxt = [bool_let(ff, ff.AND(count[0], ff.NOT(flag)))]
            for k in range(1, 17):
                nxt.append(bool_let(ff, ff.OR(ff.AND(count[k], ff.NOT(flag)),
                                                ff.AND(count[k-1], flag))))
            count = nxt
    if query == "nonvacuous": goal = ff.OR(*count[1:9])
    elif query == "prefix": goal = ff.OR(*mismatch)
    elif query == "tail":
        goal = ff.OR(*[ff.AND(ff.OR(*count[:k+1]), ff.ne(mv[k], ff.zero)) for k in range(8)])
    else: raise ValueError(query)
    ff.A(goal)
    smt = outdir / f"{query}.smt2"
    status, raw, elapsed = ff.solve(mv, str(smt))
    return {"query": query, "status": status, "seconds": round(elapsed, 3),
            "acir_encoded": encode_acir, "selected_acir_opcodes": len(sel),
            "selected_witnesses": len(wits), "unmodeled_blackboxes": free,
            "solver_record": ff.solver_record,
            "smt_sha256": hashlib.sha256(smt.read_bytes()).hexdigest(),
            "message_values": ff.parse_vals(raw) if status == "sat" else []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acir", type=Path, required=True)
    ap.add_argument("--abi", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--queries", nargs="+", choices=("nonvacuous", "prefix", "tail"),
                    default=("nonvacuous", "prefix", "tail"))
    ap.add_argument("--no-acir", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.spec.read_text())
    if len(spec["streams"]) != 2 or spec["derivation"] != {"mode": "walk", "records": {"2": 4, "3": 5, "4": 5}}:
        raise ValueError("unexpected semantic specification")
    if args.self_check:
        n = self_check()
        (args.outdir / "self_check.json").write_text(json.dumps({"category_vectors": n, "status": "pass"}, indent=2) + "\n")
        print(f"self-check pass: {n} category vectors", flush=True)
    acir = T.Acir(args.acir.read_text())
    abi = json.loads(args.abi.read_text())
    if "abi" in abi: abi = abi["abi"]
    M, streams = T.build(spec, acir, abi)
    if len(M) != 8: raise ValueError("expected N=8")
    for query in args.queries:
        result = run_one(acir, M, streams, query, args.outdir, args.seconds, not args.no_acir)
        (args.outdir / f"{query}.json").write_text(json.dumps(result, indent=2) + "\n")
        print(query, result["status"], result["seconds"], flush=True)


if __name__ == "__main__": main()
