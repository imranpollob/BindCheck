#!/usr/bin/env python3
"""Passive reads for source-lead deployment candidates with explicit roles."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import urllib.request

from census_sourcify import analyze_bytecode


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "feasibility/work/v2/repos/RippnerLabs__meridian-link/config/sepolia_address_book.json"
OUT = ROOT / "dataset"
RAW = OUT / "raw" / "p4-candidate-reads-2026-11-03-v1"
RPC = "https://ethereum-sepolia-rpc.publicnode.com"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text())
    verifier = config["verifierSmartContractAddress"].lower()
    consumer = config["bridgeSmartContractAddress"].lower()
    token = config["tokenSmartContractAddress"].lower()
    balance_of = "0x70a08231" + consumer[2:].rjust(64, "0")
    calls = [
        ("verifier_code", "eth_getCode", [verifier, "latest"]),
        ("verifier_native_balance", "eth_getBalance", [verifier, "latest"]),
        ("consumer_code", "eth_getCode", [consumer, "latest"]),
        ("consumer_native_balance", "eth_getBalance", [consumer, "latest"]),
        ("consumer_token_balance", "eth_call", [{"to": token, "data": balance_of}, "latest"]),
        ("token_decimals", "eth_call", [{"to": token, "data": "0x313ce567"}, "latest"]),
    ]
    payload = [{"jsonrpc": "2.0", "id": index + 1, "method": method, "params": params}
               for index, (_, method, params) in enumerate(calls)]
    request = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={
        "content-type": "application/json", "user-agent": "BindCheck-academic-census/1"})
    response = json.loads(urllib.request.urlopen(request, timeout=30).read())
    (RAW / "rpc-read.json").write_text(json.dumps({"rpc": RPC, "calls": calls, "response": response}, indent=2) + "\n")
    values = {calls[item["id"] - 1][0]: item.get("result") for item in response}
    bytecode = values["verifier_code"]
    analysis = analyze_bytecode(bytecode)
    row = {
        "repository": "RippnerLabs/meridian-link",
        "commit": "5a5a9f6eb2983ea38fb9475c9cd781514569e166",
        "chain_id": 11155111, "network": "sepolia-testnet",
        "verifier_address": verifier, "consumer_address": consumer, "token_address": token,
        "verifier_runtime_sha256": hashlib.sha256(bytes.fromhex(bytecode[2:])).hexdigest(),
        "default_g2_constant_counts": json.dumps(analysis["default_g2_constant_counts"]),
        "default_g2_twice_gamma_delta_signature": analysis["default_g2_twice_gamma_delta_signature"],
        "scalar_field_push32_present": analysis["scalar_field_push32_present"],
        "verifier_native_balance_wei": int(values["verifier_native_balance"], 16),
        "consumer_native_balance_wei": int(values["consumer_native_balance"], 16),
        "consumer_token_balance_raw": int(values["consumer_token_balance"], 16),
        "token_decimals": int(values["token_decimals"], 16),
        "source_runtime_correspondence": "UNKNOWN",
        "production_funds_at_risk": False,
        "verdict": "UNKNOWN",
        "notes": "explicit verifier/bridge/token roles in repository config; testnet token units have no inferred market value",
    }
    with (OUT / "p4-deployment-reads.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    summary = {"candidates_read": 1, "testnet_candidates": 1,
               "default_g2_bytecode_signatures": int(row["default_g2_twice_gamma_delta_signature"]),
               "production_funded_vulnerable_instances": 0, "safety_stop_triggered": False}
    (OUT / "p4-deployment-read-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
