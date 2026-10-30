#!/usr/bin/env python3
"""Freeze BindCheck v1.2 after its development-only validation gates."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-35"
EXPECTED_BASE = "d981c6468acbaef8c1d5d4a1c542dec4ec2d088a"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def record(relative: str) -> dict:
    path = ROOT / relative
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def git_show(relative: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{relative}"], cwd=ROOT, text=True,
    )


def function_node(source: str, name: str) -> ast.FunctionDef:
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"function not found: {name}")


class ReportingLocationNormalizer(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if (isinstance(node.func, ast.Name) and node.func.id == "warning"
                and len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "R-EFFECT"):
            node.args[1] = ast.Constant("<REPORTING_LOCATION>")
        return node

    def visit_Dict(self, node: ast.Dict):
        node = self.generic_visit(node)
        for index, key in enumerate(node.keys):
            if isinstance(key, ast.Constant) and key.value == "verifier_location":
                node.values[index] = ast.Constant("<REPORTING_LOCATION>")
        return node


def normalized_function_hash(source: str, name: str, normalize_locations: bool = False) -> str:
    node = function_node(source, name)
    if normalize_locations:
        node = ReportingLocationNormalizer().visit(node)
        ast.fix_missing_locations(node)
    return sha256_bytes(ast.dump(node, include_attributes=False).encode())


def main() -> int:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != EXPECTED_BASE:
        raise SystemExit(f"unexpected base: {head}")
    version_validation = json.loads((RAW / "version-validation.json").read_text())
    comparison = json.loads((RAW / "evaluation/evaluation-comparison.json").read_text())
    if not version_validation["beta14_through_beta22_public_leaves_and_occurrences_match"]:
        raise SystemExit("version validation did not pass")
    if not comparison["all_status_reason_warning_identity_and_nonlocation_facts_equal"]:
        raise SystemExit("D1P-34 comparison did not pass")
    if comparison["unknown_warning_locations_after"] != 0:
        raise SystemExit("unknown warning locations remain")

    analyzer_path = "src/bindcheck_d1/static_analyzer_v1.py"
    before = git_show(analyzer_path)
    after = (ROOT / analyzer_path).read_text()
    exact_functions = ["_expression_witnesses", "_nested_witnesses", "_opcode_witnesses",
                       "_leaf_bindings", "_ranges"]
    function_checks = {}
    for name in exact_functions:
        before_hash = normalized_function_hash(before, name)
        after_hash = normalized_function_hash(after, name)
        function_checks[name] = {
            "before_ast_sha256": before_hash,
            "after_ast_sha256": after_hash,
            "equal": before_hash == after_hash,
        }
    for name in ("analyze", "load_relation_consumer"):
        before_hash = normalized_function_hash(before, name, normalize_locations=True)
        after_hash = normalized_function_hash(after, name, normalize_locations=True)
        function_checks[name] = {
            "normalization": "reporting-location expressions only",
            "before_ast_sha256": before_hash,
            "after_ast_sha256": after_hash,
            "equal": before_hash == after_hash,
        }
    if not all(item["equal"] for item in function_checks.values()):
        raise SystemExit("protected analyzer AST changed")

    exact_files = [
        "protocols/d1/bindcheck-v1.1-effect-models.json",
        "src/bindcheck_d1/frontends/acir_binary_v1.py",
        "src/bindcheck_d1/frontends/acir_binary_beta22.py",
        "src/bindcheck_d1/frontends/solidity_ast_v1_1.py",
    ]
    exact_checks = {}
    for relative in exact_files:
        before_hash = sha256_bytes(git_show(relative).encode())
        after_hash = sha256(ROOT / relative)
        exact_checks[relative] = {
            "base_sha256": before_hash,
            "frozen_sha256": after_hash,
            "equal": before_hash == after_hash,
        }
    if not all(item["equal"] for item in exact_checks.values()):
        raise SystemExit("protected file changed")

    frozen_files = [
        analyzer_path,
        "src/bindcheck_d1/cli.py",
        "src/bindcheck_d1/frontends/acir_binary_beta15_21.py",
        "src/bindcheck_d1/frontends/acir_binary_v1.py",
        "src/bindcheck_d1/frontends/acir_binary_beta22.py",
        "src/bindcheck_d1/frontends/solidity_ast_v1_1.py",
        "src/bindcheck_d1/validation_v1.py",
        "protocols/d1/bindcheck-v1.1-effect-models.json",
        "protocols/d1/d1p-30-consumer-relations.json",
        "protocols/d1/d1p-30-validation-index.json",
        "tests/test_bindcheck_v1.py",
        "tests/test_bindcheck_v12.py",
        "tests/d1/fixtures/noir_versions/Nargo.toml",
        "tests/d1/fixtures/noir_versions/src/main.nr",
        "scripts/d1p_35_frontend_validation.py",
        "scripts/d1p_35_evaluate.py",
        "scripts/d1p_35_freeze.py",
    ]
    payload = {
        "schema": "bindcheck.d1p35.v1.2-freeze/v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "BindCheck v1.2",
        "base_commit": head,
        "held_out_set_b_opened_before_freeze": False,
        "allowed_change_scope": [
            "Noir beta.15 through beta.21 ACIR container decoding",
            "consumer warning source-line reporting",
        ],
        "beta3": "UNSUPPORTED_DISTINCT_SCHEMA",
        "gates": {
            "version_validation": {
                "path": "results/raw/D1P-35/version-validation.json",
                "sha256": sha256(RAW / "version-validation.json"),
            },
            "d1p34_evaluation_comparison": {
                "path": "results/raw/D1P-35/evaluation/evaluation-comparison.json",
                "sha256": sha256(RAW / "evaluation/evaluation-comparison.json"),
                "classification_counts": comparison[
                    "classification_counts_carried_by_identical_warnings"
                ],
            },
        },
        "protected_function_ast_checks": function_checks,
        "protected_exact_file_checks": exact_checks,
        "frozen_files": [record(relative) for relative in frozen_files],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["freeze_payload_sha256"] = sha256_bytes(canonical)
    output = RAW / "freeze-manifest.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(output), "sha256": sha256(output),
                      "freeze_payload_sha256": payload["freeze_payload_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
