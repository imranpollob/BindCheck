#!/usr/bin/env python3
"""D1P-09 binding, N=8 shape, and selected-cone propagation audit.

This program is intentionally offline: it has no solver or child-process
interface.  Typed certificates are polynomial identities over decoded ACIR;
propagation is applied only to the recovered historical check-added cone.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.conservative_propagation_v1 import (  # noqa: E402
    Contradiction,
    State,
    opcode_witnesses,
)
from bindcheck_d1.frontends.acir_binary_v1 import abi_bindings, decode  # noqa: E402
from bindcheck_d1.frontends.acir_bindings_v1 import certify_bindings  # noqa: E402
from bindcheck_d1.frontends.binding_certificate_check_v1 import verify_tree  # noqa: E402
from bindcheck_d1.n8_consumer_shapes_v1 import shapes, validate_exhaustively  # noqa: E402


PINS = {
    "printed_acir": "1743e5dcdeaf36172fbbde66fda165e79db9081f8a3a980ee4bbf31f61a2875a",
    "abi": "8b288933d3330874c2e5c9b00443d6b0748302fce46d5aedf7ece6536b3cbebb",
    "producer_program": "e7b5731ca7a9e09a2bd5bf7b04e66b63cf4c3a8e7b7bdc9bd6655dd132985c61",
    "producer_scaled_source": "af9df5073230c040b1c7cb31ca31b2521b5485b8bc3ff566e915ad84d710632b",
    "forwarding_program_n1000": "89c1d5d6732e31df477a8ca7ad4b1f0ed9af0c3b3b75216d9e584526a0eb6d1e",
    "producer_source_n1000": "3fd7c851050853339d7b45a71ed52fb17136202514792739817e2dcab30cfae9",
    "forwarding_source_n1000": "5e6493eb16e14f4aa47f206b3e39f5168e7647be8bb1a66c624f019ea8a5b624",
    "consumer_source": "7062065cc95f447fea8bb28242d51c836c3cf9e39f1625180ecf9c240a5ffd8f",
    "legacy_parser": "81a1cd43cd3e6e735dc325535f05d9b2a88c6c9794b434ab53e834061ff700c8",
    "producer_spec": "dd7e17ed2c9cd74000182ea613184a53f86bd1944f86a5c5cc8016663a203e1c",
    "partition_checker": "ecdcb5b8192c2354e660ccea041af7667876802988a516ba9fe977b6dd6c6ae2",
    "specializer": "afb0d15492b8b5aafdba1a52a18b11a96fe7a02485111083ae7b8f4a1b1cf9c3",
    "claude_propagator_reviewed": "0957b5f15e11c255577e6b6603bb52b742f326e55fbce6425f1cd29ab484e7f2",
}
PAYY_REVISION = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
EVIDENCE_REVISION = "7d098cd393c5cc8609765b663d393fcaebf24aeb"
OUTER = tuple(range(1275, 1283))
STREAMS = (
    {"activation": 508, "words": tuple(range(511, 519))},
    {"activation": 1143, "words": tuple(range(2293, 2301))},
)
CELLS = ("inactive", "active_empty", "length_4", "length_5", "truncated_8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path: Path, expected: str, role: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{role} hash mismatch: {actual} != {expected}")


def load_module(path: Path, name: str, expected_hash: str):
    require_hash(path, expected_hash, name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: object, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True,
                               separators=(",", ":") if compact else None,
                               indent=None if compact else 2) + "\n")


def typed_certificate(path: Path, output: Path) -> tuple[dict, dict, int, dict]:
    program = decode(path)
    circuit = program["functions"][0]
    table = abi_bindings(program["abi"], circuit)
    certificate = certify_bindings(program, table)
    checked = verify_tree(circuit, certificate)
    write_json(output, certificate, compact=True)
    inventory = {
        "identity": program["identity"],
        "current_witness_index": circuit["current_witness_index"],
        "addressable_witness_ids": circuit["current_witness_index"] + 1,
        "opcode_count": len(circuit["opcodes"]),
        "opcode_counts": dict(sorted(Counter(op["kind"] for op in circuit["opcodes"]).items())),
        "public_parameters": circuit["public_parameters"],
        "private_parameter_count": len(circuit["private_parameters"]),
        "certificate_path": str(output),
        "certificate_sha256": sha256(output),
        "certificate_equalities_checked": checked,
    }
    return program, table, checked, inventory


def shape_documents() -> tuple[list[dict], dict]:
    rows = []
    for shape in shapes():
        fixed = shape.fixed_positions
        rows.append({
            "id": shape.identifier,
            "kinds": list(shape.kinds),
            "records": list(shape.records),
            "predicate": " and ".join(
                f"outer_message[{position}] == {kind}"
                for position, kind in sorted(fixed.items())
            ),
            "fixed_kind_positions": {str(position): kind
                                     for position, kind in sorted(fixed.items())},
            "symbolic_payload_positions": sorted(
                set(range(8)) - set(fixed)
            ),
            "producer_outer_witness_bindings": {
                str(position): OUTER[position] for position in sorted(fixed)
            },
            "consumer_public_input_positions": {
                str(position): 3 + position for position in sorted(fixed)
            },
        })
    return rows, validate_exhaustively()


def single_cell_facts(cell: str, stream: dict[str, object]) -> tuple[dict[int, int], dict[int, str], set[int]]:
    activation = int(stream["activation"])
    words = tuple(int(value) for value in stream["words"])
    fixed: dict[int, int] = {}
    basis: dict[int, str] = {}
    if cell == "inactive":
        fixed[activation] = 0
        basis[activation] = "cell predicate is activation == 0"
        witnesses = {activation}
    elif cell == "active_empty":
        witnesses = {activation, words[0]}
    elif cell == "length_4":
        fixed[words[0]] = 2
        basis[words[0]] = "cell predicate contains first word == 2"
        witnesses = {activation, words[0], words[4]}
    elif cell == "length_5":
        # The complete predicate says 3 OR 4; choosing either is forbidden.
        witnesses = {activation, words[0], words[5]}
    elif cell == "truncated_8":
        # Neither branch nor a member of any valid-kind disjunction is chosen.
        witnesses = {activation, words[0], words[4], words[5]}
    else:
        raise ValueError(cell)
    return fixed, basis, witnesses


def validate_cell_implications(partition_module) -> dict[str, object]:
    records = partition_module.load_records()
    observations = {cell: [] for cell in CELLS}
    counts = Counter()
    for active in (False, True):
        for words in itertools.product(partition_module.ALPHABET, repeat=8):
            cell = partition_module.classify(words, active, records)
            counts[cell] += 1
            observations[cell].append((active, words))
    checks = {}
    for cell, models in observations.items():
        checks[cell] = {
            "active_boolean_class": (models[0][0]
                                     if all(model[0] == models[0][0] for model in models)
                                     else None),
            "word_constants": {
                str(index): models[0][1][index]
                for index in range(8)
                if all(model[1][index] == models[0][1][index] for model in models)
            },
            "enumerated_models": len(models),
        }
    expected = {
        "inactive": {"active_boolean_class": False, "word_constants": {}},
        "active_empty": {"active_boolean_class": True, "word_constants": {}},
        "length_4": {"active_boolean_class": True, "word_constants": {"0": 2}},
        "length_5": {"active_boolean_class": True, "word_constants": {}},
        "truncated_8": {"active_boolean_class": True, "word_constants": {}},
    }
    for cell, wanted in expected.items():
        for key, value in wanted.items():
            if checks[cell][key] != value:
                raise AssertionError((cell, key, checks[cell][key], value))
    return {
        "enumeration_alphabet": list(partition_module.ALPHABET),
        "counts": dict(sorted(counts.items())),
        "implications": checks,
        "propagation_policy": (
            "active_boolean_class=True means only that the field activation is nonzero; "
            "it is retained as a predicate and never fixed to field value 1; "
            "disjunction members are never selected; only inactive activation=0 "
            "and length_4 first-word=2 are propagated"
        ),
    }


def run_case(
    case_id: str,
    family: str,
    predicate: str,
    fixed: dict[int, int],
    basis: dict[int, str],
    predicate_witnesses: set[int],
    indexed: list[tuple[int, tuple]],
    original_witnesses: set[int],
    protected: set[int],
) -> dict:
    started = time.perf_counter()
    try:
        state = State(indexed, fixed, basis, protected).run()
        audit = state.audit(original_witnesses, predicate_witnesses, predicate)
        audit.update({"id": case_id, "family": family, "contradiction": None,
                      "unsupported_selected_operations": []})
    except Contradiction as error:
        audit = {
            "id": case_id,
            "family": family,
            "status": "IMPOSSIBLE_BY_EXACT_PROPAGATION",
            "case_predicate_retained_verbatim": predicate,
            "contradiction": {"location": str(error.location), "reason": error.reason},
            "unsupported_selected_operations": [],
        }
    audit["propagation_seconds"] = time.perf_counter() - started
    return audit


def summary_row(case: dict) -> dict:
    if case["contradiction"] is not None:
        return {
            "id": case["id"], "family": case["family"],
            "status": case["status"], "contradiction": case["contradiction"],
            "unsupported_selected_operations": case["unsupported_selected_operations"],
            "propagation_seconds": case["propagation_seconds"],
        }
    return {
        "id": case["id"],
        "family": case["family"],
        "status": case["status"],
        "contradiction": None,
        "unsupported_selected_operations": case["unsupported_selected_operations"],
        "original_opcodes": case["original"]["opcodes"],
        "residual_original_opcodes": case["residual"]["original_opcodes"],
        "original_witnesses": case["original"]["witnesses"],
        "residual_relation_witnesses": case["residual"]["relation_witnesses"],
        "residual_with_case_and_reconstruction_witnesses": (
            case["residual"]["with_case_and_reconstruction_witnesses"]
        ),
        "original_ranges": case["original"]["range_constraints"],
        "residual_ranges": case["residual"]["range_constraints"],
        "retained_interface_equalities": len(
            case["residual"]["retained_interface_equalities"]
        ),
        "retained_interface_relations": len(
            case["residual"]["retained_interface_relations"]
        ),
        "derived_memory_equalities": case["residual"]["derived_memory_equalities"],
        "assigned_witnesses": len(case["assignment_reasons"]),
        "reduction_reason_counts": case["reduction_reason_counts"],
        "propagation_seconds": case["propagation_seconds"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--producer-program", type=Path, required=True)
    parser.add_argument("--producer-source", type=Path, required=True)
    parser.add_argument("--forwarding-program-n1000", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--compile-record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.metadata.mkdir(parents=True, exist_ok=True)

    paths = {
        "printed_acir": ROOT / "results/artifacts/d1-n8/b_agg_agg_check_added_.compile.stdout",
        "abi": ROOT / "results/artifacts/d1-n8/b_agg_agg_check_added_.abi.json",
        "producer_spec": ROOT / "scripts/t22_specs/payy_agg_agg.json",
        "legacy_parser": ROOT / "scripts/t22_v3_tailspec.py",
        "partition_checker": ROOT / "scripts/d1p_03_partition_check.py",
        "specializer": ROOT / "scripts/d1p_04_specialize.py",
        "producer_source_n1000": args.source_root / "noir/agg_agg/src/main.nr",
        "forwarding_source_n1000": args.source_root / "noir/agg_final/src/main.nr",
        "consumer_source": args.source_root / "eth/contracts/rollup3/RollupV1.sol",
    }
    for role, expected in PINS.items():
        if role in paths:
            require_hash(paths[role], expected, role)
    require_hash(args.producer_program, PINS["producer_program"], "producer_program")
    require_hash(args.producer_source, PINS["producer_scaled_source"], "producer_scaled_source")
    require_hash(args.forwarding_program_n1000, PINS["forwarding_program_n1000"],
                 "forwarding_program_n1000")

    compile_record = json.loads(args.compile_record.read_text())
    if compile_record.get("status") != "BLOCKED" or compile_record.get("exit_status") != 101:
        raise ValueError("unexpected N=8 forwarding compile record")

    producer_certificate_path = args.output / "producer-n8-binding-certificate.json"
    producer_program, producer_table, producer_checked, producer_inventory = typed_certificate(
        args.producer_program, producer_certificate_path
    )
    forwarding_certificate_path = args.output / "forwarding-n1000-binding-certificate.json"
    forwarding_program, forwarding_table, forwarding_checked, forwarding_inventory = typed_certificate(
        args.forwarding_program_n1000, forwarding_certificate_path
    )
    recovered_abi = json.loads(paths["abi"].read_text())
    if producer_program["abi"] != recovered_abi:
        raise ValueError("local full producer artifact ABI differs from recovered evidence ABI")

    shape_rows, shape_validation = shape_documents()
    shape_document = {
        "task": "D1P-09",
        "scope": "successful N=8 consumer decoding only; payloads symbolic",
        "generator_sha256": sha256(ROOT / "src/bindcheck_d1/n8_consumer_shapes_v1.py"),
        "shapes": shape_rows,
        "validation": shape_validation,
        "separate_guards": {
            "state": ["root equality", "height monotonicity", "mint registry", "funded token state"],
            "verifier": ["enabled exact verification key", "registered message length 8",
                         "proof accepted for exact public-input vector"],
            "commit": ["verifyCommitHash is a source-level placeholder in the pinned consumer"],
            "execution": ["onlyProver", "validator signatures", "outer transaction rollback"],
        },
        "semantics": {
            "failed_transfer": "scan may continue with no committed transfer effect",
            "later_revert": "rolls back earlier mint spent-writes and successful token effects",
            "zero_value_mint": "successful registry match still writes spent=true",
            "kind_4": "consumer-invalid even though producer export grammar accepts it",
        },
    }
    shapes_path = args.output / "n8-consumer-shapes.json"
    write_json(shapes_path, shape_document)

    tail = load_module(paths["legacy_parser"], "d1p09_legacy_parser", PINS["legacy_parser"])
    partition = load_module(paths["partition_checker"], "d1p09_partition", PINS["partition_checker"])
    specializer = load_module(paths["specializer"], "d1p09_specializer", PINS["specializer"])
    cell_validation = validate_cell_implications(partition)
    acir = tail.Acir(paths["printed_acir"].read_text())
    producer_spec = json.loads(paths["producer_spec"].read_text())
    messages, streams = tail.build(producer_spec, acir, recovered_abi)
    if tuple(next(iter(tail.expr_wits(expression))) for expression in messages) != OUTER:
        raise ValueError("outer witness mapping changed")
    observed_streams = tuple({
        "activation": next(iter(tail.expr_wits(activation))),
        "words": tuple(next(iter(tail.expr_wits(word))) for word in words),
    } for words, activation in streams)
    if observed_streams != STREAMS:
        raise ValueError(f"stream mapping changed: {observed_streams}")
    seeds = set(OUTER)
    for stream in STREAMS:
        seeds.add(int(stream["activation"]))
        seeds.update(stream["words"])
    selected, cone_witnesses = tail.cone(acir, seeds)
    indexed = [(index, acir.ops[index]) for index in selected]
    unsupported_selected = [(index, acir.ops[index][0]) for index in selected
                            if acir.ops[index][0] not in State.SUPPORTED]
    if unsupported_selected:
        raise ValueError(f"selected cone has unsupported opcodes: {unsupported_selected[:8]}")

    cases = [run_case("baseline", "unspecialized", "true", {}, {}, set(),
                      indexed, cone_witnesses, seeds)]
    for shape in shape_rows:
        fixed = {OUTER[int(position)]: value
                 for position, value in shape["fixed_kind_positions"].items()}
        basis = {witness: f"complete consumer shape {shape['id']} fixes this reached kind"
                 for witness in fixed}
        cases.append(run_case(shape["id"], "consumer_shape", shape["predicate"],
                              fixed, basis, set(fixed), indexed, cone_witnesses, seeds))
    for cell in specializer.cell_pairs():
        fixed: dict[int, int] = {}
        basis: dict[int, str] = {}
        predicate_witnesses: set[int] = set()
        for name, stream in ((cell["left"], STREAMS[0]), (cell["right"], STREAMS[1])):
            stream_fixed, stream_basis, stream_witnesses = single_cell_facts(name, stream)
            overlap = set(fixed) & set(stream_fixed)
            if overlap:
                raise AssertionError(overlap)
            fixed.update(stream_fixed)
            basis.update(stream_basis)
            predicate_witnesses |= stream_witnesses
        cases.append(run_case(cell["id"], "producer_cell", cell["predicate"],
                              fixed, basis, predicate_witnesses, indexed,
                              cone_witnesses, seeds))

    propagation_document = {
        "task": "D1P-09",
        "status": "OFFLINE_COMPONENT_VALIDATION_COMPLETE",
        "scope": "historical check-added selected cone only; not the full producer relation",
        "rules": {
            "source": "selectively adapted after review of Claude-worktree analysis/propagate.py",
            "source_sha256": PINS["claude_propagator_reviewed"],
            "implementation_sha256": sha256(
                ROOT / "src/bindcheck_d1/conservative_propagation_v1.py"
            ),
            "kept": ["exact field substitution", "unique affine witness reconstruction",
                     "ground range checking", "known-index memory-read equality"],
            "omitted_for_conservatism": ["small-domain two-variable enumeration"],
            "case_handling": "complete predicate retained; only separately validated implied constants substituted",
            "payload_policy": "no payload position fixed",
        },
        "input": {
            "printed_acir_sha256": sha256(paths["printed_acir"]),
            "selected_opcodes": len(selected),
            "selected_witnesses": len(cone_witnesses),
            "selected_opcode_counts": dict(sorted(Counter(acir.ops[index][0]
                                                          for index in selected).items())),
            "printed_nontransformed_inventory": {
                "opcodes_excluding_recursive_calls": len(acir.ops),
                "recursive_calls_excluded_from_ops": len(acir.recs),
                "unmodeled_blackboxes": acir.unmodeled,
            },
            "full_typed_inventory": producer_inventory,
            "full_relation_propagation_supported": False,
            "full_relation_blockers": [
                "two recursive-aggregation semantics are outside the historical selected cone",
                "91 Brillig calls are hints and are not treated as constraints by the printed parser",
                "Poseidon2Permutation semantics are not implemented by this propagator",
                "serialized and non-transformed printed assertion sets are not established equivalent",
            ],
        },
        "consumer_shape_validation": shape_validation,
        "producer_cell_implication_validation": cell_validation,
        "cases": cases,
    }
    propagation_path = args.output / "propagation-audit-full.json"
    write_json(propagation_path, propagation_document, compact=True)
    propagation_summary = {
        "task": "D1P-09",
        "scope": propagation_document["scope"],
        "input": propagation_document["input"],
        "rules": propagation_document["rules"],
        "consumer_shape_validation": shape_validation,
        "producer_cell_implication_validation": cell_validation,
        "cases": [summary_row(case) for case in cases],
        "full_audit": {
            "path": str(propagation_path),
            "sha256": sha256(propagation_path),
        },
        "interpretation": (
            "contradiction is exact only for the selected cone plus retained case predicate; "
            "every other case remains feasibility UNKNOWN regardless of reduction"
        ),
    }
    propagation_summary_path = args.output / "propagation-audit-summary.json"
    write_json(propagation_summary_path, propagation_summary)

    producer_binding = producer_program["functions"][0]
    forwarding_binding = forwarding_program["functions"][0]
    binding_manifest = {
        "task": "D1P-09",
        "scope": "one check-added N=8 AUTH/NONVAC preparation path",
        "source_revision": PAYY_REVISION,
        "recovered_evidence_revision": EVIDENCE_REVISION,
        "tooling_sha256": {
            "scripts/d1p_09_offline.py": sha256(Path(__file__).resolve()),
            "scripts/d1p_09_compile_agg_final.py": sha256(
                ROOT / "scripts/d1p_09_compile_agg_final.py"
            ),
            "src/bindcheck_d1/conservative_propagation_v1.py": sha256(
                ROOT / "src/bindcheck_d1/conservative_propagation_v1.py"
            ),
            "src/bindcheck_d1/n8_consumer_shapes_v1.py": sha256(
                ROOT / "src/bindcheck_d1/n8_consumer_shapes_v1.py"
            ),
            "src/bindcheck_d1/frontends/acir_binary_v1.py": sha256(
                ROOT / "src/bindcheck_d1/frontends/acir_binary_v1.py"
            ),
            "src/bindcheck_d1/frontends/acir_bindings_v1.py": sha256(
                ROOT / "src/bindcheck_d1/frontends/acir_bindings_v1.py"
            ),
            "src/bindcheck_d1/frontends/binding_certificate_check_v1.py": sha256(
                ROOT / "src/bindcheck_d1/frontends/binding_certificate_check_v1.py"
            ),
        },
        "artifacts": {
            "producer_n8_full_serialized_local_scratch": producer_inventory,
            "producer_n8_recovered_printed_acir": {
                "path": str(paths["printed_acir"]), "sha256": sha256(paths["printed_acir"]),
                "provenance": f"evidence commit {EVIDENCE_REVISION}",
            },
            "producer_n8_recovered_abi": {
                "path": str(paths["abi"]), "sha256": sha256(paths["abi"]),
                "matches_full_serialized_local_scratch": True,
            },
            "forwarding_n8": {
                "status": "BLOCKED_ABSENT",
                "compile_attempt_record": str(args.compile_record),
                "compile_attempt_record_sha256": sha256(args.compile_record),
                "compile_status": compile_record,
                "source_transformation_diff": {
                    "path": str(args.compile_record.parent / "source-transformation.diff"),
                    "sha256": sha256(args.compile_record.parent / "source-transformation.diff"),
                },
            },
            "forwarding_n1000_background_only": forwarding_inventory,
            "consumer_source": {
                "path": str(paths["consumer_source"]),
                "sha256": sha256(paths["consumer_source"]),
            },
        },
        "boundary_counts": {
            "producer_full_serialized": producer_inventory["opcode_count"],
            "producer_historical_selected_cone": len(selected),
            "producer_historical_selected_cone_witnesses": len(cone_witnesses),
            "producer_full_current_witness_index": producer_binding["current_witness_index"],
        },
        "mechanically_checked": [
            {
                "claim": "N=8 producer ABI allocates key hashes w1270..w1271, headers w1272..w1274, messages w1275..w1282",
                "basis": "typed ABI mapping and declaration identity on local full artifact; recovered ABI exact match",
            },
            {
                "claim": "N=8 recursive frame-0 messages map to w511..w518; frame-1 selected recursive public-input messages map to w2293..w2300; activations are w508 and w1143",
                "basis": f"{producer_checked} replayed typed binding equalities plus frozen spec resolution",
            },
            {
                "claim": "N=1000 agg_final recursive public inputs after two constants equal old_root,new_root,commit_hash,messages in order",
                "basis": f"background artifact only; {forwarding_checked} replayed typed binding equalities",
            },
            {
                "claim": "all 11 N=8 successful decoding predicates are exhaustive and disjoint for structurally valid decoding",
                "basis": "390625 equality/control-flow class assignments enumerated offline",
            },
        ],
        "source_supported_not_n8_artifact_checked": [
            "agg_final builds recursive public inputs as two fixed inner key hashes, then old_root,new_root,commit_hash,and every message",
            "agg_final exports old_root,new_root,commit_hash,messages as its public ABI and binds the supplied inner key hash",
            "RollupV1 consumes publicInputs[0:3] as headers and publicInputs[3:3+messages_length] as messages",
            "RollupV1 checks configured vector length, guards/state, scans messages, verifies the proof, then commits root/height",
        ],
        "external_assumptions": [
            "recursive proof soundness for the exact inner verification key and public-input vector",
            "outer verifier soundness for an exact N=8 agg_final verification key and public-input vector",
            "deployed consumer configuration registers that exact key with messages_length=8",
            "onlyProver and validator-signature attacker capabilities are admitted explicitly per query",
            "funded ordinary-token/no-substitution V2 state assumptions for effect analysis",
        ],
        "unresolved_links": [
            "no matching compiled N=8 agg_final artifact, verification key, proof, or deployed registration",
            "the failed one-shot compile leaves N=8 source-to-ACIR forwarding un-certified",
            "no proof that the historical selected cone equals or can replace the full producer relation",
            "no full-relation proof that active inner-frame records concatenate to the outer messages",
            "no authorization inference from payload equality or occurrence position",
            "no N=8-to-N=1000 artifact, key, proof, or deployment equivalence",
        ],
        "interface_map": [
            {"producer": "agg_agg.old_root / w1272", "agg_final": "old_root",
             "consumer": "publicInputs[0]", "grade": "producer mechanical; forwarding N=8 source-supported; consumer source-supported"},
            {"producer": "agg_agg.new_root / w1273", "agg_final": "new_root",
             "consumer": "publicInputs[1]", "grade": "producer mechanical; forwarding N=8 source-supported; consumer source-supported"},
            {"producer": "agg_agg.commit_hash / w1274", "agg_final": "commit_hash",
             "consumer": "publicInputs[2]", "grade": "producer mechanical; forwarding N=8 source-supported; consumer source-supported"},
            {"producer": "agg_agg.messages[i] / w(1275+i), 0<=i<8",
             "agg_final": "messages[i]", "consumer": "publicInputs[3+i]",
             "grade": "producer mechanical; forwarding N=8 source-supported; consumer source-supported"},
        ],
        "separation": {
            "permissions_P": "inner-frame permission occurrences; not inferred from consumer effects",
            "effects_E": "committed consumer mint spent-writes and successful funded token transfers after full call success",
            "obligations_O": "analyst policy over matching occurrences; not inferred from implementation behavior",
            "forbidden_inferences": ["inner-to-outer concatenation without full producer constraints",
                                     "payload equality implies authorization",
                                     "N=8 equivalence to N=1000"],
        },
    }
    binding_path = args.output / "binding-manifest.json"
    write_json(binding_path, binding_manifest)

    published = {
        args.metadata / "d1p-09-binding-manifest.json": binding_manifest,
        args.metadata / "d1p-09-consumer-shapes.json": shape_document,
        args.metadata / "d1p-09-propagation-audit.json": propagation_summary,
    }
    for path, document in published.items():
        write_json(path, document)
    final = {
        "task": "D1P-09",
        "status": "OFFLINE_PREPARATION_COMPLETE_WITH_FORWARDING_BLOCKER",
        "security_verdict": "UNKNOWN",
        "solver_calls": 0,
        "compile_calls": 0,
        "cases": Counter(row["family"] for row in cases),
        "outputs": {str(path): sha256(path) for path in (
            binding_path, shapes_path, propagation_summary_path, propagation_path,
            producer_certificate_path, forwarding_certificate_path, *published.keys()
        )},
    }
    write_json(args.output / "summary.json", final)
    print(json.dumps(final, indent=2, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
