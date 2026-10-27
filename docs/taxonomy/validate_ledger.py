#!/usr/bin/env python3
"""Validate the schema and six AI-written illustrative fixtures, without network I/O."""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.validators import validator_for


ROOT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(), object_pairs_hook=unique_keys)


def pointer(parts):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def errors_with_context(errors):
    for error in errors:
        yield error
        yield from errors_with_context(error.context)


def local_references_only(value):
    if isinstance(value, dict):
        if "$ref" in value and not value["$ref"].startswith("#/"):
            raise ValueError("Fixture validation must not resolve remote references")
        for child in value.values():
            local_references_only(child)
    elif isinstance(value, list):
        for child in value:
            local_references_only(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="New JSON result file relative to docs/taxonomy/")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve() if args.output else None
    if output and (not output.is_relative_to(ROOT) or output.exists()):
        parser.error("--output must be a new file inside docs/taxonomy/")

    pins = {}
    for line in (ROOT / "validation-requirements.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            package, expected = line.split("==")
            installed = version(package)
            if installed != expected:
                raise RuntimeError(f"Pin mismatch: {package}: {installed} != {expected}")
            pins[package] = installed

    schema_path = ROOT / "ledger.schema.json"
    schema = load(schema_path)
    if validator_for(schema) is not Draft202012Validator:
        raise RuntimeError("Schema does not select the standard Draft 2020-12 validator")
    local_references_only(schema)
    Draft202012Validator.check_schema(schema)
    auxiliary_schema_results = []
    for name in ["planner-approval.schema.json", "grouped-families.schema.json",
                 "candidate-list-input.schema.json"]:
        auxiliary_path = ROOT / name
        auxiliary = load(auxiliary_path)
        if validator_for(auxiliary) is not Draft202012Validator:
            raise RuntimeError(f"{name} does not select Draft 2020-12")
        local_references_only(auxiliary)
        Draft202012Validator.check_schema(auxiliary)
        auxiliary_schema_results.append({"file": name, "sha256": sha256(auxiliary_path),
                                         "meta_schema_valid": True})
    checker = FormatChecker(formats=["date", "date-time"])
    format_controls = []
    for fmt, value, expected in [
        ("date", "2026-10-26", True),
        ("date", "2026-02-30", False),
        ("date-time", "2026-10-26T00:00:00Z", True),
        ("date-time", "2026-10-26T00:00:00", False),
    ]:
        actual = checker.conforms(value, fmt)
        if actual != expected:
            raise RuntimeError(f"Format assertion unavailable or incorrect: {fmt}, {value}")
        format_controls.append({"format": fmt, "value": value, "expected_valid": expected,
                                "actual_valid": actual, "passed": True})

    validator = Draft202012Validator(schema, format_checker=checker)
    search_plan_path = ROOT / "search-plan-v0.2.0.json"
    search_plan_envelope = load(search_plan_path)
    envelope_schema = copy.deepcopy(schema["$defs"]["search_plan_envelope"])
    envelope_schema["$schema"] = schema["$schema"]
    envelope_schema["$defs"] = schema["$defs"]
    envelope_validator = Draft202012Validator(envelope_schema, format_checker=checker)
    envelope_errors = list(envelope_validator.iter_errors(search_plan_envelope))
    if envelope_errors:
        raise RuntimeError("search-plan-v0.2.0.json is invalid against search_plan_envelope")
    canonical_plan = json.dumps(
        search_plan_envelope["search_plan"], sort_keys=True,
        separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    canonical_plan_sha256 = hashlib.sha256(canonical_plan).hexdigest()
    if canonical_plan_sha256 != search_plan_envelope["search_plan_sha256"]:
        raise RuntimeError("Search-plan canonical SHA-256 mismatch")
    if canonical_plan_sha256 != search_plan_envelope["protocol_states"]["search_plan_sha256"]:
        raise RuntimeError("Search-plan protocol state uses a different SHA-256")
    if sha256(ROOT / "protocol.md") != search_plan_envelope["search_plan"]["protocol_sha256"]:
        raise RuntimeError("Search plan protocol SHA-256 does not match protocol.md")
    endpoint_rows = search_plan_envelope["search_plan"]["source_endpoints"]
    endpoint_ids = [endpoint["id"] for endpoint in endpoint_rows]
    if len(endpoint_ids) != len(set(endpoint_ids)):
        raise RuntimeError("Search plan repeats an endpoint ID")
    endpoint_counts = {
        tier: sum(endpoint["tier"] == tier for endpoint in endpoint_rows)
        for tier in ["seed", "backbone_index", "supplemental_keyword_query"]
    }
    if endpoint_counts != {"seed": 2, "backbone_index": 13,
                           "supplemental_keyword_query": 2}:
        raise RuntimeError(f"Unexpected endpoint tier counts: {endpoint_counts}")
    to_verify = [endpoint["id"] for endpoint in endpoint_rows
                 if endpoint["verification_status"] == "to_verify_by_custodian"]
    numeric_parameters = ["maximum_results_per_endpoint", "active_time_budget_minutes",
                          "consecutive_irrelevant_pages_stop"]
    if any(search_plan_envelope["search_plan"][name]["status"] != "PROPOSED"
           for name in numeric_parameters):
        raise RuntimeError("Every numeric search-plan parameter must remain PROPOSED")
    one_approval = copy.deepcopy(search_plan_envelope)
    one_approval["search_plan"]["maximum_results_per_endpoint"]["status"] = "APPROVED"
    one_approval["search_plan"]["maximum_results_per_endpoint"]["approved_by_planner_review_ids"] = ["one-review-only"]
    if not list(envelope_validator.iter_errors(one_approval)):
        raise RuntimeError("Search-plan schema accepted a numeric approval with only one planner review")
    if search_plan_envelope["protocol_states"]["design_frozen"]:
        raise RuntimeError("Draft search plan must remain design_frozen=false")
    approval_schema_path = ROOT / "planner-approval.schema.json"
    approval_record_path = ROOT / "planner-approval-v0.2.0.json"
    approval_validator = Draft202012Validator(load(approval_schema_path),
                                               format_checker=checker)
    approval_record = load(approval_record_path)
    approval_errors = list(approval_validator.iter_errors(approval_record))
    if approval_errors:
        raise RuntimeError("Planner-approval record is structurally invalid")
    if approval_record["record_status"] != "complete" or len(approval_record["reviewers"]) != 2:
        raise RuntimeError("Planner approval must contain exactly two completed reviewer records")
    incomplete_approval = copy.deepcopy(approval_record)
    incomplete_approval["reviewers"] = incomplete_approval["reviewers"][:1]
    if not list(approval_validator.iter_errors(incomplete_approval)):
        raise RuntimeError("Planner approval schema accepted complete without two reviewers")
    freeze_assessment = approval_record["freeze_assessment"]
    if freeze_assessment["protocol_sha256"] != sha256(ROOT / "protocol.md"):
        raise RuntimeError("Freeze assessment protocol SHA-256 does not match protocol.md")
    if freeze_assessment["search_plan_sha256"] != canonical_plan_sha256:
        raise RuntimeError("Freeze assessment search-plan SHA-256 mismatch")
    if (freeze_assessment["design_frozen"] or
            freeze_assessment["design_frozen_at"] is not None or
            not freeze_assessment["missing_requirements"]):
        raise RuntimeError("Incomplete search-plan gate must remain explicitly unfrozen")
    manifest_path = ROOT / "fixtures/manifest.json"
    manifest = load(manifest_path)
    cases = manifest["cases"]
    if len(cases) != 6 or sum(case["expected_valid"] is True for case in cases) != 3:
        raise RuntimeError("Expected exactly three valid and three invalid fixtures")

    results = []
    for case in cases:
        path = (manifest_path.parent / case["file"]).resolve()
        if not path.is_relative_to(manifest_path.parent):
            raise ValueError("Fixture path escapes its directory")
        ledger = load(path)
        if len(ledger["findings"]) != 1 or ledger["annotation_rounds"]:
            raise ValueError("Each fixture must have one illustrative row and no annotations")
        errors = list(validator.iter_errors(ledger))
        details = sorted([
            {"instance_path": pointer(error.absolute_path),
             "schema_path": pointer(error.absolute_schema_path),
             "validator": error.validator, "message": error.message}
            for error in errors_with_context(errors)
        ], key=lambda detail: (detail["instance_path"], detail["schema_path"]))
        expected_error = case["expected_error"]
        intended_rejection = expected_error is None or any(
            detail["instance_path"] == expected_error["instance_path"]
            and detail["validator"] == expected_error["validator"]
            for detail in details
        )
        results.append({
            "file": str(path.relative_to(ROOT)), "sha256": sha256(path),
            "description": case["description"], "expected_valid": case["expected_valid"],
            "actual_valid": not errors, "expected_error": expected_error,
            "intended_rejection_confirmed": intended_rejection,
            "passed": (not errors) == case["expected_valid"] and intended_rejection,
            "errors": details,
        })

    base = load(ROOT / "fixtures/valid-01-unassessed.json")
    state_controls = []
    for label, flag, timestamp in [
        ("design freeze requires two approving AI-planner records and a frozen plan",
         "design_frozen", "design_frozen_at"),
        ("reservation completion requires a commitment and custodian attestation",
         "reservation_completed", "reservation_completed_at"),
        ("annotation completion requires a completed annotation round",
         "annotation_round_completed", "annotation_round_completed_at"),
    ]:
        candidate = copy.deepcopy(base)
        candidate["protocol_states"][flag] = True
        candidate["protocol_states"][timestamp] = "2026-10-27T00:00:00Z"
        rejected = bool(list(validator.iter_errors(candidate)))
        if not rejected:
            raise RuntimeError(f"Protocol-state control was not rejected: {flag}")
        state_controls.append({"control": label, "expected_valid": False,
                               "actual_valid": False, "passed": True})

    source_level = copy.deepcopy(base)
    source_level["search_plan"]["source_endpoints"] = [{
        "id": "illustrative-source-index",
        "tier": "backbone_index",
        "source_class": "audit_report_index",
        "source_role": "backbone_index",
        "organization": "Synthetic fixture organization",
        "endpoint": "urn:illustrative:source-index",
        "verification_status": "known_public_listing",
        "hosting_kind": "web",
        "snapshot_rule": "custodian_capture_immediately_after_freeze",
        "snapshot_status": "capture_after_freeze",
        "revision_or_snapshot": None,
        "snapshot_sha256": None,
        "listing_format_risk": "names_only",
        "candidate_list_handling": "agent_metadata_allowed",
        "agent_access_rule": "metadata_only_no_finding_report_body_or_bug_description_views",
        "access_limitations": ["Synthetic structural control only."],
    }]
    endpoint_errors = list(validator.iter_errors(source_level))
    if endpoint_errors:
        raise RuntimeError("Source-level endpoint without application ID was rejected")
    state_controls.append({
        "control": "source-level index endpoint requires no application ID",
        "expected_valid": True, "actual_valid": True, "passed": True,
    })

    if "approved_by_human_id" in schema["$defs"]["search_plan"]["properties"]:
        raise RuntimeError("Design schema still contains approved_by_human_id")
    finding_required = set(schema["$defs"]["finding"]["required"])
    if "funnel" in finding_required or not {
        "disclosure_assessment", "tool_funnel"
    }.issubset(finding_required):
        raise RuntimeError("Disclosure assessment and tool funnel are not separated")

    archive_root = ROOT / "history/v0.1.0"
    archive_manifest = load(archive_root / "manifest.json")
    archive_files = []
    for entry in archive_manifest["files"]:
        archived = (archive_root / entry["path"]).resolve()
        if not archived.is_relative_to(archive_root.resolve()):
            raise RuntimeError("Archived path escapes v0.1.0 directory")
        actual = sha256(archived)
        passed_archive = actual == entry["sha256"] and archived.stat().st_size == entry["bytes"]
        if not passed_archive:
            raise RuntimeError(f"v0.1.0 archive mismatch: {entry['path']}")
        archive_files.append({"path": entry["path"], "sha256": actual,
                              "bytes": archived.stat().st_size, "passed": True})

    passed = all(result["passed"] for result in results)
    report = {
        "task": "D1P-C04 taxonomy search-plan v0.2.0 validation", "notice": manifest["notice"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "python": platform.python_version(), "platform": platform.platform(),
        "validator": "jsonschema.Draft202012Validator", "packages": pins,
        "schema": {"file": "ledger.schema.json", "sha256": sha256(schema_path),
                   "version": schema["properties"]["schema_version"]["const"],
                   "meta_schema_valid": True},
        "auxiliary_schemas": auxiliary_schema_results,
        "planner_approval_record": {
            "file": approval_record_path.name,
            "sha256": sha256(approval_record_path),
            "record_status": approval_record["record_status"],
            "reviewer_names": [reviewer["reviewer_name"]
                               for reviewer in approval_record["reviewers"]],
            "valid": True,
            "complete_without_reviewers_rejected": True,
            "freeze_assessment": freeze_assessment,
        },
        "search_plan": {
            "file": search_plan_path.name,
            "file_sha256": sha256(search_plan_path),
            "canonical_payload_sha256": canonical_plan_sha256,
            "schema_valid": True,
            "design_frozen": False,
            "endpoint_counts_by_tier": endpoint_counts,
            "to_verify_by_custodian": to_verify,
            "numeric_parameter_status": "PROPOSED",
            "single_planner_numeric_approval_rejected": True,
        },
        "protocol_state_controls": state_controls,
        "v0_1_0_archive": {
            "source_commit": archive_manifest["source_commit"],
            "manifest_sha256": sha256(archive_root / "manifest.json"),
            "files_verified": len(archive_files),
            "files": archive_files,
        },
        "runner_sha256": sha256(Path(__file__)),
        "requirements_sha256": sha256(ROOT / "validation-requirements.txt"),
        "fixture_manifest_sha256": sha256(manifest_path),
        "format_assertions": format_controls, "fixtures": results,
        "summary": {"expected_valid": 3, "expected_invalid": 3,
                    "passed": sum(result["passed"] for result in results),
                    "failed": sum(not result["passed"] for result in results)},
        "exit_status": 0 if passed else 1,
        "limits": "Schema and synthetic structural validation only; no source traversal, "
                  "screening, labeling, reservation draw, human attestation, annotation round, "
                  "cross-record evidence validation, or protocol-state completion.",
    }
    if output:
        with output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"meta_schema_valid": True, **report["summary"],
                      "format_controls_passed": len(format_controls),
                      "protocol_state_controls_passed": len(state_controls),
                      "archived_files_verified": len(archive_files),
                      "output": str(output.relative_to(ROOT)) if output else None}))
    return report["exit_status"]


if __name__ == "__main__":
    sys.exit(main())
