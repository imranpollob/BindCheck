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
        for name in reserve.HARNESS_FILES:
            harness = self.root / name
            harness.parent.mkdir(parents=True, exist_ok=True)
            harness.write_text(f"# stand-in for {name}\n")

    def authorize(self, **overrides: str) -> None:
        record = {"manifest_sha256": reserve.MANIFEST_SHA256,
                  "approved_by": "test author", "approved_on": "2026-11-19"}
        record.update(overrides)
        self.auth_path.write_text(json.dumps(record))

    @staticmethod
    def commands(*, tag: str = "same", digest: str = reserve.ANALYZER_SHA256, analyzer_diff: int = 0,
                 harness_dirty: str = ""):
        def run(argv, **kwargs):
            if argv[:3] == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(argv, 0, harness_dirty, "")
            if argv[:2] == ["git", "ls-tree"]:
                return subprocess.CompletedProcess(argv, 0, "\n".join(reserve.HARNESS_FILES) + "\n", "")
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

    def test_uncommitted_harness_change_refused(self) -> None:
        # S5R-03
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run",
                               side_effect=self.commands(harness_dirty=" M eval/common.py\n")):
            with self.assertRaisesRegex(reserve.GateError, "uncommitted changes"):
                reserve.check_reserve_gate(self.root)

    def test_gate_records_harness_digests(self) -> None:
        # S5R-03: a resumed run with different harness bytes yields a different gate record.
        self.authorize()
        with mock.patch.object(reserve.subprocess, "run", side_effect=self.commands()):
            first = reserve.check_reserve_gate(self.root)
            (self.root / "eval/common.py").write_text("# changed\n")
            second = reserve.check_reserve_gate(self.root)
        self.assertIn("eval/common.py", first["harness_sha256"])
        self.assertNotEqual(first["harness_sha256"], second["harness_sha256"])

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


class S5RFindingTests(unittest.TestCase):
    """Regressions for the S5R review findings S5R-01, S5R-02 and S5R-04."""

    def setUp(self) -> None:
        self.unit = dict(reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[0])
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = pathlib.Path(self.temporary.name)

    def permit(self):
        return reserve.ReservePermit(
            reserve.ROOT, frozenset({reserve.norm(self.unit["repository"])}), {},
            frozenset({(reserve.norm(self.unit["repository"]), self.unit["commit"].lower())}))

    def test_s5r01_manifest_repository_with_other_commit_refused(self) -> None:
        permit = self.permit()
        swapped = dict(self.unit, commit="0" * 40)
        with (mock.patch.object(reserve, "authorized_repository", return_value=True),
              mock.patch.object(reserve.ReservePermit, "allows", return_value=True),
              mock.patch.object(reserve, "acquire_once") as acquire):
            with self.assertRaisesRegex(reserve.GateError, "not a manifest"):
                reserve.run_unit(swapped, self.output, pathlib.Path("/unused"), permit)
        acquire.assert_not_called()

    def test_s5r01_exact_manifest_pair_allowed(self) -> None:
        with mock.patch.object(reserve.ReservePermit, "allows", return_value=True):
            self.assertTrue(self.permit().allows_pair(self.unit["repository"], self.unit["commit"]))
            self.assertFalse(self.permit().allows_pair(self.unit["repository"], "1" * 40))

    def _run(self, analyzer: dict, raw: str | None):
        def fake_tool(tool, checkout, family_dir):
            if tool == "bindcheck-zk":
                if raw is not None:
                    (family_dir / "bindcheck-zk-raw.json").write_text(raw)
                return analyzer
            return {"raw_result": None}
        with (mock.patch.object(reserve, "authorized_repository", return_value=True),
              mock.patch.object(reserve, "acquire_once", return_value={"status": "ready"}),
              mock.patch.object(reserve, "prepare_pinned_vendor"),
              mock.patch.object(reserve, "prebuild_checkout", return_value={"status": "BUILT"}),
              mock.patch.object(reserve, "run_tool_once", side_effect=fake_tool),
              mock.patch.object(reserve, "capture_warning_sources", return_value={"files": 1}) as capture):
            result = reserve.run_unit(self.unit, self.output, pathlib.Path("/unused"), mock.Mock())
        return result, capture

    def test_s5r02_subprocess_failure_is_harness_error(self) -> None:
        for reason in sorted(reserve.HARNESS_FAILURE_REASONS):
            with self.subTest(reason=reason):
                result, _ = self._run({"reasons": [reason], "run_status": "UNKNOWN", "patterns": {}}, None)
                self.assertEqual(result["status"], "HARNESS_ERROR")
                self.assertEqual(result["reason"], reason)

    def test_s5r02_missing_raw_output_is_harness_error(self) -> None:
        result, _ = self._run({"reasons": [], "run_status": "completed", "patterns": {}}, None)
        self.assertEqual(result["status"], "HARNESS_ERROR")
        result, _ = self._run({"reasons": [], "run_status": "completed", "patterns": {}}, "{not json")
        self.assertEqual(result["status"], "HARNESS_ERROR")

    def test_s5r02_genuine_analyzer_fatal_stays_unsupported(self) -> None:
        result, _ = self._run({"reasons": ["UNSUPPORTED_INPUT"], "run_status": "UNKNOWN",
                               "fatal_reason": "UNSUPPORTED_INPUT", "patterns": {}},
                              json.dumps({"run": {"fatal_reason": "UNSUPPORTED_INPUT"}}))
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_s5r02_incomplete_result_without_raw_output_is_harness_error(self) -> None:
        result, _ = self._run({"reasons": ["SOMETHING"], "run_status": "UNKNOWN",
                               "fatal_reason": "SOMETHING", "patterns": {}}, None)
        self.assertEqual(result["status"], "HARNESS_ERROR")

    def test_s5r04_warning_sources_captured_before_checkout_deleted(self) -> None:
        result, capture = self._run({"reasons": [], "run_status": "completed", "patterns": {"P1": {}}},
                                    json.dumps({"triples": [{}]}))
        self.assertEqual(result["status"], "ANALYZABLE")
        capture.assert_called_once()
        self.assertEqual(result["warning_sources"], {"files": 1})



class S5RRecheckTests(unittest.TestCase):
    """Regressions for the S5R re-check residuals."""

    def setUp(self) -> None:
        self.rows = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)
        self.unit = dict(self.rows[0])
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = pathlib.Path(self.temporary.name)

    def test_s5r01_forged_pair_not_in_pinned_manifest_refused(self) -> None:
        forged = (reserve.norm(self.unit["repository"]), "f" * 40)
        permit = reserve.ReservePermit(reserve.ROOT, frozenset({forged[0]}), {}, frozenset({forged}))
        with mock.patch.object(reserve.ReservePermit, "allows", return_value=True):
            self.assertFalse(permit.allows_pair(self.unit["repository"], "f" * 40))

    def test_s5r01_manifest_pair_outside_permit_refused(self) -> None:
        # A real manifest pair that this permit was not issued for is refused.
        other = self.rows[1]
        permit = reserve.ReservePermit(
            reserve.ROOT, frozenset({reserve.norm(self.unit["repository"]), reserve.norm(other["repository"])}), {},
            frozenset({(reserve.norm(self.unit["repository"]), self.unit["commit"].lower())}))
        with mock.patch.object(reserve.ReservePermit, "allows", return_value=True):
            self.assertTrue(permit.allows_pair(self.unit["repository"], self.unit["commit"]))
            self.assertFalse(permit.allows_pair(other["repository"], other["commit"]))

    def test_s5r02_interrupted_attempts_are_harness_errors(self) -> None:
        self.assertTrue({"INTERRUPTED_ATTEMPT", "UNNORMALIZED_ATTEMPT"} <= reserve.HARNESS_FAILURE_REASONS)

    def test_s5r03_seal_covers_comparison_arms_and_adjudicator(self) -> None:
        sealed = reserve.harness_files(reserve.ROOT)
        for name in ("eval/run_arm_c.py", "eval/adjudicate.py", "baselines/strong/arm_c.py",
                     *reserve.HARNESS_FILES):
            self.assertIn(name, sealed)

    def test_s5r03_resume_from_other_gate_refused(self) -> None:
        units = self.rows[:1]
        reserve.run_units(units, lambda u: {"status": "UNSUPPORTED", "reason": "X"}, self.output, "gate-a")
        with self.assertRaisesRegex(reserve.EvaluationError, "not produced under this gate"):
            reserve.run_units(units, lambda u: {"status": "ANALYZABLE"}, self.output, "gate-b")
        again = reserve.run_units(units, lambda u: {"status": "ANALYZABLE"}, self.output, "gate-a")
        self.assertEqual(again[0]["status"], "UNSUPPORTED")

    def test_s5r03_resume_with_invalid_status_refused(self) -> None:
        units = self.rows[:1]
        path = self.output / "units" / units[0]["unit_id"] / "result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"repository": units[0]["repository"], "commit": units[0]["commit"],
                                    "status": "MADE_UP", "gate_sha256": "gate-a"}))
        with self.assertRaisesRegex(reserve.EvaluationError, "not produced under this gate"):
            reserve.run_units(units, lambda u: {"status": "ANALYZABLE"}, self.output, "gate-a")

    def _analyzable(self, verifier_present: bool):
        checkout_files = {}
        verifier = "contracts/Verifier.sol"
        consumer = "contracts/Pool.sol"
        unit = dict(self.unit, verifier_paths=verifier)
        def fake_acquire(unit_arg, unit_dir, checkout):
            checkout.mkdir(parents=True, exist_ok=True)
            (checkout / "contracts").mkdir()
            (checkout / consumer).write_text("contract Pool {}\n")
            if verifier_present:
                (checkout / verifier).write_text("contract Verifier {}\n")
            return {"status": "ready"}
        def fake_tool(tool, checkout, family_dir):
            if tool == "bindcheck-zk":
                (family_dir / "bindcheck-zk-raw.json").write_text(json.dumps({"triples": [{}]}))
                return {"reasons": [], "run_status": "completed", "patterns": {}}
            if tool == "arm-c":
                (family_dir / "arm-c-raw.json").write_text(json.dumps(
                    {"run": {"status": "completed"},
                     "result": {"findings": [{"location": {"path": consumer}}]}}))
            return {"raw_result": None}
        with (mock.patch.object(reserve, "authorized_repository", return_value=True),
              mock.patch.object(reserve, "acquire_once", side_effect=fake_acquire),
              mock.patch.object(reserve, "prepare_pinned_vendor"),
              mock.patch.object(reserve, "prebuild_checkout", return_value={"status": "BUILT"}),
              mock.patch.object(reserve, "run_tool_once", side_effect=fake_tool)):
            return reserve.run_unit(unit, self.output, pathlib.Path("/unused"), mock.Mock())

    def test_s5r04_real_capture_retains_verifier_source_via_family_json(self) -> None:
        result = self._analyzable(verifier_present=True)
        self.assertEqual(result["status"], "ANALYZABLE")
        self.assertEqual(result["source_capture"], "COMPLETE")
        by_path = {item["source_path"]: item for item in result["warning_sources"]["sources"]}
        # The verifier is reachable only through family.json (the finding is in the consumer).
        self.assertEqual(sorted(by_path), ["contracts/Pool.sol", "contracts/Verifier.sol"])
        self.assertEqual({item["status"] for item in by_path.values()}, {"COPIED"})
        retained = self.output / "units" / self.unit["unit_id"] / by_path["contracts/Verifier.sol"]["retained_path"]
        self.assertTrue(retained.is_file())
        self.assertFalse((self.output / "work" / self.unit["unit_id"]).exists())

    def test_s5r04_missing_source_is_quarantined(self) -> None:
        result = self._analyzable(verifier_present=False)
        self.assertEqual(result["source_capture"], "INCOMPLETE")
        self.assertIn("MISSING", result["source_capture_problems"])



class S5RRecheck2Tests(unittest.TestCase):
    """Regressions for the S5R re-check 2 residual (S5R-03)."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, check=True, text=True,
                              capture_output=True).stdout.strip()

    def make_repo(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        for name in (*reserve.HARNESS_FILES, "eval/run_arm_c.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name}\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "harness")

    def test_deleted_tracked_harness_file_refused(self) -> None:
        self.make_repo()
        self.assertIn("eval/run_arm_c.py", reserve.harness_files(self.root))
        (self.root / "eval/run_arm_c.py").unlink()
        with self.assertRaisesRegex(reserve.GateError, "missing from the working tree"):
            reserve.harness_files(self.root)

    def test_altered_same_gate_result_refused_on_resume(self) -> None:
        units = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[:1]
        output = self.root / "out"
        reserve.run_units(units, lambda u: {"status": "UNSUPPORTED", "reason": "X"}, output, "gate-a")
        path = output / "units" / units[0]["unit_id"] / "result.json"
        record = json.loads(path.read_text())
        record["status"] = "ANALYZABLE"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(reserve.EvaluationError, "run ledger"):
            reserve.run_units(units, lambda u: {"status": "ANALYZABLE"}, output, "gate-a")

    def test_unaltered_resume_accepted(self) -> None:
        units = reserve.read_csv(reserve.ROOT / reserve.MANIFEST)[:2]
        output = self.root / "out"
        reserve.run_units(units[:1], lambda u: {"status": "UNSUPPORTED", "reason": "X"}, output, "gate-a")
        records = reserve.run_units(units, lambda u: {"status": "ANALYZABLE"}, output, "gate-a")
        self.assertEqual([r["status"] for r in records], ["UNSUPPORTED", "ANALYZABLE"])

    def test_second_fresh_start_after_erased_output_refused(self) -> None:
        self.make_repo()
        reserve.claim_start(self.root, fresh=True)
        with self.assertRaisesRegex(reserve.GateError, "already started"):
            reserve.claim_start(self.root, fresh=True)

    def test_resume_requires_start_marker(self) -> None:
        self.make_repo()
        with self.assertRaisesRegex(reserve.GateError, "start marker missing"):
            reserve.claim_start(self.root, fresh=False)
        reserve.claim_start(self.root, fresh=True)
        reserve.claim_start(self.root, fresh=False)
