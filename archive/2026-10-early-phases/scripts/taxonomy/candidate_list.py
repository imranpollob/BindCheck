#!/usr/bin/env python3
"""Build a name-only candidate list from custodian-classified metadata.

The program never fetches an endpoint and accepts no finding/report text.
Mixed or unknown listings are rejected so the human custodian can sanitize
them outside an agent session.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "docs/taxonomy/search-plan-v0.2.0.json"
ROOT_KEYS = {"schema_version", "sources"}
SOURCE_KEYS = {"endpoint_id", "listing_format", "custodian_attestation", "entries"}
ENTRY_KEYS = {"application_or_project_name", "repository_url"}
FORBIDDEN_KEYS = {
    "body", "bug", "description", "details", "finding", "finding_title",
    "impact", "report", "severity", "summary", "title", "vulnerability",
}
SAFE_FORMATS = {"names_only", "custodian_sanitized_names_only"}
BLOCKED_FORMATS = {"mixed_names_and_bug_descriptions", "unknown"}


class CandidateInputError(ValueError):
    """Input would violate the metadata-only boundary."""


def load_unique(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise CandidateInputError(f"duplicate JSON key in {path.name}: {key}")
            out[key] = value
        return out

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateInputError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateInputError(f"{path.name}: root must be an object")
    return value


def reject_forbidden_keys(value: Any, location: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise CandidateInputError(
                    f"{location}: forbidden content field {key!r}; custodian must sanitize outside the agent session"
                )
            reject_forbidden_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_keys(child, f"{location}[{index}]")


def plan_endpoint_policy(plan_path: Path) -> dict[str, str]:
    plan = load_unique(plan_path)
    try:
        endpoints = plan["search_plan"]["source_endpoints"]
    except (KeyError, TypeError) as exc:
        raise CandidateInputError("search plan lacks source_endpoints") from exc
    policy: dict[str, str] = {}
    for endpoint in endpoints:
        endpoint_id = endpoint["id"]
        if endpoint_id in policy:
            raise CandidateInputError(f"duplicate endpoint ID in search plan: {endpoint_id}")
        policy[endpoint_id] = endpoint["candidate_list_handling"]
    return policy


def parse_inputs(paths: list[Path], policy: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str]] = set()
    for path in paths:
        value = load_unique(path)
        reject_forbidden_keys(value)
        if set(value) != ROOT_KEYS or value["schema_version"] != "0.2.0":
            raise CandidateInputError(f"{path.name}: expected schema_version and sources only")
        if not isinstance(value["sources"], list):
            raise CandidateInputError(f"{path.name}: sources must be an array")
        for source in value["sources"]:
            if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
                raise CandidateInputError(f"{path.name}: each source must contain exactly {sorted(SOURCE_KEYS)}")
            endpoint_id = source["endpoint_id"]
            if endpoint_id not in policy:
                raise CandidateInputError(f"{path.name}: unknown endpoint ID {endpoint_id!r}")
            listing_format = source["listing_format"]
            if listing_format in BLOCKED_FORMATS:
                raise CandidateInputError(
                    f"{endpoint_id}: listing format {listing_format!r} is unsafe; custodian must provide a sanitized name-only list"
                )
            if listing_format not in SAFE_FORMATS:
                raise CandidateInputError(f"{endpoint_id}: unsupported listing_format")
            attestation = source["custodian_attestation"]
            if listing_format == "custodian_sanitized_names_only":
                if not isinstance(attestation, str) or not attestation.strip():
                    raise CandidateInputError(f"{endpoint_id}: sanitized input needs custodian_attestation")
            elif attestation is not None:
                raise CandidateInputError(f"{endpoint_id}: names_only input must use null custodian_attestation")
            if policy[endpoint_id] == "human_sanitized_required" and listing_format != "custodian_sanitized_names_only":
                raise CandidateInputError(f"{endpoint_id}: search plan requires human-sanitized input")
            if not isinstance(source["entries"], list):
                raise CandidateInputError(f"{endpoint_id}: entries must be an array")
            for entry in source["entries"]:
                if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
                    raise CandidateInputError(f"{endpoint_id}: entries may contain only {sorted(ENTRY_KEYS)}")
                name = entry["application_or_project_name"]
                repository = entry["repository_url"]
                if not isinstance(name, str) or not name.strip():
                    raise CandidateInputError(f"{endpoint_id}: application_or_project_name must be non-empty")
                if repository is not None and (not isinstance(repository, str) or not repository.startswith(("https://", "http://"))):
                    raise CandidateInputError(f"{endpoint_id}: repository_url must be HTTP(S) or null")
                key = (name.strip(), repository, endpoint_id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "application_or_project_name": name.strip(),
                    "repository_url": repository,
                    "endpoint_id": endpoint_id,
                })
    return sorted(rows, key=lambda row: (row["application_or_project_name"].casefold(), row["endpoint_id"], row["repository_url"] or ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Custodian-classified JSON metadata inputs")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, help="New JSON output file; defaults to stdout")
    args = parser.parse_args()
    try:
        rows = parse_inputs(args.inputs, plan_endpoint_policy(args.plan))
        payload = {"schema_version": "0.2.0", "fields": ["application_or_project_name", "repository_url", "endpoint_id"], "candidates": rows}
        encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            if args.output.exists():
                raise CandidateInputError("refusing to overwrite output")
            args.output.write_text(encoded, encoding="utf-8")
        else:
            sys.stdout.write(encoded)
    except CandidateInputError as exc:
        print(f"candidate list blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
