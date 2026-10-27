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

    def test_output_inside_worktree_is_rejected(self):
        with self.assertRaises(reserve.InputError):
            reserve.ensure_external_output(
                reserve.Path(__file__).resolve().parent / "private.json",
                [reserve.Path(__file__).resolve().parents[2]],
            )


if __name__ == "__main__":
    unittest.main()
