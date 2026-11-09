#!/usr/bin/env python3
"""Derive exact report counts and rational plotting data from scored rows."""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
BENCH=ROOT/"benchmark"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--matrix",type=pathlib.Path,required=True)
    ap.add_argument("--build",type=pathlib.Path,required=True)
    ap.add_argument("--observations",type=pathlib.Path,required=True)
    ap.add_argument("--synthetic-abc",type=pathlib.Path,required=True)
    ap.add_argument("--local",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True);args=ap.parse_args()
    rows=list(csv.DictReader(args.matrix.open()))
    manifest=json.loads((BENCH/"manifest.json").read_text())
    cases=[json.loads((BENCH/item["case"]).read_text()) for item in manifest["cases"]]
    builds=json.loads(args.build.read_text())["records"]
    obs=[json.loads(line) for line in args.observations.read_text().splitlines() if line.strip()]
    composition=collections.Counter((c["origin"],c["label_status"]) for c in cases)
    build_counts=collections.Counter((next(c["origin"] for c in cases if c["id"]==b["case_id"]),b["status"]) for b in builds)
    outcome_counts=collections.defaultdict(collections.Counter)
    pattern_counts=collections.defaultdict(collections.Counter)
    unsafe=collections.defaultdict(list)
    scatter={}
    for row in rows:
        label=row["label_status"];tool=row["tool"];out=row["outcome"]
        outcome_counts[(label,tool)][out]+=1
        pattern_counts[(label,tool,row["expected_pattern"] or "MISSING")][out]+=1
        if row["unsafe_certification"]=="True":unsafe[(label,tool)].append(row["case_id"])
    for (label,tool),cnt in outcome_counts.items():
        tp=cnt["DETECT"];fp=cnt["FALSE-ALARM"]
        decided=sum(cnt[k] for k in ("DETECT","MISS","FALSE-ALARM","CLEAR"))
        total=sum(cnt.values())
        scatter[f"{label}/{tool}"]={"precision_numerator":tp,"precision_denominator":tp+fp,
                                    "decided_numerator":decided,"decided_denominator":total,
                                    "precision":"MISSING" if tp+fp==0 else f"{tp}/{tp+fp}",
                                    "decided_rate":f"{decided}/{total}"}
    case_index={c["id"]:c for c in cases}
    by_case=collections.defaultdict(dict)
    for row in rows:by_case[(row["tool"],row["case_id"])][row["expected_state"]]=row["outcome"]
    pairs=collections.defaultdict(lambda:collections.Counter())
    for (tool,cid),states in by_case.items():
        c=case_index[cid]
        if c["origin"]=="public-report":continue
        pair=c["pair_id"]
        pairs[(c["label_status"],tool,pair)]["vulnerable" if c["expected_state"]=="vulnerable" else "repaired"]+=1
    discrimination={}
    for label in sorted({c["label_status"] for c in cases if c["origin"]!="public-report"}):
        for tool in sorted({r["tool"] for r in rows}):
            pair_ids=sorted({c["pair_id"] for c in cases if c["label_status"]==label and c["origin"]!="public-report"})
            successes=[];unknown=[]
            for pair in pair_ids:
                states={c["expected_state"]:by_case[(tool,c["id"])].get(c["expected_state"],"UNKNOWN") for c in cases if c.get("pair_id")==pair and c["label_status"]==label}
                if states.get("vulnerable")=="DETECT" and states.get("repaired")=="CLEAR":successes.append(pair)
                elif "UNKNOWN" in states.values():unknown.append(pair)
            discrimination[f"{label}/{tool}"]={"success_pairs":successes,"success_count":len(successes),
                "total_pairs":len(pair_ids),"unknown_pairs":unknown}
    native_status=collections.defaultdict(collections.Counter)
    native_invocations=collections.Counter()
    for o in obs:
        if "native_status" in o:native_status[o["tool"]][o["native_status"]]+=1
        if "native_invocations" in o:native_invocations[o["tool"]]+=o["native_invocations"]
    native_execution={}
    for tool in ("circomspect","picus","zkap"):
        counts=collections.Counter();invocations=0;removed=0
        paths=list(args.synthetic_abc.glob("cases/*/B.json"))+list(args.local.glob("DEV-H*/selected/ABC/B.json"))
        for path in paths:
            x=json.loads(path.read_text())
            detail=x.get("native",{}).get("tools",{}).get(tool,{})
            counts["case_status:"+str(detail.get("status"))]+=1
            for record in detail.get("invocations",[]):
                invocations+=1
                key="timeout" if record.get("timed_out") else "exit:"+str(record.get("exit_status"))
                counts[key]+=1
                if record.get("temp_removed") is True:removed+=1
        native_execution[tool]={"cases_with_b_output":len(paths),"invocations":invocations,
                               "picus_temp_removed":removed if tool=="picus" else None,
                               "counts":dict(counts)}
    local_runs=json.loads((args.local/"runs.json").read_text())["records"]
    slither_counts=collections.Counter()
    for r in local_runs:
        d=r.get("commands",{}).get("Slither-default",{})
        if "skipped" in d:slither_counts["skipped:"+d["skipped"]]+=1
        else:slither_counts["exit:"+str(d.get("exit_status"))]+=1
    native_execution["slither_default"]={"counts":dict(slither_counts)}
    output={"schema":"bindcheck-benchmark.metrics/v1",
            "composition":{f"{a}/{b}":v for (a,b),v in sorted(composition.items())},
            "build_status":{f"{a}/{b}":v for (a,b),v in sorted(build_counts.items())},
            "outcomes":{f"{a}/{b}":dict(v) for (a,b),v in sorted(outcome_counts.items())},
            "by_pattern":{f"{a}/{b}/{p}":dict(v) for (a,b,p),v in sorted(pattern_counts.items())},
            "scatter":scatter,
            "unsafe_certification":{f"{a}/{b}":v for (a,b),v in sorted(unsafe.items())},
            "pair_discrimination":discrimination,
            "native_status":{k:dict(v) for k,v in native_status.items()},
            "native_invocations":dict(native_invocations),
            "native_execution":native_execution}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"composition":output["composition"],"build_status":output["build_status"]},sort_keys=True))

if __name__=="__main__":main()
