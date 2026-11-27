import json
from pathlib import Path

from bindcheck_d1.warptoad_bn254_regions import extract_bn254_regions
from bindcheck_d1.warptoad_variant_provenance import extract_mdom_poseidon2


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results/raw/D1P-21A"
MDOM = ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json"
MDOM_SHA = "db1a0a17b2717cce2fe9a9a01e114632634fcf43f0f813d062dfa9c660aa7f2f"
PAIRINGS = ("pinned-sdom", "m-dom-sdom", "pinned-ssrc", "m-src-ssrc")


def test_mdom_poseidon_provenance_is_derived_from_its_own_abi_and_calls():
    result = extract_mdom_poseidon2(MDOM, expected_artifact_sha256=MDOM_SHA)
    assert result["counts"] == {"merkle_node": 84, "siloed_note": 1, "unique_note": 1}
    assert result["orientation_counts"] == {"node_left": 42, "node_right": 42}
    assert len(result["calls"]) == 86
    derived = result["abi_witness_layout"]["derived_key_witnesses"]
    assert derived == {"public_contract": 5, "private_contract": 59, "leaf_nonce": 58}
    assert result["calls"][0]["input_witnesses"][1] == 59
    assert result["calls"][0]["input_witnesses"][1] != 5
    assert result["calls"][1]["input_witnesses"][1] == 58
    for level in range(42):
        sibling = 16 + level
        left, right = result["calls"][2 + 2 * level:4 + 2 * level]
        assert sibling in left["input_witnesses"][1:3]
        assert sibling in right["input_witnesses"][1:3]
    assert all(row["l1_application"]["function"] == "P2_WIDTH4_SHARED" for row in result["calls"])


def test_mdom_bn254_regions_are_checked_on_mdom_witnesses():
    result = extract_bn254_regions(
        MDOM,
        expected_artifact_sha256=MDOM_SHA,
        region_id_prefix="M-DOM-BN-",
        variant="M-DOM",
        direct_lines=(46, 47, 48),
        merkle_withdraw_lines=(61, 75),
    )
    assert result["variant"] == "M-DOM"
    assert result["counts"]["regions"] == 77
    assert result["counts"]["core_constraints"] == 24_448
    assert result["regions"][10]["construction"] == "nullifier_hash1"
    assert result["regions"][10]["boundary_input_witnesses"] == [13]
    assert all(row["functionality_check"].startswith("PASS") for row in result["regions"])
    assert all(row["locality_check"].startswith("PASS") for row in result["regions"])


def test_frozen_mdom_provenance_matches_recomputation_if_present():
    poseidon_path = RAW / "m-dom-poseidon2-provenance.json"
    bn_path = RAW / "m-dom-bn254-region-extraction.json"
    if poseidon_path.exists():
        assert json.loads(poseidon_path.read_text()) == extract_mdom_poseidon2(
            MDOM, expected_artifact_sha256=MDOM_SHA,
        )
    if bn_path.exists():
        assert json.loads(bn_path.read_text()) == extract_bn254_regions(
            MDOM,
            expected_artifact_sha256=MDOM_SHA,
            region_id_prefix="M-DOM-BN-",
            variant="M-DOM",
            direct_lines=(46, 47, 48),
            merkle_withdraw_lines=(61, 75),
        )


def test_exact_state_controls_and_attempt_budget_if_present():
    ledger_path = RAW / "proof-attempt-ledger.json"
    if not ledger_path.exists():
        return
    ledger = json.loads(ledger_path.read_text())
    assert ledger["pairingInvocationsUsed"] == 4
    assert ledger["retries"] == 0
    assert ledger["parameterSearch"] is False
    assert [row["pairing"] for row in ledger["attempts"]] == list(PAIRINGS)
    for pairing in PAIRINGS:
        result = json.loads((RAW / "controls" / f"{pairing}.json").read_text())
        assert result["status"] == "PASS"
        assert len(result["proofGenerationAttempts"]) == 1
        assert result["execution"]["verifierAccepted"] is True
        assert result["execution"]["effects"] == {
            "nullifierWritten": True,
            "recipientDelta": "5000000000000000000",
            "relayerDelta": "0",
            "totalSupplyDelta": "5000000000000000000",
        }
        assert result["execution"]["fee"]["feeFactor"] == "0"


def test_d1p21a_runner_has_no_solver_campaign_entrypoint():
    source = (ROOT / "scripts/d1p_21a_campaign_gates.py").read_text()
    assert 'sub.add_parser("setup")' in source
    assert 'sub.add_parser("proof")' in source
    assert 'sub.add_parser("solve")' not in source
    assert "runner refuses solver commands" in source
