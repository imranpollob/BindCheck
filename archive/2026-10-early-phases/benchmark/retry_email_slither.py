#!/usr/bin/env python3
"""Run Slither default detectors with pinned-worktree import paths."""
from __future__ import annotations

import csv
import json
import pathlib

from run_public import ROOT, RAW, run


def main():
    rows=[r for r in csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open())
          if r["row"] in ("28","29","30","31","32","33","40")]
    records=[]
    for row in rows:
        cid=f"GATE-{row['row']}"
        manifest=json.loads((ROOT/"benchmark/public-triples"/cid/"manifest.json").read_text())
        for side in ("vulnerable","repaired"):
            rev=manifest["revisions"][side]
            source=pathlib.Path(rev["source"])
            output=RAW/cid/side
            if side=="vulnerable" and row["row"] in ("30","31","32","33"):
                records.append({"id":cid,"side":side,"status":"REUSED_FROM_GATE_28_VULNERABLE"})
                continue
            consumer=source/rev["roles"]["consumer"]["path"]
            rec=run(["slither",consumer,"--solc","/opt/homebrew/bin/solc",
                     "--solc-args",f"--base-path {source} --include-path {source}/node_modules",
                     "--json",output/"slither-retry2.json"],
                    source,output,"slither-retry2",90,{"PYTHONPATH":str(ROOT)})
            rec["id"]=cid;rec["side"]=side
            records.append(rec)
            print(cid,side,rec["exit_status"],rec["timed_out"],flush=True)
    (RAW/"slither-email-retry2.json").write_text(json.dumps({"records":records},
                                               indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
