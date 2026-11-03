#!/usr/bin/env python3
"""Build the frozen 50-project metadata/evidence ledger from scan outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--scan", type=Path, default=here / "raw" / "candidates-v5.json")
    parser.add_argument("--ast", type=Path, default=here / "raw" / "solc-ast.json")
    parser.add_argument("--output", type=Path, default=here / "candidate-set.csv")
    args = parser.parse_args()

    scan = json.loads(args.scan.read_text(encoding="utf-8"))
    ast = {
        item["repository"]: item
        for item in json.loads(args.ast.read_text(encoding="utf-8"))
    }
    selected = [
        item for item in scan
        if item.get("circuit") and item.get("verifier") and item.get("consumer")
    ][:50]
    if len(selected) != 50:
        raise SystemExit(f"expected 50 selected projects, got {len(selected)}")

    fields = [
        "repository", "commit", "provenance", "pairing_status", "circuit",
        "verifier", "consumer", "public_signals", "check_A", "check_B",
        "check_C", "solc_ast", "solc_ast_facts", "evidence_grade", "verdict", "notes",
    ]
    rows = []
    for item in selected:
        paired = item["eligibility"] == "source-pair"
        default_check = "no-warning" if paired else "not-evaluated:pair-unresolved"
        row = {
            "repository": item["repository"],
            "commit": item["commit"],
            "provenance": item["provenance"],
            "pairing_status": "heuristic-pair" if paired else "unresolved",
            "circuit": item["circuit"],
            "verifier": item["verifier"],
            "consumer": item["consumer"],
            "public_signals": json.dumps(item["public_signals"] or ["UNKNOWN"]),
            "check_A": " | ".join(item["checks"]["A"]) or default_check,
            "check_B": " | ".join(item["checks"]["B"]) or default_check,
            "check_C": " | ".join(item["checks"]["C"]) or default_check,
            "solc_ast": ast.get(item["repository"], {}).get("status", "not-run"),
            "solc_ast_facts": json.dumps(
                ast.get(item["repository"], {}).get("facts", {}), sort_keys=True
            ),
            "evidence_grade": "E1" if any(item["checks"].values()) else "E0",
            "verdict": "UNKNOWN",
            "notes": "; ".join(item["limitations"]),
        }
        if item["repository"] == "0xbow-io/privacy-pools-core":
            row.update({
                "pairing_status": "manual-pair+r1cs",
                "circuit": "packages/circuits/circuits/withdraw.circom",
                "verifier": "packages/contracts/src/contracts/verifiers/WithdrawalVerifier.sol",
                "consumer": "packages/contracts/src/contracts/PrivacyPool.sol",
                "public_signals": json.dumps([
                    "newCommitmentHash", "existingNullifierHash", "withdrawnValue",
                    "stateRoot", "stateTreeDepth", "ASPRoot", "ASPTreeDepth", "context",
                ]),
                "check_A": "no-warning:r1cs/source adjudicated",
                "check_B": "no-warning:spent read+write and verifier field check present",
                "check_C": "no-warning:r1cs=8, verifier=8, ProofLib order=8",
                "notes": "snarkjs r1cs info: 2 outputs + 6 public inputs; .sym and ProofLib order agree",
            })
        if item["repository"] == "zkemail/proof-of-twitter":
            row.update({
                "pairing_status": "manual-source-pair",
                "public_signals": json.dumps(["pubkeyHash", "twitterUsername", "address"]),
                "check_A": "no-warning",
                "check_B": "no-warning",
                "check_C": "no-warning: compile-time exposeFrom=0 prunes conditional 9-signal output; circuit/verifier/consumer=3",
                "evidence_grade": "E0",
                "notes": "manual static-parameter adjudication resolves the initial lexical warning; solc dependency closure unavailable",
            })
        if item["repository"] == "SovereignWave/qwer":
            row["pairing_status"] = "placeholder-excluded"
            row["notes"] = "verifier explicitly described as simplified/simulated; retained for corpus accounting only"
        rows.append(row)

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "rows": len(rows),
        "E1": sum(row["evidence_grade"] == "E1" for row in rows),
        "ast": sum(row["solc_ast"] == "ast" for row in rows),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
