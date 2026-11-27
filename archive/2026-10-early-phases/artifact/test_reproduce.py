#!/usr/bin/env python3
"""Deterministic known-answer tests for artifact/reproduce.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("reproduce.py")
SPEC = importlib.util.spec_from_file_location("d2_artifact_reproduce", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
reproduce = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reproduce)


class ArtifactReproduceTests(unittest.TestCase):
    def test_safe_run_id_is_fresh_direct_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "work"
            target = reproduce.validated_work_path("fresh-01", work_root=root)
            self.assertEqual(target, root / "fresh-01")
            root.mkdir()
            target.mkdir()
            with self.assertRaises(reproduce.ArtifactError):
                reproduce.validated_work_path("fresh-01", work_root=root)

    def test_unsafe_run_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "work"
            for value in ("", "../escape", "a/b", ".hidden", "white space", "x" * 65):
                with self.subTest(value=value):
                    with self.assertRaises(reproduce.ArtifactError):
                        reproduce.validated_work_path(value, work_root=root)

    def test_sidecar_resolution_is_explicit(self) -> None:
        sidecar = Path("/tmp/reviewed-sidecar").resolve()
        self.assertEqual(
            reproduce.resolve_evidence_path("results/raw/D2-08/run-summary.json", sidecar),
            sidecar / "results/raw/D2-08/run-summary.json",
        )
        self.assertEqual(
            reproduce.resolve_evidence_path("../BindCheck/build/example.json", sidecar),
            sidecar / "external/BindCheck/build/example.json",
        )
        self.assertEqual(
            reproduce.resolve_evidence_path(
                "/Users/example/.solc-select/artifacts/solc-0.8.29/solc-0.8.29",
                sidecar,
            ),
            sidecar / "external/tools/solc-0.8.29",
        )
        with self.assertRaises(reproduce.ArtifactError):
            reproduce.resolve_evidence_path("/tmp/unrecognized", sidecar)

    def test_expected_live_mismatch_accepts_only_exact_record(self) -> None:
        exact = [{
            "path": reproduce.D2_01_ROLE_PATH,
            "reason": "CONTENT_MISMATCH",
            "expected_sha256": reproduce.D2_01_ROLE_OLD_SHA256,
            "expected_size_bytes": reproduce.D2_01_ROLE_OLD_SIZE,
            "observed_sha256": reproduce.D2_01_ROLE_CURRENT_SHA256,
            "observed_size_bytes": reproduce.D2_01_ROLE_CURRENT_SIZE,
        }]
        reproduce.validate_expected_live_d2_01_mismatch(exact)
        with self.assertRaises(reproduce.ArtifactError):
            reproduce.validate_expected_live_d2_01_mismatch([])
        altered = [dict(exact[0], path="src/bindcheck_d1/other.py")]
        with self.assertRaises(reproduce.ArtifactError):
            reproduce.validate_expected_live_d2_01_mismatch(altered)

    def test_seal_in_memory_override_never_writes_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seal = root / "seal.json"
            data = b"historical bytes\n"
            seal.write_text(json.dumps({
                "schema": "test-seal",
                "files": [{
                    "path": "missing/member.txt",
                    "sha256": reproduce.sha256_bytes(data),
                    "size_bytes": len(data),
                }],
            }), encoding="utf-8")
            result = reproduce.verify_seal(
                seal, None, byte_overrides={"missing/member.txt": data}
            )
            self.assertEqual(result["status"], "PASS")
            self.assertFalse((reproduce.ROOT / "missing/member.txt").exists())

    def test_sha256sums_parser_rejects_traversal_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "SHA256SUMS"
            digest = "0" * 64
            path.write_text(f"{digest}  ../escape\n", encoding="utf-8")
            with self.assertRaises(reproduce.ArtifactError):
                reproduce.parse_sha256sums(path)
            path.write_text(
                f"{digest}  artifact/a\n{digest}  artifact/a\n", encoding="utf-8"
            )
            with self.assertRaises(reproduce.ArtifactError):
                reproduce.parse_sha256sums(path)

    def test_status_and_expected_documents_are_nonfinal(self) -> None:
        status = reproduce.load_json(reproduce.ARTIFACT / "STATUS.json")
        expected = reproduce.load_json(reproduce.ARTIFACT / "expected-results-v1.json")
        self.assertEqual(status["status"], reproduce.STATUS)
        self.assertEqual(expected["status"], reproduce.STATUS)
        self.assertFalse(status["frozen_release_claimed"])
        self.assertFalse(status["reserved_data_included"])
        self.assertEqual(expected["research_verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
