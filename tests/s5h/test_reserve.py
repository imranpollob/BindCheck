from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from eval import reserve
from scripts import check_holdout


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        for source in (reserve.MANIFEST, reserve.SPENT):
            target = self.root / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(reserve.ROOT / source, target)

    def rows(self) -> list[dict[str, str]]:
        return reserve.read_csv(self.root / reserve.MANIFEST)

    def write_rows(self, rows: list[dict[str, str]]) -> None:
        with (self.root / reserve.MANIFEST).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def load_rehashed(self) -> list[dict[str, str]]:
        digest = hashlib.sha256((self.root / reserve.MANIFEST).read_bytes()).hexdigest()
        with mock.patch.object(reserve, "MANIFEST_SHA256", digest):
            return reserve.load_manifest(self.root)

    def test_original_manifest_has_1105_units_and_390_stratum(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            units = reserve.load_manifest(self.root)
        self.assertEqual(len(units), 1105)
        self.assertEqual(sum(row["maturity"] in reserve.STRATUM for row in units), 390)

    def test_hash_mismatch_refused(self) -> None:
        with (self.root / reserve.MANIFEST).open("ab") as handle:
            handle.write(b"\n")
        with self.assertRaisesRegex(reserve.GateError, "SHA-256"):
            reserve.load_manifest(self.root)

    def test_wrong_row_count_refused_even_when_hash_matches(self) -> None:
        self.write_rows(self.rows()[:-1])
        with self.assertRaisesRegex(reserve.GateError, "1105"):
            self.load_rehashed()

    def test_spent_pair_refused(self) -> None:
        rows = self.rows()
        spent = reserve.read_csv(self.root / reserve.SPENT)[0]
        rows[0]["repository"], rows[0]["commit"] = spent["repository"], spent["commit"]
        self.write_rows(rows)
        with self.assertRaisesRegex(reserve.GateError, "spent"):
            self.load_rehashed()

    def test_warptoad_refused(self) -> None:
        rows = self.rows()
        rows[0]["repository"] = "warptoad/warp-toad"
        self.write_rows(rows)
        with self.assertRaisesRegex(reserve.GateError, "WarpToad"):
            self.load_rehashed()

    def test_duplicate_pair_refused(self) -> None:
        rows = self.rows()
        rows[1]["repository"], rows[1]["commit"] = rows[0]["repository"], rows[0]["commit"]
        self.write_rows(rows)
        with self.assertRaisesRegex(reserve.GateError, "duplicate"):
            self.load_rehashed()

    def test_wrong_stratum_count_refused(self) -> None:
        rows = self.rows()
        member = next(row for row in rows if row["maturity"] in reserve.STRATUM)
        member["maturity"] = "unclassified"
        self.write_rows(rows)
        with self.assertRaisesRegex(reserve.GateError, "390"):
            self.load_rehashed()


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        path = self.root / reserve.AUTHORIZATION
        path.parent.mkdir(parents=True)
        self.auth_path = path

    def authorize(self, **overrides: str) -> None:
        record = {"manifest_sha256": reserve.MANIFEST_SHA256,
                  "approved_by": "test author", "approved_on": "2026-11-19"}
        record.update(overrides)
        self.auth_path.write_text(json.dumps(record))

    @staticmethod
    def commands(*, tag: str = "same", digest: str = reserve.ANALYZER_SHA256, analyzer_diff: int = 0):
        def run(argv, **kwargs):
            if argv[:2] == ["git", "rev-parse"]:
                if argv[2] == "HEAD":
                    value = "same"
                elif argv[2].startswith("refs/tags/freeze-3"):
                    value = "freeze3-commit"
                else:
                    value = tag
                return subprocess.CompletedProcess(argv, 0, value + "\n", "")
            if argv[:3] == ["git", "diff", "--quiet"]:
                return subprocess.CompletedProcess(argv, analyzer_diff, "", "")
            return subprocess.CompletedProcess(argv, 0,
                f"BINDCHECK_ZK_CONTENT_SHA256={digest}\n", "")
        return run

    def test_missing_authorization_refused(self) -> None:
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            with self.assertRaisesRegex(reserve.GateError, "missing"):
                reserve.check_reserve_gate(self.root)

    def test_inconsistent_authorization_refused(self) -> None:
        self.authorize(manifest_sha256="0" * 64)
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            with self.assertRaisesRegex(reserve.GateError, "manifest hash"):
                reserve.check_reserve_gate(self.root)

    def test_blank_approval_refused(self) -> None:
        self.authorize(approved_by="")
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            with self.assertRaisesRegex(reserve.GateError, "approved_by"):
                reserve.check_reserve_gate(self.root)

    def test_valid_authorization_record_passes(self) -> None:
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            gate = reserve.check_reserve_gate(self.root)
        self.assertEqual(gate["manifest_sha256"], reserve.MANIFEST_SHA256)
        self.assertEqual(gate["approved_by"], "test author")

    def test_wrong_tag_refused(self) -> None:
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands(tag="other")):
            with self.assertRaisesRegex(reserve.GateError, "tag does not equal"):
                reserve.check_reserve_gate(self.root)

    def test_analyzer_files_differ_from_freeze3_refused(self) -> None:
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands(analyzer_diff=1)):
            with self.assertRaisesRegex(reserve.GateError, "differ from the freeze-3 tag"):
                reserve.check_reserve_gate(self.root)

    def test_run_tag_may_differ_from_freeze3_commit(self) -> None:
        # Oracle/harness commits after freeze 3 are allowed if analyzer files are unchanged.
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            gate = reserve.check_reserve_gate(self.root)
        self.assertEqual(gate["head"], "same")

    def test_wrong_analyzer_hash_refused(self) -> None:
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands(digest="0" * 64)):
            with self.assertRaisesRegex(reserve.GateError, "analyzer content hash"):
                reserve.check_reserve_gate(self.root)


class GuardTests(unittest.TestCase):
    def test_default_cli_still_refuses_reserved_repository(self) -> None:
        repository = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[0]["repository"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = check_holdout.main([repository])
        self.assertEqual(status, 1)
        self.assertIn("FORBIDDEN", output.getvalue())

    def test_reserve_hook_requires_manifest_unit_and_valid_record(self) -> None:
        repository = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[0]["repository"]
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest = root / reserve.MANIFEST
            manifest.parent.mkdir(parents=True)
            shutil.copyfile(reserve.ROOT / reserve.MANIFEST, manifest)
            authorization = root / reserve.AUTHORIZATION
            authorization.write_text(json.dumps({"manifest_sha256": reserve.MANIFEST_SHA256,
                                                  "approved_by": "test", "approved_on": "2026-11-19"}))
            gate = {"manifest_sha256": reserve.MANIFEST_SHA256, "authorization_sha256": reserve.sha256_file(authorization)}
            permit = reserve.ReservePermit(root, frozenset({check_holdout.norm(repository)}), gate)
            with mock.patch.object(reserve, "check_reserve_gate", return_value=gate):
                self.assertTrue(reserve.authorized_repository(repository, permit))
                self.assertFalse(reserve.authorized_repository("not/in-manifest", permit))
            authorization.unlink()
            self.assertFalse(reserve.authorized_repository(repository, permit))


class RunnerTests(unittest.TestCase):
    def test_prebuild_requires_explicit_circom(self) -> None:
        result = subprocess.run([sys.executable, "eval/prebuild_heldout.py", "--sample",
                                 "reports/heldout/selected-families.csv"],
                                cwd=reserve.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--circom", result.stderr)

    def test_fake_runner_accounts_for_every_unit_once(self) -> None:
        units = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)
        statuses = sorted(reserve.FUNNEL)
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary)
            records = reserve.run_units(units, lambda unit: {"status": statuses[int(unit["unit_id"][-4:]) % len(statuses)]}, output)
            self.assertEqual(len(records), 1105)
            self.assertEqual(len({row["unit_id"] for row in records}), 1105)
            funnel = json.loads((output / "funnel.json").read_text())
            self.assertEqual(funnel["units"], 1105)
            self.assertEqual(sum(funnel["status_counts"].values()), 1105)
            self.assertEqual(funnel["stratum_units"], 390)

    def test_runner_exception_is_harness_error_not_unsupported(self) -> None:
        units = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[:2]
        def runner(unit):
            if unit is units[0]:
                raise RuntimeError("boom")
            return {"status": "UNSUPPORTED", "reason": "NO_RECOVERED_TRIPLE"}
        with tempfile.TemporaryDirectory() as temporary:
            records = reserve.run_units(units, runner, pathlib.Path(temporary))
        self.assertEqual(records[0]["status"], "HARNESS_ERROR")
        self.assertEqual(records[0]["reason"], "HARNESS_INTERNAL_ERROR")
        self.assertEqual(records[1]["status"], "UNSUPPORTED")
        self.assertEqual(len(records), 2)

    def test_run_unit_maps_each_funnel_stage_without_a_checkout(self) -> None:
        unit = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[0]
        # HARNESS_ERROR is assigned by run_units when the runner raises; see the next test.
        for expected in sorted(reserve.FUNNEL - {"HARNESS_ERROR"}):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                output = pathlib.Path(temporary)
                unit_dir = output / "units" / unit["unit_id"]
                def fake_tool(tool: str, checkout: pathlib.Path, family_dir: pathlib.Path):
                    if tool == "bindcheck-zk":
                        (family_dir / "bindcheck-zk-raw.json").write_text(
                            json.dumps({"triples": [{}] if expected == "ANALYZABLE" else []}))
                        return {"reasons": ["HARNESS_TIMEOUT"] if expected == "HARNESS_TIMEOUT" else [],
                                "run_status": "UNKNOWN" if expected == "HARNESS_TIMEOUT" else "completed",
                                "patterns": {}}
                    return {"raw_result": None}
                acquisition = {"status": "fetch-failed" if expected == "ACQUISITION_FAILED" else "ready"}
                prebuild = {"status": "BUILD_FAILED" if expected == "BUILD_FAILED" else "BUILT"}
                with (mock.patch.object(reserve, "authorized_repository", return_value=True),
                      mock.patch.object(reserve, "acquire_once", return_value=acquisition),
                      mock.patch.object(reserve, "prepare_pinned_vendor"),
                      mock.patch.object(reserve, "prebuild_checkout", return_value=prebuild),
                      mock.patch.object(reserve, "run_tool_once", side_effect=fake_tool)):
                    result = reserve.run_unit(unit, output, pathlib.Path("/unused-circom"), mock.Mock())
                self.assertEqual(result["status"], expected)
                self.assertTrue(unit_dir.exists())


if __name__ == "__main__":
    unittest.main()
