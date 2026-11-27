#!/usr/bin/env python3
"""Retry default Slither with the exact Solidity compiler required by Self."""
from __future__ import annotations

import csv
import json
import pathlib

from run_public import ROOT, RAW, run

SOLC="/Users/imranpollob/.solc-select/artifacts/solc-0.8.28/solc-0.8.28"


def main():
    rows=[r for r in csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open())
          if r["row"] in ("15","47")]
    records=[]
    for row in rows:
        cid=f"GATE-{row['row']}"
        manifest=json.loads((ROOT/"benchmark/public-triples"/cid/"manifest.json").read_text())
        for side in ("vulnerable","repaired"):
            rev=manifest["revisions"][side]
            source=pathlib.Path(rev["source"])
            consumer=source/rev["roles"]["consumer"]["path"]
            output=RAW/cid/side
            existing=output/"slither-retry2.json"
            if existing.is_file() and json.loads(existing.read_text()).get("success"):
                rec={"status":"PREVIOUS_SUCCESSFUL_RUN","receipt":str(output/"slither-retry2.receipt.json")}
            else:
                rec=run(["slither",consumer,"--solc",SOLC,"--solc-args",
                         f"--base-path {source} --include-path {source}/node_modules",
                         "--json",existing],
                        source,output,"slither-retry2",90,{"PYTHONPATH":str(ROOT)})
            rec["id"]=cid;rec["side"]=side
            records.append(rec)
            print(cid,side,rec.get("exit_status"),rec.get("timed_out"),flush=True)
    (RAW/"slither-self-retry2.json").write_text(json.dumps({"records":records},
                                          indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
