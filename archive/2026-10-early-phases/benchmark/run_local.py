#!/usr/bin/env python3
"""Run committed arms and default Slither on local locked sources only."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
BENCH=ROOT/"benchmark"
PYTHON=pathlib.Path("/opt/homebrew/bin/python3")
SLITHER=pathlib.Path("/opt/homebrew/bin/slither")

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(argv,cwd,output,timeout,env=None):
    output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    try:
        p=subprocess.Popen([str(v) for v in argv],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:out,err=p.communicate(timeout=timeout);timed_out=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate();timed_out=True
        (output/"stdout").write_bytes(out);(output/"stderr").write_bytes(err)
        return {"argv":[str(v) for v in argv],"cwd":str(cwd),"exit_status":p.returncode,
                "timed_out":timed_out,"elapsed_seconds":time.monotonic()-start,
                "stdout":str(output/"stdout"),"stdout_sha256":sha(output/"stdout"),
                "stderr":str(output/"stderr"),"stderr_sha256":sha(output/"stderr")}
    except OSError as e:
        return {"argv":[str(v) for v in argv],"cwd":str(cwd),"exit_status":None,
                "timed_out":False,"error":f"{type(e).__name__}: {e}"}

def process(item,out,dependency_root):
    case=json.loads((BENCH/item["case"]).read_text())
    records=[]
    for side,rev in case["revisions"].items():
        source=pathlib.Path(rev.get("source_tree") or rev.get("source_checkout") or "")
        if not source.is_absolute():source=ROOT/source
        base=out/case["id"]/side
        base.mkdir(parents=True,exist_ok=True)
        record={"id":case["id"],"side":side,"source":str(source),"commands":{}}
        if case["origin"] == "public-report":
            record["status"]="MISSING_TRIPLE_SOURCE";records.append(record);continue
        if not source.is_dir():
            record["status"]="MISSING_SOURCE";records.append(record);continue
        if case["origin"] == "DEV-history":
            env=os.environ.copy();env["PYTHONPATH"]=str(ROOT)
            env["BINDCHECK_STRONG_CIRCOM"]=str(pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom"))
            env["BINDCHECK_STRONG_CIRCOMSPECT"]=str(pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circomspect-src/target/release/circomspect"))
            env["BINDCHECK_STRONG_PICUS"]=str(pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/picus-src/run-picus"))
            record["commands"]["ABC"]=run([PYTHON,"-m","baselines.strong.cli",source,
                "--output",base/"ABC","--a-budget","120","--b-budget","180"],ROOT,base/"ABC-command",360,env)
            env["BINDCHECK_CIRCOM"]=env["BINDCHECK_STRONG_CIRCOM"]
            record["commands"]["BindCheck-F1"]=run([ROOT/"bindcheck-zk","analyze",source],ROOT,base/"bindcheck-command",180,env)
        consumer=rev["roles"].get("consumer")
        if consumer and (source/consumer).is_file():
            argv=[SLITHER,source/consumer,"--json",base/"slither.json"]
            if dependency_root:
                argv.extend(["--solc-remaps",f"@openzeppelin/={dependency_root.resolve()}/@openzeppelin/"])
            record["commands"]["Slither-default"]=run(argv,source,base/"slither-command",90)
        else:record["commands"]["Slither-default"]={"skipped":"CONSUMER_MISSING"}
        record["status"]="attempted"
        records.append(record)
    print(case["id"],[(r["side"],r["status"]) for r in records],flush=True)
    return records

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--jobs",type=int,default=3);ap.add_argument("--dependency-root",type=pathlib.Path)
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((BENCH/"manifest.json").read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results=list(pool.map(lambda item:process(item,out,args.dependency_root),manifest["cases"]))
    record={"schema":"bindcheck-benchmark.native-runs/v1","created_utc":dt.datetime.now(dt.UTC).isoformat(),
            "records":[x for sub in results for x in sub]}
    (out/"runs.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
