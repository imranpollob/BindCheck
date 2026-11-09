#!/usr/bin/env python3
"""Verify source locks and build the pinned local triple candidates into ignored raw output."""
from __future__ import annotations

import argparse
import base64
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
CIRCOM=pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom")
SOLC=pathlib.Path("/opt/homebrew/bin/solc")

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run(argv,cwd,timeout,stdout_path,stderr_path):
    start=time.monotonic()
    try:
        proc=subprocess.Popen([str(x) for x in argv],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:out,err=proc.communicate(timeout=timeout);timed_out=False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL)
            out,err=proc.communicate();timed_out=True
        stdout_path.parent.mkdir(parents=True,exist_ok=True)
        stdout_path.write_bytes(out);stderr_path.write_bytes(err)
        return {"argv":[str(x) for x in argv],"cwd":str(cwd),"exit_status":proc.returncode,
                "timed_out":timed_out,"elapsed_seconds":time.monotonic()-start,
                "stdout":str(stdout_path),"stdout_sha256":sha(stdout_path),
                "stderr":str(stderr_path),"stderr_sha256":sha(stderr_path)}
    except OSError as e:
        return {"argv":[str(x) for x in argv],"cwd":str(cwd),"exit_status":None,
                "timed_out":False,"error":f"{type(e).__name__}: {e}"}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--dependency-root",type=pathlib.Path)
    ap.add_argument("--dependency-tarball",type=pathlib.Path);args=ap.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((BENCH/"manifest.json").read_text())
    records=[]
    for item in manifest["cases"]:
        case=json.loads((BENCH/item["case"]).read_text())
        lock=json.loads((BENCH/item["lock"]).read_text())
        for side,rev in case["revisions"].items():
            result={"case_id":case["id"],"side":side,"commit":rev.get("commit"),"roles":rev["roles"],"checks":[],"commands":[]}
            source=pathlib.Path(rev.get("source_tree") or rev.get("snapshot_root") or rev.get("source_checkout") or "")
            if not source.is_absolute():source=ROOT/source
            result["source_root"]=str(source)
            if rev.get("source_checkout") and source.is_dir():
                head=subprocess.run(["git","rev-parse","HEAD"],cwd=source,text=True,capture_output=True,check=False)
                result["source_revision_check"]={"argv":["git","rev-parse","HEAD"],
                    "exit_status":head.returncode,"observed":head.stdout.strip(),"expected":rev.get("commit")}
                if head.returncode!=0 or head.stdout.strip()!=rev.get("commit"):
                    result["status"]="REVISION_MISMATCH";records.append(result);continue
            hashes=lock["revisions"].get(side,[])
            for entry in hashes:
                p=source/entry["path"]
                result["checks"].append({"path":entry["path"],"expected_sha256":entry["sha256"],
                    "observed_sha256":sha(p) if p.is_file() else None})
            if any(c["observed_sha256"]!=c["expected_sha256"] for c in result["checks"]):
                result["status"]="LOCK_MISMATCH";records.append(result);continue
            if case["family"]=="zkdrops" and args.dependency_root:
                package_lock=source/"package-lock.json"
                expected=json.loads(package_lock.read_text())["packages"]["node_modules/@openzeppelin/contracts"]["integrity"] if package_lock.is_file() else None
                observed=("sha512-"+base64.b64encode(hashlib.sha512(args.dependency_tarball.read_bytes()).digest()).decode()) if args.dependency_tarball and args.dependency_tarball.is_file() else None
                result["dependency_lock"]={"package_lock":str(package_lock),"package_lock_sha256":sha(package_lock) if package_lock.is_file() else None,
                    "tarball":str(args.dependency_tarball) if args.dependency_tarball else None,
                    "tarball_sha256":sha(args.dependency_tarball) if args.dependency_tarball and args.dependency_tarball.is_file() else None,
                    "expected_integrity":expected,"observed_integrity":observed}
                if not expected or observed!=expected:
                    result["status"]="DEPENDENCY_LOCK_MISMATCH";records.append(result);continue
            roles=rev["roles"]
            missing=[role for role,path in roles.items() if not path or not (source/path).is_file()]
            if missing:
                result["status"]="MISSING_ARTIFACT";result["missing_roles"]=missing;records.append(result);continue
            if not roles["circuit"].endswith(".circom"):
                result["status"]="UNSUPPORTED_FRONTEND";records.append(result);continue
            case_out=output/case["id"]/side
            case_out.mkdir(parents=True,exist_ok=True)
            circuit=source/roles["circuit"]
            compile_dir=case_out/"circom";compile_dir.mkdir()
            argv=[CIRCOM,circuit,"--r1cs","--sym","-o",compile_dir]
            for include in [source/"node_modules",circuit.parent/"node_modules",
                            pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/node_modules")]:
                if include.is_dir():argv.extend(["-l",include])
            result["commands"].append(run(argv,source,90,case_out/"circom.stdout",case_out/"circom.stderr"))
            for role in ("verifier","consumer"):
                solc_argv=[SOLC,"--abi","--base-path",source]
                if args.dependency_root and args.dependency_root.is_dir():
                    solc_argv.extend(["--include-path",args.dependency_root.resolve()])
                solc_argv.append(source/roles[role])
                result["commands"].append(run(solc_argv,source,90,case_out/f"{role}.stdout",case_out/f"{role}.stderr"))
            result["status"]="BUILD_OK" if all(c.get("exit_status")==0 and not c.get("timed_out") for c in result["commands"]) else "BUILD_FAILED"
            if rev.get("verifier_kind","").startswith("synthetic interface") and result["status"]=="BUILD_OK":
                result["status"]="BUILD_OK_NON_GROTH16"
            records.append(result)
        print(case["id"],[(r["side"],r["status"]) for r in records if r["case_id"]==case["id"]],flush=True)
    record={"schema":"bindcheck-benchmark.build/v1","created_utc":dt.datetime.now(dt.UTC).isoformat(),
            "tool_paths":{"circom":str(CIRCOM),"circom_sha256":sha(CIRCOM) if CIRCOM.is_file() else None,
                          "solc":str(SOLC),"solc_sha256":sha(SOLC) if SOLC.is_file() else None},"records":records}
    (output/"build.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
