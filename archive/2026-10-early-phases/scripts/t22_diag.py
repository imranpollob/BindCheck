#!/usr/bin/env python3
"""T22-v2 failure diagnosis (read-only instrumentation of the frozen scripts/t22_tailspec.py; it is imported, never edited).

usage: t22_diag.py --acir-dir D --scratch S --out O [--cvc5 PATH] [--cert-timeout 120]
  D  directory of `nargo compile --print-acir` outputs named <workdir>.acir.txt
  S  preserved scratch tree whose work_*/noir/target/<pkg>.json supplies the ABI
  O  new ignored output directory (refuses to overwrite files)

For every case it (1) reproduces the v2 empty-prefix per-slot specialization and the slot the probe would select,
(2) re-runs constant discovery with provenance, checking that the traced constants equal the frozen ones,
(3) builds subset certificates from the ORIGINAL (unspecialized) ACIR assertions in the provenance of a forced
constant or of a contradiction, and solves them with cvc5. An UNSAT subset implies the full ACIR relation is UNSAT
under the same premises; SAT controls show the subset is not trivially inconsistent.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_tailspec as T

P = T.P
CASES = [  # workdir, package, spec (mirrors scripts/t22_eval.py CASES; names normalized the same way)
    ("work_a_agg_agg_earlier_", "agg_agg", "payy_agg_agg.json"),
    ("work_b_agg_agg_check_added_", "agg_agg", "payy_agg_agg.json"),
    ("work_agg_utxo_a_b_", "agg_utxo", "payy_agg_utxo.json"),
    ("work_m1_b_guard_instead_of_", "agg_agg", "payy_agg_agg.json"),
    ("work_m2_b_loop_skips_last_slot", "agg_agg", "payy_agg_agg.json"),
    ("work_m3_b_helper_call_deleted", "agg_agg", "payy_agg_agg.json"),
    ("work_m4_b_different_idiom_flag_", "agg_agg", "payy_agg_agg.json"),
    ("work_m5_utxo_tail_loop_deleted", "agg_utxo", "payy_agg_utxo.json"),
    ("work_m6_utxo_else_branch_idiom", "agg_utxo", "payy_agg_utxo.json"),
]

class LinedAcir(T.Acir):
    """T.Acir plus the source line of every appended op (for provenance only)."""
    def __init__(self, text):
        self.lines = []
        super().__init__(text)
    def _op(self, line):
        n = len(self.ops)
        super()._op(line)
        if len(self.ops) > n: self.lines.append(line)

def op_wits(op):
    k = op[0]
    if k in ("assert", "range"): return T.expr_wits(op[1])
    if k == "init": return set().union(*[T.expr_wits(e) for e in op[2]]) if op[2] else set()
    if k in ("read", "write"): return T.expr_wits(op[2]) | T.expr_wits(op[3])
    return set()

# ---------------------------------------------------------------- traced mirror of T._discover_constants
def traced_discover(ops, idx, initial, initial_deps, cap=256):
    """Same control flow as T._discover_constants; additionally returns, for every constant, the set of original op
    indices whose equalities imply it, and the provenance of a contradiction instead of raising."""
    fixed, defs, fdeps, ddeps = dict(initial), {}, dict(initial_deps), {}
    def add(a, b):
        out = dict(a)
        for key, val in b.items(): out[key] = (out.get(key, 0) + val) % P
        return {key: val for key, val in out.items() if val}
    def mul(a, b):
        if len(a) * len(b) > cap * 4: raise OverflowError
        out = {}
        for ka, va in a.items():
            for kb, vb in b.items():
                key = tuple(sorted(ka + kb)); out[key] = (out.get(key, 0) + va * vb) % P
                if len(out) > cap: raise OverflowError
        return {key: val for key, val in out.items() if val}
    def reduce_fixed(poly):
        out, dep = {}, set()
        for key, cf in poly.items():
            rest = []
            for w in key:
                if w in fixed: cf = (cf * fixed[w]) % P; dep |= fdeps[w]
                else: rest.append(w)
            key2 = tuple(rest); out[key2] = (out.get(key2, 0) + cf) % P
        return {key: val for key, val in out.items() if val}, dep
    def rewrite(e):
        out, dep = {}, set()
        for cf, ws in e:
            term = {(): cf % P}
            for w in ws:
                if w in fixed: atom = {(): fixed[w]}; dep |= fdeps[w]
                else:
                    atom, d2 = reduce_fixed(defs.get(w, {(w,): 1})); dep |= d2 | ddeps.get(w, set())
                term = mul(term, atom)
            out = add(out, term)
            if len(out) > cap: raise OverflowError
        return out, dep
    for _ in range(3):
        for pos, op in enumerate(ops):
            if op[0] != "assert": continue
            try: poly, dep = rewrite(op[1])
            except OverflowError: continue
            if not poly: continue
            if set(poly) == {()}:
                return fixed, fdeps, {"op": idx[pos], "value": poly[()], "deps": sorted(dep | {idx[pos]})}
            all_wits = {w for monomial in poly for w in monomial}
            candidates = []
            for monomial, cf in poly.items():
                if len(monomial) != 1: continue
                w = monomial[0]
                if any(w in other for other in poly if other != monomial): continue
                if all(w > other for other in all_wits if other != w): candidates.append((w, cf))
            if not candidates: continue
            w, cf = max(candidates)
            if w in defs: continue
            rest = dict(poly); del rest[(w,)]
            inv = pow(cf, -1, P)
            definition = {key: (-val * inv) % P for key, val in rest.items()}
            if len(definition) > cap: continue
            defs[w] = definition; ddeps[w] = dep | {idx[pos]}
            if set(definition) <= {()}:
                value = definition.get((), 0)
                if w in fixed and fixed[w] != value:
                    return fixed, fdeps, {"op": idx[pos], "conflict_witness": w, "deps": sorted(ddeps[w] | fdeps[w])}
                fixed[w] = value; fdeps[w] = ddeps[w]; defs.pop(w, None)
    return fixed, fdeps, None

def traced_specialize(acir, selected, fixed):
    """Mirror of the constant-discovery loop at the top of T._specialize_probe_component."""
    source = [acir.ops[i] for i in selected]
    fdeps = {w: set() for w in fixed}
    for _ in range(3):
        expanded, edeps, contra = traced_discover(source, selected, fixed, fdeps)
        if contra: return expanded, edeps, contra
        if len(expanded) == len(fixed): break
        fixed, fdeps = expanded, edeps
    return fixed, fdeps, None

# ---------------------------------------------------------------- helpers
def components(ops, live):
    """union-find over live ops (witnesses + memory blocks), as in T.cone; returns {op index: root}"""
    parent = {}
    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    opw = {}
    for i in live:
        op = ops[i]; ws = set(op_wits(op))
        if op[0] in ("init", "read", "write"): ws.add(("blk", op[1]))
        ws = list(ws); opw[i] = ws
        for a in ws: f(a)
        for a in ws[1:]: parent[f(a)] = f(ws[0])
    return opw, f

def range_bits(ops, idxs):
    return sum(ops[i][2] for i in idxs if ops[i][0] == "range" and ops[i][2] < 254)

def subset_query(acir, op_idx, premises_zero, msg_expr, timeout_s, path, msg_nonzero=True, extra=None):
    sub = object.__new__(T.Acir); sub.ops = [acir.ops[i] for i in sorted(op_idx)]; sub.unmodeled = []
    ff = T.FF(timeout_s * 1000)
    T.encode(ff, sub, list(range(len(sub.ops))))
    for w in sorted(premises_zero): ff.A(ff.eq(ff.var(w), ff.zero))
    getv = []
    if msg_expr is not None:
        mv = ff.expr(msg_expr); getv.append(mv)
        if msg_nonzero: ff.A(ff.ne(mv, ff.zero))
    if extra: extra(ff)
    if not getv: getv = [ff.one]
    st, out, dt = ff.solve(getv, path)
    return {"solver": st, "seconds": round(dt, 2), "assertions": len(sub.ops), "file": os.path.relpath(path, OUT)}

def nonoverwrite(path):
    if os.path.exists(path): raise SystemExit(f"refusing to overwrite {path}")
    return path

# ---------------------------------------------------------------- main
ap = argparse.ArgumentParser()
ap.add_argument("--acir-dir", required=True); ap.add_argument("--scratch", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--cvc5", default=os.environ.get("CVC5", "cvc5")); ap.add_argument("--cert-timeout", type=int, default=120)
a = ap.parse_args()
OUT = a.out; T.CVC5 = a.cvc5
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(OUT, "smt"), exist_ok=True)
report = {}
for wd, pkg, specf in CASES:
    t0 = time.time()
    acir = LinedAcir(open(os.path.join(a.acir_dir, wd + ".acir.txt")).read())
    abi = json.load(open(os.path.join(a.scratch, wd, "noir", "target", pkg + ".json")))["abi"]
    spec = json.load(open(os.path.join(HERE, "t22_specs", specf)))
    M, streams = T.build(spec, acir, abi)
    acts = [next(iter(T.norm_terms(act)))[0] for _, act in streams]
    msg_w = [sorted(T.expr_wits(e)) for e in M]
    row = {"ops": len(acir.ops), "activation_witnesses": acts, "message_witnesses": msg_w,
           "unmodeled_blackboxes": sorted({n for n, _ in acir.unmodeled}), "slots": []}
    cdir = os.path.join(OUT, "smt", wd); os.makedirs(cdir, exist_ok=True)
    traced = {}
    for k, message in enumerate(M):
        fixed0 = {w: 0 for w in acts}
        original, _ = T.cone(acir, set(fixed0) | T.expr_wits(message))
        slot = {"slot": k, "original_cone_ops": len(original)}
        tf, tdeps, contra = traced_specialize(acir, original, dict(fixed0))
        try:
            reduced, sel, wits, implied = T._specialize_probe_component(acir, original, dict(fixed0), T.expr_wits(message))
            slot.update({"reduced_ops": len(sel), "reduced_witnesses": len(wits), "implied_constants": len(implied),
                         "reduced_range_bits": range_bits(reduced.ops, sel)})
            slot["traced_constants_match_frozen"] = (tf == implied) and contra is None
            mf = {w: implied[w] for w in T.expr_wits(message) if w in implied}
            slot["message_witness_forced"] = {f"w{w}": v for w, v in mf.items()}
            # Re-componentize the reduced query: how much of it is connected to the target slot?
            opw, f = components(reduced.ops, sel)
            roots = {f(w) for w in T.expr_wits(message) if any(w in opw[i] for i in sel)}
            rel = [i for i in sel if opw[i] and f(opw[i][0]) in roots]
            slot.update({"target_component_ops": len(rel), "target_component_range_bits": range_bits(reduced.ops, rel),
                         "disconnected_ops": len(sel) - len(rel)})
            traced[k] = (reduced, sel, rel, tf, tdeps)
        except T.Unsupported as ex:
            slot["unsupported"] = str(ex)
            slot["traced_contradiction_found"] = contra is not None
            if contra:
                slot["contradiction"] = {"op": contra["op"], "acir": acir.lines[contra["op"]][:200],
                                         "support_size": len(contra["deps"])}
                traced[k] = ("contra", contra)
        row["slots"].append(slot)
    ok = [s for s in row["slots"] if "reduced_ops" in s]
    if ok and len(ok) == len(M):
        best = min(ok, key=lambda s: (s["reduced_ops"], s["reduced_witnesses"], s["slot"]))
        row["v2_selected_slot"] = best["slot"]
        row["v2_selected"] = {"ops": best["reduced_ops"], "witnesses": best["reduced_witnesses"]}
    else:
        row["v2_selected_slot"] = None
        first = next((s for s in row["slots"] if "unsupported" in s), None)
        row["v2_probe_aborts_at_slot"] = first["slot"] if first else None

    certs = {}
    # (A) forced message constants: certify with original assertions in the provenance.
    for k, tr in traced.items():
        if tr[0] == "contra": continue
        reduced, sel, rel, tf, tdeps = tr
        forced = [w for w in T.expr_wits(M[k]) if w in tf]
        if not forced: continue
        deps = set().union(*[tdeps[w] for w in forced])
        lines = [acir.lines[i][:200] for i in sorted(deps)]
        c = {"support_ops": len(deps), "support_acir": lines if len(lines) <= 80 else lines[:80] + ["..."]}
        c["premise_and_nonzero"] = subset_query(acir, deps, acts, M[k], a.cert_timeout,
                                                nonoverwrite(os.path.join(cdir, f"cert_slot{k}_unsat_expected.smt2")))
        if k == 0:
            c["control_premise_only"] = subset_query(acir, deps, acts, M[k], a.cert_timeout,
                                                     nonoverwrite(os.path.join(cdir, f"cert_slot{k}_control_premise_only.smt2")), msg_nonzero=False)
            c["control_nonzero_only"] = subset_query(acir, deps, [], M[k], a.cert_timeout,
                                                     nonoverwrite(os.path.join(cdir, f"cert_slot{k}_control_no_premise.smt2")))
        certs[f"slot{k}"] = c
    # (B) contradictions: certify that the empty-prefix premise is itself infeasible.
    for k, tr in traced.items():
        if tr[0] != "contra": continue
        contra = tr[1]; deps = set(contra["deps"])
        lines = [acir.lines[i][:200] for i in sorted(deps)]
        c = {"support_ops": len(deps), "support_acir": lines if len(lines) <= 80 else lines[:80] + ["..."]}
        c["all_activations_zero"] = subset_query(acir, deps, acts, None, a.cert_timeout,
                                                 nonoverwrite(os.path.join(cdir, f"contra_slot{k}_unsat_expected.smt2")))
        c["control_no_premise"] = subset_query(acir, deps, [], None, a.cert_timeout,
                                               nonoverwrite(os.path.join(cdir, f"contra_slot{k}_control_no_premise.smt2")))
        for j, w in enumerate(acts):
            c[f"only_stream{j}_inactive"] = subset_query(acir, deps, [w], None, a.cert_timeout,
                                                         nonoverwrite(os.path.join(cdir, f"contra_slot{k}_only_stream{j}.smt2")))
        certs[f"contradiction_slot{k}"] = c
        break   # the frozen probe aborts at its first contradiction; one certificate per case suffices
    # (C) timeout class: emit the selected slot's target-component-only query for an offline solver-option comparison.
    sk = row.get("v2_selected_slot")
    if sk is not None and row["v2_selected"]["ops"] > 0:
        reduced, sel, rel, tf, tdeps = traced[sk]
        ff = T.FF(60 * 1000); T.encode(ff, reduced, rel)
        mv = ff.expr(M[sk]); ff.A(ff.ne(mv, ff.zero))
        p = nonoverwrite(os.path.join(cdir, f"probe_slot{sk}_target_component_only.smt2"))
        st, out, dt = ff.solve([mv], p)
        certs["target_component_only_60s"] = {"slot": sk, "ops": len(rel), "solver": st, "seconds": round(dt, 2),
                                              "file": os.path.relpath(p, OUT)}
    row["certificates"] = certs
    # (D) prune_dangling exposure of unmodeled black-box outputs (soundness hazard for SAT results).
    seeds = set(acts) | set().union(*[T.expr_wits(e) for e in M])
    live = T.prune_dangling(acir, seeds)
    bb_out = {w for _, o in acir.unmodeled for w in o}
    live_w = set().union(*[op_wits(acir.ops[i]) for i in live])
    pruned_bb = sorted(w for i in set(range(len(acir.ops))) - live for w in op_wits(acir.ops[i]) if w in bb_out and w not in live_w)
    row["blackbox_outputs_only_in_pruned_asserts"] = len(pruned_bb)
    row["seconds"] = round(time.time() - t0, 1)
    report[wd] = row
    print(f"{wd:34} sel={row.get('v2_selected')} slots_forced={[s['slot'] for s in row['slots'] if s.get('message_witness_forced')]}"
          f" unsupported={[s['slot'] for s in row['slots'] if 'unsupported' in s]} "
          + " ".join(f"{n}:{ {q: v['solver'] for q, v in c.items() if isinstance(v, dict) and 'solver' in v} if 'solver' not in c else c['solver']}"
                     for n, c in certs.items()), flush=True)
json.dump(report, open(nonoverwrite(os.path.join(OUT, "20_diagnosis.json")), "w"), indent=1)
