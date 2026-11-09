#!/usr/bin/env python3
"""Supplement full-tree GATE-47 runs with exact register-ID triple inputs."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import tempfile

from run_public import ROOT, ZKF, CIRCOM, CIRCOMSPECT, PICUS, run

OUT=ROOT/"results/raw/bench/e1-public-targeted-20261109"
PATTERN=re.compile(r'\b(?:include|import)\s+(?:[^;]*?from\s+)?["\']([^"\']+)["\']')


def project(source, manifest, dest):
    pending=[]
    for role in ("circuit","verifier","consumer","target"):
        rel=manifest["roles"].get(role,{}).get("path")
        if rel:pending.append(source/rel)
    seen=set();copied=[]
    while pending:
        path=pending.pop()
        if path in seen or not path.is_file() or not path.is_relative_to(source):
            continue
        seen.add(path)
        rel=path.relative_to(source)
        target=dest/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
        copied.append({"path":rel.as_posix(),
                       "sha256":hashlib.sha256(target.read_bytes()).hexdigest()})
        text=path.read_text(errors="replace")
        for name in PATTERN.findall(text):
            if name.startswith("."):
                other=(path.parent/name).resolve()
                if other.is_relative_to(source) and other.is_file():pending.append(other)
    modules=source/"node_modules"
    if modules.is_dir(): (dest/"node_modules").symlink_to(modules,target_is_directory=True)
    return sorted(copied,key=lambda x:x["path"])


def one(side):
    manifest=json.loads((ROOT/"benchmark/public-triples/GATE-47/manifest.json").read_text())
    rev=manifest["revisions"][side]
    source=pathlib.Path(rev["source"])
    output=OUT/side
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gate47-target-",dir=output) as name:
        inp=pathlib.Path(name)
        copied=project(source,rev,inp)
        env={"PYTHONPATH":str(ROOT),"BINDCHECK_CIRCOM":CIRCOM,
             "BINDCHECK_STRONG_CIRCOM":CIRCOM,
             "BINDCHECK_STRONG_CIRCOMSPECT":CIRCOMSPECT,
             "BINDCHECK_STRONG_PICUS":PICUS}
        commands={}
        commands["ABC"]=run(["/opt/homebrew/bin/python3","-m","baselines.strong.cli",
                             inp,"--output",output/"ABC","--a-budget","40",
                             "--b-budget","45"],ROOT,output,"ABC",150,env)
        commands["BindCheck-F2"]=run([ROOT/"bindcheck-zk","analyze",inp],
                                      ROOT,output,"bindcheck",120,env)
        consumer=inp/rev["roles"]["consumer"]["path"]
        commands["Slither-default"]=run(["slither",consumer,"--solc",
            "/Users/imranpollob/.solc-select/artifacts/solc-0.8.28/solc-0.8.28",
            "--json",output/"slither.json"],inp,output,"slither",90,env)
        circuit=inp/rev["roles"]["circuit"]["path"]
        commands["zkFuzz"]=run([ZKF,"--path_to_mutation_setting",
            ROOT/"benchmark/zkfuzz-settings.json","-l",inp/"node_modules",circuit],
            inp,output,"zkfuzz",90,env)
    return {"side":side,"commit":rev["commit"],"input_files":copied,
            "scratch_removed":not inp.exists(),"commands":commands,
            "purpose":"targeted register-ID triple; full-tree arm B cap omitted this circuit"}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    records=[one(side) for side in ("vulnerable","repaired")]
    (OUT/"runs.json").write_text(json.dumps({"records":records},indent=2,sort_keys=True)+"\n")
    print([(r["side"],len(r["input_files"]),r["scratch_removed"]) for r in records])


if __name__=="__main__":main()
