#!/usr/bin/env python3
"""Run the frozen D1P-41 preliminary arm ablation in one command.

The script does not change BindCheck rules. It runs the current analyzer and
constructs the producer-only, consumer-only, unjoined-union, and full arms by
filtering warning outputs with the rule masks frozen in the protocol.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from bindcheck_d1.static_analyzer_v1 import analyze


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "protocols/d1/d1p-41-ablation-preliminary.json"
OUTPUT_DIR = ROOT / "results/raw/D1P-41"
RESULT_PATH = OUTPUT_DIR / "ablation-results.json"
FIRST_ATTEMPT_PATH = OUTPUT_DIR / "attempt-01-scoring-bug.json"
ANALYZER_PATH = ROOT / "src/bindcheck_d1/static_analyzer_v1.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(path: str) -> Path:
    return (ROOT / path).resolve()


def warning_indices(warning: dict[str, Any]) -> set[int]:
    evidence = warning.get("evidence", {})
    indices: set[int] = set()
    if isinstance(evidence.get("public_index"), int):
        indices.add(evidence["public_index"])
    for value in evidence.get("public_indices", []):
        if isinstance(value, int):
            indices.add(value)
    return indices


def is_related(warning: dict[str, Any], example: dict[str, Any]) -> bool:
    expected = example["expected_boundary"]
    if warning["rule"] not in expected["rules"]:
        return False
    # The current R-POLARITY warning identifies the structurally paired replay
    # relation, but its evidence schema has no public_index field. Rule match
    # is therefore the frozen semantic-boundary predicate for this rule.
    if warning["rule"] == "R-POLARITY":
        return True
    expected_indices = set(expected["public_indices"])
    if not expected_indices:
        return True
    return bool(expected_indices.intersection(warning_indices(warning)))


def effect_named(warning: dict[str, Any]) -> bool:
    # R-EFFECT names a committed consumer effect; R-POLARITY names the
    # protected replay-state write, but not the downstream duplicate effect.
    return warning["rule"] in {"R-EFFECT", "R-POLARITY"}


def score_arm(warnings: list[dict[str, Any]], example: dict[str, Any]) -> dict[str, Any]:
    related = [warning for warning in warnings if is_related(warning, example)]
    if example.get("clean_control", False):
        detected = not warnings
        matches_expected = not warnings
    else:
        detected = bool(related)
        matches_expected = detected

    credits = set()
    for warning in related:
        if warning["rule"] == "R-EFFECT":
            credits.update({"producer-binding", "consumer-relationship"})
        elif warning["rule"] == "R-BIND":
            credits.add("producer-binding")
        elif warning["rule"] in {"R-CONSUMER", "R-POLARITY", "R-ANCHOR"}:
            credits.add("consumer-relationship")

    return {
        "detection": detected,
        "matches_expected_outcome": matches_expected,
        "effect_at_risk_named": any(effect_named(warning) for warning in related),
        "effect_naming_rules": [
            warning["rule"] for warning in related if effect_named(warning)
        ],
        "warning_count": len(warnings),
        "related_warning_count": len(related),
        "irrelevant_warning_count": len(warnings) - len(related),
        "human_confirmation_steps": 4 - len(credits),
        "remaining_checks": [
            check for check in (
                "establish the relevant producer binding or gap",
                "establish the relevant consumer guard/effect/state relationship",
                "confirm the reviewed policy requires that relationship",
                "confirm a reachable execution and committed or contained outcome",
            )
            if not (
                (check.startswith("establish the relevant producer") and "producer-binding" in credits)
                or (check.startswith("establish the relevant consumer") and "consumer-relationship" in credits)
            )
        ],
        "warning_rules": [warning["rule"] for warning in warnings],
        "related_warning_ids": [warning["id"] for warning in related],
        "irrelevant_warning_ids": [
            warning["id"] for warning in warnings if warning not in related
        ],
    }


def git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text())
    masks = {
        arm: set(spec["output_rules"])
        for arm, spec in protocol["arms"].items()
    }
    expected_masks = {
        "producer-only": {"R-BIND"},
        "consumer-only": {"R-CONSUMER", "R-POLARITY", "R-ANCHOR"},
        "unjoined-union": {"R-BIND", "R-CONSUMER", "R-POLARITY", "R-ANCHOR"},
        "full-bindcheck": {
            "R-BIND", "R-CONSUMER", "R-POLARITY", "R-ANCHOR", "R-EFFECT"
        },
    }
    if masks != expected_masks:
        raise ValueError(f"protocol arm masks changed: {masks!r}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if RESULT_PATH.exists() and not FIRST_ATTEMPT_PATH.exists():
        FIRST_ATTEMPT_PATH.write_bytes(RESULT_PATH.read_bytes())
    examples = []
    for example in protocol["examples"]:
        artifact = resolve(example["artifact"])
        source = resolve(example["source"])
        relation = resolve(example["relation"])
        for kind, path in (("artifact", artifact), ("source", source), ("relation", relation)):
            if not path.is_file():
                raise FileNotFoundError(f"{example['id']} missing {kind}: {path}")

        full = analyze(artifact, source, relation, label=f"{example['id']}:{example['target']}")
        full_path = OUTPUT_DIR / f"{example['id']}-full-analysis.json"
        full_path.write_text(json.dumps(full, indent=2, sort_keys=True) + "\n")
        arms = {}
        for arm, allowed_rules in masks.items():
            warnings = [
                warning for warning in full["warnings"] if warning["rule"] in allowed_rules
            ]
            arms[arm] = {
                "mask": {
                    "allowed_output_rules": sorted(allowed_rules),
                    "producer_occurrence_facts": arm in {"producer-only", "unjoined-union", "full-bindcheck"},
                    "consumer_facts": arm in {"consumer-only", "unjoined-union", "full-bindcheck"},
                    "cross_layer_linking": arm == "full-bindcheck",
                },
                "score": score_arm(warnings, example),
                "warnings": warnings,
            }

        examples.append({
            "id": example["id"],
            "target": example["target"],
            "hypothesis": example["hypothesis"],
            "intended_policy": example["intended_policy"],
            "reachable_execution": example["reachable_execution"],
            "expected_outcome_before_arms": example["expected_outcome_before_arms"],
            "clean_control": example.get("clean_control", False),
            "inputs": {
                "artifact": str(artifact), "artifact_sha256": sha256(artifact),
                "source": str(source), "source_sha256": sha256(source),
                "relation": str(relation), "relation_sha256": sha256(relation),
            },
            "full_analysis": {
                "path": str(full_path.relative_to(ROOT)),
                "sha256": sha256(full_path),
                "schema": full["schema"],
            },
            "arms": arms,
            "external_baseline": example["external_baseline"],
        })

    positive = [example for example in examples if not example["clean_control"]]
    controls = [example for example in examples if example["clean_control"]]
    aggregate: dict[str, Any] = {}
    for arm in masks:
        scores = [example["arms"][arm]["score"] for example in positive]
        control_scores = [example["arms"][arm]["score"] for example in controls]
        aggregate[arm] = {
            "positive_examples": len(scores),
            "detections": sum(score["detection"] for score in scores),
            "examples_naming_effect_at_risk": sum(
                score["effect_at_risk_named"] for score in scores
            ),
            "warning_objects": sum(score["warning_count"] for score in scores),
            "related_warning_objects": sum(score["related_warning_count"] for score in scores),
            "irrelevant_warning_objects": sum(
                score["irrelevant_warning_count"] for score in scores
            ),
            "mean_human_confirmation_steps": round(
                sum(score["human_confirmation_steps"] for score in scores) / len(scores), 3
            ),
            "clean_controls_matching_expected": sum(
                score["matches_expected_outcome"] for score in control_scores
            ),
            "clean_controls": len(control_scores),
        }

    baseline_counts = {
        "Noir compiler lint": Counter(
            example["external_baseline"]["noir"] for example in examples
        ),
        "Slither": Counter(
            example["external_baseline"]["slither"] for example in examples
        ),
    }
    result = {
        "schema": "bindcheck.d1p41.ablation-results/v1",
        "status": "PRELIMINARY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "PYTHONPATH=src python3 scripts/d1p_41_ablation_preliminary.py",
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "git_head": git_value("rev-parse", "HEAD"),
            "git_branch": git_value("branch", "--show-current"),
        },
        "freeze": {
            "protocol": str(PROTOCOL_PATH.relative_to(ROOT)),
            "protocol_sha256": sha256(PROTOCOL_PATH),
            "analyzer": str(ANALYZER_PATH.relative_to(ROOT)),
            "analyzer_sha256": sha256(ANALYZER_PATH),
            "analyzer_changed_by_task": False,
        },
        "arm_method": "Run the unchanged full analyzer, then mask warning outputs by the frozen rule sets; consumer-only additionally declares producer occurrence facts masked, and unjoined-union synthesizes no warning.",
        "aggregate": aggregate,
        "external_baselines": {
            "status": "reported separately, not arms",
            "source": "docs/baselines/d1p-32-benchmark.md",
            "classifications": {name: dict(counts) for name, counts in baseline_counts.items()},
            "scoring_limit": "Imported per-target lint classifications do not provide warning-object counts. They are navigation signals, not mismatch detections, and receive no cross-layer confirmation credit.",
        },
        "examples": examples,
        "claim_limits": protocol["claim_limits"],
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "result": str(RESULT_PATH.relative_to(ROOT)),
        "result_sha256": sha256(RESULT_PATH),
        "aggregate": aggregate,
        "external_baselines": result["external_baselines"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
