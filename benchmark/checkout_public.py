#!/usr/bin/env python3
"""Materialize each fetched gate commit in ignored, removable worktrees."""
from __future__ import annotations

import concurrent.futures
import csv
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench/public-fetch-20261109"


def one(repo, commit):
    bare = RAW / "cache" / repo.replace("/", "__")
    work = RAW / "work" / repo.replace("/", "__") / commit[:12]
    work.parent.mkdir(parents=True, exist_ok=True)
    argv = ["git", f"--git-dir={bare}", "worktree", "add", "--detach", str(work), commit]
    try:
        run = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
        result = {"repository": repo, "commit": commit, "worktree": str(work),
                  "argv": argv, "exit_status": run.returncode, "stdout": run.stdout,
                  "stderr": run.stderr}
    except subprocess.TimeoutExpired as exc:
        result = {"repository": repo, "commit": commit, "worktree": str(work),
                  "argv": argv, "exit_status": None, "timed_out": True,
                  "stdout": str(exc.stdout or ""), "stderr": str(exc.stderr or "")}
    if work.is_dir():
        head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"],
                              capture_output=True, text=True)
        result["observed_head"] = head.stdout.strip() if head.returncode == 0 else None
    return result


def main():
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    pairs = sorted({(row["repository"], row[k]) for row in rows
                    for k in ("vulnerable_commit", "fixed_commit")})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(one, *pair) for pair in pairs]
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(result["repository"], result["commit"][:8],
                  result["exit_status"], flush=True)
    (RAW / "checkouts.json").write_text(json.dumps({"records": sorted(results,
                  key=lambda x: (x["repository"], x["commit"]))}, indent=2,
                  sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
