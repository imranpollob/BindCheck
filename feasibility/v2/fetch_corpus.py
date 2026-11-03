#!/usr/bin/env python3
"""Fetch the frozen 50-project corpus at its exact recorded revisions.

This is source acquisition only. It neither contacts deployments nor executes
project code. Repositories live in the ignored feasibility/work/v2 tree.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


SPARSE_PATHS = (
    "/**/*.circom",
    "/**/*.sol",
    "/**/*.json",
    "/**/*.lock",
    "/**/*.toml",
    "/**/*.yaml",
    "/**/*.yml",
    "/**/*.md",
    "/**/*.sym",
    "/**/*.r1cs",
    "/**/*.zkey",
    "/**/*.wasm",
    "/**/*.ptau",
    "/**/*.sh",
)


def command(args: list[str], cwd: pathlib.Path | None = None, timeout: int = 180) -> dict[str, object]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "argv": args,
            "exit": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": args,
            "exit": None,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timeout": True,
        }


def fetch(row: dict[str, str], repos: pathlib.Path) -> dict[str, object]:
    repository = row["repository"]
    revision = row["commit"]
    destination = repos / repository.replace("/", "__")
    steps: list[dict[str, object]] = []
    if not (destination / ".git").exists():
        clone = command(
            [
                "git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                f"https://github.com/{repository}.git", str(destination),
            ],
            timeout=300,
        )
        steps.append(clone)
        if clone["exit"] != 0:
            return {"repository": repository, "commit": revision, "status": "clone-failed", "steps": steps}

    sparse = command(
        ["git", "sparse-checkout", "set", "--no-cone", *SPARSE_PATHS],
        cwd=destination,
    )
    steps.append(sparse)
    if sparse["exit"] != 0:
        return {"repository": repository, "commit": revision, "status": "sparse-failed", "steps": steps}

    has_commit = command(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=destination)
    steps.append(has_commit)
    if has_commit["exit"] != 0:
        fetched = command(
            ["git", "fetch", "--quiet", "--depth", "1", "origin", revision],
            cwd=destination,
            timeout=300,
        )
        steps.append(fetched)
        if fetched["exit"] != 0:
            return {"repository": repository, "commit": revision, "status": "fetch-commit-failed", "steps": steps}

    checkout = command(["git", "checkout", "--quiet", "--detach", revision], cwd=destination, timeout=300)
    steps.append(checkout)
    if checkout["exit"] != 0:
        return {"repository": repository, "commit": revision, "status": "checkout-failed", "steps": steps}

    observed = command(["git", "rev-parse", "HEAD"], cwd=destination)
    steps.append(observed)
    head = str(observed["stdout"]).strip()
    status = "fetched" if observed["exit"] == 0 and head == revision else "revision-mismatch"
    return {
        "repository": repository,
        "commit": revision,
        "observed_head": head,
        "status": status,
        "path": str(destination),
        "steps": steps,
    }


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=pathlib.Path, default=root / "feasibility/candidate-set.csv")
    parser.add_argument("--repos", type=pathlib.Path, default=root / "feasibility/work/v2/repos")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.ledger.open(newline="", encoding="utf-8")))
    args.repos.mkdir(parents=True, exist_ok=True)
    if args.output is None:
        timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        args.output = root / f"results/raw/feasibility-v2/corpus-fetch-{timestamp}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch, row, args.repos): row for row in rows}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{result['status']}\t{result['repository']}")
    results.sort(key=lambda item: str(item["repository"]))
    record = {
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "ledger": str(args.ledger),
        "ledger_sha256": hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
        "requested": len(rows),
        "fetched": sum(item["status"] == "fetched" for item in results),
        "results": results,
    }
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"requested": record["requested"], "fetched": record["fetched"], "output": str(args.output)}))
    return 0 if record["fetched"] == record["requested"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
