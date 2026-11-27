#!/usr/bin/env python3
"""Fetch Semaphore's exact circomlib from its pinned Yarn lock."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import subprocess
import tarfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/"results/raw/bench/public-deps-20261109/gate36"
WORK=ROOT/"results/raw/bench/public-fetch-20261109/work/semaphore-protocol__semaphore"


def main():
    row=next(r for r in csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open()) if r["row"]=="36")
    source=WORK/row["vulnerable_commit"][:12]
    lock=(source/"yarn.lock").read_text()
    match=re.search(r'circomlib@\^2\.0\.2:\n  version "([^"]+)"\n  resolved "[^"]+"\n  integrity (\S+)',lock)
    assert match and match.group(1)=="2.0.2"
    expected=match.group(2)
    RAW.mkdir(parents=True,exist_ok=True)
    argv=["npm","pack","circomlib@2.0.2","--pack-destination",str(RAW),"--json"]
    run=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=120)
    (RAW/"npm-pack.stdout").write_text(run.stdout)
    (RAW/"npm-pack.stderr").write_text(run.stderr)
    if run.returncode!=0:raise SystemExit(run.stderr)
    package=json.loads(run.stdout)[0]
    assert package["integrity"]==expected,(package["integrity"],expected)
    archive=RAW/package["filename"]
    installed=[]
    for commit in (row["vulnerable_commit"],row["fixed_commit"]):
        work=WORK/commit[:12]
        target=work/"node_modules/circomlib"
        target.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,"r:gz") as tar:
            for member in tar:
                if not member.name.startswith("package/"):continue
                relative=pathlib.PurePosixPath(member.name).relative_to("package")
                if not relative.parts:continue
                if ".." in relative.parts:raise ValueError(member.name)
                destination=target.joinpath(*relative.parts)
                if member.isdir():destination.mkdir(parents=True,exist_ok=True)
                elif member.isfile():
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    with tar.extractfile(member) as src,destination.open("wb") as dst:
                        dst.write(src.read())
        installed.append({"commit":commit,"target":str(target),
                          "package_json_sha256":hashlib.sha256((target/"package.json").read_bytes()).hexdigest()})
    receipt={"argv":argv,"exit_status":run.returncode,"expected_integrity":expected,
             "observed_integrity":package["integrity"],"archive":str(archive),
             "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
             "installed":installed}
    (RAW/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(receipt["observed_integrity"])


if __name__=="__main__":main()
