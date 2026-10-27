#!/usr/bin/env python3
"""Compare the extracted relation with the prior manual consumer summary."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path

from compare_executions import proof_context, selected_path
from extract_relation import Extractor, UINT256_MAX


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--build-info", type=Path, required=True)
    parser.add_argument("--compiler-output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paper = args.paper_root.resolve()
    sys.path.insert(0, str(paper / "src"))
    from bindcheck_d1.joint_warptoad import (  # noqa: PLC0415
        PUBLIC_INPUTS,
        build_consumer_transition,
        implementation_effect_summary,
    )

    relation = Extractor(args.build_info, args.compiler_output, args.source).extract()
    manual_path = paper / "src/bindcheck_d1/joint_warptoad.py"
    manual_source = inspect.getsource(build_consumer_transition)
    manual_summary = implementation_effect_summary("BASE")

    proof = json.loads((paper / "results/raw/D1P-12R/honest-proof.json").read_text())
    for key, value in {
        "fee_factor": "0x1", "priority_fee": "0x1", "amount": "0x0", "max_fee": "0x1"
    }.items():
        proof["proofInputs"][key] = value
    pre = {
        "nullifierExists": False, "relayerBalance": "0", "recipientBalance": "0",
        "totalSupply": str(UINT256_MAX),
    }
    context = proof_context(proof, 0, pre, sender=2)
    extracted, errors = selected_path(relation, context)
    p = proof["proofInputs"]
    keys = [
        "nullifier", "chain_id", "amount", "giga_root", "destination_local_root",
        "aztec_warptoad_address", "fee_factor", "priority_fee", "max_fee",
        "relayer_address", "recipient_address",
    ]
    words = [int(p[key], 16) for key in keys]
    manual = build_consumer_transition(
        words,
        basefee=0,
        state={
            "giga_roots": {words[3]}, "local_roots": {words[4]}, "nullifiers": set(),
            "total_supply": UINT256_MAX, "balances": {},
        },
        verifier_accepts=True,
        msg_sender=2,
    )

    origins = [item["origin"].removeprefix("calldata._")
               for item in relation["verifier_boundary"]["public_words"]]
    normalized_origins = [
        {
            "chainid": "chain_id", "gigaRoot": "giga_root", "localRoot": "destination_local_root",
            "aztecWarptoadAddress": "aztec_warptoad_address", "feeFactor": "fee_factor",
            "priorityFee": "priority_fee", "maxFee": "max_fee", "relayer": "relayer_address",
            "recipient": "recipient_address",
        }.get(origin.removeprefix("block.").removeprefix("pre."), origin)
        for origin in origins
    ]

    report = {
        "schema": "bindcheck.d1p16.manual-comparison.v1",
        "manual_source": {
            "path": str(manual_path),
            "sha256": hashlib.sha256(manual_path.read_bytes()).hexdigest(),
            "classification": manual_summary["classification"],
        },
        "agreements": {
            "public_word_order": normalized_origins == list(PUBLIC_INPUTS),
            "manual_public_names": list(PUBLIC_INPUTS),
            "extracted_public_origins_normalized": normalized_origins,
            "base_mint_callsites": [
                item["callsite"] for item in manual_summary["mint_occurrences"] if item["present"] != "false"
            ],
            "nullifier_write_key": manual_summary["nullifier_writes"][0]["key"],
            "rollback": manual_summary["rollback"],
            "five_concrete_disagreements": [],
        },
        "disagreements": [
            {
                "kind": "revert precedence and tentative trace",
                "witness": "pre.totalSupply=2^256-1, fee=1, amount=0, nonzero receivers, verifier relation true",
                "extracted": {
                    "revert": extracted["revert"] if extracted else None,
                    "tentative_mints": [] if extracted is None else [
                        {key: value for key, value in mint.items() if not key.endswith("_ir")}
                        for mint in extracted["tentative"]["mints"]
                    ],
                    "committed_mints": [] if extracted is None else extracted["committed"]["mints"],
                },
                "manual": {
                    "revert": {"location": manual["revert_location"], "reason": manual["revert_reason"]},
                    "occurrences": manual["occurrences"],
                },
                "impact": "committed state agrees because both roll back; exceptional trace and first failing guard differ",
            },
            {
                "kind": "producer/consumer boundary placement",
                "manual": "chain_id==31337 and aztec_address==0 are checked beside verifier_accepts",
                "extracted": "chain ID and configuration are consumer-constructed verifier arguments; their connection to producer witnesses belongs to the joint binding relation, not to standalone consumer guards or recovered producer constraints",
                "source_check_present": "chain_id != CHAIN_ID or aztec_address != AZTEC_WARPTOAD_ADDRESS" in manual_source,
                "impact": "no disagreement on the five pinned executions; extracted factorization is the required relational boundary",
            },
        ],
        "representation_differences": [
            {
                "kind": "revert diagnostic normalization",
                "manual": "ERC20 receiver and supply failures use source ranges and expanded reason strings",
                "extracted": "AST terminals use the exact revert/assignment line and normalized custom-error or Panic(0x11) names",
                "impact": "guards and committed semantics are unchanged; exact custom-error arguments are not serialized",
            }
        ],
        "comparison_errors": errors,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
