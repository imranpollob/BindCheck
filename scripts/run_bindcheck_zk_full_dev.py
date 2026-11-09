#!/usr/bin/env python3
"""Acquire and analyze the complete 56-row DEV corpus without path hints.

The row set is reconstructed only from the frozen 50-row feasibility ledger
and ``historical_dev`` entries in ``dataset/source-queries.json``.  This script
does not open the combined DEV/EVAL source ledger or the recall-set ledger.
The analyzer itself remains offline; only the explicit acquisition phase uses
GitHub to obtain the pinned public source revisions.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "bindcheck-zk"
CHECKOUT_ROOT = ROOT / "feasibility" / "work" / "full-dev"
RAW_ROOT = ROOT / "results" / "raw" / "T24"

SOURCE_SUFFIXES = (
    "circom", "sol", "nr", "json", "lock", "toml", "yaml", "yml", "md",
    "sym", "r1cs", "zkey", "wasm", "ptau", "sh", "js", "ts", "mjs", "cjs",
)
SPARSE_PATHS = tuple(
    pattern
    for suffix in SOURCE_SUFFIXES
    for pattern in (f"/*.{suffix}", f"/**/*.{suffix}")
) + (
    "/Makefile", "/**/Makefile", "/justfile", "/**/justfile",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(
    argv: list[str], *, cwd: pathlib.Path | None = None, timeout: float = 600.0,
    output_limit: int | None = 12000,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"},
        )
        stdout = completed.stdout if output_limit is None else completed.stdout[-output_limit:]
        stderr = completed.stderr if output_limit is None else completed.stderr[-output_limit:]
        return {
            "argv": argv,
            "cwd": str(cwd) if cwd else None,
            "exit_status": completed.returncode,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or "" if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr or "" if isinstance(exc.stderr, str) else ""
        if output_limit is not None:
            stdout = stdout[-output_limit:]
            stderr = stderr[-output_limit:]
        return {
            "argv": argv,
            "cwd": str(cwd) if cwd else None,
            "exit_status": None,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": stdout,
            "stderr": stderr,
        }


def dev_rows() -> list[dict[str, str]]:
    """Return exactly the frozen DEV rows without opening either mixed ledger."""
    rows: list[dict[str, str]] = []
    with (ROOT / "feasibility" / "candidate-set.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for index, item in enumerate(csv.DictReader(handle), 1):
            rows.append({
                "id": f"DEV-F{index:02d}",
                "repository": item["repository"],
                "commit": item["commit"],
                "variant": "feasibility-50",
                "source": "feasibility/candidate-set.csv",
            })
    query_config = json.loads((ROOT / "dataset" / "source-queries.json").read_text())
    for index, item in enumerate(query_config["historical_dev"], 1):
        rows.append({
            "id": f"DEV-H{index:02d}",
            "repository": item["repository"],
            "commit": item["commit"],
            "variant": item["variant"],
            "source": "dataset/source-queries.json:historical_dev",
        })
    if len(rows) != 56:
        raise ValueError(f"DEV row reconstruction expected 56 rows, observed {len(rows)}")
    if len({(item["repository"], item["commit"]) for item in rows}) != 56:
        raise ValueError("DEV row reconstruction contains a duplicate repository/commit pair")
    return rows


def checkout_path(row: dict[str, str]) -> pathlib.Path:
    safe = row["repository"].replace("/", "__")
    return CHECKOUT_ROOT / f"{row['id']}--{safe}--{row['commit'][:12]}"


def acquire(row: dict[str, str]) -> dict[str, Any]:
    destination = checkout_path(row)
    destination.parent.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    if not (destination / ".git").is_dir():
        clone = run_command([
            "git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
            f"https://github.com/{row['repository']}.git", str(destination),
        ])
        steps.append(clone)
        if clone["exit_status"] != 0:
            return {**row, "path": str(destination), "status": "clone-failed", "steps": steps}
    sparse = run_command(
        ["git", "sparse-checkout", "set", "--no-cone", *SPARSE_PATHS],
        cwd=destination,
    )
    steps.append(sparse)
    if sparse["exit_status"] != 0:
        return {**row, "path": str(destination), "status": "sparse-failed", "steps": steps}
    present = run_command(
        ["git", "cat-file", "-e", f"{row['commit']}^{{commit}}"], cwd=destination,
    )
    steps.append(present)
    if present["exit_status"] != 0:
        fetched = run_command(
            ["git", "fetch", "--quiet", "--depth", "1", "origin", row["commit"]],
            cwd=destination,
        )
        steps.append(fetched)
        if fetched["exit_status"] != 0:
            return {**row, "path": str(destination), "status": "fetch-failed", "steps": steps}
    checkout = run_command(
        ["git", "checkout", "--quiet", "--detach", row["commit"]], cwd=destination,
    )
    steps.append(checkout)
    if checkout["exit_status"] != 0:
        return {**row, "path": str(destination), "status": "checkout-failed", "steps": steps}
    observed = run_command(["git", "rev-parse", "HEAD"], cwd=destination, timeout=10)
    steps.append(observed)
    head = observed["stdout"].strip()
    status = "ready" if observed["exit_status"] == 0 and head == row["commit"] else "revision-mismatch"
    return {**row, "path": str(destination), "observed_head": head, "status": status, "steps": steps}


def validate_existing(row: dict[str, str]) -> dict[str, Any]:
    destination = checkout_path(row)
    observed = run_command(["git", "rev-parse", "HEAD"], cwd=destination, timeout=10)
    head = observed["stdout"].strip()
    status = "ready" if observed["exit_status"] == 0 and head == row["commit"] else "revision-mismatch"
    return {
        **row,
        "path": str(destination),
        "observed_head": head,
        "status": status,
        "steps": [observed],
    }


def failure_cause(record: dict[str, Any]) -> str:
    text = (record.get("stderr") or "") + "\n" + (record.get("stdout") or "")
    if record.get("timed_out"):
        return "timeout"
    if re.search(r"(?:has not been found|No such file|not found)", text, re.I):
        return "missing-include-or-file"
    if re.search(r"pragma|compiler version|version not supported", text, re.I):
        return "compiler-version"
    if re.search(r"parse|syntax|P10\d\d", text, re.I):
        return "parse-or-type"
    if record.get("reason"):
        return str(record["reason"])
    return "nonzero-exit"


def summarize(row: dict[str, str], result: dict[str, Any], command: dict[str, Any]) -> dict[str, Any]:
    coverage = result.get("coverage", {})
    builds = coverage.get("builds", [])
    build_ok = 0
    failures: dict[str, int] = {}
    for build in builds:
        record = build.get("record") or {}
        if record.get("kind") == "existing" or (
            record.get("exit_status") == 0 and not record.get("timed_out")
        ):
            build_ok += 1
        else:
            cause = failure_cause(record)
            failures[cause] = failures.get(cause, 0) + 1
    cap_skips = sum(
        item.get("reason") == "MAX_FILES_EXCEEDED"
        for item in coverage.get("skipped", [])
    )
    patterns = result.get("patterns", {})
    return {
        "id": row["id"],
        "repository": row["repository"],
        "commit": row["commit"],
        "variant": row["variant"],
        "crash": command.get("exit_status") not in (0, 2) or not isinstance(result, dict),
        "run_status": result.get("run", {}).get("status"),
        "fatal_reason": result.get("run", {}).get("fatal_reason"),
        "triples": result.get("discovery", {}).get("triples", 0),
        "circuits": result.get("discovery", {}).get("circuits", 0),
        "verifiers": result.get("discovery", {}).get("verifiers", 0),
        "consumers": result.get("discovery", {}).get("consumers", 0),
        "builds_ok": build_ok,
        "builds_failed": sum(failures.values()),
        "build_failure_causes": failures,
        "files_inventoried": coverage.get("files_inventoried", 0),
        "files_skipped_by_cap": cap_skips,
        "excluded": coverage.get("excluded", []),
        "verdicts": {
            pattern: patterns.get(pattern, {}).get("verdict", "UNKNOWN")
            for pattern in ("P1", "P2", "P3", "P4", "P5")
        },
        "reasons": {
            pattern: patterns.get(pattern, {}).get("reasons", [])
            for pattern in ("P1", "P2", "P3", "P4", "P5")
        },
        "applicability": {
            pattern: patterns.get(pattern, {}).get("applicability", "UNKNOWN")
            for pattern in ("P1", "P2", "P3", "P4", "P5")
        },
        "unknown_reason_codes": {
            pattern: patterns.get(pattern, {}).get("unknown_reason_codes", [])
            for pattern in ("P1", "P2", "P3", "P4", "P5")
        },
        "runtime_seconds": result.get("run", {}).get("elapsed_seconds"),
    }


def analyze_row(row: dict[str, str], output_dir: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    repository = checkout_path(row)
    record = run_command(
        [str(CLI), "analyze", str(repository)], cwd=ROOT, timeout=150,
        output_limit=None,
    )
    result_path = output_dir / f"{row['id']}--result.json"
    result_path.write_text(record["stdout"], encoding="utf-8")
    try:
        payload = json.loads(record["stdout"])
    except json.JSONDecodeError as exc:
        payload = {"run": {"status": "UNKNOWN", "fatal_reason": "NON_JSON_OUTPUT"}, "coverage": {}}
        record["json_error"] = str(exc)
    record.update({
        "id": row["id"],
        "repository": row["repository"],
        "commit": row["commit"],
        "result": result_path.relative_to(ROOT).as_posix(),
        "result_sha256": sha256(result_path),
        "analyzer_content_sha256": payload.get("tool", {}).get("content_sha256"),
    })
    return record, summarize(row, payload, record)


def main() -> int:
    global CHECKOUT_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    parser.add_argument("--fetch-jobs", type=int, default=6)
    parser.add_argument("--analyze-jobs", type=int, default=3)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--raw-task", default="T24")
    parser.add_argument("--checkout-root", type=pathlib.Path, default=CHECKOUT_ROOT)
    args = parser.parse_args()
    if not re.fullmatch(r"T\d+|soundness", args.raw_task):
        raise ValueError("--raw-task must be a T-number or soundness")
    CHECKOUT_ROOT = args.checkout_root.resolve()

    rows = dev_rows()
    run_id = dt.datetime.now(dt.UTC).strftime(f"{args.phase}-%Y%m%dT%H%M%SZ-") + str(os.getpid())
    output_dir = RAW_ROOT.parent / args.raw_task / run_id
    output_dir.mkdir(parents=True)
    acquisitions: list[dict[str, Any]] = []
    if args.skip_fetch:
        acquisitions = [validate_existing(row) for row in rows]
    else:
        with ThreadPoolExecutor(max_workers=args.fetch_jobs) as pool:
            futures = {pool.submit(acquire, row): row for row in rows}
            for future in as_completed(futures):
                item = future.result()
                acquisitions.append(item)
                print(f"ACQUIRE\t{item['id']}\t{item['status']}", flush=True)
        acquisitions.sort(key=lambda item: item["id"])
    unavailable = [item for item in acquisitions if item["status"] != "ready"]
    if unavailable:
        (output_dir / "acquisition.json").write_text(
            json.dumps(acquisitions, indent=2, sort_keys=True) + "\n"
        )
        raise SystemExit(f"{len(unavailable)} DEV rows were not acquired; see {output_dir}")

    records: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.analyze_jobs) as pool:
        futures = {pool.submit(analyze_row, row, output_dir): row for row in rows}
        for future in as_completed(futures):
            record, summary = future.result()
            records.append(record)
            ledger.append(summary)
            print(
                f"ANALYZE\t{summary['id']}\ttriples={summary['triples']}\t"
                f"status={summary['run_status']}\truntime={summary['runtime_seconds']}",
                flush=True,
            )
    records.sort(key=lambda item: item["id"])
    ledger.sort(key=lambda item: item["id"])
    (output_dir / "acquisition.json").write_text(
        json.dumps(acquisitions, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "per-row-ledger.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    )
    analyzer_hashes = {
        item["analyzer_content_sha256"]
        for item in records
        if item.get("analyzer_content_sha256")
    }
    if len(analyzer_hashes) != 1:
        raise ValueError(f"expected one analyzer content hash, observed {sorted(analyzer_hashes)}")
    manifest = {
        "schema": "bindcheck-zk.full-dev-run/v1",
        "phase": args.phase,
        "raw_task": args.raw_task,
        "scope": "exactly 56 DEV rows reconstructed without opening mixed source-corpus or recall-set ledgers",
        "run_id": run_id,
        "started_from_revision": run_command(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10)["stdout"].strip(),
        "analyzer_content_sha256": next(iter(analyzer_hashes)),
        "row_sources": ["feasibility/candidate-set.csv", "dataset/source-queries.json:historical_dev"],
        "records": records,
        "ledger_sha256": sha256(output_dir / "per-row-ledger.json"),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({
        "evidence": output_dir.relative_to(ROOT).as_posix(),
        "rows": len(ledger),
        "crashes": sum(item["crash"] for item in ledger),
        "rows_with_triples": sum(item["triples"] > 0 for item in ledger),
        "builds_ok": sum(item["builds_ok"] for item in ledger),
        "builds_failed": sum(item["builds_failed"] for item in ledger),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
