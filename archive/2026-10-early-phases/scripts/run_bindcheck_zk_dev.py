#!/usr/bin/env python3
"""Run bindcheck-zk and baseline adapters on the three declared DEV cases only.

This script intentionally does not open dataset/source-corpus.csv or
dataset/recall-set.csv.  Its target paths and revisions are fixed below.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "bindcheck-zk"
RAW_ROOT = ROOT / "results" / "raw" / "T23"

CASES = (
    {
        "id": "spsc",
        "path": "feasibility/work/v2/repos/NethermindEth__spsc",
        "revision": "6d07155ecf295e6d68936bf424557621d0c66456",
        "circuits": ["circuits/circom/joinsplit.circom"],
        "consumers": ["contracts/circom/src/SPSC.sol"],
        "expected_p1": "VERIFIED_WITHIN_SCOPE",
    },
    {
        "id": "racepass",
        "path": "feasibility/work/v2/repos/Servesh21__RacePass",
        "revision": "abd54b5c541ac9d26f938a6bdbd78545526249e5",
        "circuits": ["circuits/age_proof/age_check.circom", "circuits/kyc_proof/kyc_check.circom"],
        "consumers": ["contracts/passes/EventPass.sol"],
        "expected_p1": "VIOLATION",
    },
    {
        "id": "zkredential",
        "path": "feasibility/work/v2/repos/ethpanda-org__ETHShanghai-2025",
        "revision": "23917814522bac494150c7e99a123aa15a448155",
        "circuits": ["projects/ZKredential/packages/zk-proof-server/circuits/propertyfy_circuit.circom"],
        "consumers": ["projects/ZKredential/packages/zk-contracts/contracts/core/ComplianceGateway.sol"],
        "expected_p1": "VIOLATION",
    },
)

BASELINES = ("slither", "circomspect", "zkap", "picus")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv: list[str], *, cwd: pathlib.Path, timeout: float = 150.0) -> dict:
    started = time.monotonic()
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"},
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "exit_status": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    run_id = dt.datetime.now(dt.UTC).strftime("run-%Y%m%dT%H%M%SZ-") + str(os.getpid())
    output_dir = RAW_ROOT / run_id
    output_dir.mkdir(parents=True)
    records: list[dict] = []
    summaries: list[dict] = []
    for case in CASES:
        repository = ROOT / case["path"]
        revision_record = command(["git", "rev-parse", "HEAD"], cwd=repository, timeout=10)
        revision = revision_record["stdout"].strip()
        if revision_record["exit_status"] != 0 or revision != case["revision"]:
            raise SystemExit(f"{case['id']}: expected revision {case['revision']}, observed {revision!r}")
        common: list[str] = []
        for circuit in case["circuits"]:
            common.extend(["--circuit", circuit])
        for consumer in case["consumers"]:
            common.extend(["--consumer", consumer])
        jobs = [("bindcheck", [str(CLI), "analyze", str(repository), *common])]
        jobs.extend(
            (
                baseline,
                [str(CLI), "baseline", baseline, str(repository), "--timeout", "120", *common],
            )
            for baseline in BASELINES
        )
        for tool, argv in jobs:
            record = command(argv, cwd=ROOT)
            result_path = output_dir / f"{case['id']}--{tool}.json"
            result_path.write_text(record["stdout"], encoding="utf-8")
            try:
                payload = json.loads(record["stdout"])
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{case['id']} {tool}: non-JSON output: {exc}") from exc
            records.append({
                "case": case["id"],
                "tool": tool,
                "revision": revision,
                "argv": argv,
                "exit_status": record["exit_status"],
                "elapsed_seconds": record["elapsed_seconds"],
                "stderr": record["stderr"],
                "result": result_path.relative_to(ROOT).as_posix(),
                "result_sha256": sha256(result_path),
            })
            summaries.append({
                "case": case["id"],
                "tool": tool,
                "run_status": payload.get("run", {}).get("status"),
                "p1": payload.get("patterns", {}).get("P1", {}).get("verdict"),
                "p1_reasons": payload.get("patterns", {}).get("P1", {}).get("reasons", []),
                "coverage": payload.get("coverage", {}),
            })
            if tool == "bindcheck" and summaries[-1]["p1"] != case["expected_p1"]:
                raise SystemExit(
                    f"{case['id']}: expected P1 {case['expected_p1']}, observed {summaries[-1]['p1']}"
                )
    manifest = {
        "schema": "bindcheck-zk.dev-run/v1",
        "scope": "three fixed DEV cases only; no EVAL or recall rows opened",
        "run_id": run_id,
        "started_from_revision": command(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10)["stdout"].strip(),
        "records": records,
        "summaries": summaries,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": output_dir.relative_to(ROOT).as_posix(),
        "result_files": len(records),
        "bindcheck_p1": {item["case"]: item["p1"] for item in summaries if item["tool"] == "bindcheck"},
        "baseline_status": {
            f"{item['case']}:{item['tool']}": item["run_status"]
            for item in summaries if item["tool"] != "bindcheck"
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
