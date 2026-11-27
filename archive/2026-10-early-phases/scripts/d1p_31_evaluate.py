#!/usr/bin/env python3
"""Run the frozen BindCheck v1 benchmark evaluation for D1P-31.

The analyzer and validator are invoked through the public CLI.  This runner
does not import or alter either rule engine.  WarpToad consumer relations are
compiled/extracted before analysis with the already-pinned D1P-18 route;
extractor rejection is preserved as unsupported and the CLI then runs its
conservative source profile so every requested target still has an output.
"""

from __future__ import annotations

import argparse
import difflib
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-31"
XBM = ROOT / "results/raw/X-BM"
BENCH = ROOT / "benchmarks/binding-mutants"
ANALYSES = RAW / "analyses"
LOGS = RAW / "logs"
RELATIONS = RAW / "consumer-relations"
VALIDATIONS = RAW / "validations"
SIBLING = ROOT.parent / "BindCheck"

PINNED_WT_ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
PINNED_WT_SOURCE = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol"
PINNED_WT_RELATION = ROOT / "results/raw/D1P-18/relation.json"
PAYY_BASE_ARTIFACT = SIBLING / "tools/cases/payy-c4d2c90/noir/target/agg_agg.json"
PAYY_BASE_SOURCE = BENCH / "baselines/RollupV1.sol"

BUILD_INFO = ROOT / "results/raw/D1P-12R/workspace/source/backend/artifacts/build-info/solc-0_8_29-a52609323fd0bce65aec2ea493681a10c5c96cfa.json"
COMPILER_OUTPUT = BUILD_INFO.with_suffix(".output.json")
SOLCJS = ROOT / "results/raw/D1P-18/tooling/node_modules/solc/soljson.js"
VALIDATION_INDEX = ROOT / "protocols/d1/d1p-31-validation-index.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def run(command: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "argv": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "runtime_seconds": round(time.monotonic() - started, 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def target_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for index in range(1, 10):
        mutant = f"WT-C{index:02d}"
        specs.append({
            "label": mutant,
            "kind": "mutant",
            "app": "WarpToad",
            "side": "circuit",
            "artifact": XBM / f"build/{mutant}/circuits/withdraw/target/withdraw.json",
            "source": PINNED_WT_SOURCE,
            "consumer_ir": PINNED_WT_RELATION,
        })
    for index in range(1, 10):
        mutant = f"WT-S{index:02d}"
        specs.append({
            "label": mutant,
            "kind": "mutant",
            "app": "WarpToad",
            "side": "consumer",
            "artifact": PINNED_WT_ARTIFACT,
            "source": XBM / f"mutants/{mutant}/WarpToadCore.sol",
            "consumer_ir": RELATIONS / mutant / "relation.json",
        })
    for index in range(1, 8):
        mutant = f"PY-C{index:02d}"
        specs.append({
            "label": mutant,
            "kind": "mutant",
            "app": "Payy",
            "side": "circuit",
            "artifact": XBM / f"build/{mutant}/noir/target/agg_agg.json",
            "source": PAYY_BASE_SOURCE,
            "consumer_ir": None,
        })
    for index in range(1, 6):
        mutant = f"PY-S{index:02d}"
        specs.append({
            "label": mutant,
            "kind": "mutant",
            "app": "Payy",
            "side": "consumer",
            "artifact": PAYY_BASE_ARTIFACT,
            "source": XBM / f"mutants/{mutant}/RollupV1.sol",
            "consumer_ir": None,
        })

    d1p30 = [
        ("warptoad-pinned", PINNED_WT_ARTIFACT, PINNED_WT_SOURCE, PINNED_WT_RELATION),
        ("warptoad-m-dom", ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json", PINNED_WT_SOURCE, PINNED_WT_RELATION),
        ("warptoad-m-src", PINNED_WT_ARTIFACT, ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol", ROOT / "results/raw/D1P-21B/m-src-relation.json"),
        ("payy-earlier", SIBLING / "build/T22/scratch/work_a_agg_agg_earlier_/noir/target/agg_agg.json", SIBLING / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol", None),
        ("payy-check-added", SIBLING / "build/T22/scratch/work_b_agg_agg_check_added_/noir/target/agg_agg.json", SIBLING / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol", None),
    ]
    for label, artifact, source, relation in d1p30:
        specs.append({
            "label": label,
            "kind": "D1P-30 target",
            "app": "WarpToad" if label.startswith("warptoad") else "Payy",
            "side": "combined",
            "artifact": artifact,
            "source": source,
            "consumer_ir": relation,
        })
    return specs


def prepare_relations() -> dict[str, Any]:
    """Compile and extract each WarpToad source mutant independently."""
    sys.path.insert(0, str(ROOT / "prototypes/d1p16"))
    from extract_relation import Extractor  # type: ignore
    from source_mutation_tests import compile_variant  # type: ignore

    original_meta = json.loads(BUILD_INFO.read_text())
    records = []
    for index in range(1, 10):
        mutant = f"WT-S{index:02d}"
        target = RELATIONS / mutant
        target.mkdir(parents=True, exist_ok=True)
        source_path = XBM / f"mutants/{mutant}/WarpToadCore.sol"
        source = source_path.read_text()
        started = time.monotonic()
        record: dict[str, Any] = {
            "target": mutant,
            "source": file_record(source_path),
            "started_at_utc": utc_now(),
        }
        transient: list[Path] = []
        try:
            meta, output, copied_source, compile_record = compile_variant(
                SOLCJS, original_meta, mutant.lower(), source, target
            )
            transient = [meta, output, target / "standard-input.json", target / "standard-output.json"]
            relation = Extractor(
                meta, output, copied_source, expected_source_sha256=sha256(source_path)
            ).extract()
            relation_path = target / "relation.json"
            write_json(relation_path, relation)
            record.update({
                "status": "PASS",
                "relation": file_record(relation_path),
                "compile_record": file_record(target / "compile.json"),
                "success_paths": relation["summary"]["success_paths"],
                "revert_paths": relation["summary"]["revert_paths"],
            })
        except Exception as exc:  # exact fail-closed extractor reason is evidence
            record.update({
                "status": "UNSUPPORTED",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        finally:
            for path in transient:
                if path.is_file():
                    path.unlink()
            record["runtime_seconds"] = round(time.monotonic() - started, 6)
        records.append(record)
    result = {
        "schema": "bindcheck.d1p31.consumer-extraction/v1",
        "generated_at_utc": utc_now(),
        "compiler": file_record(SOLCJS),
        "original_build_info": file_record(BUILD_INFO),
        "original_compiler_output": file_record(COMPILER_OUTPUT),
        "records": records,
    }
    write_json(RAW / "consumer-extraction.json", result)
    return result


def analyze_all() -> dict[str, Any]:
    extraction_path = RAW / "consumer-extraction.json"
    extraction = json.loads(extraction_path.read_text()) if extraction_path.is_file() else {"records": []}
    extraction_by_target = {row["target"]: row for row in extraction["records"]}
    records = []
    for spec in target_specs():
        output = ANALYSES / f"{spec['label']}.json"
        command = [
            str(ROOT / "bin/bindcheck"), "analyze", str(spec["artifact"]),
            str(spec["source"]), "--label", spec["label"], "--json", str(output),
        ]
        relation = spec["consumer_ir"]
        frontend_status = "supported"
        frontend_reason = None
        if relation is not None and relation.is_file():
            command.extend(["--consumer-ir", str(relation)])
        elif spec["label"].startswith("WT-S"):
            frontend_status = "unsupported"
            extraction_record = extraction_by_target.get(spec["label"], {})
            frontend_reason = extraction_record.get("error", "checked consumer relation unavailable")
        result = run(command)
        log_path = LOGS / f"analyze-{spec['label']}.json"
        write_json(log_path, result)
        record = {
            "target": spec["label"],
            "kind": spec["kind"],
            "app": spec["app"],
            "side": spec["side"],
            "artifact": file_record(spec["artifact"]),
            "source": file_record(spec["source"]),
            "consumer_ir": file_record(relation) if relation is not None and relation.is_file() else None,
            "frontend_status": frontend_status,
            "frontend_reason": frontend_reason,
            "command_record": file_record(log_path),
            "returncode": result["returncode"],
        }
        if output.is_file():
            analysis = json.loads(output.read_text())
            record.update({
                "analysis": file_record(output),
                "rules": [warning["rule"] for warning in analysis["warnings"]],
                "warning_count": analysis["warning_count"],
                "runtime_seconds": analysis["runtime_seconds"],
                "manual_inputs": analysis["manual_inputs"],
                "limitations": analysis["limitations"],
            })
        else:
            record.update({"rules": [], "warning_count": 0, "runtime_seconds": result["runtime_seconds"]})
        records.append(record)
    summary = {
        "schema": "bindcheck.d1p31.analysis-run/v1",
        "generated_at_utc": utc_now(),
        "targets": records,
        "counts": {
            "requested": len(records),
            "completed": sum(row["returncode"] == 0 for row in records),
            "mutants": sum(row["kind"] == "mutant" for row in records),
            "d1p30_targets": sum(row["kind"] == "D1P-30 target" for row in records),
            "warnings": sum(row["warning_count"] for row in records),
            "unsupported_frontends": sum(row["frontend_status"] == "unsupported" for row in records),
        },
    }
    write_json(RAW / "analysis-run.json", summary)
    return summary


def validate_mutants() -> dict[str, Any]:
    """Attempt every mutant warning once through the frozen validation CLI.

    The 45-minute proving budget is a cap.  Content-addressed route rejection
    consumes no proving budget and remains E1/UNKNOWN rather than a miss.
    """
    benchmark_artifact = json.loads((XBM / "build/WT-C03/circuits/withdraw/target/withdraw.json").read_text())
    proved_artifact = json.loads((ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json").read_text())
    benchmark_source = (XBM / "mutants/WT-S01/WarpToadCore.sol").read_text()
    proved_source = (ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol").read_text()

    def executable_source(value: str) -> str:
        return "\n".join(
            prefix.rstrip()
            for line in value.splitlines()
            if (prefix := line.split("//", 1)[0].rstrip())
        )

    changed = [row for row in difflib.ndiff(benchmark_source.splitlines(), proved_source.splitlines())
               if row.startswith(("- ", "+ "))]
    correspondence = {
        "schema": "bindcheck.d1p31.validation-correspondence/v1",
        "generated_at_utc": utc_now(),
        "wt_c03": {
            "benchmark_artifact": file_record(XBM / "build/WT-C03/circuits/withdraw/target/withdraw.json"),
            "proved_artifact": file_record(ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json"),
            "bytecode_equal": benchmark_artifact["bytecode"] == proved_artifact["bytecode"],
            "abi_equal": benchmark_artifact["abi"] == proved_artifact["abi"],
            "noir_version_equal": benchmark_artifact["noir_version"] == proved_artifact["noir_version"],
        },
        "wt_s01": {
            "benchmark_source": file_record(XBM / "mutants/WT-S01/WarpToadCore.sol"),
            "proved_source": file_record(ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol"),
            "executable_source_equal": executable_source(benchmark_source) == executable_source(proved_source),
            "diff_is_comment_and_eof_only": all(
                not row[2:].strip() or row[2:].lstrip().startswith("//") for row in changed
            ),
            "changed_lines": changed,
        },
    }
    write_json(RAW / "validation-correspondence.json", correspondence)

    started = time.monotonic()
    budget_seconds = 45 * 60
    records = []
    benchmark_manifest = json.loads((BENCH / "manifest.json").read_text())
    mutants = [spec for spec in target_specs() if spec["kind"] == "mutant"]
    mutants.sort(key=lambda spec: (benchmark_manifest["mutants"][spec["label"]]["operator"], spec["label"]))
    for spec in mutants:
        operator = benchmark_manifest["mutants"][spec["label"]]["operator"]
        analysis_path = ANALYSES / f"{spec['label']}.json"
        if not analysis_path.is_file():
            continue
        analysis = json.loads(analysis_path.read_text())
        for warning in analysis["warnings"]:
            if time.monotonic() - started >= budget_seconds:
                break
            output = VALIDATIONS / f"{spec['label']}-{warning['id']}.json"
            selector = f"{analysis_path}#{warning['id']}"
            command = [
                str(ROOT / "bin/bindcheck"), "validate", selector,
                "--validation-index", str(VALIDATION_INDEX), "--json", str(output),
            ]
            result = run(command)
            log_path = LOGS / f"validate-{spec['label']}-{warning['id']}.json"
            write_json(log_path, result)
            validation = json.loads(output.read_text()) if output.is_file() else None
            records.append({
                "target": spec["label"],
                "operator_class": operator,
                "warning": warning["id"],
                "rule": warning["rule"],
                "returncode": result["returncode"],
                "runtime_seconds": result["runtime_seconds"],
                "validation": file_record(output) if output.is_file() else None,
                "command_record": file_record(log_path),
                "status": validation.get("status") if validation else "ERROR",
                "highest_evidence_level": validation.get("highest_evidence_level", "E1") if validation else "E1",
                "manual_steps": validation.get("manual_steps") if validation else None,
                "reason": (
                    validation.get("reason")
                    or ("no content-addressed validation route"
                        if validation.get("status") == "NO_VALIDATION_ROUTE"
                        else validation.get("scope_note"))
                ) if validation else result["stderr"].strip(),
            })
        if time.monotonic() - started >= budget_seconds:
            break
    summary = {
        "schema": "bindcheck.d1p31.validation-run/v1",
        "generated_at_utc": utc_now(),
        "budget_seconds": budget_seconds,
        "wall_seconds": round(time.monotonic() - started, 6),
        "attempted": len(records),
        "operator_class_order": list(dict.fromkeys(row["operator_class"] for row in records)),
        "records": records,
        "note": "A missing content-addressed validation route is UNKNOWN at E1 and consumes no proving time.",
    }
    write_json(RAW / "validation-run.json", summary)
    return summary


def manifest() -> dict[str, Any]:
    paths = sorted(path for path in RAW.rglob("*") if path.is_file() and path.name != "artifact-manifest.json")
    frozen_inputs = [
        ROOT / "bin/bindcheck",
        ROOT / "src/bindcheck_d1/cli.py",
        ROOT / "src/bindcheck_d1/static_analyzer_v1.py",
        ROOT / "src/bindcheck_d1/validation_v1.py",
        BENCH / "manifest.json",
        *sorted((BENCH / "mutants").glob("*.md")),
    ]
    deliverables = [
        ROOT / "README.md",
        ROOT / "docs/project-status.md",
        ROOT / "docs/research-contract.md",
        ROOT / "docs/history/research-contract-2026-10-27.md",
        ROOT / "protocols/d1/d1p-31-validation-index.json",
        ROOT / "reports/D1P-31.md",
        ROOT / "scripts/d1p_31_evaluate.py",
        ROOT / "scripts/d1p_31_adjudicate.py",
    ]
    value = {
        "schema": "bindcheck.d1p31.artifact-manifest/v1",
        "generated_at_utc": utc_now(),
        "frozen_inputs": [file_record(path) for path in frozen_inputs],
        "deliverables": [file_record(path) for path in deliverables],
        "raw_evidence": [file_record(path) for path in paths],
        "notes": [
            "D1P-31 raw evidence is ignored and prior namespaces are read only.",
            "Manifest hashes establish byte identity, not source/build correspondence.",
            "Ground-truth markdown is used only by the later adjudication stage.",
        ],
    }
    write_json(RAW / "artifact-manifest.json", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "analyze", "validate", "manifest", "all"])
    args = parser.parse_args()
    if args.stage in {"prepare", "all"}:
        prepare_relations()
    if args.stage in {"analyze", "all"}:
        analyze_all()
    if args.stage in {"validate", "all"}:
        validate_mutants()
    if args.stage in {"manifest", "all"}:
        manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
