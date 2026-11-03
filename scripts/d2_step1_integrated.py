#!/usr/bin/env python3
"""Run the frozen D2-01 integrated development reconciliation.

The runner adds no detection rules.  It executes the existing D1P-42 and
D1P-43 development protocols, invokes the integrated public analysis surface
over the full mutant benchmark and exact Payy pair, and writes a versioned
case table.  Historical and current measurements remain separate.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from bindcheck_d1.integrated_analyzer_v1 import (  # noqa: E402
    analyze_integrated,
    warning_stable_id,
)
from scripts.d1p_40_correctness_audit import benchmark_specs  # noqa: E402
from scripts.d1p_43_role_ablation_preliminary import producer_inputs  # noqa: E402
from scripts.d2_foundation import prepare_run_manifest, verify_seal  # noqa: E402


SCHEMA = "bindcheck.d2.integrated-development-results/v1"
PROTOCOL = ROOT / "protocols/d2/d2-01-integrated-development-v1.json"
BOUNDARY = ROOT / "protocols/d2/development-boundary-v1.json"
ASSOCIATIONS = ROOT / "protocols/d2/d2-01-benchmark-associations-v1.json"
EXTERNAL_INPUTS = ROOT / "protocols/d2/d2-01-external-inputs-v1.json"
BENCHMARK_MANIFEST = ROOT / "benchmarks/binding-mutants/manifest.json"
D1P41_PROTOCOL = ROOT / "protocols/d1/d1p-41-ablation-preliminary.json"
D1P43_PROTOCOL = ROOT / "protocols/d1/d1p-43-role-binding-preliminary.json"
D1P42_EXPECTED = ROOT / "tests/d1/fixtures/d1p42/expected-outcomes.json"
D1P42_FACTS = ROOT / "protocols/d1/d1p-42-extent-facts-interface.json"
NARGO = ROOT / "results/raw/D1P-35/tools/noir-1.0.0-beta.22/nargo"
SOLC = Path("/Users/imranpollob/.solc-select/artifacts/solc-0.8.29/solc-0.8.29")
PAYY_ROOT = ROOT.parent / "BindCheck"
FROZEN_ENVIRONMENT_PATHS = {
    "BINDCHECK_NARGO_BETA22": NARGO,
    "BINDCHECK_SOLC_0_8_29": SOLC,
    "BINDCHECK_PAYY_ROOT": PAYY_ROOT,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def external_file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def run_command(
    name: str,
    argv: list[str],
    *,
    output: Path,
    timeout: int,
) -> dict[str, Any]:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update({
        name: str(path.resolve()) for name, path in FROZEN_ENVIRONMENT_PATHS.items()
    })
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env={**environment, "PYTHONPATH": str(ROOT / "src")},
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    stdout_path = output / "logs" / f"{name}.stdout"
    stderr_path = output / "logs" / f"{name}.stderr"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)
    record = {
        "name": name,
        "argv": argv,
        "status": "TIMEOUT" if timed_out else "PASS" if process.returncode == 0 else "FAIL",
        "exit_code": process.returncode,
        "wall_seconds": round(time.monotonic() - started, 6),
        "timeout_seconds": timeout,
        "stdout": file_record(stdout_path),
        "stderr": file_record(stderr_path),
    }
    return record


def verify_environment_paths() -> dict[str, Any]:
    mismatches = []
    observed = {}
    for name, expected_path in FROZEN_ENVIRONMENT_PATHS.items():
        expected = expected_path.resolve()
        raw = os.environ.get(name)
        observed[name] = {
            "declared": raw,
            "effective": str(expected),
        }
        if raw is not None and Path(raw).expanduser().resolve() != expected:
            mismatches.append({
                "variable": name,
                "declared": raw,
                "required": str(expected),
            })
    return {
        "schema": "bindcheck.d2.environment-path-verification/v1",
        "status": "PASS" if not mismatches else "FAIL",
        "paths": observed,
        "mismatches": mismatches,
    }


def verify_external_inputs(manifest: Path = EXTERNAL_INPUTS) -> dict[str, Any]:
    data = json.loads(manifest.read_text())
    if data.get("schema") != "bindcheck.d2.external-input-manifest/v1":
        raise ValueError(f"unsupported external-input manifest: {data.get('schema')!r}")
    records: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for expected in data.get("files", []):
        raw = Path(expected["path"])
        path = raw if raw.is_absolute() else ROOT / raw
        path = path.resolve()
        key = str(path)
        if key in seen:
            mismatches.append({"path": expected["path"], "reason": "DUPLICATE_PATH"})
            continue
        seen.add(key)
        if not path.is_file() or path.is_symlink():
            mismatches.append({"path": expected["path"], "reason": "MISSING_OR_NOT_REGULAR"})
            continue
        observed = external_file_record(path)
        records.append({**observed, "declared_path": expected["path"], "role": expected["role"]})
        if (observed["sha256"], observed["size_bytes"]) != (
            expected["sha256"], expected["size_bytes"]
        ):
            mismatches.append({
                "path": expected["path"],
                "reason": "CONTENT_MISMATCH",
                "expected_sha256": expected["sha256"],
                "observed_sha256": observed["sha256"],
                "expected_size_bytes": expected["size_bytes"],
                "observed_size_bytes": observed["size_bytes"],
            })
    return {
        "schema": "bindcheck.d2.external-input-verification/v1",
        "manifest": file_record(manifest),
        "status": "PASS" if not mismatches else "FAIL",
        "checked_files": len(records),
        "files": records,
        "mismatches": mismatches,
    }


def _files_under(path: Path) -> set[Path]:
    if path.is_file():
        return {path.resolve()}
    return {
        candidate.resolve()
        for candidate in path.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
        and not any(part in {".git", "__pycache__"} for part in candidate.parts)
        and candidate.name not in {".DS_Store", "latest.json", "run-index.json"}
    }


def required_seal_paths() -> set[str]:
    """Return every in-checkout byte that can influence the D2-01 result."""
    required: set[Path] = set()
    for entry in (
        ROOT / "src/bindcheck_d1",
        ROOT / "scripts/d2_step1_integrated.py",
        ROOT / "scripts/d2_foundation.py",
        ROOT / "scripts/d1p_40_correctness_audit.py",
        ROOT / "scripts/d1p_42_extent_audit.py",
        ROOT / "scripts/d1p_43_role_ablation_preliminary.py",
        PROTOCOL,
        BOUNDARY,
        ASSOCIATIONS,
        EXTERNAL_INPUTS,
        BENCHMARK_MANIFEST,
        D1P41_PROTOCOL,
        D1P43_PROTOCOL,
        D1P42_EXPECTED,
        D1P42_FACTS,
        ROOT / "benchmarks/binding-mutants",
        ROOT / "tests/d1/fixtures/d1p42",
        ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json",
        ROOT / "results/raw/D1P-18/relation.json",
        ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol",
        ROOT / "results/raw/D1P-31/consumer-relations",
        ROOT / "results/raw/D1P-34/adjudication.json",
        ROOT / "results/raw/D1P-34/compiler-asts",
        ROOT / "results/raw/D1P-34/consumer-relations",
        NARGO,
        ROOT / "results/raw/X-BM/build",
        ROOT / "results/raw/X-BM/mutants",
    ):
        if not entry.exists():
            raise FileNotFoundError(f"required D2-01 input is absent: {entry}")
        required.update(_files_under(entry))
    return {relative(path) for path in required}


def verify_seal_coverage(manifest: Path) -> dict[str, Any]:
    data = json.loads(manifest.read_text())
    listed = [item["path"] for item in data.get("files", [])]
    required = required_seal_paths()
    missing = sorted(required.difference(listed))
    duplicates = sorted(path for path, count in Counter(listed).items() if count > 1)
    return {
        "schema": "bindcheck.d2.seal-coverage/v1",
        "status": "PASS" if not missing and not duplicates else "FAIL",
        "required_files": len(required),
        "sealed_files": len(listed),
        "missing": missing,
        "duplicates": duplicates,
    }


def remaining_timeout(deadline: float, cap: int) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("D2_GLOBAL_WALL_BUDGET_EXHAUSTED")
    return max(1, min(cap, int(remaining)))


def warning_indices(warning: dict[str, Any]) -> set[int]:
    evidence = warning.get("evidence", {})
    result: set[int] = set()
    if isinstance(evidence.get("public_index"), int):
        result.add(evidence["public_index"])
    result.update(
        value for value in evidence.get("public_indices", [])
        if isinstance(value, int)
    )
    return result


def association_candidates(
    warnings: list[dict[str, Any]], association: dict[str, Any]
) -> list[dict[str, Any]]:
    kinds = set(association.get("kinds", []))
    return [
        warning for warning in warnings
        if warning.get("rule") == association["rule"]
        and (
            not kinds
            or warning.get("evidence", {}).get("kind") in kinds
        )
    ]


def association_satisfied(
    warnings: list[dict[str, Any]], association: dict[str, Any]
) -> bool:
    candidates = association_candidates(warnings, association)
    if not candidates:
        return False
    expected_indices = set(association.get("public_indices", []))
    observed_indices: set[int] = set()
    for warning in candidates:
        observed_indices.update(warning_indices(warning))
    return expected_indices.issubset(observed_indices)


def matched_association_warnings(
    warnings: list[dict[str, Any]], associations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for association in associations:
        if not association_satisfied(warnings, association):
            continue
        for warning in association_candidates(warnings, association):
            key = warning.get("stable_id") or warning.get("id") or repr(warning)
            if key not in seen:
                seen.add(key)
                matched.append(warning)
    return matched


def run_integrated_benchmark(
    *,
    output: Path,
    static_benchmark: dict[str, Any],
    deadline: float,
) -> dict[str, Any]:
    static_rows = {row["target"]: row for row in static_benchmark["targets"]}
    association_ledger = json.loads(ASSOCIATIONS.read_text())
    frozen_targets = association_ledger["targets"]
    manifest = json.loads(BENCHMARK_MANIFEST.read_text())
    expected_targets = {spec["target"] for spec in benchmark_specs()}
    if set(static_rows) != expected_targets:
        raise ValueError("D2_STATIC_BENCHMARK_TARGET_SET_MISMATCH")
    if set(frozen_targets) != expected_targets:
        raise ValueError("D2_FROZEN_ASSOCIATION_TARGET_SET_MISMATCH")
    if set(manifest["mutants"]) != expected_targets:
        raise ValueError("D2_BENCHMARK_MANIFEST_TARGET_SET_MISMATCH")
    rows = []
    for spec in benchmark_specs():
        remaining_timeout(deadline, 1800)
        target = spec["target"]
        producer = producer_inputs(target)
        producer_source = producer[0] if producer else None
        support_sources = producer[1] if producer else []
        result = analyze_integrated(
            spec["artifact"],
            spec["source"],
            spec["relation"],
            target,
            producer_source=producer_source,
            producer_support_sources=support_sources,
            role_binding=True if producer is not None else None,
        )
        result_path = output / "integrated/benchmark" / f"{target}.json"
        write_json(result_path, result)
        frozen = frozen_targets[target]
        associations = frozen["required_associations"]
        matched = matched_association_warnings(result["warnings"], associations)
        all_associations_satisfied = bool(associations) and all(
            association_satisfied(result["warnings"], association)
            for association in associations
        )
        if result["support_status"] == "UNKNOWN":
            classification = "UNSUPPORTED"
        elif frozen["expected_outcome"] == "DETECTED" and all_associations_satisfied:
            classification = "DETECTED"
        elif frozen["expected_outcome"] == "UNKNOWN":
            classification = "PROTOCOL_MISMATCH"
        else:
            classification = "MISS"
        mutation = manifest["mutants"][target]
        rows.append({
            "target": target,
            "family": "WarpToad" if target.startswith("WT-") else "Payy",
            "classification": classification,
            "frozen_expected_outcome": frozen["expected_outcome"],
            "all_required_associations_satisfied": all_associations_satisfied,
            "support_status": result["support_status"],
            "support_reasons": [
                component.get("reason_code")
                for component in result["components"].values()
                if component["status"] == "UNKNOWN"
            ],
            "operator": mutation["operator"],
            "binding_broken": mutation["binding_broken"],
            "expected_effect": mutation["expected_effect"],
            "expected_associations": associations,
            "matched_warning_ids": [warning["id"] for warning in matched],
            "matched_stable_ids": [warning["stable_id"] for warning in matched],
            "all_warning_ids": [warning["id"] for warning in result["warnings"]],
            "all_stable_ids": [warning["stable_id"] for warning in result["warnings"]],
            "analysis": file_record(result_path),
        })
    counts = {
        "targets": len(rows),
        "detected": sum(row["classification"] == "DETECTED" for row in rows),
        "unsupported": sum(row["classification"] == "UNSUPPORTED" for row in rows),
        "misses": sum(
            row["classification"] in {"MISS", "PROTOCOL_MISMATCH"} for row in rows
        ),
        "warning_objects": sum(len(row["all_warning_ids"]) for row in rows),
        "associated_warning_objects": sum(len(row["matched_warning_ids"]) for row in rows),
    }
    return {"schema": "bindcheck.d2.integrated-benchmark/v1", "counts": counts, "targets": rows}


def run_integrated_payy(
    output: Path, d1p42: Path, *, deadline: float
) -> list[dict[str, Any]]:
    rows = []
    for revision, expected_extent in (("earlier", True), ("check-added", False)):
        remaining_timeout(deadline, 1800)
        base = d1p42 / "payy" / revision
        inputs = base / "inputs"
        result = analyze_integrated(
            inputs / "producer_artifact.json",
            inputs / "consumer_source.sol",
            base / "consumer-relation.json",
            f"payy-{revision}",
            producer_source=inputs / "producer_source.nr",
            mapping_bridge=inputs / "bridge_artifact.json",
            role_binding=False,
        )
        result_path = output / "integrated/payy" / f"{revision}.json"
        write_json(result_path, result)
        extent = [warning for warning in result["warnings"] if warning["rule"] == "R-EXTENT"]
        rows.append({
            "revision": revision,
            "expected_r_extent": expected_extent,
            "observed_r_extent": bool(extent),
            "matches_expected": bool(extent) == expected_extent,
            "r_extent_ids": [warning["id"] for warning in extent],
            "r_extent_stable_ids": [warning["stable_id"] for warning in extent],
            "all_warning_rules": [warning["rule"] for warning in result["warnings"]],
            "all_warning_ids": [warning["id"] for warning in result["warnings"]],
            "all_stable_ids": [warning["stable_id"] for warning in result["warnings"]],
            "other_warnings": [
                {
                    "rule": warning["rule"],
                    "legacy_id": warning["id"],
                    "stable_id": warning["stable_id"],
                }
                for warning in result["warnings"] if warning["rule"] != "R-EXTENT"
            ],
            "analysis": file_record(result_path),
        })
    return rows


def case_table(
    *,
    integrated_benchmark: dict[str, Any],
    ablation: dict[str, Any],
    payy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in integrated_benchmark["targets"]:
        rows.append({
            "dataset": "mutant-benchmark-current",
            "case": item["target"],
            "family": item["family"],
            "exposure": "EXPOSED_DEVELOPMENT",
            "version": SCHEMA,
            "policy": f"binding field: {item['binding_broken']}",
            "expected_defect": item["expected_effect"],
            "outcome": item["classification"],
            "warning_association": {
                "frozen_ledger": relative(ASSOCIATIONS),
                "expected": item["expected_associations"],
                "all_required_associations_satisfied": item[
                    "all_required_associations_satisfied"
                ],
                "matched_legacy_ids": item["matched_warning_ids"],
                "matched_stable_ids": item["matched_stable_ids"],
            },
            "evidence_grade": "E1" if item["classification"] == "DETECTED" else "E0",
            "research_verdict": "UNKNOWN",
            "raw_output_path": item["analysis"]["path"],
        })
    for item in ablation["ablation_examples"]:
        full = item["arms"]["full-bindcheck"]
        score = full["score"]
        related_ids = set(score["related_warning_ids"])
        if score["status"] == "UNKNOWN":
            outcome = "UNKNOWN"
        elif item.get("clean_control"):
            outcome = "CONTROL_NO_WARNING" if score["matches_expected_outcome"] else "CONTROL_MISMATCH"
        else:
            outcome = "DETECTED" if score["detection"] else "MISS"
        rows.append({
            "dataset": "d1p41-discriminating-rerun",
            "case": item["id"],
            "family": "Payy" if item["target"].startswith("PY-") else "WarpToad",
            "exposure": "EXPOSED_DEVELOPMENT",
            "version": ablation["schema"],
            "policy": item.get("intended_policy", "matching development control"),
            "expected_defect": item.get("expected_outcome_before_arms", "none; control"),
            "outcome": outcome,
            "warning_association": {
                "related_legacy_ids": score["related_warning_ids"],
                "related_stable_ids": [
                    warning_stable_id(warning) for warning in full.get("warnings", [])
                    if warning.get("id") in related_ids
                ],
                "irrelevant_legacy_ids": score["irrelevant_warning_ids"],
                "support_gate": full.get("support_gate"),
            },
            "evidence_grade": "E1" if outcome == "DETECTED" else "E0",
            "research_verdict": "UNKNOWN",
            "raw_output_path": relative(Path(ablation["_result_path"])),
        })
    for item in ablation["role_targets"]:
        outcome = (
            "UNKNOWN" if item["status"] == "UNKNOWN"
            else "DETECTED" if item.get("matches_expected_outcome", False)
            else "MISS"
        )
        association = {
            "rule": "R-ROLE",
            "kinds": item.get("expected_kinds", []),
            "public_indices": item.get("expected_public_indices", []),
        }
        matching_warnings = (
            association_candidates(item.get("warnings", []), association)
            if item.get("matches_expected_outcome", False)
            else []
        )
        rows.append({
            "dataset": "d1p43-role-target-rerun",
            "case": item["id"],
            "family": "Payy" if item["target"].startswith("PY-") else "WarpToad",
            "exposure": "EXPOSED_DEVELOPMENT",
            "version": ablation["schema"],
            "policy": item["intended_policy"],
            "expected_defect": item["expected_outcome_before_run"],
            "outcome": outcome,
            "warning_association": {
                "all_required_associations_satisfied": item.get(
                    "matches_expected_outcome", False
                ),
                "expected_kinds": item.get("expected_kinds", []),
                "expected_public_indices": item.get("expected_public_indices", []),
                "matching_legacy_ids": [warning["id"] for warning in matching_warnings],
                "matching_stable_ids": [
                    warning_stable_id(warning) for warning in matching_warnings
                ],
                "support_gate": item.get("support_gate"),
            },
            "evidence_grade": "E1" if outcome == "DETECTED" else "E0",
            "research_verdict": "UNKNOWN",
            "raw_output_path": relative(Path(ablation["_result_path"])),
        })
    for item in payy:
        earlier = item["revision"] == "earlier"
        outcome = (
            "DETECTED" if item["observed_r_extent"]
            else "REPAIR_CONTROL_NO_R_EXTENT" if not earlier
            else "MISS"
        )
        other_warnings = item.get("other_warnings", [])
        rows.append({
            "dataset": "payy-extent-pair",
            "case": f"payy-{item['revision']}",
            "family": "Payy",
            "exposure": "KNOWN_BUG_AND_REPAIR_DEVELOPMENT",
            "version": SCHEMA,
            "policy": "the consumer may rely only on message words that the proof binds",
            "expected_defect": (
                "consumer relies through messages_length beyond active_messages_count"
                if earlier else "repair binds every configured message word"
            ),
            "outcome": outcome,
            "warning_association": {
                "rule": "R-EXTENT",
                "matched_legacy_ids": item["r_extent_ids"],
                "matched_stable_ids": item["r_extent_stable_ids"],
                "all_warning_rules": item["all_warning_rules"],
                "all_warning_legacy_ids": item.get("all_warning_ids", []),
                "all_warning_stable_ids": item["all_stable_ids"],
                "other_warnings": other_warnings,
            },
            "evidence_grade": "E1" if item["all_stable_ids"] else "E0",
            "research_verdict": "UNKNOWN",
            "raw_output_path": item["analysis"]["path"],
        })
    return rows


def ablation_regression_check(ablation: dict[str, Any]) -> dict[str, Any]:
    frozen = json.loads(PROTOCOL.read_text())["frozen_ablation_vector"]
    examples = {item["id"]: item for item in ablation["ablation_examples"]}
    expected_example_ids = set(frozen["positive_case_ids"] + frozen["clean_control_ids"])
    mismatches: list[dict[str, Any]] = []
    if set(examples) != expected_example_ids:
        mismatches.append({
            "scope": "example-set",
            "expected": sorted(expected_example_ids),
            "observed": sorted(examples),
        })
    positive = set(frozen["positive_case_ids"])
    unknown = set(frozen["unknown_case_ids"])
    controls = set(frozen["clean_control_ids"])
    for arm, expectation in frozen["arms"].items():
        detected = {
            case_id for case_id in positive
            if case_id in examples
            and examples[case_id]["arms"][arm]["score"]["status"] == "SUPPORTED"
            and examples[case_id]["arms"][arm]["score"]["detection"] is True
        }
        observed_unknown = {
            case_id for case_id in positive
            if case_id in examples
            and examples[case_id]["arms"][arm]["score"]["status"] == "UNKNOWN"
        }
        matching_controls = {
            case_id for case_id in controls
            if case_id in examples
            and examples[case_id]["arms"][arm]["score"]["status"] == "SUPPORTED"
            and examples[case_id]["arms"][arm]["score"]["matches_expected_outcome"] is True
        }
        expected_detected = set(expectation["detected_case_ids"])
        if detected != expected_detected:
            mismatches.append({
                "scope": arm, "field": "detected_case_ids",
                "expected": sorted(expected_detected), "observed": sorted(detected),
            })
        if observed_unknown != unknown:
            mismatches.append({
                "scope": arm, "field": "unknown_case_ids",
                "expected": sorted(unknown), "observed": sorted(observed_unknown),
            })
        if matching_controls != controls:
            mismatches.append({
                "scope": arm, "field": "matching_clean_control_ids",
                "expected": sorted(controls), "observed": sorted(matching_controls),
            })
    role_targets = {item["id"]: item for item in ablation["role_targets"]}
    expected_role_ids = set(frozen["role_target_ids"])
    if set(role_targets) != expected_role_ids:
        mismatches.append({
            "scope": "role-target-set",
            "expected": sorted(expected_role_ids),
            "observed": sorted(role_targets),
        })
    for case_id, item in role_targets.items():
        if item["status"] == "UNKNOWN":
            recomputed = item.get("matches_expected_outcome") is True
        else:
            association = {
                "rule": "R-ROLE",
                "kinds": item.get("expected_kinds", []),
                "public_indices": item.get("expected_public_indices", []),
            }
            recomputed = association_satisfied(item.get("warnings", []), association)
        if not recomputed or item.get("matches_expected_outcome") is not True:
            mismatches.append({
                "scope": "role-target", "case": case_id,
                "field": "frozen_association", "observed": item,
            })
    return {
        "schema": "bindcheck.d2.ablation-regression-check/v1",
        "status": "PASS" if not mismatches else "FAIL",
        "mismatches": mismatches,
        "observed_aggregate": ablation["aggregate"],
    }


def reconciliation(
    *,
    static_benchmark: dict[str, Any],
    integrated_benchmark: dict[str, Any],
    ablation: dict[str, Any],
    payy: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "bindcheck.d2.evidence-reconciliation/v1",
        "current_development": {
            "static_only_d1p42": static_benchmark["counts"],
            "integrated_d2": integrated_benchmark["counts"],
            "interpretation": (
                "The integrated count may add only predeclared D1P-43 R-ROLE associations. "
                "It supersedes no historical report and remains exposed E1 development evidence."
            ),
        },
        "versioned_ablation": {
            "d1p41_historical": {
                "full": "6/8 supported positives",
                "unjoined_union": "6/8 supported positives",
                "status": "pre-correctness-audit preliminary experiment",
            },
            "d1p43_corrected_rerun": ablation["aggregate"],
            "interpretation": "Different versioned datasets/results; denominators are not combined.",
        },
        "payy": {
            "current_extent_rows": payy,
            "current_static_grade": "E1 for the earlier R-EXTENT warning",
            "preserved_validation": (
                "T15-T19 provide the historical real-proof and committed-effect chain for the "
                "known earlier message-tail mechanism; that E4 evidence is not newly produced "
                "by D2 and is not transferred to other warnings or mutants."
            ),
            "check_added": "repair control has no R-EXTENT; silence remains UNKNOWN, not VERIFIED_WITHIN_SCOPE",
        },
        "transfer_attempts": {
            "project_attempts": 12,
            "unique_projects": 8,
            "supported_analyses": 0,
            "warning_count": 0,
            "family_count": "UNKNOWN_NOT_ADJUDICATED",
            "basis": "D1P-33 four projects plus D1P-36 eight projects, four of which repeat D1P-33",
            "interpretation": "Repeated attempts are not independent families and unsupported is not a miss or safety evidence.",
        },
        "historical_validation_ledger": {
            "version": "BindCheck v1.1 / D1P-34 53-warning set",
            "grades": {"E4": 11, "E4-preserved": 1, "E3": 7, "E1+mock": 1, "E1": 33},
            "basis": "TE06 final corrected ledger; 11+1+7+1+33 = 53",
            "interpretation": (
                "These grades do not validate the current integrated warning set. "
                "E1+mock is not E2, and warning-object grades are not distinct-defect counts."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seal", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    seal = args.seal.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    protocol = json.loads(PROTOCOL.read_text())
    budget = protocol["resource_budget"]
    environment_verification = verify_environment_paths()
    if environment_verification["status"] != "PASS":
        raise SystemExit(
            "D2-01 frozen environment path verification failed: "
            f"{environment_verification['mismatches']}"
        )
    verification = verify_seal(root=ROOT, manifest=seal)
    if verification["status"] != "PASS":
        raise SystemExit(f"D2-01 seal verification failed: {verification['mismatches']}")
    coverage = verify_seal_coverage(seal)
    if coverage["status"] != "PASS":
        raise SystemExit(
            "D2-01 seal coverage failed: "
            f"missing={coverage['missing']} duplicates={coverage['duplicates']}"
        )
    external_verification = verify_external_inputs()
    if external_verification["status"] != "PASS":
        raise SystemExit(
            "D2-01 external input verification failed: "
            f"{external_verification['mismatches']}"
        )
    output.mkdir(parents=True)
    started = time.monotonic()
    deadline = started + int(budget["wall_seconds"])
    commands: list[dict[str, Any]] = []
    external_calls_used = 0
    d1p42 = output / "d1p42-rerun"
    d1p43 = output / "d1p43-rerun"
    ablation_path = d1p43 / "ablation-and-role-target-results.json"

    def existing_outputs() -> dict[str, Any]:
        candidates = {
            "run_manifest": output / "run-manifest.json",
            "d1p42_ledger": d1p42 / "run-ledger.json",
            "d1p42_benchmark": d1p42 / "benchmark-rerun.json",
            "d1p43_result": ablation_path,
            "integrated_benchmark": output / "integrated/benchmark-results.json",
            "integrated_payy": output / "integrated/payy-results.json",
            "case_table": output / "development-case-table.json",
            "reconciliation": output / "reconciliation.json",
        }
        return {
            name: file_record(path) for name, path in candidates.items() if path.is_file()
        }

    try:
        prepare_run_manifest(
            root=ROOT,
            output=output / "run-manifest.json",
            run_id="D2-01-integrated-development-v1",
            experiment="D2 Step 1 integrated development reconciliation",
            inputs=[
                BENCHMARK_MANIFEST, D1P41_PROTOCOL, D1P43_PROTOCOL,
                D1P42_EXPECTED, D1P42_FACTS,
            ],
            configurations=[PROTOCOL, BOUNDARY, ASSOCIATIONS, EXTERNAL_INPUTS, seal],
            tool_specs=[
                ("nargo-beta22", str(NARGO), None),
                ("solc-0.8.29", str(SOLC), None),
            ],
            seeds=["none; deterministic authored cases"],
            wall_seconds=int(budget["wall_seconds"]),
            memory_mib=budget["memory_mib"],
            max_calls=int(budget["external_compiler_or_execution_calls"]),
        )
        command = run_command(
            "d1p42-rerun",
            [sys.executable, str(ROOT / "scripts/d1p_42_extent_audit.py"),
             "--output", str(d1p42)],
            output=output,
            timeout=remaining_timeout(deadline, 1200),
        )
        commands.append(command)
        if command["status"] != "PASS":
            raise RuntimeError(
                f"D2_D1P42_{command['status']}:exit={command['exit_code']}"
            )
        d1p42_ledger = json.loads((d1p42 / "run-ledger.json").read_text())
        external_calls_used = len(d1p42_ledger["commands"])
        if external_calls_used > int(budget["external_compiler_or_execution_calls"]):
            raise RuntimeError(
                "D2_EXTERNAL_CALL_BUDGET_EXCEEDED:"
                f"{external_calls_used}>{budget['external_compiler_or_execution_calls']}"
            )
        command = run_command(
            "d1p43-rerun",
            [sys.executable, str(ROOT / "scripts/d1p_43_role_ablation_preliminary.py"),
             "--output", str(d1p43), "--status", "FINAL_DEVELOPMENT"],
            output=output,
            timeout=remaining_timeout(deadline, 600),
        )
        commands.append(command)
        if command["status"] != "PASS":
            raise RuntimeError(
                f"D2_D1P43_{command['status']}:exit={command['exit_code']}"
            )

        static_benchmark = json.loads((d1p42 / "benchmark-rerun.json").read_text())
        ablation = json.loads(ablation_path.read_text())
        ablation["_result_path"] = str(ablation_path)
        integrated_benchmark = run_integrated_benchmark(
            output=output, static_benchmark=static_benchmark, deadline=deadline,
        )
        integrated_benchmark_path = output / "integrated/benchmark-results.json"
        write_json(integrated_benchmark_path, integrated_benchmark)
        payy = run_integrated_payy(output, d1p42, deadline=deadline)
        payy_path = output / "integrated/payy-results.json"
        write_json(payy_path, {"targets": payy})
        remaining_timeout(deadline, 1800)
        rows = case_table(
            integrated_benchmark=integrated_benchmark,
            ablation=ablation,
            payy=payy,
        )
        table = {
            "schema": "bindcheck.d2.development-case-table/v1",
            "generated_at_utc": now(),
            "row_count": len(rows),
            "required_fields": [
                "case", "family", "exposure", "version", "policy", "expected_defect",
                "outcome", "warning_association", "evidence_grade", "raw_output_path",
            ],
            "datasets": dict(Counter(row["dataset"] for row in rows)),
            "rows": rows,
        }
        table_path = output / "development-case-table.json"
        write_json(table_path, table)
        reconciled = reconciliation(
            static_benchmark=static_benchmark,
            integrated_benchmark=integrated_benchmark,
            ablation=ablation,
            payy=payy,
        )
        reconciliation_path = output / "reconciliation.json"
        write_json(reconciliation_path, reconciled)
        expected_static_counts = {
            "targets": 30,
            "detected": 11,
            "unsupported": 19,
            "misses": 0,
            "warning_objects": 13,
        }
        static_regression_matches = static_benchmark["counts"] == expected_static_counts
        ablation_check = ablation_regression_check(ablation)
        expected_classifications = {
            target: "DETECTED" if item["expected_outcome"] == "DETECTED" else "UNSUPPORTED"
            for target, item in json.loads(ASSOCIATIONS.read_text())["targets"].items()
        }
        association_regression_matches = all(
            row["classification"] == expected_classifications[row["target"]]
            for row in integrated_benchmark["targets"]
        )
        completion_checks = {
            "static_regression": static_regression_matches,
            "frozen_integrated_associations": association_regression_matches,
            "integrated_zero_misses": integrated_benchmark["counts"]["misses"] == 0,
            "full_case_ablation_vector": ablation_check["status"] == "PASS",
            "payy_extent_pair": all(item["matches_expected"] for item in payy),
            "case_table_rows": len(rows) == 49,
            "wall_budget": time.monotonic() <= deadline,
            "call_budget": external_calls_used <= int(
                budget["external_compiler_or_execution_calls"]
            ),
        }
        summary = {
            "schema": SCHEMA,
            "generated_at_utc": now(),
            "status": "COMPLETE" if all(completion_checks.values()) else "PARTIAL",
            "research_verdict": "UNKNOWN",
            "environment": {
                "git_head": git_value("rev-parse", "HEAD"),
                "git_branch": git_value("branch", "--show-current"),
                "python": sys.version,
                "platform": platform.platform(),
            },
            "seal": {
                "path": relative(seal),
                "verification": verification,
                "coverage": coverage,
            },
            "external_inputs": external_verification,
            "environment_paths": environment_verification,
            "run_manifest": file_record(output / "run-manifest.json"),
            "resource_budget": {
                "declared": budget,
                "external_calls_used": external_calls_used,
                "wall_seconds_used": round(time.monotonic() - started, 6),
            },
            "commands": commands,
            "completion_checks": completion_checks,
            "results": {
                "static_benchmark": static_benchmark["counts"],
                "integrated_benchmark": integrated_benchmark["counts"],
                "ablation": ablation["aggregate"],
                "ablation_regression": ablation_check,
                "role_targets": ablation["role_target_summary"],
                "payy_extent": payy,
                "case_rows": len(rows),
            },
            "outputs": existing_outputs(),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "claim_limits": protocol["claim_limits"],
        }
        summary_path = output / "run-summary.json"
        write_json(summary_path, summary)
        print(json.dumps({
            "status": summary["status"],
            "research_verdict": summary["research_verdict"],
            "integrated_benchmark": integrated_benchmark["counts"],
            "ablation": ablation["aggregate"],
            "role_targets": ablation["role_target_summary"],
            "payy_extent": [
                {key: item[key] for key in (
                    "revision", "observed_r_extent", "matches_expected"
                )}
                for item in payy
            ],
            "case_rows": len(rows),
            "completion_checks": completion_checks,
            "output": relative(summary_path),
        }, indent=2, sort_keys=True))
        return 0 if summary["status"] == "COMPLETE" else 1
    except Exception as error:
        partial = {
            "schema": SCHEMA,
            "generated_at_utc": now(),
            "status": "PARTIAL",
            "research_verdict": "UNKNOWN",
            "blocker": {"type": type(error).__name__, "message": str(error)},
            "seal": {
                "path": relative(seal),
                "verification": verification,
                "coverage": coverage,
            },
            "external_inputs": external_verification,
            "environment_paths": environment_verification,
            "resource_budget": {
                "declared": budget,
                "external_calls_used": external_calls_used,
                "wall_seconds_used": round(time.monotonic() - started, 6),
            },
            "commands": commands,
            "outputs": existing_outputs(),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "claim_limits": protocol["claim_limits"],
        }
        summary_path = output / "run-summary.json"
        write_json(summary_path, partial)
        print(json.dumps({
            "status": "PARTIAL",
            "research_verdict": "UNKNOWN",
            "blocker": partial["blocker"],
            "output": relative(summary_path),
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
