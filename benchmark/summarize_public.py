#!/usr/bin/env python3
"""Add pinned public triple and execution receipts to the machine metrics."""
from __future__ import annotations

import collections
import csv
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/bench"
RAW=ROOT/"results/raw/bench/e1-public-20261109"


def load(path):
    try:return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError):return None


def main():
    metrics=load(OUT/"metrics.json")
    rows=list(csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open()))
    runs={}
    result_roots={}
    reused_slots=0
    for name in ("runs-structural.json","runs-email.json","runs-self.json",
                 "runs-structural-zkfuzz.json"):
        data=load(RAW/name)
        if data:
            for record in data["records"]:
                if record.get("reused_from"):
                    reused_slots+=1
                key=(record["id"],record["side"])
                runs.setdefault(key,{}).update(record.get("commands",{}))
                result_roots[key]=pathlib.Path(record.get("source_result_root") or RAW/record["id"]/record["side"])
    build_counts=collections.Counter()
    role_counts=collections.defaultdict(collections.Counter)
    execution=collections.defaultdict(collections.Counter)
    raw_patterns=collections.defaultdict(collections.Counter)
    pattern_rows=[]
    cases={}
    for row in rows:
        cid=f"GATE-{row['row']}"
        path=ROOT/"benchmark/public-triples"/cid/"manifest.json"
        manifest=load(path)
        by={}
        for side,rev in manifest["revisions"].items():
            status=rev.get("buildability",{}).get("status",rev.get("status","UNKNOWN"))
            build_counts[status]+=1
            for role,record in rev.get("build",{}).items():
                if role in ("circuit","verifier","consumer"):
                    role_counts[role][record.get("status","UNKNOWN")]+=1
            cmd=runs.get((cid,side),{})
            bind_path=result_roots.get((cid,side),RAW/cid/side)/"bindcheck.stdout"
            bind=load(bind_path)
            for pattern in ("P1","P2","P3","P4","P5"):
                verdict=(bind or {}).get("patterns",{}).get(pattern,{}).get("verdict","MISSING")
                raw_patterns[pattern][verdict]+=1
                pattern_rows.append({"case_id":cid,"side":side,"pattern":pattern,
                                     "verdict":verdict,"source":str(bind_path)})
            for tool in ("ABC","BindCheck-F2","Slither-default","zkFuzz","ZKAP"):
                d=cmd.get(tool)
                value=("MISSING" if d is None else "EXIT_UNRECORDED" if d.get("status")=="OUTPUT_PRESENT_EXIT_UNRECORDED" else
                       "TIMEOUT" if d.get("timed_out") else
                       "EXIT_"+str(d.get("exit_status")) if "exit_status" in d else
                       d.get("status","UNKNOWN"))
                execution[tool][value]+=1
            by[side]={"commit":rev["commit"],"buildability":status,
                      "blocker":rev.get("structural_blocker"),
                      "roles":{k:v.get("path") for k,v in rev.get("roles",{}).items()},
                      "dependency_install":rev.get("dependency_install",{}).get("status","UNKNOWN")}
        cases[cid]={"manifest":str(path.relative_to(ROOT)),"revisions":by}
    metrics["public_pinned"]={"pairs":len(rows),"revision_slots":sum(len(c["revisions"]) for c in cases.values()),
                              "unique_repository_commits":len({(row["repository"],row[k]) for row in rows for k in ("vulnerable_commit","fixed_commit")}),
                              "reused_revision_slots":reused_slots,
                              "buildability":dict(build_counts),
                              "role_builds":{k:dict(v) for k,v in role_counts.items()},
                              "execution":{k:dict(v) for k,v in execution.items()},
                              "raw_bindcheck_patterns":{k:dict(v) for k,v in raw_patterns.items()},
                              "cases":cases,
                              "labels":"PENDING"}
    with (OUT/"public-patterns.csv").open("w",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=list(pattern_rows[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(pattern_rows)
    (OUT/"metrics.json").write_text(json.dumps(metrics,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
