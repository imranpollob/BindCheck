#!/usr/bin/env python3
"""Generate bounded D1P-21B validation evidence; never runs a solver campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from bindcheck_d1 import joint_warptoad as manual
from bindcheck_d1.joint_warptoad_d1p14d import freeze_honest_fixture


HERE = Path(__file__).resolve().parent
for dependency in (HERE.parent / "d1p16", HERE.parent / "d1p20"):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

from compare_executions import (  # noqa: E402
    map_value,
    number,
    proof_context,
    selected_path,
)
import validate_d1p20 as prior_validation  # noqa: E402
from joint_variant import (  # noqa: E402
    CONTROL_VARIANTS,
    build_omega,
    encode_query,
    fixed_terminal_query,
    load_extracted_relation,
    manual_input_manifest,
    relation_shape,
    serialize_consumer_ir,
)


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def contains_storage(value: Any, name: str) -> bool:
    if isinstance(value, list):
        return any(contains_storage(item, name) for item in value)
    if not isinstance(value, dict):
        return False
    if value.get("op") == "storage" and value.get("args", [None])[0] == name:
        return True
    return any(contains_storage(item, name) for item in value.values())


def normalized_path(path: dict[str, Any], *, remove_k2: bool) -> dict[str, Any]:
    result = copy.deepcopy(path)
    result.pop("id", None)
    if remove_k2:
        result["guards_ir"] = [
            guard for guard in result["guards_ir"]
            if not contains_storage(guard, "localRootHistory")
        ]
        result["guards"] = [
            guard for guard in result["guards"] if "localRootHistory" not in guard
        ]
    return result


def compare_variants(pinned: dict[str, Any], msrc: dict[str, Any]) -> dict[str, Any]:
    pinned_kept = [
        path for path in pinned["paths"]
        if not (path["status"] == "revert" and path["revert"]["reason"] == "_localRoot unknown")
    ]
    if len(pinned_kept) != len(msrc["paths"]):
        raise AssertionError("M-SRC does not differ by exactly one terminal family")
    mapping = []
    for pinned_path, msrc_path in zip(pinned_kept, msrc["paths"]):
        equal = canonical(normalized_path(pinned_path, remove_k2=True)) == canonical(
            normalized_path(msrc_path, remove_k2=False)
        )
        mapping.append({
            "pinned": pinned_path["id"],
            "m_src": msrc_path["id"],
            "status": msrc_path["status"],
            "equal_after_removing_k2_guard": equal,
        })
    checks = {
        "path_delta_minus_one": relation_shape(msrc)["path_count"]
        == relation_shape(pinned)["path_count"] - 1,
        "revert_delta_minus_one": relation_shape(msrc)["revert_paths"]
        == relation_shape(pinned)["revert_paths"] - 1,
        "success_count_unchanged": relation_shape(msrc)["success_paths"]
        == relation_shape(pinned)["success_paths"],
        "removed_family_is_k2": any(
            path["revert"] and path["revert"]["reason"] == "_localRoot unknown"
            for path in pinned["paths"]
        ) and not any(
            path["revert"] and path["revert"]["reason"] == "_localRoot unknown"
            for path in msrc["paths"]
        ),
        "all_remaining_families_match_after_k2_removal": all(
            item["equal_after_removing_k2_guard"] for item in mapping
        ),
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "mapping": mapping})
    return {
        "schema": "bindcheck.d1p21b.variant-comparison/v1",
        "method": "unchanged D1P-18 extractor; path comparison removes only K2 guards from pinned",
        "pinned": {
            "shape": relation_shape(pinned),
            "canonical_sha256": hashlib.sha256((canonical(pinned) + "\n").encode()).hexdigest(),
        },
        "m_src": {
            "shape": relation_shape(msrc),
            "canonical_sha256": hashlib.sha256((canonical(msrc) + "\n").encode()).hexdigest(),
        },
        "removed_family": {
            "pinned_path": "p01",
            "reason": "_localRoot unknown",
            "location": "WarpToadCore.sol:156",
            "guard": "not(select(pre.localRootHistory, calldata._localRoot))",
        },
        "success_family_mapping": [item for item in mapping if item["status"] == "success"],
        "all_family_mapping": mapping,
        "checks": checks,
        "all_checks_pass": True,
    }


def with_configuration_state(state: dict[str, Any], words: list[int]) -> dict[str, Any]:
    result = copy.deepcopy(state)
    result["aztec_warptoad_address"] = str(words[5])
    return result


def solver_result(solver: Path, query: bytes) -> dict[str, Any]:
    result = prior_validation.run_solver(solver, query)
    result["observed"] = result["stdout"].splitlines()[0] if result["stdout"] else ""
    return result


def validate_pinned_executions(
    paper: Path, artifact: Path, relation_path: Path, solver: Path, identities: dict[str, Any]
) -> dict[str, Any]:
    prior_comparison = load(relation_path.parent / "five-execution-comparison.json")
    results = {}
    for name, case in prior_validation.concrete_cases(paper).items():
        public_words = prior_validation.words(case["proof"])
        s0 = with_configuration_state(
            prior_validation.state_from_pre(case["proof"], case["pre"]), public_words
        )
        omega = build_omega(
            artifact,
            goal="AUTH-1",
            s0=s0,
            identities=identities,
            consumer_model="EXTRACTED",
            relation_path=relation_path,
            environment={"chain_id": public_words[1]},
        )
        base, certificate = encode_query(
            omega, consumer_model="EXTRACTED", drop_producer=True
        )
        query = fixed_terminal_query(base, words=public_words, basefee=case["basefee"])
        result = solver_result(solver, query)
        expected = "sat" if case["expected_success"] else "unsat"
        checks = {
            "solver_matches_recorded_success": result["observed"] == expected,
            "prior_relation_path_matches": prior_comparison["cases"][name]["selected_path"]
            == case["expected_path"],
            "prior_relation_had_no_disagreement": prior_comparison["cases"][name][
                "disagreements"
            ] == [],
            "query_balanced": manual.balanced_smt_parentheses(query)["balanced"],
            "state_configuration_equals_public_word_5": int(s0["aztec_warptoad_address"])
            == public_words[5],
        }
        if not all(checks.values()):
            raise AssertionError({"case": name, "result": result, "checks": checks})
        results[name] = {
            "expected": expected,
            "observed": result["observed"],
            "selected_path": case["expected_path"],
            "query_sha256": result["query_sha256"],
            "certificate_sha256": hashlib.sha256(
                manual.canonical_bytes(certificate)
            ).hexdigest(),
            "checks": checks,
        }
    return {
        "schema": "bindcheck.d1p21b.pinned-executions/v1",
        "classification": "five fixed archived executions; no primary solver campaign",
        "cases": results,
        "all_checks_pass": True,
    }


def validate_controls(
    paper: Path, artifact: Path, relation_path: Path, solver: Path, identities: dict[str, Any]
) -> dict[str, Any]:
    proof = load(paper / "results/raw/D1P-14A/fc-pos-proof.json")
    receipt = load(paper / "results/raw/D1P-14A/fc-pos-receipt.json")
    fixture = freeze_honest_fixture(proof, receipt)
    public_words = [int(value) for value in fixture["public_words"]]
    s0 = with_configuration_state(fixture["admitted_state"], public_words)
    results = {}
    policy_hashes = set()
    for control_id, target in CONTROL_VARIANTS.items():
        for polarity in ("positive", "negative"):
            omega = build_omega(
                artifact,
                goal="AUTH-1",
                s0=s0,
                identities=identities,
                consumer_model="EXTRACTED",
                relation_path=relation_path,
                control_id=control_id if polarity == "positive" else None,
                environment={"chain_id": public_words[1]},
            )
            base, certificate = encode_query(
                omega, consumer_model="EXTRACTED", drop_producer=True
            )
            query = fixed_terminal_query(
                base,
                words=public_words,
                basefee=int(fixture["environment"]["basefee"]),
                designated_goal=target,
            )
            result = solver_result(solver, query)
            expected = "sat" if polarity == "positive" else "unsat"
            if result["observed"] != expected:
                raise AssertionError({"control": control_id, "polarity": polarity, "result": result})
            slot = f"{control_id}{'P' if polarity == 'positive' else 'N'}"
            policy_hashes.add(manual.canonical_sha256(omega["policy"]))
            results[slot] = {
                "target": target,
                "expected": expected,
                "observed": result["observed"],
                "query_sha256": result["query_sha256"],
                "certificate_sha256": hashlib.sha256(
                    manual.canonical_bytes(certificate)
                ).hexdigest(),
            }
    if len(policy_hashes) != 1:
        raise AssertionError("policy changed across D1P-14D controls")
    return {
        "schema": "bindcheck.d1p21b.pinned-controls/v1",
        "classification": "eight deterministic D1P-14D controls; no primary solver campaign",
        "policy_sha256": next(iter(policy_hashes)),
        "results": results,
        "positive_sat": sum(item["observed"] == "sat" for key, item in results.items() if key.endswith("P")),
        "negative_unsat": sum(item["observed"] == "unsat" for key, item in results.items() if key.endswith("N")),
        "all_checks_pass": True,
    }


def validate_msrc_polarity(
    paper: Path,
    artifact: Path,
    pinned_path: Path,
    msrc_path: Path,
    solver: Path,
    identities: dict[str, Any],
) -> dict[str, Any]:
    proof = load(paper / "results/raw/D1P-19/m-src-attack-proof.json")
    execution = load(paper / "results/raw/D1P-19/m-src-execution.json")
    public_words = [number(value) for value in proof["publicInputs"]]
    gate = execution["attackGate"]
    relayer, recipient = public_words[9], public_words[10]
    s0 = {
        "giga_root_history": [str(public_words[3])],
        "local_root_history": [],
        "nullifiers": [],
        "total_supply": str(gate["pre"]["supply"]),
        "balances": {
            str(relayer): str(gate["pre"]["relayer"]),
            str(recipient): str(gate["pre"]["recipient"]),
        },
        "aztec_warptoad_address": str(public_words[5]),
    }
    priority_fee = public_words[7]
    effective_gas_price = number(gate["receipt"]["effectiveGasPrice"])
    basefee = effective_gas_price - priority_fee
    if basefee < 0:
        raise AssertionError("invalid D1P-19 fee reconstruction")

    solver_results = {}
    certificates = {}
    for variant, relation_path in (("M-SRC", msrc_path), ("PINNED", pinned_path)):
        omega = build_omega(
            artifact,
            goal="AUTH-1",
            s0=s0,
            identities=identities,
            consumer_model="EXTRACTED",
            relation_path=relation_path,
            environment={"chain_id": public_words[1]},
        )
        base, certificate = encode_query(
            omega, consumer_model="EXTRACTED", drop_producer=True
        )
        query = fixed_terminal_query(base, words=public_words, basefee=basefee)
        solver_results[variant] = solver_result(solver, query)
        certificates[variant] = certificate

    pre = {
        "nullifierExists": False,
        "relayerBalance": number(gate["pre"]["relayer"]),
        "recipientBalance": number(gate["pre"]["recipient"]),
        "totalSupply": number(gate["pre"]["supply"]),
    }
    context = proof_context(proof, basefee, pre, relayer)
    context["pre.localRootHistory"] = map_value({}, False)
    context["pre.aztecWarptoadAddress"] = public_words[5]
    selected = {}
    for variant, relation_path in (("M-SRC", msrc_path), ("PINNED", pinned_path)):
        path, errors = selected_path(load_extracted_relation(relation_path), context)
        selected[variant] = {
            "path": None if path is None else path["id"],
            "status": None if path is None else path["status"],
            "revert": None if path is None else path["revert"],
            "errors": errors,
        }

    checks = {
        "archived_real_proof_generated_verifier_accepted": proof["generatedVerifierAccepted"],
        "archived_m_src_consumer_succeeded": gate["receipt"]["status"] == "success",
        "archived_pinned_rejected_at_k2": load(
            paper / "results/raw/D1P-19/pinned-negative-execution.json"
        )["gates"]["pinnedConsumerRejectedAtK2"],
        "m_src_fixed_input_sat": solver_results["M-SRC"]["observed"] == "sat",
        "pinned_fixed_input_unsat": solver_results["PINNED"]["observed"] == "unsat",
        "m_src_selects_success": selected["M-SRC"]["status"] == "success",
        "pinned_selects_k2": selected["PINNED"]["revert"] == {
            "location": "WarpToadCore.sol:156",
            "reason": "_localRoot unknown",
        },
        "producer_relation_not_mocked_always_true": all(
            certificate["verifier_boundary"]["mode"]
            == "explicit accepted-proof assumption for dropped-producer control only"
            for certificate in certificates.values()
        ),
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "solver": solver_results, "selected": selected})
    return {
        "schema": "bindcheck.d1p21b.m-src-polarity/v1",
        "classification": "fixed-input replay of an archived real-proof execution; not a solver campaign",
        "proof_sha256": proof["proofSha256"],
        "public_words": [str(value) for value in public_words],
        "fixed_pre_state": s0,
        "basefee": {
            "value": str(basefee),
            "derivation": "archived effectiveGasPrice minus public priority_fee; fee_factor is zero",
        },
        "solver_results": solver_results,
        "selected_paths": selected,
        "checks": checks,
        "all_checks_pass": True,
    }


def validate_state_binding(
    paper: Path, artifact: Path, relation_path: Path, solver: Path, identities: dict[str, Any]
) -> dict[str, Any]:
    canonical_state = load(paper / "results/raw/D1P-19/canonical-states.json")["S_DOM"]
    a_wt = number(canonical_state["A_WT"])
    amount = number(canonical_state["commitment"]["amount"])
    words = [
        number(canonical_state["commitment"]["nullifier"]),
        manual.CHAIN_ID,
        amount,
        number(canonical_state["admittedGigaTree"]["root"]),
        number(canonical_state["l1LocalRootHistory"][0]),
        a_wt,
        0,
        0,
        amount,
        int("70997970c51812dc3a010c7d01b50e0d17dc79c8", 16),
        int("90f79bf6eb2c4f870365e785982e1f101e93b906", 16),
    ]
    s0 = {
        "giga_root_history": [str(words[3])],
        "local_root_history": [str(words[4])],
        "nullifiers": [],
        "total_supply": "0",
        "balances": {},
        "aztec_warptoad_address": str(a_wt),
    }
    omega = build_omega(
        artifact,
        goal="AUTH-1",
        s0=s0,
        identities=identities,
        consumer_model="EXTRACTED",
        relation_path=relation_path,
        environment={"chain_id": words[1]},
    )
    base, certificate = encode_query(
        omega, consumer_model="EXTRACTED", drop_producer=True
    )
    matching = solver_result(solver, fixed_terminal_query(base, words=words, basefee=0))
    mismatching_words = list(words)
    mismatching_words[5] = 0
    mismatching = solver_result(
        solver, fixed_terminal_query(base, words=mismatching_words, basefee=0)
    )
    query_text, _ = encode_query(omega, consumer_model="EXTRACTED", drop_producer=True)
    checks = {
        "s_dom_a_wt_nonzero": a_wt != 0,
        "matching_state_word_sat": matching["observed"] == "sat",
        "old_manual_zero_word_unsat": mismatching["observed"] == "unsat",
        "query_contains_state_value": manual._bv(a_wt) in query_text.decode(),
        "certificate_records_binding": certificate["configuration_bindings"][
            "aztecWarptoadAddress"
        ] == "fixed_pre_state_S0.aztec_warptoad_address",
    }
    if not all(checks.values()):
        raise AssertionError({"checks": checks, "matching": matching, "mismatching": mismatching})
    return {
        "schema": "bindcheck.d1p21b.state-binding/v1",
        "classification": "fixed S_DOM polarity control; no producer or primary search",
        "admitted_aztec_warptoad_address": str(a_wt),
        "matching": matching,
        "old_manual_zero": mismatching,
        "checks": checks,
        "all_checks_pass": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--pinned-relation", type=Path, required=True)
    parser.add_argument("--m-src-relation", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output = args.output_dir.resolve()
    prepared = output / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    identities = {
        "openzeppelin": {
            "version": "5.6.1",
            "status": "EXTRACTED identity; versioned manual effect model",
        }
    }
    pinned = load_extracted_relation(args.pinned_relation)
    msrc = load_extracted_relation(args.m_src_relation)

    for name, relation, path in (
        ("pinned", pinned, args.pinned_relation),
        ("m-src", msrc, args.m_src_relation),
    ):
        ir = serialize_consumer_ir(relation)
        ir["source_relation_path"] = str(path.resolve())
        ir["source_relation_file_sha256"] = sha256(path)
        write_json(output / f"{name}-consumer-ir.json", ir)

    manifest = {
        "schema": "bindcheck.d1p21b.manual-input-manifests/v1",
        "pinned": manual_input_manifest(pinned),
        "m_src": manual_input_manifest(msrc),
        "same_library_effect_models": manual_input_manifest(pinned)["effect_model_table"]
        == manual_input_manifest(msrc)["effect_model_table"],
        "same_boundary_declarations": manual_input_manifest(pinned)["boundary_declarations"]
        == manual_input_manifest(msrc)["boundary_declarations"],
        "variant_specific_source_read_inventory": (
            manual_input_manifest(pinned)["other_state_reads"]
            != manual_input_manifest(msrc)["other_state_reads"]
        ),
    }
    write_json(output / "manual-input-manifest.json", manifest)

    variant_comparison = compare_variants(pinned, msrc)
    write_json(output / "variant-comparison.json", variant_comparison)
    executions = validate_pinned_executions(
        args.paper_root, args.artifact, args.pinned_relation, args.solver, identities
    )
    write_json(output / "pinned-concrete-executions.json", executions)
    controls = validate_controls(
        args.paper_root, args.artifact, args.pinned_relation, args.solver, identities
    )
    write_json(output / "pinned-d1p14d-controls.json", controls)
    polarity = validate_msrc_polarity(
        args.paper_root,
        args.artifact,
        args.pinned_relation,
        args.m_src_relation,
        args.solver,
        identities,
    )
    write_json(output / "m-src-fixed-input-polarity.json", polarity)
    state_binding = validate_state_binding(
        args.paper_root, args.artifact, args.pinned_relation, args.solver, identities
    )
    write_json(output / "s-dom-state-binding.json", state_binding)

    # T-ARITH is checked on both relation shapes. This is parse-only and does
    # not consume a campaign call.
    tarith = {}
    for name, relation_path, config in (
        ("pinned", args.pinned_relation, 0),
        ("m-src", args.m_src_relation, 0),
    ):
        proof = load(args.paper_root / "results/raw/D1P-14A/fc-pos-proof.json")
        receipt = load(args.paper_root / "results/raw/D1P-14A/fc-pos-receipt.json")
        fixture = freeze_honest_fixture(proof, receipt)
        fixture_words = [int(value) for value in fixture["public_words"]]
        s0 = copy.deepcopy(fixture["admitted_state"])
        s0["aztec_warptoad_address"] = str(config)
        omega = build_omega(
            args.artifact,
            goal="AUTH-1",
            s0=s0,
            identities=identities,
            consumer_model="EXTRACTED",
            relation_path=relation_path,
            environment={"chain_id": fixture_words[1]},
        )
        full_query, full_certificate = encode_query(
            omega, consumer_model="EXTRACTED", drop_producer=False
        )
        (prepared / f"{name}-base-full.smt2").write_bytes(full_query)
        full_parse = prior_validation.run_solver(args.solver, full_query, parse_only=True)
        full_checks = {
            "all_paths_serialized": full_certificate["path_families_serialized"]
            == relation_shape(load_extracted_relation(relation_path))["path_count"],
            "producer_witness_bridges": full_certificate["verifier_boundary"][
                "producer_witness_bridges"
            ] == 11,
            "parse_only_pass": full_parse["returncode"] == 0,
        }
        if not all(full_checks.values()):
            raise AssertionError({"variant": name, "checks": full_checks, "parse": full_parse})
        query, certificate = encode_query(
            omega,
            consumer_model="EXTRACTED",
            drop_producer=True,
            backend_option="T-ARITH",
        )
        (prepared / f"{name}-t-arith.smt2").write_bytes(query)
        parsed = prior_validation.run_solver(args.solver, query, parse_only=True)
        checks = {
            "one_fresh_fee": query.count(b"(declare-const fee_amount (_ BitVec 256))") == 1,
            "no_concrete_fee_definition": b"(define-fun fee_amount" not in query,
            "all_paths_serialized": certificate["path_families_serialized"]
            == relation_shape(load_extracted_relation(relation_path))["path_count"],
            "parse_only_pass": parsed["returncode"] == 0,
        }
        if not all(checks.values()):
            raise AssertionError({"variant": name, "checks": checks, "parse": parsed})
        tarith[name] = {
            "full_base": {
                "checks": full_checks,
                "parse_only": full_parse,
                "certificate": full_certificate,
            },
            "checks": checks,
            "parse_only": parsed,
            "certificate": certificate,
        }

    extractor_path = HERE.parent / "d1p16" / "extract_relation.py"
    validation = {
        "schema": "bindcheck.d1p21b.validation/v1",
        "status": "PASS",
        "base_revision": "4897d6814ab1eb8adf1bae6526b5ac4436b8dd10",
        "unchanged_extractor_sha256": sha256(extractor_path),
        "relations": {
            "pinned": {"file_sha256": sha256(args.pinned_relation), "shape": relation_shape(pinned)},
            "m_src": {"file_sha256": sha256(args.m_src_relation), "shape": relation_shape(msrc)},
        },
        "configuration_reads_rebound": ["aztecWarptoadAddress", "block.chainid"],
        "pinned_executions": {"count": 5, "all_checks_pass": executions["all_checks_pass"]},
        "pinned_d1p14d_controls": {
            "count": 8,
            "positive_sat": controls["positive_sat"],
            "negative_unsat": controls["negative_unsat"],
            "all_checks_pass": controls["all_checks_pass"],
        },
        "m_src_fixed_input_polarity": polarity["checks"],
        "s_dom_state_binding": state_binding["checks"],
        "t_arith": tarith,
        "solver_accounting": {
            "primary_solver_calls": 0,
            "fixed_archived_execution_calls": 5,
            "deterministic_control_calls": 8,
            "fixed_m_src_polarity_calls": 2,
            "fixed_s_dom_binding_calls": 2,
            "parse_only_calls": 4,
        },
        "claim_scope": "variant-general extraction/serialization fidelity on the tested WarpToad mint fragment; automatic obligation derivation remains open",
    }
    write_json(output / "validation.json", validation)
    print(json.dumps({
        "status": "PASS",
        "pinned_shape": relation_shape(pinned),
        "m_src_shape": relation_shape(msrc),
        "fixed_validation_calls": 17,
        "primary_solver_calls": 0,
        "output": str(output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

