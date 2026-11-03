from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/d2_foundation.py"
SPEC = importlib.util.spec_from_file_location("d2_foundation", MODULE_PATH)
assert SPEC and SPEC.loader
D2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D2)


class FoundationTest(unittest.TestCase):
    def test_seal_verifies_then_detects_tamper(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as raw:
            work = Path(raw)
            payload = work / "payload.txt"
            payload.write_text("original\n")
            seal = work / "seal.json"
            record = D2.create_seal(
                root=ROOT, output=seal, version="test-v1", entries=[payload]
            )
            self.assertTrue(record["excluded"]["manifest_self_excluded"])
            self.assertEqual(D2.verify_seal(root=ROOT, manifest=seal)["status"], "PASS")
            payload.write_text("changed\n")
            failed = D2.verify_seal(root=ROOT, manifest=seal)
            self.assertEqual(failed["status"], "FAIL")
            self.assertEqual(failed["mismatches"][0]["reason"], "CONTENT_MISMATCH")

    def test_seal_excludes_manifest_and_mutable_indexes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as raw:
            work = Path(raw)
            (work / "payload.txt").write_text("x\n")
            (work / "latest.json").write_text('{}\n')
            seal = work / "seal-v1.json"
            record = D2.create_seal(
                root=ROOT, output=seal, version="test-v1", entries=[work]
            )
            sealed = {item["path"] for item in record["files"]}
            self.assertIn(D2._relative(work / "payload.txt", ROOT), sealed)
            self.assertNotIn(D2._relative(work / "latest.json", ROOT), sealed)
            self.assertNotIn(D2._relative(seal, ROOT), sealed)

    def test_seal_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as raw:
            work = Path(raw)
            payload = work / "payload.txt"
            payload.write_text("x\n")
            seal = work / "seal.json"
            D2.create_seal(root=ROOT, output=seal, version="v1", entries=[payload])
            with self.assertRaises(FileExistsError):
                D2.create_seal(root=ROOT, output=seal, version="v2", entries=[payload])

    def test_seal_rejects_symlink_members(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as raw:
            work = Path(raw)
            payload = work / "payload.txt"
            payload.write_text("x\n")
            link = work / "linked.txt"
            link.symlink_to(payload)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                D2.create_seal(
                    root=ROOT, output=work / "seal.json", version="v1", entries=[link]
                )

    def test_prepare_run_records_required_identity_classes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "results/raw") as raw:
            work = Path(raw)
            input_path = work / "input.bin"
            config_path = work / "config.json"
            input_path.write_bytes(b"input")
            config_path.write_text('{"setting":1}\n')
            output = work / "run.json"
            record = D2.prepare_run_manifest(
                root=ROOT,
                output=output,
                run_id="unit-run",
                experiment="unit-experiment",
                inputs=[input_path],
                configurations=[config_path],
                seeds=["17"],
                wall_seconds=3,
                memory_mib=64,
                max_calls=2,
            )
            self.assertEqual(record["schema"], D2.RUN_SCHEMA)
            self.assertEqual(record["repository"]["commit"], D2._git_record(ROOT)["commit"])
            self.assertEqual(record["inputs"][0]["sha256"], D2.sha256(input_path))
            self.assertEqual(record["configurations"][0]["sha256"], D2.sha256(config_path))
            self.assertEqual(record["seeds"], ["17"])
            self.assertEqual(record["resource_budget"]["max_calls"], 2)
            self.assertEqual({item["name"] for item in record["tools"]}, {"python", "git"})
            self.assertEqual(json.loads(output.read_text())["run_id"], "unit-run")


if __name__ == "__main__":
    unittest.main()
