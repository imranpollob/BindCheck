#!/usr/bin/env python3
"""D1P-21B variant-general extracted-consumer adapter.

This module preserves the D1P-20 implementation and evidence byte-for-byte.
It removes only the frozen path-shape assumption and binds source-extracted
configuration reads to the admitted state/environment supplied in Omega.
Unsupported IR and effect shapes still use the D1P-18/D1P-20 named,
fail-closed rejections.
"""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from bindcheck_d1 import joint_warptoad as manual
from bindcheck_d1.model_v2 import FIELD_MODULUS


HERE = Path(__file__).resolve().parent
D1P16 = HERE.parent / "d1p16"
D1P20 = HERE.parent / "d1p20"
for dependency in (D1P16, D1P20):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import joint_extracted as d1p20  # noqa: E402
from extract_relation import UnsupportedConstruct  # noqa: E402


CONSUMER_MODELS = d1p20.CONSUMER_MODELS
CONTROL_VARIANTS = d1p20.CONTROL_VARIANTS
INHERITED_EMITTER = d1p20._emit_extracted_consumer


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode()).hexdigest()


def relation_shape(relation: dict[str, Any]) -> dict[str, Any]:
    """Compute the observed shape, rather than accepting a claimed fixed shape."""
    paths = relation.get("paths")
    if not isinstance(paths, list) or not paths:
        raise UnsupportedConstruct("relation_paths", "D1P-21B:relation", "missing terminal paths")
    ids = [path.get("id") for path in paths]
    if any(not isinstance(path_id, str) or not path_id for path_id in ids):
        raise UnsupportedConstruct("path_id", "D1P-21B:relation", repr(ids))
    if len(ids) != len(set(ids)):
        raise UnsupportedConstruct("path_id", "D1P-21B:relation", "duplicate path id")
    statuses = [path.get("status") for path in paths]
    unsupported = sorted({status for status in statuses if status not in {"success", "revert"}})
    if unsupported:
        raise UnsupportedConstruct("path_status", "D1P-21B:relation", repr(unsupported))
    revert_paths = [path for path in paths if path["status"] == "revert"]
    all_reverts_commit_nothing = all(
        not path.get("committed", {}).get(kind)
        for path in revert_paths
        for kind in ("storage_writes", "mints", "burns", "transfers", "events")
    )
    return {
        "path_count": len(paths),
        "success_paths": statuses.count("success"),
        "revert_paths": statuses.count("revert"),
        "all_reverts_commit_nothing": all_reverts_commit_nothing,
    }


def load_extracted_relation(path: Path) -> dict[str, Any]:
    relation = json.loads(path.read_text())
    if relation.get("schema") != "bindcheck.d1p18.extracted-consumer-relation.v2":
        raise UnsupportedConstruct("relation_schema", str(path), str(relation.get("schema")))
    assertions = relation.get("pins", {}).get("assertions", {})
    if not assertions or not all(assertions.values()):
        raise UnsupportedConstruct("relation_pin", str(path), "one or more extractor pins failed")
    observed = relation_shape(relation)
    claimed = relation.get("summary")
    if claimed != observed:
        raise UnsupportedConstruct(
            "relation_shape", str(path), f"claimed={claimed!r}; observed={observed!r}"
        )
    if not observed["all_reverts_commit_nothing"]:
        raise UnsupportedConstruct(
            "rollback", str(path), "a revert path contains a committed effect"
        )
    return relation


def _collect_ir_reads(value: Any, storage: set[str], symbols: set[str]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_ir_reads(item, storage, symbols)
        return
    if not isinstance(value, dict):
        return
    if value.get("op") == "storage":
        storage.add(value["args"][0])
    if value.get("op") == "symbol":
        symbols.add(value["args"][0])
    for item in value.values():
        _collect_ir_reads(item, storage, symbols)


def manual_input_manifest(relation: dict[str, Any]) -> dict[str, Any]:
    """Update D1P-20's manifest to distinguish bindings from constants."""
    manifest = copy.deepcopy(d1p20.manual_input_manifest(relation))
    storage: set[str] = set()
    symbols: set[str] = set()
    _collect_ir_reads(relation, storage, symbols)
    manifest["schema"] = "bindcheck.d1p21b.manual-input-manifest/v1"
    manifest.pop("fixed_environment", None)
    manifest["configuration_bindings"] = [
        {
            "source_read": "pre.aztecWarptoadAddress",
            "relation_storage": "aztecWarptoadAddress",
            "omega_input": "fixed_pre_state_S0.aztec_warptoad_address",
            "classification": "SOURCE-EXTRACTED STORAGE READ BOUND TO ADMITTED STATE",
            "prior_d1p20_constant_removed": True,
        },
        {
            "source_read": "block.chainid",
            "omega_input": "environment.chain_id",
            "classification": "SOURCE-EXTRACTED ENVIRONMENT READ BOUND TO ADMITTED ENVIRONMENT",
            "prior_d1p20_constant_removed": True,
        },
        {
            "source_read": "pre.withdrawVerifier",
            "omega_input": "boundary_declarations[].declaration",
            "classification": "MANUAL RELATIONAL BOUNDARY TARGET; NO NUMERIC CONSTANT IN SMT",
            "prior_d1p20_constant_removed": False,
        },
    ]
    manifest["other_state_reads"] = sorted(storage - {"aztecWarptoadAddress"})
    manifest["other_environment_reads"] = sorted(
        symbol for symbol in symbols if symbol.startswith("block.") and symbol != "block.chainid"
    )
    manifest["environment_assumptions"] = [
        {
            "source_read": "msg.sender",
            "omega_input": "environment.msg_sender_value",
            "classification": "PINNED OWNED-LOCAL RELAYER SUBSTITUTION; NOT DEPLOYMENT CONFIGURATION",
        },
        {
            "source_read": "block.basefee",
            "omega_input": "symbolic basefee",
            "classification": "SYMBOLIC TRANSACTION ENVIRONMENT",
        },
    ]
    return manifest


def serialize_consumer_ir(relation: dict[str, Any]) -> dict[str, Any]:
    observed = relation_shape(relation)
    paths = [
        {
            "id": path["id"],
            "status": path["status"],
            "guards": copy.deepcopy(path["guards_ir"]),
            "revert": copy.deepcopy(path["revert"]),
            "committed": copy.deepcopy(path["committed"]),
            "tentative": copy.deepcopy(path["tentative"]),
            "rollback": path["rollback"],
        }
        for path in relation["paths"]
    ]
    return {
        "schema": "bindcheck.d1p21b.extracted-consumer-ir/v1",
        "classification": "EXTRACTED implementation relation",
        "source_relation_canonical_sha256": _canonical_sha256(relation),
        "serialized_paths_canonical_sha256": _canonical_sha256(paths),
        "source_relation_schema": relation["schema"],
        "pins": copy.deepcopy(relation["pins"]),
        "verifier_boundary": copy.deepcopy(relation["verifier_boundary"]),
        "paths": paths,
        "relation_shape": observed,
        "summary": copy.deepcopy(relation["summary"]),
        "manual_inputs": manual_input_manifest(relation),
        "policy": "not included; policy is serialized after implementation effects",
    }


def build_omega(
    artifact: Path,
    *,
    goal: str,
    s0: dict[str, Any],
    identities: dict[str, Any],
    consumer_model: str = "MANUAL",
    relation_path: Path | None = None,
    implementation_variant: str = "BASE",
    control_id: str | None = None,
    environment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if consumer_model not in CONSUMER_MODELS:
        raise ValueError(f"unknown consumer_model: {consumer_model}")
    if consumer_model == "MANUAL":
        if environment is not None:
            raise ValueError("MANUAL remains unchanged and does not accept an environment override")
        return manual.build_omega(
            artifact,
            goal=goal,
            s0=s0,
            identities=identities,
            implementation_variant=implementation_variant,
            control_id=control_id,
        )
    if implementation_variant != "BASE":
        raise UnsupportedConstruct(
            "extracted_implementation_variant",
            "D1P-21B:build_omega",
            "implementation variants are validation-only control transforms",
        )
    if relation_path is None:
        raise ValueError("EXTRACTED requires relation_path")
    if environment is None or "chain_id" not in environment:
        raise UnsupportedConstruct(
            "admitted_environment_binding",
            "D1P-21B:environment",
            "missing chain_id for source block.chainid read",
        )
    if "aztec_warptoad_address" not in s0:
        raise UnsupportedConstruct(
            "admitted_state_binding",
            "D1P-21B:fixed_pre_state_S0",
            "missing aztec_warptoad_address for source storage read",
        )
    base = manual.build_omega(
        artifact,
        goal=goal,
        s0=s0,
        identities=identities,
        implementation_variant="BASE",
        control_id=None,
    )
    base["environment"]["chain_id"] = int(environment["chain_id"])
    relation = load_extracted_relation(relation_path)
    ir = serialize_consumer_ir(relation)
    ir["source_relation_path"] = str(relation_path.resolve())
    ir["source_relation_file_sha256"] = hashlib.sha256(relation_path.read_bytes()).hexdigest()
    base["schema"] = "bindcheck.d1p21b.omega/v1"
    base["consumer_model"] = "EXTRACTED"
    base["consumer_T_mint"] = {
        "classification": "EXTRACTED",
        "automatic_extraction_claim": True,
        "claim_scope": "tested WarpToadCore.mint fragment only",
        "source_relation_sha256": ir["source_relation_file_sha256"],
        "relation": ir,
        "configuration_bindings": {
            "aztecWarptoadAddress": "fixed_pre_state_S0.aztec_warptoad_address",
            "block.chainid": "environment.chain_id",
        },
        "control_transform": (
            {
                "id": control_id,
                "classification": "D1P-14D validation-only implementation mutation",
                "policy_unchanged": True,
                "expected_goal": CONTROL_VARIANTS[control_id],
            }
            if control_id is not None
            else None
        ),
    }
    base["diagnostic_control"] = base["consumer_T_mint"]["control_transform"]
    return base


def _emit_extracted_consumer(
    lines: list[str], omega: dict[str, Any], *, backend_option: str
) -> dict[str, Any]:
    """Reuse the fail-closed D1P-20 IR lowering, replacing only input bindings."""
    start = len(lines)
    effects = INHERITED_EMITTER(lines, omega, backend_option=backend_option)
    chain_id = int(omega["environment"]["chain_id"])
    aztec_address = int(omega["fixed_pre_state_S0"]["aztec_warptoad_address"])
    replacements = {
        "(define-fun env_chain_id ()": (
            f"(define-fun env_chain_id () (_ BitVec 256) {manual._bv(chain_id)})"
        ),
        "(define-fun config_aztec_address ()": (
            f"(define-fun config_aztec_address () (_ BitVec 256) {manual._bv(aztec_address)})"
        ),
    }
    seen = set()
    for index in range(start, len(lines)):
        for prefix, replacement in replacements.items():
            if lines[index].startswith(prefix):
                lines[index] = replacement
                seen.add(prefix)
    if seen != set(replacements):
        raise UnsupportedConstruct(
            "configuration_binding",
            "D1P-21B:SMT",
            f"missing inherited definitions: {sorted(set(replacements) - seen)!r}",
        )
    return effects


def audit_extracted_query(
    omega: dict[str, Any], query: bytes, certificate: dict[str, Any], *, drop_producer: bool
) -> None:
    text = query.decode()
    ir = omega["consumer_T_mint"]["relation"]
    expected_ids = [path["id"] for path in ir["paths"]]
    if "; IMPLEMENTATION_SUMMARY MANUAL_ASSUMED" in text:
        raise ValueError("manual consumer summary leaked into EXTRACTED query")
    if text.count("; IMPLEMENTATION_RELATION EXTRACTED begin") != 1:
        raise ValueError("missing extracted implementation marker")
    if text.count("; PATH ") != len(expected_ids):
        raise ValueError("not all extracted path families were serialized")
    if ("serialized_path_ids" in certificate and
            certificate["serialized_path_ids"] != expected_ids):
        raise ValueError("serialized path order differs from extracted relation")
    if text.count("; CONSUMER_VERIFIER_ARGUMENT ") != 11:
        raise ValueError("recovered verifier-argument bridge count mismatch")
    for required in (
        "consumer_success",
        "consumer_revert",
        "rollback_holds",
        "; POLICY_EVALUATION begin",
        "(define-fun G1",
        "(define-fun G5",
    ):
        if required not in text:
            raise ValueError(f"missing extracted query marker: {required}")
    state_value = int(omega["fixed_pre_state_S0"]["aztec_warptoad_address"])
    chain_value = int(omega["environment"]["chain_id"])
    if f"(define-fun config_aztec_address () (_ BitVec 256) {manual._bv(state_value)})" not in text:
        raise ValueError("admitted aztecWarptoadAddress binding missing")
    if f"(define-fun env_chain_id () (_ BitVec 256) {manual._bv(chain_value)})" not in text:
        raise ValueError("admitted block.chainid binding missing")
    if hashlib.sha256(query).hexdigest() != certificate["query_sha256"]:
        raise ValueError("query hash mismatch")
    if not manual.balanced_smt_parentheses(query)["balanced"]:
        raise ValueError("query parentheses are not balanced")
    if not drop_producer and certificate["verifier_boundary"]["producer_witness_bridges"] != 11:
        raise ValueError("joint producer witness bridges missing")
    if certificate["backend_option"] == "T-ARITH":
        if text.count("(declare-const fee_amount (_ BitVec 256))") != 1:
            raise ValueError("T-ARITH fresh fee declaration mismatch")
        if "(define-fun fee_amount" in text:
            raise ValueError("T-ARITH retained concrete fee definition")


def encode_query(
    omega: dict[str, Any],
    *,
    drop_producer: bool = False,
    backend_option: str = "BASE",
    consumer_model: str = "MANUAL",
) -> tuple[bytes, dict[str, Any]]:
    """Encode the D1P-20 relation interface without its fixed-shape audit."""
    if consumer_model == "MANUAL":
        return manual.encode_query(
            omega, drop_producer=drop_producer, backend_option=backend_option
        )
    if consumer_model != "EXTRACTED" or omega.get("consumer_model") != "EXTRACTED":
        raise ValueError("EXTRACTED encoder requires EXTRACTED Omega")
    if backend_option not in manual.BACKEND_OPTIONS:
        raise ValueError(f"unknown backend option: {backend_option}")
    goal = omega["goal"]["name"]
    if drop_producer and goal != "AUTH-1":
        raise ValueError("only AUTH-1 Q1 may drop R_v")
    circuit = omega["producer_relation_R_hat"]["functions"][0]
    opcodes = circuit["opcodes"]
    counts = Counter(opcode["kind"] for opcode in opcodes)
    lines = [
        "; D1P-21B variant-general joint encoding with extracted consumer relation",
        f"; omega_sha256={manual.canonical_sha256(omega)}",
        f"; goal={goal}",
        f"; producer_relation={'DROPPED_CONTROL' if drop_producer else 'FULL'}",
        "(set-logic ALL)",
        "(set-option :produce-models true)",
        f"(define-sort F () (_ FiniteField {FIELD_MODULUS}))",
    ]
    emitted = Counter()
    referenced: set[int] = set(range(11))
    if not drop_producer:
        for opcode in opcodes:
            referenced.update(manual._input_witnesses(opcode))
        for witness in sorted(referenced):
            lines.append(f"(declare-const w{witness} F)")
    for index in range(11):
        lines.append(f"(declare-const pi{index} (_ BitVec 256))")
    lines.extend([
        "(declare-const basefee (_ BitVec 256))",
        f"(define-fun msg_sender () (_ BitVec 256) {manual._bv(omega['environment']['msg_sender_value'])})",
    ])
    for index in range(11):
        lines.append(f"; DV_WORD {index} {manual.PUBLIC_INPUTS[index]}")
        lines.append(f"(assert (bvult pi{index} {manual._bv(FIELD_MODULUS)}))")
        if not drop_producer:
            lines.append(
                f"(assert (= w{index} {manual._field_from_bv(254, f'pi{index}')}))"
            )
    for index in (9, 10):
        lines.append(f"(assert (bvult pi{index} {manual._bv(manual.ADDRESS_LIMIT)}))")
    if not drop_producer:
        for opcode in opcodes:
            index, kind = opcode["opcode_index"], opcode["kind"]
            if kind == "AssertZero":
                lines.extend([
                    f"; ACIR AssertZero {index}",
                    f"(assert (= {manual._expression(opcode['expression'])} {manual._ff(0)}))",
                ])
            elif kind == "RANGE":
                lines.append(f"; ACIR RANGE {index}")
                inp, bits = opcode["input"], opcode["num_bits"]
                if "constant" in inp:
                    lines.append(
                        f"(assert {'true' if inp['constant'] < (1 << bits) else 'false'})"
                    )
                else:
                    name = f"range_{index}"
                    lines.extend([
                        f"(declare-const {name} (_ BitVec {bits}))",
                        f"(assert (= w{inp['witness']} {manual._field_from_bv(bits, name)}))",
                    ])
            elif kind == "Poseidon2Permutation":
                lines.append(
                    f"; ACIR Poseidon2Permutation {index} HAVOC_OUTPUTS "
                    + ",".join(str(item) for item in opcode["outputs"])
                )
            elif kind == "BrilligCall":
                lines.append(f"; ACIR BrilligCall {index} WITNESS_GENERATION_ONLY")
            else:
                raise UnsupportedConstruct("acir_opcode", f"opcode:{index}", kind)
            emitted[kind] += 1

    effects = _emit_extracted_consumer(lines, omega, backend_option=backend_option)
    manual._emit_policy(lines, omega, effects)
    lines.append("(check-sat)")
    data = ("\n".join(lines) + "\n").encode()
    parens = manual.balanced_smt_parentheses(data)
    if not parens["balanced"]:
        raise ValueError(f"unbalanced generated SMT: {parens}")
    ir = omega["consumer_T_mint"]["relation"]
    certificate = {
        "schema": "bindcheck.d1p21b.transformation/v1",
        "omega_sha256": manual.canonical_sha256(omega),
        "goal": goal,
        "consumer_model": "EXTRACTED",
        "consumer_summary_classification": "EXTRACTED",
        "source_relation_sha256": omega["consumer_T_mint"]["source_relation_sha256"],
        "source_relation_canonical_sha256": ir["source_relation_canonical_sha256"],
        "serialized_paths_canonical_sha256": ir["serialized_paths_canonical_sha256"],
        "relation_shape": copy.deepcopy(ir["relation_shape"]),
        "serialized_path_ids": [path["id"] for path in ir["paths"]],
        "backend_option": backend_option,
        "producer_relation": "dropped by deterministic control" if drop_producer else "full",
        "verifier_boundary": {
            "mode": "explicit relational boundary discharged by R_hat and D_v"
            if not drop_producer
            else "explicit accepted-proof assumption for dropped-producer control only",
            "declaration": ir["verifier_boundary"]["declaration"],
            "consumer_argument_bridges": 11,
            "producer_witness_bridges": 0 if drop_producer else 11,
        },
        "configuration_bindings": copy.deepcopy(
            omega["consumer_T_mint"]["configuration_bindings"]
        ),
        "decoded_opcode_counts": dict(sorted(counts.items())),
        "emitted_opcode_counts": dict(sorted(emitted.items())),
        "path_families_serialized": len(effects["path_ids"]),
        "success_path_families": effects["success_ids"],
        "revert_path_families": effects["revert_ids"],
        "rollback_serialized": True,
        "policy_serialized_after_implementation": True,
        "control_transform": omega["consumer_T_mint"].get("control_transform"),
        "balanced_parentheses": parens,
        "query_sha256": hashlib.sha256(data).hexdigest(),
        "query_bytes": len(data),
    }
    if backend_option == "T-ARITH":
        certificate["preservation_argument"] = (
            "Identical to MANUAL T-ARITH: replace only the recovered fee product value "
            "with one fresh uint256 while retaining branch, overflow, cap, subtraction, "
            "receiver, supply, path, and effect structure."
        )
    audit_extracted_query(omega, data, certificate, drop_producer=drop_producer)
    return data, certificate


fixed_terminal_query = d1p20.fixed_terminal_query
