#!/usr/bin/env python3
"""Reproduce the D1P-30 five-target analysis and validation audit."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.static_analyzer_v1 import analyze  # noqa: E402
from bindcheck_d1.validation_v1 import validate  # noqa: E402


RAW = ROOT / "results/raw/D1P-30"
ANALYSES = RAW / "analyses"
VALIDATIONS = RAW / "validations"
INDEX = ROOT / "protocols/d1/d1p-30-validation-index.json"
CONSUMER_INDEX = ROOT / "protocols/d1/d1p-30-consumer-relations.json"
SIBLING = ROOT.parent / "BindCheck"

TARGETS = [
    {
        "label": "warptoad-pinned",
        "artifact": ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json",
        "source": ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol",
        "consumer_ir": ROOT / "results/raw/D1P-18/relation.json",
        "expected_rules": [],
        "negative_control": True,
    },
    {
        "label": "warptoad-m-dom",
        "artifact": ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json",
        "source": ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol",
        "consumer_ir": ROOT / "results/raw/D1P-18/relation.json",
        "expected_rules": ["R-BIND"],
        "negative_control": False,
    },
    {
        "label": "warptoad-m-src",
        "artifact": ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json",
        "source": ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol",
        "consumer_ir": ROOT / "results/raw/D1P-21B/m-src-relation.json",
        "expected_rules": ["R-ANCHOR"],
        "negative_control": False,
    },
    {
        "label": "payy-earlier",
        "artifact": SIBLING / "build/T22/scratch/work_a_agg_agg_earlier_/noir/target/agg_agg.json",
        "source": SIBLING / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol",
        "consumer_ir": None,
        "expected_rules": ["R-BIND", "R-EFFECT"],
        "negative_control": False,
    },
    {
        "label": "payy-check-added",
        "artifact": SIBLING / "build/T22/scratch/work_b_agg_agg_check_added_/noir/target/agg_agg.json",
        "source": SIBLING / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol",
        "consumer_ir": None,
        "expected_rules": [],
        "negative_control": True,
    },
]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    started = time.monotonic()
    analysis_records = []
    validation_records = []
    input_paths = {
        INDEX,
        CONSUMER_INDEX,
        ROOT / "bin/bindcheck",
        ROOT / "src/bindcheck_d1/cli.py",
        ROOT / "src/bindcheck_d1/static_analyzer_v1.py",
        ROOT / "src/bindcheck_d1/validation_v1.py",
        ROOT / "tests/test_bindcheck_v1.py",
        Path(__file__).resolve(),
    }
    for target in TARGETS:
        for key in ("artifact", "source", "consumer_ir"):
            if target[key] is not None:
                input_paths.add(target[key])
        result = analyze(target["artifact"], target["source"], target["consumer_ir"], target["label"])
        observed = [warning["rule"] for warning in result["warnings"]]
        if observed != target["expected_rules"]:
            raise SystemExit(f"{target['label']}: expected {target['expected_rules']}, observed {observed}")
        output = ANALYSES / f"{target['label']}.json"
        write_json(output, result)
        analysis_records.append({
            "target": target["label"], "warnings": observed,
            "runtime_seconds": result["runtime_seconds"],
            "negative_control": target["negative_control"], "result": file_record(output),
        })
        for warning in result["warnings"]:
            validation_output = VALIDATIONS / f"{target['label']}-{warning['id']}.json"
            selector = str(output) + (f"#{warning['id']}" if len(result["warnings"]) > 1 else "")
            validation = validate(selector, INDEX, ROOT)
            write_json(validation_output, validation)
            if validation["status"] != "PASS":
                raise SystemExit(f"{target['label']} {warning['id']}: validation {validation['status']}")
            validation_records.append({
                "target": target["label"], "warning": warning["id"], "rule": warning["rule"],
                "highest_evidence_level": validation["highest_evidence_level"],
                "fresh_execution": validation["route"]["fresh_execution"],
                "manual_steps": validation["manual_steps"], "result": file_record(validation_output),
            })

    controls = [record for record in analysis_records if record["negative_control"]]
    summary = {
        "schema": "bindcheck.d1p30.run-summary/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "d1p21c": {"status": "SKIPPED", "reason": "no process or result namespace existed at D1P-30 start"},
        "analyses": analysis_records,
        "validations": validation_records,
        "negative_controls": {
            "count": len(controls),
            "false_warnings": sum(len(record["warnings"]) for record in controls),
            "targets": [record["target"] for record in controls],
        },
        "wall_seconds": round(time.monotonic() - started, 6),
    }
    write_json(RAW / "run-summary.json", summary)

    output_paths = sorted(path for path in RAW.rglob("*") if path.is_file()
                          and path.name != "artifact-manifest.json")
    manifest = {
        "schema": "bindcheck.d1p30.artifact-manifest/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": [file_record(path) for path in sorted(input_paths)],
        "outputs": [file_record(path) for path in output_paths],
        "notes": [
            "Payy input artifacts live in the adjacent BindCheck evidence workspace and are hash pinned here.",
            "A manifest hash records bytes, not source/build correspondence; correspondence comes from the cited prior manifests.",
            "D1P-12 through D1P-21 evidence is read only.",
        ],
    }
    write_json(RAW / "artifact-manifest.json", manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
