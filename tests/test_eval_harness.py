from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from eval.adjudicate import cohen_kappa
from eval.common import (
    PLAN_SOURCE_SHA256,
    RECALL_LEDGER,
    ROOT,
    SOURCE_LEDGER,
    GateError,
    check_eval_gate,
    aggregate_payload_verdict,
    normalize_tool_payload,
    read_csv,
    select_families,
    sha256_file,
)
from eval.run_heldout import run_tool_once
from eval.run_recall import score_pair, strict_resolved_rows
from eval.summarize import build_summary, summarize_group


def git(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = read_csv(SOURCE_LEDGER)

    def test_preregistered_eval_selection(self) -> None:
        self.assertEqual(sha256_file(SOURCE_LEDGER), PLAN_SOURCE_SHA256)
        selected = select_families(self.rows, "EVAL")
        self.assertEqual(len(selected), 278)
        counts: dict[str, int] = {}
        for item in selected:
            counts[item["stratum"]] = counts.get(item["stratum"], 0) + 1
        self.assertEqual(counts, {
            "verified-deployed": 38,
            "deployed-address-in-docs": 60,
            "audited-production": 60,
            "hackathon-student": 60,
            "unclassified": 60,
        })
        self.assertEqual(len({item["family_id"] for item in selected}), 278)
        dev = {row["v2_family_id"] for row in self.rows if row["split"] == "DEV"}
        self.assertFalse(dev & {item["family_id"] for item in selected})
        for item in selected:
            expected = hashlib.sha256(
                ("bindcheck-eval-v2-family-sample-2026-11-03|" + item["family_id"]).encode()
            ).hexdigest()
            self.assertEqual(item["sample_hash"], expected)

    def test_five_family_dev_subset_is_deterministic(self) -> None:
        first = select_families(self.rows, "DEV", max_families=5)
        second = select_families(self.rows, "DEV", max_families=5)
        self.assertEqual(first, second)
        self.assertEqual([item["repository"] for item in first], [
            "KanishJebaMathewM/Truxify",
            "polybase/payy",
            "ava-labs/EncryptedERC",
            "Blacksaviour/Undertow",
            "Veilpayapp/VEILPAY-APP",
        ])


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        git(self.root, "init", "--quiet")
        git(self.root, "config", "user.name", "Eval Test")
        git(self.root, "config", "user.email", "eval@example.invalid")
        self.dataset = self.root / "source-corpus-v2.csv"
        self.dataset.write_text("repository,commit\nowner/repo," + "a" * 40 + "\n")
        self.analyzer_hash = "1" * 64
        freeze = self.root / "freeze.sh"
        freeze.write_text(
            "#!/bin/sh\nset -eu\nprintf '%s\\n' "
            f"'BINDCHECK_ZK_CONTENT_SHA256={self.analyzer_hash}'\n"
        )
        freeze.chmod(0o755)
        git(self.root, "add", "source-corpus-v2.csv", "freeze.sh")
        git(self.root, "commit", "--quiet", "-m", "fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def tag(self, name: str, source_hash: str) -> None:
        message = (
            f"BINDCHECK_ZK_CONTENT_SHA256={self.analyzer_hash}\n"
            f"SOURCE_CORPUS_V2_SHA256={source_hash}"
        )
        git(self.root, "tag", "-a", name, "-m", message)

    def dataset_tag(self, source_hash: str) -> None:
        git(
            self.root, "tag", "-a", "bindcheck-zk-dataset-v2-test", "-m",
            f"SOURCE_CORPUS_V2_SHA256={source_hash}",
        )

    def test_eval_refused_without_env_tag_or_matching_hash(self) -> None:
        with self.assertRaisesRegex(GateError, "BINDCHECK_EVAL_AUTHORIZED"):
            check_eval_gate(self.root, self.dataset, environ={})
        with self.assertRaisesRegex(GateError, "no bindcheck-zk-frozen"):
            check_eval_gate(
                self.root, self.dataset, environ={"BINDCHECK_EVAL_AUTHORIZED": "1"}
            )
        self.tag("bindcheck-zk-frozen-wrong", "0" * 64)
        with self.assertRaisesRegex(GateError, "SOURCE_CORPUS_V2_SHA256"):
            check_eval_gate(
                self.root, self.dataset, environ={"BINDCHECK_EVAL_AUTHORIZED": "1"}
            )

    def test_matching_annotated_tag_passes_and_dataset_mutation_fails(self) -> None:
        dataset_hash = sha256_file(self.dataset)
        self.tag("bindcheck-zk-frozen-test", dataset_hash)
        with self.assertRaisesRegex(GateError, "dataset-v2"):
            check_eval_gate(
                self.root, self.dataset, environ={"BINDCHECK_EVAL_AUTHORIZED": "1"}
            )
        self.dataset_tag(dataset_hash)
        gate = check_eval_gate(
            self.root, self.dataset, environ={"BINDCHECK_EVAL_AUTHORIZED": "1"}
        )
        self.assertEqual(gate["tag"], "bindcheck-zk-frozen-test")
        self.assertEqual(gate["dataset_tag"], "bindcheck-zk-dataset-v2-test")
        self.dataset.write_text(self.dataset.read_text() + "other/repo," + "b" * 40 + "\n")
        with self.assertRaisesRegex(GateError, "SOURCE_CORPUS_V2_SHA256"):
            check_eval_gate(
                self.root, self.dataset, environ={"BINDCHECK_EVAL_AUTHORIZED": "1"}
            )


class ResumeTests(unittest.TestCase):
    def test_started_tool_attempt_is_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            family_dir = pathlib.Path(temporary)
            (family_dir / "bindcheck-zk-attempt.json").write_text(json.dumps({"status": "started"}))
            result = run_tool_once("bindcheck-zk", family_dir / "missing-checkout", family_dir)
            self.assertEqual(result["verdict"], "UNKNOWN")
            self.assertEqual(result["reasons"], ["INTERRUPTED_ATTEMPT"])


class SummaryTests(unittest.TestCase):
    def test_pattern_normalization_preserves_applicability_and_reasons(self) -> None:
        payload = {
            "patterns": {
                "P1": {"verdict": "VIOLATION", "applicability": "APPLICABLE", "reasons": ["UNBOUND_EFFECT_AMOUNT"], "unknown_reason_codes": []},
                "P2": {"verdict": "UNKNOWN", "applicability": "NOT_APPLICABLE", "reasons": ["NO_CONTEXT"], "unknown_reason_codes": ["NO_TARGET"]},
                "P3": {"verdict": "UNKNOWN", "applicability": "APPLICABLE", "reasons": ["MIXED_SUMMARY"], "unknown_reason_codes": ["UNSUPPORTED_CONSTRUCT"]},
            },
            "triples": [
                {"patterns": {"P3": {"verdict": "UNKNOWN", "reason": "REAL_UNKNOWN", "unknown_reason_code": "UNSUPPORTED_CONSTRUCT"}}},
                {"patterns": {"P3": {"verdict": "VERIFIED_WITHIN_SCOPE", "reason": "VERIFIED_REASON"}}},
            ],
        }
        normalized = normalize_tool_payload("bindcheck-zk", payload, "raw.json")
        self.assertEqual(normalized["patterns"]["P1"]["verdict"], "VIOLATION")
        self.assertEqual(normalized["patterns"]["P2"]["applicability"], "NOT_APPLICABLE")
        self.assertEqual(normalized["patterns"]["P2"]["verdict"], "UNKNOWN")
        self.assertEqual(normalized["patterns"]["P3"]["reasons"], ["MIXED_SUMMARY"])
        self.assertEqual(normalized["patterns"]["P3"]["unknown_reason_codes"], ["UNSUPPORTED_CONSTRUCT"])
        verdict, reasons = aggregate_payload_verdict(payload, "P3")
        self.assertEqual(verdict, "UNKNOWN")
        self.assertIn("REAL_UNKNOWN", reasons)
        self.assertNotIn("VERIFIED_REASON", reasons)

    def test_per_pattern_summary_has_verdict_by_applicability_and_unknown_codes(self) -> None:
        families = [
            {"family": {"stratum": "verified-deployed"}, "tools": {"bindcheck-zk": normalize_tool_payload("bindcheck-zk", {
                "patterns": {"P1": {"verdict": "VIOLATION", "applicability": "APPLICABLE", "reasons": ["UNBOUND"]},
                             "P2": {"verdict": "UNKNOWN", "applicability": "NOT_APPLICABLE", "reasons": ["NO_CONTEXT"]}},
            }, "a.json")}},
            {"family": {"stratum": "verified-deployed"}, "tools": {"bindcheck-zk": normalize_tool_payload("bindcheck-zk", {
                "patterns": {"P1": {"verdict": "UNKNOWN", "applicability": "APPLICABLE", "reasons": ["UNRESOLVED"], "unknown_reason_codes": ["UNSUPPORTED_CONSTRUCT"]},
                             "P2": {"verdict": "VERIFIED_WITHIN_SCOPE", "applicability": "APPLICABLE", "reasons": ["CONTEXT_BOUND"]}},
            }, "b.json")}},
        ]
        summary = build_summary(families, seed=7, replicates=0)
        p1 = summary["tools"]["bindcheck-zk"]["P1"]["overall"]
        p2 = summary["tools"]["bindcheck-zk"]["P2"]["overall"]
        self.assertEqual(p1["verdict_by_applicability"]["VIOLATION"]["APPLICABLE"], 1)
        self.assertEqual(p1["verdict_by_applicability"]["UNKNOWN"]["APPLICABLE"], 1)
        self.assertEqual(p1["unknown_by_reason"], {"UNRESOLVED": 1})
        self.assertEqual(p1["unknown_by_reason_code"], {"UNSUPPORTED_CONSTRUCT": 1})
        self.assertEqual(p2["verdict_by_applicability"]["UNKNOWN"]["NOT_APPLICABLE"], 1)
        self.assertEqual(p2["applicable"], 1)
        self.assertEqual(p2["decided"], 1)

    def test_unknown_future_reasons_and_not_applicable_are_preserved(self) -> None:
        records = [
            {"verdict": "VIOLATION", "applicability": "APPLICABLE", "reasons": []},
            {"verdict": "VERIFIED_WITHIN_SCOPE", "applicability": "APPLICABLE", "reasons": []},
            {"verdict": "UNKNOWN", "applicability": "APPLICABLE", "reasons": ["FUTURE_REASON_9000"]},
            {"verdict": "UNKNOWN", "applicability": "NOT_APPLICABLE", "reasons": ["NO_NATIVE_SCOPE"]},
        ]
        summary = summarize_group(records, seed=7, replicates=200)
        self.assertEqual(summary["applicable"], 3)
        self.assertEqual(summary["decided"], 2)
        self.assertEqual(summary["unknown_by_reason"], {"FUTURE_REASON_9000": 1, "NO_NATIVE_SCOPE": 1})
        self.assertIn("violation_rate_among_applicable", summary["family_bootstrap_95pct"])


class RecallTests(unittest.TestCase):
    def test_strict_resolved_inventory_has_sixteen_pairs(self) -> None:
        self.assertEqual(len(strict_resolved_rows(read_csv(RECALL_LEDGER), "EVAL")), 16)

    def test_predicate_build_location_and_e4_are_separate(self) -> None:
        vulnerable = {
            "patterns": {"P3": {"verdict": "VIOLATION"}},
            "triples": [{"patterns": {"P3": {
                "verdict": "VIOLATION", "evidence_grade": "E1",
                "location": {"path": "Consumer.sol", "line": 42},
            }}}],
            "coverage": {"builds": [{"record": {"exit_status": 0, "timed_out": False}}]},
        }
        fixed = {
            "patterns": {"P3": {"verdict": "VERIFIED_WITHIN_SCOPE"}},
            "triples": [],
            "coverage": {"builds": [{"record": {"kind": "existing"}}]},
        }
        score = score_pair("P3", r"Consumer\.sol:42$", vulnerable, fixed)
        self.assertTrue(score["predicate_detected"])
        self.assertTrue(score["pair_build_success"])
        self.assertTrue(score["location_match"])
        self.assertFalse(score["e4"])


class AdjudicationTests(unittest.TestCase):
    def test_known_cohen_kappa(self) -> None:
        result = cohen_kappa(
            {"a": "TP", "b": "TP", "c": "FP"},
            {"a": "TP", "b": "FP", "c": "FP"},
        )
        self.assertEqual(result["observed_agreement"], 0.666667)
        self.assertEqual(result["expected_agreement"], 0.444444)
        self.assertEqual(result["cohen_kappa"], 0.4)


if __name__ == "__main__":
    unittest.main()
