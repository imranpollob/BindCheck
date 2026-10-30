#!/usr/bin/env python3
"""Run the D1P-43 successor ablation and role-target suite in one command.

The historical D1P-41 protocol and evidence are not rewritten.  This runner
reuses its examples, adds R-ROLE only to the full BindCheck arm, respects
current analyzer fail-closed gates, and evaluates the prospectively frozen
D1P-43 target protocol.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any

from bindcheck_d1.role_binding import (
    RoleBindingUnsupported,
    analyze_role_binding,
)
from bindcheck_d1.static_analyzer_v1 import analyze


ROOT = Path(__file__).resolve().parents[1]
BASE_PROTOCOL_PATH = ROOT / "protocols/d1/d1p-41-ablation-preliminary.json"
ROLE_PROTOCOL_PATH = ROOT / "protocols/d1/d1p-43-role-binding-preliminary.json"
OUTPUT_DIR = ROOT / "results/raw/D1P-43"
RESULT_PATH = OUTPUT_DIR / "ablation-and-role-target-results.json"
ANALYZER_PATH = ROOT / "src/bindcheck_d1/static_analyzer_v1.py"
ROLE_MODULE_PATH = ROOT / "src/bindcheck_d1/role_binding.py"
COMMAND = "PYTHONPATH=src python3 scripts/d1p_43_role_ablation_preliminary.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(path: str) -> Path:
    return (ROOT / path).resolve()


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def warning_indices(warning: dict[str, Any]) -> set[int]:
    evidence = warning.get("evidence", {})
    indices: set[int] = set()
    if isinstance(evidence.get("public_index"), int):
        indices.add(evidence["public_index"])
    for value in evidence.get("public_indices", []):
        if isinstance(value, int):
            indices.add(value)
    return indices


def producer_inputs(target: str) -> tuple[Path, list[Path]] | None:
    if target.startswith("WT-C"):
        directory = ROOT / "results/raw/X-BM/mutants" / target
        return (
            directory / "warptoad-withdraw-main.nr",
            [directory / "warptoad-nargo-hashing-lib.nr"],
        )
    if target.startswith("WT-S") or target == "warptoad-pinned":
        return (
            ROOT / "benchmarks/binding-mutants/baselines/warptoad-withdraw-main.nr",
            [ROOT / "benchmarks/binding-mutants/baselines/warptoad-nargo-hashing-lib.nr"],
        )
    return None


def existing_role_kind(role_protocol: dict[str, Any], example_id: str) -> str | None:
    item = next(
        entry for entry in role_protocol["existing_discriminating_examples"]
        if entry["id"] == example_id
    )
    match = re.search(r"R-ROLE/([a-z-]+)", item["expected_role_result"])
    return match.group(1) if match else None


def is_related(
    warning: dict[str, Any],
    example: dict[str, Any],
    expected_role_kind: str | None,
) -> bool:
    expected = example["expected_boundary"]
    if warning["rule"] == "R-ROLE":
        if warning.get("evidence", {}).get("kind") != expected_role_kind:
            return False
    elif warning["rule"] not in expected["rules"]:
        return False
    if warning["rule"] in {"R-POLARITY"}:
        return True
    expected_indices = set(expected["public_indices"])
    return not expected_indices or bool(expected_indices.intersection(warning_indices(warning)))


def effect_named(warning: dict[str, Any]) -> bool:
    if warning["rule"] in {"R-EFFECT", "R-POLARITY"}:
        return True
    return (
        warning["rule"] == "R-ROLE"
        and warning.get("evidence", {}).get("kind")
        in {"polarity", "effect-authorization", "effect-beneficiary"}
    )


def score_arm(
    warnings: list[dict[str, Any]],
    example: dict[str, Any],
    expected_role_kind: str | None,
    *,
    status: str,
    expected_unknown: bool,
) -> dict[str, Any]:
    if status == "UNKNOWN":
        return {
            "status": "UNKNOWN",
            "detection": None,
            "matches_expected_outcome": expected_unknown,
            "effect_at_risk_named": None,
            "warning_count": None,
            "related_warning_count": None,
            "irrelevant_warning_count": None,
            "human_confirmation_steps": None,
            "remaining_checks": [
                "resolve the controlling analyzer support gate before scoring warnings"
            ],
            "warning_rules": [],
            "related_warning_ids": [],
            "irrelevant_warning_ids": [],
        }
    related = [
        warning for warning in warnings
        if is_related(warning, example, expected_role_kind)
    ]
    if example.get("clean_control", False):
        detected = not warnings
        matches_expected = not warnings
    else:
        detected = bool(related)
        matches_expected = detected
    credits: set[str] = set()
    for warning in related:
        if warning["rule"] in {"R-EFFECT", "R-ROLE"}:
            credits.update({"producer-binding", "consumer-relationship"})
        elif warning["rule"] == "R-BIND":
            credits.add("producer-binding")
        elif warning["rule"] in {"R-CONSUMER", "R-POLARITY", "R-ANCHOR"}:
            credits.add("consumer-relationship")
    checks = [
        "establish the relevant producer binding or gap",
        "establish the relevant consumer guard/effect/state relationship",
        "confirm the reviewed policy requires that relationship",
        "confirm a reachable execution and committed or contained outcome",
    ]
    remaining = [
        check for check in checks
        if not (
            check.startswith("establish the relevant producer")
            and "producer-binding" in credits
        ) and not (
            check.startswith("establish the relevant consumer")
            and "consumer-relationship" in credits
        )
    ]
    return {
        "status": "SUPPORTED",
        "detection": detected,
        "matches_expected_outcome": matches_expected,
        "effect_at_risk_named": any(effect_named(warning) for warning in related),
        "warning_count": len(warnings),
        "related_warning_count": len(related),
        "irrelevant_warning_count": len(warnings) - len(related),
        "human_confirmation_steps": len(remaining),
        "remaining_checks": remaining,
        "warning_rules": [warning["rule"] for warning in warnings],
        "related_warning_ids": [warning["id"] for warning in related],
        "irrelevant_warning_ids": [
            warning["id"] for warning in warnings if warning not in related
        ],
    }


def run_base_examples(
    base_protocol: dict[str, Any], role_protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    masks = {arm: set(rules) for arm, rules in role_protocol["arms"].items()}
    examples = []
    for example in base_protocol["examples"]:
        artifact = resolve(example["artifact"])
        consumer_source = resolve(example["source"])
        relation = resolve(example["relation"])
        expected_kind = existing_role_kind(role_protocol, example["id"])
        expected_unknown = next(
            item["expected_role_result"].startswith("UNKNOWN")
            for item in role_protocol["existing_discriminating_examples"]
            if item["id"] == example["id"]
        )
        input_record: dict[str, Any] = {
            "artifact": str(artifact),
            "artifact_sha256": sha256(artifact),
            "consumer_source": str(consumer_source),
            "consumer_source_sha256": sha256(consumer_source),
            "relation": str(relation),
            "relation_sha256": sha256(relation),
        }
        try:
            analysis = analyze(
                artifact, consumer_source, relation,
                label=f"{example['id']}:{example['target']}",
            )
        except ValueError as error:
            arms = {
                arm: {
                    "status": "UNKNOWN",
                    "support_gate": str(error),
                    "warnings": [],
                    "score": score_arm(
                        [], example, expected_kind,
                        status="UNKNOWN", expected_unknown=expected_unknown,
                    ),
                }
                for arm in masks
            }
            examples.append({
                "id": example["id"],
                "target": example["target"],
                "expected_role_kind": expected_kind,
                "expected_unknown": expected_unknown,
                "status": "UNKNOWN",
                "support_gate": str(error),
                "inputs": input_record,
                "arms": arms,
                "external_baseline": example["external_baseline"],
            })
            continue

        analysis_path = OUTPUT_DIR / f"ablation-{example['id']}-analysis.json"
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
        role_warnings: list[dict[str, Any]] = []
        role_status = "SUPPORTED"
        role_gate = None
        selected_producer = producer_inputs(example["target"])
        if selected_producer is None:
            role_status = "UNKNOWN"
            role_gate = "NO_PRODUCER_SEMANTIC_SOURCE_ROUTED"
        else:
            producer_source, support_sources = selected_producer
            input_record.update({
                "producer_source": str(producer_source),
                "producer_source_sha256": sha256(producer_source),
                "producer_support_sources": [
                    {"path": str(path), "sha256": sha256(path)} for path in support_sources
                ],
            })
            try:
                role_result = analyze_role_binding(
                    analysis,
                    producer_source=producer_source,
                    producer_support_sources=support_sources,
                )
                role_warnings = role_result["warnings"]
                role_path = OUTPUT_DIR / f"ablation-{example['id']}-role.json"
                role_path.write_text(json.dumps(role_result, indent=2, sort_keys=True) + "\n")
                input_record["role_result"] = {
                    "path": str(role_path.relative_to(ROOT)), "sha256": sha256(role_path)
                }
            except RoleBindingUnsupported as error:
                role_status = "UNKNOWN"
                role_gate = str(error)

        arms: dict[str, Any] = {}
        for arm, allowed_rules in masks.items():
            warnings = [
                warning for warning in analysis["warnings"]
                if warning["rule"] in allowed_rules
            ]
            status = "SUPPORTED"
            support_gate = None
            if arm == "full-bindcheck":
                if role_status == "SUPPORTED":
                    warnings.extend(role_warnings)
                else:
                    status = "UNKNOWN"
                    support_gate = role_gate
            arms[arm] = {
                "status": status,
                "support_gate": support_gate,
                "mask": {
                    "allowed_output_rules": sorted(allowed_rules),
                    "cross_layer_linking": arm == "full-bindcheck",
                    "role_binding_enabled": arm == "full-bindcheck",
                },
                "warnings": warnings if status == "SUPPORTED" else [],
                "score": score_arm(
                    warnings if status == "SUPPORTED" else [],
                    example,
                    expected_kind,
                    status=status,
                    expected_unknown=expected_unknown,
                ),
            }
        examples.append({
            "id": example["id"],
            "target": example["target"],
            "hypothesis": example["hypothesis"],
            "intended_policy": example["intended_policy"],
            "reachable_execution": example["reachable_execution"],
            "expected_outcome_before_arms": example["expected_outcome_before_arms"],
            "expected_role_kind": expected_kind,
            "expected_unknown": expected_unknown,
            "clean_control": example.get("clean_control", False),
            "status": "SUPPORTED",
            "inputs": input_record,
            "analysis_result": {
                "path": str(analysis_path.relative_to(ROOT)), "sha256": sha256(analysis_path)
            },
            "arms": arms,
            "external_baseline": example["external_baseline"],
        })
    return examples


def target_external_baseline(target: str) -> dict[str, str]:
    if target.startswith("WT-C"):
        return {"noir": "miss", "slither": "unsupported"}
    if target.startswith("WT-S"):
        return {"noir": "unsupported", "slither": "E1-lint"}
    if target.startswith("PY-S"):
        return {"noir": "unsupported", "slither": "E1-lint"}
    return {"noir": "unclassified", "slither": "unclassified"}


def run_role_targets(role_protocol: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for target in role_protocol["new_targets"]:
        artifact = resolve(target["artifact"])
        consumer_source = resolve(target["consumer_source"])
        relation = resolve(target["relation"])
        inputs: dict[str, Any] = {
            "artifact": str(artifact), "artifact_sha256": sha256(artifact),
            "consumer_source": str(consumer_source),
            "consumer_source_sha256": sha256(consumer_source),
            "relation": str(relation), "relation_sha256": sha256(relation),
        }
        try:
            analysis = analyze(
                artifact, consumer_source, relation,
                label=f"{target['id']}:{target['target']}",
            )
        except ValueError as error:
            status = "UNKNOWN"
            matches = target.get("expected_status") == "UNKNOWN"
            results.append({
                **{key: target[key] for key in (
                    "id", "target", "intended_policy", "reachable_execution",
                    "expected_outcome_before_run",
                )},
                "status": status,
                "support_gate": str(error),
                "matches_expected_outcome": matches,
                "warnings": [],
                "inputs": inputs,
                "external_baseline": target_external_baseline(target["target"]),
            })
            continue

        analysis_path = OUTPUT_DIR / f"target-{target['id']}-analysis.json"
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
        producer_source_value = target.get("producer_source")
        if not producer_source_value:
            results.append({
                **{key: target[key] for key in (
                    "id", "target", "intended_policy", "reachable_execution",
                    "expected_outcome_before_run",
                )},
                "status": "UNKNOWN",
                "support_gate": "NO_PRODUCER_SEMANTIC_SOURCE_ROUTED",
                "matches_expected_outcome": target.get("expected_status") == "UNKNOWN",
                "warnings": [],
                "inputs": inputs,
                "external_baseline": target_external_baseline(target["target"]),
            })
            continue
        producer_source = resolve(producer_source_value)
        support_sources = [resolve(path) for path in target.get("producer_support_sources", [])]
        inputs.update({
            "producer_source": str(producer_source),
            "producer_source_sha256": sha256(producer_source),
            "producer_support_sources": [
                {"path": str(path), "sha256": sha256(path)} for path in support_sources
            ],
        })
        try:
            role_result = analyze_role_binding(
                analysis,
                producer_source=producer_source,
                producer_support_sources=support_sources,
            )
        except RoleBindingUnsupported as error:
            results.append({
                **{key: target[key] for key in (
                    "id", "target", "intended_policy", "reachable_execution",
                    "expected_outcome_before_run",
                )},
                "status": "UNKNOWN",
                "support_gate": str(error),
                "matches_expected_outcome": target.get("expected_status") == "UNKNOWN",
                "warnings": [],
                "inputs": inputs,
                "external_baseline": target_external_baseline(target["target"]),
            })
            continue
        role_path = OUTPUT_DIR / f"target-{target['id']}-role.json"
        role_path.write_text(json.dumps(role_result, indent=2, sort_keys=True) + "\n")
        warnings = role_result["warnings"]
        expected_kinds = set(target["expected_kinds"])
        observed_kinds = {warning["evidence"]["kind"] for warning in warnings}
        expected_indices = set(target["expected_public_indices"])
        observed_expected_indices: set[int] = set()
        for warning in warnings:
            if warning["evidence"]["kind"] in expected_kinds:
                observed_expected_indices.update(warning_indices(warning))
        matching_warnings = [
            warning for warning in warnings
            if warning["evidence"]["kind"] in expected_kinds
        ]
        matches = (
            target["expected_rule"] == "R-ROLE"
            and expected_kinds.issubset(observed_kinds)
            and expected_indices.issubset(observed_expected_indices)
        )
        results.append({
            **{key: target[key] for key in (
                "id", "target", "intended_policy", "reachable_execution",
                "expected_outcome_before_run",
            )},
            "status": "SUPPORTED",
            "support_gate": None,
            "matches_expected_outcome": matches,
            "expected_kinds": sorted(expected_kinds),
            "observed_kinds": sorted(observed_kinds),
            "expected_public_indices": sorted(expected_indices),
            "observed_expected_public_indices": sorted(observed_expected_indices),
            "warning_count": len(warnings),
            "matching_warning_count": len(matching_warnings),
            "irrelevant_warning_count": len(warnings) - len(matching_warnings),
            "warnings": warnings,
            "inputs": inputs,
            "analysis_result": {
                "path": str(analysis_path.relative_to(ROOT)), "sha256": sha256(analysis_path)
            },
            "role_result": {
                "path": str(role_path.relative_to(ROOT)), "sha256": sha256(role_path)
            },
            "external_baseline": target_external_baseline(target["target"]),
        })
    return results


def aggregate_ablation(examples: list[dict[str, Any]], arms: list[str]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {}
    for arm in arms:
        positive = [
            example["arms"][arm]["score"] for example in examples
            if not example.get("clean_control", False)
            and example["arms"][arm]["score"]["status"] == "SUPPORTED"
        ]
        unknown = [
            example for example in examples
            if not example.get("clean_control", False)
            and example["arms"][arm]["score"]["status"] == "UNKNOWN"
        ]
        controls = [
            example["arms"][arm]["score"] for example in examples
            if example.get("clean_control", False)
            and example["arms"][arm]["score"]["status"] == "SUPPORTED"
        ]
        aggregate[arm] = {
            "supported_positive_examples": len(positive),
            "unknown_positive_examples": len(unknown),
            "unknown_example_ids": [example["id"] for example in unknown],
            "detections": sum(bool(score["detection"]) for score in positive),
            "examples_naming_effect_at_risk": sum(
                bool(score["effect_at_risk_named"]) for score in positive
            ),
            "warning_objects": sum(score["warning_count"] for score in positive),
            "related_warning_objects": sum(
                score["related_warning_count"] for score in positive
            ),
            "irrelevant_warning_objects": sum(
                score["irrelevant_warning_count"] for score in positive
            ),
            "mean_human_confirmation_steps": round(
                sum(score["human_confirmation_steps"] for score in positive) / len(positive), 3
            ) if positive else None,
            "clean_controls_matching_expected": sum(
                bool(score["matches_expected_outcome"]) for score in controls
            ),
            "supported_clean_controls": len(controls),
        }
    return aggregate


def main() -> int:
    base_protocol = json.loads(BASE_PROTOCOL_PATH.read_text())
    role_protocol = json.loads(ROLE_PROTOCOL_PATH.read_text())
    expected_masks = {
        "producer-only": {"R-BIND"},
        "consumer-only": {"R-CONSUMER", "R-POLARITY", "R-ANCHOR"},
        "unjoined-union": {"R-BIND", "R-CONSUMER", "R-POLARITY", "R-ANCHOR"},
        "full-bindcheck": {
            "R-BIND", "R-CONSUMER", "R-POLARITY", "R-ANCHOR", "R-EFFECT", "R-ROLE"
        },
    }
    observed_masks = {arm: set(rules) for arm, rules in role_protocol["arms"].items()}
    if observed_masks != expected_masks:
        raise ValueError(f"D1P-43 arm masks changed: {observed_masks!r}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    examples = run_base_examples(base_protocol, role_protocol)
    targets = run_role_targets(role_protocol)
    aggregate = aggregate_ablation(examples, list(role_protocol["arms"]))
    baseline_counts = {
        "Noir compiler lint": Counter(
            example["external_baseline"]["noir"] for example in examples
        ),
        "Slither": Counter(
            example["external_baseline"]["slither"] for example in examples
        ),
    }
    result = {
        "schema": "bindcheck.d1p43.preliminary-results/v1",
        "status": "PRELIMINARY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": COMMAND,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "git_head": git_value("rev-parse", "HEAD"),
            "git_branch": git_value("branch", "--show-current"),
        },
        "freeze": {
            "base_protocol": str(BASE_PROTOCOL_PATH.relative_to(ROOT)),
            "base_protocol_sha256": sha256(BASE_PROTOCOL_PATH),
            "role_protocol": str(ROLE_PROTOCOL_PATH.relative_to(ROOT)),
            "role_protocol_sha256": sha256(ROLE_PROTOCOL_PATH),
            "analyzer": str(ANALYZER_PATH.relative_to(ROOT)),
            "analyzer_sha256": sha256(ANALYZER_PATH),
            "analyzer_changed_by_task": False,
            "role_module": str(ROLE_MODULE_PATH.relative_to(ROOT)),
            "role_module_sha256": sha256(ROLE_MODULE_PATH),
        },
        "arm_method": (
            "Run the current analyzer; mask its warning outputs for the first three arms; "
            "append separately computed R-ROLE warnings only to full BindCheck. Analyzer or "
            "role-interface support failures are UNKNOWN, never no-warning results."
        ),
        "aggregate": aggregate,
        "external_baselines": {
            "status": "reported separately, not arms",
            "source": "docs/baselines/d1p-32-benchmark.md",
            "classifications": {
                name: dict(counts) for name, counts in baseline_counts.items()
            },
            "scoring_limit": (
                "Noir/Slither E1 lints localize variables or functions but do not describe "
                "producer-consumer role correspondence and receive no arm credit."
            ),
        },
        "ablation_examples": examples,
        "role_targets": targets,
        "role_target_summary": {
            "targets": len(targets),
            "supported": sum(target["status"] == "SUPPORTED" for target in targets),
            "unknown": sum(target["status"] == "UNKNOWN" for target in targets),
            "matching_expected": sum(target["matches_expected_outcome"] for target in targets),
            "supported_with_target_warning": sum(
                target["status"] == "SUPPORTED" and target.get("matching_warning_count", 0) > 0
                for target in targets
            ),
        },
        "claim_limits": role_protocol["claim_limits"],
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "result": str(RESULT_PATH.relative_to(ROOT)),
        "aggregate": aggregate,
        "role_target_summary": result["role_target_summary"],
    }, indent=2, sort_keys=True))
    return 0 if all(target["matches_expected_outcome"] for target in targets) else 1


if __name__ == "__main__":
    raise SystemExit(main())
