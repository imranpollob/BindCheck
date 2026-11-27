#!/usr/bin/env python3
"""D1P-42 bounded extent audit over synthetic, Payy and benchmark inputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from bindcheck_d1.frontends.recursive_public_mapping_v1 import build as build_mapping  # noqa: E402
from bindcheck_d1.frontends.solidity_ast_v1_1 import extract  # noqa: E402
from bindcheck_d1.static_analyzer_v1 import analyze, load_producer  # noqa: E402
from scripts.d1p_40_correctness_audit import benchmark_specs  # noqa: E402


FIXTURES = ROOT / "tests/d1/fixtures/d1p42"
NARGO = Path(os.environ.get(
    "BINDCHECK_NARGO_BETA22",
    ROOT / "results/raw/D1P-35/tools/noir-1.0.0-beta.22/nargo",
))
SOLC = Path(os.environ.get(
    "BINDCHECK_SOLC_0_8_29",
    "/Users/imranpollob/.solc-select/artifacts/solc-0.8.29/solc-0.8.29",
))
PAYY = Path(os.environ.get("BINDCHECK_PAYY_ROOT", ROOT.parent / "BindCheck"))
COMMANDS: list[dict[str, Any]] = []


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path, base: Path | None = None) -> dict[str, Any]:
    return {"path": str(path.relative_to(base) if base else path),
            "bytes": path.stat().st_size, "sha256": sha256(path)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(name: str, argv: list[str], *, cwd: Path, logs: Path,
        expected: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{name}.stdout").write_text(completed.stdout)
    (logs / f"{name}.stderr").write_text(completed.stderr)
    COMMANDS.append({
        "name": name, "argv": argv, "cwd": str(cwd), "exit_status": completed.returncode,
        "runtime_seconds": round(time.monotonic() - started, 6),
        "stdout_sha256": sha256(logs / f"{name}.stdout"),
        "stderr_sha256": sha256(logs / f"{name}.stderr"),
    })
    if completed.returncode not in expected:
        raise RuntimeError(f"{name} exit {completed.returncode}: {completed.stderr[-1000:]}")
    return completed


def compile_synthetic(raw: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    workspace = raw / "synthetic/workspaces"
    logs = raw / "logs"
    artifacts: dict[str, Path] = {}
    for name in ("bound_all", "bound_prefix", "max_fee_bound", "max_fee_unbound"):
        target = workspace / name
        shutil.copytree(FIXTURES / "noir" / name, target)
        run(f"nargo-compile-{name}", [str(NARGO), "compile", "--program-dir", str(target)],
            cwd=ROOT, logs=logs)
        artifacts[name] = next((target / "target").glob("*.json"))

    asts: dict[str, Path] = {}
    for name in ("ConsumerAll", "ConsumerLimited"):
        source = FIXTURES / "solidity" / f"{name}.sol"
        completed = run(f"solc-{name}", [str(SOLC), "--combined-json", "ast", str(source)],
                        cwd=ROOT, logs=logs)
        ast = raw / f"synthetic/{name}.ast.json"
        ast.write_text(completed.stdout)
        asts[name] = ast
    return artifacts, asts


def execute_synthetic(raw: Path, artifacts: dict[str, Path]) -> list[dict[str, Any]]:
    cases = [
        ("bound-all-match", "bound_all", 0,
         'values = ["1", "2", "3", "4"]\nactive_count = 2\nexpected = ["1", "2", "3", "4"]\n'),
        ("bound-all-tail-change", "bound_all", 1,
         'values = ["1", "2", "9", "10"]\nactive_count = 2\nexpected = ["1", "2", "3", "4"]\n'),
        ("bound-prefix-tail-change", "bound_prefix", 0,
         'values = ["1", "2", "9", "10"]\nactive_count = 2\nexpected = ["1", "2", "3", "4"]\n'),
        ("bound-prefix-active-change", "bound_prefix", 1,
         'values = ["1", "2", "9", "10"]\nactive_count = 4\nexpected = ["1", "2", "3", "4"]\n'),
        ("max-fee-bound-over", "max_fee_bound", 1, 'amount = "10"\nmax_fee = "11"\n'),
        ("max-fee-unbound-over", "max_fee_unbound", 0, 'amount = "10"\nmax_fee = "11"\n'),
    ]
    rows = []
    for name, fixture, expected_exit, prover in cases:
        workspace = artifacts[fixture].parents[1]
        prover_name = name.replace("-", "_")
        (workspace / f"{prover_name}.toml").write_text(prover)
        completed = run(name, [str(NARGO), "execute", "-p", prover_name], cwd=workspace,
                        logs=raw / "logs", expected={expected_exit})
        rows.append({"id": name, "fixture": fixture, "expected_exit": expected_exit,
                     "observed_exit": completed.returncode})
    return rows


def synthetic_analyses(raw: Path, artifacts: dict[str, Path],
                       asts: dict[str, Path]) -> dict[str, Any]:
    producer_sources = {name: FIXTURES / "noir" / name / "src/main.nr"
                        for name in ("bound_all", "bound_prefix")}
    all_leaves = load_producer(artifacts["bound_all"], producer_sources["bound_all"])["public_leaves"]
    relations = {}
    for label in ("ConsumerAll", "ConsumerLimited"):
        source = FIXTURES / "solidity" / f"{label}.sol"
        combined = json.loads(asts[label].read_text())
        source_key = next(key for key in combined["sources"] if key.endswith(f"{label}.sol"))
        relation = extract(asts[label], source_key, source, all_leaves)
        relation_path = raw / f"synthetic/{label}.relation.json"
        write_json(relation_path, relation)
        relations[label] = relation_path
    pairs = [
        ("bound-all-consumer-all", "bound_all", "ConsumerAll", False),
        ("bound-prefix-consumer-limited", "bound_prefix", "ConsumerLimited", False),
        ("bound-prefix-consumer-all", "bound_prefix", "ConsumerAll", True),
    ]
    rows = []
    for case_id, producer, consumer, expected_warning in pairs:
        source = FIXTURES / "solidity" / f"{consumer}.sol"
        result = analyze(artifacts[producer], source, relations[consumer], case_id,
                         producer_source=producer_sources[producer])
        output = raw / f"synthetic/{case_id}.analysis.json"
        write_json(output, result)
        extent = [item for item in result["warnings"] if item["rule"] == "R-EXTENT"]
        if bool(extent) != expected_warning:
            raise AssertionError(f"{case_id}: expected R-EXTENT={expected_warning}, got {extent}")
        rows.append({"id": case_id, "expected_r_extent": expected_warning,
                     "observed_r_extent": bool(extent),
                     "warning_rules": [item["rule"] for item in result["warnings"]],
                     "analysis": record(output, raw)})
    return {"pairs": rows, "relations": {key: record(value, raw) for key, value in relations.items()}}


def payy_inputs(raw: Path, revision: str) -> dict[str, Path]:
    settings = {
        "earlier": ("payy-c4d2c90", "src-c4d2c90", "payy-baseline.json",
                    ROOT / "benchmarks/binding-mutants/baselines/RollupV1.sol"),
        "check-added": ("payy-history", "src-dcd5d96", "payy-check-added.json",
                        PAYY / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol"),
    }
    case, bridge_case, ast_name, consumer = settings[revision]
    source_root = PAYY / f"tools/cases/{case}"
    originals = {
        "producer_artifact": source_root / "noir/target/agg_agg.json",
        "producer_source": source_root / "noir/agg_agg/src/main.nr",
        "bridge_artifact": PAYY / f"build/T09/{bridge_case}/noir/target/agg_final.json",
        "consumer_source": consumer,
        "consumer_ast": ROOT / f"results/raw/D1P-34/compiler-asts/{ast_name}",
    }
    copied = {}
    destination = raw / f"payy/{revision}/inputs"
    destination.mkdir(parents=True, exist_ok=True)
    for role, source in originals.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        target = destination / f"{role}{source.suffix}"
        shutil.copy2(source, target)
        if sha256(target) != sha256(source):
            raise AssertionError(f"copy hash mismatch: {source}")
        copied[role] = target
    write_json(destination / "manifest.json", {
        "revision": revision,
        "originals": {role: record(path) for role, path in originals.items()},
        "copies": {role: record(path, raw) for role, path in copied.items()},
    })
    return copied


def payy_analyses(raw: Path) -> dict[str, Any]:
    rows = []
    for revision, expected_extent in (("earlier", True), ("check-added", False)):
        inputs = payy_inputs(raw, revision)
        certificate = build_mapping(inputs["producer_artifact"], inputs["bridge_artifact"])
        certificate_path = raw / f"payy/{revision}/mapping-certificate.json"
        write_json(certificate_path, certificate)
        producer = load_producer(inputs["producer_artifact"], inputs["producer_source"])
        relation = extract(inputs["consumer_ast"], "contracts/rollup3/RollupV1.sol",
                           inputs["consumer_source"], producer["public_leaves"], certificate)
        relation_path = raw / f"payy/{revision}/consumer-relation.json"
        write_json(relation_path, relation)
        result = analyze(inputs["producer_artifact"], inputs["consumer_source"], relation_path,
                         f"payy-{revision}", producer_source=inputs["producer_source"],
                         mapping_bridge=inputs["bridge_artifact"])
        analysis_path = raw / f"payy/{revision}/analysis.json"
        write_json(analysis_path, result)
        extent = [item for item in result["warnings"] if item["rule"] == "R-EXTENT"]
        if bool(extent) != expected_extent:
            raise AssertionError(f"Payy {revision}: unexpected R-EXTENT set")
        rows.append({
            "revision": revision, "expected_r_extent": expected_extent,
            "warning_rules": [item["rule"] for item in result["warnings"]],
            "mapping": {"producer_words": certificate["inner_public_count"],
                        "consumer_words": certificate["consumer_public_count"],
                        "configuration_words": len(certificate["configuration_prefix"]),
                        "mapped_words": len(certificate["mapping"]),
                        "checked_identities": certificate["checked_polynomial_identities"]},
            "extent_evidence": extent[0]["evidence"] if extent else None,
            "certificate": record(certificate_path, raw), "relation": record(relation_path, raw),
            "analysis": record(analysis_path, raw),
        })
    return {"targets": rows}


def warptoad_reconciliation() -> dict[str, Any]:
    pinned_path = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
    mutant_path = ROOT / "results/raw/X-BM/build/WT-C02/circuits/withdraw/target/withdraw.json"
    pinned = next(item for item in load_producer(pinned_path)["public_leaves"]
                  if item["path"] == "max_fee")
    mutant = next(item for item in load_producer(mutant_path)["public_leaves"]
                  if item["path"] == "max_fee")
    if pinned["occurrence_count"] != 3 or mutant["occurrence_count"] != 0:
        raise AssertionError("WT-C02 max_fee occurrence differential changed")
    return {
        "classification": "not a bug",
        "reason": "The pinned integer comparison has three proof-enforced and three Brillig inventory occurrences; WT-C02 removes the comparison and all six occurrences. Acceptance of max_fee=0 satisfies the pinned max_fee<=amount condition and does not refute the differential.",
        "pinned": {"artifact": record(pinned_path), "leaf": pinned},
        "WT-C02": {"artifact": record(mutant_path), "leaf": mutant},
    }


def rerun_benchmark(raw: Path) -> dict[str, Any]:
    prior = json.loads((ROOT / "results/raw/D1P-34/adjudication.json").read_text())
    prior_targets = {item["target"]: item for item in prior["targets"]}
    rows = []
    for spec in benchmark_specs():
        row = {"target": spec["target"], "app": spec["app"]}
        if spec["relation"] is None:
            row.update({"analysis_status": "UNSUPPORTED",
                        "reason": "EXACT_RECURSIVE_MAPPING_CERTIFICATE_UNAVAILABLE",
                        "classification": "UNSUPPORTED", "warnings": []})
        else:
            try:
                result = analyze(spec["artifact"], spec["source"], spec["relation"], spec["target"])
                output = raw / f"benchmark/analyses/{spec['target']}.json"
                write_json(output, result)
                classification = prior_targets[spec["target"]]["classification"]
                if classification == "DETECTED" and not result["warnings"]:
                    classification = "MISS"
                row.update({"analysis_status": "PASS", "classification": classification,
                            "warnings": [{"rule": item["rule"], "location": item["location"],
                                          "evidence": item["evidence"]}
                                         for item in result["warnings"]],
                            "analysis": record(output, raw)})
            except Exception as error:
                row.update({"analysis_status": "UNSUPPORTED", "classification": "UNSUPPORTED",
                            "reason": f"{type(error).__name__}:{error}", "warnings": []})
        rows.append(row)
    counts = {"targets": len(rows),
              "detected": sum(row["classification"] == "DETECTED" for row in rows),
              "unsupported": sum(row["classification"] == "UNSUPPORTED" for row in rows),
              "misses": sum(row["classification"] == "MISS" for row in rows),
              "warning_objects": sum(len(row["warnings"]) for row in rows)}
    return {"counts": counts, "targets": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.output.resolve()
    if raw.exists():
        raise SystemExit(f"refusing to overwrite evidence: {raw}")
    if not NARGO.is_file() or not SOLC.is_file():
        raise SystemExit(f"missing pinned tools: nargo={NARGO.is_file()} solc={SOLC.is_file()}")
    raw.mkdir(parents=True)
    expected = json.loads((FIXTURES / "expected-outcomes.json").read_text())
    artifacts, asts = compile_synthetic(raw)
    synthetic = synthetic_analyses(raw, artifacts, asts)
    synthetic["execution_controls"] = execute_synthetic(raw, artifacts)
    payy = payy_analyses(raw)
    warptoad = warptoad_reconciliation()
    benchmark = rerun_benchmark(raw)
    write_json(raw / "synthetic-results.json", synthetic)
    write_json(raw / "payy-results.json", payy)
    write_json(raw / "warptoad-reconciliation.json", warptoad)
    write_json(raw / "benchmark-rerun.json", benchmark)
    run("nargo-version", [str(NARGO), "--version"], cwd=ROOT, logs=raw / "logs")
    run("solc-version", [str(SOLC), "--version"], cwd=ROOT, logs=raw / "logs")
    ledger = {
        "schema": "bindcheck.d1p42.run-ledger/v1", "generated_at_utc": now(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "commands": COMMANDS,
        "inputs": {"expected_outcomes": record(FIXTURES / "expected-outcomes.json"),
                   "facts_interface": record(ROOT / "protocols/d1/d1p-42-extent-facts-interface.json"),
                   "nargo": record(NARGO), "solc": record(SOLC)},
        "outputs": {name: record(raw / name, raw) for name in
                    ("synthetic-results.json", "payy-results.json",
                     "warptoad-reconciliation.json", "benchmark-rerun.json")},
        "expected_case_count": len(expected["cases"]),
    }
    write_json(raw / "run-ledger.json", ledger)
    print(json.dumps({"output": str(raw), "synthetic_pairs": synthetic["pairs"],
                      "payy": [{"revision": row["revision"], "warning_rules": row["warning_rules"]}
                               for row in payy["targets"]],
                      "warptoad": warptoad["classification"],
                      "benchmark": benchmark["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
