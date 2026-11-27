#!/usr/bin/env python3
"""T22-v2 diagnosis helpers that were first run as inline code (saved for reproduction; read-only on the frozen analyzer).

usage:
  t22_diag_aux.py slots      --acir-dir D --scratch S --case WORKDIR [--slots 0,1,2]
      Per-slot frozen v2 specialization: target forcing and target occurrence in the reduced constraints.
      Output format equals results/raw/T22/32_v2_diagnosis/25_m1_slot1_latent.txt and 26_m2_slots.txt.
  t22_diag_aux.py cone-stats --acir-dir D --scratch S --case WORKDIR [--case ...]
      Opcode kinds and range-check widths in the general (all-seed) cone used by nonvacuous/prefix/tail.
  t22_diag_aux.py smt-stats  FILE.smt2 [...]
      Line-count statistics of SMT queries (same counting as `wc -l` and `grep -c PATTERN`).
"""
import argparse, collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_tailspec as T

HERE = os.path.dirname(os.path.abspath(__file__))

def load(acir_dir, scratch, wd):
    pkg = "agg_utxo" if "utxo" in wd else "agg_agg"
    acir = T.Acir(open(os.path.join(acir_dir, wd + ".acir.txt")).read())
    abi = json.load(open(os.path.join(scratch, wd, "noir", "target", pkg + ".json")))["abi"]
    spec = json.load(open(os.path.join(HERE, "t22_specs", f"payy_{pkg}.json")))
    M, streams = T.build(spec, acir, abi)
    return acir, M, streams

def slots(a):
    acir, M, streams = load(a.acir_dir, a.scratch, a.case)
    acts = [next(iter(T.norm_terms(act)))[0] for _, act in streams]
    ks = [int(x) for x in a.slots.split(",")] if a.slots else range(len(M))
    for k in ks:
        fixed = {w: 0 for w in acts}
        orig, _ = T.cone(acir, set(fixed) | T.expr_wits(M[k]))
        red, sel, wits, imp = T._specialize_probe_component(acir, orig, dict(fixed), T.expr_wits(M[k]))
        tw = next(iter(T.expr_wits(M[k])))
        occurs = [i for i in sel if tw in (T.expr_wits(red.ops[i][1]) if red.ops[i][0] in ("assert", "range") else set())]
        print(f"slot={k} target=w{tw} original_ops={len(orig)} reduced_ops={len(sel)} reduced_wits={len(wits)} "
              f"target_forced={imp.get(tw)} target_in_reduced_constraints={len(occurs)}")

def cone_stats(a):
    for wd in a.case:
        acir, M, streams = load(a.acir_dir, a.scratch, wd)
        seeds = set()
        for e in M: seeds |= T.expr_wits(e)
        for words, act in streams:
            for e in words: seeds |= T.expr_wits(e)
            if act: seeds |= T.expr_wits(act)
        sel, _ = T.cone(acir, seeds)
        kinds = collections.Counter(acir.ops[i][0] for i in sel)
        bits = collections.Counter(acir.ops[i][2] for i in sel if acir.ops[i][0] == "range")
        print(wd, dict(kinds), "range widths:", dict(sorted(bits.items())), "encoded bits:", sum(b * c for b, c in bits.items() if b < 254))

def smt_stats(a):
    for f in a.file:
        text = open(f).read(); lines = text.split("\n")[:-1] if text.endswith("\n") else text.split("\n")
        count = lambda pred: sum(1 for ln in lines if pred(ln))
        print(f"{f} lines={text.count(chr(10))} decl={count(lambda l: 'declare-const' in l)} "
              f"rb={count(lambda l: 'declare-const rb' in l)} wdecl={count(lambda l: 'declare-const w' in l)} "
              f"asserts={count(lambda l: l.startswith('(assert'))} ite={count(lambda l: '(ite' in l)}")

ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
p = sub.add_parser("slots"); p.add_argument("--acir-dir", required=True); p.add_argument("--scratch", required=True)
p.add_argument("--case", required=True); p.add_argument("--slots")
p = sub.add_parser("cone-stats"); p.add_argument("--acir-dir", required=True); p.add_argument("--scratch", required=True)
p.add_argument("--case", action="append", required=True)
p = sub.add_parser("smt-stats"); p.add_argument("file", nargs="+")
a = ap.parse_args()
{"slots": slots, "cone-stats": cone_stats, "smt-stats": smt_stats}[a.cmd](a)
