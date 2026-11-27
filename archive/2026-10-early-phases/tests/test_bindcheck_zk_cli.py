from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

from bindcheck_zk.freeze import freeze_manifest
from tests.test_bindcheck_zk_controls import write_fixture


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "bindcheck-zk"


class BindCheckZKCLITests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        return completed, json.loads(completed.stdout)

    def test_analyze_emits_one_pinned_result(self):
        with tempfile.TemporaryDirectory(prefix="bindcheck-zk-cli-") as name:
            root = pathlib.Path(name)
            write_fixture(root, "p1_fixed_direct")
            completed, output = self.run_cli(
                "analyze", str(root),
                "--circuit", "circuits/main.nr",
                "--consumer", "contracts/Consumer.sol",
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(output["schema"], "bindcheck-zk.result/v1")
        self.assertEqual(output["patterns"]["P1"]["verdict"], "VERIFIED_WITHIN_SCOPE")
        self.assertEqual({item["path"] for item in output["inputs"]["files"]}, {
            "circuits/main.nr", "contracts/Consumer.sol", "contracts/Verifier.sol",
        })
        self.assertEqual(output["tool"]["content_sha256"], freeze_manifest(ROOT)[0])

    def test_bundle_reads_runtime_without_network(self):
        with tempfile.TemporaryDirectory(prefix="bindcheck-zk-bundle-") as name:
            root = pathlib.Path(name)
            write_fixture(root, "p4_runtime_default")
            completed, output = self.run_cli("analyze-bundle", str(root))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(output["inputs"]["mode"], "verified-source-bundle")
        self.assertEqual(output["patterns"]["P4"]["verdict"], "UNKNOWN")
        self.assertIn("DEFAULT_G2_RUNTIME_SIGNATURE", output["patterns"]["P4"]["reasons"])

    def test_bad_input_is_unknown_json_not_crash(self):
        completed, output = self.run_cli("analyze", "/definitely/not/a/repository")
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(output["run"]["status"], "UNKNOWN")
        self.assertTrue(all(item["verdict"] == "UNKNOWN" for item in output["patterns"].values()))

    def test_freeze_manifest_is_deterministic(self):
        first = freeze_manifest(ROOT)
        second = freeze_manifest(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 64)
        self.assertIn("bindcheck_zk/config.json", {name for name, _ in first[1]})
        self.assertIn("requirements-bindcheck-zk.txt", {name for name, _ in first[1]})

    def test_unavailable_baseline_uses_common_unknown_envelope(self):
        with tempfile.TemporaryDirectory(prefix="bindcheck-zk-baseline-") as name:
            root = pathlib.Path(name)
            write_fixture(root, "p1_fixed_direct")
            completed, output = self.run_cli(
                "baseline", "zkap", str(root),
                "--circuit", "circuits/main.nr",
                "--consumer", "contracts/Consumer.sol",
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(output["patterns"]["P1"]["verdict"], "UNKNOWN")
        self.assertEqual(output["patterns"]["P1"]["reasons"], ["BASELINE_TOOL_UNAVAILABLE"])


if __name__ == "__main__":
    unittest.main()
