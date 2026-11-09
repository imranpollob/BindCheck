#!/usr/bin/env python3
"""Run the merged freeze-2 analyzer with full and circuit-withheld inputs."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
BENCH=ROOT/"benchmark"
DEV=pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev")
CIRCOM=pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom")
WITHHELD_SUFFIXES={".circom",".nr",".r1cs",".sym",".zkey",".wasm",".wtns"}
SKIP_DIRS={".git","build","node_modules","target","out","cache","dist","artifacts","__pycache__"}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source_for(case):
    if case["origin"]=="synthetic":
        return ROOT/"redteam/adversarial"/case["id"]
    if case["origin"]=="DEV-history":
        source=case["revisions"]["selected"].get("source_checkout")
        return pathlib.Path(source) if source else None
    return None

def project(source,dest):
    copied=[];withheld=[]
    for path in sorted(source.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(source).parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        rel=path.relative_to(source)
        if path.suffix.lower() in WITHHELD_SUFFIXES:
            withheld.append({"path":rel.as_posix(),"sha256":sha(path)})
            continue
        target=dest/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
        copied.append({"path":rel.as_posix(),"sha256":sha(target)})
    return copied,withheld

def run(argv,cwd,out,timeout,env):
    start=time.monotonic()
    proc=subprocess.Popen([str(v) for v in argv],cwd=cwd,env=env,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:stdout,stderr=proc.communicate(timeout=timeout);timed=False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL)
        stdout,stderr=proc.communicate();timed=True
    out.mkdir(parents=True,exist_ok=True)
    (out/"stdout").write_bytes(stdout);(out/"stderr").write_bytes(stderr)
    parsed=None
    try:parsed=json.loads(stdout)
    except json.JSONDecodeError:pass
    if parsed is not None:(out/"result.json").write_text(json.dumps(parsed,indent=2,sort_keys=True)+"\n")
    return {"argv":[str(v) for v in argv],"cwd":str(cwd),"exit_status":proc.returncode,
            "timed_out":timed,"elapsed_seconds":time.monotonic()-start,
            "stdout":str(out/"stdout"),"stdout_sha256":sha(out/"stdout"),
            "stderr":str(out/"stderr"),"stderr_sha256":sha(out/"stderr"),
            "result":str(out/"result.json") if parsed is not None else None,
            "result_sha256":sha(out/"result.json") if parsed is not None else None,
            "run_status":parsed.get("run",{}).get("status") if parsed else "TIMEOUT" if timed else "UNKNOWN"}

def one(case,out):
    source=source_for(case)
    cid=case["id"]
    result={"id":cid,"source":str(source) if source else None,"modes":{}}
    if not source or not source.is_dir():
        result["status"]="SOURCE_MISSING";return result
    if case["origin"]=="DEV-history":
        observed=subprocess.check_output(["git","rev-parse","HEAD"],cwd=source,text=True).strip()
        expected=case["revisions"]["selected"]["commit"]
        result["source_revision"]={"expected":expected,"observed":observed}
        if observed!=expected:
            result["status"]="REVISION_MISMATCH";return result
    env=os.environ.copy();env["BINDCHECK_CIRCOM"]=str(CIRCOM)
    result["modes"]["full"]=run([ROOT/"bindcheck-zk","analyze",source],ROOT,out/cid/"full",180,env)
    with tempfile.TemporaryDirectory(prefix=f"{cid}-",dir=out/"scratch") as name:
        projected=pathlib.Path(name)
        copied,withheld=project(source,projected)
        result["ablation_input"]={"copied":copied,"withheld":withheld,
                                  "withheld_suffixes":sorted(WITHHELD_SUFFIXES)}
        result["modes"]["no-circuit"]=run([ROOT/"bindcheck-zk","analyze",projected],
                                           ROOT,out/cid/"no-circuit",180,env)
    result["scratch_removed"]=not projected.exists()
    result["status"]="attempted"
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--jobs",type=int,default=3)
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/"scratch").mkdir()
    manifest=json.loads((BENCH/"manifest.json").read_text())
    cases=[json.loads((BENCH/x["case"]).read_text()) for x in manifest["cases"]]
    cases=[c for c in cases if c["origin"] in ("synthetic","DEV-history")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(one,c,out) for c in cases]
        records=[]
        for future in concurrent.futures.as_completed(futures):
            record=future.result();records.append(record)
            print(record["id"],record["status"],flush=True)
    record={"schema":"bindcheck-benchmark.freeze2-runs/v1",
            "created_utc":dt.datetime.now(dt.UTC).isoformat(),
            "freeze_sha256":"92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a",
            "cases":len(cases),"records":sorted(records,key=lambda x:x["id"])}
    (out/"runs.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
