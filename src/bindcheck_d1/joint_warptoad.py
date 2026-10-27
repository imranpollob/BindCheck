"""D1P-14B WarpToad joint consumer/ACIR diagnostic encoding.

The module deliberately keeps three boundaries visible:

* :func:`lower_mint` is a concrete, occurrence-preserving lowering of the
  pinned ``WarpToadCore.mint`` and OpenZeppelin 5.6.1 ``ERC20._mint`` route.
* :func:`build_omega` is the canonical abstract object controlled by amended
  D1P-B01 section 6.
* :func:`encode_query` is a checked transformation of an Omega object.  It
  never interprets Poseidon2 or Brillig: Poseidon2 outputs and Brillig outputs
  remain free witnesses, while all decoded AssertZero and RANGE constraints
  are emitted exactly.

This is diagnostic machinery.  It does not establish a D1 verdict, verifier
soundness, hash collision resistance, or cross-chain reachability.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .frontends.acir_binary_beta22 import abi_bindings, decode
from .model_v2 import FIELD_MODULUS


UINT256 = 1 << 256
ADDRESS_LIMIT = 1 << 160
CHAIN_ID = 31337
AZTEC_WARPTOAD_ADDRESS = 0

PUBLIC_INPUTS = [
    "nullifier", "chain_id", "amount", "giga_root",
    "destination_local_root", "aztec_warptoad_address", "fee_factor",
    "priority_fee", "max_fee", "relayer_address", "recipient_address",
]

IMPLEMENTATION_VARIANTS = {"BASE", "C1_FULL_RECIPIENT_PLUS_FEE", "C2_FEE_TO_RECIPIENT", "C3_EXTRA_MINT", "C4_WRONG_NULLIFIER_WRITE"}


def canonical_bytes(value: Any) -> bytes:
    """RFC-8259 JSON profile used for Omega: UTF-8, sorted, compact, no LF."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checked_add(lhs: int, rhs: int) -> int | None:
    result = lhs + rhs
    return result if result < UINT256 else None


def _checked_mul(lhs: int, rhs: int) -> int | None:
    result = lhs * rhs
    return result if result < UINT256 else None


def build_consumer_transition(
    words: Iterable[int], *, basefee: int, state: dict[str, Any],
    verifier_accepts: bool = True, msg_sender: int = 0,
    implementation_variant: str = "BASE",
) -> dict[str, Any]:
    """Build the manual/assumed T_mint transition and committed effects.

    ``state`` contains the fixed pre-state abstractions used by section 6:
    giga/local root history, consumed nullifiers, total supply, and balances.
    The result contains implementation effects only, without G1--G5 or any
    policy verdict.  On every revert its post-state equals pre-state.
    """
    if implementation_variant not in IMPLEMENTATION_VARIANTS:
        raise ValueError(f"unknown implementation summary variant: {implementation_variant}")
    values = list(words)
    if len(values) != 11:
        raise ValueError("T_mint requires exactly eleven public words")
    if not 0 <= basefee < UINT256 or not 0 <= msg_sender < ADDRESS_LIMIT:
        raise ValueError("environment value outside EVM type")
    if any(not 0 <= value < UINT256 for value in values):
        raise ValueError("calldata word outside uint256")
    if any(not 0 <= values[index] < ADDRESS_LIMIT for index in (9, 10)):
        raise ValueError("address word outside uint160")

    pre = {
        "giga_roots": set(state["giga_roots"]),
        "local_roots": set(state["local_roots"]),
        "nullifiers": set(state.get("nullifiers", set())),
        "total_supply": int(state.get("total_supply", 0)),
        "balances": {int(k): int(v) for k, v in state.get("balances", {}).items()},
    }

    def reverted(location: str, reason: str) -> dict[str, Any]:
        return {
            "success": False, "revert_location": location, "revert_reason": reason,
            "state": pre, "occurrences": [], "aggregates": {},
            "nullifier_writes": [], "other_balance_changes": [],
            "implementation_variant": implementation_variant,
        }

    nullifier, chain_id, amount, giga_root, local_root, aztec_address, fee_factor, priority_fee, max_fee, relayer, recipient = values
    if giga_root not in pre["giga_roots"]:
        return reverted("WarpToadCore.sol:155", "_gigaRoot unknown")
    if local_root not in pre["local_roots"]:
        return reverted("WarpToadCore.sol:156", "_localRoot unknown")
    if nullifier in pre["nullifiers"]:
        return reverted("WarpToadCore.sol:157", "nullifier already exists")
    # The write at line 158 is tentative until the call commits.
    if chain_id != CHAIN_ID or aztec_address != AZTEC_WARPTOAD_ADDRESS or not verifier_accepts:
        return reverted("WarpToadCore.sol:161", "invalid proof")

    occurrences: list[dict[str, Any]] = []
    fee = 0
    if fee_factor != 0:
        fee_base = _checked_add(basefee, priority_fee)
        if fee_base is None:
            return reverted("WarpToadCore.sol:165", "Panic(0x11): uint256 addition overflow")
        fee_value = _checked_mul(fee_factor, fee_base)
        if fee_value is None:
            return reverted("WarpToadCore.sol:165", "Panic(0x11): uint256 multiplication overflow")
        fee = fee_value
        if fee > max_fee:
            return reverted("WarpToadCore.sol:166", "_relayerFee is larger than _maxFee")
        beneficiary = msg_sender if relayer == 1 else relayer
        if beneficiary == 0:
            return reverted("ERC20.sol:214-218", "ERC20InvalidReceiver(0)")
        if fee > amount:
            return reverted("WarpToadCore.sol:172", "Panic(0x11): uint256 subtraction underflow")
        if recipient == 0:
            return reverted("ERC20.sol:214-218", "ERC20InvalidReceiver(0)")
        occurrences = [
            {"kind": "mint", "role": "FEE", "callsite": "WarpToadCore.sol:171",
             "ordinal": 0, "beneficiary": beneficiary, "amount": fee},
            {"kind": "mint", "role": "RECIPIENT", "callsite": "WarpToadCore.sol:172",
             "ordinal": 1, "beneficiary": recipient, "amount": amount - fee},
        ]
    else:
        if recipient == 0:
            return reverted("ERC20.sol:214-218", "ERC20InvalidReceiver(0)")
        occurrences = [
            {"kind": "mint", "role": "RECIPIENT", "callsite": "WarpToadCore.sol:175",
             "ordinal": 0, "beneficiary": recipient, "amount": amount},
        ]

    # D1P-14C sensitivity controls mutate only this implementation summary.
    # The policy evaluator below is unchanged across all five variants.
    if implementation_variant == "C1_FULL_RECIPIENT_PLUS_FEE":
        if fee_factor == 0 or fee == 0:
            return reverted("D1P-14C-control", "C1 requires a positive fee")
        occurrences[1]["amount"] = amount
    elif implementation_variant == "C2_FEE_TO_RECIPIENT":
        if fee_factor == 0 or fee == 0 or relayer == recipient:
            return reverted("D1P-14C-control", "C2 requires positive fee and distinct beneficiaries")
        occurrences[0]["beneficiary"] = recipient
    elif implementation_variant == "C3_EXTRA_MINT":
        occurrences.append({
            "kind": "mint", "role": "RECIPIENT",
            "callsite": "D1P-14C-mutant:extra-mint", "ordinal": len(occurrences),
            "beneficiary": recipient, "amount": 0,
        })

    nullifier_writes = [{"key": nullifier, "value": True, "ordinal": 0}]
    if implementation_variant == "C4_WRONG_NULLIFIER_WRITE":
        nullifier_writes.append({
            "key": (nullifier + 1) % UINT256, "value": True, "ordinal": 1,
            "callsite": "D1P-14C-mutant:wrong-nullifier-write",
        })

    minted_total = sum(occurrence["amount"] for occurrence in occurrences)
    total_after = _checked_add(pre["total_supply"], minted_total)
    if total_after is None:
        return reverted("ERC20.sol:176-180", "Panic(0x11): totalSupply overflow")
    post = {
        "giga_roots": set(pre["giga_roots"]),
        "local_roots": set(pre["local_roots"]),
        "nullifiers": set(pre["nullifiers"]) | {item["key"] for item in nullifier_writes},
        "total_supply": total_after,
        "balances": dict(pre["balances"]),
    }
    for occurrence in occurrences:
        address = occurrence["beneficiary"]
        post["balances"][address] = post["balances"].get(address, 0) + occurrence["amount"]

    recipient_occ = [o for o in occurrences if o["role"] == "RECIPIENT"]
    fee_occ = [o for o in occurrences if o["role"] == "FEE"]
    recipient_sum = sum(o["amount"] for o in recipient_occ)
    fee_sum = sum(o["amount"] for o in fee_occ)
    balance_deltas: dict[int, int] = {}
    for occurrence in occurrences:
        address = occurrence["beneficiary"]
        balance_deltas[address] = balance_deltas.get(address, 0) + occurrence["amount"]
    aggregate_ok = all(
        post["balances"].get(address, 0) - pre["balances"].get(address, 0) == delta
        for address, delta in balance_deltas.items()
    ) and post["total_supply"] - pre["total_supply"] == recipient_sum + fee_sum
    return {
        "success": True, "revert_location": None, "revert_reason": None,
        "state": post, "occurrences": occurrences,
        "nullifier_writes": nullifier_writes,
        "other_balance_changes": [
            {"kind": "balance_credit", "source_occurrence_ordinal": occurrence["ordinal"],
             "beneficiary": occurrence["beneficiary"], "amount": occurrence["amount"]}
            for occurrence in occurrences
        ],
        "aggregates": {
            "recipient_amount": recipient_sum, "fee_amount": fee_sum,
            "total_minted": recipient_sum + fee_sum,
            "balance_deltas": balance_deltas, "crosscheck": aggregate_ok,
        },
        "implementation_variant": implementation_variant,
    }


def evaluate_effect_policy(transition: dict[str, Any], words: Iterable[int]) -> dict[str, Any]:
    """Evaluate the unchanged AUTH-1/NONVAC-1 policy over implementation effects."""
    values = list(words)
    if len(values) != 11:
        raise ValueError("policy requires exactly eleven public words")
    if not transition["success"]:
        goals = {f"G{i}": False for i in range(1, 6)}
        return {"goals": goals, "auth_violation": False, "nonvac": False}
    amount, max_fee, relayer, recipient = values[2], values[8], values[9], values[10]
    occurrences = transition["occurrences"]
    recipient_occ = [item for item in occurrences if item["role"] == "RECIPIENT"]
    fee_occ = [item for item in occurrences if item["role"] == "FEE"]
    total_minted = sum(item["amount"] for item in occurrences)
    fee_total = sum(item["amount"] for item in fee_occ)
    other = transition["other_balance_changes"]
    aggregate_ok = (
        len(other) == len(occurrences)
        and all(
            effect["source_occurrence_ordinal"] == occurrence["ordinal"]
            and effect["beneficiary"] == occurrence["beneficiary"]
            and effect["amount"] == occurrence["amount"]
            for effect, occurrence in zip(other, occurrences)
        )
        and transition["state"]["total_supply"] - total_minted >= 0
    )
    writes = transition["nullifier_writes"]
    goals = {
        "G1": total_minted != amount,
        "G2": fee_total > max_fee,
        "G3": any(item["beneficiary"] != recipient for item in recipient_occ)
              or any(item["beneficiary"] != relayer for item in fee_occ),
        "G4": len(recipient_occ) > 1 or len(fee_occ) > 1 or not aggregate_ok,
        "G5": len(writes) != 1 or any(item["key"] != values[0] for item in writes),
    }
    return {
        "goals": goals, "auth_violation": any(goals.values()),
        "nonvac": bool(occurrences or writes),
    }


def lower_mint(
    words: Iterable[int], *, basefee: int, state: dict[str, Any],
    verifier_accepts: bool = True, msg_sender: int = 0,
    implementation_variant: str = "BASE",
) -> dict[str, Any]:
    """Compatibility wrapper: manual transition first, unchanged policy second."""
    values = list(words)
    transition = build_consumer_transition(
        values, basefee=basefee, state=state, verifier_accepts=verifier_accepts,
        msg_sender=msg_sender, implementation_variant=implementation_variant,
    )
    return {**transition, **evaluate_effect_policy(transition, values)}


def _semantic_decoded(decoded: dict[str, Any]) -> dict[str, Any]:
    """Remove only path-bearing identity metadata from the decoded program."""
    return {
        "serialization": decoded["serialization"],
        "decoder_version": decoded["identity"]["decoder_version"],
        "artifact_sha256": decoded["identity"]["artifact_sha256"],
        "compressed_sha256": decoded["identity"]["compressed_sha256"],
        "abi": decoded["abi"],
        "functions": decoded["functions"],
        "unconstrained_functions": decoded["unconstrained_functions"],
    }


def implementation_effect_summary(variant: str = "BASE") -> dict[str, Any]:
    """Return the manual implementation IR without any policy predicates."""
    if variant not in IMPLEMENTATION_VARIANTS:
        raise ValueError(variant)
    fee_beneficiary = "pi10" if variant == "C2_FEE_TO_RECIPIENT" else "pi9"
    recipient_fee_amount = "pi2" if variant == "C1_FULL_RECIPIENT_PLUS_FEE" else "bvsub(pi2,fee_amount)"
    extra_present = variant == "C3_EXTRA_MINT"
    wrong_write_present = variant == "C4_WRONG_NULLIFIER_WRITE"
    occurrences = [
        {"id": "mint_fee", "kind": "mint", "role": "FEE", "callsite": "WarpToadCore.sol:171",
         "ordinal": 0, "present": "fee_branch", "amount": "fee_amount", "beneficiary": fee_beneficiary},
        {"id": "mint_recipient_fee", "kind": "mint", "role": "RECIPIENT",
         "callsite": "WarpToadCore.sol:172", "ordinal": 1, "present": "fee_branch",
         "amount": recipient_fee_amount, "beneficiary": "pi10"},
        {"id": "mint_recipient_zero", "kind": "mint", "role": "RECIPIENT",
         "callsite": "WarpToadCore.sol:175", "ordinal": 0, "present": "not_fee_branch",
         "amount": "pi2", "beneficiary": "pi10"},
        {"id": "mint_extra", "kind": "mint", "role": "RECIPIENT",
         "callsite": "D1P-14C-mutant:extra-mint", "ordinal": 2,
         "present": "true" if extra_present else "false", "amount": "zero",
         "beneficiary": "pi10"},
    ]
    writes = [
        {"id": "nullifier_primary", "kind": "nullifier_write", "ordinal": 0,
         "present": "true", "key": "pi0", "value": True},
        {"id": "nullifier_extra", "kind": "nullifier_write", "ordinal": 1,
         "present": "true" if wrong_write_present else "false",
         "key": "bvadd(pi0,one)", "value": True},
    ]
    return {
        "classification": "MANUAL / ASSUMED",
        "research_contract_boundary": "Necessary manual implementation summary under research contract section 6.3; excluded from automatic-extraction claims.",
        "variant": variant,
        "source_guards": [
            "gigaRootHistory[pi3]", "localRootHistory[pi4]", "!nullifiers[pi0]",
            "verify(proof,[pi0..pi10])", "checked fee arithmetic", "fee_amount <= pi8",
            "checked amount subtraction", "OpenZeppelin receiver/total-supply checks",
        ],
        "mint_occurrences": occurrences,
        "nullifier_writes": writes,
        "other_balance_changes": [
            {"id": f"balance_{item['id']}", "kind": "balance_credit",
             "source_occurrence": item["id"], "present": item["present"],
             "amount": item["amount"], "beneficiary": item["beneficiary"]}
            for item in occurrences
        ],
        "total_supply_change": "sum(amount of each present mint occurrence)",
        "rollback": "no committed occurrence or write on revert",
        "zero_value_executed_mint_is_occurrence": True,
        "equal_beneficiaries_do_not_merge_occurrences": True,
    }


def build_omega(
    artifact: Path, *, goal: str, s0: dict[str, Any], identities: dict[str, Any],
    implementation_variant: str = "BASE", control_id: str | None = None,
) -> dict[str, Any]:
    if goal not in {"AUTH-1", "NONVAC-1"}:
        raise ValueError(goal)
    decoded = decode(artifact)
    circuit = decoded["functions"][0]
    bindings = abi_bindings(decoded["abi"], circuit)
    if [bindings[name][0] for name in PUBLIC_INPUTS] != list(range(11)):
        raise ValueError("public ABI/witness mapping is not w0..w10")
    return {
        "schema": "bindcheck.d1p14c.omega/v1",
        "scope": {
            "protocol": "WarpToad", "revision": "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8",
            "call": "WarpToadCore.mint", "single_call": True,
            "same_chain": True, "owned_local": True, "fork": False,
            "named_relayer_restriction": "low160(w9) != address(1)",
            "cross_chain_reachability_claim": False,
        },
        "producer_relation_R_hat": _semantic_decoded(decoded),
        "hash_layer": {
            "classification": "L0_UNINTERPRETED_HAVOC",
            "Poseidon2Permutation": "all 86 output witnesses are free; no functionality, ground instance, collision, or preimage axiom",
            "bn254_poseidon": "arithmetic already lowered into AssertZero and retained exactly",
            "Brillig": "witness-generation machinery only; outputs free except for downstream ACIR constraints",
            "collision_resistance": "NOT_ASSUMED", "hash_completeness": "L0 only",
        },
        "decoder_boundary_D_v": {
            "word_count": 11, "field_modulus": FIELD_MODULUS,
            "rule": "each bytes32 public word is strictly below P and is then the identical field value",
            "address_words": [9, 10], "address_rule": "numeric value is below 2^160",
            "public_order": [{"word": i, "name": name, "witness": i}
                             for i, name in enumerate(PUBLIC_INPUTS)],
        },
        "consumer_T_mint": {
            "classification": "MANUAL / ASSUMED",
            "automatic_extraction_claim": False,
            "source": "WarpToadCore.sol:114-177",
            "ordered_guards": [
                "gigaRootHistory[w3]", "localRootHistory[w4]", "!nullifiers[w0]",
                "tentative nullifiers[w0]=true", "verify(proof, [w0..w10])",
                "checked fee arithmetic", "fee <= w8", "named relayer restriction",
                "OpenZeppelin _mint receiver and total-supply checks",
            ],
            "effect_occurrences": {
                "nonzero_fee": ["FEE@WarpToadCore.sol:171#0", "RECIPIENT@WarpToadCore.sol:172#1"],
                "zero_fee": ["RECIPIENT@WarpToadCore.sol:175#0"],
                "revert": [], "zero_value_executed_mint_is_occurrence": True,
                "equal_beneficiaries_remain_two_occurrences": True,
            },
            "rollback": "all tentative state and occurrences roll back on revert",
            "openzeppelin": identities["openzeppelin"],
            "transition_and_effects": implementation_effect_summary(implementation_variant),
            "supporting_concrete_differential_checks_only": [
                "D1P-12R honest mint", "D1P-12R replay rejection",
                "D1P-14A FC-POS", "D1P-14A FC-NEG", "D1P-14A zero-fee",
            ],
        },
        "environment": {
            "chain_id": CHAIN_ID, "basefee": "symbolic uint256",
            "msg_sender": "canonical ordinary local relayer by checked sender-independence substitution",
            "msg_sender_value": int("70997970c51812dc3a010c7d01b50e0d17dc79c8", 16),
        },
        "fixed_pre_state_S0": s0,
        "policy": {
            "status": "DRAFT, not approved",
            "evaluation_boundary": "evaluated after and over the independently serialized implementation effects",
            "included": {
                "F2a": "sum of committed mint occurrence amounts equals w2",
                "F4": "FEE occurrence sum is at most w8",
                "F5": "RECIPIENT beneficiaries equal low160(w10); FEE beneficiaries equal low160(w9)",
                "nullifier_linkage": "exactly one committed write keyed by w0",
            },
            "excluded": ["F3 fee formula as a policy condition", "coverage/F9", "consumer-direction claims"],
        },
        "auth_scope_choice": {
            "name": "AUTH-1[G1-G5]", "G4_retained": True, "G5_retained": True,
            "derivation": "G4 is computed from occurrence multiplicity and occurrence/balance crosschecks; G5 is computed from explicit nullifier-write presence and keys. Neither is inserted as a constant policy clause.",
        },
        "diagnostic_control": (
            {"id": control_id, "mutates_only": "consumer_T_mint.transition_and_effects",
             "policy_unchanged": True,
             "expected_goal": {"C1": "G1", "C2": "G3", "C3": "G4", "C4": "G5"}[control_id]}
            if control_id is not None else None
        ),
        "goal": {
            "name": goal,
            "formula": "successful T_mint and (G1 or G2 or G3 or G4 or G5)" if goal == "AUTH-1"
                       else "successful T_mint and at least one committed mint or nullifier-write occurrence",
        },
        "assumptions": [
            "generated verifier soundness for the committed artifact",
            "fixed S0 reconstructed from the owned-local setup",
            "DRAFT policy is the analysis target only",
        ],
        "identities": identities,
    }


def _ff(value: int) -> str:
    return f"(as ff{value % FIELD_MODULUS} F)"


def _ff_add(terms: list[str]) -> str:
    if not terms:
        return _ff(0)
    if len(terms) == 1:
        return terms[0]
    return "(ff.add " + " ".join(terms) + ")"


def _ff_mul(terms: list[str]) -> str:
    if not terms:
        return _ff(1)
    if len(terms) == 1:
        return terms[0]
    return "(ff.mul " + " ".join(terms) + ")"


def _expression(expression: dict[str, Any]) -> str:
    terms = [_ff(expression["constant"])]
    terms.extend(_ff_mul([_ff(coefficient), f"w{left}", f"w{right}"])
                 for coefficient, left, right in expression["mul"])
    terms.extend(_ff_mul([_ff(coefficient), f"w{witness}"])
                 for coefficient, witness in expression["linear"])
    return _ff_add(terms)


def _input_witnesses(opcode: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    kind = opcode["kind"]
    if kind == "AssertZero":
        for _coefficient, left, right in opcode["expression"]["mul"]:
            result.update((left, right))
        result.update(witness for _coefficient, witness in opcode["expression"]["linear"])
    elif kind == "RANGE":
        if "witness" in opcode["input"]:
            result.add(opcode["input"]["witness"])
    elif kind == "Poseidon2Permutation":
        result.update(item["witness"] for item in opcode["inputs"] if "witness" in item)
        result.update(opcode["outputs"])
    elif kind == "BrilligCall":
        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"witness", "simple", "memory_array"} and isinstance(child, int):
                        result.add(child)
                    else:
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(opcode)
    else:
        raise ValueError(f"unsupported opcode {kind}")
    return result


def _field_from_bv(bits: int, name: str) -> str:
    terms = [
        f"(ite (= ((_ extract {index} {index}) {name}) #b1) {_ff(1 << index)} {_ff(0)})"
        for index in range(bits)
    ]
    return _ff_add(terms)


def _bv(value: int, bits: int = 256) -> str:
    return f"(_ bv{value} {bits})"


def _bv_sum_no_overflow(lhs: str, rhs: str) -> str:
    return f"(bvuge (bvadd {lhs} {rhs}) {lhs})"


def _bv_product_no_overflow(lhs: str, rhs: str) -> str:
    return f"(= ((_ extract 511 256) (bvmul ((_ zero_extend 256) {lhs}) ((_ zero_extend 256) {rhs}))) {_bv(0)})"


def _bool_or(values: list[str]) -> str:
    if not values:
        return "false"
    if len(values) == 1:
        return values[0]
    return "(or " + " ".join(values) + ")"


def _bool_and(values: list[str]) -> str:
    if not values:
        return "true"
    if len(values) == 1:
        return values[0]
    return "(and " + " ".join(values) + ")"


def _bv_add(values: list[str]) -> str:
    if not values:
        return _bv(0)
    if len(values) == 1:
        return values[0]
    result = values[0]
    for value in values[1:]:
        result = f"(bvadd {result} {value})"
    return result


def _summary_expr(value: str) -> str:
    exact = {
        "true": "true", "false": "false", "fee_branch": "fee_branch",
        "not_fee_branch": "(not fee_branch)", "fee_amount": "fee_amount",
        "pi0": "pi0", "pi2": "pi2", "pi9": "pi9", "pi10": "pi10",
        "zero": _bv(0), "bvsub(pi2,fee_amount)": "(bvsub pi2 fee_amount)",
        "bvadd(pi0,one)": "(bvadd pi0 (_ bv1 256))",
    }
    if value not in exact:
        raise ValueError(f"unsupported manual-summary expression: {value}")
    return exact[value]


def _emit_consumer_transition(lines: list[str], omega: dict[str, Any]) -> dict[str, Any]:
    """Emit only the MANUAL/ASSUMED transition and effect representation."""
    summary = omega["consumer_T_mint"]["transition_and_effects"]
    giga_roots = [int(value) for value in omega["fixed_pre_state_S0"]["giga_root_history"]]
    local_roots = [int(value) for value in omega["fixed_pre_state_S0"]["local_root_history"]]
    total_supply = int(omega["fixed_pre_state_S0"]["total_supply"])
    root_or = lambda word, roots: _bool_or([f"(= {word} {_bv(root)})" for root in roots])
    lines.extend([
        "; IMPLEMENTATION_SUMMARY MANUAL_ASSUMED begin",
        "; source guards and successful-transition arithmetic",
        f"(assert (= pi1 {_bv(CHAIN_ID)}))",
        f"(assert (= pi5 {_bv(AZTEC_WARPTOAD_ADDRESS)}))",
        f"(assert {root_or('pi3', giga_roots)})",
        f"(assert {root_or('pi4', local_roots)})",
        f"(assert (not (= pi9 {_bv(1)})))",
        "(define-fun fee_branch () Bool (not (= pi6 (_ bv0 256))))",
        "(define-fun fee_base () (_ BitVec 256) (bvadd basefee pi7))",
        "(define-fun fee_amount () (_ BitVec 256) (bvmul pi6 fee_base))",
        f"(assert (=> fee_branch {_bv_sum_no_overflow('basefee', 'pi7')}))",
        f"(assert (=> fee_branch {_bv_product_no_overflow('pi6', 'fee_base')}))",
        "(assert (=> fee_branch (bvule fee_amount pi8)))",
        "(assert (=> fee_branch (bvule fee_amount pi2)))",
        "; explicit mint occurrences, independently of policy",
    ])
    mint_names = []
    for occurrence in summary["mint_occurrences"]:
        name = occurrence["id"]
        mint_names.append(name)
        lines.extend([
            f"; EFFECT mint {name} role={occurrence['role']} callsite={occurrence['callsite']} ordinal={occurrence['ordinal']}",
            f"(define-fun {name}_present () Bool {_summary_expr(occurrence['present'])})",
            f"(define-fun {name}_amount () (_ BitVec 256) {_summary_expr(occurrence['amount'])})",
            f"(define-fun {name}_beneficiary () (_ BitVec 256) {_summary_expr(occurrence['beneficiary'])})",
            f"(assert (=> {name}_present (not (= {name}_beneficiary {_bv(0)}))))",
        ])
    total_terms = [f"(ite {name}_present {name}_amount {_bv(0)})" for name in mint_names]
    lines.extend([
        f"(define-fun impl_total_supply_delta () (_ BitVec 256) {_bv_add(total_terms)})",
        f"(assert (bvule impl_total_supply_delta {_bv(UINT256 - 1 - total_supply)}))",
        "; explicit balance changes generated from implementation mint semantics",
    ])
    balance_names = []
    for effect in summary["other_balance_changes"]:
        name = effect["id"]
        balance_names.append(name)
        lines.extend([
            f"; EFFECT balance {name} source={effect['source_occurrence']}",
            f"(define-fun {name}_present () Bool {_summary_expr(effect['present'])})",
            f"(define-fun {name}_amount () (_ BitVec 256) {_summary_expr(effect['amount'])})",
            f"(define-fun {name}_beneficiary () (_ BitVec 256) {_summary_expr(effect['beneficiary'])})",
        ])
    lines.append("; explicit committed nullifier-write slots")
    write_names = []
    for write in summary["nullifier_writes"]:
        name = write["id"]
        write_names.append(name)
        lines.extend([
            f"; EFFECT nullifier_write {name} ordinal={write['ordinal']}",
            f"(define-fun {name}_present () Bool {_summary_expr(write['present'])})",
            f"(define-fun {name}_key () (_ BitVec 256) {_summary_expr(write['key'])})",
        ])
    control = omega.get("diagnostic_control")
    if control:
        lines.append(f"; CONTROL_SCENARIO {control['id']} implementation-only mutation")
        if control["id"] in {"C1", "C2"}:
            lines.extend(["(assert fee_branch)", f"(assert (bvugt fee_amount {_bv(0)}))"])
        if control["id"] == "C2":
            lines.append("(assert (not (= pi9 pi10)))")
    lines.append("; IMPLEMENTATION_SUMMARY MANUAL_ASSUMED end")
    return {
        "summary": summary, "mint_names": mint_names,
        "balance_names": balance_names, "write_names": write_names,
    }


def _emit_policy(lines: list[str], omega: dict[str, Any], effects: dict[str, Any]) -> None:
    """Evaluate unchanged G1--G5 over the already-emitted effect representation."""
    summary = effects["summary"]
    mint_names = effects["mint_names"]
    writes = effects["write_names"]
    present_amounts = [f"(ite {name}_present {name}_amount {_bv(0)})" for name in mint_names]
    fee_names = [item["id"] for item in summary["mint_occurrences"] if item["role"] == "FEE"]
    fee_amounts = [f"(ite {name}_present {name}_amount {_bv(0)})" for name in fee_names]
    beneficiary_violations = []
    for item in summary["mint_occurrences"]:
        expected = "pi9" if item["role"] == "FEE" else "pi10"
        beneficiary_violations.append(
            f"(and {item['id']}_present (not (= {item['id']}_beneficiary {expected})))"
        )
    multiplicity = []
    for role in ("FEE", "RECIPIENT"):
        names = [item["id"] for item in summary["mint_occurrences"] if item["role"] == role]
        multiplicity.extend(
            f"(and {names[left]}_present {names[right]}_present)"
            for left in range(len(names)) for right in range(left + 1, len(names))
        )
    balance_crosschecks = []
    for balance in summary["other_balance_changes"]:
        source = balance["source_occurrence"]
        balance_crosschecks.extend([
            f"(= {balance['id']}_present {source}_present)",
            f"(=> {balance['id']}_present (= {balance['id']}_amount {source}_amount))",
            f"(=> {balance['id']}_present (= {balance['id']}_beneficiary {source}_beneficiary))",
        ])
    exactly_one_write_terms = []
    for selected in writes:
        exactly_one_write_terms.append(_bool_and(
            [f"{name}_present" if name == selected else f"(not {name}_present)" for name in writes]
        ))
    wrong_keys = [f"(and {name}_present (not (= {name}_key pi0)))" for name in writes]
    lines.extend([
        "; POLICY_EVALUATION begin; no effects are created below this line",
        f"(define-fun policy_total_minted () (_ BitVec 256) {_bv_add(present_amounts)})",
        f"(define-fun policy_fee_total () (_ BitVec 256) {_bv_add(fee_amounts)})",
        f"(define-fun policy_balance_crosscheck () Bool {_bool_and(balance_crosschecks)})",
        "(define-fun policy_supply_crosscheck () Bool (= impl_total_supply_delta policy_total_minted))",
        f"(define-fun policy_exactly_one_nullifier_write () Bool {_bool_or(exactly_one_write_terms)})",
        "(define-fun G1 () Bool (not (= policy_total_minted pi2)))",
        "(define-fun G2 () Bool (bvugt policy_fee_total pi8))",
        f"(define-fun G3 () Bool {_bool_or(beneficiary_violations)})",
        f"(define-fun G4 () Bool {_bool_or(multiplicity + ['(not policy_balance_crosscheck)', '(not policy_supply_crosscheck)'])})",
        f"(define-fun G5 () Bool {_bool_or(['(not policy_exactly_one_nullifier_write)', *wrong_keys])})",
        f"(define-fun NONVAC () Bool {_bool_or([f'{name}_present' for name in mint_names + writes])})",
        "; POLICY_EVALUATION end",
    ])
    if omega["goal"]["name"] == "AUTH-1":
        lines.append("(assert (or G1 G2 G3 G4 G5))")
    else:
        lines.append("(assert NONVAC)")


def balanced_smt_parentheses(data: bytes) -> dict[str, Any]:
    """Check SMT parentheses while ignoring semicolon comments and strings."""
    text = data.decode("utf-8")
    depth = 0
    line = 1
    column = 0
    in_comment = False
    in_string = False
    escaped = False
    for char in text:
        column += 1
        if char == "\n":
            line += 1; column = 0; in_comment = False
            continue
        if in_comment:
            continue
        if in_string:
            if char == '"' and not escaped:
                in_string = False
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
            continue
        if char == ";":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return {"balanced": False, "depth": depth, "line": line, "column": column,
                        "reason": "unexpected closing parenthesis"}
    return {"balanced": depth == 0 and not in_string, "depth": depth, "line": line,
            "column": column, "reason": None if depth == 0 and not in_string else "unclosed parenthesis or string"}


def encode_query(omega: dict[str, Any], *, drop_producer: bool = False) -> tuple[bytes, dict[str, Any]]:
    """Encode one of the three frozen queries and return bytes plus certificate."""
    goal = omega["goal"]["name"]
    if drop_producer and goal != "AUTH-1":
        raise ValueError("only AUTH-1 Q1 may drop R_v")
    circuit = omega["producer_relation_R_hat"]["functions"][0]
    opcodes = circuit["opcodes"]
    counts = Counter(opcode["kind"] for opcode in opcodes)
    lines = [
        "; D1P-14C checked transformation of canonical Omega",
        f"; omega_sha256={canonical_sha256(omega)}",
        f"; goal={goal}", f"; producer_relation={'DROPPED_Q1' if drop_producer else 'FULL'}",
        "(set-logic ALL)", "(set-option :produce-models true)",
        f"(define-sort F () (_ FiniteField {FIELD_MODULUS}))",
    ]
    emitted = Counter()
    referenced: set[int] = set(range(11))
    if not drop_producer:
        for opcode in opcodes:
            referenced.update(_input_witnesses(opcode))
        for witness in sorted(referenced):
            lines.append(f"(declare-const w{witness} F)")
    for index in range(11):
        lines.append(f"(declare-const pi{index} (_ BitVec 256))")
    lines.extend([
        "(declare-const basefee (_ BitVec 256))",
        f"(define-fun msg_sender () (_ BitVec 256) {_bv(omega['environment']['msg_sender_value'])})",
    ])

    # D_v: canonical public inputs, address widths, and identity bridge to w0..w10.
    for index in range(11):
        lines.append(f"; DV_WORD {index} {PUBLIC_INPUTS[index]}")
        lines.append(f"(assert (bvult pi{index} {_bv(FIELD_MODULUS)}))")
        if not drop_producer:
            lines.append(f"(assert (= w{index} {_field_from_bv(254, f'pi{index}')}))")
    for index in (9, 10):
        lines.append(f"(assert (bvult pi{index} {_bv(ADDRESS_LIMIT)}))")

    # Full R_hat, with the section 6.4 L0 hash layer.
    if not drop_producer:
        for opcode in opcodes:
            index = opcode["opcode_index"]
            kind = opcode["kind"]
            if kind == "AssertZero":
                lines.append(f"; ACIR AssertZero {index}")
                lines.append(f"(assert (= {_expression(opcode['expression'])} {_ff(0)}))")
            elif kind == "RANGE":
                lines.append(f"; ACIR RANGE {index}")
                inp = opcode["input"]
                bits = opcode["num_bits"]
                if "constant" in inp:
                    ok = inp["constant"] < (1 << bits)
                    lines.append(f"(assert {'true' if ok else 'false'})")
                else:
                    range_name = f"range_{index}"
                    lines.append(f"(declare-const {range_name} (_ BitVec {bits}))")
                    lines.append(f"(assert (= w{inp['witness']} {_field_from_bv(bits, range_name)}))")
            elif kind == "Poseidon2Permutation":
                lines.append(f"; ACIR Poseidon2Permutation {index} HAVOC_OUTPUTS " +
                             ",".join(str(item) for item in opcode["outputs"]))
            elif kind == "BrilligCall":
                lines.append(f"; ACIR BrilligCall {index} WITNESS_GENERATION_ONLY")
            else:
                raise ValueError(f"fail closed: unsupported opcode {kind} at {index}")
            emitted[kind] += 1

    effects = _emit_consumer_transition(lines, omega)
    _emit_policy(lines, omega, effects)
    lines.append("(check-sat)")
    data = ("\n".join(lines) + "\n").encode("utf-8")
    parens = balanced_smt_parentheses(data)
    if not parens["balanced"]:
        raise ValueError(f"unbalanced generated SMT: {parens}")
    certificate = {
        "schema": "bindcheck.d1p14c.transformation/v1",
        "omega_sha256": canonical_sha256(omega), "goal": goal,
        "producer_relation": "dropped by Q1 definition" if drop_producer else "full",
        "decoded_opcode_counts": dict(sorted(counts.items())),
        "emitted_opcode_counts": dict(sorted(emitted.items())),
        "omitted_opcode_counts": dict(sorted(counts.items())) if drop_producer else {},
        "hash_layer": omega["hash_layer"],
        "public_bridge_count": 0 if drop_producer else 11,
        "canonicality_guard_count": 11, "address_width_guard_count": 2,
        "consumer_lowering": "all T_mint success guards and committed occurrences in Omega",
        "consumer_summary_classification": "MANUAL / ASSUMED",
        "implementation_variant": omega["consumer_T_mint"]["transition_and_effects"]["variant"],
        "policy_scope": omega["auth_scope_choice"],
        "diagnostic_control": omega.get("diagnostic_control"),
        "balanced_parentheses": parens,
        "sender_substitution": {
            "value": omega["environment"]["msg_sender_value"],
            "justification": "Under low160(w9)!=1, msg.sender is not read by T_mint; replacing any nonzero sender with the ordinary local relayer preserves every guard and effect occurrence.",
        },
        "query_sha256": hashlib.sha256(data).hexdigest(), "query_bytes": len(data),
    }
    audit_transformation(omega, data, certificate, drop_producer=drop_producer)
    return data, certificate


def audit_transformation(
    omega: dict[str, Any], query: bytes, certificate: dict[str, Any], *, drop_producer: bool,
) -> None:
    text = query.decode("utf-8")
    if f"omega_sha256={canonical_sha256(omega)}" not in text:
        raise ValueError("query is not bound to Omega")
    if hashlib.sha256(query).hexdigest() != certificate["query_sha256"]:
        raise ValueError("query hash mismatch")
    circuit = omega["producer_relation_R_hat"]["functions"][0]
    expected = Counter(opcode["kind"] for opcode in circuit["opcodes"])
    observed = Counter()
    for kind in expected:
        observed[kind] = text.count(f"; ACIR {kind} ")
    if drop_producer:
        if any(observed.values()) or certificate["omitted_opcode_counts"] != dict(sorted(expected.items())):
            raise ValueError("Q1 producer-drop certificate mismatch")
    elif observed != expected or certificate["emitted_opcode_counts"] != dict(sorted(expected.items())):
        raise ValueError(f"opcode transformation mismatch: {observed} != {expected}")
    if text.count("; DV_WORD ") != 11:
        raise ValueError("D_v word coverage mismatch")
    if not balanced_smt_parentheses(query)["balanced"]:
        raise ValueError("query parentheses are not balanced")
    for marker in ("; IMPLEMENTATION_SUMMARY", "; POLICY_EVALUATION", "(define-fun G1", "(define-fun G5", "(check-sat)"):
        if marker not in text:
            raise ValueError(f"missing query marker {marker}")
    if "collision" in text.lower() or "injective" in text.lower():
        raise ValueError("forbidden hash axiom text in solver input")

