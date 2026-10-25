#!/usr/bin/env python3
"""Provenance-checked, serialization-only intake for the six T22-v5 queries.

The historical execution manifest uses absolute Linux paths.  This adapter
matches identities by unique, role-specific suffixes and accepts all local
paths explicitly.  It validates every input before importing the legacy
builder or creating an output directory.

No solver result can be produced here: the temporary ``FF.solve`` replacement
serializes the exact historical SMT-LIB header/body/footer and then raises a
private completion exception.  The legacy process launcher is independently
replaced with a fail-closed guard for the duration of each query build.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import platform
from pathlib import Path
import sys
from typing import Callable


CASES = ("check_added", "running_flag")
QUERIES = ("nonvacuous", "prefix", "tail")
INPUT_ROLES = {
    "check_added_acir": "b_agg_agg_check_added_.compile.stdout",
    "check_added_abi": "b_agg_agg_check_added_.abi.json",
    "running_flag_acir": "m4_b_different_idiom_flag_.compile.stdout",
    "running_flag_abi": "m4_b_different_idiom_flag_.abi.json",
}
COMPONENT_SUFFIXES = {
    "protocol": "/scripts/t22_v5_protocol.md",
    "encoder": "/scripts/t22_v5_compact.py",
    "parser": "/scripts/t22_v3_tailspec.py",
    "spec": "/scripts/t22_specs/payy_agg_agg.json",
}


class IntakeError(RuntimeError):
    """A provenance, input, or serialization boundary failure."""


class SerializationComplete(Exception):
    """Internal control flow: exact query bytes were written, without solving."""

    def __init__(self, data: bytes):
        super().__init__("serialization complete; solver execution prohibited")
        self.data = data


@dataclass(frozen=True)
class InputBundle:
    check_added_acir: Path
    check_added_abi: Path
    running_flag_acir: Path
    running_flag_abi: Path

    def items(self):
        for role in INPUT_ROLES:
            yield role, Path(getattr(self, role))


@dataclass(frozen=True)
class Components:
    protocol: Path
    encoder: Path
    parser: Path
    spec: Path

    def items(self):
        for role in COMPONENT_SUFFIXES:
            yield role, Path(getattr(self, role))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_suffix_hash(entries: dict[str, str], suffix: str) -> str:
    normalized = suffix.replace("\\", "/")
    matches = [value for key, value in entries.items()
               if key.replace("\\", "/").endswith(normalized)]
    if len(matches) != 1:
        raise IntakeError(
            f"manifest suffix must resolve exactly once: {suffix!r}; got {len(matches)}"
        )
    return matches[0]


def load_expected(manifest_path: Path) -> dict:
    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text())
    if data.get("task") != "D1-01" or data.get("limits", {}).get("N") != 8:
        raise IntakeError("expected the frozen D1-01 manifest with N=8")
    frozen = data.get("frozen_file_sha256")
    if not isinstance(frozen, dict):
        raise IntakeError("manifest lacks frozen_file_sha256")

    inputs = {
        role: _unique_suffix_hash(frozen, "/" + name)
        for role, name in INPUT_ROLES.items()
    }
    components = {
        role: _unique_suffix_hash(frozen, suffix)
        for role, suffix in COMPONENT_SUFFIXES.items()
    }
    queries = {
        f"{case}/{query}": _unique_suffix_hash(
            frozen, f"/results/raw/D1-01/generated/{case}/{query}.smt2"
        )
        for case in CASES for query in QUERIES
    }
    provenance = data.get("historical_provenance", {})
    for key in ("payy_B_revision", "nargo", "noirc"):
        if not provenance.get(key):
            raise IntakeError(f"manifest lacks historical_provenance.{key}")
    return {
        "manifest_sha256": sha256(manifest_path),
        "inputs": inputs,
        "components": components,
        "queries": queries,
        "historical_provenance": provenance,
        "limits": data["limits"],
    }


def _validate_paths(actual_items, expected: dict[str, str], category: str) -> list[dict]:
    checks = []
    for role, path in actual_items:
        record = {
            "category": category,
            "role": role,
            "name": path.name,
            "expected_sha256": expected[role],
        }
        if not path.is_file():
            record.update(status="MISSING", reason_code="REQUIRED_ARTIFACT_MISSING")
        else:
            actual = sha256(path)
            record["actual_sha256"] = actual
            if actual == expected[role]:
                record["status"] = "MATCH"
            else:
                record.update(status="MISMATCH", reason_code="ARTIFACT_HASH_MISMATCH")
        checks.append(record)
    return checks


def validate_files(expected: dict, inputs: InputBundle, components: Components) -> list[dict]:
    return (
        _validate_paths(inputs.items(), expected["inputs"], "input")
        + _validate_paths(components.items(), expected["components"], "component")
    )


def _serialization_solve(ff, values, path=None):
    """Serialize the frozen FF query exactly, then abort before result handling."""
    if path is None:
        raise IntakeError("serialization-only sink requires an explicit output path")
    tailspec = sys.modules[ff.__class__.__module__]
    header = [
        "(set-logic QF_FF)",
        "(set-option :produce-models true)",
        f"(define-sort F () (_ FiniteField {tailspec.P}))",
    ]
    script = "\n".join(
        header + ff.lines
        + ["(check-sat)", "(get-value (" + " ".join(values) + "))"]
    ) + "\n"
    data = script.encode("utf-8")
    with Path(path).open("xb") as output:
        output.write(data)
    raise SerializationComplete(data)


def _forbid_solver(*_args, **_kwargs):
    raise IntakeError("NO_SOLVER_BOUNDARY_VIOLATION")


def _generate_one(compact, acir, messages, streams, query: str, outdir: Path) -> bytes:
    tailspec = compact.T
    original_solve = tailspec.FF.solve
    original_runner = tailspec._run_killable
    tailspec.FF.solve = _serialization_solve
    tailspec._run_killable = _forbid_solver
    try:
        try:
            compact.run_one(acir, messages, streams, query, outdir, 300, True)
        except SerializationComplete as complete:
            return complete.data
        raise IntakeError("legacy builder returned a solver result")
    finally:
        tailspec.FF.solve = original_solve
        tailspec._run_killable = original_runner


def _load_legacy_modules(components: Components):
    script_dir = str(Path(components.encoder).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import t22_v5_compact as compact  # pylint: disable=import-outside-toplevel

    if Path(compact.__file__).resolve() != Path(components.encoder).resolve():
        raise IntakeError("loaded compact encoder does not match requested path")
    if Path(compact.T.__file__).resolve() != Path(components.parser).resolve():
        raise IntakeError("loaded ACIR parser does not match requested path")
    return compact


def _parse_pair(compact, acir_path: Path, abi_path: Path, spec: dict):
    acir = compact.T.Acir(Path(acir_path).read_text())
    abi = json.loads(Path(abi_path).read_text())
    if "abi" in abi:
        abi = abi["abi"]
    messages, streams = compact.T.build(spec, acir, abi)
    if len(messages) != 8:
        raise IntakeError(f"expected N=8 messages, got {len(messages)}")
    if len(streams) != 2:
        raise IntakeError(f"expected two streams, got {len(streams)}")
    if any(len(words) != 8 or active is None for words, active in streams):
        raise IntakeError("each stream must bind eight words and an activation expression")
    return acir, messages, streams


def generate_queries(expected: dict, inputs: InputBundle, components: Components,
                     output_dir: Path) -> dict:
    """Generate six SMT files after all file and semantic validation succeeds."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise IntakeError(f"fresh output path required: {output_dir}")
    compact = _load_legacy_modules(components)
    spec = json.loads(Path(components.spec).read_text())
    required_derivation = {"mode": "walk", "records": {"2": 4, "3": 5, "4": 5}}
    if len(spec.get("streams", [])) != 2 or spec.get("derivation") != required_derivation:
        raise IntakeError("unexpected semantic specification")

    parsed = {
        "check_added": _parse_pair(
            compact, inputs.check_added_acir, inputs.check_added_abi, spec
        ),
        "running_flag": _parse_pair(
            compact, inputs.running_flag_acir, inputs.running_flag_abi, spec
        ),
    }
    output_dir.mkdir(parents=True)
    query_checks = []
    for case in CASES:
        case_dir = output_dir / case
        case_dir.mkdir()
        acir, messages, streams = parsed[case]
        for query in QUERIES:
            data = _generate_one(compact, acir, messages, streams, query, case_dir)
            actual = hashlib.sha256(data).hexdigest()
            expected_hash = expected["queries"][f"{case}/{query}"]
            query_checks.append({
                "slot": f"{case}/{query}",
                "file": f"{case}/{query}.smt2",
                "bytes": len(data),
                "expected_sha256": expected_hash,
                "actual_sha256": actual,
                "status": "MATCH" if actual == expected_hash else "MISMATCH",
                "solver_execution": "PROHIBITED_NOT_EXECUTED",
            })
    matched = all(row["status"] == "MATCH" for row in query_checks)
    return {
        "tool_status": "PASS" if matched else "BLOCKED",
        "artifact_status": "AVAILABLE" if matched else "BLOCKED",
        "reason_code": None if matched else "QUERY_HASH_MISMATCH",
        "query_checks": query_checks,
        "solver_processes_launched": 0,
    }


def perform_intake(manifest_path: Path, inputs: InputBundle, components: Components,
                   output_dir: Path,
                   generator: Callable = generate_queries) -> dict:
    expected = load_expected(manifest_path)
    checks = validate_files(expected, inputs, components)
    rejected = [row for row in checks if row["status"] != "MATCH"]
    base = {
        "task": "D1P-01",
        "manifest_sha256": expected["manifest_sha256"],
        "historical_provenance": expected["historical_provenance"],
        "limits": expected["limits"],
        "file_checks": checks,
        "security_verdict": "UNKNOWN",
    }
    if rejected:
        base.update(
            tool_status="PASS",
            artifact_status="BLOCKED",
            reason_codes=sorted({row["reason_code"] for row in rejected}),
            query_generation="NOT_STARTED_INPUT_VALIDATION_FAILED",
            solver_processes_launched=0,
        )
        return base

    generated = generator(expected, inputs, components, output_dir)
    base.update(generated)
    base["query_generation"] = "SERIALIZATION_ONLY_COMPLETE"
    base["runtime"] = {"python": sys.version, "platform": platform.platform()}
    manifest_output = Path(output_dir) / "intake-manifest.json"
    manifest_output.write_text(json.dumps(base, indent=2, sort_keys=True) + "\n")
    return base


def run_self_check() -> dict:
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import t22_v5_compact as compact  # pylint: disable=import-outside-toplevel
    count = compact.self_check()
    return {
        "task": "D1P-01",
        "check": "compact_walk",
        "category_vectors": count,
        "status": "PASS",
        "scope": "specification rewrite only; no ACIR summary or security verdict",
        "solver_processes_launched": 0,
    }


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    intake = sub.add_parser("intake", help="validate inputs and serialize six queries")
    intake.add_argument("--manifest", type=Path,
                        default=root / "metadata/d1/d1-01-execution-manifest.json")
    intake.add_argument("--protocol", type=Path,
                        default=root / "scripts/t22_v5_protocol.md")
    intake.add_argument("--encoder", type=Path,
                        default=root / "scripts/t22_v5_compact.py")
    intake.add_argument("--parser", type=Path,
                        default=root / "scripts/t22_v3_tailspec.py")
    intake.add_argument("--spec", type=Path,
                        default=root / "scripts/t22_specs/payy_agg_agg.json")
    intake.add_argument("--check-added-acir", type=Path, required=True)
    intake.add_argument("--check-added-abi", type=Path, required=True)
    intake.add_argument("--running-flag-acir", type=Path, required=True)
    intake.add_argument("--running-flag-abi", type=Path, required=True)
    intake.add_argument("--output", type=Path, required=True)
    sub.add_parser("self-check", help="run only the compact-walk equivalence check")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "self-check":
            result = run_self_check()
        else:
            inputs = InputBundle(
                args.check_added_acir,
                args.check_added_abi,
                args.running_flag_acir,
                args.running_flag_abi,
            )
            components = Components(args.protocol, args.encoder, args.parser, args.spec)
            result = perform_intake(args.manifest, inputs, components, args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("artifact_status", "AVAILABLE") != "BLOCKED" else 2
    except (IntakeError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({
            "task": "D1P-01",
            "tool_status": "BLOCKED",
            "artifact_status": "BLOCKED",
            "reason_code": "INTAKE_ERROR",
            "detail": str(error),
            "solver_processes_launched": 0,
            "security_verdict": "UNKNOWN",
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
