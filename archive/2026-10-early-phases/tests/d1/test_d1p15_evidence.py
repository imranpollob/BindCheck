import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results/raw/D1P-15"


def load(name: str):
    return json.loads((RAW / name).read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hash_reference_evidence_covers_both_honest_inputs_and_all_calls():
    evidence = load("hash-reference-check.json")
    assert evidence["allPassed"] is True
    assert len(evidence["fixtures"]) == 2
    assert sum(item["poseidon2"]["checkedOpcodes"] for item in evidence["fixtures"]) == 172
    assert all(item["poseidon2"]["passed"] for item in evidence["fixtures"])
    assert all(item["bn254"]["evmTreeMatchesOriginRoot"] for item in evidence["fixtures"])


def test_injected_mutation_has_own_key_and_passes_the_three_required_gates():
    setup = load("setup-identities.json")
    execution = load("o1-execution.json")
    identities = setup["artifact_identity"]
    assert identities["own_key_identity"] is True
    assert identities["mutation_vk"]["sha256"] != identities["pinned_vk"]["sha256"]
    assert identities["mutation_vk"]["sha256"] == sha256(RAW / "artifacts/m-dom-vk.bin")
    assert execution["injected"] is True
    assert execution["gates"]["honestMutationMint"] is True
    assert execution["gates"]["foreignMutationVExec"] is True
    assert execution["gates"]["foreignPinnedRejects"] is True
    assert execution["configuredWarpToadAddress"] != execution["foreignContractAddress"]


def test_both_real_proofs_reach_the_generated_verifier_and_actual_mint():
    execution = load("o1-execution.json")
    ledger = load("proof-attempt-ledger.json")
    assert len(ledger["attempts"]) == ledger["limit"] == 2
    assert ledger["parameter_search"] is False
    for case_name in ("honest", "foreign"):
        proof = load(f"{case_name}-proof.json")
        case = execution["cases"][case_name]
        assert proof["proofBytes"] == 9152
        assert len(proof["publicInputs"]) == 11
        assert proof["jsVerified"] and proof["generatedVerifierAccepted"]
        assert case["mutationExecution"] == {
            "witnessSolved": True,
            "jsVerified": True,
            "verifierAccepted": True,
        }
        assert case["mint"]["effects"] == {
            "nullifierWritten": True,
            "recipientDelta": "5000000000000000000",
            "relayerDelta": "0",
            "totalSupplyDelta": "5000000000000000000",
        }
        assert case["rootAdmission"]["privilegedInitialization"] is True
        assert case["rootAdmission"]["noCrossChainReachabilityClaim"] is True
    assert execution["cases"]["honest"]["pinnedExecution"]["outcome"] == "accepted"
    assert execution["cases"]["foreign"]["pinnedExecution"]["outcome"] == "rejected"


def test_d1p15_command_ledger_contains_no_solver_invocation():
    solver_names = ("cvc5", "z3", "yices", "boolector")
    records = [json.loads(path.read_text()) for path in (RAW / "command-records").glob("*.json")]
    assert records
    assert not [
        record["label"] for record in records
        if any(any(name in arg.lower() for name in solver_names) for arg in record["argv"])
    ]
    failures = [record["label"] for record in records if record["exit_code"] != 0]
    assert failures == ["o1-injected-vexec-preflight-import-failure"]
    assert load("audit.json")["claim_limits"]["security_verdict"] == "UNKNOWN"
