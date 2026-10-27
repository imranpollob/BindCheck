#!/usr/bin/env python3
"""Use the D1P-18 Solidity-AST relation as the joint encoder's consumer model.

The canonical D1P-14C/D1P-17 module is imported, never edited.  MANUAL is the
default and delegates byte-for-byte to that module.  EXTRACTED translates the
D1P-18 IR fail-closed, bridges recovered verifier arguments to the joint public
words, and then invokes the unchanged policy serializer over extracted effects.
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
if str(D1P16) not in sys.path:
    sys.path.insert(0, str(D1P16))
from extract_relation import UnsupportedConstruct  # noqa: E402


CONSUMER_MODELS = {"MANUAL", "EXTRACTED"}
CONTROL_VARIANTS = {
    "C1": "G1",
    "C2": "G3",
    "C3": "G4",
    "C4": "G5",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _relation_sha256(relation: dict[str, Any]) -> str:
    return hashlib.sha256((_canonical(relation) + "\n").encode()).hexdigest()


def load_extracted_relation(path: Path) -> dict[str, Any]:
    relation = json.loads(path.read_text())
    if relation.get("schema") != "bindcheck.d1p18.extracted-consumer-relation.v2":
        raise UnsupportedConstruct("relation_schema", str(path), str(relation.get("schema")))
    if relation.get("summary") != {
        "all_reverts_commit_nothing": True,
        "path_count": 22,
        "revert_paths": 19,
        "success_paths": 3,
    }:
        raise UnsupportedConstruct("relation_shape", str(path), "expected frozen 22/19/3 relation")
    if not all(relation.get("pins", {}).get("assertions", {}).values()):
        raise UnsupportedConstruct("relation_pin", str(path), "one or more D1P-18 pins failed")
    return relation


def manual_input_manifest(relation: dict[str, Any]) -> dict[str, Any]:
    """Enumerate every non-AST input still used by the extracted route."""
    models = json.loads((D1P16 / "library_effect_models.v1.json").read_text())
    declarations = []
    for library_name, library in models["libraries"].items():
        for table_name in ("declarations", "storage_declarations", "event_declarations"):
            for declaration, model in library.get(table_name, {}).items():
                declarations.append({
                    "library": library_name,
                    "table": table_name,
                    "declaration": declaration,
                    "semantic": model["semantic"],
                    "classification": "MANUAL EFFECT MODEL ENTRY",
                })
    boundaries = [
        {
            "declaration": declaration,
            "semantic": model["semantic"],
            "assumed_true": model["assumed_true"],
            "classification": "MANUAL RELATIONAL BOUNDARY DECLARATION",
        }
        for declaration, model in models["external_boundaries"].items()
    ]
    return {
        "schema": "bindcheck.d1p20.manual-input-manifest/v1",
        "effect_model_table": {
            "path": "prototypes/d1p16/library_effect_models.v1.json",
            "version": models["version"],
            "sha256": relation["pins"]["library_effect_models_sha256"],
            "case_specific_entries": models["case_specific_entries"],
        },
        "library_model_entries": sorted(declarations, key=lambda item: item["declaration"]),
        "boundary_declarations": boundaries,
        "fixed_environment": [
            {
                "name": "block.chainid",
                "value": manual.CHAIN_ID,
                "classification": "PINNED OWNED-LOCAL ENVIRONMENT",
            },
            {
                "name": "aztecWarptoadAddress",
                "value": manual.AZTEC_WARPTOAD_ADDRESS,
                "classification": "PINNED OWNED-LOCAL DEPLOYMENT CONFIGURATION",
            },
        ],
        "policy_adapter": {
            "classification": "MANUAL POLICY INTERPRETATION; NOT IMPLEMENTATION RELATION",
            "role_mapping": {
                "WarpToadCore.sol:171": "FEE",
                "WarpToadCore.sol:172": "RECIPIENT",
                "WarpToadCore.sol:175": "RECIPIENT",
            },
            "reason": "G1-G5 consume semantic occurrence roles; role names are kept outside the extracted implementation relation.",
        },
    }


def serialize_consumer_ir(relation: dict[str, Any]) -> dict[str, Any]:
    """Serialize all D1P-18 terminal paths without adding implementation equations."""
    paths = []
    for path in relation["paths"]:
        paths.append({
            "id": path["id"],
            "status": path["status"],
            "guards": copy.deepcopy(path["guards_ir"]),
            "revert": copy.deepcopy(path["revert"]),
            "committed": copy.deepcopy(path["committed"]),
            "tentative": copy.deepcopy(path["tentative"]),
            "rollback": path["rollback"],
        })
    return {
        "schema": "bindcheck.d1p20.extracted-consumer-ir/v1",
        "classification": "EXTRACTED implementation relation",
        "source_relation_canonical_sha256": _relation_sha256(relation),
        "source_relation_schema": relation["schema"],
        "pins": copy.deepcopy(relation["pins"]),
        "verifier_boundary": copy.deepcopy(relation["verifier_boundary"]),
        "paths": paths,
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
) -> dict[str, Any]:
    """Build Omega; MANUAL remains the unchanged default."""
    if consumer_model not in CONSUMER_MODELS:
        raise ValueError(f"unknown consumer_model: {consumer_model}")
    if consumer_model == "MANUAL":
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
            "D1P-20:build_omega",
            "implementation variants are validation-only control transforms",
        )
    if relation_path is None:
        raise ValueError("EXTRACTED requires relation_path")
    base = manual.build_omega(
        artifact, goal=goal, s0=s0, identities=identities,
        implementation_variant="BASE", control_id=None,
    )
    relation = load_extracted_relation(relation_path)
    ir = serialize_consumer_ir(relation)
    ir["source_relation_path"] = str(relation_path.resolve())
    ir["source_relation_file_sha256"] = hashlib.sha256(relation_path.read_bytes()).hexdigest()
    base["schema"] = "bindcheck.d1p20.omega/v1"
    base["consumer_model"] = "EXTRACTED"
    base["consumer_T_mint"] = {
        "classification": "EXTRACTED",
        "automatic_extraction_claim": True,
        "claim_scope": "tested WarpToadCore.mint fragment only",
        "source_relation_sha256": ir["source_relation_file_sha256"],
        "relation": ir,
        "control_transform": (
            {
                "id": control_id,
                "classification": "D1P-14D validation-only implementation mutation",
                "policy_unchanged": True,
                "expected_goal": CONTROL_VARIANTS[control_id],
            }
            if control_id is not None else None
        ),
    }
    base["environment"]["aztec_warptoad_address"] = manual.AZTEC_WARPTOAD_ADDRESS
    base["diagnostic_control"] = base["consumer_T_mint"]["control_transform"]
    return base


class SMTTranslator:
    def __init__(self, omega: dict[str, Any], backend_option: str):
        self.omega = omega
        self.backend_option = backend_option
        self.ir = omega["consumer_T_mint"]["relation"]
        self.path_location = "D1P-20:extracted-relation"
        self.symbols = {
            "calldata._nullifier": "pi0",
            "block.chainid": "env_chain_id",
            "calldata._amount": "pi2",
            "calldata._gigaRoot": "pi3",
            "calldata._localRoot": "pi4",
            "calldata._feeFactor": "pi6",
            "calldata._priorityFee": "pi7",
            "calldata._maxFee": "pi8",
            "calldata._relayer": "pi9",
            "calldata._recipient": "pi10",
            "block.basefee": "basefee",
            "msg.sender": "msg_sender",
            "calldata._poof": "proof_bytes",
        }
        fee_mints = [
            mint
            for path in self.ir["paths"]
            for mint in path["committed"]["mints"]
            if mint["location"] == "WarpToadCore.sol:171"
        ]
        if not fee_mints:
            raise UnsupportedConstruct("fee_expression", self.path_location, "missing line 171 mint")
        self.fee_ir_key = _canonical(fee_mints[0]["amount_ir"])
        verifier_relations = {
            _canonical(guard)
            for path in self.ir["paths"]
            for guard in path["guards"]
            if guard.get("op") == "relation"
        }
        if len(verifier_relations) != 1:
            raise UnsupportedConstruct(
                "verifier_relation_shape", self.path_location,
                f"expected one exact verifier relation, found {len(verifier_relations)}",
            )
        self.verifier_relation_ir_key = next(iter(verifier_relations))

    def reject(self, kind: str, detail: str) -> UnsupportedConstruct:
        return UnsupportedConstruct(kind, self.path_location, detail)

    def _membership(self, storage: str, key: str) -> str:
        state = self.omega["fixed_pre_state_S0"]
        mapping = {
            "gigaRootHistory": state.get("giga_root_history", []),
            "localRootHistory": state.get("local_root_history", []),
            "nullifiers": state.get("nullifiers", []),
        }
        if storage not in mapping:
            raise self.reject("storage_read", storage)
        return manual._bool_or([f"(= {key} {manual._bv(int(value))})" for value in mapping[storage]])

    def expr(self, node: Any) -> str:
        if not isinstance(node, dict) or "op" not in node:
            raise self.reject("ir_node", repr(node))
        if self.backend_option == "T-ARITH" and _canonical(node) == self.fee_ir_key:
            return "fee_amount"
        op, args = node["op"], node.get("args", [])
        if op == "const":
            value = args[0]
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, int):
                return manual._bv(value)
            raise self.reject("constant", repr(value))
        if op == "symbol":
            name = args[0]
            if name not in self.symbols:
                raise self.reject("symbol", name)
            if name == "calldata._poof":
                raise self.reject("proof_value", "proof bytes may appear only at verifier boundary")
            return self.symbols[name]
        if op == "storage":
            name = args[0]
            exact = {
                "aztecWarptoadAddress": "config_aztec_address",
                "_totalSupply": "pre_total_supply",
            }
            if name not in exact:
                raise self.reject("storage_scalar", name)
            return exact[name]
        if op == "cast":
            if len(args) != 2:
                raise self.reject("cast_arity", repr(args))
            if args[0] not in {"bytes32", "bytes20", "uint160", "uint256"}:
                raise self.reject("cast_type", str(args[0]))
            return self.expr(args[1])
        if op == "select":
            base = args[0]
            if base.get("op") != "storage":
                raise self.reject("map_base", repr(base))
            return self._membership(base["args"][0], self.expr(args[1]))
        if op == "not":
            return f"(not {self.expr(args[0])})"
        binary = {
            "eq": "=", "neq": "distinct", "lt": "bvult", "le": "bvule",
            "gt": "bvugt", "ge": "bvuge", "add": "bvadd", "sub": "bvsub",
            "mul": "bvmul", "add_mod": "bvadd", "sub_mod": "bvsub", "mul_mod": "bvmul",
        }
        if op in binary:
            return f"({binary[op]} {self.expr(args[0])} {self.expr(args[1])})"
        if op == "no_overflow_add":
            lhs, rhs = self.expr(args[0]), self.expr(args[1])
            return (manual._native_bv_sum_no_overflow(lhs, rhs)
                    if self.backend_option == "T-OVF" else manual._bv_sum_no_overflow(lhs, rhs))
        if op == "no_underflow_sub":
            return f"(bvuge {self.expr(args[0])} {self.expr(args[1])})"
        if op == "no_overflow_mul":
            lhs, rhs = self.expr(args[0]), self.expr(args[1])
            return (manual._native_bv_product_no_overflow(lhs, rhs)
                    if self.backend_option == "T-OVF" else manual._bv_product_no_overflow(lhs, rhs))
        if op == "relation":
            if _canonical(node) != self.verifier_relation_ir_key:
                raise self.reject("verifier_relation", "unmodeled relational boundary")
            return "consumer_verifier_boundary"
        raise self.reject("ir_operator", op)


def _same_ir(items: list[dict[str, Any]], field: str, location: str) -> dict[str, Any]:
    values = {_canonical(item[field]) for item in items}
    if len(values) != 1:
        raise UnsupportedConstruct("effect_merge", location, f"different {field} expressions")
    return items[0][field]


def _emit_extracted_consumer(
    lines: list[str], omega: dict[str, Any], *, backend_option: str,
) -> dict[str, Any]:
    translator = SMTTranslator(omega, backend_option)
    ir = omega["consumer_T_mint"]["relation"]
    if backend_option not in manual.BACKEND_OPTIONS:
        raise ValueError(f"unknown backend option: {backend_option}")
    lines.extend([
        "; IMPLEMENTATION_RELATION EXTRACTED begin",
        f"; source_relation_sha256={ir['source_relation_file_sha256']}",
        f"; BACKEND_OPTION {backend_option}",
        f"(define-fun env_chain_id () (_ BitVec 256) {manual._bv(manual.CHAIN_ID)})",
        f"(define-fun config_aztec_address () (_ BitVec 256) {manual._bv(manual.AZTEC_WARPTOAD_ADDRESS)})",
        f"(define-fun pre_total_supply () (_ BitVec 256) {manual._bv(int(omega['fixed_pre_state_S0']['total_supply']))})",
        "; The verifier gate below is the recovered argument bridge. Full queries additionally assert joint R_hat and D_v; dropped-producer controls explicitly assume accepted-proof feasibility.",
    ])
    if backend_option == "T-ARITH":
        lines.extend([
            "; T-ARITH over-approximation: identical fresh fee value for MANUAL and EXTRACTED",
            "(declare-const fee_amount (_ BitVec 256))",
        ])

    boundary = ir["verifier_boundary"]
    if boundary["kind"] != "uninterpreted producer relation; never assumed true":
        raise translator.reject("verifier_boundary", boundary["kind"])
    if len(boundary["public_words"]) != 11:
        raise translator.reject("verifier_word_count", str(len(boundary["public_words"])))
    verifier_bridges = []
    for word in boundary["public_words"]:
        index = word["index"]
        expression = translator.expr(word["expression_ir"])
        verifier_bridges.append(f"(= pi{index} consumer_verify_word_{index})")
        lines.extend([
            f"; CONSUMER_VERIFIER_ARGUMENT {index} origin={word['origin']}",
            f"(define-fun consumer_verify_word_{index} () (_ BitVec 256) {expression})",
        ])
    lines.append(
        f"(define-fun consumer_verifier_boundary () Bool {manual._bool_and(verifier_bridges)})"
    )

    path_ids = []
    success_ids = []
    revert_ids = []
    for path in ir["paths"]:
        path_id = path["id"]
        path_ids.append(path_id)
        guards = [translator.expr(guard) for guard in path["guards"]]
        lines.append(f"; PATH {path_id} status={path['status']} rollback={str(path['rollback']).lower()}")
        lines.append(f"(define-fun path_{path_id} () Bool {manual._bool_and(guards)})")
        (success_ids if path["status"] == "success" else revert_ids).append(path_id)
    lines.extend([
        f"(define-fun consumer_success () Bool {manual._bool_or([f'path_{item}' for item in success_ids])})",
        f"(define-fun consumer_revert () Bool {manual._bool_or([f'path_{item}' for item in revert_ids])})",
        f"(assert (not (= pi9 {manual._bv(1)})))",
        "(assert consumer_success)",
    ])

    by_location: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for path in ir["paths"]:
        if path["status"] != "success":
            continue
        for mint in path["committed"]["mints"]:
            by_location.setdefault(mint["location"], []).append((path["id"], mint))
    expected_locations = {
        "WarpToadCore.sol:171": ("mint_fee", "FEE"),
        "WarpToadCore.sol:172": ("mint_recipient_fee", "RECIPIENT"),
        "WarpToadCore.sol:175": ("mint_recipient_zero", "RECIPIENT"),
    }
    if set(by_location) != set(expected_locations):
        raise translator.reject("mint_callsites", repr(sorted(by_location)))
    summary_mints = []
    mint_names = []
    for location, (name, role) in expected_locations.items():
        occurrences = by_location[location]
        path_terms = [f"path_{path_id}" for path_id, _mint in occurrences]
        present = manual._bool_or(path_terms)
        amount_ir = _same_ir([mint for _path, mint in occurrences], "amount_ir", location)
        amount = translator.expr(amount_ir)
        beneficiaries = [(f"path_{path_id}", translator.expr(mint["beneficiary_ir"]))
                         for path_id, mint in occurrences]
        beneficiary = beneficiaries[-1][1]
        for condition, value in reversed(beneficiaries[:-1]):
            beneficiary = f"(ite {condition} {value} {beneficiary})"
        control = omega["consumer_T_mint"].get("control_transform")
        if control and control["id"] == "C1" and name == "mint_recipient_fee":
            amount = "pi2"
        if control and control["id"] == "C2" and name == "mint_fee":
            beneficiary = "pi10"
        lines.extend([
            f"; EFFECT mint {name} role={role} callsite={location}",
            f"(define-fun {name}_present () Bool {present})",
            f"(define-fun {name}_amount () (_ BitVec 256) {amount})",
            f"(define-fun {name}_beneficiary () (_ BitVec 256) {beneficiary})",
        ])
        summary_mints.append({"id": name, "role": role})
        mint_names.append(name)
    control = omega["consumer_T_mint"].get("control_transform")
    if control and control["id"] == "C3":
        lines.extend([
            "; EFFECT mint mint_extra validation-only D1P-14D control",
            "(define-fun mint_extra_present () Bool consumer_success)",
            f"(define-fun mint_extra_amount () (_ BitVec 256) {manual._bv(0)})",
            "(define-fun mint_extra_beneficiary () (_ BitVec 256) pi10)",
        ])
        summary_mints.append({"id": "mint_extra", "role": "RECIPIENT"})
        mint_names.append("mint_extra")

    balance_names = []
    summary_balances = []
    for mint in summary_mints:
        source = mint["id"]
        name = f"balance_{source}"
        balance_names.append(name)
        summary_balances.append({"id": name, "source_occurrence": source})
        lines.extend([
            f"; EFFECT balance {name} source={source}",
            f"(define-fun {name}_present () Bool {source}_present)",
            f"(define-fun {name}_amount () (_ BitVec 256) {source}_amount)",
            f"(define-fun {name}_beneficiary () (_ BitVec 256) {source}_beneficiary)",
        ])
    total_terms = [f"(ite {name}_present {name}_amount {manual._bv(0)})" for name in mint_names]
    lines.append(f"(define-fun impl_total_supply_delta () (_ BitVec 256) {manual._bv_add(total_terms)})")

    lines.extend([
        "; EFFECT nullifier_write nullifier_primary extracted from WarpToadCore.sol:158",
        "(define-fun nullifier_primary_present () Bool consumer_success)",
        "(define-fun nullifier_primary_key () (_ BitVec 256) pi0)",
    ])
    write_names = ["nullifier_primary"]
    summary_writes = [{"id": "nullifier_primary"}]
    if control and control["id"] == "C4":
        lines.extend([
            "; EFFECT nullifier_write nullifier_extra validation-only D1P-14D control",
            "(define-fun nullifier_extra_present () Bool consumer_success)",
            "(define-fun nullifier_extra_key () (_ BitVec 256) (bvadd pi0 (_ bv1 256)))",
        ])
        write_names.append("nullifier_extra")
        summary_writes.append({"id": "nullifier_extra"})

    all_effect_names = mint_names + write_names
    lines.extend([
        f"(define-fun rollback_holds () Bool (=> consumer_revert {manual._bool_and([f'(not {name}_present)' for name in all_effect_names])}))",
        "(assert rollback_holds)",
        "; IMPLEMENTATION_RELATION EXTRACTED end",
    ])
    summary = {
        "classification": "EXTRACTED",
        "mint_occurrences": summary_mints,
        "nullifier_writes": summary_writes,
        "other_balance_changes": summary_balances,
    }
    return {
        "summary": summary,
        "mint_names": mint_names,
        "balance_names": balance_names,
        "write_names": write_names,
        "path_ids": path_ids,
        "success_ids": success_ids,
        "revert_ids": revert_ids,
    }


def encode_query(
    omega: dict[str, Any], *, drop_producer: bool = False,
    backend_option: str = "BASE", consumer_model: str = "MANUAL",
) -> tuple[bytes, dict[str, Any]]:
    """Encode with MANUAL (unchanged default) or EXTRACTED consumer relation."""
    if consumer_model not in CONSUMER_MODELS:
        raise ValueError(f"unknown consumer_model: {consumer_model}")
    if consumer_model == "MANUAL":
        return manual.encode_query(
            omega, drop_producer=drop_producer, backend_option=backend_option
        )
    if omega.get("consumer_model") != "EXTRACTED":
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
        "; D1P-20 joint encoding with extracted consumer relation",
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
            lines.append(f"(assert (= w{index} {manual._field_from_bv(254, f'pi{index}')}))")
    for index in (9, 10):
        lines.append(f"(assert (bvult pi{index} {manual._bv(manual.ADDRESS_LIMIT)}))")
    if not drop_producer:
        for opcode in opcodes:
            index, kind = opcode["opcode_index"], opcode["kind"]
            if kind == "AssertZero":
                lines.extend([f"; ACIR AssertZero {index}",
                              f"(assert (= {manual._expression(opcode['expression'])} {manual._ff(0)}))"])
            elif kind == "RANGE":
                lines.append(f"; ACIR RANGE {index}")
                inp, bits = opcode["input"], opcode["num_bits"]
                if "constant" in inp:
                    lines.append(f"(assert {'true' if inp['constant'] < (1 << bits) else 'false'})")
                else:
                    name = f"range_{index}"
                    lines.extend([f"(declare-const {name} (_ BitVec {bits}))",
                                  f"(assert (= w{inp['witness']} {manual._field_from_bv(bits, name)}))"])
            elif kind == "Poseidon2Permutation":
                lines.append(f"; ACIR Poseidon2Permutation {index} HAVOC_OUTPUTS " +
                             ",".join(str(item) for item in opcode["outputs"]))
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
    certificate = {
        "schema": "bindcheck.d1p20.transformation/v1",
        "omega_sha256": manual.canonical_sha256(omega),
        "goal": goal,
        "consumer_model": "EXTRACTED",
        "consumer_summary_classification": "EXTRACTED",
        "source_relation_sha256": omega["consumer_T_mint"]["source_relation_sha256"],
        "backend_option": backend_option,
        "producer_relation": "dropped by deterministic control" if drop_producer else "full",
        "verifier_boundary": {
            "mode": "explicit relational boundary discharged by R_hat and D_v" if not drop_producer
                    else "explicit accepted-proof assumption for dropped-producer control only",
            "declaration": omega["consumer_T_mint"]["relation"]["verifier_boundary"]["declaration"],
            "consumer_argument_bridges": 11,
            "producer_witness_bridges": 0 if drop_producer else 11,
        },
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


def audit_extracted_query(
    omega: dict[str, Any], query: bytes, certificate: dict[str, Any], *, drop_producer: bool,
) -> None:
    text = query.decode()
    if "; IMPLEMENTATION_SUMMARY MANUAL_ASSUMED" in text:
        raise ValueError("manual consumer summary leaked into EXTRACTED query")
    if text.count("; IMPLEMENTATION_RELATION EXTRACTED begin") != 1:
        raise ValueError("missing extracted implementation marker")
    if text.count("; PATH p") != 22:
        raise ValueError("not all 22 extracted path families were serialized")
    if text.count("; CONSUMER_VERIFIER_ARGUMENT ") != 11:
        raise ValueError("recovered verifier-argument bridge count mismatch")
    for required in ("consumer_success", "consumer_revert", "rollback_holds",
                     "; POLICY_EVALUATION begin", "(define-fun G1", "(define-fun G5"):
        if required not in text:
            raise ValueError(f"missing extracted query marker: {required}")
    if hashlib.sha256(query).hexdigest() != certificate["query_sha256"]:
        raise ValueError("query hash mismatch")
    if not manual.balanced_smt_parentheses(query)["balanced"]:
        raise ValueError("query parentheses are not balanced")
    if not drop_producer and certificate["verifier_boundary"]["producer_witness_bridges"] != 11:
        raise ValueError("joint producer witness bridges missing")
    option = certificate["backend_option"]
    if option == "T-ARITH":
        if text.count("(declare-const fee_amount (_ BitVec 256))") != 1:
            raise ValueError("T-ARITH fresh fee declaration mismatch")
        if "(define-fun fee_amount" in text:
            raise ValueError("T-ARITH retained concrete fee definition")


def fixed_terminal_query(
    query: bytes,
    *,
    words: list[int],
    basefee: int,
    designated_goal: str | None = None,
) -> bytes:
    """Fix concrete inputs and optionally assert one policy goal."""
    terminal = b"(assert (or G1 G2 G3 G4 G5))\n(check-sat)\n"
    if query.count(terminal) != 1:
        raise ValueError("unexpected AUTH terminal shape")
    fixed = [f"(assert (= pi{i} {manual._bv(value)}))" for i, value in enumerate(words)]
    fixed.append(f"(assert (= basefee {manual._bv(basefee)}))")
    if designated_goal is not None:
        fixed.append(f"(assert {designated_goal})")
    fixed.append("(check-sat)")
    return query.replace(terminal, ("\n".join(fixed) + "\n").encode())

