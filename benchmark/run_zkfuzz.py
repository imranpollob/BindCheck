#!/usr/bin/env python3
"""Run pinned circuit-only zkFuzz with a fixed seed and a process-group timeout."""
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

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def one(case,side,rev,binary,out,timeout):
    source=pathlib.Path(rev.get("source_tree") or rev.get("source_checkout") or "")
    if not source.is_absolute():source=ROOT/source
    rel=rev["roles"].get("circuit")
    record={"case_id":case["id"],"side":side,"circuit":rel,"source_root":str(source)}
    if not rel or not (source/rel).is_file():
        record["status"]="MISSING_CIRCUIT";return record
    if not rel.endswith(".circom"):
        record["status"]="UNSUPPORTED_FRONTEND";return record
    target=out/case["id"]/side;target.mkdir(parents=True,exist_ok=True)
    argv=[str(binary),"--path_to_mutation_setting",str(BENCH/"zkfuzz-settings.json"),str(source/rel)]
    start=time.monotonic()
    try:
        p=subprocess.Popen(argv,cwd=source/rel.rsplit('/',1)[0] if '/' in rel else source,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:stdout,stderr=p.communicate(timeout=timeout);timed=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate();timed=True
        (target/"stdout").write_bytes(stdout);(target/"stderr").write_bytes(stderr)
        record.update({"argv":argv,"exit_status":p.returncode,"timed_out":timed,
          "elapsed_seconds":time.monotonic()-start,"stdout":str(target/"stdout"),
          "stdout_sha256":sha(target/"stdout"),"stderr":str(target/"stderr"),
          "stderr_sha256":sha(target/"stderr"),
          "status":"TIMEOUT" if timed else "COMPLETED" if p.returncode==0 else "ERROR"})
    except OSError as e:record.update({"status":"SETUP_FAILED","error":f"{type(e).__name__}: {e}"})
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--binary",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--jobs",type=int,default=4);ap.add_argument("--timeout",type=float,default=120)
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((BENCH/"manifest.json").read_text())
    entries=[]
    for item in manifest["cases"]:
        c=json.loads((BENCH/item["case"]).read_text())
        for side,rev in c["revisions"].items():entries.append((c,side,rev))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(one,c,s,r,args.binary.resolve(),out,args.timeout) for c,s,r in entries]
        results=[]
        for f in concurrent.futures.as_completed(futures):
            result=f.result();results.append(result)
            print(result["case_id"],result["side"],result["status"],flush=True)
    record={"schema":"bindcheck-benchmark.zkfuzz-runs/v1","created_utc":dt.datetime.now(dt.UTC).isoformat(),
      "binary_sha256":sha(args.binary),"settings_sha256":sha(BENCH/"zkfuzz-settings.json"),
      "timeout_seconds":args.timeout,"jobs":args.jobs,
      "records":sorted(results,key=lambda r:(r["case_id"],r["side"]))}
    (out/"runs.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
