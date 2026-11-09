#!/usr/bin/env python3
"""Install pinned public worktree dependencies in ignored paths, with receipts."""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / "results/raw/bench/public-fetch-20261109/work"
RAW = ROOT / "results/raw/bench/public-deps-20261109"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def one(repo, commit):
    source = WORK / repo.replace("/", "__") / commit[:12]
    lock = source / "yarn.lock"
    if repo == "selfxyz/self":
        argv = ["npm", "exec", "--yes", "--package=@yarnpkg/cli-dist@4.6.0",
                "--", "yarn", "install", "--immutable", "--mode=skip-build"]
        env_extra = {"YARN_NODE_LINKER": "node-modules"}
    else:
        argv = ["yarn", "install", "--frozen-lockfile", "--ignore-scripts",
                "--ignore-engines", "--non-interactive"]
        env_extra = {}
    out = RAW / repo.replace("/", "__") / commit[:12]
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy();env.update(env_extra)
    started = time.monotonic()
    proc = subprocess.Popen(argv, cwd=source, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=300);timed = False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate();timed = True
    (out / "stdout").write_bytes(stdout)
    (out / "stderr").write_bytes(stderr)
    return {"repository": repo, "commit": commit, "source": str(source),
            "lock": str(lock), "lock_sha256": sha(lock) if lock.is_file() else None,
            "argv": argv, "env_extra": env_extra, "exit_status": proc.returncode,
            "timed_out": timed, "elapsed_seconds": time.monotonic()-started,
            "stdout": str(out / "stdout"), "stdout_sha256": sha(out / "stdout"),
            "stderr": str(out / "stderr"), "stderr_sha256": sha(out / "stderr")}


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",choices=("zkemail/ether-email-auth","selfxyz/self"))
    ap.add_argument("--jobs",type=int,default=1)
    args=ap.parse_args()
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    pairs = sorted({(row["repository"], row[k]) for row in rows
                    for k in ("vulnerable_commit", "fixed_commit")
                    if row["repository"] in ("zkemail/ether-email-auth", "selfxyz/self")
                    and (args.repo is None or row["repository"]==args.repo)})
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(one, *pair) for pair in pairs]
        records = []
        for future in concurrent.futures.as_completed(futures):
            record = future.result();records.append(record)
            print(record["repository"],record["commit"][:8],record["exit_status"],flush=True)
    RAW.mkdir(parents=True,exist_ok=True)
    output_name="runs-self.json" if args.repo=="selfxyz/self" else "runs.json"
    (RAW / output_name).write_text(json.dumps({"records": sorted(records,
           key=lambda x: (x["repository"],x["commit"]))},indent=2,sort_keys=True)+"\n")


if __name__ == "__main__":main()
