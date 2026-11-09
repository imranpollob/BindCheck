#!/usr/bin/env python3
"""Fetch pinned public Git trees into ignored temporary storage for audit.

No source checkout or generated dependency is committed. Each fetch and tree
inventory is retained under results/raw/bench/public-fetch-20261109.
"""
from __future__ import annotations

import concurrent.futures
import csv
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench/public-fetch-20261109"


def run(argv, cwd=None, timeout=180):
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                                timeout=timeout, check=False)
        return {"argv": argv, "exit_status": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "elapsed_seconds": time.monotonic() - start}
    except subprocess.TimeoutExpired as exc:
        return {"argv": argv, "exit_status": None, "timed_out": True,
                "stdout": (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                "stderr": (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                "elapsed_seconds": time.monotonic() - start}


def fetch_repo(repo, commits):
    dest = RAW / "cache" / repo.replace("/", "__")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir(exist_ok=True)
    log = [run(["git", "init", "--bare", str(dest)])]
    if log[-1]["exit_status"] != 0:
        return {"repo": repo, "cache": str(dest), "commands": log}
    log.append(run(["git", "-C", str(dest), "remote", "add", "origin",
                    f"https://github.com/{repo}.git"]))
    for commit in sorted(commits):
        entry = run(["git", "-C", str(dest), "-c", "http.lowSpeedLimit=1000",
                     "-c", "http.lowSpeedTime=30", "fetch", "--filter=blob:none",
                     "--no-tags", "--depth=1", "origin", commit], timeout=240)
        log.append(entry)
        if entry["exit_status"] == 0:
            tree = run(["git", "-C", str(dest), "ls-tree", "-r", "--name-only", commit])
            log.append({k: v for k, v in tree.items() if k != "stdout"})
            if tree["exit_status"] == 0:
                path = RAW / "trees" / f"{commit}.txt"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(tree["stdout"])
                log[-1]["tree_file"] = str(path)
                log[-1]["tree_entries"] = len(tree["stdout"].splitlines())
    return {"repo": repo, "cache": str(dest), "commands": log}


def main():
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    by_repo = {}
    for row in rows:
        by_repo.setdefault(row["repository"], set()).update([row["vulnerable_commit"], row["fixed_commit"]])
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fetch_repo, repo, commits): repo for repo, commits in by_repo.items()}
        results = []
        for future in concurrent.futures.as_completed(futures):
            value = future.result()
            results.append(value)
            print(value["repo"], sum(c.get("exit_status") == 0 and "fetch" in c["argv"] for c in value["commands"]),
                  "/", len(by_repo[value["repo"]]), flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "fetch.json").write_text(json.dumps({"records": sorted(results, key=lambda x: x["repo"])},
                                                indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
