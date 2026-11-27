#!/usr/bin/env python3
"""Reproduce the D1P-40 extraction-correctness controls and benchmark rerun."""

from __future__ import annotations

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

from bindcheck_d1.frontends.solidity_ast_v1_1 import extract  # noqa: E402
from bindcheck_d1.static_analyzer_v1 import analyze, load_producer  # noqa: E402


RAW = ROOT / "results/raw/D1P-40/final-04"
FIXTURES = ROOT / "tests/d1/fixtures/d1p40"
NARGO = Path(os.environ.get(
    "BINDCHECK_NARGO_BETA22",
    ROOT / "results/raw/D1P-35/tools/noir-1.0.0-beta.22/nargo",
))
SOLC = Path(os.environ.get(
    "BINDCHECK_SOLC_0_8_29",
    "/Users/imranpollob/.solc-select/artifacts/solc-0.8.29/solc-0.8.29",
))
XBM = ROOT / "results/raw/X-BM"
PAYY_ROOT = Path(os.environ.get("BINDCHECK_PAYY_ROOT", ROOT.parent / "BindCheck"))
PAYY_EARLIER = PAYY_ROOT / "tools/cases/payy-c4d2c90/noir/target/agg_agg.json"
PAYY_CHECK = PAYY_ROOT / "tools/cases/payy-history/noir/target/agg_agg.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


COMMANDS: list[dict[str, Any]] = []


def run(label: str, argv: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    stdout_path = RAW / "logs" / f"{label}.stdout"
    stderr_path = RAW / "logs" / f"{label}.stderr"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    COMMANDS.append({
        "label": label, "argv": argv, "cwd": str(cwd), "returncode": completed.returncode,
        "runtime_seconds": round(time.monotonic() - started, 6),
        "stdout": file_record(stdout_path), "stderr": file_record(stderr_path),
    })
    if completed.returncode:
        raise RuntimeError(f"{label} failed with {completed.returncode}: {completed.stderr[-800:]}")
    return completed


def compile_noir() -> dict[str, Path]:
    artifacts = {}
    for case in ("memory_constant", "memory_dynamic", "memory_write_only", "nested_abi", "anchor"):
        workspace = RAW / "synthetic/noir" / case
        shutil.copytree(FIXTURES / "noir" / case, workspace)
        run(f"nargo-{case}", [str(NARGO), "compile", "--program-dir", str(workspace)])
        matches = list((workspace / "target").glob("*.json"))
        if len(matches) != 1:
            raise RuntimeError(f"{case}: expected one artifact, found {len(matches)}")
        artifacts[case] = matches[0]
    return artifacts


def compile_solidity() -> dict[str, tuple[Path, Path, str]]:
    records = {}
    for source in sorted((FIXTURES / "solidity").glob("*.sol")):
        relative = source.relative_to(ROOT)
        completed = run(f"solc-{source.stem}", [str(SOLC), "--combined-json", "ast", str(relative)])
        ast = RAW / "synthetic/solidity" / f"{source.stem}.json"
        ast.parent.mkdir(parents=True, exist_ok=True)
        ast.write_text(completed.stdout)
        records[source.stem] = (source, ast, str(relative))
    return records


def leaves(paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": path, "public_index": index} for index, path in enumerate(paths)]


def synthetic_checks(noir: dict[str, Path], solidity: dict[str, tuple[Path, Path, str]]) -> dict[str, Any]:
    constant = load_producer(noir["memory_constant"])
    dynamic = load_producer(noir["memory_dynamic"])
    write_only = load_producer(noir["memory_write_only"])
    nested = load_producer(noir["nested_abi"])
    anchor_producer = load_producer(noir["anchor"])

    dynamic_by_path = {item["path"]: item for item in dynamic["public_leaves"]}
    if {dynamic_by_path[name]["memory_dependency_status"] for name in ("left", "right")} != {
        "unresolved-dynamic"
    }:
        raise AssertionError("dynamic MemoryInit dependencies were not marked unresolved")
    write_by_path = {item["path"]: item for item in write_only["public_leaves"]}
    if write_by_path["value"]["occurrence_count"] != 0:
        raise AssertionError("write-only value was incorrectly counted as proof-enforced")
    constant_counts = {item["path"]: item["occurrence_count"] for item in constant["public_leaves"]}
    if constant_counts != {"left": 0, "right": 1, "expected": 1}:
        raise AssertionError(f"constant-index control mismatch: {constant_counts}")
    nested_paths = [item["path"] for item in nested["public_leaves"]]
    expected_nested = [
        "envelope.tag", "envelope.pair.values[0]", "envelope.pair.values[1]",
        "tail[0]", "tail[1]",
    ]
    if nested_paths != expected_nested:
        raise AssertionError(f"nested ABI order mismatch: {nested_paths}")

    relations: dict[str, dict[str, Any]] = {}
    relation_paths: dict[str, Path] = {}
    path_sets = {
        "NestedMapping": expected_nested,
        "Effects": ["items[0]", "items[1]", "items[2]"],
        "LoopBounds": ["items[0]", "items[1]", "items[2]", "items[3]"],
        "AnchorPositive": ["root"],
        "AnchorNegative": ["root"],
    }
    for name, paths in path_sets.items():
        source, ast, source_key = solidity[name]
        relation = extract(ast, source_key, source, leaves(paths))
        relation_path = RAW / "synthetic/relations" / f"{name}.json"
        write_json(relation_path, relation)
        relations[name] = relation
        relation_paths[name] = relation_path

    ambiguous_source, ambiguous_ast, ambiguous_key = solidity["AmbiguousPrefix"]
    try:
        extract(ambiguous_ast, ambiguous_key, ambiguous_source, leaves([
            "selector[0]", "selector[1]", "messages[0]", "messages[1]", "messages[2]",
        ]))
    except ValueError as exc:
        ambiguous_reason = str(exc)
    else:
        raise AssertionError("ambiguous selector prefix was accepted")
    if not ambiguous_reason.startswith("SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS"):
        raise AssertionError(ambiguous_reason)

    effects = relations["Effects"]["effects"]
    if [(item["kind"], item["words"]) for item in effects] != [
        ("storage-write", [0]), ("token-transfer", [1]),
    ]:
        raise AssertionError(f"effect classification mismatch: {effects}")
    loop_effects = relations["LoopBounds"]["effects"]
    if len(loop_effects) != 1 or loop_effects[0]["words"] != [0, 1]:
        raise AssertionError(f"loop bounds mismatch: {loop_effects}")
    if relations["AnchorPositive"]["anchor_words"][0]["must_be_in"] is not True:
        raise AssertionError("positive anchor was not admitted")
    if relations["AnchorNegative"]["anchor_words"][0]["must_be_in"] is not False:
        raise AssertionError("unguarded anchor was not recorded")

    positive = analyze(noir["anchor"], solidity["AnchorPositive"][0],
                       relation_paths["AnchorPositive"], "anchor-positive")
    negative = analyze(noir["anchor"], solidity["AnchorNegative"][0],
                       relation_paths["AnchorNegative"], "anchor-negative")
    if positive["warnings"]:
        raise AssertionError(f"positive anchor warned: {positive['warnings']}")
    if [item["rule"] for item in negative["warnings"]] != ["R-ANCHOR"]:
        raise AssertionError(f"negative anchor rules: {negative['warnings']}")

    payy = load_producer(PAYY_EARLIER)
    payy_unresolved = [
        item["path"] for item in payy["public_leaves"]
        if item["occurrence_count"] == 0
        and item["memory_dependency_status"] == "unresolved-dynamic"
    ]
    if payy_unresolved != [f"messages[{index}]" for index in range(1, 1000)]:
        raise AssertionError("Payy unresolved MemoryInit set differs from messages[1..999]")

    return {
        "schema": "bindcheck.d1p40.synthetic-correctness/v1",
        "generated_at_utc": now(),
        "noir_artifacts": {name: file_record(path) for name, path in noir.items()},
        "solidity_sources": {name: file_record(item[0]) for name, item in solidity.items()},
        "checks": [
            {"item": "memory-constant", "classification": "not a bug",
             "expected": {"left": 0, "right": 1, "expected": 1}, "observed": constant_counts},
            {"item": "memory-dynamic", "classification": "confirmed bug",
             "expected": "UNKNOWN unless address constraints are proved",
             "observed": {name: dynamic_by_path[name]["memory_dependency_status"]
                          for name in ("left", "right")}},
            {"item": "memory-write-only", "classification": "not a bug",
             "expected": "value unused", "observed_occurrences": write_by_path["value"]["occurrence_count"]},
            {"item": "nested-ABI-order", "classification": "not a bug",
             "expected": expected_nested, "observed": nested_paths},
            {"item": "selector-prefix", "classification": "confirmed bug",
             "expected": "fail closed without an exact producer/consumer mapping", "observed": ambiguous_reason},
            {"item": "storage-and-token-effects", "classification": "confirmed bug",
             "expected": [["storage-write", [0]], ["token-transfer", [1]]],
             "observed": [[item["kind"], item["words"], item["location"]] for item in effects]},
            {"item": "bounded-loop-effects", "classification": "confirmed bug",
             "expected_words": [0, 1], "observed_words": loop_effects[0]["words"]},
            {"item": "R-ANCHOR-reachability", "classification": "confirmed bug",
             "positive_rules": [], "negative_rules": [item["rule"] for item in negative["warnings"]]},
            {"item": "Payy-memory-tail", "classification": "unclear",
             "expected": "requires address/path proof", "unresolved_count": len(payy_unresolved),
             "first": payy_unresolved[0], "last": payy_unresolved[-1]},
        ],
        "relations": {name: file_record(path) for name, path in relation_paths.items()},
        "anchor_analyses": {"positive": positive, "negative": negative},
    }


def benchmark_specs() -> list[dict[str, Any]]:
    wt_artifact = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
    wt_source = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol"
    wt_relation = ROOT / "results/raw/D1P-18/relation.json"
    specs = []
    for index in range(1, 10):
        label = f"WT-C{index:02d}"
        specs.append({"target": label, "app": "WarpToad",
                      "artifact": XBM / f"build/{label}/circuits/withdraw/target/withdraw.json",
                      "source": wt_source, "relation": wt_relation})
    for index in range(1, 10):
        label = f"WT-S{index:02d}"
        relation = ROOT / f"results/raw/D1P-31/consumer-relations/{label}/relation.json"
        specs.append({"target": label, "app": "WarpToad", "artifact": wt_artifact,
                      "source": XBM / f"mutants/{label}/WarpToadCore.sol",
                      "relation": relation if relation.is_file() else None})
    for index in range(1, 8):
        label = f"PY-C{index:02d}"
        specs.append({"target": label, "app": "Payy",
                      "artifact": XBM / f"build/{label}/noir/target/agg_agg.json",
                      "source": ROOT / "benchmarks/binding-mutants/baselines/RollupV1.sol",
                      "relation": None})
    for index in range(1, 6):
        label = f"PY-S{index:02d}"
        specs.append({"target": label, "app": "Payy", "artifact": PAYY_EARLIER,
                      "source": XBM / f"mutants/{label}/RollupV1.sol", "relation": None})
    return specs


def rerun_benchmark() -> dict[str, Any]:
    prior = json.loads((ROOT / "results/raw/D1P-34/adjudication.json").read_text())
    prior_targets = {item["target"]: item for item in prior["targets"]}
    records = []
    for spec in benchmark_specs():
        record = {"target": spec["target"], "app": spec["app"],
                  "artifact": file_record(spec["artifact"]), "source": file_record(spec["source"])}
        if spec["relation"] is None:
            reason = ("SOLIDITY_PUBLIC_INPUT_MAPPING_AMBIGUOUS" if spec["app"] == "Payy"
                      else "CHECKED_CONSUMER_AST_UNAVAILABLE")
            record.update({"analysis_status": "UNSUPPORTED",
                           "reason": reason,
                           "warnings": [], "classification": "UNSUPPORTED"})
        else:
            try:
                result = analyze(spec["artifact"], spec["source"], spec["relation"], spec["target"])
                output = RAW / "benchmark/analyses" / f"{spec['target']}.json"
                write_json(output, result)
                old = prior_targets[spec["target"]]
                classification = old["classification"]
                if classification == "DETECTED" and not result["warnings"]:
                    classification = "MISS"
                record.update({"analysis_status": "PASS", "analysis": file_record(output),
                               "warnings": [{"id": item["id"], "rule": item["rule"],
                                             "location": item["location"], "evidence": item["evidence"]}
                                            for item in result["warnings"]],
                               "classification": classification})
            except Exception as exc:
                record.update({"analysis_status": "UNSUPPORTED",
                               "reason": f"{type(exc).__name__}:{exc}", "warnings": [],
                               "classification": "UNSUPPORTED"})
        records.append(record)
    counts = {
        "targets": len(records),
        "detected": sum(item["classification"] == "DETECTED" for item in records),
        "unsupported": sum(item["classification"] == "UNSUPPORTED" for item in records),
        "misses": sum(item["classification"] == "MISS" for item in records),
        "warning_objects": sum(len(item["warnings"]) for item in records),
    }
    return {
        "schema": "bindcheck.d1p40.benchmark-rerun/v1", "generated_at_utc": now(),
        "comparison": {"D1P-34": prior["totals"], "D1P-40": counts}, "counts": counts,
        "targets": records,
    }


def main() -> int:
    if RAW.exists():
        raise SystemExit(f"refusing to overwrite preserved evidence: {RAW}")
    if not NARGO.is_file() or not SOLC.is_file():
        raise SystemExit(f"missing compiler: nargo={NARGO.is_file()} solc={SOLC.is_file()}")
    RAW.mkdir(parents=True)
    noir = compile_noir()
    solidity = compile_solidity()
    synthetic = synthetic_checks(noir, solidity)
    benchmark = rerun_benchmark()
    write_json(RAW / "synthetic-results.json", synthetic)
    write_json(RAW / "benchmark-rerun.json", benchmark)
    versions = {
        "python": sys.version, "nargo": run("nargo-version", [str(NARGO), "--version"]).stdout,
        "solc": run("solc-version", [str(SOLC), "--version"]).stdout,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    write_json(RAW / "run-ledger.json", {
        "schema": "bindcheck.d1p40.run-ledger/v1", "generated_at_utc": now(),
        "versions": versions, "commands": COMMANDS,
        "inputs": {"nargo": file_record(NARGO), "solc": file_record(SOLC),
                   "effect_models": file_record(ROOT / "protocols/d1/bindcheck-v1.3-effect-models.json")},
        "outputs": {"synthetic": file_record(RAW / "synthetic-results.json"),
                    "benchmark": file_record(RAW / "benchmark-rerun.json")},
    })
    print(json.dumps({"synthetic_checks": len(synthetic["checks"]),
                      "benchmark": benchmark["counts"],
                      "raw": str(RAW)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
