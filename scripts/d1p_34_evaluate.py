#!/usr/bin/env python3
"""Build compiler-AST facts and run the D1P-34 BindCheck v1.1 evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.frontends.solidity_ast_v1_1 import extract  # noqa: E402
from bindcheck_d1.static_analyzer_v1 import analyze, load_producer  # noqa: E402


RAW = ROOT / "results/raw/D1P-34"
ASTS = RAW / "compiler-asts"
IRS = RAW / "consumer-relations"
ANALYSES = RAW / "analyses"
XBM = ROOT / "results/raw/X-BM"
BENCH = ROOT / "benchmarks/binding-mutants"
SIBLING = ROOT.parent / "BindCheck"
SOLC = Path("/Users/imranpollob/.svm/0.8.20/solc-0.8.20")
SKELETON = XBM / "build/PY-S01"
PAYY_ARTIFACT = SIBLING / "tools/cases/payy-c4d2c90/noir/target/agg_agg.json"
PAYY_CHECK_ARTIFACT = SIBLING / "tools/cases/payy-history/noir/target/agg_agg.json"
PAYY_BASE_SOURCE = BENCH / "baselines/RollupV1.sol"
PAYY_CHECK_SOURCE = SIBLING / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol"
WT_ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
WT_SOURCE = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol"
WT_RELATION = ROOT / "results/raw/D1P-18/relation.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def build_consumer_ir(label: str, source: Path, public_leaves: list[dict[str, Any]]) -> dict[str, Any]:
    started = time.monotonic()
    ASTS.mkdir(parents=True, exist_ok=True)
    IRS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="d1p34-solc-") as temporary:
        workspace = Path(temporary)
        shutil.copytree(SKELETON, workspace, dirs_exist_ok=True)
        entry = workspace / "contracts/rollup3/RollupV1.sol"
        shutil.copy2(source, entry)
        command = [
            str(SOLC), "--base-path", str(workspace), "--include-path",
            str(workspace / "node_modules"), "@openzeppelin/contracts-upgradeable/=stubs/",
            "--combined-json", "ast", str(entry),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    log = {
        "argv": command, "returncode": completed.returncode,
        "stderr": completed.stderr, "runtime_seconds": round(time.monotonic() - started, 6),
    }
    write_json(RAW / f"logs/solc-{label}.json", log)
    if completed.returncode:
        raise RuntimeError(f"{label}: solc AST extraction failed: {completed.stderr[-1000:]}")
    combined_path = ASTS / f"{label}.json"
    combined_path.write_text(completed.stdout)
    source_key = "contracts/rollup3/RollupV1.sol"
    relation = extract(combined_path, source_key, source, public_leaves)
    relation_path = IRS / f"{label}.json"
    write_json(relation_path, relation)
    return {"label": label, "source": file_record(source), "ast": file_record(combined_path),
            "relation": file_record(relation_path), "solc": file_record(SOLC),
            "runtime_seconds": log["runtime_seconds"]}


def prepare_payy_relations() -> dict[str, Path]:
    public_leaves = load_producer(PAYY_ARTIFACT)["public_leaves"]
    sources = {"payy-baseline": PAYY_BASE_SOURCE, "payy-check-added": PAYY_CHECK_SOURCE}
    for index in range(1, 6):
        sources[f"PY-S{index:02d}"] = XBM / f"mutants/PY-S{index:02d}/RollupV1.sol"
    records = []
    relations = {}
    for label, source in sources.items():
        records.append(build_consumer_ir(label, source, public_leaves))
        relations[label] = IRS / f"{label}.json"
    write_json(RAW / "consumer-extraction.json", {
        "schema": "bindcheck.d1p34.consumer-extraction/v1",
        "generated_at_utc": utc_now(), "public_count": len(public_leaves),
        "records": records,
    })
    return relations


def target_specs(payy_relations: dict[str, Path]) -> list[dict[str, Any]]:
    specs = []
    for index in range(1, 10):
        label = f"WT-C{index:02d}"
        specs.append({"label": label, "kind": "mutant", "app": "WarpToad",
                      "artifact": XBM / f"build/{label}/circuits/withdraw/target/withdraw.json",
                      "source": WT_SOURCE, "relation": WT_RELATION})
    for index in range(1, 10):
        label = f"WT-S{index:02d}"
        relation = ROOT / f"results/raw/D1P-31/consumer-relations/{label}/relation.json"
        specs.append({"label": label, "kind": "mutant", "app": "WarpToad",
                      "artifact": WT_ARTIFACT, "source": XBM / f"mutants/{label}/WarpToadCore.sol",
                      "relation": relation if relation.is_file() else None})
    for index in range(1, 8):
        label = f"PY-C{index:02d}"
        specs.append({"label": label, "kind": "mutant", "app": "Payy",
                      "artifact": XBM / f"build/{label}/noir/target/agg_agg.json",
                      "source": PAYY_BASE_SOURCE, "relation": payy_relations["payy-baseline"]})
    for index in range(1, 6):
        label = f"PY-S{index:02d}"
        specs.append({"label": label, "kind": "mutant", "app": "Payy",
                      "artifact": PAYY_ARTIFACT, "source": XBM / f"mutants/{label}/RollupV1.sol",
                      "relation": payy_relations[label]})
    specs.extend([
        {"label": "warptoad-pinned", "kind": "D1P-30 target", "app": "WarpToad",
         "artifact": WT_ARTIFACT, "source": WT_SOURCE, "relation": WT_RELATION},
        {"label": "warptoad-m-dom", "kind": "D1P-30 target", "app": "WarpToad",
         "artifact": ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json",
         "source": WT_SOURCE, "relation": WT_RELATION},
        {"label": "warptoad-m-src", "kind": "D1P-30 target", "app": "WarpToad",
         "artifact": WT_ARTIFACT,
         "source": ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol",
         "relation": ROOT / "results/raw/D1P-21B/m-src-relation.json"},
        {"label": "payy-earlier", "kind": "D1P-30 target", "app": "Payy",
         "artifact": PAYY_ARTIFACT, "source": PAYY_BASE_SOURCE,
         "relation": payy_relations["payy-baseline"]},
        {"label": "payy-check-added", "kind": "D1P-30 target", "app": "Payy",
         "artifact": PAYY_CHECK_ARTIFACT, "source": PAYY_CHECK_SOURCE,
         "relation": payy_relations["payy-check-added"]},
    ])
    return specs


def main() -> int:
    if not SOLC.is_file():
        raise SystemExit(f"missing pinned compiler: {SOLC}")
    payy_relations = prepare_payy_relations()
    records = []
    for spec in target_specs(payy_relations):
        relation = spec["relation"]
        record = {"target": spec["label"], "kind": spec["kind"], "app": spec["app"],
                  "artifact": file_record(spec["artifact"]), "source": file_record(spec["source"])}
        if relation is None:
            record.update({"status": "UNSUPPORTED", "reason": "CHECKED_CONSUMER_AST_UNAVAILABLE",
                           "warnings": [], "runtime_seconds": 0.0})
        else:
            try:
                result = analyze(spec["artifact"], spec["source"], relation, spec["label"])
                output = ANALYSES / f"{spec['label']}.json"
                write_json(output, result)
                record.update({"status": "PASS", "relation": file_record(relation),
                               "analysis": file_record(output),
                               "warnings": [{"id": item["id"], "rule": item["rule"],
                                             "location": item["location"], "evidence": item["evidence"]}
                                            for item in result["warnings"]],
                               "runtime_seconds": result["runtime_seconds"]})
            except Exception as exc:
                record.update({"status": "UNSUPPORTED", "reason": f"{type(exc).__name__}:{exc}",
                               "warnings": [], "runtime_seconds": 0.0})
        records.append(record)
        print(spec["label"], record["status"], [item["rule"] for item in record["warnings"]])
    run = {"schema": "bindcheck.d1p34.analysis-run/v1", "generated_at_utc": utc_now(),
           "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                   text=True).strip(),
           "targets": records,
           "counts": {"requested": len(records), "completed": sum(r["status"] == "PASS" for r in records),
                      "unsupported": sum(r["status"] == "UNSUPPORTED" for r in records),
                      "warnings": sum(len(r["warnings"]) for r in records)}}
    write_json(RAW / "analysis-run.json", run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
