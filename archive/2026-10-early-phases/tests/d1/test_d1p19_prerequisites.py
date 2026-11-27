import json
from pathlib import Path

from bindcheck_d1.warptoad_bn254_regions import extract_bn254_regions
from bindcheck_d1.warptoad_p6 import audit_p6


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"


def test_all_bn254_regions_are_local_and_functional():
    result = extract_bn254_regions(ARTIFACT)
    assert result["counts"]["regions"] == 77
    assert result["counts"]["construction_counts"] == {
        "commitment_hash2": 1,
        "evm_merkle_hash2": 64,
        "giga_merkle_hash2": 10,
        "nullifier_hash1": 1,
        "precommitment_hash3": 1,
    }
    assert result["counts"]["core_size_distribution"] == {"317": 75, "329": 1, "344": 1}
    assert result["counts"]["shared_input_prelude_constraints"] == 70
    assert result["counts"]["materialized_output_links"] == 76
    assert result["counts"]["fused_virtual_output_boundaries"] == 1
    assert all(row["functionality_check"].startswith("PASS") for row in result["regions"])
    assert all(row["locality_check"].startswith("PASS") for row in result["regions"])


def test_frozen_d1p19_region_extraction_if_present():
    frozen = ROOT / "results/raw/D1P-19/bn254-region-extraction.json"
    if frozen.exists():
        assert json.loads(frozen.read_text()) == extract_bn254_regions(ARTIFACT)


def test_p6_function_identity_terms_and_domains():
    result = audit_p6(ROOT)
    assert result["overall"] == "PASS"
    assert result["termCoverage"]["programPoseidon2Count"] == 86
    assert result["termCoverage"]["programBn254RegionCount"] == 77
    assert result["termCoverage"]["admittedStateGroundTermCount"] == 229
    assert result["termCoverage"]["sSrcIncludesBurnLeavesAndLazyImtNodes"]
    assert result["functionIdentity"]["status"] == "PASS"
    assert result["canonicalDomains"]["status"] == "PASS"
    assert result["canonicalDomains"]["solidityPoseidonT3NoncanonicalBehavior"] == (
        "reduces modulo P; does not reject"
    )


def test_frozen_d1p19_p6_audit_if_present():
    frozen = ROOT / "results/raw/D1P-19/p6-audit.json"
    if frozen.exists():
        assert json.loads(frozen.read_text()) == audit_p6(ROOT)
