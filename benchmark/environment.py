#!/usr/bin/env python3
"""Capture exact executable and source identities for the E1 run."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
TOOLS=pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools")

def probe(argv,cwd=ROOT):
    try:
        r=subprocess.run(argv,cwd=cwd,text=True,capture_output=True,timeout=30,check=False)
        return {"argv":argv,"exit_status":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"argv":argv,"exit_status":None,"error":f"{type(e).__name__}: {e}"}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def main():
    import sys
    out=pathlib.Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
    commands={
      "git_head":["git","rev-parse","HEAD"],"git_status":["git","status","--short"],
      "freeze":["./freeze.sh"],"python":["/opt/homebrew/bin/python3","--version"],
      "slither":["/opt/homebrew/bin/slither","--version"],"solc":["/opt/homebrew/bin/solc","--version"],
      "circom":[str(TOOLS/"circom-src/target/release/circom"),"--version"],
      "circomspect":[str(TOOLS/"circomspect-src/target/release/circomspect"),"--version"],
      "picus":[str(TOOLS/"picus-src/run-picus"),"--help"],
      "docker":["docker","version"],"colima":["colima","status"],
      "host_memory":["sysctl","-n","hw.memsize"],"host_disk":["df","-k","."],
    }
    paths={"python":pathlib.Path("/opt/homebrew/bin/python3"),"slither":pathlib.Path("/opt/homebrew/bin/slither"),
           "solc":pathlib.Path("/opt/homebrew/bin/solc"),"circom":TOOLS/"circom-src/target/release/circom",
           "circomspect":TOOLS/"circomspect-src/target/release/circomspect",
           "picus":TOOLS/"picus-src/run-picus"}
    result={"schema":"bindcheck-benchmark.environment/v1","created_utc":dt.datetime.now(dt.UTC).isoformat(),
            "commands":{k:probe(v) for k,v in commands.items()},
            "executables":{k:{"path":str(p),"sha256":sha(p)} for k,p in paths.items()},
            "source_revisions":{k:probe(["git","rev-parse","HEAD"],TOOLS/(k+"-src")) for k in ("circom","circomspect","picus")},
            "zkap_preflight":{"docker_path":shutil.which("docker"),"colima_path":shutil.which("colima"),
              "prior_record":"reports/redteam/manifests/zkap-preflight.json"}}
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
