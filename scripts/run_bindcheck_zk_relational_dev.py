#!/usr/bin/env python3
"""Run the relational analyzer on the sealed 56-row DEV population only.

The row reconstruction and acquisition helpers intentionally come from the
T24/T25 DEV runner.  This script never opens a source-corpus ledger, recall
expectation, recall set, EVAL row, or private deployment ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from run_bindcheck_zk_full_dev import acquire, checkout_path, dev_rows, run_command, validate_existing


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "bindcheck-zk"
RAW_ROOT = ROOT / "results" / "raw" / "relational"
DIMENSIONS = ("EXTENT", "MASK", "REPRESENTATION", "MULTIPLICITY_SCOPE", "ROLE_IDENTITY")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(row: dict[str, str], payload: dict[str, Any], command: dict[str, Any]) -> dict[str, Any]:
    relational = payload.get("relational", {})
    dimensions = relational.get("dimensions", {})
    flags: list[dict[str, Any]] = []
    for pair_index, pair in enumerate(relational.get("pairs", [])):
        for dimension in DIMENSIONS:
            finding = pair.get("dimensions", {}).get(dimension, {})
            if finding.get("verdict") == "VIOLATION":
                flags.append({
                    "pair_index": pair_index,
                    "dimension": dimension,
                    "reason": finding.get("reason"),
                    "circuit": pair.get("circuit", {}).get("path"),
                    "consumer": pair.get("consumer", {}).get("path"),
                    "function": pair.get("consumer", {}).get("function"),
                })
    return {
        "id": row["id"],
        "repository": row["repository"],
        "commit": row["commit"],
        "variant": row["variant"],
        "command_exit_status": command.get("exit_status"),
        "command_timed_out": command.get("timed_out"),
        "fatal_reason": relational.get("run", {}).get("fatal_reason"),
        "runtime_seconds": relational.get("run", {}).get("elapsed_seconds"),
        "circom_entry_sources": relational.get("coverage", {}).get("circom_entry_sources", 0),
        "compiled_relations": relational.get("coverage", {}).get("compiled_relations", 0),
        "paired_paths": relational.get("coverage", {}).get("paired_paths", 0),
        "dimensions": {
            dimension: {
                "verdict": dimensions.get(dimension, {}).get("verdict", "UNKNOWN"),
                "applicability": dimensions.get(dimension, {}).get("applicability", "UNKNOWN"),
                "results": dimensions.get(dimension, {}).get("results", 0),
                "applicable_results": dimensions.get(dimension, {}).get("applicable_results", 0),
                "decided_results": dimensions.get(dimension, {}).get("decided_results", 0),
                "violation_results": dimensions.get(dimension, {}).get("violation_results", 0),
                "reasons": dimensions.get(dimension, {}).get("reasons", []),
            }
            for dimension in DIMENSIONS
        },
        "flags": flags,
    }


def analyze_row(row: dict[str, str], output_dir: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any]]:
    repository = checkout_path(row)
    argv = [str(CLI), "analyze", str(repository), "--relational"]
    command = run_command(argv, cwd=ROOT, timeout=330, output_limit=None)
    result_path = output_dir / f"{row['id']}--result.json"
    result_path.write_text(command.get("stdout", ""), encoding="utf-8")
    try:
        payload = json.loads(command.get("stdout", ""))
    except json.JSONDecodeError as exc:
        payload = {"relational": {"run": {"fatal_reason": "NON_JSON_OUTPUT"}}}
        command["json_error"] = str(exc)
    command.update({
        "id": row["id"],
        "repository": row["repository"],
        "commit": row["commit"],
        "result": result_path.relative_to(ROOT).as_posix(),
        "result_sha256": sha256(result_path),
        "analyzer_content_sha256": payload.get("tool", {}).get("content_sha256"),
    })
    return command, summarize(row, payload, command)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--fetch-jobs", type=int, default=6)
    parser.add_argument("--analyze-jobs", type=int, default=3)
    args = parser.parse_args()

    rows = dev_rows()
    run_id = dt.datetime.now(dt.UTC).strftime("dev-%Y%m%dT%H%M%SZ-") + str(os.getpid())
    output_dir = RAW_ROOT / run_id
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
    (output_dir / "acquisition.json").write_text(
        json.dumps(acquisitions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    unavailable = [item for item in acquisitions if item["status"] != "ready"]
    if unavailable:
        raise SystemExit(f"{len(unavailable)} DEV rows unavailable; evidence: {output_dir}")

    records: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.analyze_jobs) as pool:
        futures = {pool.submit(analyze_row, row, output_dir): row for row in rows}
        for future in as_completed(futures):
            record, summary = future.result()
            records.append(record)
            ledger.append(summary)
            print(
                f"ANALYZE\t{summary['id']}\tcompiled={summary['compiled_relations']}\t"
                f"pairs={summary['paired_paths']}\tflags={len(summary['flags'])}\t"
                f"runtime={summary['runtime_seconds']}",
                flush=True,
            )
    records.sort(key=lambda item: item["id"])
    ledger.sort(key=lambda item: item["id"])
    ledger_path = output_dir / "per-row-ledger.json"
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    analyzer_hashes = {item["analyzer_content_sha256"] for item in records if item.get("analyzer_content_sha256")}
    if len(analyzer_hashes) != 1:
        raise ValueError(f"expected one analyzer hash, observed {sorted(analyzer_hashes)}")

    circom = pathlib.Path(os.environ.get("BINDCHECK_CIRCOM", ""))
    version = subprocess.run(
        [str(circom), "--version"], text=True, capture_output=True, check=False
    ) if circom.is_file() else None
    manifest = {
        "schema": "bindcheck-zk.relational-dev-run/v1",
        "scope": "exactly 56 DEV rows reconstructed without source-corpus, recall-set, recall-expectation, or EVAL access",
        "run_id": run_id,
        "git_revision": run_command(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10)["stdout"].strip(),
        "analyzer_content_sha256": next(iter(analyzer_hashes)),
        "row_sources": ["feasibility/candidate-set.csv", "dataset/source-queries.json:historical_dev"],
        "command_template": [str(CLI), "analyze", "<DEV_CHECKOUT>", "--relational"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "circom_path": str(circom) if circom.is_file() else None,
            "circom_sha256": sha256(circom) if circom.is_file() else None,
            "circom_version": version.stdout.strip() if version else None,
        },
        "records": records,
        "ledger_sha256": sha256(ledger_path),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": output_dir.relative_to(ROOT).as_posix(),
        "rows": len(ledger),
        "fatal_rows": sum(item["fatal_reason"] is not None for item in ledger),
        "compiled_relations": sum(item["compiled_relations"] for item in ledger),
        "paired_paths": sum(item["paired_paths"] for item in ledger),
        "flags": sum(len(item["flags"]) for item in ledger),
        "manifest_sha256": sha256(manifest_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
