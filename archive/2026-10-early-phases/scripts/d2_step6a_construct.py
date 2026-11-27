#!/usr/bin/env python3
"""Construct and smoke-test D2 Step 6a baselines and transformations.

This is not a scored Gate A runner. It refuses to overwrite its output, uses
only exposed-development inputs, and preserves every construction row.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.composition_baselines_v1 import (  # noqa: E402
    BASELINE_NAMES,
    POLICY_SCHEMA,
    audit_existing_union,
    compose,
)
from bindcheck_d1.frontends.solidity_ast_v1_1 import extract  # noqa: E402
from bindcheck_d1.integrated_analyzer_v1 import analyze_integrated  # noqa: E402
from bindcheck_d1.static_analyzer_v1 import load_producer  # noqa: E402


DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-06a-construction-v1.json"
DEFAULT_OUTPUT = ROOT / "results/raw/D2-06A/construction-01"
COMMANDS: list[dict[str, Any]] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite generated evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_new_json(path: Path, value: Any) -> None:
    write_new(path, json_bytes(value))


def record(path: Path, base: Path = ROOT) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        display = resolved.relative_to(base.resolve()).as_posix()
    except ValueError:
        display = str(resolved)
    return {
        "path": display,
        "sha256": sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def run(
    name: str,
    argv: Sequence[str],
    *,
    cwd: Path,
    logs: Path,
    expected: set[int] = {0},
) -> subprocess.CompletedProcess[str]:
    started = time.monotonic()
    completed = subprocess.run(
        list(argv), cwd=cwd, text=True, capture_output=True, check=False
    )
    stdout_path = logs / f"{name}.stdout"
    stderr_path = logs / f"{name}.stderr"
    write_new(stdout_path, completed.stdout.encode())
    write_new(stderr_path, completed.stderr.encode())
    COMMANDS.append(
        {
            "name": name,
            "argv": list(argv),
            "cwd": str(cwd.resolve()),
            "exit_status": completed.returncode,
            "runtime_seconds": time.monotonic() - started,
            "stdout": record(stdout_path),
            "stderr": record(stderr_path),
        }
    )
    if completed.returncode not in expected:
        detail = completed.stderr[-2000:] or completed.stdout[-2000:]
        raise RuntimeError(f"{name} exited {completed.returncode}: {detail}")
    return completed


def verify_file(entry: Mapping[str, Any]) -> Path:
    path = Path(entry["path"])
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"input hash mismatch: {path}")
    return path


def load_protocol(path: Path) -> dict[str, Any]:
    protocol = json.loads(path.read_text())
    if protocol.get("schema") != "bindcheck.d2.step6a-construction/v1":
        raise ValueError("unexpected Step 6a construction protocol schema")
    if protocol.get("status") != "FROZEN_FOR_UNSCORED_CONSTRUCTION":
        raise ValueError("Step 6a construction protocol is not frozen")
    for entry in [
        protocol["step5"]["protocol"],
        protocol["step5"]["narrative"],
        *protocol["inputs"].values(),
        *protocol["tools"].values(),
        protocol["implementation"]["composition_module"],
        protocol["implementation"]["runner"],
    ]:
        verify_file(entry)
    required_arms = tuple(protocol["baseline_construction"]["required_arms"])
    if required_arms != BASELINE_NAMES:
        raise ValueError(f"protocol arm order mismatch: {required_arms!r}")
    return protocol


def token_replace(text: str, replacements: Mapping[str, str]) -> str:
    import re

    for old, new in replacements.items():
        text, count = re.subn(rf"\b{re.escape(old)}\b", new, text)
        if count == 0:
            raise ValueError(f"identifier replacement did not match: {old}")
    return text


def exact_replace(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"exact replacement expected once, observed {count}: {old!r}")
    return text.replace(old, new)


def transformed_sources(
    transform_id: str, producer: str, consumer: str
) -> tuple[str, str, dict[str, Any]]:
    if transform_id == "TR-IDENTIFIER-RENAME":
        producer_map = {
            "values": "payload",
            "active_count": "used_count",
            "expected": "reference_values",
        }
        consumer_map = {"publicInputs": "statementWords"}
        return (
            token_replace(producer, producer_map),
            token_replace(consumer, consumer_map),
            {
                "producer_identifier_map": producer_map,
                "consumer_identifier_map": consumer_map,
                "physical_public_word_map": {str(i): i for i in range(5)},
            },
        )
    if transform_id == "TR-HELPER-EXTRACTION":
        old = (
            "fn main(values: pub [Field; 4], active_count: pub u32, expected: [Field; 4]) {\n"
            "    for i in 0..4 {\n"
            "        if i < active_count {\n"
            "            assert(values[i] == expected[i]);\n"
            "        }\n"
            "    }\n"
            "}\n"
        )
        new = (
            "fn bind_active_prefix(values: [Field; 4], active_count: u32, expected: [Field; 4]) {\n"
            "    for i in 0..4 {\n"
            "        if i < active_count {\n"
            "            assert(values[i] == expected[i]);\n"
            "        }\n"
            "    }\n"
            "}\n\n"
            "fn main(values: pub [Field; 4], active_count: pub u32, expected: [Field; 4]) {\n"
            "    bind_active_prefix(values, active_count, expected);\n"
            "}\n"
        )
        return (
            exact_replace(producer, old, new),
            consumer,
            {
                "extracted_helper": "bind_active_prefix",
                "physical_public_word_map": {str(i): i for i in range(5)},
            },
        )
    if transform_id == "TR-EQUIVALENT-EXPRESSION":
        return (
            exact_replace(
                producer,
                "assert(values[i] == expected[i]);",
                "assert(expected[i] == values[i]);",
            ),
            consumer,
            {
                "rewrite": "equality operand commutation",
                "physical_public_word_map": {str(i): i for i in range(5)},
            },
        )
    if transform_id == "TR-MATCHED-PUBLIC-REORDER":
        return (
            exact_replace(
                producer,
                "fn main(values: pub [Field; 4], active_count: pub u32, expected: [Field; 4])",
                "fn main(active_count: pub u32, values: pub [Field; 4], expected: [Field; 4])",
            ),
            exact_replace(
                consumer,
                "accumulator = accumulator ^ publicInputs[i];",
                "accumulator = accumulator ^ publicInputs[i + 1];",
            ),
            {
                "logical_to_original_index": {
                    "payload[0]": 0,
                    "payload[1]": 1,
                    "payload[2]": 2,
                    "payload[3]": 3,
                    "active_count": 4,
                },
                "logical_to_transformed_index": {
                    "active_count": 0,
                    "payload[0]": 1,
                    "payload[1]": 2,
                    "payload[2]": 3,
                    "payload[3]": 4,
                },
                "physical_public_word_map": {
                    "0": 1,
                    "1": 2,
                    "2": 3,
                    "3": 4,
                    "4": 0,
                },
            },
        )
    raise ValueError(f"unknown transformation id: {transform_id}")


def prover_text(transform_id: str, active_count: int) -> str:
    values_name = "payload" if transform_id == "TR-IDENTIFIER-RENAME" else "values"
    count_name = "used_count" if transform_id == "TR-IDENTIFIER-RENAME" else "active_count"
    expected_name = "reference_values" if transform_id == "TR-IDENTIFIER-RENAME" else "expected"
    return (
        f'{values_name} = ["1", "2", "9", "10"]\n'
        f"{count_name} = {active_count}\n"
        f'{expected_name} = ["1", "2", "3", "4"]\n'
    )


def abi_layout(artifact: Path, aliases: Mapping[str, str]) -> dict[str, Any]:
    abi = json.loads(artifact.read_text())["abi"]
    public = []
    physical_index = 0
    for parameter in abi["parameters"]:
        if parameter.get("visibility") != "public":
            continue
        name = aliases.get(parameter["name"], parameter["name"])
        kind = parameter["type"]["kind"]
        if kind == "array":
            for offset in range(parameter["type"]["length"]):
                public.append(
                    {
                        "physical_index": physical_index,
                        "logical_word": f"{name}[{offset}]",
                        "type": parameter["type"]["type"],
                    }
                )
                physical_index += 1
        else:
            public.append(
                {
                    "physical_index": physical_index,
                    "logical_word": name,
                    "type": parameter["type"],
                }
            )
            physical_index += 1
    return {"public_words": public, "return_type": abi.get("return_type")}


def construction_policy(layout: Mapping[str, Any], transform_id: str) -> dict[str, Any]:
    aliases: dict[str, str] = {}
    if transform_id == "TR-IDENTIFIER-RENAME":
        aliases = {
            "payload": "values",
            "used_count": "active_count",
            "reference_values": "expected",
            "statementWords": "public_inputs",
        }
    return {
        "schema": POLICY_SCHEMA,
        "policy_id": "construction-map-only-no-reviewed-sigma",
        "version": "1",
        "review_status": "NOT_SUPPLIED",
        "policy_author": None,
        "policy_reviewer": None,
        "comparison_group": "d1p42-bound-prefix-consumer-all",
        "word_identities": {
            str(word["physical_index"]): word["logical_word"]
            for word in layout["public_words"]
        },
        "term_aliases": aliases,
        "obligations": [],
    }


def consumer_algebra_control(reordered: bool) -> dict[str, Any]:
    masks = [
        [0, 0, 0, 0],
        [1, 2, 3, 4],
        [2**256 - 1, 0, 2**128 + 7, 19],
        [0x1234, 0xABCDEF, 0xDEADBEEF, 0x55555555],
    ]
    rows = []
    for count, payload in enumerate(masks):
        original_words = payload + [2]
        transformed_words = [2] + payload if reordered else original_words
        original_value = 0
        transformed_value = 0
        for index in range(4):
            original_value ^= original_words[index]
            transformed_value ^= transformed_words[index + 1 if reordered else index]
        rows.append(
            {
                "id": count,
                "original": original_value,
                "transformed": transformed_value,
                "equal": original_value == transformed_value,
            }
        )
    return {
        "model": "exact 256-bit XOR algebra over four mapped payload words",
        "rows": rows,
        "all_equal": all(row["equal"] for row in rows),
    }


def compile_and_analyze_variant(
    *,
    transform_id: str,
    producer_source: str,
    consumer_source: str,
    nargo_toml: bytes,
    destination: Path,
    nargo: Path,
    solc: Path,
    logs: Path,
) -> dict[str, Any]:
    producer_dir = destination / "producer"
    producer_path = producer_dir / "src/main.nr"
    consumer_path = destination / "ConsumerAll.sol"
    write_new(producer_dir / "Nargo.toml", nargo_toml)
    write_new(producer_path, producer_source.encode())
    write_new(consumer_path, consumer_source.encode())
    run(
        f"{transform_id}-nargo-compile",
        [str(nargo), "compile", "--program-dir", str(producer_dir)],
        cwd=ROOT,
        logs=logs,
    )
    artifact = next((producer_dir / "target").glob("*.json"))
    ast_run = run(
        f"{transform_id}-solc-ast",
        [str(solc), "--combined-json", "ast", str(consumer_path)],
        cwd=ROOT,
        logs=logs,
    )
    ast_path = destination / "consumer.ast.json"
    write_new(ast_path, ast_run.stdout.encode())
    controls = []
    for control_id, active_count, expected_exit in (
        ("tail-change", 2, 0),
        ("active-change", 4, 1),
    ):
        prover_name = f"control_{control_id.replace('-', '_')}"
        write_new(
            producer_dir / f"{prover_name}.toml",
            prover_text(transform_id, active_count).encode(),
        )
        completed = run(
            f"{transform_id}-nargo-execute-{control_id}",
            [str(nargo), "execute", "-p", prover_name],
            cwd=producer_dir,
            logs=logs,
            expected={expected_exit},
        )
        controls.append(
            {
                "id": control_id,
                "expected_exit": expected_exit,
                "observed_exit": completed.returncode,
            }
        )
    result: dict[str, Any] = {
        "source": {
            "producer": record(producer_path),
            "consumer": record(consumer_path),
        },
        "build": {
            "producer_artifact": record(artifact),
            "consumer_ast": record(ast_path),
            "status": "PASS",
        },
        "producer_execution_controls": controls,
        "consumer_algebra_control": consumer_algebra_control(
            transform_id == "TR-MATCHED-PUBLIC-REORDER"
        ),
    }
    aliases = (
        {"payload": "values", "used_count": "active_count"}
        if transform_id == "TR-IDENTIFIER-RENAME"
        else {}
    )
    layout = abi_layout(artifact, aliases)
    result["abi_layout"] = layout
    try:
        producer = load_producer(artifact, producer_path)
        combined = json.loads(ast_path.read_text())
        source_key = next(
            key for key in combined["sources"] if key.endswith("ConsumerAll.sol")
        )
        relation = extract(
            ast_path, source_key, consumer_path, producer["public_leaves"]
        )
        relation_path = destination / "consumer-relation.json"
        write_new_json(relation_path, relation)
        integrated = analyze_integrated(
            artifact,
            consumer_path,
            relation_path,
            f"d2-06a-{transform_id}",
            producer_source=producer_path,
            role_binding=False,
        )
        integrated_path = destination / "integrated-analysis.json"
        write_new_json(integrated_path, integrated)
        arms = compose(integrated, construction_policy(layout, transform_id))
        arms_path = destination / "composition-arms.json"
        write_new_json(arms_path, arms)
        result["analysis"] = {
            "status": integrated["support_status"],
            "relation": record(relation_path),
            "integrated": record(integrated_path),
            "composition_arms": record(arms_path),
            "warning_rules": [warning["rule"] for warning in integrated["warnings"]],
            "semantic_ids": {
                arm: sorted(
                    candidate["semantic_id"]
                    for candidate in arms["baselines"][arm]["candidates"]
                )
                for arm in BASELINE_NAMES
            },
        }
    except (OSError, StopIteration, TypeError, ValueError) as error:
        result["analysis"] = {
            "status": "UNSUPPORTED",
            "reason": f"{type(error).__name__}:{error}",
        }
    return result


def logical_layout(layout: Mapping[str, Any]) -> dict[str, Any]:
    return {
        word["logical_word"]: word["type"] for word in layout["public_words"]
    }


def construct_transformations(
    protocol: Mapping[str, Any], raw: Path, nargo: Path, solc: Path
) -> dict[str, Any]:
    producer_path = verify_file(protocol["inputs"]["synthetic_producer_source"])
    consumer_path = verify_file(protocol["inputs"]["synthetic_consumer_source"])
    nargo_toml_path = verify_file(protocol["inputs"]["synthetic_nargo_toml"])
    original_producer = producer_path.read_text()
    original_consumer = consumer_path.read_text()
    planned = protocol["transformations"]
    original = compile_and_analyze_variant(
        transform_id="ORIGINAL",
        producer_source=original_producer,
        consumer_source=original_consumer,
        nargo_toml=nargo_toml_path.read_bytes(),
        destination=raw / "transformations/original",
        nargo=nargo,
        solc=solc,
        logs=raw / "logs",
    )
    original["id"] = "ORIGINAL"
    original["input"] = {
        "producer": record(producer_path),
        "consumer": record(consumer_path),
    }
    original_ids = original.get("analysis", {}).get("semantic_ids", {})
    original_layout = logical_layout(original["abi_layout"])
    rows = []
    for specification in planned:
        if specification["construction"] != "ATTEMPT":
            rows.append(
                {
                    "id": specification["id"],
                    "class": specification["class"],
                    "status": specification["construction"],
                    "reason": specification["reason"],
                    "attempted": False,
                    "accepted_for_transformation_stability": False,
                }
            )
            continue
        transform_id = specification["id"]
        transformed_producer, transformed_consumer, mapping = transformed_sources(
            transform_id, original_producer, original_consumer
        )
        destination = raw / "transformations" / transform_id
        output = compile_and_analyze_variant(
            transform_id=transform_id,
            producer_source=transformed_producer,
            consumer_source=transformed_consumer,
            nargo_toml=nargo_toml_path.read_bytes(),
            destination=destination,
            nargo=nargo,
            solc=solc,
            logs=raw / "logs",
        )
        write_new_json(destination / "mapping.json", mapping)
        controls_match = all(
            row["expected_exit"] == row["observed_exit"]
            for row in output["producer_execution_controls"]
        )
        layout_match = logical_layout(output["abi_layout"]) == original_layout
        algebra_match = output["consumer_algebra_control"]["all_equal"]
        semantic_ids = output.get("analysis", {}).get("semantic_ids")
        stability = (
            {
                arm: semantic_ids.get(arm) == original_ids.get(arm)
                for arm in BASELINE_NAMES
            }
            if semantic_ids is not None
            else None
        )
        semantically_controlled = controls_match and layout_match and algebra_match
        rows.append(
            {
                "id": transform_id,
                "class": specification["class"],
                "status": (
                    "SEMANTICALLY_CONTROLLED"
                    if semantically_controlled
                    else "CONTROL_FAILED"
                ),
                "attempted": True,
                "accepted_for_transformation_stability": (
                    semantically_controlled and semantic_ids is not None
                ),
                "transformation_argument": specification["transformation_argument"],
                "mapping": record(destination / "mapping.json"),
                "output": output,
                "control_summary": {
                    "producer_execution_vector_matches": controls_match,
                    "logical_abi_layout_matches": layout_match,
                    "consumer_algebra_matches": algebra_match,
                    "proof_generation": "NOT_RUN_CONSTRUCTION_ONLY",
                    "formal_equivalence_proof": "NOT_ESTABLISHED",
                },
                "semantic_identity_stability": stability,
                "claim_limit": (
                    "The source argument plus focused controls support use as a "
                    "construction control; they are not a general semantic-equivalence proof."
                ),
            }
        )
    return {
        "schema": "bindcheck.d2.step6a-transformation-ledger/v1",
        "status": "CONSTRUCTION_SMOKE_ONLY",
        "research_verdict": "UNKNOWN",
        "original": original,
        "planned_count": len(planned),
        "attempted_count": sum(row["attempted"] for row in rows),
        "preconstruction_rejected_count": sum(not row["attempted"] for row in rows),
        "semantically_controlled_count": sum(
            row["status"] == "SEMANTICALLY_CONTROLLED" for row in rows
        ),
        "stability_eligible_count": sum(
            row["accepted_for_transformation_stability"] for row in rows
        ),
        "rows": rows,
    }


def run_integrated_case(
    *,
    case_id: str,
    artifact: Path,
    consumer: Path,
    relation: Path,
    producer_source: Path | None,
    support_sources: Sequence[Path] = (),
) -> dict[str, Any]:
    return analyze_integrated(
        artifact,
        consumer,
        relation,
        case_id,
        producer_source=producer_source,
        producer_support_sources=support_sources,
        role_binding=producer_source is not None,
    )


def implementation_map_policy(record_value: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    identities: dict[str, str] = {}
    static = record_value.get("static_analysis")
    if isinstance(static, Mapping):
        for word in static.get("producer", {}).get("public_leaves", []):
            if isinstance(word.get("public_index"), int) and isinstance(word.get("path"), str):
                identities[str(word["public_index"])] = word["path"]
    return {
        "schema": POLICY_SCHEMA,
        "policy_id": "construction-map-only-no-reviewed-sigma",
        "version": "1",
        "review_status": "NOT_SUPPLIED",
        "policy_author": None,
        "policy_reviewer": None,
        "comparison_group": case_id,
        "word_identities": identities,
        "term_aliases": {},
        "obligations": [],
    }


def baseline_case_inputs(raw: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case_id, source in (
        ("GA-PAYY-TAIL-EARLIER", ROOT / "results/raw/D2-01-recovery-01/integrated/payy/earlier.json"),
        ("GA-PAYY-TAIL-CHECK-ADDED", ROOT / "results/raw/D2-01-recovery-01/integrated/payy/check-added.json"),
    ):
        cases.append({
            "case_id": case_id,
            "group": "GA-PAYY-TAIL",
            "record": json.loads(source.read_text()),
            "source": record(source),
        })
    m_dom = run_integrated_case(
        case_id="GA-WARPTOAD-MDOM",
        artifact=ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json",
        consumer=ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol",
        relation=ROOT / "results/raw/D1P-18/relation.json",
        producer_source=ROOT / "results/raw/D1P-21A/workspace/m-dom-sdom/backend/circuits/withdraw/src/main.nr",
        support_sources=[ROOT / "results/raw/D1P-21A/workspace/m-dom-sdom/backend/circuits/nargo_hashing/src/lib.nr"],
    )
    m_src = run_integrated_case(
        case_id="GA-WARPTOAD-MSRC",
        artifact=ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json",
        consumer=ROOT / "results/raw/D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol",
        relation=ROOT / "results/raw/D1P-21B/m-src-relation.json",
        producer_source=ROOT / "benchmarks/binding-mutants/baselines/warptoad-withdraw-main.nr",
        support_sources=[ROOT / "benchmarks/binding-mutants/baselines/warptoad-nargo-hashing-lib.nr"],
    )
    for case_id, value in (("GA-WARPTOAD-MDOM", m_dom), ("GA-WARPTOAD-MSRC", m_src)):
        output = raw / "baseline-smoke/integrated" / f"{case_id}.json"
        write_new_json(output, value)
        cases.append({"case_id": case_id, "group": case_id, "record": value, "source": record(output)})
    d1p43 = json.loads(
        (ROOT / "results/raw/D2-01-recovery-01/d1p43-rerun/ablation-and-role-target-results.json").read_text()
    )
    for example in d1p43["ablation_examples"]:
        case_id = f"GA-WARPTOAD-RELATIONSHIP-{example['id']}"
        target = example["target"]
        if target == "warptoad-pinned":
            value = run_integrated_case(
                case_id=case_id,
                artifact=ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json",
                consumer=ROOT / "results/raw/D1P-19/workspace/pinned-source/backend/contracts/core/WarpToadCore.sol",
                relation=ROOT / "results/raw/D1P-18/relation.json",
                producer_source=ROOT / "benchmarks/binding-mutants/baselines/warptoad-withdraw-main.nr",
                support_sources=[ROOT / "benchmarks/binding-mutants/baselines/warptoad-nargo-hashing-lib.nr"],
            )
            source_path = raw / "baseline-smoke/integrated" / f"{case_id}.json"
            write_new_json(source_path, value)
        else:
            source_path = ROOT / "results/raw/D2-01-recovery-01/integrated/benchmark" / f"{target}.json"
            value = json.loads(source_path.read_text())
        cases.append({
            "case_id": case_id,
            "group": "GA-WARPTOAD-RELATIONSHIP",
            "record": value,
            "source": record(source_path),
            "historical_example_status": example["status"],
        })
    return cases


def construct_baseline_smoke(raw: Path) -> dict[str, Any]:
    cases = baseline_case_inputs(raw)
    rows = []
    for item in cases:
        output = compose(
            item["record"],
            implementation_map_policy(item["record"], item["case_id"]),
        )
        output_path = raw / "baseline-smoke/arms" / f"{item['case_id']}.json"
        write_new_json(output_path, output)
        for arm_name, arm in output["baselines"].items():
            rows.append({
                "case_id": item["case_id"],
                "group": item["group"],
                "arm": arm_name,
                "construction_status": arm["status"],
                "scoring_readiness": arm["scoring_readiness"],
                "candidate_count": len(arm["candidates"]),
                "composition_runtime_seconds": arm["composition_runtime_seconds"],
                "policy_review_status": output["policy"]["review_status"],
                "source": item["source"],
                "output": record(output_path),
                "scored": False,
            })
    expected = len(cases) * len(BASELINE_NAMES)
    if len(rows) != expected:
        raise AssertionError("baseline construction denominator mismatch")
    return {
        "schema": "bindcheck.d2.step6a-baseline-smoke/v1",
        "status": "CONSTRUCTION_SMOKE_ONLY",
        "research_verdict": "UNKNOWN",
        "case_appearances": len(cases),
        "arm_count": len(BASELINE_NAMES),
        "planned_case_arms": expected,
        "construction_status_counts": dict(Counter(row["construction_status"] for row in rows)),
        "scoring_readiness_counts": dict(Counter(row["scoring_readiness"] for row in rows)),
        "rows": rows,
        "limits": [
            "Case appearances are not independent families and are not deduplicated scored cases.",
            "No reviewed sigma was supplied; strong-simple policy checks and equal-policy scoring remain unresolved.",
            "Candidate counts are smoke observations, not detections, misses, precision, or recall.",
        ],
    }


def information_budget_matrix() -> dict[str, Any]:
    rows = [
        ["producer-only", True, False, False, False, False, False, "existing producer warning output"],
        ["consumer-only", False, True, False, False, False, False, "existing consumer warning output"],
        ["unjoined-union", True, True, False, False, False, False, "set union; no synthesis"],
        ["basic-structural-composition", True, True, True, False, False, False, "positional occurrence/dataflow"],
        ["strong-simple-composition", True, True, True, True, True, "INTERFACE_SUPPORTED_BUT_NOT_SUPPLIED", "joins and direct obligations"],
        ["full-bindcheck", True, True, True, True, True, "RECORDED_NOT_CONSUMED", "frozen integrated output"],
    ]
    keys = ["arm", "producer_facts", "consumer_facts", "exact_mapping", "conditional_facts", "identities_annotations", "reviewed_policy", "method"]
    return {
        "schema": "bindcheck.d2.step6a-information-budget/v1",
        "status": "UNRESOLVED_EQUAL_POLICY_INTERFACE",
        "rows": [dict(zip(keys, row, strict=True)) for row in rows],
        "strong_vs_full_shared_implementation_facts": True,
        "strong_vs_full_equal_reviewed_policy_consumption": False,
        "step7_blocker": (
            "A human-authored/reviewed sigma is absent, and the current full analyzer "
            "does not consume the generic direct-obligation object supported by strong simple composition."
        ),
        "scored_comparison_allowed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    protocol_path = args.protocol.resolve()
    raw = args.output.resolve()
    if raw.exists():
        raise SystemExit(f"refusing to overwrite output namespace: {raw}")
    started = time.monotonic()
    protocol = load_protocol(protocol_path)
    raw.mkdir(parents=True)
    nargo = verify_file(protocol["tools"]["nargo_beta22"])
    solc = verify_file(protocol["tools"]["solc_0_8_29"])
    run("nargo-version", [str(nargo), "--version"], cwd=ROOT, logs=raw / "logs")
    run("solc-version", [str(solc), "--version"], cwd=ROOT, logs=raw / "logs")
    union_source = json.loads(verify_file(protocol["inputs"]["d1p43_ablation_result"]).read_text())
    union_audit = audit_existing_union(union_source)
    write_new_json(raw / "union-audit.json", union_audit)
    transformations = construct_transformations(protocol, raw, nargo, solc)
    write_new_json(raw / "transformation-ledger.json", transformations)
    baseline_smoke = construct_baseline_smoke(raw)
    write_new_json(raw / "baseline-smoke-summary.json", baseline_smoke)
    budgets = information_budget_matrix()
    write_new_json(raw / "information-budget-matrix.json", budgets)
    write_new_json(raw / "commands.json", COMMANDS)
    elapsed = time.monotonic() - started
    outputs = {
        name: record(raw / name, raw)
        for name in (
            "union-audit.json",
            "transformation-ledger.json",
            "baseline-smoke-summary.json",
            "information-budget-matrix.json",
            "commands.json",
        )
    }
    manifest = {
        "schema": "bindcheck.d2.step6a-run-manifest/v1",
        "created_at_utc": utc_now(),
        "status": "CONSTRUCTION_SMOKE_ONLY",
        "research_verdict": "UNKNOWN",
        "protocol": record(protocol_path),
        "repository": {
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True).strip()),
        },
        "platform": {"platform": platform.platform(), "machine": platform.machine(), "python": sys.version},
        "tools": {"nargo": record(nargo), "solc": record(solc), "python": record(Path(sys.executable))},
        "outputs": outputs,
        "cost_accounting": {
            "runner_elapsed_seconds": elapsed,
            "subprocess_call_count": len(COMMANDS),
            "subprocess_runtime_seconds": sum(command["runtime_seconds"] for command in COMMANDS),
            "composition_runtime_seconds": sum(row["composition_runtime_seconds"] for row in baseline_smoke["rows"]),
            "shared_extraction": "performed once per integrated input or generated variant",
            "arm_specific_cost": "composition runtime recorded per arm",
            "proof_calls": 0,
            "network_calls": 0,
            "human_minutes": None,
            "human_minutes_note": "No human activity was measured by this automated runner; do not impute zero or saved time.",
            "agent_activity": "Disclosed in the Step 6a handoff; not converted to human time.",
        },
        "resource_budget": protocol["resource_budget"],
        "scored": False,
    }
    write_new_json(raw / "run-manifest.json", manifest)
    summary = {
        "schema": "bindcheck.d2.step6a-run-summary/v1",
        "status": "COMPLETE_CONSTRUCTION_SMOKE_ONLY",
        "research_verdict": "UNKNOWN",
        "scored": False,
        "union_audit": union_audit["status"],
        "baseline_case_arms": baseline_smoke["planned_case_arms"],
        "baseline_construction_status_counts": baseline_smoke["construction_status_counts"],
        "transformation_counts": {
            "planned": transformations["planned_count"],
            "attempted": transformations["attempted_count"],
            "preconstruction_rejected": transformations["preconstruction_rejected_count"],
            "semantically_controlled": transformations["semantically_controlled_count"],
            "stability_eligible": transformations["stability_eligible_count"],
        },
        "equal_policy_information": budgets["status"],
        "outputs": {**outputs, "run-manifest.json": record(raw / "run-manifest.json", raw)},
        "elapsed_seconds": elapsed,
        "claim_limits": protocol["claim_limits"],
    }
    write_new_json(raw / "run-summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
