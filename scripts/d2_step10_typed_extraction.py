#!/usr/bin/env python3
"""Generate bounded, unscored D2 Step 10 extraction-trust evidence.

Only synthetic exposed fixtures and existing compiler-free regressions are
used. The runner does not compile targets, prove, inspect reserved data,
infer policy, score Gate A, or modify the integrated analyzer.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.core.authorization_boundary_v1 import (  # noqa: E402
    evaluate_equal_input_arms,
    validate_boundary_input,
)
from bindcheck_d1.roles.compiler_identity_v1 import (  # noqa: E402
    FIXTURE_LABEL,
    MappingCertificate,
    MappingEntry,
    sha256_json,
)
from bindcheck_d1.typed_extraction_v1 import (  # noqa: E402
    TypedExtractionError,
    audit_d1p40_regressions,
    build_inventory,
    validate_inventory,
)
from tests.test_d2_step10_typed_extraction import (  # noqa: E402
    _boundary,
    _build,
    _exported_facts,
    _fixture_bundle,
    _static_analysis,
)


PROTOCOL_SCHEMA = "bindcheck.d2.step10-protocol/v2"
DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-10-typed-extraction-v2.json"
DEFAULT_OUT = ROOT / "results/raw/D2-10/run-02"


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
        raise FileExistsError(f"refusing to overwrite immutable evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def resolve_repo_path(path_text: str) -> Path:
    candidate = Path(path_text)
    resolved = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"protocol path escapes repository: {path_text}") from error
    return resolved


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(f"expected regular file: {path}")
    return {
        "path": resolved.relative_to(ROOT.resolve()).as_posix(),
        "sha256": sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def validate_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    if protocol.get("schema") != PROTOCOL_SCHEMA:
        raise ValueError("unsupported Step 10 protocol schema")
    expected = {
        "fixture_label": FIXTURE_LABEL,
        "score_enabled": False,
        "reserved_data_allowed": False,
        "network_allowed": False,
        "research_verdict": "UNKNOWN",
    }
    for field, value in expected.items():
        if protocol.get(field) != value:
            raise ValueError(f"invalid Step 10 protocol boundary: {field}")
    records = protocol.get("input_files")
    if not isinstance(records, list) or not records:
        raise ValueError("Step 10 protocol requires hash-bound inputs")
    verified = []
    for record in records:
        observed = file_record(resolve_repo_path(str(record["path"])))
        if observed["sha256"] != record.get("sha256"):
            raise ValueError(f"protocol input hash mismatch: {record['path']}")
        if observed["size_bytes"] != record.get("size_bytes"):
            raise ValueError(f"protocol input size mismatch: {record['path']}")
        verified.append(observed)
    return {"status": "PASS", "verified_inputs": verified}


def fact_type_inventory(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Replay the v1 inventory and apply the explicit v2 semantic deltas."""
    base_record = protocol.get("fact_type_inventory_base")
    if not isinstance(base_record, Mapping):
        raise ValueError("Step 10 v2 requires a hash-bound fact inventory base")
    base_path = resolve_repo_path(str(base_record["path"]))
    observed = file_record(base_path)
    if (
        observed["sha256"] != base_record.get("sha256")
        or observed["size_bytes"] != base_record.get("size_bytes")
    ):
        raise ValueError("fact inventory base hash mismatch")
    base = read_json(base_path)
    rows = {
        str(item["id"]): deepcopy(item)
        for item in base.get("fact_type_inventory", [])
    }
    corrections = protocol.get("fact_type_inventory_corrections")
    if not isinstance(corrections, list) or not corrections:
        raise ValueError("Step 10 v2 requires explicit fact inventory corrections")
    for correction in corrections:
        fact_id = str(correction.get("id"))
        if fact_id not in rows or not isinstance(correction.get("replace"), Mapping):
            raise ValueError(f"invalid fact inventory correction: {fact_id}")
        rows[fact_id].update(deepcopy(dict(correction["replace"])))
    return [rows[fact_id] for fact_id in sorted(rows)]


def _identity_mapping(value: Any) -> dict[str, Any]:
    return MappingCertificate(
        transformation_id="TR-IDENTITY-CONTROL",
        source_bundle_id="fixture-source-bundle",
        target_bundle_id="fixture-target-bundle",
        entries=(MappingEntry(
            logical_slot="public-value-0",
            from_identity_ref=value.reference(),
            to_identity_ref=value.reference(),
            from_abi_index=0,
            to_abi_index=0,
        ),),
        source_identity_count=1,
        target_identity_count=1,
        evidence_sha256=(sha256_json({"mapping": "identity-control"}),),
        mapping_source_refs=("external:d2-step10-identity-control",),
    ).to_dict()


def exercise(protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise exact, conditional, approximate, mapping, and adversarial rows."""
    exact, identities = _build()
    exact_validation = validate_inventory(exact)
    exact_boundary = _boundary(exact, identities)
    exact_boundary_validation = validate_boundary_input(exact_boundary)
    exact_parity = evaluate_equal_input_arms(exact_boundary)
    if exact_boundary_validation["identity_chain_status"] != "PASS":
        raise RuntimeError("exact fixture identity chain did not validate")
    if not exact_parity["semantic_parity"] or exact_parity["research_verdict"] != "UNKNOWN":
        raise RuntimeError("exact fixture violated equal-input/fail-closed invariant")

    controls: list[dict[str, Any]] = []

    dynamic = _static_analysis()
    dynamic["producer"]["public_leaves"][0]["memory_dependency_status"] = "unresolved-dynamic"
    dynamic_inventory, _ = _build(analysis=dynamic)
    dynamic_fact = _exported_facts(dynamic_inventory)["producer_binding_candidate"]
    controls.append({
        "id": "dynamic-memory-alias",
        "status": "PASS" if (
            dynamic_fact["support"] == "UNKNOWN"
            and dynamic_fact["quantifier"] == "MAY"
            and dynamic_fact["approximation"] == "OVER_APPROXIMATION"
        ) else "FAIL",
        "observed": dynamic_fact,
    })

    prefix = _static_analysis()
    prefix["producer"]["public_leaves"][0]["binding_condition"] = {
        "kind": "prefix", "extent": "surface_name_n",
    }
    prefix_unknown, _ = _build(analysis=deepcopy(prefix))
    prefix_bound, _ = _build(
        analysis=prefix,
        condition_variables={"surface_name_n": "authenticated_extent"},
    )
    unknown_fact = _exported_facts(prefix_unknown)["producer_binding_candidate"]
    bound_fact = _exported_facts(prefix_bound)["producer_binding_candidate"]
    controls.append({
        "id": "branch-boundary-prefix",
        "status": "PASS" if (
            unknown_fact["support"] == "UNKNOWN"
            and bound_fact["condition"].get("kind") == "PREDICATE"
        ) else "FAIL",
        "unbacked": unknown_fact,
        "compiler_backed": bound_fact,
    })

    inactive = _static_analysis()
    inactive["producer"]["public_leaves"][0]["binding_condition"] = {"kind": "never"}
    inactive["consumer"]["public_words"][0]["reliance_condition"] = {"kind": "never"}
    inactive_inventory, inactive_identities = _build(analysis=inactive)
    inactive_result = evaluate_equal_input_arms(
        _boundary(inactive_inventory, inactive_identities)
    )
    inactive_obligation = inactive_result["results"]["full-bindcheck"][
        "obligation_results"
    ][0]
    controls.append({
        "id": "inactive-padding-nonvacuity",
        "status": "PASS" if inactive_obligation["mechanical_state"] == "UNKNOWN" else "FAIL",
        "observed": inactive_obligation,
    })

    multiple_paths = _static_analysis()
    multiple_paths["consumer"]["public_words"][0]["reliance_condition"] = {
        "kind": "any", "conditions": [{"kind": "always"}, {"kind": "never"}],
    }
    multiple_inventory, _ = _build(analysis=multiple_paths)
    multiple_fact = _exported_facts(multiple_inventory)["consumer_reliance_candidate"]
    controls.append({
        "id": "multiple-verifier-paths-unjoined",
        "status": "PASS" if multiple_fact["support"] == "UNKNOWN" else "FAIL",
        "observed": multiple_fact,
    })

    bundle, mapping_identities = _fixture_bundle()
    mapping = _identity_mapping(mapping_identities["value"])
    mapping_inventory = build_inventory(
        _static_analysis(),
        bundle,
        mappings=(mapping,),
        authorization_identity_by_index={0: mapping_identities["auth"].reference()},
        effect_identity_by_index={0: mapping_identities["effect"].reference()},
    )
    mapping_result = evaluate_equal_input_arms(
        _boundary(mapping_inventory, mapping_identities)
    )
    mapping_obligation = mapping_result["results"]["full-bindcheck"][
        "obligation_results"
    ][0]
    controls.append({
        "id": "mapping-certificate-not-bound-by-step9",
        "status": "PASS" if (
            mapping_obligation["mechanical_state"] == "UNKNOWN"
            and "PRODUCER_MAPPING_CERTIFICATE_NOT_BOUND" in mapping_obligation["reason_codes"]
        ) else "FAIL",
        "mapping_id": mapping["mapping_id"],
        "observed": mapping_obligation,
    })

    value = mapping_identities["value"]
    incompatible = replace(
        value,
        object_identity=replace(value.object_identity, encoding="field-modulus-canonical"),
    )
    incompatible_mapping = MappingCertificate(
        transformation_id="TR-ENCODING-MISMATCH",
        source_bundle_id="fixture-source-bundle",
        target_bundle_id="fixture-target-bundle",
        entries=(MappingEntry(
            logical_slot="public-value-0",
            from_identity_ref=value.reference(),
            to_identity_ref=incompatible.reference(),
            from_abi_index=0,
            to_abi_index=0,
        ),),
        source_identity_count=1,
        target_identity_count=1,
        evidence_sha256=(sha256_json({"mapping": "encoding-mismatch"}),),
        mapping_source_refs=("external:d2-step10-encoding-mismatch",),
    ).to_dict()
    encoding_reason = None
    try:
        build_inventory(
            _static_analysis(),
            bundle,
            mappings=(incompatible_mapping,),
            authorization_identity_by_index={0: mapping_identities["auth"].reference()},
            effect_identity_by_index={0: mapping_identities["effect"].reference()},
        )
    except TypedExtractionError as error:
        encoding_reason = str(error)
    controls.append({
        "id": "field-integer-encoding-mismatch",
        "status": "PASS" if encoding_reason == "IDENTITY_MAPPING_NOT_SEMANTIC_BIJECTION" else "FAIL",
        "observed_reason": encoding_reason,
    })

    unmapped = _static_analysis()
    unmapped["producer"]["public_leaves"][0]["public_index"] = 1
    unmapped["consumer"]["public_words"][0]["index"] = 1
    unmapped["consumer"]["effect_word_indices"] = [1]
    unmapped["extent_facts"]["coverage"][0]["public_index"] = 1
    unmapped_inventory, _ = _build(analysis=unmapped)
    controls.append({
        "id": "unmapped-public-input",
        "status": "PASS" if unmapped_inventory["unmapped_public_indices"] == [1] else "FAIL",
        "observed": {
            "status": unmapped_inventory["status"],
            "unmapped_public_indices": unmapped_inventory["unmapped_public_indices"],
        },
    })

    adversarial: list[dict[str, Any]] = []
    cases = (
        (
            "same-display-name-different-object", "same_name_other_object", "effect",
            "auth", "effect", "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
        ),
        (
            "same-object-different-context", "same_object_other_context", "effect",
            "auth", "effect", "PRODUCER_AUTHORIZATION_IDENTITY_MISMATCH",
        ),
        (
            "swapped-effect-identity", "auth", "auth",
            "auth", "effect", "RELIANCE_PROTECTED_EFFECT_IDENTITY_MISMATCH",
        ),
    )
    for case_id, export_auth, export_effect, expected_auth, expected_effect, reason in cases:
        inventory, case_identities = _build(
            auth_key=export_auth, effect_key=export_effect,
        )
        boundary = _boundary(
            inventory, case_identities,
            auth_key=expected_auth, effect_key=expected_effect,
        )
        validation = validate_boundary_input(boundary)
        result = evaluate_equal_input_arms(boundary)
        obligation = result["results"]["full-bindcheck"]["obligation_results"][0]
        issue_codes = sorted({
            item["reason_code"] for item in validation["identity_chain_issues"]
        })
        adversarial.append({
            "id": case_id,
            "status": "PASS" if (
                validation["identity_chain_status"] == "UNKNOWN"
                and obligation["mechanical_state"] == "UNKNOWN"
                and reason in issue_codes
            ) else "FAIL",
            "expected_reason": reason,
            "identity_chain_status": validation["identity_chain_status"],
            "identity_chain_issues": validation["identity_chain_issues"],
            "mechanical_state": obligation["mechanical_state"],
            "effective_state": obligation["state"],
        })

    d1p40 = audit_d1p40_regressions()
    if d1p40["status"] != "PASS":
        raise RuntimeError("D1P-40 permanent regression failed")
    if any(row["status"] != "PASS" for row in (*controls, *adversarial)):
        raise RuntimeError("one or more Step 10 controls failed")

    return {
        "typed_inventory": exact,
        "typed_inventory_validation": exact_validation,
        "boundary_parity": exact_parity,
        "controls": {
            "schema": "bindcheck.d2.step10-controls/v2",
            "fixture_label": FIXTURE_LABEL,
            "status": "PASS",
            "research_verdict": "UNKNOWN",
            "rows": controls,
        },
        "adversarial": {
            "schema": "bindcheck.d2.step10-adversarial/v2",
            "fixture_label": FIXTURE_LABEL,
            "status": "PASS",
            "research_verdict": "UNKNOWN",
            "rows": adversarial,
            "pre_result_defect": {
                "status": "FIXED_BEFORE_STEP10_RESULT",
                "description": (
                    "The initial Step9 validator checked fact IDs but not the complete "
                    "producer-authorization/value/reliance-effect identity chain."
                ),
                "permanent_regression": "same/object/context/effect swaps remain UNKNOWN",
            },
        },
        "d1p40": d1p40,
        "fact_type_inventory": {
            "schema": "bindcheck.d2.step10-fact-type-inventory/v2",
            "fixture_label": FIXTURE_LABEL,
            "research_verdict": "UNKNOWN",
            "rows": fact_type_inventory(protocol),
        },
    }


def run(protocol_path: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise FileExistsError(f"refusing to overwrite evidence namespace: {out}")
    protocol = read_json(protocol_path)
    protocol_check = validate_protocol(protocol)
    started = time.monotonic()
    evidence = exercise(protocol)
    elapsed = time.monotonic() - started
    out.mkdir(parents=True, exist_ok=False)

    outputs = {
        "typed-inventory.json": evidence["typed_inventory"],
        "typed-inventory-validation.json": evidence["typed_inventory_validation"],
        "boundary-parity.json": evidence["boundary_parity"],
        "condition-and-approximation-controls.json": evidence["controls"],
        "adversarial-results.json": evidence["adversarial"],
        "d1p40-regressions.json": evidence["d1p40"],
        "fact-type-inventory.json": evidence["fact_type_inventory"],
    }
    for name, value in outputs.items():
        write_new_json(out / name, value)

    summary = {
        "schema": "bindcheck.d2.step10-run-summary/v2",
        "fixture_label": FIXTURE_LABEL,
        "status": "PASS",
        "research_verdict": "UNKNOWN",
        "score_eligible": False,
        "reserved_data_used": False,
        "network_used": False,
        "external_compiler_or_prover_calls": 0,
        "d1p40_regressions": 5,
        "semantic_controls": len(evidence["controls"]["rows"]),
        "adversarial_controls": len(evidence["adversarial"]["rows"]),
        "identity_chain_status": "PASS",
        "equal_input_semantic_parity": evidence["boundary_parity"]["semantic_parity"],
        "effective_result": "UNKNOWN_UNREVIEWED_DEVELOPMENT_FIXTURE",
        "supersedes_raw_run": "results/raw/D2-10/run-01",
        "limitations": [
            "Synthetic construction and compiler-free regressions only.",
            "No human-reviewed policy, scored case, proof, or committed effect.",
            "Targeted checks do not prove universal extraction soundness.",
        ],
    }
    write_new_json(out / "run-summary.json", summary)

    manifest = {
        "schema": "bindcheck.d2.step10-run-manifest/v2",
        "fixture_label": FIXTURE_LABEL,
        "started_at_utc": utc_now(),
        "protocol": file_record(protocol_path),
        "protocol_validation": protocol_check,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "runtime_seconds": round(elapsed, 6),
        "outputs_before_manifest": [
            file_record(out / name) for name in sorted((*outputs, "run-summary.json"))
        ],
        "research_verdict": "UNKNOWN",
        "score_eligible": False,
    }
    write_new_json(out / "run-manifest.json", manifest)
    sealed = [file_record(path) for path in sorted(out.iterdir())]
    seal = {
        "schema": "bindcheck.d2.step10-content-seal/v2",
        "fixture_label": FIXTURE_LABEL,
        "status": "PASS",
        "protocol_sha256": sha256_file(protocol_path),
        "sealed_file_count": len(sealed),
        "files": sealed,
        "research_verdict": "UNKNOWN",
        "score_eligible": False,
    }
    write_new_json(out / "content-seal-v1.json", seal)
    return summary | {
        "out": out.resolve().relative_to(ROOT.resolve()).as_posix(),
        "protocol_sha256": sha256_file(protocol_path),
        "seal_sha256": sha256_file(out / "content-seal-v1.json"),
        "sealed_file_count": len(sealed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    protocol_path = args.protocol.resolve()
    protocol = read_json(protocol_path)
    protocol_check = validate_protocol(protocol)
    if args.validate_only:
        evidence = exercise(protocol)
        print(json.dumps({
            "status": "PASS",
            "protocol": protocol_check,
            "d1p40": evidence["d1p40"]["status"],
            "controls": evidence["controls"]["status"],
            "adversarial": evidence["adversarial"]["status"],
            "research_verdict": "UNKNOWN",
        }, indent=2, sort_keys=True))
        return 0
    print(json.dumps(run(protocol_path, args.out.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
