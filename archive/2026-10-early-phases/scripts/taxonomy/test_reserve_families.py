#!/usr/bin/env python3
"""Synthetic unit tests; these do not perform or persist a reservation draw."""

import hashlib
import unittest

import reserve_families as reserve


def group(group_id, eligibility, *, exposed=False, newly_eligible=True):
    return {
        "group_id": group_id,
        "candidate_application_names": [f"Synthetic {group_id}"],
        "newly_eligible": newly_eligible,
        "exposed": exposed,
        "tool_transfer_eligibility": eligibility,
        "stratum_id": f"synthetic:{eligibility}",
        "grouping_basis": "Synthetic test metadata only.",
    }


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.grouped = {
            "schema_version": "0.2.0",
            "grouped_at": "2026-10-27",
            "rounding": "ceil_per_stratum",
            "groups": [
                group("g1", "eligible"),
                group("g2", "eligible"),
                group("g3", "eligible"),
                group("g4", "ineligible"),
                group("g5", "ineligible"),
                group("g6", "unknown", exposed=True),
            ],
        }

    def test_seeded_selection_is_deterministic_and_stratified(self):
        seed = bytes(range(32))
        first = reserve.build_manifest(self.grouped, seed)
        second = reserve.build_manifest(self.grouped, seed)
        self.assertEqual(first, second)
        self.assertEqual(first["eligible_group_count"], 5)
        self.assertEqual(first["reserved_group_count"], 3)
        counts = {row["tool_transfer_eligibility"]: row["reserved_group_count"] for row in first["strata"]}
        self.assertEqual(counts, {"eligible": 2, "ineligible": 1})
        self.assertNotIn("g6", first["reserved_family_group_ids"])

    def test_commitment_is_nonce_then_canonical_manifest(self):
        manifest = reserve.build_manifest(self.grouped, bytes(range(32)))
        nonce = bytes(reversed(range(32)))
        expected = hashlib.sha256(nonce + reserve.canonical_json(manifest)).hexdigest()
        self.assertEqual(len(expected), 64)
        self.assertEqual(expected, hashlib.sha256(nonce + reserve.canonical_json(manifest)).hexdigest())

    def test_stratum_must_record_tool_eligibility(self):
        self.grouped["groups"][0]["stratum_id"] = "synthetic:wrong"
        with self.assertRaises(reserve.InputError):
            reserve.validate_grouped_list(self.grouped)

    def test_draw_rejects_pool_with_no_tool_transfer_eligible_group(self):
        self.grouped["groups"] = [group("g4", "ineligible"), group("g5", "unknown")]
        with self.assertRaises(reserve.InputError):
            reserve.build_manifest(self.grouped, bytes(range(32)))

    def test_default_fraction_is_unchanged_half(self):
        seed = bytes(range(32))
        manifest = reserve.build_manifest(self.grouped, seed)
        explicit = reserve.build_manifest(self.grouped, seed, reserve.parse_fraction("1/2"))
        self.assertEqual(manifest, explicit)
        self.assertNotIn("reservation_fraction", manifest)
        for size, ceil_count, floor_count in ((1, 1, 0), (5, 3, 2), (8, 4, 4), (30, 15, 15)):
            self.assertEqual(reserve.reserve_count(size, "ceil_per_stratum"), ceil_count)
            self.assertEqual(reserve.reserve_count(size, "floor_per_stratum"), floor_count)

    def test_one_third_ceil_per_stratum_30_and_8(self):
        third = reserve.parse_fraction("1/3")
        self.grouped["groups"] = [group(f"e{i:02d}", "eligible") for i in range(30)] + [
            group(f"u{i}", "unknown") for i in range(8)
        ]
        manifest = reserve.build_manifest(self.grouped, bytes(range(32)), third)
        counts = {row["stratum_id"]: row["reserved_group_count"] for row in manifest["strata"]}
        self.assertEqual(counts, {"synthetic:eligible": 10, "synthetic:unknown": 3})
        self.assertEqual(manifest["reserved_group_count"], 13)
        self.assertEqual(len(manifest["reserved_family_group_ids"]), 13)
        self.assertEqual(manifest["reservation_fraction"], "1/3")

    def test_one_third_single_strata_counts(self):
        third = reserve.parse_fraction("1/3")
        for size, expected in ((30, 10), (8, 3)):
            self.grouped["groups"] = [group(f"e{i:02d}", "eligible") for i in range(size)]
            manifest = reserve.build_manifest(self.grouped, bytes(range(32)), third)
            self.assertEqual(manifest["reserved_group_count"], expected)
        self.assertEqual(reserve.reserve_count(8, "floor_per_stratum", third), 2)

    def test_fraction_must_be_exact_and_proper(self):
        for text in ("0.33", "1/1", "0/3", "3/2", "1/0", "-1/3", " 1/3", "1 / 3"):
            with self.assertRaises(reserve.InputError, msg=text):
                reserve.parse_fraction(text)
        self.assertEqual(reserve.parse_fraction("2/6"), reserve.parse_fraction("1/3"))

    def test_output_inside_worktree_is_rejected(self):
        with self.assertRaises(reserve.InputError):
            reserve.ensure_external_output(
                reserve.Path(__file__).resolve().parent / "private.json",
                [reserve.Path(__file__).resolve().parents[2]],
            )


if __name__ == "__main__":
    unittest.main()
