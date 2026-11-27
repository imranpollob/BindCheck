import hashlib
import json
from pathlib import Path
import subprocess

from bindcheck_d1.joint_warptoad import canonical_bytes
from bindcheck_d1.joint_warptoad_d1p14d import (
    CONTROL_VARIANTS,
    audit_concrete_control,
    encode_concrete_control,
    expected_effect_records,
    freeze_honest_fixture,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
PROOF = ROOT / "results/raw/D1P-14A/fc-pos-proof.json"
RECEIPT = ROOT / "results/raw/D1P-14A/fc-pos-receipt.json"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
C_MANIFEST = ROOT / "metadata/d1/d1p-14c-artifact-manifest.json"


def fixture():
    return freeze_honest_fixture(json.loads(PROOF.read_text()), json.loads(RECEIPT.read_text()))


def identities():
    return {"openzeppelin": {"version": "5.6.1", "status": "EXTRACTED identity; MANUAL / ASSUMED behavior"}}


def test_fixed_fixture_has_required_arithmetic_and_distinct_named_beneficiaries():
    value = fixture()
    assert value["all_checks_pass"]
    assert value["derived_arithmetic"] == {
        "fee_base": "200000000",
        "fee": "194881000400000000",
        "recipient_remainder": "4805118999600000000",
    }
    assert value["public_inputs"]["relayer_address"] != value["public_inputs"]["recipient_address"]
    assert value["environment"]["msg_sender"] == value["public_inputs"]["relayer_address"]


def test_expected_effects_are_independent_and_have_exact_polarity():
    expected = expected_effect_records(fixture())
    assert expected["all_checks_pass"]
    for control, (_variant, target) in CONTROL_VARIANTS.items():
        record = expected["records"][control]
        assert record["positive"]["goals"][target]
        assert not record["negative"]["goals"][target]
        assert [name for name, result in record["positive"]["goals"].items() if result] == [target]
        assert not any(record["negative"]["goals"].values())


def test_all_eight_queries_fix_inputs_preserve_policy_and_parse():
    value = fixture()
    policy_hashes = set()
    for control in CONTROL_VARIANTS:
        for polarity in ("positive", "negative"):
            query, certificate, omega = encode_concrete_control(
                ARTIFACT, identities=identities(), fixture=value,
                control_id=control, polarity=polarity,
            )
            audit_concrete_control(query, certificate, value)
            policy_hashes.add(hashlib.sha256(canonical_bytes(omega["policy"])).hexdigest())
            parsed = subprocess.run(
                [str(SOLVER), "--lang=smt2", "--parse-only"], input=query,
                capture_output=True, timeout=30,
            )
            assert parsed.returncode == 0, (control, polarity, parsed.stderr.decode())
    assert len(policy_hashes) == 1


def test_d1p14c_primary_query_hashes_are_the_frozen_reference():
    manifest = json.loads(C_MANIFEST.read_text())
    expected = {item["id"]: item["query"]["sha256"] for item in manifest["schedule"] if item["kind"] == "primary"}
    assert expected == {
        "Q1": "a188b4a155b41b92a2531d0ae7c92593baaaf373f64f61068c739c66d2a5fa2b",
        "Q2": "7aa4935a6d3fb5c8cb6b7141bace0c80f9a16745db662ce8220c636f927c7701",
        "Q3": "922df98e7d6fd04fb24628462039199515257aab78c08bc3b6ee02ea617b141d",
    }
    for item in manifest["schedule"]:
        if item["kind"] != "primary":
            continue
        source = ROOT / item["query"]["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected[item["id"]]
