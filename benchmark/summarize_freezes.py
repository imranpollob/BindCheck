#!/usr/bin/env python3
"""Add exact per-pattern freeze and input-ablation data to E1 metrics."""
from __future__ import annotations

import collections
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark"
RAW = ROOT / "results/raw/bench"
OUT = ROOT / "reports/bench"
PATTERNS = ("P1", "P2", "P3", "P4", "P5")


def load(path):
    try: return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return None


def verdict(record, pattern):
    if record is None: return "MISSING"
    return record.get("patterns", {}).get(pattern, {}).get("verdict", "MISSING")


def main():
    manifest = load(BENCH / "manifest.json")
    cases = [load(BENCH / x["case"]) for x in manifest["cases"]]
    cases = [x for x in cases if x["origin"] != "public-report"]
    runs = {x["id"]: x for x in load(RAW / "e1-freeze2-20261109/runs.json")["records"]}
    withheld_suffixes=collections.Counter()
    for run in runs.values():
        for item in run["ablation_input"]["withheld"]:
            withheld_suffixes[pathlib.Path(item["path"]).suffix]+=1
    matrix = list(csv.DictReader((OUT / "matrix.csv").open()))
    matrix_index = {(r["tool"], r["case_id"]): r for r in matrix}
    rows = []
    transitions = {"f1_to_f2": collections.defaultdict(collections.Counter),
                   "f2_to_no_circuit": collections.defaultdict(collections.Counter)}
    expected = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    all_unchanged = True
    for case in cases:
        cid = case["id"]
        if case["origin"] == "synthetic":
            f1_path = RAW / "e1-synthetic-bindcheck-freeze1-20261109/cases" / cid / "result.json"
        else:
            f1_path = RAW / "e1-local-20261109" / cid / "selected/bindcheck-command/stdout"
        f1 = load(f1_path)
        f2_path = pathlib.Path(runs[cid]["modes"]["full"]["result"])
        no_path = pathlib.Path(runs[cid]["modes"]["no-circuit"]["result"])
        f2, no = load(f2_path), load(no_path)
        for pattern in PATTERNS:
            v1,v2,v0 = verdict(f1,pattern),verdict(f2,pattern),verdict(no,pattern)
            rows.append({"case_id":cid,"origin":case["origin"],
                         "expected_pattern":case["expected_pattern"],"pattern":pattern,
                         "freeze1":v1,"freeze2":v2,"no_circuit":v0,
                         "freeze1_source":str(f1_path),"freeze2_source":str(f2_path),
                         "no_circuit_source":str(no_path)})
            transitions["f1_to_f2"][pattern][f"{v1}->{v2}"] += 1
            transitions["f2_to_no_circuit"][pattern][f"{v2}->{v0}"] += 1
        p = case["expected_pattern"]
        for tool in ("BindCheck-F1","BindCheck-F2","BindCheck-F2-no-circuit"):
            expected[p][tool][matrix_index[tool,cid]["outcome"]] += 1
        if matrix_index["BindCheck-F1",cid]["outcome"] != matrix_index["BindCheck-F2",cid]["outcome"]:
            all_unchanged = False
    with (OUT / "freeze-patterns.csv").open("w",newline="") as file:
        writer = csv.DictWriter(file,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(rows)
    metrics = load(OUT / "metrics.json")
    metrics["freeze_comparison"] = {
        "case_count":len(cases),"pattern_rows":len(rows),
        "withheld_suffixes":dict(withheld_suffixes),
        "scratch_removed_count":sum(bool(run.get("scratch_removed")) for run in runs.values()),
        "full_run_status":dict(collections.Counter(run["modes"]["full"]["run_status"] for run in runs.values())),
        "no_circuit_run_status":dict(collections.Counter(run["modes"]["no-circuit"]["run_status"] for run in runs.values())),
        "scored_f1_f2_identical":all_unchanged,
        "transitions":{mode:{p:dict(c) for p,c in by.items()} for mode,by in transitions.items()},
        "expected_pattern_outcomes":{p:{tool:dict(c) for tool,c in by.items()}
                                     for p,by in expected.items()},
        "adv_v14_v15":{cid:{p:{"freeze1":next(r["freeze1"] for r in rows if r["case_id"]==cid and r["pattern"]==p),
                                "freeze2":next(r["freeze2"] for r in rows if r["case_id"]==cid and r["pattern"]==p),
                                "no_circuit":next(r["no_circuit"] for r in rows if r["case_id"]==cid and r["pattern"]==p)}
                           for p in PATTERNS} for cid in ("ADV-V14","ADV-V15")},
        "input_receipts":str(RAW / "e1-freeze2-20261109/runs.json"),
        "per_pattern_file":"reports/bench/freeze-patterns.csv"}
    (OUT / "metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n")


if __name__ == "__main__":main()
