#!/usr/bin/env python3
"""Build and exercise the bounded D2 Step 9 development fixtures.

The runner is intentionally unable to run the integrated analyzer, a scored
baseline, or a reserved-data experiment.  It constructs only synthetic,
exposed ``UNREVIEWED_DEVELOPMENT_FIXTURE`` inputs and refuses to overwrite an
existing evidence namespace.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.core.authorization_boundary_v1 import (  # noqa: E402
    BOUNDARY_INPUT_SCHEMA,
    FIXTURE_POLICY_STATUS,
    AuthorizationObligation,
    BoundaryInput,
    BoundedQuery,
    PermissionRecord,
    PolicyRecord,
    ProtectedEffect,
    evaluate_equal_input_arms,
    validate_boundary_input,
)
from bindcheck_d1.roles.compiler_identity_v1 import (  # noqa: E402
    CompilerProvenance,
    ContextIdentity,
    IdentityBundle,
    IdentityFact,
    IdentityRecord,
    ObjectIdentity,
    identity_reference,
    sha256_json,
)


DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-09-authorization-boundary-v1.json"
DEFAULT_OUT = ROOT / "results/raw/D2-09"
VARIANTS = (
    "private-equality-counterexample",
    "matched-positive-control",
    "annotation-only-negative-control",
    "may-producer-negative-control",
    "underapprox-producer-negative-control",
    "unknown-producer-negative-control",
    "unsupported-condition-negative-control",
    "context-mismatch-negative-control",
    "inactive-path-negative-control",
    "alternative-authorization-negative-control",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
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
        raise FileExistsError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _artifact_digest(label: str) -> str:
    return sha256_json({"fixture": "d2-step9", "label": label, "version": 1})


def _identity(
    *,
    slot: str,
    kind: str,
    domain: str,
    actor: str,
    node: str,
    abi_index: int,
    display_name: str | None = None,
) -> IdentityRecord:
    artifact = _artifact_digest("synthetic-compiler-artifact")
    provenance = CompilerProvenance(
        artifact_sha256=artifact,
        compiler_id="synthetic-step9-fixture",
        compiler_version="1.0.0",
        artifact_schema="bindcheck.synthetic-compiler-fixture/v1",
        evidence_kind="FIXTURE_NODE_AND_ABI",
        node_id=node,
        abi_index=abi_index,
        source_sha256=_artifact_digest("synthetic-source"),
        support="SUPPORTED",
        display_path="synthetic/d2-step9.fixture",
        display_span=f"node:{node}",
    )
    return IdentityRecord(
        object_identity=ObjectIdentity(
            kind=kind,
            logical_slot=slot,
            representation="bounded-integer",
            state_scope="single-transition",
            encoding="unsigned-canonical",
            value_type="u8",
        ),
        context_identity=ContextIdentity(
            kind="synthetic-execution-context",
            domain=domain,
            deployment="fixture-deployment",
            state_version="state-v1",
            actor=actor,
            epoch="fixture-epoch-0",
        ),
        provenance=(provenance,),
        derivation_class="DERIVED",
        support="SUPPORTED",
        display_hints=(("fixture_name", display_name or slot),),
    )


def _const(value: Any) -> dict[str, Any]:
    return {"const": value}


def _var(name: str) -> dict[str, Any]:
    return {"var": name}


def _eq(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": "PREDICATE",
        "predicate": {"op": "eq", "left": dict(left), "right": dict(right)},
    }


def _fields(quantity: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        "action": _const("transfer"),
        "asset": _const("fixture-token"),
        "quantity": dict(quantity),
        "beneficiary": _const("fixture-beneficiary"),
        "domain": _const("fixture-settlement-domain"),
        "state_version": _const("state-v1"),
    }


def build_fixture(variant: str) -> BoundaryInput:
    """Construct one deterministic synthetic input for a declared variant."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown Step 9 fixture variant: {variant}")
    producer = _identity(
        slot="producer-public-p",
        kind="producer-public-value",
        domain="fixture-producer-domain",
        actor="fixture-prover",
        node="producer-p",
        abi_index=0,
    )
    private_x = _identity(
        slot="producer-private-x",
        kind="producer-private-value",
        domain="fixture-producer-domain",
        actor="fixture-prover",
        node="private-x",
        abi_index=1,
    )
    authorized_x = _identity(
        slot="authenticated-authorized-x",
        kind="authenticated-policy-value",
        domain="fixture-settlement-domain",
        actor="fixture-authorizer",
        node="authorized-x",
        abi_index=2,
    )
    same_name_other_object = _identity(
        slot="other-logical-authorized-x",
        kind="authenticated-policy-value",
        domain="fixture-settlement-domain",
        actor="fixture-authorizer",
        node="other-logical-authorized-x",
        abi_index=3,
        display_name="authenticated-authorized-x",
    )
    same_object_other_context = _identity(
        slot="authenticated-authorized-x",
        kind="authenticated-policy-value",
        domain="other-settlement-domain",
        actor="other-authorizer",
        node="authorized-x-other-context",
        abi_index=4,
        display_name="authenticated-authorized-x",
    )
    effect_identity = _identity(
        slot="transfer-occurrence-0",
        kind="protected-effect-occurrence",
        domain="fixture-settlement-domain",
        actor="fixture-consumer",
        node="effect-0",
        abi_index=5,
    )

    private_relation = variant == "private-equality-counterexample"
    producer_condition = _eq(
        _var("p"), _var("private_x" if private_relation else "authorized_x")
    )
    producer_fact = IdentityFact(
        fact_kind="producer_guarantee",
        subject_identity_ref=identity_reference(authorized_x),
        object_identity_ref=identity_reference(producer),
        quantifier=("MAY" if variant == "may-producer-negative-control" else "MUST"),
        condition=(
            {"kind": "UNCONDITIONAL"}
            if variant == "unsupported-condition-negative-control"
            else producer_condition
        ),
        approximation=(
            "UNDER_APPROXIMATION"
            if variant == "underapprox-producer-negative-control"
            else "EXACT"
        ),
        derivation_class=(
            "ANNOTATED" if variant == "annotation-only-negative-control" else "DERIVED"
        ),
        support=("UNKNOWN" if variant == "unknown-producer-negative-control" else "SUPPORTED"),
        reason=(
            "FIXTURE_EXTRACTION_UNRESOLVED"
            if variant == "unknown-producer-negative-control"
            else None
        ),
        provenance_refs=(producer.provenance_hash,),
        annotation_refs=(
            (f"external:annotation:{_artifact_digest('annotation:fixture-relation')}",)
            if variant == "annotation-only-negative-control"
            else ()
        ),
    )
    reliance_fact = IdentityFact(
        fact_kind="consumer_used",
        subject_identity_ref=identity_reference(effect_identity),
        object_identity_ref=identity_reference(producer),
        quantifier="MAY",
        condition={"kind": "ALWAYS"},
        approximation="OVER_APPROXIMATION",
        derivation_class="DERIVED",
        support="SUPPORTED",
        provenance_refs=(effect_identity.provenance_hash,),
        parent_fact_ids=(producer_fact.fact_id,),
    )
    bundle = IdentityBundle(
        bundle_name=f"d2-step9-{variant}",
        identities=(
            producer,
            private_x,
            authorized_x,
            same_name_other_object,
            same_object_other_context,
            effect_identity,
        ),
        facts=(producer_fact, reliance_fact),
        input_sha256=(
            _artifact_digest("synthetic-compiler-artifact"),
            _artifact_digest(f"fixture-definition:{variant}"),
        ),
        limitations=(
            "synthetic exposed fixture only",
            "not compiler extraction from a scored target",
            "finite u8 subset restricted to values zero and one",
        ),
    )

    authorizing_ref = identity_reference(
        same_object_other_context
        if variant == "context-mismatch-negative-control"
        else authorized_x
    )
    permission = PermissionRecord(
        permission_id="fixture-permission-transfer",
        authorizing_identity_ref=authorizing_ref,
        protected_effect_identity_ref=identity_reference(effect_identity),
        fields=_fields(_var("authorized_x")),
        condition={"kind": "ALWAYS"},
    )
    policy = PolicyRecord(
        policy_id="d2-step9-unreviewed-fixture-policy",
        version="1.0.0",
        review_status=FIXTURE_POLICY_STATUS,
        permissions=(permission,),
        source_sha256=(_artifact_digest("unreviewed-fixture-policy"),),
        limitations=(
            "AI-authored mechanical fixture; no human adoption or review",
            "never eligible for scoring or a policy-correctness claim",
        ),
    )
    effect = ProtectedEffect(
        effect_id="fixture-effect-transfer-0",
        protected_effect_identity_ref=identity_reference(effect_identity),
        fields=_fields(_var("p")),
        path_condition=(
            {"kind": "NEVER"}
            if variant == "inactive-path-negative-control"
            else {"kind": "ALWAYS"}
        ),
        source_fact_ids=(reliance_fact.fact_id,),
        alternative_authorization_refs=(
            ("unreviewed:alternative-mechanism",)
            if variant == "alternative-authorization-negative-control"
            else ()
        ),
    )
    obligation = AuthorizationObligation(
        obligation_id="fixture-obligation-transfer-0",
        protected_effect_id=effect.effect_id,
        authorization_identity_ref=identity_reference(authorized_x),
        protected_effect_identity_ref=identity_reference(effect_identity),
        producer_fact_ids=(producer_fact.fact_id,),
        reliance_fact_ids=(reliance_fact.fact_id,),
        fields=_fields(_var("p")),
        activation={"kind": "ALWAYS"},
        discharge={"kind": "ALWAYS"},
        assumption_refs=("assumption:synthetic-finite-integer-interpretation",),
    )
    return BoundaryInput(
        case_id=f"D2-09-{variant.upper()}",
        identity_bundle=bundle.to_dict(),
        policy=policy,
        obligations=(obligation,),
        effects=(effect,),
        query=BoundedQuery(
            variable_domains={"p": (0, 1), "private_x": (0, 1)},
            attacker_controlled=("p", "private_x"),
            fixed_authenticated_context={"authorized_x": 0},
            max_assignments=4,
        ),
        assumptions=(
            "synthetic finite integer equality has its ordinary mathematical meaning",
        ),
        limitations=(
            "UNREVIEWED_DEVELOPMENT_FIXTURE",
            "no primary target, scored analyzer, proof, replay, or reserved data",
        ),
    )


def _resolve_repo_path(path_text: str) -> Path:
    path = (ROOT / path_text).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"bound path leaves repository: {path_text}") from exc
    return path


def validate_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    if protocol.get("schema") != "bindcheck.d2.authorization-boundary-protocol/v1":
        raise ValueError("unexpected Step 9 protocol schema")
    boundary = protocol.get("execution_boundary", {})
    if boundary.get("fixture_label") != FIXTURE_POLICY_STATUS:
        raise ValueError("protocol fixture label is not the required unreviewed label")
    for prohibited in (
        "scored_execution_authorized",
        "reserved_data_authorized",
        "retroactive_gate_a_rescore_authorized",
    ):
        if boundary.get(prohibited) is not False:
            raise ValueError(f"protocol must set {prohibited}=false")
    if protocol.get("research_verdict") != "UNKNOWN":
        raise ValueError("Step 9 protocol research verdict must remain UNKNOWN")
    records: list[dict[str, Any]] = []
    for row in protocol.get("artifact_bindings", []):
        path = _resolve_repo_path(row["path"])
        actual = sha256_file(path)
        if actual != row["sha256"]:
            raise ValueError(f"artifact binding mismatch for {row['path']}: {actual}")
        records.append({"path": row["path"], "sha256": actual, "role": row["role"]})
    return {"status": "PASS", "artifact_bindings": records}


def _expected_mechanical_state(variant: str) -> str:
    return {
        "private-equality-counterexample": "MISMATCH_CANDIDATE",
        "matched-positive-control": "ESTABLISHED",
        "annotation-only-negative-control": "UNKNOWN",
        "may-producer-negative-control": "UNKNOWN",
        "underapprox-producer-negative-control": "UNKNOWN",
        "unknown-producer-negative-control": "UNKNOWN",
        "unsupported-condition-negative-control": "UNKNOWN",
        "context-mismatch-negative-control": "MISMATCH_CANDIDATE",
        "inactive-path-negative-control": "UNKNOWN",
        "alternative-authorization-negative-control": "UNKNOWN",
    }[variant]


def exercise_fixtures() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        case_start = time.perf_counter()
        boundary = build_fixture(variant)
        validation = validate_boundary_input(boundary)
        result = evaluate_equal_input_arms(boundary)
        case_wall_seconds = time.perf_counter() - case_start
        mechanical_states = {
            arm: value["obligation_results"][0]["mechanical_state"]
            for arm, value in result["results"].items()
        }
        effective_states = {
            arm: value["state"] for arm, value in result["results"].items()
        }
        expected = _expected_mechanical_state(variant)
        if set(mechanical_states.values()) != {expected}:
            raise ValueError(
                f"known-answer mismatch for {variant}: {mechanical_states} != {expected}"
            )
        if set(effective_states.values()) != {"UNKNOWN"}:
            raise ValueError(f"fixture escaped fail-closed policy gate: {variant}")
        if not result["semantic_parity"]:
            raise ValueError(f"equal-input arms diverged for {variant}")
        artifacts[variant] = {
            "input": boundary.canonical(),
            "validation": validation,
            "result": result,
        }
        rows.append(
            {
                "variant": variant,
                "case_id": boundary.case_id,
                "input_sha256": boundary.input_sha256,
                "mechanical_state": expected,
                "effective_state": "UNKNOWN",
                "semantic_parity": True,
                "score_eligible": False,
                "evidence_grade": "E0",
                "assignment_space": validation["assignment_space"],
                "assignment_limit": boundary.query.max_assignments,
                "arm_assignment_counts": {
                    arm: value["obligation_results"][0]["assignment_count"]
                    for arm, value in result["results"].items()
                },
                "arm_relying_assignment_counts": {
                    arm: value["obligation_results"][0]["relying_assignment_count"]
                    for arm, value in result["results"].items()
                },
                "case_wall_seconds": case_wall_seconds,
            }
        )
    return rows, artifacts


def _file_records(out: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(item for item in out.rglob("*") if item.is_file()):
        if path.name == "checksums.sha256":
            continue
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def run(protocol_path: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite evidence namespace: {out}")
    started_at = utc_now()
    start = time.perf_counter()
    protocol = read_json(protocol_path)
    protocol_check = validate_protocol(protocol)
    rows, artifacts = exercise_fixtures()

    out.mkdir(parents=True, exist_ok=False)
    for variant, values in artifacts.items():
        fixture_dir = out / variant
        write_new_json(fixture_dir / "boundary-input.json", values["input"])
        write_new_json(fixture_dir / "validation.json", values["validation"])
        write_new_json(fixture_dir / "equal-arms-result.json", values["result"])

    elapsed = time.perf_counter() - start
    counts = {state: 0 for state in ("ESTABLISHED", "MISMATCH_CANDIDATE", "UNKNOWN")}
    for row in rows:
        counts[row["mechanical_state"]] += 1
    summary = {
        "schema": "bindcheck.d2.authorization-boundary-summary/v1",
        "status": "COMPLETE_MECHANICAL_FIXTURE_ONLY",
        "research_verdict": "UNKNOWN",
        "fixture_label": FIXTURE_POLICY_STATUS,
        "case_count": len(rows),
        "mechanical_state_counts": counts,
        "effective_state_counts": {"UNKNOWN": len(rows)},
        "equal_input_arm_parity_count": sum(row["semantic_parity"] for row in rows),
        "score_rows": [],
        "scored_execution": False,
        "reserved_data_accessed": False,
        "rows": rows,
        "claim_limit": (
            "Synthetic mechanical E0 evidence only. Mechanical states are not "
            "policy-reviewed findings, Gate A scores, or primary outcomes."
        ),
    }
    write_new_json(out / "summary.json", summary)
    manifest = {
        "schema": "bindcheck.d2.authorization-boundary-run-manifest/v1",
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "command": [
            sys.executable,
            str(Path(__file__).relative_to(ROOT)),
            "--protocol",
            str(protocol_path.relative_to(ROOT)),
            "--out",
            str(out.relative_to(ROOT)),
        ],
        "python": sys.version,
        "platform": platform.platform(),
        "protocol": {
            "path": protocol_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(protocol_path),
        },
        "protocol_validation": protocol_check,
        "machine_wall_seconds": elapsed,
        "machine_hour_cap": protocol["budget"]["machine_hours"],
        "machine_cap_exceeded": elapsed > protocol["budget"]["machine_hours"] * 3600,
        "effort_accounting": {
            "human_researcher_time": "NOT_MEASURED_DO_NOT_INFER",
            "human_policy_authoring_or_review": "NOT_PERFORMED",
            "ai_agent_is_not_a_human_role": True,
            "setup_items": [
                "versioned core module and public exports",
                "immutable raw namespace and overwrite refusal",
                "protocol/hash validation and deterministic fixture builder",
            ],
            "specification_items": [
                "supported fragment and attacker/fixed-context boundary",
                "common policy/obligation/effect schemas",
                "fact admissibility and approximation rules",
                "ten bounded known-answer controls",
            ],
            "setup_item_count": 3,
            "specification_item_count": 4,
            "researcher_day_cap": protocol["budget"]["researcher_days"],
            "researcher_cap_status": "UNRESOLVED_WITHOUT_HUMAN_TIME_LOG",
        },
        "execution_boundary": {
            "scored_execution": False,
            "integrated_analyzer_dispatched": False,
            "baseline_dispatched": False,
            "proof_or_replay_dispatched": False,
            "network_access": False,
            "reserved_data_accessed": False,
        },
    }
    write_new_json(out / "run-manifest.json", manifest)
    records = _file_records(out)
    checksums = "".join(f"{row['sha256']}  {row['path']}\n" for row in records)
    checksums_path = out / "checksums.sha256"
    if checksums_path.exists():
        raise FileExistsError(f"refusing to overwrite existing record: {checksums_path}")
    checksums_path.write_text(checksums)
    return {
        **summary,
        "run_manifest_sha256": sha256_file(out / "run-manifest.json"),
        "summary_sha256": sha256_file(out / "summary.json"),
        "checksums_sha256": sha256_file(checksums_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    protocol_path = args.protocol.resolve()
    if args.validate_only:
        protocol = read_json(protocol_path)
        result = {
            "protocol": validate_protocol(protocol),
            "fixture_rows": exercise_fixtures()[0],
            "status": "PASS",
        }
    else:
        result = run(protocol_path, args.out.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
