#!/usr/bin/env python3
"""Passive Sourcify export join for deployed verifier consumers.

This script makes no RPC requests.  It begins with the frozen GitHub Solidity
files that matched a verifier-call regex, joins their exact SHA-256 values to
Sourcify compilation sources, and retains only deployments where the matched
file is the compiled contract's own source and both runtime match flags are
true.  It never reads or seeds from the private P4 address ledger.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any

import duckdb


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
RAW = DATASET / "raw" / "sourcify-consumers-2026-11-03-v2"
DB = RAW / "sourcify-consumers-staged.duckdb"
EXPORT = "https://export.sourcify.dev/"
GITHUB_INVENTORY = DATASET / "github-source-inventory-v2.csv"
OUTPUT = DATASET / "onchain-consumers-v2.csv"
MATCH_OUTPUT = DATASET / "sourcify-github-matches-v2.csv"
SUMMARY = DATASET / "onchain-consumers-v2-summary.json"
CHAINS = {
    1: "ethereum",
    10: "optimism",
    137: "polygon",
    324: "zksync-era",
    8453: "base",
    42161: "arbitrum-one",
    59144: "linea",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_objects(table: str) -> list[dict[str, Any]]:
    marker = ""
    objects: list[dict[str, Any]] = []
    namespace = {"s": "http://doc.s3.amazonaws.com/2006-03-01"}
    while True:
        params = {"prefix": f"v2/{table}/", "max-keys": "1000"}
        if marker:
            params["marker"] = marker
        request = urllib.request.Request(EXPORT + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "BindCheck-academic-consumer-census-v2"})
        root = ET.fromstring(urllib.request.urlopen(request, timeout=60).read())
        for node in root.findall("s:Contents", namespace):
            def value(name: str) -> str:
                child = node.find(f"s:{name}", namespace)
                return child.text if child is not None and child.text is not None else ""
            objects.append({"key": value("Key"), "last_modified": value("LastModified"), "etag": value("ETag").strip('"'), "size": int(value("Size") or 0)})
        truncated = (root.findtext("s:IsTruncated", default="false", namespaces=namespace) or "false").lower() == "true"
        if not truncated:
            break
        marker = root.findtext("s:NextMarker", default="", namespaces=namespace) or objects[-1]["key"]
    if not objects:
        raise RuntimeError(f"no Sourcify objects listed for {table}")
    return objects


def sql_urls(objects: list[dict[str, Any]]) -> str:
    values = [EXPORT + item["key"] for item in objects]
    return "[" + ",".join("'" + value.replace("'", "''") + "'" for value in values) + "]"


def parse_evidence(value: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in value.split("||"):
        if "@sha256:" not in item:
            continue
        path, rest = item.split("@sha256:", 1)
        digest, _, suffix = rest.partition("#")
        result[digest] = {"path": path, "evidence": suffix}
    return result


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    with GITHUB_INVENTORY.open(newline="", encoding="utf-8") as handle:
        inventory = list(csv.DictReader(handle))
    github_sources: list[tuple[str, str, str, bytes, str]] = []
    for row in inventory:
        evidence = parse_evidence(row["consumer_evidence"])
        for digest in sorted(set(row["consumer_source_sha256s"].split("|")) - {""}):
            item = evidence.get(digest, {})
            github_sources.append((row["repository"], row["commit"], item.get("path", ""), bytes.fromhex(digest), item.get("evidence", "")))
    github_sources = sorted(set(github_sources))
    if not github_sources:
        raise RuntimeError("GitHub inventory has no consumer source hashes")

    tables = ("compiled_contracts_sources", "compiled_contracts", "verified_contracts", "contract_deployments")
    object_manifest = {table: list_objects(table) for table in tables}
    (RAW / "parquet-objects.json").write_text(json.dumps(object_manifest, indent=2, sort_keys=True) + "\n")

    connection = duckdb.connect(str(DB))
    connection.execute("INSTALL httpfs; LOAD httpfs")
    connection.execute("PRAGMA threads=4")
    connection.execute("SET memory_limit='1GB'")
    temp_directory = RAW / "duckdb-temp"
    temp_directory.mkdir(exist_ok=True)
    connection.execute("SET temp_directory=?", [str(temp_directory)])
    connection.execute("CREATE OR REPLACE TABLE github_sources(repository VARCHAR, commit VARCHAR, github_path VARCHAR, source_hash BLOB, regex_evidence VARCHAR)")
    connection.executemany("INSERT INTO github_sources VALUES (?,?,?,?,?)", github_sources)
    chain_ids = "(" + ",".join(map(str, CHAINS)) + ")"
    stage_queries = [
        ("source_compilations", f"""
        CREATE OR REPLACE TABLE source_compilations AS
          SELECT DISTINCT g.repository, g.commit, g.github_path, g.source_hash,
                 g.regex_evidence, ccs.compilation_id, ccs.path AS sourcify_source_path
          FROM read_parquet({sql_urls(object_manifest['compiled_contracts_sources'])}) ccs
          JOIN github_sources g ON g.source_hash = ccs.source_hash
        """),
        ("relevant_compilations", f"""
        CREATE OR REPLACE TABLE relevant_compilations AS
          SELECT DISTINCT cc.id AS compilation_id, cc.name AS compiled_contract_name,
                 cc.fully_qualified_name
          FROM read_parquet({sql_urls(object_manifest['compiled_contracts'])}) cc
          JOIN (SELECT DISTINCT compilation_id FROM source_compilations) s ON s.compilation_id=cc.id
        """),
        ("exact_verified", f"""
        CREATE OR REPLACE TABLE exact_verified AS
          SELECT DISTINCT compilation_id, deployment_id, id AS verified_contract_id
          FROM read_parquet({sql_urls(object_manifest['verified_contracts'])})
          JOIN (SELECT DISTINCT compilation_id AS wanted_compilation_id FROM source_compilations)
            ON compilation_id=wanted_compilation_id
          WHERE runtime_match=true AND runtime_metadata_match=true
        """),
        ("relevant_deployments", f"""
        CREATE OR REPLACE TABLE relevant_deployments AS
          SELECT DISTINCT d.id AS deployment_id, d.chain_id,
                 lower('0x'||hex(d.address)) AS address, d.block_number
          FROM read_parquet({sql_urls(object_manifest['contract_deployments'])}) d
          JOIN (SELECT DISTINCT deployment_id FROM exact_verified) v ON v.deployment_id=d.id
          WHERE d.chain_id IN {chain_ids}
        """),
        ("exact_consumer_deployments", """
        CREATE OR REPLACE TABLE exact_consumer_deployments AS
        SELECT DISTINCT s.repository, s.commit, s.github_path,
               lower(hex(s.source_hash)) AS source_sha256, s.regex_evidence,
               s.sourcify_source_path, s.compilation_id,
               cc.compiled_contract_name, cc.fully_qualified_name,
               v.verified_contract_id, d.chain_id, d.address, d.block_number
        FROM source_compilations s
        JOIN relevant_compilations cc ON cc.compilation_id=s.compilation_id
        JOIN exact_verified v ON v.compilation_id=s.compilation_id
        JOIN relevant_deployments d ON d.deployment_id=v.deployment_id
        WHERE s.sourcify_source_path=split_part(cc.fully_qualified_name, ':', 1)
        """),
    ]
    (RAW / "staged-exact-consumer-deployments.sql").write_text(
        "\n\n".join(f"-- {name}\n{query.strip()};" for name, query in stage_queries) + "\n"
    )
    started = dt.datetime.now(dt.UTC)
    stage_counts: dict[str, int] = {}
    existing_tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    reused_stages: list[str] = []
    for name, query in stage_queries:
        if name in existing_tables:
            reused_stages.append(name)
        else:
            connection.execute(query)
        stage_counts[name] = connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        suffix = " (reused)" if name in reused_stages else ""
        print(f"Sourcify stage {name}: {stage_counts[name]} rows{suffix}", flush=True)
    columns = [item[0] for item in connection.execute("DESCRIBE exact_consumer_deployments").fetchall()]
    joined = [dict(zip(columns, row)) for row in connection.execute("SELECT * FROM exact_consumer_deployments ORDER BY chain_id,address,repository,commit,github_path").fetchall()]

    match_fields = columns + ["chain_name", "match_rule"]
    match_records = []
    for row in joined:
        value = {key: "" if item is None else item for key, item in row.items()}
        value["chain_name"] = CHAINS[int(row["chain_id"])]
        value["match_rule"] = "exact source SHA-256; deployed compiled target uses matched source path; runtime_match=true; runtime_metadata_match=true"
        match_records.append(value)
    with MATCH_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, match_fields)
        writer.writeheader()
        writer.writerows(match_records)

    deployments: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in match_records:
        deployments[(int(row["chain_id"]), str(row["address"]), str(row["source_sha256"]))].append(row)
    output_fields = [
        "chain_id", "chain_name", "address", "block_number", "source_sha256", "sourcify_source_paths",
        "compiled_contract_names", "fully_qualified_names", "verified_contract_ids", "compilation_ids",
        "repository_links", "github_repositories", "github_commits", "github_paths", "consumer_regex_evidence",
        "runtime_match", "runtime_metadata_match", "collection_scope", "verdict",
    ]
    output_records = []
    for (chain_id, address, digest), members in sorted(deployments.items()):
        block_numbers = [int(row["block_number"]) for row in members if str(row["block_number"]).strip()]
        output_records.append({
            "chain_id": chain_id, "chain_name": CHAINS[chain_id], "address": address,
            "block_number": min(block_numbers) if block_numbers else "", "source_sha256": digest,
            "sourcify_source_paths": "|".join(sorted({str(row["sourcify_source_path"]) for row in members})),
            "compiled_contract_names": "|".join(sorted({str(row["compiled_contract_name"]) for row in members})),
            "fully_qualified_names": "|".join(sorted({str(row["fully_qualified_name"]) for row in members})),
            "verified_contract_ids": "|".join(sorted({str(row["verified_contract_id"]) for row in members})),
            "compilation_ids": "|".join(sorted({str(row["compilation_id"]) for row in members})),
            "repository_links": "|".join(sorted({f"https://github.com/{row['repository']}" for row in members})),
            "github_repositories": "|".join(sorted({str(row["repository"]) for row in members})),
            "github_commits": "|".join(sorted({str(row["commit"]) for row in members})),
            "github_paths": "|".join(sorted({str(row["github_path"]) for row in members})),
            "consumer_regex_evidence": "|".join(sorted({str(row["regex_evidence"]) for row in members})),
            "runtime_match": "true", "runtime_metadata_match": "true",
            "collection_scope": "passive Sourcify Parquet exact-source join; no RPC; no P4-seeded tracing",
            "verdict": "UNKNOWN",
        })
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, output_fields)
        writer.writeheader()
        writer.writerows(output_records)

    summary = {
        "schema_version": 2,
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "snapshot_date": "2026-11-03",
        "data_source": EXPORT + "v2/",
        "selection": "GitHub verifier-call-regex source SHA-256 joined to Sourcify compiled target source; runtime_match=true and runtime_metadata_match=true",
        "coverage_limit": "targeted exact-source join for GitHub inventory call sites; not a global scan of the 17.082-GiB compressed Sourcify sources table",
        "rpc_requests": 0,
        "private_p4_addresses_used_as_seeds": 0,
        "github_consumer_source_rows": len(github_sources),
        "github_consumer_source_hashes": len({row[3] for row in github_sources}),
        "matched_repository_deployment_rows": len(match_records),
        "onchain_consumer_rows": len(output_records),
        "unique_deployments": len({(row["chain_id"], row["address"]) for row in output_records}),
        "unique_github_repositories": len({row["repository"] for row in match_records}),
        "chain_counts": {name: sum(row["chain_name"] == name for row in output_records) for name in CHAINS.values()},
        "object_counts": {table: len(items) for table, items in object_manifest.items()},
        "object_bytes": {table: sum(item["size"] for item in items) for table, items in object_manifest.items()},
        "stage_counts": stage_counts,
        "reused_stages_on_output_pass": reused_stages,
        "github_inventory_sha256": sha256(GITHUB_INVENTORY),
        "match_output_sha256": sha256(MATCH_OUTPUT),
        "output_sha256": sha256(OUTPUT),
        "output_pass_elapsed_seconds": round((dt.datetime.now(dt.UTC) - started).total_seconds(), 3),
        "staged_remote_elapsed_seconds": None,
        "staged_remote_elapsed_note": "The successful remote stages were committed before a nullable-block formatting failure; the reused output pass cannot reconstruct their in-process timer. Filesystem timestamps bound the staged run from 2026-11-04T16:33:36-0800 to 2026-11-04T17:55:17-0800 (4,901 seconds).",
        "verdict": "UNKNOWN",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (RAW / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
