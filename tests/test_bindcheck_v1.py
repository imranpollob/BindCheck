from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from bindcheck_d1.static_analyzer_v1 import analyze, _opcode_witnesses
from bindcheck_d1.cli import DEFAULT_CONSUMER_INDEX, resolve_consumer_ir
from bindcheck_d1.validation_v1 import select_warning, validate


ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
MDOM = ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json"
PINNED_SOURCE = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol"
PINNED_RELATION = ROOT / "results/raw/D1P-18/relation.json"
MSRC_SOURCE = ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol"
MSRC_RELATION = ROOT / "results/raw/D1P-21B/m-src-relation.json"
PAYY_ROOT = ROOT.parent / "BindCheck"
PAYY_SOURCE = ROOT / "benchmarks/binding-mutants/baselines/RollupV1.sol"
PAYY_CHECK_SOURCE = PAYY_ROOT / "tools/cases/payy-history/eth/contracts/rollup3/RollupV1.sol"
PAYY_EARLIER = PAYY_ROOT / "tools/cases/payy-c4d2c90/noir/target/agg_agg.json"
PAYY_CHECK = PAYY_ROOT / "tools/cases/payy-history/noir/target/agg_agg.json"
PAYY_EARLIER_IR = ROOT / "results/raw/D1P-34/consumer-relations/payy-baseline.json"
PAYY_CHECK_IR = ROOT / "results/raw/D1P-34/consumer-relations/payy-check-added.json"


class BindCheckV1Tests(unittest.TestCase):
    def test_pinned_has_no_supported_warning(self):
        result = analyze(PINNED, PINNED_SOURCE, PINNED_RELATION, "pinned")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["polarity"]["replay"]["must_not_be_in"])
        self.assertTrue(result["polarity"]["replay"]["written"])

    def test_mdom_finds_unused_domain_word(self):
        result = analyze(MDOM, PINNED_SOURCE, PINNED_RELATION, "m-dom")
        self.assertEqual([warning["rule"] for warning in result["warnings"]], ["R-BIND"])
        self.assertEqual(result["warnings"][0]["evidence"]["public_indices"], [5])

    def test_msrc_finds_missing_must_be_in_anchor(self):
        result = analyze(PINNED, MSRC_SOURCE, MSRC_RELATION, "m-src")
        self.assertEqual([warning["rule"] for warning in result["warnings"]], ["R-CONSUMER"])
        self.assertEqual(result["warnings"][0]["evidence"]["public_index"], 4)

    def test_two_argument_cli_relation_resolution_is_content_addressed(self):
        self.assertEqual(resolve_consumer_ir(MSRC_SOURCE, None, DEFAULT_CONSUMER_INDEX), MSRC_RELATION)
        self.assertIsNone(resolve_consumer_ir(PAYY_SOURCE, None, DEFAULT_CONSUMER_INDEX))

    def test_full_size_payy_differential_without_reference_oracle(self):
        earlier = analyze(PAYY_EARLIER, PAYY_SOURCE, PAYY_EARLIER_IR, "earlier")
        repaired = analyze(PAYY_CHECK, PAYY_CHECK_SOURCE, PAYY_CHECK_IR, "check-added")
        self.assertEqual([warning["rule"] for warning in earlier["warnings"]],
                         ["R-BIND", "R-EFFECT", "R-CONSUMER"])
        self.assertEqual(earlier["warnings"][0]["evidence"]["public_indices"],
                         list(range(6, 1005)))
        self.assertEqual([warning["rule"] for warning in repaired["warnings"]], ["R-CONSUMER"])
        self.assertTrue(repaired["polarity"]["replay"]["must_not_be_in"])
        self.assertTrue(repaired["polarity"]["replay"]["written"])

    def test_source_only_loader_is_removed(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_CONSUMER_AST_REQUIRED"):
            analyze(PINNED, PINNED_SOURCE, None, "unsupported")

    def test_opcode_use_roles_cover_outputs_memory_and_brillig(self):
        poseidon = {"kind": "Poseidon2Permutation", "inputs": [{"witness": 1}], "outputs": [2]}
        memory = {"kind": "MemoryOp", "block_id": 7,
                  "operation": {"mul": [], "linear": [[1, 3]], "constant": 0},
                  "index": {"mul": [], "linear": [[1, 4]], "constant": 0},
                  "value": {"mul": [], "linear": [[1, 5]], "constant": 0}}
        init = {"kind": "MemoryInit", "block_id": 7, "init": [6]}
        brillig = {"kind": "BrilligCall", "id": 0,
                   "inputs": [{"single": {"mul": [], "linear": [[1, 8]], "constant": 0}}],
                   "outputs": [{"single": 9}], "predicate": None}
        self.assertEqual(_opcode_witnesses(poseidon), ([1, 2], [], []))
        self.assertEqual(_opcode_witnesses(memory), ([3, 4, 5], [], []))
        self.assertEqual(_opcode_witnesses(init), ([], [], [6]))
        self.assertEqual(_opcode_witnesses(brillig), ([], [8, 9], []))

    def test_ast_relation_recovers_replay_and_burn_effect(self):
        relation = json.loads(PAYY_EARLIER_IR.read_text())
        self.assertEqual(relation["verifier_boundary"]["signature"],
                         "function (bytes memory,bytes32[] memory) view external returns (bool)")
        self.assertTrue(all(item["guarded_absent"] for item in relation["replay_records"]))
        self.assertIn("token-transfer", {item["kind"] for item in relation["effects"]})

    def test_analysis_path_has_no_application_specific_tokens(self):
        paths = [ROOT / "src/bindcheck_d1/static_analyzer_v1.py",
                 ROOT / "src/bindcheck_d1/frontends/solidity_ast_v1_1.py"]
        text = "\n".join(path.read_text() for path in paths)
        for token in ("withdrawVerifier", "verifyMessages", "verifyRootHash", ".spent",
                      "WarpToad", "Payy", "RollupV1"):
            self.assertNotIn(token, text)

    def test_warning_selector_requires_id_for_multiple(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analysis.json"
            path.write_text(json.dumps({"schema": "bindcheck.static-analysis.v1", "warnings": [
                {"id": "W001"}, {"id": "W002"},
            ]}))
            with self.assertRaises(ValueError):
                select_warning(str(path))
            _path, warning = select_warning(str(path) + "#W002")
            self.assertEqual(warning["id"], "W002")

    def test_validator_runs_missing_preparation_then_checks_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warning_path = root / "warning.json"
            warning_path.write_text(json.dumps({
                "id": "W001", "rule": "R-BIND",
                "target_identity": {"artifact_sha256": "a", "consumer_sha256": "b", "rule": "R-BIND"},
            }))
            index_path = root / "index.json"
            index_path.write_text(json.dumps({"routes": [{
                "id": "synthetic", "match": {"artifact_sha256": "a", "consumer_sha256": "b", "rule": "R-BIND"},
                "classification": "test", "fresh_execution": True,
                "manual_steps": 0, "manual_inputs": [], "scope_note": "test only", "failed_routes": [],
                "prepare": {
                    "sentinel": "evidence.json", "outputs": ["evidence.json"], "cwd": ".",
                    "argv": [sys.executable, "-c", "from pathlib import Path; Path('evidence.json').write_text('{\\\"ok\\\": true}')"],
                },
                "stages": [{
                    "name": "synthetic", "evidence_level": "E2", "mode": "fresh",
                    "explanation": "test", "checks": [{"path": "evidence.json", "json_path": "ok", "equals": True}],
                }],
            }]}))
            result = validate(str(warning_path), index_path, root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["highest_evidence_level"], "E2")
            self.assertTrue(result["preparation"]["command_executed"])


if __name__ == "__main__":
    unittest.main()
