#!/usr/bin/env python3
"""Passive Sourcify full-runtime-match verifier census on fixed major chains.

The script performs only public dataset downloads and JSON-RPC reads
(`eth_getCode` and `eth_getBalance`).  It never sends a transaction and does
not call verifier entry points.  Bytecode detections are explicitly heuristic
unless the exact default BN254 G2 constant signature is present.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

import duckdb


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
RAW = DATASET / "raw" / "sourcify-census-2026-11-03-v1"
DB = RAW / "sourcify.duckdb"
EXPORT = "https://export.sourcify.dev/"
CHAINS = {
    1: ("ethereum", "https://ethereum-rpc.publicnode.com"),
    10: ("optimism", "https://optimism-rpc.publicnode.com"),
    137: ("polygon", "https://polygon-bor-rpc.publicnode.com"),
    324: ("zksync-era", "https://mainnet.era.zksync.io"),
    8453: ("base", "https://base-rpc.publicnode.com"),
    42161: ("arbitrum-one", "https://arbitrum-one-rpc.publicnode.com"),
    59144: ("linea", "https://linea-rpc.publicnode.com"),
}
SCALAR_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617
BN254_G2 = (
    11559732032986387107991004021392285783925812861821192530917403151452391805634,
    10857046999023057135944570762232829481370756359578518086990519993285655852781,
    4082367875863433681332203403145435568316851327593401208105741076214120093531,
    8495653923123431417604973247489272438418190587263600148770280649306958101930,
)


def parquet_urls(table):
    request = urllib.request.Request(EXPORT + f"?prefix=v2/{table}/", headers={"user-agent": "BindCheck-academic-census/1"})
    root = ET.fromstring(urllib.request.urlopen(request, timeout=60).read())
    namespace = {"s": "http://doc.s3.amazonaws.com/2006-03-01"}
    keys = [node.text for node in root.findall(".//s:Key", namespace)]
    if not keys:
        raise RuntimeError(f"no Sourcify export objects for {table}")
    return [EXPORT + key for key in keys]


def sql_list(values):
    return "[" + ",".join("'" + value.replace("'", "''") + "'" for value in values) + "]"


def build_index(connection):
    connection.execute("INSTALL httpfs; LOAD httpfs")
    urls = {table: parquet_urls(table) for table in (
        "signatures", "compiled_contracts_signatures", "compiled_contracts",
        "verified_contracts", "contract_deployments")}
    (RAW / "parquet-objects.json").write_text(json.dumps(urls, indent=2) + "\n")
    connection.execute(f"""CREATE OR REPLACE TABLE verifier_signatures AS
        SELECT signature_hash_32, signature
        FROM read_parquet({sql_list(urls['signatures'])})
        WHERE regexp_matches(signature, '^(verifyProof|verifyTx)\\(')
          AND (signature LIKE '%uint256[2]%' OR signature LIKE '%bytes%')
          AND (signature LIKE '%uint256[%]%' OR signature LIKE '%uint256[]%')""")
    connection.execute(f"""CREATE OR REPLACE TABLE verifier_compilation_ids AS
        SELECT DISTINCT compilation_id
        FROM read_parquet({sql_list(urls['compiled_contracts_signatures'])}) c
        JOIN verifier_signatures s USING (signature_hash_32)
        WHERE c.signature_type='function'""")
    connection.execute(f"""CREATE OR REPLACE TABLE verifier_compilations AS
        SELECT c.id,c.name,c.fully_qualified_name,c.compiler,c.version,c.language,c.runtime_code_hash
        FROM read_parquet({sql_list(urls['compiled_contracts'])}) c
        JOIN verifier_compilation_ids v ON v.compilation_id=c.id
        WHERE regexp_matches(lower(coalesce(c.name,'')), '(verifier|verify)')""")
    chain_ids = "(" + ",".join(map(str, CHAINS)) + ")"
    connection.execute(f"""CREATE OR REPLACE TABLE exact_deployments AS
        SELECT d.chain_id, lower('0x'||hex(d.address)) address, d.block_number,
               v.id verified_contract_id, v.compilation_id, cc.name, cc.fully_qualified_name,
               cc.compiler, cc.version, lower('0x'||hex(cc.runtime_code_hash)) runtime_code_hash,
               v.runtime_match, v.runtime_metadata_match
        FROM read_parquet({sql_list(urls['verified_contracts'])}) v
        JOIN verifier_compilation_ids z ON z.compilation_id=v.compilation_id
        JOIN read_parquet({sql_list(urls['contract_deployments'])}) d ON d.id=v.deployment_id
        JOIN verifier_compilations cc ON cc.id=v.compilation_id
        WHERE d.chain_id IN {chain_ids} AND v.runtime_match=true AND v.runtime_metadata_match=true""")
    return {table: len(items) for table, items in urls.items()}


def rpc(chain_id, calls, attempts=4):
    url = CHAINS[chain_id][1]
    payload = [{"jsonrpc": "2.0", "id": index + 1, "method": method, "params": params}
               for index, (method, params) in enumerate(calls)]
    body = json.dumps(payload if len(payload) > 1 else payload[0]).encode()
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, data=body, headers={
                "content-type": "application/json", "user-agent": "BindCheck-academic-census/1"})
            response = json.loads(urllib.request.urlopen(request, timeout=45).read())
            if isinstance(response, dict):
                response = [response]
            by_id = {item.get("id"): item for item in response}
            return [by_id.get(index + 1, {}).get("result") for index in range(len(calls))]
        except Exception:
            if attempt + 1 == attempts:
                return [None] * len(calls)
            time.sleep(1.5 * (attempt + 1))


def push32_values(code):
    raw = bytes.fromhex(code.removeprefix("0x"))
    values = []
    index = 0
    while index < len(raw):
        opcode = raw[index]
        if 0x60 <= opcode <= 0x7F:
            size = opcode - 0x5F
            operand = raw[index + 1:index + 1 + size]
            if size == 32:
                values.append(int.from_bytes(operand, "big"))
            index += 1 + size
        else:
            index += 1
    return values


def analyze_bytecode(code):
    values = push32_values(code)
    counts = collections.Counter(values)
    default_counts = [counts[value] for value in BN254_G2]
    default_g2_twice = all(count >= 2 for count in default_counts)
    repeated_pairs = collections.defaultdict(list)
    for index in range(len(values) - 1):
        pair = (values[index], values[index + 1])
        if pair[0] and pair[1]:
            repeated_pairs[pair].append(index)
    duplicate_large_pairs = [pair for pair, places in repeated_pairs.items()
                             if len(places) > 1 and all(value.bit_length() > 160 for value in pair)
                             and not all(value in BN254_G2 for value in pair)]
    repeated_four = collections.Counter(tuple(values[index:index + 4]) for index in range(len(values) - 3))
    repeated_four_large = [item for item, count in repeated_four.items()
                           if count > 1 and all(value.bit_length() > 160 for value in item)]
    return {
        "bytecode_bytes": (len(code) - 2) // 2,
        "default_g2_constant_counts": default_counts,
        "default_g2_twice_gamma_delta_signature": default_g2_twice,
        "scalar_field_push32_present": counts[SCALAR_FIELD] > 0,
        "missing_scalar_field_push32_guard_heuristic": counts[SCALAR_FIELD] == 0,
        "duplicate_large_push32_pairs": len(duplicate_large_pairs),
        "repeated_four_large_push32_sequences": len(repeated_four_large),
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(DB))
    started = dt.datetime.now(dt.UTC)
    existing = {row[0] for row in connection.execute("show tables").fetchall()}
    if {"verifier_signatures", "verifier_compilation_ids", "verifier_compilations", "exact_deployments"} <= existing:
        manifest = RAW / "parquet-objects.json"
        object_counts = ({key: len(value) for key, value in json.loads(manifest.read_text()).items()}
                         if manifest.exists() else {})
    else:
        object_counts = build_index(connection)
    columns = [item[0] for item in connection.execute("describe exact_deployments").fetchall()]
    deployments = [dict(zip(columns, row)) for row in connection.execute("select * from exact_deployments order by chain_id,address").fetchall()]
    block_file = RAW / "rpc-block-tags.json"
    if block_file.exists():
        block_tags = {int(key): value for key, value in json.loads(block_file.read_text()).items()}
    else:
        block_tags = {}
        for chain_id in CHAINS:
            value = rpc(chain_id, [("eth_blockNumber", [])])[0]
            if not isinstance(value, str):
                raise RuntimeError(f"could not freeze block tag for chain {chain_id}")
            block_tags[chain_id] = value
        block_file.write_text(json.dumps(block_tags, indent=2, sort_keys=True) + "\n")
    # One code read per chain/runtime hash; all matching rows have exact runtime
    # correspondence by construction.
    representatives = {}
    for row in deployments:
        representatives.setdefault((row["chain_id"], row["runtime_code_hash"]), row["address"])
    code_cache_file = RAW / "rpc-code-cache.json"
    code_cache = json.loads(code_cache_file.read_text()) if code_cache_file.exists() else {}
    code_by_key = {}
    for chain_id in CHAINS:
        items = [(key, address) for key, address in representatives.items() if key[0] == chain_id]
        missing = []
        for key, address in items:
            cache_key = f"{chain_id}|{key[1]}"
            cached = code_cache.get(cache_key)
            if cached and cached.get("block") == block_tags[chain_id] and isinstance(cached.get("code"), str):
                code_by_key[key] = cached["code"]
            else:
                missing.append((key, address))
        for offset in range(0, len(missing), 40):
            batch = missing[offset:offset + 40]
            results = rpc(chain_id, [("eth_getCode", [address, block_tags[chain_id]]) for _, address in batch])
            for ((key, _), result) in zip(batch, results):
                if isinstance(result, str):
                    code_by_key[key] = result
                    code_cache[f"{chain_id}|{key[1]}"] = {"block": block_tags[chain_id], "code": result}
            code_cache_file.write_text(json.dumps(code_cache, sort_keys=True) + "\n")
    records = []
    for row in deployments:
        key = (row["chain_id"], row["runtime_code_hash"])
        code = code_by_key.get(key)
        analysis = analyze_bytecode(code) if isinstance(code, str) and code not in ("0x", "0x0") else {}
        record = dict(row)
        record.update({"chain_name": CHAINS[row["chain_id"]][0], "rpc_code_available": bool(analysis), **analysis})
        record["verdict"] = "UNKNOWN"
        record["evidence_grade"] = "E1" if (analysis.get("default_g2_twice_gamma_delta_signature") or analysis.get("missing_scalar_field_push32_guard_heuristic")) else "E0"
        records.append(record)
    flagged = [row for row in records if row.get("evidence_grade") == "E1"]
    # Balance reads are passive.  They measure the verifier address only;
    # consumer TVL is not inferred without a source-confirmed consumer link.
    balance_cache_file = RAW / "rpc-balance-cache.json"
    balance_cache = json.loads(balance_cache_file.read_text()) if balance_cache_file.exists() else {}
    for chain_id in CHAINS:
        items = [row for row in flagged if row["chain_id"] == chain_id]
        missing = []
        for row in items:
            cache_key = f"{chain_id}|{row['address']}"
            cached = balance_cache.get(cache_key)
            if cached and cached.get("block") == block_tags[chain_id] and isinstance(cached.get("balance"), str):
                row["verifier_native_balance_wei"] = int(cached["balance"], 16)
                row["consumer_link_status"] = "unavailable-from-verifier-only-census"
                row["consumer_tvl_status"] = "UNKNOWN"
            else:
                missing.append(row)
        for offset in range(0, len(missing), 40):
            batch = missing[offset:offset + 40]
            results = rpc(chain_id, [("eth_getBalance", [row["address"], block_tags[chain_id]]) for row in batch])
            for row, result in zip(batch, results):
                row["verifier_native_balance_wei"] = int(result, 16) if isinstance(result, str) else None
                row["consumer_link_status"] = "unavailable-from-verifier-only-census"
                row["consumer_tvl_status"] = "UNKNOWN"
                if isinstance(result, str):
                    balance_cache[f"{chain_id}|{row['address']}"] = {"block": block_tags[chain_id], "balance": result}
            balance_cache_file.write_text(json.dumps(balance_cache, sort_keys=True) + "\n")
    fieldnames = sorted({key for row in records for key in row})
    with (DATASET / "onchain-census.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row)
    runtime_groups = {}
    for row in records:
        runtime_groups.setdefault(row["runtime_code_hash"], row)
    default_key_rows = [row for row in records if row.get("default_g2_twice_gamma_delta_signature")]
    summary = {
        "schema_version": 1, "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "snapshot_date": "2026-11-03", "data_source": EXPORT + "v2/",
        "selection": "Sourcify runtime_match=true and runtime_metadata_match=true; verifier-like ABI signature and verifier-like compiled name",
        "chains": {str(key): value[0] for key, value in CHAINS.items()},
        "rpc_block_tags": {str(key): value for key, value in block_tags.items()},
        "parquet_object_counts": object_counts,
        "signature_rows": connection.execute("select count(*) from verifier_signatures").fetchone()[0],
        "compilation_ids": connection.execute("select count(*) from verifier_compilation_ids").fetchone()[0],
        "verifier_named_compilations": connection.execute("select count(*) from verifier_compilations").fetchone()[0],
        "exact_deployment_rows": len(records),
        "unique_deployments": len({(row['chain_id'], row['address']) for row in records}),
        "unique_runtime_hashes": len(runtime_groups),
        "rpc_code_available": sum(bool(row.get("rpc_code_available")) for row in records),
        "default_g2_gamma_delta_signature_deployments": sum(bool(row.get("default_g2_twice_gamma_delta_signature")) for row in records),
        "default_g2_gamma_delta_signature_runtime_hashes": len({row['runtime_code_hash'] for row in records if row.get("default_g2_twice_gamma_delta_signature")}),
        "default_g2_gamma_delta_signature_unique_deployments": len({(row['chain_id'], row['address']) for row in records if row.get("default_g2_twice_gamma_delta_signature")}),
        "missing_scalar_guard_heuristic_deployments": sum(bool(row.get("missing_scalar_field_push32_guard_heuristic")) for row in records),
        "duplicate_ic_heuristic_deployments": sum(bool(row.get("duplicate_large_push32_pairs")) for row in records),
        "flagged_verifier_positive_native_balance": sum((row.get("verifier_native_balance_wei") or 0) > 0 for row in flagged),
        "flagged_verifier_balance_reads_available": sum(row.get("verifier_native_balance_wei") is not None for row in flagged),
        "flagged_verifier_balance_reads_unavailable": sum(row.get("verifier_native_balance_wei") is None for row in flagged),
        "default_key_verifier_zero_native_balance": sum(row.get("verifier_native_balance_wei") == 0 for row in default_key_rows),
        "default_key_verifier_positive_native_balance": sum((row.get("verifier_native_balance_wei") or 0) > 0 for row in default_key_rows),
        "default_key_verifier_balance_reads_unavailable": sum(row.get("verifier_native_balance_wei") is None for row in default_key_rows),
        "source_confirmed_consumer_links": 0,
        "funded_vulnerable_consumer_instances": 0,
        "safety_stop_triggered": False,
        "limitations": [
            "absence of the scalar-field PUSH32 is only a missing-guard heuristic",
            "duplicate PUSH32 pairs are not a source-confirmed duplicate-IC result",
            "verifier balance is not consumer TVL; no consumer link is inferred",
            "PLONK and non-snarkjs ABI/template variants may be missed",
        ],
        "elapsed_seconds": round((dt.datetime.now(dt.UTC) - started).total_seconds(), 3),
    }
    (DATASET / "onchain-census-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
