from __future__ import annotations

import copy
from pathlib import Path
import unittest

from bindcheck_d1.frontends.recursive_public_mapping_v1 import (
    build as build_mapping_certificate,
    verify_certificate,
)
from bindcheck_d1.static_analyzer_v1 import _extent_coverage, load_producer


ROOT = Path(__file__).resolve().parents[1]
PAYY = ROOT.parent / "BindCheck"
PAYY_EARLIER = PAYY / "tools/cases/payy-c4d2c90/noir/target/agg_agg.json"
PAYY_EARLIER_SOURCE = PAYY / "tools/cases/payy-c4d2c90/noir/agg_agg/src/main.nr"
PAYY_CHECK = PAYY / "tools/cases/payy-history/noir/target/agg_agg.json"
PAYY_CHECK_SOURCE = PAYY / "tools/cases/payy-history/noir/agg_agg/src/main.nr"
PAYY_EARLIER_BRIDGE = PAYY / "build/T09/src-c4d2c90/noir/target/agg_final.json"
WT_PINNED = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
WT_C02 = ROOT / "results/raw/X-BM/build/WT-C02/circuits/withdraw/target/withdraw.json"


def fact(condition: dict) -> dict:
    return {"status": "EXACT", "condition": condition}


class D1P42ExtentInterfaceTests(unittest.TestCase):
    def test_all_path_binding_covers_a_full_consumer(self):
        result = _extent_coverage(fact({"kind": "always"}), fact({
            "kind": "prefix", "extent": "configured_length", "extent_value": 4,
        }))
        self.assertEqual((result["status"], result["covered"]), ("EXACT", True))

    def test_matching_prefixes_are_covered(self):
        condition = {"kind": "prefix", "extent": "active_count"}
        result = _extent_coverage(fact(condition), fact(condition))
        self.assertEqual((result["status"], result["covered"]), ("EXACT", True))

    def test_wider_consumer_reports_the_uncovered_region(self):
        result = _extent_coverage(
            fact({"kind": "prefix", "extent": "active_count"}),
            fact({"kind": "prefix", "extent": "configured_length", "extent_value": 4}),
        )
        self.assertFalse(result["covered"])
        self.assertEqual(result["uncovered_region"],
                         "active_count <= word_offset < configured_length")

    def test_unknown_condition_never_becomes_covered(self):
        result = _extent_coverage(
            {"status": "UNKNOWN", "condition": {"kind": "unknown", "reason": "test"}},
            fact({"kind": "always"}),
        )
        self.assertEqual((result["status"], result["covered"]), ("UNKNOWN", None))


@unittest.skipUnless(PAYY_EARLIER.is_file() and PAYY_EARLIER_BRIDGE.is_file(),
                     "owned-local Payy artifacts unavailable")
class D1P42PayyCertificateTests(unittest.TestCase):
    def test_exact_1005_to_1003_certificate_is_total(self):
        certificate = build_mapping_certificate(PAYY_EARLIER, PAYY_EARLIER_BRIDGE)
        self.assertEqual(certificate["inner_public_count"], 1005)
        self.assertEqual(certificate["consumer_public_count"], 1003)
        self.assertEqual(len(certificate["configuration_prefix"]), 2)
        self.assertEqual(len(certificate["mapping"]), 1003)
        self.assertEqual(certificate["mapping"][0]["producer_path"], "old_root")
        self.assertEqual(certificate["mapping"][-1]["producer_path"], "messages[999]")
        self.assertTrue(verify_certificate(certificate, PAYY_EARLIER, PAYY_EARLIER_BRIDGE))

    def test_tampered_mapping_certificate_fails_closed(self):
        certificate = build_mapping_certificate(PAYY_EARLIER, PAYY_EARLIER_BRIDGE)
        tampered = copy.deepcopy(certificate)
        tampered["mapping"][0]["producer_index"] += 1
        with self.assertRaisesRegex(ValueError, "PRODUCER_IDENTITY_CHANGED"):
            verify_certificate(tampered, PAYY_EARLIER, PAYY_EARLIER_BRIDGE)

    def test_earlier_is_prefix_bound_and_check_added_is_all_path_bound(self):
        earlier = load_producer(PAYY_EARLIER, PAYY_EARLIER_SOURCE)
        check = load_producer(PAYY_CHECK, PAYY_CHECK_SOURCE)
        earlier_messages = [item for item in earlier["public_leaves"]
                            if item["path"].startswith("messages[")]
        check_messages = [item for item in check["public_leaves"]
                          if item["path"].startswith("messages[")]
        self.assertEqual({item["binding_condition"]["kind"] for item in earlier_messages},
                         {"prefix"})
        self.assertEqual({item["binding_condition"]["extent"] for item in earlier_messages},
                         {"active_messages_count"})
        self.assertEqual({item["binding_condition"]["kind"] for item in check_messages},
                         {"always"})


@unittest.skipUnless(WT_PINNED.is_file() and WT_C02.is_file(),
                     "owned-local WarpToad artifacts unavailable")
class D1P42WarpToadComparisonTests(unittest.TestCase):
    def test_max_fee_integer_comparison_is_counted_and_mutant_removes_it(self):
        pinned = next(item for item in load_producer(WT_PINNED)["public_leaves"]
                      if item["path"] == "max_fee")
        mutant = next(item for item in load_producer(WT_C02)["public_leaves"]
                      if item["path"] == "max_fee")
        self.assertEqual(pinned["occurrence_count"], 3)
        self.assertEqual(pinned["witness_generation_occurrence_count"], 3)
        self.assertEqual(mutant["occurrence_count"], 0)
        self.assertEqual(mutant["witness_generation_occurrence_count"], 0)
        self.assertEqual(mutant["binding_condition"], {"kind": "never"})


if __name__ == "__main__":
    unittest.main()
