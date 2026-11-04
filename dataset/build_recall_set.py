#!/usr/bin/env python3
"""Create a 20--40 case integration recall ledger from pinned public sources."""

from __future__ import annotations

import argparse
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


def field(block: str, name: str) -> str:
    match = re.search(rf"^\* {re.escape(name)}:\s*(.*)$", block, re.M)
    return match.group(1).strip() if match else ""


def nested_field(block: str, name: str) -> str:
    match = re.search(rf"^\s+- {re.escape(name)}:\s*(.*)$", block, re.M)
    return match.group(1).strip() if match else ""


def repository(project: str) -> str:
    match = re.search(r"github\.com/([^/]+/[^/#]+)", project)
    return match.group(1).removesuffix(".git") if match else ""


def github_token() -> str:
    return subprocess.run(["gh", "auth", "token"], text=True, capture_output=True, check=True).stdout.strip()


def resolve_commit(repo: str, value: str, token: str, raw: pathlib.Path) -> tuple[str, str]:
    value = value.strip().removeprefix("0x")
    if not repo or not value:
        return value, "not-publicly-pinned"
    if len(value) not in range(7, 41) or not re.fullmatch(r"[0-9a-fA-F]+", value):
        return value, "invalid-or-non-git-reference"
    url = f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(value)}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "bindcheck-recall-inventory",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload: Any = json.load(response)
        target = raw / f"commit-{repo.replace('/', '__')}--{value}.json"
        target.write_text(json.dumps(payload, sort_keys=True) + "\n")
        return payload["sha"], "resolved"
    except urllib.error.HTTPError as exc:
        return value, f"github-http-{exc.code}"


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=here / "recall-queries.json")
    parser.add_argument("--output", type=pathlib.Path, default=here / "recall-set.csv")
    parser.add_argument("--summary", type=pathlib.Path, default=here / "recall-summary.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    clone = here / "clones/zkbugs"
    observed = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    if observed != config["zkbugs_commit"]:
        raise SystemExit(f"zkbugs revision mismatch: {observed}")
    raw = here / "raw" / config["snapshot_id"]
    raw.mkdir(parents=True, exist_ok=True)
    text = (clone / "BUGS.md").read_text(encoding="utf-8")
    blocks = {block.splitlines()[0].strip(): block for block in re.split(r"^## (?=\S)", text, flags=re.M)[1:]}
    token = github_token()
    rows: list[dict[str, str]] = []

    for bug_id in config["selected_zkbugs_ids"]:
        if bug_id not in blocks:
            raise SystemExit(f"missing selected zkbugs id: {bug_id}")
        block = blocks[bug_id]
        project = field(block, "Project")
        repo = repository(project)
        vuln, vuln_status = resolve_commit(repo, field(block, "Commit"), token, raw)
        fixed, fixed_status = resolve_commit(repo, field(block, "Fix Commit"), token, raw)
        rows.append({
            "case_id": bug_id, "repository": repo, "project_url": project,
            "vulnerable_commit": vuln, "fixed_commit": fixed,
            "vulnerable_commit_status": vuln_status, "fixed_commit_status": fixed_status,
            "dsl": field(block, "DSL"), "pattern": field(block, "Root Cause") or field(block, "Vulnerability"),
            "impact": field(block, "Impact"), "source_url": nested_field(block, "Source Link"),
            "source_kind": "zksecurity/zkbugs pinned audit/advisory extraction",
            "scope_class": "integration-or-execution-semantics", "evidence_grade": "E0", "verdict": "UNKNOWN",
            "recall_executed": "false", "notes": "candidate recall case; semantic inclusion requires independent author review",
        })

    for item in config["manual_public_cases"]:
        repo = repository(item["project"])
        vuln, vuln_status = resolve_commit(repo, item["vulnerable_commit"], token, raw)
        fixed, fixed_status = resolve_commit(repo, item["fixed_commit"], token, raw)
        rows.append({
            "case_id": item["id"], "repository": repo, "project_url": item["project"],
            "vulnerable_commit": vuln, "fixed_commit": fixed,
            "vulnerable_commit_status": vuln_status, "fixed_commit_status": fixed_status,
            "dsl": "Circom/Solidity or generated Groth16 verifier", "pattern": item["pattern"], "impact": "proof-to-execution mismatch",
            "source_url": item["source_url"], "source_kind": "public issue/advisory/technical incident record",
            "scope_class": "integration", "evidence_grade": "E0", "verdict": "UNKNOWN", "recall_executed": "false",
            "notes": "public historical case; no new analyzer run in this dataset task",
        })

    fields = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema_version": 1, "snapshot_id": config["snapshot_id"], "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "cases": len(rows), "with_resolved_vulnerable_commit": sum(row["vulnerable_commit_status"] == "resolved" for row in rows),
        "with_resolved_fixed_commit": sum(row["fixed_commit_status"] == "resolved" for row in rows),
        "recall_executed": 0, "verdict": "UNKNOWN", "evidence_grade": "E0",
        "strict_integration_cases": sum(row["scope_class"] == "integration" for row in rows),
        "integration_or_execution_semantics_candidates": sum(row["scope_class"] == "integration-or-execution-semantics" for row in rows),
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "zkbugs_commit": observed,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (raw / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
