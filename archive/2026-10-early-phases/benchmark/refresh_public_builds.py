#!/usr/bin/env python3
"""Retry source-linked public builds once per distinct pinned triple revision."""
from __future__ import annotations

import concurrent.futures
import csv
import json
import pathlib

from audit_public import ROLES, one

ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFESTS=ROOT/"benchmark/public-triples"


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--jobs",type=int,default=1)
    ap.add_argument("--ids",nargs="*",default=["15","28","29","30","31","32","33","40","47"])
    args=ap.parse_args()
    rows=[r for r in csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open()) if r["row"] in args.ids]
    groups={}
    for row in rows:
        for side in ("vulnerable","repaired"):
            commit=row["vulnerable_commit" if side=="vulnerable" else "fixed_commit"]
            roles=ROLES[row["row"]]
            key=(row["repository"],commit,roles.get("circuit"),roles.get("verifier"),roles.get("consumer"))
            groups.setdefault(key,[]).append((row,side))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures={key:pool.submit(one,*members[0]) for key,members in groups.items()}
        results={}
        for key,future in futures.items():
            result=future.result();results[key]=result
            print(result["repository"],result["commit"][:8],
                  {k:v.get("status") for k,v in result["build"].items()},flush=True)
    for key,members in groups.items():
        result=results[key]
        rep=members[0]
        for row,side in members:
            path=MANIFESTS/f"GATE-{row['row']}"/"manifest.json"
            manifest=json.loads(path.read_text())
            copy=json.loads(json.dumps(result))
            if (row,side)!=rep:
                copy["build_reused_from"]={"case_id":f"GATE-{rep[0]['row']}","side":rep[1],
                                           "reason":"same repository commit and identical circuit/verifier/consumer paths"}
            manifest["revisions"][side]=copy
            path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
