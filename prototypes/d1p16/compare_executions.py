#!/usr/bin/env python3
"""Concretize the AST-extracted relation against the five archived executions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from extract_relation import Extractor, UINT256_MAX


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def number(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("0x"):
            return int(value, 16)
        if value.isdigit():
            return int(value)
    return value


def map_value(entries: dict[int, Any], default: Any) -> dict[Any, Any]:
    return {"__default__": default, **entries}


def eval_ir(expr: Any, context: dict[str, Any]) -> Any:
    if isinstance(expr, list):
        return [eval_ir(x, context) for x in expr]
    if not isinstance(expr, dict) or "op" not in expr:
        return expr
    op, args = expr["op"], expr["args"]
    if op == "const":
        return args[0]
    if op == "symbol":
        return context[args[0]]
    if op == "storage":
        return context[f"pre.{args[0]}"]
    if op == "select":
        mapping, key = eval_ir(args[0], context), eval_ir(args[1], context)
        return mapping.get(key, mapping["__default__"])
    if op == "store":
        mapping = dict(eval_ir(args[0], context))
        mapping[eval_ir(args[1], context)] = eval_ir(args[2], context)
        return mapping
    if op == "cast":
        return eval_ir(args[1], context)
    if op == "not":
        return not eval_ir(args[0], context)
    if op == "relation":
        # This concrete oracle comes from an actual verifier call in each archived
        # execution. It does not alter the extracted symbolic boundary.
        return context["producer_relation"]
    a = eval_ir(args[0], context)
    b = eval_ir(args[1], context) if len(args) > 1 else None
    operations = {
        "eq": lambda: a == b,
        "neq": lambda: a != b,
        "lt": lambda: a < b,
        "le": lambda: a <= b,
        "gt": lambda: a > b,
        "ge": lambda: a >= b,
        "add": lambda: a + b,
        "sub": lambda: a - b,
        "mul": lambda: a * b,
        "add_mod": lambda: (a + b) % (UINT256_MAX + 1),
        "sub_mod": lambda: (a - b) % (UINT256_MAX + 1),
        "mul_mod": lambda: (a * b) % (UINT256_MAX + 1),
        "no_overflow_add": lambda: a + b <= UINT256_MAX,
        "no_underflow_sub": lambda: a >= b,
        "no_overflow_mul": lambda: a == 0 or b <= UINT256_MAX // a,
    }
    if op not in operations:
        raise NotImplementedError(op)
    return operations[op]()


def proof_context(proof: dict[str, Any], basefee: int, pre: dict[str, Any], sender: int) -> dict[str, Any]:
    inputs = proof["proofInputs"]
    names = {
        "_nullifier": "nullifier",
        "_amount": "amount",
        "_gigaRoot": "giga_root",
        "_localRoot": "destination_local_root",
        "_feeFactor": "fee_factor",
        "_priorityFee": "priority_fee",
        "_maxFee": "max_fee",
        "_relayer": "relayer_address",
        "_recipient": "recipient_address",
    }
    context = {f"calldata.{target}": number(inputs[source]) for target, source in names.items()}
    context.update({
        "calldata._poof": proof.get("proofSha256", "archived-proof"),
        "block.chainid": number(inputs["chain_id"]),
        "block.basefee": basefee,
        "msg.sender": sender,
        "producer_relation": True,
        "pre.aztecWarptoadAddress": number(inputs["aztec_warptoad_address"]),
        "pre.withdrawVerifier": 0xBEEF,
        "pre.gigaRootHistory": map_value({number(inputs["giga_root"]): True}, False),
        "pre.localRootHistory": map_value({number(inputs["destination_local_root"]): True}, False),
        "pre.nullifiers": map_value({number(inputs["nullifier"]): bool(pre["nullifierExists"])}, False),
        "pre._balances": map_value({
            number(inputs["relayer_address"]): number(pre["relayerBalance"]),
            number(inputs["recipient_address"]): number(pre["recipientBalance"]),
        }, 0),
        "pre._totalSupply": number(pre["totalSupply"]),
    })
    return context


def selected_path(relation: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    matches, errors = [], []
    for path in relation["paths"]:
        try:
            if all(bool(eval_ir(guard, context)) for guard in path["guards_ir"]):
                matches.append(path)
        except Exception as exc:  # evidence should retain evaluator failures
            errors.append(f"{path['id']}: {type(exc).__name__}: {exc}")
    if len(matches) != 1:
        errors.append(f"expected exactly one concrete path, found {len(matches)}: {[p['id'] for p in matches]}")
        return None, errors
    return matches[0], errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--build-info", type=Path, required=True)
    parser.add_argument("--compiler-output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.paper_root.resolve()
    paths = {
        "honest_proof": root / "results/raw/D1P-12R/honest-proof.json",
        "honest_receipt": root / "results/raw/D1P-12R/mint-receipt.json",
        "execution": root / "results/raw/D1P-12R/execution-result.json",
        "fc_proof": root / "results/raw/D1P-14A/fc-pos-proof.json",
        "fc_pos": root / "results/raw/D1P-14A/fc-pos-receipt.json",
        "fc_neg": root / "results/raw/D1P-14A/fc-neg-receipt.json",
        "zero_proof": root / "results/raw/D1P-14A/zero-fee-proof.json",
        "zero_receipt": root / "results/raw/D1P-14A/zero-fee-receipt.json",
        "manual": root / "results/raw/D1P-14B/lowering-validation.json",
    }
    evidence = {name: load(path) for name, path in paths.items()}
    relation = Extractor(args.build_info, args.compiler_output, args.source).extract()
    expected_cases = evidence["manual"]["cases"]
    sender = number(evidence["execution"]["accounts"]["sender"])

    honest_pre = evidence["honest_receipt"]["pre"]
    common_fc_pre = evidence["fc_pos"]["pre"]
    zero_pre = evidence["zero_receipt"]["pre"]
    replay_pre = {**evidence["execution"]["mint"]["post"], "nullifierExists": True}
    cases = {
        "D1P-12R_honest": (evidence["honest_proof"], number(evidence["honest_receipt"]["block"]["baseFeePerGas"]), honest_pre),
        "D1P-12R_replay": (evidence["honest_proof"], number(evidence["honest_receipt"]["block"]["baseFeePerGas"]), replay_pre),
        "D1P-14A_FC-POS": (evidence["fc_proof"], number(evidence["fc_pos"]["block"]["baseFeePerGas"]), common_fc_pre),
        "D1P-14A_FC-NEG": (evidence["fc_proof"], number(evidence["fc_neg"]["block"]["baseFeePerGas"]), evidence["fc_neg"]["consumerState"]["pre"] | {"relayerBalance": evidence["fc_neg"]["consumerState"]["pre"]["relayerTokenBalance"], "recipientBalance": evidence["fc_neg"]["consumerState"]["pre"]["recipientTokenBalance"]}),
        "D1P-14A_zero-fee": (evidence["zero_proof"], number(evidence["zero_receipt"]["block"]["baseFeePerGas"]), {**zero_pre, "relayerBalance": zero_pre["relayerTokenBalance"], "recipientBalance": zero_pre["recipientTokenBalance"]}),
    }
    expected_posts = {
        "D1P-12R_honest": evidence["honest_receipt"]["post"],
        "D1P-12R_replay": replay_pre,
        "D1P-14A_FC-POS": evidence["fc_pos"]["post"],
        "D1P-14A_FC-NEG": evidence["fc_neg"]["consumerState"]["post"],
        "D1P-14A_zero-fee": evidence["zero_receipt"]["post"],
    }

    results, disagreements = {}, []
    for name, (proof, basefee, pre) in cases.items():
        # Normalize differing receipt field names.
        pre = dict(pre)
        pre.setdefault("relayerBalance", pre.get("relayerTokenBalance", "0"))
        pre.setdefault("recipientBalance", pre.get("recipientTokenBalance", "0"))
        context = proof_context(proof, basefee, pre, sender)
        path, errors = selected_path(relation, context)
        case_disagreements = list(errors)
        expected = expected_cases[name]
        if path is not None:
            actual_success = path["status"] == "success"
            if actual_success != expected["success"]:
                case_disagreements.append(f"success: extracted={actual_success} expected={expected['success']}")
            if not actual_success:
                if path["revert"]["reason"] != expected["revert_reason"]:
                    case_disagreements.append(f"reason: extracted={path['revert']['reason']!r} expected={expected['revert_reason']!r}")
                if path["revert"]["location"] != expected["revert_location"]:
                    case_disagreements.append(f"location: extracted={path['revert']['location']!r} expected={expected['revert_location']!r}")
                if path["committed"]["storage_writes"] or path["committed"]["mints"]:
                    case_disagreements.append("revert committed tentative effects")

            actual_mints = [
                {
                    "beneficiary": eval_ir(mint["beneficiary_ir"], context),
                    "amount": eval_ir(mint["amount_ir"], context),
                    "location": mint["location"],
                }
                for mint in path["committed"]["mints"]
            ]
            expected_mints = [
                {"beneficiary": item["beneficiary"], "amount": item["amount"], "location": item["callsite"]}
                for item in expected["occurrences"]
            ]
            if actual_mints != expected_mints:
                case_disagreements.append(f"mints: extracted={actual_mints!r} expected={expected_mints!r}")

            post_ir = path["committed"]["post_state_ir"]
            post_nullifiers = eval_ir(post_ir.get("nullifiers", {"op": "storage", "args": ["nullifiers"]}), context)
            post_balances = eval_ir(post_ir.get("_balances", {"op": "storage", "args": ["_balances"]}), context)
            post_supply = eval_ir(post_ir.get("_totalSupply", {"op": "storage", "args": ["_totalSupply"]}), context)
            relevant_addresses = {number(proof["proofInputs"]["relayer_address"]), number(proof["proofInputs"]["recipient_address"])}
            actual_state = {
                "nullifier_present": bool(post_nullifiers.get(number(proof["proofInputs"]["nullifier"]), post_nullifiers["__default__"])),
                "balances": {str(address): post_balances.get(address, post_balances["__default__"]) for address in relevant_addresses},
                "total_supply": post_supply,
            }
            expected_post = expected_posts[name]
            relayer = number(proof["proofInputs"]["relayer_address"])
            recipient = number(proof["proofInputs"]["recipient_address"])
            expected_state = {
                "nullifier_present": bool(expected_post["nullifierExists"]),
                "balances": {
                    str(relayer): number(expected_post.get("relayerBalance", expected_post.get("relayerTokenBalance", 0))),
                    str(recipient): number(expected_post.get("recipientBalance", expected_post.get("recipientTokenBalance", 0))),
                },
                "total_supply": number(expected_post["totalSupply"]),
            }
            if actual_state != expected_state:
                case_disagreements.append(f"post_state: extracted={actual_state!r} expected={expected_state!r}")

            extracted_words = [eval_ir(item["expression_ir"], context) for item in relation["verifier_boundary"]["public_words"]]
            expected_words = [number(item) for item in proof["publicInputs"]]
            word_mismatches = [i for i, (a, b) in enumerate(zip(extracted_words, expected_words)) if a != b]
            if len(extracted_words) != len(expected_words) or word_mismatches:
                case_disagreements.append(f"public_words: mismatching indices={word_mismatches}")

            results[name] = {
                "selected_path": path["id"],
                "status": path["status"],
                "revert": path["revert"],
                "public_words_exact": not word_mismatches and len(extracted_words) == len(expected_words),
                "mints": actual_mints,
                "post_state": actual_state,
                "rollback": path["rollback"],
                "disagreements": case_disagreements,
            }
        else:
            results[name] = {"selected_path": None, "disagreements": case_disagreements}
        disagreements += [f"{name}: {item}" for item in case_disagreements]

    report = {
        "schema": "bindcheck.d1p16.concrete-comparison.v1",
        "relation_summary": relation["summary"],
        "evidence": [digest(path) for path in paths.values()],
        "cases": results,
        "disagreements": disagreements,
        "all_checks_pass": not disagreements,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
