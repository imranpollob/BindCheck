"""In-memory guard removal probes; never edits the checkout or opens a reserve repo."""

from __future__ import annotations

import importlib
import inspect
import textwrap
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from eval import reserve  # noqa: E402
from scripts import check_holdout  # noqa: E402

tests = importlib.import_module("test_reserve")

PROBES = (
    (reserve, "load_manifest", "if not path.is_file() or sha256_file(path) != MANIFEST_SHA256:",
     "if not path.is_file():", "ManifestTests.test_hash_mismatch_refused"),
    (reserve, "load_manifest", "if len(rows) != 1105:", "if False:",
     "ManifestTests.test_wrong_row_count_refused_even_when_hash_matches"),
    (reserve, "load_manifest", "if pair in pairs or pair in spent:", "if pair in pairs:",
     "ManifestTests.test_spent_pair_refused"),
    (reserve, "load_manifest", "if pair[0] == \"warptoad/warp-toad\":", "if False:",
     "ManifestTests.test_warptoad_refused"),
    (reserve, "load_manifest", "if pair in pairs or pair in spent:", "if pair in spent:",
     "ManifestTests.test_duplicate_pair_refused"),
    (reserve, "load_manifest", "if stratum_count != 390:", "if False:",
     "ManifestTests.test_wrong_stratum_count_refused"),
    (reserve, "check_reserve_gate", "if head != run_tag:", "if False:",
     "GateTests.test_wrong_tag_refused"),
    (reserve, "check_reserve_gate", "if diff.returncode != 0:", "if False:",
     "GateTests.test_analyzer_files_differ_from_freeze3_refused"),
    (reserve, "run_units", "outcome = {\"status\": \"HARNESS_ERROR\"", "outcome = {\"status\": \"UNSUPPORTED\"",
     "RunnerTests.test_runner_exception_is_harness_error_not_unsupported"),
    (reserve, "check_reserve_gate", "or matches[0] != ANALYZER_SHA256:", ":",
     "GateTests.test_wrong_analyzer_hash_refused"),
    (reserve, "check_reserve_gate", "if not path.is_file():", "if False:",
     "GateTests.test_missing_authorization_refused"),
    (reserve, "check_reserve_gate", "authorization.get(\"manifest_sha256\") != MANIFEST_SHA256:",
     "False:", "GateTests.test_inconsistent_authorization_refused"),
    (reserve, "check_reserve_gate", "if any(not isinstance(authorization.get(key), str) or not authorization[key].strip()",
     "if False and any(not isinstance(authorization.get(key), str) or not authorization[key].strip()",
     "GateTests.test_blank_approval_refused"),
    (check_holdout, "main", "family = index.get(norm(arg))", "family = None",
     "GuardTests.test_default_cli_still_refuses_reserved_repository"),
    (check_holdout, "reserve_decision", "return isinstance(permit, ReservePermit) and permit.allows(repository)",
     "return True", "GuardTests.test_reserve_hook_requires_manifest_unit_and_valid_record"),
    (reserve, "run_unit", "if not permit.allows_pair(unit[\"repository\"], unit[\"commit\"]):", "if False:",
     "S5RFindingTests.test_s5r01_manifest_repository_with_other_commit_refused"),
    (reserve.ReservePermit, "allows_pair", "if pair not in self.pairs or not self.allows(repository):", "if not self.allows(repository):",
     "S5RRecheckTests.test_s5r01_manifest_pair_outside_permit_refused"),
    (reserve, "run_unit", "if harness_failure:", "if False:",
     "S5RFindingTests.test_s5r02_subprocess_failure_is_harness_error"),
    (reserve, "run_unit", "return {\"status\": \"HARNESS_ERROR\", \"reason\": \"ANALYZER_RAW_OUTPUT_MISSING_OR_CORRUPT\"}", "payload = {}",
     "S5RFindingTests.test_s5r02_missing_raw_output_is_harness_error"),
    (reserve, "run_unit", "sources = capture_warning_sources(checkout, unit_dir)", "sources = None",
     "S5RFindingTests.test_s5r04_warning_sources_captured_before_checkout_deleted"),
    (reserve, "check_reserve_gate", "if dirty.returncode or dirty.stdout.strip():", "if False:",
     "GateTests.test_uncommitted_harness_change_refused"),
    (reserve.ReservePermit, "allows_pair", "return pair in pinned", "return True",
     "S5RRecheckTests.test_s5r01_forged_pair_not_in_pinned_manifest_refused"),
    (reserve, "run_unit", "if not raw.is_file():", "if False:",
     "S5RFindingTests.test_s5r02_incomplete_result_without_raw_output_is_harness_error"),
    (reserve, "run_units", "if record.get(\"gate_sha256\") != gate_sha256 or record.get(\"status\") not in FUNNEL:", "if False:",
     "S5RRecheckTests.test_s5r03_resume_from_other_gate_refused"),
    (reserve, "run_unit", "atomic_write_json(unit_dir / \"family.json\", {", "dict({",
     "S5RRecheckTests.test_s5r04_real_capture_retains_verifier_source_via_family_json"),
    (reserve, "run_unit", "\"source_capture\": \"COMPLETE\" if not incomplete else \"INCOMPLETE\",", "\"source_capture\": \"COMPLETE\",",
     "S5RRecheckTests.test_s5r04_missing_source_is_quarantined"),
    (reserve, "harness_files", "if absent:", "if False:",
     "S5RRecheck2Tests.test_deleted_tracked_harness_file_refused"),
    (reserve, "run_units", "if ledger.get(unit_id) != sha256_file(path):", "if False:",
     "S5RRecheck2Tests.test_altered_same_gate_result_refused_on_resume"),
    (reserve, "claim_start", "if created.returncode:", "if False:",
     "S5RRecheck2Tests.test_second_fresh_start_after_erased_output_refused"),
    (reserve, "claim_start", "if current != head:", "if False:",
     "S5RRecheck2Tests.test_resume_requires_start_marker"),
    (reserve, "run_units", "for unit in units:", "for unit in units[:-1]:",
     "RunnerTests.test_fake_runner_accounts_for_every_unit_once"),
)


def main() -> int:
    failures = 0
    for module, name, old, new, test_name in PROBES:
        source = textwrap.dedent(inspect.getsource(getattr(module, name)))
        if source.count(old) != 1:
            raise RuntimeError(f"mutation site changed: {name}: {old}")
        namespace: dict[str, object] = {}
        module_globals = vars(sys.modules[module.__module__]) if isinstance(module, type) else module.__dict__
        exec(compile(source.replace(old, new), f"<mutated {name}>", "exec"), module_globals, namespace)
        target = reserve if name == "reserve_decision" else module
        with mock.patch.object(target, name, namespace[name]):
            case = unittest.defaultTestLoader.loadTestsFromName(test_name, tests)
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream).run(case)
        detected = not result.wasSuccessful()
        print(f"{'DETECTED' if detected else 'MISSED'}\t{name}\t{test_name}")
        failures += not detected
    source = (ROOT / "eval/prebuild_heldout.py").read_text()
    old = 'parser.add_argument("--circom", type=pathlib.Path, required=True)'
    if source.count(old) != 1:
        raise RuntimeError("prebuild --circom mutation site changed")
    with tempfile.TemporaryDirectory() as temporary:
        path = pathlib.Path(temporary) / "prebuild_heldout.py"
        path.write_text(source.replace(old, old.replace("required=True", "required=False")))
        result = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True,
                                text=True, env={**os.environ, "PYTHONPATH": str(ROOT)})
    detected = result.returncode != 2 or "--circom" not in result.stderr
    print(f"{'DETECTED' if detected else 'MISSED'}\tprebuild_main\tRunnerTests.test_prebuild_requires_explicit_circom")
    failures += not detected
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
