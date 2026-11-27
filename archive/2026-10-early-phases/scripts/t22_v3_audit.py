#!/usr/bin/env python3
"""Post-run audit, without changing the frozen T22-v3 analyzer or expectations.

Usage: CVC5=/pinned/cvc5 python3 -I scripts/t22_v3_audit.py
Compares source, ABI and bytecode with v2 and re-solves each saved SAT probe.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_v3_tailspec as T

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
resource.setrlimit(resource.RLIMIT_AS, (4194304 * 1024, 4194304 * 1024))
FREEZE = Path("results/raw/T22/33_v3_freeze")
RUN = Path("results/raw/T22/33_v3_primary")
OUT = RUN / "30_audit"
OUT.mkdir(exist_ok=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


report = {"frozen_inputs": [], "old_evidence": {}, "cases": [], "sat_probes": []}
for line in (FREEZE / "00_sha256.txt").read_text().splitlines():
    expected, path = line.split("  ", 1)
    actual = sha(path)
    assert actual == expected, ("frozen input changed", path)
    report["frozen_inputs"].append({"path": path, "sha256": actual})
old = json.loads((FREEZE / "02_preserved_evidence.json").read_text())
for path, expected in old.items():
    assert sha(path) == expected, ("old evidence changed", path)
report["old_evidence"] = {"files_checked": len(old), "unchanged": True}
third_party_status = subprocess.check_output(
    ["git", "-C", "tools/cases/payy-history", "status", "--short"], text=True)
assert third_party_status in (RUN / "10_run_manifest.txt").read_text()
report["third_party_checkout_status_unchanged"] = True
rows = json.loads((RUN / "20_payy_eval.json").read_text())
assert len(rows) == 9
old_rows = {r["case"]: r for r in json.loads(
    Path("results/raw/T22/31_v2_primary/20_payy_eval.json").read_text())}
assert set(old_rows) == {r["case"] for r in rows}
for row in rows:
    assert row["expected"] == old_rows[row["case"]]["expected"]
    assert row["t21"] == old_rows[row["case"]]["t21"]
    slug = re.sub(r"[^a-z0-9]+", "_", row["case"].lower())
    wd = "work_" + slug
    pkg = "agg_utxo" if "utxo" in slug else "agg_agg"
    oldtree = Path("build/T22/scratch-31_v2_primary") / wd / "noir"
    newtree = Path("build/T22/scratch-33_v3_primary") / wd / "noir"
    before = json.loads((oldtree / "target" / (pkg + ".json")).read_text())
    after = json.loads((newtree / "target" / (pkg + ".json")).read_text())
    assert before["abi"] == after["abi"], wd
    assert before["bytecode"] == after["bytecode"], wd
    assert (oldtree / pkg / "src/main.nr").read_bytes() == (newtree / pkg / "src/main.nr").read_bytes(), wd
    acirpath = RUN / ("20_payy_eval.json.artifacts/" + slug + ".compile.stdout")
    diagpath = Path("results/raw/T22/32_v2_diagnosis/acir") / (wd + ".acir.txt")
    same_acir = acirpath.read_bytes() == diagpath.read_bytes()
    assert same_acir, wd
    comparisons = {}
    for q in ("nonvacuous", "prefix", "tail"):
        new_query = RUN / ("20_payy_eval.json.smt/" + slug) / (q + ".smt2")
        old_query = Path("results/raw/T22/31_v2_primary/20_payy_eval.json.smt") / slug / (q + ".smt2")
        if new_query.exists() and old_query.exists():
            comparisons[q] = new_query.read_bytes() == old_query.read_bytes()
            assert comparisons[q], (wd, q, "general query changed")
    report["cases"].append({"case": row["case"], "verdict": row["t22"],
        "same_expectation_and_t21_as_v2": True,
        "same_source_abi_bytecode_acir_as_v2": True, "acir_sha256": sha(acirpath),
        "general_queries_identical_where_both_issued": comparisons,
        "bytecode_sha256": hashlib.sha256(after["bytecode"].encode()).hexdigest()})
    details = row["queries"].get("probe", {}).get("details", {})
    for slot in details.get("slots", []):
        if slot["solver"] != "sat": continue
        k = slot["message_index"]
        spec = json.loads((Path("scripts/t22_specs") / ("payy_" + pkg + ".json")).read_text())
        a = T.Acir(acirpath.read_text())
        messages, streams = T.build(spec, a, after["abi"])
        fixed = {next(iter(T.norm_terms(act)))[0]: 0 for _, act in streams}
        original, original_w = T.cone(a, set(fixed) | T.expr_wits(messages[k]))
        reduced, _, _, implied = T._specialize_probe_component(a, original, fixed, T.expr_wits(messages[k]))
        goal = T._sub_constants(messages[k], implied)
        assert not (T.expr_wits(goal) & set(implied)), wd
        # These primary SAT slots must not depend on the goal-implied bug.
        assert not (T.expr_wits(messages[k]) & set(implied)), wd
        selected, witnesses = T.cone(reduced, T.expr_wits(goal))
        assert len(selected) == slot["opcodes_in_cone"], wd
        assert len(witnesses) == slot["witnesses"], wd
        assert not [n for n, outs in a.unmodeled if set(outs) & (witnesses | original_w)], wd
        ff = T.FF(60000)
        T.encode(ff, reduced, selected)
        mv = ff.expr(goal)
        ff.A(ff.ne(mv, ff.zero))
        audit_smt = OUT / (slug + f"_slot_{k}.smt2")
        st, output, seconds = ff.solve([mv], str(audit_smt))
        saved_smt = RUN / ("20_payy_eval.json.smt/" + slug) / f"probe_slot_{k}.smt2"
        assert audit_smt.read_bytes() == saved_smt.read_bytes(), wd
        values = ff.parse_vals(output)
        assert st == "sat" and values and values[0] != 0, wd
        report["sat_probes"].append({"case": row["case"], "slot": k,
            "no_original_or_substituted_goal_witness_in_implied": True,
            "target_component_encoded": True, "same_smt_bytes": True,
            "opcodes": len(selected), "witnesses": len(witnesses), "solver": st,
            "message_value": values[0], "seconds": seconds,
            "smt_sha256": sha(saved_smt), "solver_exit_status": ff.solver_record["exit_status"]})
report["status"] = "all audit assertions passed"
(OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "old_files": len(old), "cases": len(rows),
                  "sat_probes_rechecked": len(report["sat_probes"])}, indent=2))
