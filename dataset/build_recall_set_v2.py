#!/usr/bin/env python3
"""Append public recall candidates and apply a frozen inventory-only scope rule."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
CONFIG = HERE / "recall-queries-v2.json"
V1 = HERE / "recall-set.csv"
SOURCE_V2 = HERE / "source-corpus-v2.csv"
OUTPUT = HERE / "recall-set-v2.csv"
SUMMARY = HERE / "recall-set-v2-summary.json"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(block: str, name: str) -> str:
    match = re.search(rf"^\* {re.escape(name)}:[ \t]*(.*)$", block, re.M)
    return match.group(1).strip() if match else ""


def nested_field(block: str, name: str) -> str:
    match = re.search(rf"^[ \t]+- {re.escape(name)}:[ \t]*(.*)$", block, re.M)
    return match.group(1).strip() if match else ""


def repository(project: str) -> str:
    match = re.search(r"github\.com/([^/]+/[^/#]+)", project)
    return match.group(1).removesuffix(".git") if match else ""


def token() -> str:
    return subprocess.run(["gh", "auth", "token"], text=True, capture_output=True, check=True).stdout.strip()


def resolve(repo: str, value: str, credential: str, raw: pathlib.Path) -> tuple[str, str]:
    value = value.strip().removeprefix("0x")
    if not repo or not value:
        return value, "not-publicly-pinned"
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
        return value, "invalid-or-non-git-reference"
    cache = raw / f"commit-{re.sub(r'[^A-Za-z0-9_.-]+', '__', repo)}--{value}.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
        return payload["sha"], "resolved"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(value)}",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {credential}", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "bindcheck-recall-v2"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload: Any = json.load(response)
        cache.write_text(json.dumps(payload, sort_keys=True) + "\n")
        return payload["sha"], "resolved"
    except urllib.error.HTTPError as exc:
        return value, f"github-http-{exc.code}"


def main() -> int:
    config = json.loads(CONFIG.read_text())
    clone = HERE / "clones" / "zkbugs"
    observed = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    if observed != config["zkbugs_commit"]:
        raise RuntimeError(f"zkbugs revision mismatch: {observed}")
    raw = HERE / "raw" / config["snapshot_id"]
    raw.mkdir(parents=True, exist_ok=True)
    with V1.open(newline="", encoding="utf-8") as handle:
        v1 = list(csv.DictReader(handle))
    original_fields = list(v1[0])
    with SOURCE_V2.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    integration_repositories = {
        row["repository"].lower()
        for row in source_rows
        if row["v2_predup_disposition"] == "in-scope"
    }
    effect_re = re.compile(config["effect_integration_case_id_regex"])
    source_text = (clone / "BUGS.md").read_text(encoding="utf-8")
    blocks = {block.splitlines()[0].strip(): block for block in re.split(r"^## (?=\S)", source_text, flags=re.M)[1:]}
    credential = token()

    output: list[dict[str, str]] = []

    def enrich(row: dict[str, str], block: str, origin: str) -> dict[str, str]:
        repo_integration = row["repository"].lower() in integration_repositories
        regex_match = bool(effect_re.search(row["case_id"]))
        if row["scope_class"] == "integration":
            scope = "integration"
            basis = "v1 strict-integration disposition preserved"
        elif repo_integration and regex_match:
            scope = "integration"
            basis = "fixed effect/integration case-id regex plus repository-level v2 circuit+consumer-call inventory; case/revision correspondence unvalidated"
        else:
            scope = "integration-or-execution-semantics"
            basis = "strict inventory rule not satisfied; retained as broader candidate"
        value = dict(row)
        value.update({
            "v2_scope_class": scope,
            "v2_scope_basis": basis,
            "v2_row_origin": origin,
            "v2_repository_has_circuit_consumer_inventory": str(repo_integration).lower(),
            "v2_case_id_effect_regex_match": str(regex_match).lower(),
            "v2_source_record_sha256": hashlib.sha256(block.encode()).hexdigest() if block else "",
            "v2_pair_status": "vulnerable-and-fixed-resolved" if row["vulnerable_commit_status"] == row["fixed_commit_status"] == "resolved" else "incomplete-public-pair",
        })
        return value

    for row in v1:
        output.append(enrich(row, blocks.get(row["case_id"], ""), "v1-preserved"))

    existing = {row["case_id"] for row in v1}
    for case_id in config["additional_zkbugs_ids"]:
        if case_id in existing:
            raise RuntimeError(f"additional case already exists in v1: {case_id}")
        block = blocks.get(case_id)
        if not block:
            raise RuntimeError(f"missing zkbugs record: {case_id}")
        project = field(block, "Project")
        repo = repository(project)
        vulnerable, vulnerable_status = resolve(repo, field(block, "Commit"), credential, raw)
        fixed, fixed_status = resolve(repo, field(block, "Fix Commit"), credential, raw)
        row = {
            "case_id": case_id,
            "repository": repo,
            "project_url": project,
            "vulnerable_commit": vulnerable,
            "fixed_commit": fixed,
            "vulnerable_commit_status": vulnerable_status,
            "fixed_commit_status": fixed_status,
            "dsl": field(block, "DSL"),
            "pattern": field(block, "Root Cause") or field(block, "Vulnerability"),
            "impact": field(block, "Impact"),
            "source_url": nested_field(block, "Source Link"),
            "source_kind": "zksecurity/zkbugs pinned audit extraction; v2 addition",
            "scope_class": "integration-or-execution-semantics",
            "evidence_grade": "E0",
            "verdict": "UNKNOWN",
            "recall_executed": "false",
            "notes": "inventory candidate only; no analyzer run and no vulnerability reproduction",
        }
        output.append(enrich(row, block, "v2-addition"))

    new_fields = ["v2_scope_class", "v2_scope_basis", "v2_row_origin", "v2_repository_has_circuit_consumer_inventory", "v2_case_id_effect_regex_match", "v2_source_record_sha256", "v2_pair_status"]
    fields = original_fields + new_fields
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(output)
    for index, row in enumerate(v1):
        assert {field: output[index][field] for field in original_fields} == row

    summary = {
        "schema_version": 2,
        "snapshot_id": config["snapshot_id"],
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "cases": len(output),
        "v1_cases_preserved": len(v1),
        "new_cases": len(output) - len(v1),
        "strict_integration_cases": sum(row["v2_scope_class"] == "integration" for row in output),
        "broader_candidates": sum(row["v2_scope_class"] != "integration" for row in output),
        "resolved_vulnerable_commits": sum(row["vulnerable_commit_status"] == "resolved" for row in output),
        "resolved_fixed_commits": sum(row["fixed_commit_status"] == "resolved" for row in output),
        "resolved_pairs": sum(row["v2_pair_status"] == "vulnerable-and-fixed-resolved" for row in output),
        "recall_executed": 0,
        "verdict": "UNKNOWN",
        "config_sha256": sha256(CONFIG),
        "v1_ledger_sha256": sha256(V1),
        "source_v2_sha256": sha256(SOURCE_V2),
        "output_sha256": sha256(OUTPUT),
        "zkbugs_commit": observed,
        "append_only_projection_check": "PASS",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (raw / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
