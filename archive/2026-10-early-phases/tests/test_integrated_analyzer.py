"""Focused controls for the D2 integrated analysis interface."""

from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bindcheck_d1.cli import main as cli_main, parser
from bindcheck_d1.integrated_analyzer_v1 import (
    analyze_integrated,
    warning_stable_id,
)
from bindcheck_d1.role_binding import RoleBindingUnsupported
from bindcheck_d1.validation_v1 import select_warning, validate


def warning(identifier: str, rule: str = "R-BIND") -> dict:
    return {
        "id": identifier,
        "rule": rule,
        "severity": "warning",
        "confidence": "high",
        "location": "Fixture.sol:10",
        "explanation": "fixture explanation",
        "suggested_fix": "fixture repair",
        "evidence": {"public_indices": [2]},
        "target_identity": {
            "artifact_sha256": "artifact",
            "consumer_sha256": "consumer",
            "rule": rule,
        },
    }


def static_result(warnings: list[dict]) -> dict:
    return {
        "schema": "bindcheck.static-analysis.v1.4-dev",
        "target": "fixture",
        "producer": {"sha256": "artifact", "public_leaves": []},
        "consumer": {"source_sha256": "consumer"},
        "rules": {"R-BIND": "fixture"},
        "warnings": warnings,
        "warning_count": len(warnings),
        "manual_inputs": [],
        "limitations": [],
    }


class IntegratedAnalyzerTests(unittest.TestCase):
    def paths(self, root: Path) -> tuple[Path, Path, Path, Path]:
        paths = tuple(root / name for name in (
            "artifact.json", "Consumer.sol", "relation.json", "main.nr"
        ))
        for path in paths:
            path.write_text(path.name)
        return paths  # type: ignore[return-value]

    def test_stable_identity_does_not_depend_on_legacy_ordinal(self) -> None:
        first = warning("W001")
        second = warning("W099")
        second["location"] = "Fixture.sol:999"
        self.assertEqual(warning_stable_id(first), warning_stable_id(second))
        second["evidence"] = {"public_indices": [3]}
        self.assertNotEqual(warning_stable_id(first), warning_stable_id(second))

    def test_stable_identity_recursively_ignores_source_locations(self) -> None:
        first = warning("W001")
        first["target_identity"]["source_location"] = {
            "file": "Fixture.sol", "line": 10, "column": 4,
        }
        first["evidence"] = {
            "public_indices": [2],
            "binding": {
                "producer_role": "state_root",
                "effect_location": "Fixture.sol:10:4",
                "provenance": {
                    "sourceSpan": {
                        "start": {"line": 10, "column": 4},
                        "end": {"line": 10, "column": 17},
                    },
                    "line_number": 10,
                },
            },
        }
        second = deepcopy(first)
        second["target_identity"]["source_location"] = {
            "file": "Moved.sol", "line": 900, "column": 40,
        }
        second["evidence"]["binding"]["effect_location"] = "Moved.sol:900:40"
        second["evidence"]["binding"]["provenance"] = {
            "sourceSpan": {
                "start": {"line": 900, "column": 40},
                "end": {"line": 901, "column": 2},
            },
            "line_number": 900,
        }
        self.assertEqual(warning_stable_id(first), warning_stable_id(second))

        second["evidence"]["binding"]["producer_role"] = "nullifier_root"
        self.assertNotEqual(warning_stable_id(first), warning_stable_id(second))

    def test_static_and_role_warnings_are_composed_without_rule_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact, consumer, relation, producer = self.paths(Path(temporary))
            role = {
                "schema": "bindcheck.role-binding.v1",
                "warnings": [warning("ROLE001", "R-ROLE")],
                "warning_count": 1,
            }
            with (
                patch(
                    "bindcheck_d1.integrated_analyzer_v1.analyze_static",
                    return_value=static_result([warning("W001")]),
                ),
                patch(
                    "bindcheck_d1.integrated_analyzer_v1.analyze_role_binding",
                    return_value=role,
                ),
            ):
                result = analyze_integrated(
                    artifact, consumer, relation, producer_source=producer,
                    producer_support_sources=(),
                )
        self.assertEqual(result["support_status"], "SUPPORTED")
        self.assertEqual([item["rule"] for item in result["warnings"]], ["R-BIND", "R-ROLE"])
        self.assertEqual(
            [item["analysis_component"] for item in result["warnings"]],
            ["static", "role_binding"],
        )
        self.assertEqual(len({item["stable_id"] for item in result["warnings"]}), 2)
        self.assertEqual(result["outcome"]["verdict"], "UNKNOWN")
        self.assertEqual(result["outcome"]["evidence_grade"], "E1")

    def test_role_support_failure_is_unknown_and_preserves_partial_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact, consumer, relation, producer = self.paths(Path(temporary))
            with (
                patch(
                    "bindcheck_d1.integrated_analyzer_v1.analyze_static",
                    return_value=static_result([warning("W001")]),
                ),
                patch(
                    "bindcheck_d1.integrated_analyzer_v1.analyze_role_binding",
                    side_effect=RoleBindingUnsupported("ROLE_WORD_WIDTH_MISMATCH:fixture"),
                ),
            ):
                result = analyze_integrated(
                    artifact, consumer, relation, producer_source=producer,
                )
        self.assertEqual(result["support_status"], "UNKNOWN")
        self.assertEqual(result["components"]["role_binding"]["reason_code"],
                         "ROLE_WORD_WIDTH_MISMATCH")
        self.assertEqual([item["id"] for item in result["warnings"]], ["W001"])
        self.assertEqual(result["outcome"]["verdict"], "UNKNOWN")

    def test_static_support_failure_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact, consumer, relation, _producer = self.paths(Path(temporary))
            with patch(
                "bindcheck_d1.integrated_analyzer_v1.analyze_static",
                side_effect=ValueError("CONSUMER_PUBLIC_INPUT_MAPPING_UNVERIFIED:fixture"),
            ):
                result = analyze_integrated(artifact, consumer, relation)
        self.assertEqual(result["support_status"], "UNKNOWN")
        self.assertEqual(result["components"]["static"]["reason_code"],
                         "CONSUMER_PUBLIC_INPUT_MAPPING_UNVERIFIED")
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["outcome"]["evidence_grade"], "E0")

    def test_missing_input_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = analyze_integrated(
                root / "missing-artifact.json",
                root / "missing-consumer.sol",
                root / "missing-relation.json",
            )
        self.assertEqual(result["support_status"], "UNKNOWN")
        self.assertEqual(result["components"]["static"]["reason_code"],
                         "INPUT_FILE_NOT_FOUND")

    def test_validator_selects_integrated_warning_by_stable_id(self) -> None:
        item = warning("W001")
        item["source_id"] = "W001"
        item["stable_id"] = warning_stable_id(item)
        other = warning("W002")
        other["evidence"]["public_indices"] = [3]
        other["stable_id"] = warning_stable_id(other)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "analysis.json"
            path.write_text(json.dumps({
                "schema": "bindcheck.integrated-analysis.v1",
                "warnings": [item, other],
            }))
            _path, selected = select_warning(f"{path}#{item['stable_id']}")
        self.assertEqual(selected["id"], "W001")

    def test_validator_accepts_stable_id_after_nested_location_change(self) -> None:
        item = warning("W001")
        item["evidence"]["binding"] = {
            "role": "state_root",
            "source_location": {"line": 10, "column": 2},
        }
        item["stable_id"] = warning_stable_id(item)
        item["evidence"]["binding"]["source_location"] = {
            "line": 999, "column": 88,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "analysis.json"
            path.write_text(json.dumps({
                "schema": "bindcheck.integrated-analysis.v1",
                "warnings": [item],
            }))
            _path, selected = select_warning(f"{path}#{item['stable_id']}")
        self.assertEqual(selected["id"], "W001")

    def test_validator_rejects_forged_stable_id_before_selection(self) -> None:
        item = warning("W001")
        item["stable_id"] = "BC-00000000000000000000"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "analysis.json"
            path.write_text(json.dumps({
                "schema": "bindcheck.integrated-analysis.v1",
                "warnings": [item],
            }))
            with self.assertRaisesRegex(ValueError, "WARNING_STABLE_ID_MISMATCH:W001"):
                select_warning(f"{path}#{item['stable_id']}")

    def test_validator_rejects_stale_stable_id_before_route_matching(self) -> None:
        item = warning("W001")
        item["stable_id"] = warning_stable_id(item)
        item["evidence"]["public_indices"] = [3]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            analysis = root / "analysis.json"
            analysis.write_text(json.dumps({
                "schema": "bindcheck.integrated-analysis.v1",
                "warnings": [item],
            }))
            index = root / "index.json"
            index.write_text(json.dumps({"routes": [{
                "id": "forged-route",
                "match": {"stable_id": item["stable_id"]},
            }]}))
            with self.assertRaisesRegex(ValueError, "WARNING_STABLE_ID_MISMATCH:W001"):
                validate(str(analysis), index, root)

    def test_validator_accepts_current_static_schema_and_stable_route(self) -> None:
        item = warning("W001")
        item["stable_id"] = warning_stable_id(item)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            analysis = root / "analysis.json"
            analysis.write_text(json.dumps({
                "schema": "bindcheck.static-analysis.v1.4-dev",
                "warnings": [item],
            }))
            index = root / "index.json"
            index.write_text(json.dumps({"routes": [{
                "id": "stable-route",
                "match": {"stable_id": item["stable_id"]},
                "classification": "test",
                "fresh_execution": False,
                "manual_steps": 0,
                "manual_inputs": [],
                "scope_note": "test",
                "failed_routes": [],
                "stages": [],
            }]}))
            result = validate(str(analysis), index, root)
        self.assertEqual(result["route"]["id"], "stable-route")
        self.assertEqual(result["highest_evidence_level"], "E1")

    def test_cli_exposes_integration_inputs(self) -> None:
        args = parser().parse_args([
            "analyze", "artifact.json", "Consumer.sol",
            "--producer-source", "main.nr",
            "--producer-support-source", "hash.nr",
            "--mapping-bridge", "bridge.json",
        ])
        self.assertEqual(args.producer_source, Path("main.nr"))
        self.assertEqual(args.producer_support_source, [Path("hash.nr")])
        self.assertEqual(args.mapping_bridge, Path("bridge.json"))

    def test_legacy_two_argument_cli_preserves_static_schema(self) -> None:
        legacy = static_result([])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "analysis.json"
            with (
                patch("bindcheck_d1.cli.resolve_consumer_ir", return_value=None),
                patch("bindcheck_d1.cli.analyze_static", return_value=legacy) as static,
                patch("bindcheck_d1.cli.analyze_integrated") as integrated,
                patch("bindcheck_d1.cli.readable_static", return_value="legacy"),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = cli_main([
                    "analyze", "artifact.json", "Consumer.sol", "--json", str(output),
                ])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output.read_text())["schema"],
                             "bindcheck.static-analysis.v1.4-dev")
            static.assert_called_once()
            integrated.assert_not_called()


if __name__ == "__main__":
    unittest.main()
