"""D1P-14D deterministic regression controls over the D1P-14C model.

This module does not modify D1P-14C.  It fixes one existing honest fixture in
otherwise unchanged dropped-producer control queries and changes the terminal
goal from the AUTH disjunction to the designated G1/G3/G4/G5 predicate.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from bindcheck_d1.joint_warptoad import (
    PUBLIC_INPUTS,
    balanced_smt_parentheses,
    build_omega,
    canonical_bytes,
    canonical_sha256,
    encode_query,
    lower_mint,
)


CONTROL_VARIANTS = {
    "C1": ("C1_FULL_RECIPIENT_PLUS_FEE", "G1"),
    "C2": ("C2_FEE_TO_RECIPIENT", "G3"),
    "C3": ("C3_EXTRA_MINT", "G4"),
    "C4": ("C4_WRONG_NULLIFIER_WRITE", "G5"),
}


def _integer(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def freeze_honest_fixture(proof_record: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Freeze the public/environment/state values from D1P-14A FC-POS."""
    inputs = proof_record["proofInputs"]
    public = [_integer(inputs[name]) for name in PUBLIC_INPUTS]
    basefee = _integer(receipt["block"]["baseFeePerGas"])
    relayer, recipient = public[9], public[10]
    amount, fee_factor, priority_fee, max_fee = public[2], public[6], public[7], public[8]
    fee_base = basefee + priority_fee
    fee = fee_factor * fee_base
    checks = {
        "eleven_public_inputs": len(public) == 11,
        "positive_fee": fee > 0,
        "distinct_beneficiaries": relayer != recipient,
        "named_relayer_not_wildcard": relayer != 1,
        "fee_addition_uint256": fee_base < 2**256,
        "fee_multiplication_uint256": fee < 2**256,
        "fee_within_cap": fee <= max_fee,
        "fee_within_amount": fee <= amount,
        "receipt_fee_matches": fee == _integer(receipt["effects"]["relayerDelta"]),
        "receipt_recipient_matches": amount - fee == _integer(receipt["effects"]["recipientDelta"]),
        "receipt_conservation_matches": amount == _integer(receipt["effects"]["totalSupplyDelta"]),
        "receipt_nullifier_initially_unused": receipt["pre"]["nullifierExists"] is False,
    }
    if not all(checks.values()):
        raise ValueError(f"honest control fixture prerequisites failed: {checks}")
    return {
        "schema": "bindcheck.d1p14d.fixed-control-fixture/v1",
        "classification": "concrete encoder regression fixture derived from D1P-14A FC-POS",
        "source": {
            "proof_record": "results/raw/D1P-14A/fc-pos-proof.json",
            "receipt": "results/raw/D1P-14A/fc-pos-receipt.json",
        },
        "public_order": list(PUBLIC_INPUTS),
        "public_inputs": {name: str(public[index]) for index, name in enumerate(PUBLIC_INPUTS)},
        "public_words": list(map(str, public)),
        "environment": {
            "basefee": str(basefee),
            "msg_sender": str(relayer),
            "named_relayer": True,
        },
        "admitted_state": {
            "giga_root_history": [str(public[3])],
            "local_root_history": [str(public[4])],
            "nullifiers": [],
            "total_supply": str(receipt["pre"]["totalSupply"]),
            "balances": {str(relayer): "0", str(recipient): "0"},
            "fixed_assumption": "owned-local D1P-14A FC-POS pre-mint state",
        },
        "derived_arithmetic": {
            "fee_base": str(fee_base), "fee": str(fee),
            "recipient_remainder": str(amount - fee),
        },
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "claim_boundary": "fixed concrete inputs for encoder regression only; not a search-capability or performance fixture",
    }


def fixture_words(fixture: dict[str, Any]) -> list[int]:
    return [int(value) for value in fixture["public_words"]]


def fixture_state(fixture: dict[str, Any]) -> dict[str, Any]:
    state = fixture["admitted_state"]
    return {
        "giga_roots": set(map(int, state["giga_root_history"])),
        "local_roots": set(map(int, state["local_root_history"])),
        "nullifiers": set(map(int, state["nullifiers"])),
        "total_supply": int(state["total_supply"]),
        "balances": {int(key): int(value) for key, value in state["balances"].items()},
    }


def expected_effect_records(fixture: dict[str, Any]) -> dict[str, Any]:
    """Evaluate each polarity before solving and cross-check direct arithmetic."""
    words = fixture_words(fixture)
    basefee = int(fixture["environment"]["basefee"])
    msg_sender = int(fixture["environment"]["msg_sender"])
    amount = words[2]
    fee = words[6] * (basefee + words[7])
    direct = {
        "BASE": {
            "mint_amounts": [fee, amount - fee],
            "mint_beneficiaries": [words[9], words[10]],
            "nullifier_write_keys": [words[0]],
            "goals": {"G1": False, "G2": False, "G3": False, "G4": False, "G5": False},
        },
        "C1": {
            "mint_amounts": [fee, amount],
            "mint_beneficiaries": [words[9], words[10]],
            "nullifier_write_keys": [words[0]],
            "goals": {"G1": True, "G2": False, "G3": False, "G4": False, "G5": False},
        },
        "C2": {
            "mint_amounts": [fee, amount - fee],
            "mint_beneficiaries": [words[10], words[10]],
            "nullifier_write_keys": [words[0]],
            "goals": {"G1": False, "G2": False, "G3": True, "G4": False, "G5": False},
        },
        "C3": {
            "mint_amounts": [fee, amount - fee, 0],
            "mint_beneficiaries": [words[9], words[10], words[10]],
            "nullifier_write_keys": [words[0]],
            "goals": {"G1": False, "G2": False, "G3": False, "G4": True, "G5": False},
        },
        "C4": {
            "mint_amounts": [fee, amount - fee],
            "mint_beneficiaries": [words[9], words[10]],
            "nullifier_write_keys": [words[0], (words[0] + 1) % 2**256],
            "goals": {"G1": False, "G2": False, "G3": False, "G4": False, "G5": True},
        },
    }
    records: dict[str, Any] = {}
    for control, (variant, target) in CONTROL_VARIANTS.items():
        positive = lower_mint(
            words, basefee=basefee, state=fixture_state(fixture), msg_sender=msg_sender,
            implementation_variant=variant,
        )
        negative = lower_mint(
            words, basefee=basefee, state=fixture_state(fixture), msg_sender=msg_sender,
            implementation_variant="BASE",
        )
        observed_positive = {
            "mint_amounts": [item["amount"] for item in positive["occurrences"]],
            "mint_beneficiaries": [item["beneficiary"] for item in positive["occurrences"]],
            "nullifier_write_keys": [item["key"] for item in positive["nullifier_writes"]],
            "goals": positive["goals"],
        }
        observed_negative = {
            "mint_amounts": [item["amount"] for item in negative["occurrences"]],
            "mint_beneficiaries": [item["beneficiary"] for item in negative["occurrences"]],
            "nullifier_write_keys": [item["key"] for item in negative["nullifier_writes"]],
            "goals": negative["goals"],
        }
        checks = {
            "positive_transition_success": positive["success"],
            "negative_transition_success": negative["success"],
            "positive_direct_effects_match": observed_positive == direct[control],
            "negative_direct_effects_match": observed_negative == direct["BASE"],
            "positive_target_true": positive["goals"][target] is True,
            "negative_target_false": negative["goals"][target] is False,
            "positive_only_designated_goal": [name for name, value in positive["goals"].items() if value] == [target],
            "negative_no_violation": not any(negative["goals"].values()),
        }
        if not all(checks.values()):
            raise ValueError(f"expected-effect check failed for {control}: {checks}")
        records[control] = {
            "variant": variant, "target": target,
            "positive": observed_positive, "negative": observed_negative,
            "direct_expected_positive": direct[control],
            "direct_expected_negative": direct["BASE"],
            "checks": checks, "all_checks_pass": True,
        }
    return {
        "schema": "bindcheck.d1p14d.expected-effects/v1",
        "fixture_sha256": canonical_sha256(fixture),
        "policy": "unchanged D1P-14C G1-G5",
        "records": records,
        "all_checks_pass": all(item["all_checks_pass"] for item in records.values()),
        "classification": "pre-solve concrete encoder regression expectations; not solver search evidence",
    }


def _bv(value: int) -> str:
    return f"(_ bv{value} 256)"


def encode_concrete_control(
    artifact: Path, *, identities: dict[str, Any], fixture: dict[str, Any],
    control_id: str, polarity: str,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Generate one fixed-input positive or negative designated-goal query."""
    if control_id not in CONTROL_VARIANTS or polarity not in {"positive", "negative"}:
        raise ValueError((control_id, polarity))
    variant, target = CONTROL_VARIANTS[control_id]
    selected_variant = variant if polarity == "positive" else "BASE"
    omega = build_omega(
        artifact, goal="AUTH-1", s0=fixture["admitted_state"], identities=identities,
        implementation_variant=selected_variant,
        control_id=control_id if polarity == "positive" else None,
    )
    base, base_certificate = encode_query(omega, drop_producer=True)
    terminal = b"(assert (or G1 G2 G3 G4 G5))\n(check-sat)\n"
    if base.count(terminal) != 1:
        raise ValueError("unexpected D1P-14C terminal goal shape")
    words = fixture_words(fixture)
    fixed_lines = [
        "; D1P-14D concrete encoder regression",
        f"; fixture_sha256={canonical_sha256(fixture)}",
        f"; control={control_id} polarity={polarity} designated_goal={target}",
    ]
    fixed_lines.extend(f"(assert (= pi{index} {_bv(value)}))" for index, value in enumerate(words))
    fixed_lines.append(f"(assert (= basefee {_bv(int(fixture['environment']['basefee']))}))")
    fixed_lines.extend([f"(assert {target})", "(check-sat)"])
    query = base.replace(terminal, ("\n".join(fixed_lines) + "\n").encode())
    parens = balanced_smt_parentheses(query)
    if not parens["balanced"]:
        raise ValueError(f"unbalanced D1P-14D control query: {parens}")
    certificate = {
        "schema": "bindcheck.d1p14d.control-transformation/v1",
        "control": control_id, "polarity": polarity, "target": target,
        "implementation_variant": selected_variant,
        "policy_sha256": canonical_sha256(omega["policy"]),
        "fixture_sha256": canonical_sha256(fixture),
        "fixed_public_equalities": 11, "fixed_environment_equalities": 1,
        "producer_relation": "dropped exactly as D1P-14C control/Q1 route",
        "base_d1p14c_query_sha256": hashlib.sha256(base).hexdigest(),
        "base_d1p14c_certificate": base_certificate,
        "terminal_transformation": "replace AUTH disjunction assertion with designated target assertion after fixing pi0..pi10 and basefee",
        "balanced_parentheses": parens,
        "query_sha256": hashlib.sha256(query).hexdigest(), "query_bytes": len(query),
        "expected_answer": "SAT" if polarity == "positive" else "UNSAT",
        "claim_boundary": "deterministic concrete encoder regression only",
    }
    return query, certificate, omega


def audit_concrete_control(
    query: bytes, certificate: dict[str, Any], fixture: dict[str, Any],
) -> None:
    text = query.decode()
    if hashlib.sha256(query).hexdigest() != certificate["query_sha256"]:
        raise ValueError("query hash mismatch")
    if certificate["fixture_sha256"] != canonical_sha256(fixture):
        raise ValueError("fixture hash mismatch")
    marker = "; D1P-14D concrete encoder regression"
    if text.count(marker) != 1:
        raise ValueError("missing D1P-14D control marker")
    fixed_tail = text.split(marker, 1)[1]
    for index, value in enumerate(fixture_words(fixture)):
        if fixed_tail.count(f"(assert (= pi{index} {_bv(value)}))") != 1:
            raise ValueError(f"fixed pi{index} equality mismatch")
    basefee = int(fixture["environment"]["basefee"])
    if fixed_tail.count(f"(assert (= basefee {_bv(basefee)}))") != 1:
        raise ValueError("fixed basefee equality mismatch")
    target = certificate["target"]
    if text.count(f"(assert {target})") != 1:
        raise ValueError("designated goal assertion mismatch")
    if "(assert (or G1 G2 G3 G4 G5))" in text:
        raise ValueError("generic AUTH disjunction survived control transformation")
    if not balanced_smt_parentheses(query)["balanced"]:
        raise ValueError("query is not balanced")


def canonical_fixture_bytes(fixture: dict[str, Any]) -> bytes:
    return canonical_bytes(fixture)
