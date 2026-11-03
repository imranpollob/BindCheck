#!/usr/bin/env python3
"""Finalize D2 Gate A without scoring when prospective fairness gates fail.

This runner is intentionally incapable of dispatching an analyzer, baseline,
proof system, fuzzer, or scorer. It verifies frozen Step 5/6 evidence,
materializes an exact zero-score finalization packet, seals the retained bytes
with the D2 foundation utility, and verifies that seal.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import d2_foundation as foundation  # noqa: E402


DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-07-gate-a-finalization-v1.json"
DEFAULT_OUT = ROOT / "results/raw/D2-07-recovery-01"
EXPECTED_BLOCKERS = {
    "HUMAN_POLICY_AUTHOR_OR_ADOPTION_MISSING",
    "DISTINCT_HUMAN_POLICY_REVIEW_MISSING",
    "STRONG_FULL_POE_INTERFACE_NOT_EQUAL",
    "FAIR_SAME_POLICY_ARM_INCOMPLETE",
}
EXPECTED_ROW_LOCAL_UNRESOLVED = {"SUBJECTIVE_SCORER_ADJUDICATOR_UNAVAILABLE"}
EXPECTED_CASES = {
    "GA-PAYY-TAIL-EARLIER",
    "GA-PAYY-TAIL-CHECK-ADDED",
    "GA-WARPTOAD-MDOM",
    "GA-WARPTOAD-MSRC",
    *(f"GA-WARPTOAD-RELATIONSHIP-E{i}" for i in range(1, 10)),
}
EXPECTED_INTERNAL_ARMS = {
    "producer-only",
    "consumer-only",
    "unjoined-union",
    "basic-structural-composition",
    "strong-simple-composition",
    "full-bindcheck",
}
EXPECTED_EXTERNAL_ARMS = {
    "CMP-NOIR",
    "CMP-SLITHER",
    "CMP-MYTHRIL",
    "CMP-FOUNDRY",
    "CMP-ECHIDNA",
    "CMP-ZKAP",
    "CMP-CIVER",
    "CMP-CCC-CHECK",
    "CMP-PICUS",
    "CMP-SMARTAXE",
    "CMP-ELSA",
}
ATTEMPTED_TRANSFORMATIONS = {
    "TR-IDENTIFIER-RENAME",
    "TR-HELPER-EXTRACTION",
    "TR-EQUIVALENT-EXPRESSION",
    "TR-MATCHED-PUBLIC-REORDER",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_new_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing record: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def resolve(root: Path, path_text: str) -> Path:
    path = Path(path_text)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"path outside repository root: {path_text}") from error
    return resolved


def file_record(root: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(f"expected regular non-symlink file: {path}")
    return {
        "path": resolved.relative_to(root.resolve()).as_posix(),
        "sha256": sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def verify_bound_files(root: Path, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        path = resolve(root, row["path"])
        record = file_record(root, path)
        if record["sha256"] != row["sha256"]:
            raise ValueError(
                f"artifact hash mismatch for {row['path']}: "
                f"{record['sha256']} != {row['sha256']}"
            )
        records.append({**record, "role": row.get("role")})
    return records


def iter_entry_files(root: Path, entries: Iterable[str]) -> list[Path]:
    """Resolve the immutable file universe later passed to foundation."""
    selected: set[Path] = set()
    for path_text in entries:
        entry = resolve(root, path_text)
        if entry.is_symlink():
            raise ValueError(f"seal entry is a symlink: {path_text}")
        if not entry.exists():
            raise FileNotFoundError(f"seal entry does not exist: {path_text}")
        candidates = [entry]
        if entry.is_dir():
            candidates = sorted(path for path in entry.rglob("*") if path.is_file())
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"seal member is a symlink: {candidate}")
            if candidate.name in foundation.MUTABLE_INDEX_NAMES:
                continue
            if any(part in {".git", "__pycache__"} for part in candidate.parts):
                continue
            selected.add(candidate.resolve())
    return sorted(selected, key=lambda path: path.relative_to(root.resolve()).as_posix())


def _source_paths(root: Path) -> dict[str, Path]:
    return {
        "step5": root / "protocols/d2/d2-05-early-comparison-draft-v1.json",
        "step6a_protocol": root / "protocols/d2/d2-06a-construction-v1.json",
        "step6a_summary": root / "results/raw/D2-06A/construction-03/run-summary.json",
        "step6a_baseline": root / "results/raw/D2-06A/construction-03/baseline-smoke-summary.json",
        "information": root / "results/raw/D2-06A/construction-03/information-budget-matrix.json",
        "transformations": root / "results/raw/D2-06A/construction-03/transformation-ledger.json",
        "step6b_protocol": root / "protocols/d2/d2-06b-comparator-smoke-v1.json",
        "inventory": root / "docs/evaluation/d2-06b-comparator-inventory-v1.json",
        "step6b_summary": root / "results/raw/D2-06B/recovery-01/smoke-summary.json",
    }


def load_sources(root: Path) -> dict[str, dict[str, Any]]:
    sources = {key: read_json(path) for key, path in _source_paths(root).items()}
    case_outputs: dict[str, dict[str, Any]] = {}
    output_path_by_case: dict[str, str] = {}
    for row in sources["step6a_baseline"].get("rows", []):
        case_id = row["case_id"]
        path_text = row["output"]["path"]
        prior = output_path_by_case.setdefault(case_id, path_text)
        if prior != path_text:
            raise ValueError(f"Step 6a case has inconsistent shared output: {case_id}")
    for case_id, path_text in output_path_by_case.items():
        case_outputs[case_id] = read_json(resolve(root, path_text))
    sources["step6a_case_outputs"] = case_outputs
    return sources


def assess_readiness(
    protocol: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Return a deterministic readiness decision from frozen machine fields."""
    if protocol.get("status") != "BLOCKED_FINALIZATION_ZERO_SCORED_ARMS":
        raise ValueError("Step 7 protocol must be a blocked zero-score finalization")
    if protocol.get("gate_a_decision") != "INCONCLUSIVE":
        raise ValueError("blocked finalization must use the Step 5 INCONCLUSIVE class")
    if protocol.get("research_verdict") != "UNKNOWN":
        raise ValueError("research verdict must remain UNKNOWN")
    boundary = protocol.get("execution_boundary", {})
    if boundary.get("scored_execution_authorized") is not False:
        raise ValueError("scored execution must be unauthorized")
    if boundary.get("scored_arm_count") != 0 or boundary.get("objective_subset") != []:
        raise ValueError("blocked finalization must contain zero scored arms and no objective subset")

    blockers: set[str] = set()
    row_local_unresolved: set[str] = set()
    step5 = sources["step5"]
    if step5.get("status") != "DRAFT_UNSEALED_DO_NOT_SCORE":
        raise ValueError("unexpected Step 5 status")

    step6a_summary = sources["step6a_summary"]
    if step6a_summary.get("scored") is not False:
        raise ValueError("Step 6a construction unexpectedly claims scoring")
    if step6a_summary.get("status") != "COMPLETE_CONSTRUCTION_SMOKE_ONLY":
        raise ValueError("unexpected Step 6a summary status")

    information = sources["information"]
    if (
        information.get("scored_comparison_allowed") is False
        and information.get("strong_vs_full_equal_reviewed_policy_consumption") is False
        and information.get("status") == "UNRESOLVED_EQUAL_POLICY_INTERFACE"
    ):
        blockers.add("STRONG_FULL_POE_INTERFACE_NOT_EQUAL")

    step6b_protocol = sources["step6b_protocol"]
    independence = step6b_protocol.get("same_policy", {}).get("independence", {})
    step6a_policies = [
        value.get("policy", {}) for value in sources["step6a_case_outputs"].values()
    ]
    if len(step6a_policies) != len(EXPECTED_CASES):
        raise ValueError("Step 6a policy record does not cover all candidate cases")
    step6a_authors_missing = all(
        policy.get("policy_author") is None
        and policy.get("review_status") == "NOT_SUPPLIED"
        for policy in step6a_policies
    )
    step6a_reviewers_missing = all(
        policy.get("policy_reviewer") is None
        and policy.get("review_status") == "NOT_SUPPLIED"
        for policy in step6a_policies
    )
    if (
        independence.get("human_policy_author_status") == "UNRESOLVED"
        and step6a_authors_missing
    ):
        blockers.add("HUMAN_POLICY_AUTHOR_OR_ADOPTION_MISSING")
    if (
        independence.get("different_human_reviewer_status") == "UNRESOLVED"
        and step6a_reviewers_missing
    ):
        blockers.add("DISTINCT_HUMAN_POLICY_REVIEW_MISSING")

    step6b_summary = sources["step6b_summary"]
    if step6b_summary.get("scored") is not False:
        raise ValueError("Step 6b smoke unexpectedly claims scoring")
    inventory = sources["inventory"]
    comparator_ids = {row["id"] for row in inventory.get("comparators", [])}
    if comparator_ids != EXPECTED_EXTERNAL_ARMS:
        raise ValueError(f"external comparator inventory mismatch: {sorted(comparator_ids)}")
    if (
        inventory.get("status") == "CONSTRUCTION_INVENTORY_UNSEALED_DO_NOT_SCORE"
        and step6b_protocol.get("status") == "CONSTRUCTION_SMOKE_ONLY_UNSEALED_DO_NOT_SCORE"
    ):
        blockers.add("FAIR_SAME_POLICY_ARM_INCOMPLETE")

    transformations = sources["transformations"]
    attempted = {row["id"]: row for row in transformations.get("rows", []) if row.get("attempted")}
    if set(attempted) != ATTEMPTED_TRANSFORMATIONS:
        raise ValueError(f"attempted transformation set mismatch: {sorted(attempted)}")
    for row in attempted.values():
        controls = row.get("control_summary", {})
        if row.get("status") != "SEMANTICALLY_CONTROLLED":
            raise ValueError(f"transformation is not bounded-control ready: {row['id']}")
        if not all(
            controls.get(field) is True
            for field in (
                "logical_abi_layout_matches",
                "producer_execution_vector_matches",
                "consumer_algebra_matches",
            )
        ):
            raise ValueError(f"transformation focused control failed: {row['id']}")
        if controls.get("formal_equivalence_proof") != "NOT_ESTABLISHED":
            raise ValueError("Step 7 must not upgrade bounded controls to formal proof")

    humans = protocol.get("human_dependencies_and_prior_exposure", {})
    if (
        humans.get("two_independent_subjective_scorers") == "UNRESOLVED"
        or humans.get("distinct_adjudicator") == "UNRESOLVED"
    ):
        row_local_unresolved.add("SUBJECTIVE_SCORER_ADJUDICATOR_UNAVAILABLE")

    declared_blockers = {row["code"] for row in protocol.get("global_blockers", [])}
    if declared_blockers != EXPECTED_BLOCKERS:
        raise ValueError(f"protocol blocker set mismatch: {sorted(declared_blockers)}")
    if blockers != EXPECTED_BLOCKERS:
        raise ValueError(f"evidence blocker set mismatch: {sorted(blockers)}")
    declared_row_local = {
        row["code"] for row in protocol.get("row_local_unresolved_conditions", [])
    }
    if declared_row_local != EXPECTED_ROW_LOCAL_UNRESOLVED:
        raise ValueError(f"row-local condition set mismatch: {sorted(declared_row_local)}")
    if row_local_unresolved != EXPECTED_ROW_LOCAL_UNRESOLVED:
        raise ValueError(
            f"evidence row-local condition set mismatch: {sorted(row_local_unresolved)}"
        )

    case_ids = {
        case_id
        for group in protocol.get("case_and_target_dispositions", [])
        for case_id in group.get("case_ids", [])
    }
    if case_ids != EXPECTED_CASES:
        raise ValueError(f"candidate case set mismatch: {sorted(case_ids)}")
    if any(
        group.get("status") != "UNRESOLVED" or group.get("denominator_membership") is not False
        for group in protocol["case_and_target_dispositions"]
    ):
        raise ValueError("every blocked candidate must remain UNRESOLVED and outside denominators")
    if any(
        set(group.get("reason_codes", [])) != EXPECTED_BLOCKERS
        for group in protocol["case_and_target_dispositions"]
    ):
        raise ValueError("every candidate group must cite the exact global blocker set")

    arms = protocol.get("arm_dispositions", {})
    if set(arms.get("internal", [])) != EXPECTED_INTERNAL_ARMS:
        raise ValueError("internal arm inventory mismatch")
    if set(arms.get("external_inventory_ids", [])) != EXPECTED_EXTERNAL_ARMS:
        raise ValueError("external arm inventory mismatch")

    denominators = protocol.get("denominators", {})
    scored_denominators = (
        "objective_case_arm_rows",
        "target_detection",
        "diagnosis",
        "safe_control_false_warning",
        "validation",
        "transformation_stability",
        "scored_external_comparators",
    )
    if any(denominators.get(key) != 0 for key in scored_denominators):
        raise ValueError("all scored denominators must be explicitly zero")

    prototype_budget = protocol["prospective_missing_mechanism_prototype"]["budget"]
    if prototype_budget != {"researcher_days": 2, "machine_hours": 8}:
        raise ValueError("prospective prototype budget must remain two researcher-days/eight machine-hours")
    recommendation = protocol.get("scope_recommendation", {})
    if recommendation.get("decision") != "BOUNDED_PROTOTYPE":
        raise ValueError("INCONCLUSIVE Gate A must carry the explicit bounded-prototype recommendation")
    if recommendation.get("combined_cap") != {
        "researcher_days": 2,
        "machine_hours": 8,
        "applies_across_mechanical_and_primary_phases": True,
    }:
        raise ValueError("scope recommendation must preserve the combined prototype cap")
    if (
        recommendation.get("mechanical_fixture_phase", {}).get("required_label")
        != "UNREVIEWED_DEVELOPMENT_FIXTURE"
    ):
        raise ValueError("mechanical tests must be labeled as an unreviewed development fixture")
    if (
        recommendation.get("primary_discriminating_experiment", {}).get("status")
        != "BLOCKED_PENDING_HUMAN_POLICY_ROLES"
    ):
        raise ValueError("primary prototype experiment must remain blocked on human policy roles")
    if recommendation.get("reserved_data_authorized") is not False:
        raise ValueError("Gate A scope recommendation cannot authorize reserved data")
    if recommendation.get("retroactive_gate_a_rescore_authorized") is not False:
        raise ValueError("bounded prototype cannot retroactively rescore Gate A")

    return {
        "status": "BLOCKED_BEFORE_SCORE",
        "gate_a_decision": "INCONCLUSIVE",
        "research_verdict": "UNKNOWN",
        "scored_execution_authorized": False,
        "scored_arm_count": 0,
        "objective_subset": [],
        "blocker_codes": sorted(blockers),
        "row_local_unresolved_codes": sorted(row_local_unresolved),
        "candidate_case_count": len(case_ids),
        "candidate_case_ids": sorted(case_ids),
        "internal_arm_count": len(EXPECTED_INTERNAL_ARMS),
        "external_inventory_count": len(EXPECTED_EXTERNAL_ARMS),
        "bounded_transformation_count": len(attempted),
    }


def case_target_inventory(
    protocol: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    match_fields = protocol["warning_matching"]["required_match_fields"]
    source_by_case: dict[str, dict[str, Any]] = {}
    for row in sources["step6a_baseline"].get("rows", []):
        source_by_case.setdefault(row["case_id"], row["source"])
    for group in protocol["case_and_target_dispositions"]:
        for case_id in group["case_ids"]:
            rows.append(
                {
                    "case_id": case_id,
                    "group": group["group"],
                    "semantic_target_source": group["target_source"],
                    "semantic_target": group["semantic_target"],
                    "construction_source": source_by_case[case_id],
                    "construction_policy_record": sources["step6a_case_outputs"][
                        case_id
                    ]["policy"],
                    "required_match_fields": match_fields,
                    "status": "UNRESOLVED",
                    "reason_codes": group["reason_codes"],
                    "denominator_membership": False,
                    "score": None,
                }
            )
    return sorted(rows, key=lambda row: row["case_id"])


def build_packet_manifest(
    *,
    root: Path,
    protocol_path: Path,
    protocol: dict[str, Any],
    readiness: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    created_at: str,
    generated_output_paths: list[Path] | None = None,
    prior_attempt_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seal_files = iter_entry_files(root, protocol["seal_plan"]["entries"])
    artifact_inventory = [file_record(root, path) for path in seal_files]
    inventory_by_id = {
        row["id"]: row for row in sources["inventory"].get("comparators", [])
    }
    external_arms = [
        {
            "id": comparator_id,
            "construction_record": inventory_by_id[comparator_id].get("arms"),
            "status": "UNSCORED_APPLICABILITY_OR_CONSTRUCTION_ONLY",
        }
        for comparator_id in sorted(EXPECTED_EXTERNAL_ARMS)
    ]
    internal_arms = [
        {"id": arm, "status": "UNSCORED_CONSTRUCTION_ONLY"}
        for arm in sorted(EXPECTED_INTERNAL_ARMS)
    ]
    form_records = [
        file_record(root, resolve(root, row["path"])) for row in protocol["forms"]
    ]
    runner_paths = [
        "scripts/d2_foundation.py",
        "scripts/d2_step6a_construct.py",
        "scripts/d2_step6b_same_policy_smoke.py",
        "scripts/d2_step7_gate_a.py",
    ]
    runner_records = [file_record(root, resolve(root, path)) for path in runner_paths]
    return {
        "schema": "bindcheck.d2.gate-a-blocked-packet-manifest/v1",
        "created_at_utc": created_at,
        "protocol": file_record(root, protocol_path),
        "status": readiness["status"],
        "gate_a_decision": readiness["gate_a_decision"],
        "research_verdict": "UNKNOWN",
        "scored_execution": {
            "authorized": False,
            "executed": False,
            "arm_count": 0,
            "score_row_count": 0,
            "objective_subset": [],
        },
        "blocker_codes": readiness["blocker_codes"],
        "row_local_unresolved_codes": readiness["row_local_unresolved_codes"],
        "case_and_target_inventory": case_target_inventory(protocol, sources),
        "arm_inventory": {"internal": internal_arms, "external": external_arms},
        "transformation_inventory": protocol["transformation_dispositions"],
        "resource_inventory": protocol["resource_budget"],
        "form_inventory": form_records,
        "runner_inventory": runner_records,
        "artifact_inventory": artifact_inventory,
        "artifact_inventory_count": len(artifact_inventory),
        "artifact_inventory_total_bytes": sum(row["size_bytes"] for row in artifact_inventory),
        "seal_only_generated_extras": [
            {
                "path": path.resolve().relative_to(root.resolve()).as_posix(),
                "hash_source": "content-seal-v1.json",
            }
            for path in (generated_output_paths or [])
        ],
        "denominators": protocol["denominators"],
        "historical_reconciliation": protocol["step_5_and_6_audit"],
        "step_7_recovery_history": protocol["step_7_recovery_history"],
        "prior_attempt_audit": prior_attempt_audit,
        "human_dependencies_and_prior_exposure": protocol[
            "human_dependencies_and_prior_exposure"
        ],
        "prospective_missing_mechanism_prototype": protocol[
            "prospective_missing_mechanism_prototype"
        ],
        "scope_recommendation": protocol["scope_recommendation"],
        "self_hash_rule": "This manifest cannot hash itself; the subsequent content seal hashes this exact file.",
    }


def assert_packet_matches_seal(
    *,
    root: Path,
    packet: dict[str, Any],
    seal: dict[str, Any],
    generated_paths: list[Path],
) -> dict[str, Any]:
    """Require exact equality between packet base members and final seal bytes."""
    expected_rows = [
        *packet["artifact_inventory"],
        *(file_record(root, path) for path in generated_paths),
    ]

    def keyed(rows: Iterable[dict[str, Any]]) -> dict[str, tuple[str, int]]:
        result: dict[str, tuple[str, int]] = {}
        for row in rows:
            path = row["path"]
            value = (row["sha256"], row["size_bytes"])
            if path in result and result[path] != value:
                raise ValueError(f"conflicting packet/seal record for {path}")
            result[path] = value
        return result

    expected = keyed(expected_rows)
    observed = keyed(seal.get("files", []))
    if expected != observed:
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        changed = sorted(
            path for path in set(expected) & set(observed) if expected[path] != observed[path]
        )
        raise ValueError(
            "packet inventory does not equal final seal members: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )
    return {
        "status": "PASS",
        "packet_base_members": len(packet["artifact_inventory"]),
        "declared_generated_extras": len(generated_paths),
        "seal_members": len(observed),
        "compared_fields": ["path", "sha256", "size_bytes"],
    }


def audit_prior_attempt(
    *, root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    """Verify that the retained first attempt is zero-score and now non-authoritative."""
    history = protocol.get("step_7_recovery_history", {}).get("initial_attempt", {})
    if history.get("status") != "FAILED_INTEGRATION_RACE_NON_AUTHORITATIVE":
        raise ValueError("Step 7 recovery must declare the first attempt non-authoritative")
    retained = verify_bound_files(root, history.get("retained_files", []))
    namespace = resolve(root, history["namespace"])
    recorded_verification = read_json(namespace / "seal-verification.json")
    if recorded_verification.get("status") != "PASS":
        raise ValueError("first attempt did not retain its at-creation PASS record")
    if recorded_verification.get("packet_to_seal_consistency", {}).get("status") != "PASS":
        raise ValueError("first attempt did not retain packet-to-seal consistency")
    summary = read_json(namespace / "finalization-summary.json")
    if (
        summary.get("scored_execution") is not False
        or summary.get("score_rows") != []
        or summary.get("analyzer_or_baseline_dispatched") is not False
        or summary.get("research_tool_calls") != 0
    ):
        raise ValueError("first attempt is not a zero-score finalization")
    current = foundation.verify_seal(
        root=root, manifest=namespace / "content-seal-v1.json"
    )
    if current.get("status") != history.get("required_current_verification"):
        raise ValueError("first-attempt seal must currently fail before recovery")
    if not current.get("mismatches"):
        raise ValueError("first-attempt failed verification lacks a byte mismatch")
    return {
        "schema": "bindcheck.d2.gate-a-prior-attempt-audit/v1",
        "created_at_utc": utc_now(),
        "status": "PASS_FOR_RECOVERY",
        "initial_attempt_disposition": history["status"],
        "retained_files": retained,
        "recorded_at_creation_verification": {
            "status": recorded_verification["status"],
            "manifest_sha256": recorded_verification["manifest_sha256"],
            "packet_to_seal_consistency": recorded_verification[
                "packet_to_seal_consistency"
            ],
        },
        "current_verification": current,
        "scored_execution": False,
        "score_rows": [],
        "analyzer_or_baseline_dispatched": False,
        "research_tool_calls": 0,
        "scientific_retry": False,
        "reason": "Integration-race recovery after a required tracked-document correction; no scientific output was produced.",
    }


def finalize(
    *, root: Path = ROOT, protocol_path: Path = DEFAULT_PROTOCOL, out: Path = DEFAULT_OUT
) -> dict[str, Any]:
    root = root.resolve()
    protocol_path = protocol_path.resolve()
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"refusing to reuse finalization namespace: {out}")

    protocol = read_json(protocol_path)
    verify_bound_files(root, protocol["controlling_artifact_bindings"])
    verify_bound_files(root, protocol["forms"])
    sources = load_sources(root)
    readiness = assess_readiness(protocol, sources)
    prior_attempt_audit = audit_prior_attempt(root=root, protocol=protocol)

    # Resolve and hash every planned seal entry before creating any output.
    seal_entries = [resolve(root, path) for path in protocol["seal_plan"]["entries"]]
    iter_entry_files(root, protocol["seal_plan"]["entries"])

    out.mkdir(parents=True)
    prior_attempt_path = out / "prior-attempt-audit.json"
    write_new_json(prior_attempt_path, prior_attempt_audit)
    run_manifest_path = out / "run-manifest.json"
    source_paths = _source_paths(root)
    foundation.prepare_run_manifest(
        root=root,
        output=run_manifest_path,
        run_id="D2-07-gate-a-blocked-finalization-recovery-01",
        experiment="gate-a-readiness-and-zero-score-seal-recovery",
        inputs=[
            prior_attempt_path,
            root / "results/raw/D2-07/finalization-summary.json",
            root / "results/raw/D2-07/content-seal-v1.json",
            source_paths["step6a_summary"],
            source_paths["step6a_baseline"],
            source_paths["information"],
            source_paths["transformations"],
            source_paths["inventory"],
            source_paths["step6b_summary"],
        ],
        configurations=[
            protocol_path,
            source_paths["step5"],
            source_paths["step6a_protocol"],
            source_paths["step6b_protocol"],
        ],
        seeds=[],
        wall_seconds=protocol["resource_budget"]["blocked_finalization"]["wall_seconds"],
        memory_mib=protocol["resource_budget"]["blocked_finalization"]["memory_mib"],
        max_calls=0,
    )

    created_at = utc_now()
    packet = build_packet_manifest(
        root=root,
        protocol_path=protocol_path,
        protocol=protocol,
        readiness=readiness,
        sources=sources,
        created_at=created_at,
        generated_output_paths=[
            prior_attempt_path,
            run_manifest_path,
            out / "packet-manifest.json",
            out / "finalization-summary.json",
        ],
        prior_attempt_audit=prior_attempt_audit,
    )
    packet_path = out / "packet-manifest.json"
    write_new_json(packet_path, packet)

    summary = {
        "schema": "bindcheck.d2.gate-a-blocked-finalization-summary/v1",
        "created_at_utc": created_at,
        **readiness,
        "authoritative_namespace": "results/raw/D2-07-recovery-01",
        "recovery_of": "results/raw/D2-07",
        "recovery_reason": "Required tracked-document correction after an integration-race finalizer invocation; no scientific output or score was produced.",
        "scientific_retry": False,
        "scored_execution": False,
        "score_rows": [],
        "outcome_counts": {
            "DETECTED": 0,
            "MISSED": 0,
            "UNSUPPORTED": 0,
            "NOT_APPLICABLE": 0,
            "BUILD_FAILED": 0,
            "UNRESOLVED_CANDIDATE_CASES": len(EXPECTED_CASES),
        },
        "construction_evidence_scored": False,
        "historical_smoke_evidence_scored": False,
        "reserved_data_accessed": False,
        "analyzer_or_baseline_dispatched": False,
        "research_tool_calls": 0,
        "network_calls": 0,
        "scientific_retries": 0,
        "memory_enforcement": "NOT_OS_ENFORCED_HASHING_ONLY_FINALIZATION",
        "d2_06b_timing_interpretation": "Retained as forge-command wall time including observed compilation, not compilation-exclusive analysis time.",
        "prototype_implemented": False,
        "scope_recommendation": protocol["scope_recommendation"]["decision"],
        "primary_prototype_experiment_status": protocol["scope_recommendation"][
            "primary_discriminating_experiment"
        ]["status"],
        "decision_rationale": protocol["decision_rationale"],
    }
    summary_path = out / "finalization-summary.json"
    write_new_json(summary_path, summary)

    seal_path = out / "content-seal-v1.json"
    seal = foundation.create_seal(
        root=root,
        output=seal_path,
        version=protocol["seal_plan"]["version"],
        entries=[
            *seal_entries,
            prior_attempt_path,
            run_manifest_path,
            packet_path,
            summary_path,
        ],
    )
    consistency = assert_packet_matches_seal(
        root=root,
        packet=packet,
        seal=seal,
        generated_paths=[
            prior_attempt_path,
            run_manifest_path,
            packet_path,
            summary_path,
        ],
    )
    verification = foundation.verify_seal(root=root, manifest=seal_path)
    if verification["status"] != "PASS":
        raise RuntimeError(f"new content seal failed verification: {verification}")
    verification.update(
        {
            "created_at_utc": utc_now(),
            "post_seal_record_not_sealed_due_to_hash_dependency": True,
            "scored_execution_occurred_before_seal": False,
            "scored_execution_authorized_after_seal": False,
            "packet_to_seal_consistency": consistency,
        }
    )
    write_new_json(out / "seal-verification.json", verification)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="verify bindings and readiness without writing a finalization namespace",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    protocol_path = args.protocol.resolve()
    protocol = read_json(protocol_path)
    verify_bound_files(root, protocol["controlling_artifact_bindings"])
    verify_bound_files(root, protocol["forms"])
    readiness = assess_readiness(protocol, load_sources(root))
    prior_attempt = audit_prior_attempt(root=root, protocol=protocol)
    if args.validate_only:
        readiness["prior_attempt_current_verification"] = prior_attempt[
            "current_verification"
        ]["status"]
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0
    summary = finalize(root=root, protocol_path=protocol_path, out=args.out)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
