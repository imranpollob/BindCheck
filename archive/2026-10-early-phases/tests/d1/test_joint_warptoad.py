import copy
import hashlib
import json
from pathlib import Path
import subprocess

from bindcheck_d1.joint_warptoad import (
    CHAIN_ID,
    FIELD_MODULUS,
    audit_transformation,
    balanced_smt_parentheses,
    build_omega,
    build_consumer_transition,
    canonical_bytes,
    encode_query,
    evaluate_effect_policy,
    lower_mint,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
RELAYER = int("70997970c51812dc3a010c7d01b50e0d17dc79c8", 16)
RECIPIENT = int("90f79bf6eb2c4f870365e785982e1f101e93b906", 16)
GIGA = int("2b94cf5e8746b3f5c9631f4c5df32907a699c58c94b2ad4d7b5cec1639183f55", 16)
LOCAL = int("2d252a5fea4ed67e85d8e446324eb9d0153e997a7b75e04c95e5d6b48ac099f5", 16)


def state():
    return {
        "giga_roots": {GIGA}, "local_roots": {LOCAL}, "nullifiers": set(),
        "total_supply": 5_000_000_000_000_000_000,
        "balances": {RELAYER: 0, RECIPIENT: 0},
    }


def words(*, fee_factor=974_405_002, max_fee=5_000_000_000_000_000_000):
    return [
        123, CHAIN_ID, 5_000_000_000_000_000_000, GIGA, LOCAL, 0,
        fee_factor, 100_000_000, max_fee, RELAYER, RECIPIENT,
    ]


def omega(goal="AUTH-1", implementation_variant="BASE", control_id=None):
    s0 = {
        "giga_root_history": [str(GIGA)], "local_root_history": [str(LOCAL)],
        "nullifiers": [], "total_supply": "5000000000000000000",
    }
    identities = {"openzeppelin": {"version": "5.6.1", "status": "EXTRACTED"}}
    return build_omega(
        ARTIFACT, goal=goal, s0=s0, identities=identities,
        implementation_variant=implementation_variant, control_id=control_id,
    )


def test_concrete_nonzero_fee_occurrences_and_policy():
    result = lower_mint(words(), basefee=100_000_000, state=state(), msg_sender=RELAYER)
    assert result["success"]
    assert [o["role"] for o in result["occurrences"]] == ["FEE", "RECIPIENT"]
    assert result["aggregates"]["fee_amount"] == 194_881_000_400_000_000
    assert result["aggregates"]["recipient_amount"] == 4_805_118_999_600_000_000
    assert result["aggregates"]["total_minted"] == 5_000_000_000_000_000_000
    assert not result["auth_violation"] and result["nonvac"]


def test_fee_cap_revert_rolls_back_and_replay_rejects():
    pre = state()
    capped = lower_mint(
        words(max_fee=1_000_000_000_000_000_000), basefee=2_000_000_000,
        state=pre, msg_sender=RELAYER,
    )
    assert not capped["success"]
    assert capped["revert_location"] == "WarpToadCore.sol:166"
    assert capped["occurrences"] == [] and capped["state"] == pre
    replay_state = state()
    replay_state["nullifiers"].add(123)
    replay = lower_mint(words(), basefee=100_000_000, state=replay_state)
    assert not replay["success"]
    assert replay["revert_location"] == "WarpToadCore.sol:157"


def test_zero_fee_has_one_recipient_occurrence_and_no_fee_occurrence():
    result = lower_mint(words(fee_factor=0), basefee=100_000_000, state=state())
    assert result["success"]
    assert [(o["role"], o["amount"]) for o in result["occurrences"]] == [
        ("RECIPIENT", 5_000_000_000_000_000_000),
    ]
    assert result["aggregates"]["fee_amount"] == 0


def test_equal_beneficiaries_still_have_two_occurrences():
    candidate = words()
    candidate[10] = RELAYER
    result = lower_mint(candidate, basefee=100_000_000, state=state())
    assert result["success"] and len(result["occurrences"]) == 2
    assert len(result["aggregates"]["balance_deltas"]) == 1
    assert result["aggregates"]["crosscheck"]


def test_transition_is_built_before_and_without_policy():
    transition = build_consumer_transition(words(), basefee=100_000_000, state=state())
    assert "goals" not in transition and "auth_violation" not in transition
    assert transition["occurrences"] and transition["nullifier_writes"]
    policy = evaluate_effect_policy(transition, words())
    assert policy["goals"] == {"G1": False, "G2": False, "G3": False, "G4": False, "G5": False}
    assert not policy["auth_violation"] and policy["nonvac"]


def test_implementation_only_sensitivity_controls_hit_expected_goals():
    expected = {
        "C1_FULL_RECIPIENT_PLUS_FEE": "G1",
        "C2_FEE_TO_RECIPIENT": "G3",
        "C3_EXTRA_MINT": "G4",
        "C4_WRONG_NULLIFIER_WRITE": "G5",
    }
    for variant, goal in expected.items():
        result = lower_mint(
            words(), basefee=100_000_000, state=state(),
            implementation_variant=variant,
        )
        assert result["success"] and result["auth_violation"]
        assert result["goals"][goal], (variant, result["goals"])
    c3 = lower_mint(words(), basefee=100_000_000, state=state(), implementation_variant="C3_EXTRA_MINT")
    assert len([item for item in c3["occurrences"] if item["role"] == "RECIPIENT"]) == 2
    c4 = lower_mint(words(), basefee=100_000_000, state=state(), implementation_variant="C4_WRONG_NULLIFIER_WRITE")
    assert len(c4["nullifier_writes"]) == 2
    assert c4["nullifier_writes"][1]["key"] != words()[0]


def test_canonical_omega_and_checked_query_transformations():
    auth = omega()
    assert canonical_bytes(auth) == canonical_bytes(json.loads(canonical_bytes(auth)))
    q1, c1 = encode_query(auth, drop_producer=True)
    audit_transformation(auth, q1, c1, drop_producer=True)
    assert c1["omitted_opcode_counts"] == {
        "AssertZero": 24860, "BrilligCall": 20,
        "Poseidon2Permutation": 86, "RANGE": 107,
    }
    q2, c2 = encode_query(auth)
    audit_transformation(auth, q2, c2, drop_producer=False)
    assert c2["emitted_opcode_counts"] == c1["omitted_opcode_counts"]
    assert q2.count(b"; ACIR Poseidon2Permutation ") == 86
    assert b"collision" not in q2.lower() and b"injective" not in q2.lower()
    nonvac = omega("NONVAC-1")
    q3, c3 = encode_query(nonvac)
    audit_transformation(nonvac, q3, c3, drop_producer=False)
    assert hashlib.sha256(q3).hexdigest() == c3["query_sha256"]
    assert q2 != q3


def test_public_boundary_is_strictly_canonical():
    auth = omega()
    query, _ = encode_query(auth, drop_producer=True)
    assert query.count(f"(assert (bvult pi".encode()) >= 11
    assert str(FIELD_MODULUS).encode() in query


def test_all_d1p14c_emitted_smt_is_balanced_and_cvc5_parseable():
    solver = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
    assert solver.exists()
    cases = [
        ("C1", omega(implementation_variant="C1_FULL_RECIPIENT_PLUS_FEE", control_id="C1"), True),
        ("C2", omega(implementation_variant="C2_FEE_TO_RECIPIENT", control_id="C2"), True),
        ("C3", omega(implementation_variant="C3_EXTRA_MINT", control_id="C3"), True),
        ("C4", omega(implementation_variant="C4_WRONG_NULLIFIER_WRITE", control_id="C4"), True),
        ("Q1", omega(), True), ("Q2", omega(), False),
        ("Q3", omega("NONVAC-1"), False),
    ]
    policies = {canonical_bytes(value[1]["policy"]) for value in cases}
    assert len(policies) == 1, "controls must not mutate policy"
    for name, value, dropped in cases:
        query, _certificate = encode_query(value, drop_producer=dropped)
        assert balanced_smt_parentheses(query)["balanced"], name
        parsed = subprocess.run(
            [str(solver), "--lang=smt2", "--parse-only"], input=query,
            capture_output=True, timeout=60,
        )
        assert parsed.returncode == 0, (name, parsed.stdout.decode(), parsed.stderr.decode())

