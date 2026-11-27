#!/usr/bin/env python3
"""Focused D1P-21B regressions."""

import json
from pathlib import Path
import sys
import unittest

from bindcheck_d1 import joint_warptoad as manual

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "d1p16"))
from extract_relation import UnsupportedConstruct  # noqa: E402
from joint_variant import (  # noqa: E402
    build_omega,
    encode_query,
    load_extracted_relation,
    relation_shape,
)

LANE = HERE.parents[1]
PAPER = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper")
ARTIFACT = PAPER / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
PINNED = LANE / "results/raw/D1P-18/relation.json"
MSRC = LANE / "results/raw/D1P-21B/m-src-relation.json"
RESULTS = LANE / "results/raw/D1P-21B"
IDENTITIES = {"openzeppelin": {"version": "5.6.1"}}
S0 = {
    "giga_root_history": ["1"],
    "local_root_history": ["2"],
    "nullifiers": [],
    "total_supply": "0",
    "balances": {},
    "aztec_warptoad_address": "81985529216486895",
}


class D1P21BTests(unittest.TestCase):
    def extracted(self, relation: Path):
        return build_omega(
            ARTIFACT,
            goal="AUTH-1",
            s0=S0,
            identities=IDENTITIES,
            consumer_model="EXTRACTED",
            relation_path=relation,
            environment={"chain_id": 31337},
        )

    def test_dynamic_shapes_are_accepted_and_all_paths_serialized(self):
        expected = [(PINNED, 22, 19, 3), (MSRC, 21, 18, 3)]
        for relation_path, count, reverts, successes in expected:
            relation = load_extracted_relation(relation_path)
            self.assertEqual(
                {"path_count": count, "revert_paths": reverts, "success_paths": successes,
                 "all_reverts_commit_nothing": True},
                relation_shape(relation),
            )
            query, certificate = encode_query(
                self.extracted(relation_path),
                consumer_model="EXTRACTED",
                drop_producer=True,
            )
            self.assertEqual(count, query.count(b"; PATH "))
            self.assertEqual(count, certificate["path_families_serialized"])
            self.assertEqual(count, len(certificate["serialized_path_ids"]))

    def test_storage_configuration_comes_from_admitted_state(self):
        query, certificate = encode_query(
            self.extracted(PINNED), consumer_model="EXTRACTED", drop_producer=True
        )
        self.assertIn(manual._bv(int(S0["aztec_warptoad_address"])), query.decode())
        self.assertEqual(
            "fixed_pre_state_S0.aztec_warptoad_address",
            certificate["configuration_bindings"]["aztecWarptoadAddress"],
        )

    def test_missing_state_configuration_fails_closed(self):
        incomplete = dict(S0)
        incomplete.pop("aztec_warptoad_address")
        with self.assertRaises(UnsupportedConstruct) as caught:
            build_omega(
                ARTIFACT,
                goal="AUTH-1",
                s0=incomplete,
                identities=IDENTITIES,
                consumer_model="EXTRACTED",
                relation_path=PINNED,
                environment={"chain_id": 31337},
            )
        self.assertEqual("UNSUPPORTED_ADMITTED_STATE_BINDING", caught.exception.code)

    def test_missing_environment_configuration_fails_closed(self):
        with self.assertRaises(UnsupportedConstruct) as caught:
            build_omega(
                ARTIFACT,
                goal="AUTH-1",
                s0=S0,
                identities=IDENTITIES,
                consumer_model="EXTRACTED",
                relation_path=PINNED,
            )
        self.assertEqual("UNSUPPORTED_ADMITTED_ENVIRONMENT_BINDING", caught.exception.code)

    def test_manual_default_remains_byte_identical(self):
        wrapped = build_omega(ARTIFACT, goal="AUTH-1", s0=S0, identities=IDENTITIES)
        direct = manual.build_omega(ARTIFACT, goal="AUTH-1", s0=S0, identities=IDENTITIES)
        self.assertEqual(manual.canonical_bytes(direct), manual.canonical_bytes(wrapped))
        self.assertEqual(manual.encode_query(direct, drop_producer=True),
                         encode_query(wrapped, drop_producer=True))

    def test_generated_validation_passes_required_checks(self):
        validation = json.loads((RESULTS / "validation.json").read_text())
        self.assertEqual("PASS", validation["status"])
        self.assertEqual(0, validation["solver_accounting"]["primary_solver_calls"])
        self.assertEqual(5, validation["pinned_executions"]["count"])
        self.assertEqual(8, validation["pinned_d1p14d_controls"]["count"])
        self.assertTrue(validation["m_src_fixed_input_polarity"]["m_src_fixed_input_sat"])
        self.assertTrue(validation["m_src_fixed_input_polarity"]["pinned_fixed_input_unsat"])


if __name__ == "__main__":
    unittest.main()
