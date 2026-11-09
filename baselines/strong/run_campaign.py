#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .arm_a import analyze_arm_a
from .arm_b import analyze_arm_b
from .arm_c import analyze_arm_c
from .common import ROOT, sha256_file, write_json

DEV_CHECKOUTS = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev")


SOURCE_SUFFIXES = ("circom", "sol", "nr", "json", "lock", "toml", "yaml", "yml", "md", "sym", "r1cs", "sh", "js", "ts")
SPARSE_PATHS = tuple(pattern for suffix in SOURCE_SUFFIXES for pattern in (f"/*.{suffix}", f"/**/*.{suffix}")) + (
    "/Makefile", "/**/Makefile", "/justfile", "/**/justfile",
)
DATA_WALL_TOKENS = (
    "zkemail", "zk-email", "semaphore-protocol", "selfxyz/self", "/maci",
    "a16z/zkdrops",
    "tangle-network", "nightfall", "zeto", "veil", "foom",
)


def _run(argv: list[str], *, cwd: pathlib.Path | None = None, timeout: float = 600.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return {
            "argv": argv, "cwd": str(cwd) if cwd else None,
            "exit_status": result.returncode, "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": result.stdout, "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv, "cwd": str(cwd) if cwd else None,
            "exit_status": None, "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": exc.stdout or "", "stderr": exc.stderr or "",
        }


def dev_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with (ROOT / "dataset" / "source-corpus-v2.csv").open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            if item["split"] != "DEV":
                continue
            index = len(rows) + 1
            row_id = f"DEV-F{index:02d}" if index <= 50 else f"DEV-H{index - 50:02d}"
            rows.append({"id": row_id, "repository": item["repository"],
                         "commit": item["commit"], "source": "dataset/source-corpus-v2.csv:DEV"})
    if len(rows) != 56 or len({(row["repository"], row["commit"]) for row in rows}) != 56:
        raise ValueError("DEV reconstruction must contain 56 unique pinned repository revisions")
    return rows


def synthetic_rows() -> list[dict[str, str]]:
    expected = json.loads((ROOT / "redteam" / "adversarial" / "expected.json").read_text(encoding="utf-8"))
    rows = []
    for item in expected["cases"]:
        path = ROOT / "redteam" / "adversarial" / item["id"]
        rows.append({"id": item["id"], "path": str(path), "label": item["label"], "family": item["family"]})
    return rows


def data_wall_blocked(repository: str) -> bool:
    lowered = repository.lower()
    return any(token in lowered for token in DATA_WALL_TOKENS)


def checkout_path(work_root: pathlib.Path, row: dict[str, str]) -> pathlib.Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "__", row["repository"])
    return work_root / f"{row['id']}--{safe}--{row['commit'][:12]}"


def acquire(work_root: pathlib.Path, row: dict[str, str]) -> tuple[pathlib.Path, dict[str, Any]]:
    destination = checkout_path(work_root, row)
    destination.parent.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    clone = _run([
        "git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
        f"https://github.com/{row['repository']}.git", str(destination),
    ])
    steps.append(clone)
    if clone["exit_status"] != 0:
        return destination, {**row, "status": "clone-failed", "steps": steps}
    sparse = _run(["git", "sparse-checkout", "set", "--no-cone", *SPARSE_PATHS], cwd=destination)
    steps.append(sparse)
    if sparse["exit_status"] != 0:
        return destination, {**row, "status": "sparse-failed", "steps": steps}
    fetch = _run(["git", "fetch", "--quiet", "--depth", "1", "origin", row["commit"]], cwd=destination)
    steps.append(fetch)
    if fetch["exit_status"] != 0:
        return destination, {**row, "status": "fetch-failed", "steps": steps}
    checkout = _run(["git", "checkout", "--quiet", "--detach", row["commit"]], cwd=destination)
    steps.append(checkout)
    observed = _run(["git", "rev-parse", "HEAD"], cwd=destination, timeout=20)
    steps.append(observed)
    head = observed["stdout"].strip()
    status = "ready" if checkout["exit_status"] == 0 and head == row["commit"] else "revision-mismatch"
    return destination, {**row, "status": status, "observed_head": head, "steps": steps}


def existing_dev_checkout(row: dict[str, str]) -> tuple[pathlib.Path, dict[str, Any]]:
    matches = list(DEV_CHECKOUTS.glob(f"{row['id']}--*--{row['commit'][:12]}"))
    if len(matches) != 1:
        return DEV_CHECKOUTS / row["id"], {**row, "status": "CHECKOUT_MISSING_OR_AMBIGUOUS", "matches": [str(p) for p in matches]}
    source = matches[0]
    observed = _run(["git", "rev-parse", "HEAD"], cwd=source, timeout=20)
    head = observed["stdout"].strip()
    status = "ready" if observed["exit_status"] == 0 and head == row["commit"] else "REVISION_MISMATCH"
    return source, {**row, "status": status, "observed_head": head,
                    "source_accessed": status == "ready", "steps": [observed], "read_only_reused": True}


def blocked_result(arm: str, row: dict[str, str], reason: str) -> dict[str, Any]:
    return {
        "schema": "bindcheck-redteam.strong-result/v1",
        "tool": {"name": "bindcheck-strong", "version": "0.1.0", "arm": arm},
        "run": {"status": "UNKNOWN", "fatal_reason": reason, "elapsed_seconds": 0.0},
        "inputs": {"repository": row.get("repository"), "commit": row.get("commit"), "files": []},
        "result": {"verdict": "UNKNOWN", "evidence_grade": "E0", "findings": []},
        "coverage": {"source_accessed": False},
        "native": {},
        "limitations": ["The row was scheduled but source was not accessed; no safe or comparative result follows."],
    }


def cleanup_clone(path: pathlib.Path, work_root: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve()
    root = work_root.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError(f"refusing cleanup outside campaign work root: {resolved}")
    existed = resolved.exists()
    if existed:
        shutil.rmtree(resolved)
    return {"path": str(resolved), "existed": existed, "removed": not resolved.exists()}


def run_row(
    row: dict[str, str],
    campaign: str,
    output: pathlib.Path,
    work_root: pathlib.Path,
    a_budget: float,
    b_budget: float,
) -> dict[str, Any]:
    row_output = output / "cases" / row["id"]
    row_output.mkdir(parents=True, exist_ok=True)
    if campaign == "dev":
        source, acquisition = existing_dev_checkout(row)
        write_json(row_output / "acquisition.json", acquisition)
        if acquisition["status"] != "ready":
            results = {arm: blocked_result(arm, row, acquisition["status"]) for arm in ("A", "B", "C")}
            for arm, result in results.items():
                write_json(row_output / f"{arm}.json", result)
            return {"row": row, "acquisition": acquisition, "results": results, "cleanup": None}
    else:
        source = pathlib.Path(row["path"])
        acquisition = {**row, "status": "local-synthetic", "source_accessed": True}
        write_json(row_output / "acquisition.json", acquisition)
    try:
        try:
            arm_a = analyze_arm_a(source, row_output / "A", a_budget)
            write_json(row_output / "A.json", arm_a)
            arm_b = analyze_arm_b(source, row_output / "B", b_budget)
            write_json(row_output / "B.json", arm_b)
            arm_c = analyze_arm_c(source, row_output / "C", arm_a, arm_b)
            write_json(row_output / "C.json", arm_c)
            results = {"A": arm_a, "B": arm_b, "C": arm_c}
        except Exception as exc:
            results = {}
            for arm in ("A", "B", "C"):
                path = row_output / f"{arm}.json"
                if path.is_file():
                    results[arm] = json.loads(path.read_text(encoding="utf-8"))
                else:
                    results[arm] = blocked_result(arm, row, f"RUNNER_EXCEPTION:{type(exc).__name__}")
                    results[arm]["coverage"]["exception_detail"] = str(exc)
                    write_json(path, results[arm])
    finally:
        cleanup = None
    return {"row": row, "acquisition": acquisition, "results": results, "cleanup": cleanup}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=("synthetic", "dev"), required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--a-budget", type=float, default=120.0)
    parser.add_argument("--b-budget", type=float, default=180.0)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    work_root = output / "work"
    work_root.mkdir()
    rows = synthetic_rows() if args.campaign == "synthetic" else dev_rows()
    started_utc = dt.datetime.now(dt.UTC).isoformat()
    completed: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(run_row, row, args.campaign, output, work_root, args.a_budget, args.b_budget): row
            for row in rows
        }
        for future in as_completed(futures):
            item = future.result()
            completed.append(item)
            print(f"{args.campaign}\t{item['row']['id']}\t{item['acquisition']['status']}", flush=True)
    completed.sort(key=lambda item: item["row"]["id"])
    revision = _run(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=20)["stdout"].strip()
    for arm in ("A", "B", "C"):
        records = []
        for item in completed:
            result_path = output / "cases" / item["row"]["id"] / f"{arm}.json"
            result = item["results"][arm]
            records.append({
                "id": item["row"]["id"],
                "repository": item["row"].get("repository"),
                "commit": item["row"].get("commit"),
                "result_path": result_path.relative_to(ROOT).as_posix() if result_path.is_relative_to(ROOT) else str(result_path),
                "result_sha256": sha256_file(result_path),
                "run_status": result["run"]["status"],
                "fatal_reason": result["run"].get("fatal_reason"),
                "verdict": result["result"]["verdict"],
                "finding_codes": [finding["code"] for finding in result["result"]["findings"]],
                "picus_temp_bytes_by_run": [record.get("temp_bytes_before_cleanup") for record in result.get("native", {}).get("tools", {}).get("picus", {}).get("invocations", [])],
                "cleanup": item["cleanup"],
            })
        manifest = {
            "schema": "bindcheck-redteam.arm-manifest/v1",
            "campaign": args.campaign,
            "arm": arm,
            "started_utc": started_utc,
            "finished_utc": dt.datetime.now(dt.UTC).isoformat(),
            "started_from_revision": revision,
            "row_count": len(records),
            "row_sources": ["redteam/adversarial/expected.json"] if args.campaign == "synthetic" else ["dataset/source-corpus-v2.csv:DEV"],
            "data_wall_tokens": list(DATA_WALL_TOKENS),
            "records": records,
        }
        write_json(output / f"arm-{arm}-manifest.json", manifest)
    write_json(output / "campaign.json", {
        "schema": "bindcheck-redteam.campaign/v1",
        "campaign": args.campaign,
        "started_utc": started_utc,
        "finished_utc": dt.datetime.now(dt.UTC).isoformat(),
        "rows": len(rows),
        "jobs": args.jobs,
        "a_budget_seconds": args.a_budget,
        "b_budget_seconds": args.b_budget,
        "work_root_empty_after_run": not any(work_root.iterdir()),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
