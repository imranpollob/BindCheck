#!/usr/bin/env python3
"""Compile source mutations and verify that extraction changes without extractor edits."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from extract_relation import Extractor


SOURCE_NAME = "project/contracts/core/WarpToadCore.sol"
MUTATIONS = {
    "mint_beneficiary": (
        "_mint(_recipient, _amount - _relayerFee);",
        "_mint(_relayer, _amount - _relayerFee);",
    ),
    "remove_fee_guard": (
        'require(_relayerFee <= _maxFee, "_relayerFee is larger than _maxFee");',
        "// D1P-18 mutation: fee-cap guard removed.",
    ),
    "nullifier_write_key": (
        "nullifiers[_nullifier] = true;",
        "nullifiers[_localRoot] = true;",
    ),
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def success_paths(relation: dict[str, Any]) -> list[dict[str, Any]]:
    return [path for path in relation["paths"] if path["status"] == "success"]


def compile_variant(
    solcjs: Path,
    original_meta: dict[str, Any],
    variant: str,
    source: str,
    variant_dir: Path,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    build_input = copy.deepcopy(original_meta["input"])
    build_input["sources"][SOURCE_NAME]["content"] = source
    variant_id = f"d1p18-{variant}"
    standard_input_path = variant_dir / "standard-input.json"
    raw_output_path = variant_dir / "standard-output.json"
    standard_input_path.write_text(canonical(build_input) + "\n")
    solc_package = solcjs.resolve().parent
    wrapper = Path(__file__).with_name("compile_standard_json.js").resolve()
    command = ["node", str(wrapper), str(solc_package), str(standard_input_path), str(raw_output_path)]
    compiler = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if compiler.returncode != 0 or not raw_output_path.exists():
        raise RuntimeError(
            f"solcjs failed for {variant}: rc={compiler.returncode}, "
            f"stderr={compiler.stderr.decode(errors='replace')!r}"
        )
    output = json.loads(raw_output_path.read_text())
    errors = [
        item for item in output.get("errors", []) if item.get("severity") == "error"
    ]
    if errors:
        raise RuntimeError(f"solc errors for {variant}: {errors}")

    source_path = variant_dir / "WarpToadCore.sol"
    meta_path = variant_dir / "build-info.json"
    output_path = variant_dir / "build-info.output.json"
    source_path.write_text(source)
    write_json(meta_path, {
        "_format": original_meta.get("_format"),
        "id": variant_id,
        "solcLongVersion": original_meta["solcLongVersion"],
        "input": build_input,
    })
    write_json(output_path, {"_format": "hh-sol-build-info-1", "id": variant_id, "output": output})
    compile_record = {
        "command": command,
        "returncode": compiler.returncode,
        "stderr": compiler.stderr.decode(errors="replace"),
        "stdout": compiler.stdout.decode(errors="replace"),
        "error_count": len(errors),
        "warning_count": sum(
            item.get("severity") == "warning" for item in output.get("errors", [])
        ),
        "standard_input": {
            "bytes": standard_input_path.stat().st_size,
            "sha256": sha256_bytes(standard_input_path.read_bytes()),
        },
        "standard_output": {
            "bytes": raw_output_path.stat().st_size,
            "sha256": sha256_bytes(raw_output_path.read_bytes()),
        },
    }
    write_json(variant_dir / "compile.json", compile_record)
    return meta_path, output_path, source_path, compile_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-info", type=Path, required=True)
    parser.add_argument("--compiler-output", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--solcjs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = args.source.read_text()
    original_meta = json.loads(args.build_info.read_text())
    baseline = Extractor(args.build_info, args.compiler_output, args.source).extract()

    results: dict[str, Any] = {}
    for variant, (old, new) in MUTATIONS.items():
        occurrence_count = source.count(old)
        if occurrence_count != 1:
            raise AssertionError(
                f"{variant}: expected exactly one source occurrence, found {occurrence_count}"
            )
        mutated = source.replace(old, new)
        variant_dir = output_dir / variant
        variant_dir.mkdir(parents=True, exist_ok=True)
        meta_path, compiler_path, source_path, compile_record = compile_variant(
            args.solcjs.resolve(), original_meta, variant, mutated, variant_dir
        )
        source_sha256 = sha256_bytes(mutated.encode())
        relation = Extractor(
            meta_path,
            compiler_path,
            source_path,
            expected_source_sha256=source_sha256,
        ).extract()
        write_json(variant_dir / "relation.json", relation)
        # Full compiler input/output are reproducible from the archived input,
        # one recorded replacement, and pinned compiler. Retain hashes instead
        # of duplicating roughly 50 MiB per variant in the lane deliverable.
        for transient in [meta_path, compiler_path, variant_dir / "standard-input.json", variant_dir / "standard-output.json"]:
            transient.unlink()

        checks: list[dict[str, Any]] = []
        if variant == "mint_beneficiary":
            baseline_second = [
                path["committed"]["mints"][1]["beneficiary"]
                for path in success_paths(baseline)
                if len(path["committed"]["mints"]) == 2
            ]
            mutated_second = [
                path["committed"]["mints"][1]["beneficiary"]
                for path in success_paths(relation)
                if len(path["committed"]["mints"]) == 2
            ]
            checks = [
                {
                    "check": "baseline second fee-branch mint targets recipient",
                    "observed": baseline_second,
                    "pass": baseline_second == ["calldata._recipient", "calldata._recipient"],
                },
                {
                    "check": "mutated second fee-branch mint follows relayer resolution",
                    "observed": mutated_second,
                    "pass": mutated_second == ["msg.sender", "calldata._relayer"],
                },
            ]
        elif variant == "remove_fee_guard":
            guard = "<= calldata._maxFee"
            baseline_hits = sum(
                guard in item for path in baseline["paths"] for item in path["guards"]
            )
            mutated_hits = sum(
                guard in item for path in relation["paths"] for item in path["guards"]
            )
            baseline_fee_reverts = sum(
                path["status"] == "revert"
                and path["revert"]["reason"] == "_relayerFee is larger than _maxFee"
                for path in baseline["paths"]
            )
            mutated_fee_reverts = sum(
                path["status"] == "revert"
                and path["revert"]["reason"] == "_relayerFee is larger than _maxFee"
                for path in relation["paths"]
            )
            checks = [
                {
                    "check": "fee-cap guard and revert family present only in baseline",
                    "baseline_guard_occurrences": baseline_hits,
                    "mutated_guard_occurrences": mutated_hits,
                    "baseline_fee_revert_families": baseline_fee_reverts,
                    "mutated_fee_revert_families": mutated_fee_reverts,
                    "pass": baseline_hits > 0 and mutated_hits == 0
                    and baseline_fee_reverts == 1 and mutated_fee_reverts == 0,
                },
                {
                    "check": "removing guard removes exactly one path family",
                    "baseline_path_count": baseline["summary"]["path_count"],
                    "mutated_path_count": relation["summary"]["path_count"],
                    "pass": relation["summary"]["path_count"]
                    == baseline["summary"]["path_count"] - 1,
                },
            ]
        elif variant == "nullifier_write_key":
            def nullifier_keys(candidate: dict[str, Any]) -> list[str]:
                return sorted({
                    write["key"]
                    for path in success_paths(candidate)
                    for write in path["committed"]["storage_writes"]
                    if write["slot"] == "nullifiers"
                })

            baseline_keys = nullifier_keys(baseline)
            mutated_keys = nullifier_keys(relation)
            checks = [
                {
                    "check": "nullifier write key follows source mutation",
                    "baseline_keys": baseline_keys,
                    "mutated_keys": mutated_keys,
                    "pass": baseline_keys == ["calldata._nullifier"]
                    and mutated_keys == ["calldata._localRoot"],
                }
            ]
        if not checks or not all(check["pass"] for check in checks):
            raise AssertionError(f"{variant}: relation-change checks failed: {checks}")

        results[variant] = {
            "source_replacement": {"old": old, "new": new, "occurrences": occurrence_count},
            "source_sha256": source_sha256,
            "relation_sha256": sha256_bytes((variant_dir / "relation.json").read_bytes()),
            "compiler": compile_record,
            "summary": relation["summary"],
            "checks": checks,
            "all_checks_pass": True,
        }

    report = {
        "schema": "bindcheck.d1p18.source-mutation-tests.v1",
        "method": "source replacement followed by pinned solc compilation and unchanged extractor",
        "extractor_sha256": sha256_bytes(
            Path(__file__).with_name("extract_relation.py").read_bytes()
        ),
        "effect_model_sha256": sha256_bytes(
            Path(__file__).with_name("library_effect_models.v1.json").read_bytes()
        ),
        "baseline_source_sha256": sha256_bytes(source.encode()),
        "baseline_summary": baseline["summary"],
        "mutations": results,
        "all_checks_pass": True,
    }
    write_json(output_dir / "mutation-test-results.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
