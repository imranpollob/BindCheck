from __future__ import annotations

import json
from pathlib import Path
import unittest

from bindcheck_d1.composition_baselines_v1 import (
    BASELINE_NAMES,
    CompositionInputError,
    POLICY_SCHEMA,
    audit_existing_union,
    compose,
)


ROOT = Path(__file__).resolve().parents[1]


def policy(*, amount_index: int = 0, renamed: bool = False) -> dict:
    active_surface = "used_count" if renamed else "active_count"
    return {
        "schema": POLICY_SCHEMA,
        "policy_id": "test-policy",
        "version": "1",
        "comparison_group": "logical-test-case",
        "word_identities": {
            str(amount_index): "amount",
            str(1 if amount_index == 0 else 0): "domain",
        },
        "term_aliases": {
            active_surface: "active_extent",
            "configured_length": "configured_extent",
        },
        "obligations": [
            {
                "id": "O-AMOUNT",
                "word_ids": ["amount"],
                "checks": [
                    "producer_binding",
                    "consumer_dataflow",
                    "extent_coverage",
                    "role_correspondence",
                ],
            }
        ],
    }


def integrated_record(*, amount_index: int = 0, renamed: bool = False, clean: bool = False) -> dict:
    domain_index = 1 if amount_index == 0 else 0
    active_surface = "used_count" if renamed else "active_count"
    amount_occurrences = 2 if clean else 0
    domain_used = True if clean else False
    boundary = "match" if clean else "mismatch"
    warnings = [] if clean else [
        {
            "id": "W001",
            "rule": "R-BIND",
            "location": "Producer.nr:1",
            "evidence": {
                "public_indices": [amount_index],
                "occurrence_counts": [0],
                "witnesses": [amount_index],
            },
            "target_identity": {"rule": "R-BIND"},
        },
        {
            "id": "W002",
            "rule": "R-CONSUMER",
            "location": "Consumer.sol:2",
            "evidence": {"public_indices": [domain_index]},
            "target_identity": {"rule": "R-CONSUMER"},
        },
    ]
    integrated_warnings = [
        {**warning, "source_id": warning["id"], "stable_id": f"BC-{warning['id']}"}
        for warning in warnings
    ]
    return {
        "schema": "bindcheck.integrated-analysis.v1",
        "target": "surface-variant" if renamed or amount_index else "original",
        "support_status": "SUPPORTED",
        "components": {
            "static": {"status": "SUPPORTED"},
            "role_binding": {"status": "SUPPORTED"},
        },
        "inputs": {
            "producer_artifact": {
                "sha256": "b" * 64 if renamed or amount_index else "a" * 64
            },
            "consumer_source": {
                "sha256": "d" * 64 if renamed or amount_index else "c" * 64
            },
        },
        "static_analysis": {
            "producer": {
                "public_leaves": [
                    {
                        "public_index": amount_index,
                        "path": "renamed_amount" if renamed else "amount",
                        "occurrence_count": amount_occurrences,
                        "binding_condition": {
                            "kind": "always" if clean else "never"
                        },
                    },
                    {
                        "public_index": domain_index,
                        "path": "domain",
                        "occurrence_count": 1,
                        "binding_condition": {"kind": "always"},
                    },
                ]
            },
            "consumer": {
                "public_words": [
                    {
                        "index": amount_index,
                        "origin": "renamedAmount" if renamed else "amount",
                        "consumer_used": True,
                    },
                    {
                        "index": domain_index,
                        "origin": "domain",
                        "consumer_used": domain_used,
                    },
                ],
                "effect_word_indices": [amount_index],
            },
            "extent_facts": {
                "coverage": [
                    {
                        "public_index": amount_index,
                        "path": "payload[0]",
                        "status": "EXACT",
                        "covered": clean,
                        "producer_condition": (
                            "true" if clean else f"word_offset < {active_surface}"
                        ),
                        "consumer_condition": "word_offset < configured_length",
                        "uncovered_region": (
                            None
                            if clean
                            else f"{active_surface} <= word_offset < configured_length"
                        ),
                    }
                ]
            },
            "warnings": warnings,
        },
        "role_binding": {
            "status": "SUPPORTED",
            "words": [
                {
                    "public_index": amount_index,
                    "boundary_correspondence": boundary,
                    "producer": {
                        "boundary_role": "value:amount" if clean else "unknown",
                        "identity": [],
                    },
                    "consumer": {
                        "boundary_role": "value:amount",
                        "identity": [],
                        "effects": [{"role": "principal-amount"}],
                        "state_checks": [],
                    },
                },
                {
                    "public_index": domain_index,
                    "boundary_correspondence": "match",
                    "producer": {"boundary_role": "domain:chain", "identity": ["chain"]},
                    "consumer": {
                        "boundary_role": "domain:chain",
                        "identity": ["chain"],
                        "effects": [],
                        "state_checks": [],
                    },
                },
            ],
        },
        "warnings": integrated_warnings,
        "outcome": {
            "verdict": "UNKNOWN",
            "evidence_grade": "E1" if warnings else "E0",
        },
    }


class CompositionBaselineTests(unittest.TestCase):
    def test_all_required_arms_are_runnable_and_unscored(self) -> None:
        result = compose(integrated_record(), policy())
        self.assertEqual(tuple(result["baselines"]), BASELINE_NAMES)
        self.assertEqual(result["research_verdict"], "UNKNOWN")
        self.assertEqual(result["status"], "CONSTRUCTION_SMOKE_TEST")
        self.assertEqual(len(result["baselines"]["producer-only"]["candidates"]), 1)
        self.assertEqual(len(result["baselines"]["consumer-only"]["candidates"]), 1)
        self.assertEqual(len(result["baselines"]["unjoined-union"]["candidates"]), 2)
        self.assertGreaterEqual(
            len(result["baselines"]["strong-simple-composition"]["candidates"]),
            len(result["baselines"]["basic-structural-composition"]["candidates"]),
        )
        self.assertFalse(
            result["baselines"]["full-bindcheck"]["information_budget"]
            ["policy_consumed_by_current_analyzer"]
        )

    def test_clean_direct_obligation_produces_no_composition_candidate(self) -> None:
        result = compose(integrated_record(clean=True), policy())
        self.assertEqual(
            result["baselines"]["basic-structural-composition"]["candidates"], []
        )
        strong = result["baselines"]["strong-simple-composition"]
        self.assertEqual(strong["candidates"], [])
        self.assertEqual(strong["obligation_results"][0]["status"], "SATISFIED")
        self.assertEqual(result["research_verdict"], "UNKNOWN")

    def test_semantic_ids_survive_renaming_and_matched_reordering(self) -> None:
        original = compose(integrated_record(), policy())
        transformed = compose(
            integrated_record(amount_index=1, renamed=True),
            policy(amount_index=1, renamed=True),
        )
        for arm in ("basic-structural-composition", "strong-simple-composition"):
            original_by_kind = {
                candidate["kind"]: candidate["semantic_id"]
                for candidate in original["baselines"][arm]["candidates"]
            }
            transformed_by_kind = {
                candidate["kind"]: candidate["semantic_id"]
                for candidate in transformed["baselines"][arm]["candidates"]
            }
            self.assertEqual(original_by_kind, transformed_by_kind)
            self.assertNotEqual(
                {candidate["candidate_id"] for candidate in original["baselines"][arm]["candidates"]},
                {candidate["candidate_id"] for candidate in transformed["baselines"][arm]["candidates"]},
            )

    def test_unsupported_static_component_remains_unknown(self) -> None:
        record = integrated_record()
        record["components"]["static"]["status"] = "UNKNOWN"
        record["support_status"] = "UNKNOWN"
        result = compose(record, policy())
        for arm in BASELINE_NAMES:
            self.assertEqual(result["baselines"][arm]["status"], "UNKNOWN")
            self.assertEqual(result["baselines"][arm]["candidates"], [])

    def test_policy_rejects_duplicate_semantic_word_identity(self) -> None:
        invalid = policy()
        invalid["word_identities"] = {"0": "amount", "1": "amount"}
        with self.assertRaises(CompositionInputError):
            compose(integrated_record(), invalid)

    def test_existing_d1p43_union_is_exact_set_union(self) -> None:
        result = json.loads(
            (
                ROOT
                / "results/raw/D2-01-recovery-01/d1p43-rerun/ablation-and-role-target-results.json"
            ).read_text()
        )
        audit = audit_existing_union(result)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["examples"], 9)
        self.assertEqual(audit["supported_examples"], 8)
        self.assertEqual(audit["unknown_examples"], 1)


if __name__ == "__main__":
    unittest.main()
