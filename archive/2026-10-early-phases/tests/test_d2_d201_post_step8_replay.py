from __future__ import annotations

import copy
from contextlib import redirect_stdout
import io
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/d2_d201_post_step8_replay.py"
SPEC = importlib.util.spec_from_file_location("d2_d201_post_step8_replay", MODULE_PATH)
assert SPEC and SPEC.loader
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


class D201PostStep8ReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.role_path = ROOT / REPLAY.OVERLAY_PATH
        cls.before_hash = REPLAY._sha256_path(cls.role_path)
        cls.result = REPLAY.run_replay()
        cls.after_hash = REPLAY._sha256_path(cls.role_path)

    def test_live_failure_and_historical_overlay_are_exact(self):
        self.assertEqual(self.result["status"], "PASS")
        live = self.result["direct_live_checkout_replay"]
        self.assertEqual(live["status"], "EXPECTED_FAIL")
        self.assertEqual(live["checked_files"], 8134)
        self.assertEqual(live["mismatch_count"], 1)
        self.assertEqual(live["mismatches"][0]["path"], REPLAY.OVERLAY_PATH)
        self.assertEqual(live["mismatches"][0]["observed_sha256"], REPLAY.CURRENT_SHA256)
        historical = self.result["historical_overlay_replay"]
        self.assertEqual(historical["status"], "PASS")
        self.assertEqual(historical["checked_files"], 8134)
        self.assertEqual(historical["mismatch_count"], 0)
        self.assertEqual(historical["in_memory_substitution_count"], 1)

    def test_replay_does_not_modify_current_role_binding(self):
        self.assertEqual(self.before_hash, REPLAY.CURRENT_SHA256)
        self.assertEqual(self.after_hash, REPLAY.CURRENT_SHA256)
        self.assertEqual(
            self.result["historical_blob"]["materialization"], "IN_MEMORY_ONLY"
        )

    def test_step8_provenance_and_d2_00_gap_stay_separate(self):
        self.assertEqual(self.result["step8_provenance"]["status"], "VERIFIED")
        gap = self.result["d2_00_retention_gap"]
        self.assertEqual(gap["status"], "UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED")
        self.assertEqual(gap["base_commit_lookup"], "ABSENT")
        self.assertFalse(gap["reconstruction_attempted"])
        self.assertFalse(gap["included_in_overlay"])
        self.assertFalse(self.result["interpretation"]["current_checkout_equivalence"])
        self.assertEqual(self.result["interpretation"]["research_verdict"], "UNKNOWN")

    def test_protocol_refuses_a_second_or_different_overlay(self):
        protocol = json.loads(REPLAY.DEFAULT_PROTOCOL.read_text())
        bad = copy.deepcopy(protocol)
        bad["historical_overlay"]["allowed_substitution_count"] = 2
        with self.assertRaisesRegex(ValueError, "only one overlay"):
            REPLAY._validate_protocol(bad)
        bad = copy.deepcopy(protocol)
        bad["historical_overlay"]["path"] = "src/bindcheck_d1/static_analyzer_v1.py"
        with self.assertRaisesRegex(ValueError, "overlay path"):
            REPLAY._validate_protocol(bad)

    def test_cli_error_is_fail_closed_for_tampered_protocol(self):
        protocol = json.loads(REPLAY.DEFAULT_PROTOCOL.read_text())
        protocol["source_seal"]["member_count"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(protocol))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(REPLAY.main(["--protocol", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
