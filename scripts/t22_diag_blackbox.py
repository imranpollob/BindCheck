#!/usr/bin/env python3
"""T22-v2 diagnosis helper: are unmodeled black-box outputs hidden from the probe's `free` check by prune_dangling?

usage: t22_diag_blackbox.py --acir-dir D --scratch S --diagnosis O/20_diagnosis.json
For each case whose v2 probe selected a slot, compare the selected slot's connected component with pruning disabled
against the frozen pruned cone, and list unmodeled black-box outputs present in the former but absent from the latter.
The frozen scripts/t22_tailspec.py is imported, never edited; pruning is disabled only inside this process.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_tailspec as T

ap = argparse.ArgumentParser()
ap.add_argument("--acir-dir", required=True); ap.add_argument("--scratch", required=True); ap.add_argument("--diagnosis", required=True)
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
diag = json.load(open(a.diagnosis))
frozen_prune = T.prune_dangling
for wd, row in diag.items():
    pkg = "agg_utxo" if "utxo" in wd else "agg_agg"
    spec = json.load(open(os.path.join(HERE, "t22_specs", f"payy_{pkg}.json")))
    acir = T.Acir(open(os.path.join(a.acir_dir, wd + ".acir.txt")).read())
    abi = json.load(open(os.path.join(a.scratch, wd, "noir", "target", pkg + ".json")))["abi"]
    M, streams = T.build(spec, acir, abi)
    bb = {w: n for n, o in acir.unmodeled for w in o}
    slots = [row["v2_selected_slot"]] if row.get("v2_selected_slot") is not None else range(len(M))
    for k in slots:
        seeds = set(row["activation_witnesses"]) | T.expr_wits(M[k])
        _, pruned_w = T.cone(acir, seeds)
        T.prune_dangling = lambda acir_, keep: set(range(len(acir_.ops)))
        try: _, full_w = T.cone(acir, seeds)
        finally: T.prune_dangling = frozen_prune
        hidden = sorted(w for w in full_w - pruned_w if w in bb)
        print(json.dumps({"case": wd, "slot": k, "unpruned_component_witnesses": len(full_w), "pruned_cone_witnesses": len(pruned_w),
                          "blackbox_outputs_in_unpruned": sorted({bb[w] for w in full_w if w in bb}),
                          "blackbox_outputs_hidden_by_pruning": len(hidden), "hidden_kinds": sorted({bb[w] for w in hidden})}))
