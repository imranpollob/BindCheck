#!/usr/bin/env python3
"""Synthetic tests for the metadata-only candidate-list boundary."""

import json
from pathlib import Path
import tempfile
import unittest

import candidate_list


class CandidateListTests(unittest.TestCase):
    def write(self, directory, name, value):
        path = Path(directory) / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_names_only_output_has_exact_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "safe.json", {
                "schema_version": "0.2.0",
                "sources": [{
                    "endpoint_id": "safe-endpoint",
                    "listing_format": "names_only",
                    "custodian_attestation": None,
                    "entries": [{"application_or_project_name": "Synthetic Project", "repository_url": "https://example.invalid/repo"}],
                }],
            })
            rows = candidate_list.parse_inputs([path], {"safe-endpoint": "agent_metadata_allowed"})
            self.assertEqual(rows, [{"application_or_project_name": "Synthetic Project", "repository_url": "https://example.invalid/repo", "endpoint_id": "safe-endpoint"}])

    def test_mixed_listing_is_flagged_for_custodian(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "mixed.json", {
                "schema_version": "0.2.0",
                "sources": [{"endpoint_id": "mixed-endpoint", "listing_format": "mixed_names_and_bug_descriptions", "custodian_attestation": None, "entries": []}],
            })
            with self.assertRaises(candidate_list.CandidateInputError):
                candidate_list.parse_inputs([path], {"mixed-endpoint": "human_sanitized_required"})

    def test_description_field_is_rejected_before_parsing(self):
        with self.assertRaises(candidate_list.CandidateInputError):
            candidate_list.reject_forbidden_keys({"application_or_project_name": "Synthetic", "description": "must not enter agent input"})

    def test_plan_can_require_human_sanitization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "unsafe-mode.json", {
                "schema_version": "0.2.0",
                "sources": [{"endpoint_id": "seed", "listing_format": "names_only", "custodian_attestation": None, "entries": []}],
            })
            with self.assertRaises(candidate_list.CandidateInputError):
                candidate_list.parse_inputs([path], {"seed": "human_sanitized_required"})

    def test_sanitized_input_requires_attestation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "missing-attestation.json", {
                "schema_version": "0.2.0",
                "sources": [{"endpoint_id": "seed", "listing_format": "custodian_sanitized_names_only", "custodian_attestation": None, "entries": []}],
            })
            with self.assertRaises(candidate_list.CandidateInputError):
                candidate_list.parse_inputs([path], {"seed": "human_sanitized_required"})


if __name__ == "__main__":
    unittest.main()
