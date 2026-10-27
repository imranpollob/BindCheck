#!/usr/bin/env python3
"""Validate the schema and six AI-written illustrative fixtures, without network I/O."""

import argparse
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

    passed = all(result["passed"] for result in results)
    report = {
        "task": "D1P-C01 validation follow-up", "notice": manifest["notice"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "python": platform.python_version(), "platform": platform.platform(),
        "validator": "jsonschema.Draft202012Validator", "packages": pins,
        "schema": {"file": "ledger.schema.json", "sha256": sha256(schema_path),
                   "version": schema["properties"]["schema_version"]["const"],
                   "meta_schema_valid": True},
        "runner_sha256": sha256(Path(__file__)),
        "requirements_sha256": sha256(ROOT / "validation-requirements.txt"),
        "fixture_manifest_sha256": sha256(manifest_path),
        "format_assertions": format_controls, "fixtures": results,
        "summary": {"expected_valid": 3, "expected_invalid": 3,
                    "passed": sum(result["passed"] for result in results),
                    "failed": sum(not result["passed"] for result in results)},
        "exit_status": 0 if passed else 1,
        "limits": "Schema and synthetic structural validation only; no screening, application "
                  "labeling, cross-record evidence validation, human review, or freeze.",
    }
    if output:
        with output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps({"meta_schema_valid": True, **report["summary"],
                      "format_controls_passed": len(format_controls),
                      "output": str(output.relative_to(ROOT)) if output else None}))
    return report["exit_status"]


if __name__ == "__main__":
    sys.exit(main())
