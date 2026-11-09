#!/usr/bin/env python3
"""Verify pinned role hashes, then remove only this lane's temporary worktrees."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import shutil
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/"results/raw/bench/public-fetch-20261109"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows=list(csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open()))
    checks=[]
    for row in rows:
        path=ROOT/"benchmark/public-triples"/f"GATE-{row['row']}"/"manifest.json"
        manifest=json.loads(path.read_text())
        for side,rev in manifest["revisions"].items():
            source=pathlib.Path(rev["source"])
            head=subprocess.run(["git","-C",str(source),"rev-parse","HEAD"],
                                capture_output=True,text=True)
            assert head.returncode==0 and head.stdout.strip()==rev["commit"]
            for role,info in rev["roles"].items():
                if info["type"]=="file":
                    target=source/info["path"]
                    actual=sha(target)
                    assert actual==info["sha256"],(path,side,role)
                    checks.append({"case_id":manifest["id"],"side":side,"role":role,
                                   "path":info["path"],"sha256":actual})
    checkouts=json.loads((RAW/"checkouts.json").read_text())["records"]
    checkout_results=[]
    for item in checkouts:
        bare=RAW/"cache"/item["repository"].replace("/","__")
        work=pathlib.Path(item["worktree"])
        if work.is_dir():
            argv=["git",f"--git-dir={bare}","worktree","remove","--force",str(work)]
            run=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
            checkout_results.append({"worktree":str(work),"argv":argv,
                                     "exit_status":run.returncode,"stderr":run.stderr,
                                     "removed":not work.exists()})
    manual=RAW/"work/8a62db1e"
    if manual.is_dir():
        bare=RAW/"cache/zkemail__ether-email-auth"
        argv=["git",f"--git-dir={bare}","worktree","remove","--force",str(manual)]
        run=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
        checkout_results.append({"worktree":str(manual),"argv":argv,
                                 "exit_status":run.returncode,"stderr":run.stderr,
                                 "removed":not manual.exists()})
    if any(not r["removed"] for r in checkout_results):
        raise SystemExit("one or more temporary worktrees remain; caches retained")
    shutil.rmtree(RAW/"cache")
    receipt={"verified_role_hashes":checks,"worktree_removals":checkout_results,
             "bare_cache_removed":not (RAW/"cache").exists()}
    (RAW/"cleanup.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(len(checks),len(checkout_results))


if __name__=="__main__":main()
