import json
from pathlib import Path

from bindcheck_d1.warptoad_poseidon_provenance import DOMAINS, IV, trace_withdraw_poseidon2


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"


def test_pinned_beta22_poseidon2_call_sites_are_fully_classified():
    result = trace_withdraw_poseidon2(ARTIFACT)
    assert result["count_resolution"]["equation"] == "2 + (42 * 2) = 86"
    assert result["counts"] == {"merkle_node": 84, "siloed_note": 1, "unique_note": 1}
    assert result["orientation_counts"] == {"node_left": 42, "node_right": 42}
    calls = result["calls"]
    assert len(calls) == 86
    assert [calls[0]["construction"], calls[1]["construction"]] == ["siloed_note", "unique_note"]
    assert calls[0]["input_witnesses"][1] == 5
    assert calls[1]["input_witnesses"][1] == 58
    assert calls[0]["boundary"]["absorption"] == [
        "domain:siloed_note", "contract_address", "note_hash",
    ]
    assert calls[1]["boundary"]["absorption"] == [
        "domain:unique_note", "leaf_nonce", "siloed_note_hash",
    ]
    for level in range(42):
        left, right = calls[2 + 2 * level:4 + 2 * level]
        assert left["merkle_level"] == right["merkle_level"] == level
        assert left["orientation_candidate"] == "node_left"
        assert right["orientation_candidate"] == "node_right"
        assert left["boundary"]["absorption"] == [
            "domain:merkle_node", "current_node", f"sibling[{level}]",
        ]
        assert right["boundary"]["absorption"] == [
            "domain:merkle_node", f"sibling[{level}]", "current_node",
        ]
        assert 16 + level in left["input_witnesses"][1:3]
        assert 16 + level in right["input_witnesses"][1:3]
    assert {call["boundary"]["domain_separator"] for call in calls} == set(DOMAINS.values())
    assert all(call["boundary"]["initial_state"] == [0, 0, 0, IV] for call in calls)
    assert all(call["boundary"]["permutation_count"] == 1 for call in calls)
    assert all(call["boundary"]["output_selection"] == "lane_0" for call in calls)


def test_frozen_d1p15_provenance_if_present_matches_recomputation():
    frozen = ROOT / "results/raw/D1P-15/poseidon2-provenance.json"
    if frozen.exists():
        assert json.loads(frozen.read_text()) == trace_withdraw_poseidon2(ARTIFACT)
