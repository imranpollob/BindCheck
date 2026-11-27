#!/usr/bin/env python3
"""Generate and validate D1P-20 evidence without a primary solver campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from bindcheck_d1 import joint_warptoad as manual
from bindcheck_d1.joint_warptoad_d1p14d import freeze_honest_fixture

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "d1p16"))
from compare_executions import number  # noqa: E402

from joint_extracted import (  # noqa: E402
    CONTROL_VARIANTS,
    build_omega,
    encode_query,
    fixed_terminal_query,
    load_extracted_relation,
    manual_input_manifest,
    serialize_consumer_ir,
)


PUBLIC_INPUT_NAMES = list(manual.PUBLIC_INPUTS)


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def words(proof: dict[str, Any]) -> list[int]:
    values = proof["proofInputs"]
    return [number(values[name]) for name in PUBLIC_INPUT_NAMES]


def state_from_pre(proof: dict[str, Any], pre: dict[str, Any]) -> dict[str, Any]:
    public = proof["proofInputs"]
    nullifier = number(public["nullifier"])
    relayer = number(public["relayer_address"])
    recipient = number(public["recipient_address"])
    return {
        "giga_root_history": [str(number(public["giga_root"]))],
        "local_root_history": [str(number(public["destination_local_root"]))],
        "nullifiers": [str(nullifier)] if pre["nullifierExists"] else [],
        "total_supply": str(number(pre["totalSupply"])),
        "balances": {
            str(relayer): str(number(pre.get("relayerBalance", pre.get("relayerTokenBalance", 0)))),
            str(recipient): str(number(pre.get("recipientBalance", pre.get("recipientTokenBalance", 0)))),
        },
    }


def run_solver(solver: Path, query: bytes, *, parse_only: bool = False) -> dict[str, Any]:
    command = [str(solver), "--lang=smt2"]
    if parse_only:
        command.append("--parse-only")
    completed = subprocess.run(
        command, input=query, capture_output=True, timeout=30, check=False
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode(errors="replace").strip(),
        "stderr": completed.stderr.decode(errors="replace").strip(),
        "query_sha256": hashlib.sha256(query).hexdigest(),
        "query_bytes": len(query),
    }


def concrete_cases(paper: Path) -> dict[str, dict[str, Any]]:
    honest_proof = load(paper / "results/raw/D1P-12R/honest-proof.json")
    honest_receipt = load(paper / "results/raw/D1P-12R/mint-receipt.json")
    execution = load(paper / "results/raw/D1P-12R/execution-result.json")
    fc_proof = load(paper / "results/raw/D1P-14A/fc-pos-proof.json")
    fc_pos = load(paper / "results/raw/D1P-14A/fc-pos-receipt.json")
    fc_neg = load(paper / "results/raw/D1P-14A/fc-neg-receipt.json")
    zero_proof = load(paper / "results/raw/D1P-14A/zero-fee-proof.json")
    zero_receipt = load(paper / "results/raw/D1P-14A/zero-fee-receipt.json")
    replay_pre = {**execution["mint"]["post"], "nullifierExists": True}
    fc_neg_pre = {
        **fc_neg["consumerState"]["pre"],
        "relayerBalance": fc_neg["consumerState"]["pre"]["relayerTokenBalance"],
        "recipientBalance": fc_neg["consumerState"]["pre"]["recipientTokenBalance"],
    }
    zero_pre = {
        **zero_receipt["pre"],
        "relayerBalance": zero_receipt["pre"]["relayerTokenBalance"],
        "recipientBalance": zero_receipt["pre"]["recipientTokenBalance"],
    }
    return {
        "D1P-12R_honest": {
            "proof": honest_proof, "pre": honest_receipt["pre"],
            "basefee": number(honest_receipt["block"]["baseFeePerGas"]),
            "expected_success": True, "expected_path": "p18",
        },
        "D1P-12R_replay": {
            "proof": honest_proof, "pre": replay_pre,
            "basefee": number(honest_receipt["block"]["baseFeePerGas"]),
            "expected_success": False, "expected_path": "p02",
        },
        "D1P-14A_FC-POS": {
            "proof": fc_proof, "pre": fc_pos["pre"],
            "basefee": number(fc_pos["block"]["baseFeePerGas"]),
            "expected_success": True, "expected_path": "p18",
        },
        "D1P-14A_FC-NEG": {
            "proof": fc_proof, "pre": fc_neg_pre,
            "basefee": number(fc_neg["block"]["baseFeePerGas"]),
            "expected_success": False, "expected_path": "p06",
        },
        "D1P-14A_zero-fee": {
            "proof": zero_proof, "pre": zero_pre,
            "basefee": number(zero_receipt["block"]["baseFeePerGas"]),
            "expected_success": True, "expected_path": "p21",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--relation", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output = args.output_dir.resolve()
    prepared = output / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    relation = load_extracted_relation(args.relation)
    consumer_ir = serialize_consumer_ir(relation)
    consumer_ir["source_relation_path"] = str(args.relation.resolve())
    consumer_ir["source_relation_file_sha256"] = sha256(args.relation)
    write_json(output / "extracted-consumer-ir.json", consumer_ir)
    write_json(output / "manual-input-manifest.json", manual_input_manifest(relation))

    identities = {
        "openzeppelin": {
            "version": "5.6.1",
            "status": "EXTRACTED identity; behavior authorized by versioned manual effect-model entries",
        }
    }
    fc_proof = load(args.paper_root / "results/raw/D1P-14A/fc-pos-proof.json")
    fc_receipt = load(args.paper_root / "results/raw/D1P-14A/fc-pos-receipt.json")
    fixture = freeze_honest_fixture(fc_proof, fc_receipt)
    s0 = fixture["admitted_state"]

    manual_direct = manual.build_omega(
        args.artifact, goal="AUTH-1", s0=s0, identities=identities
    )
    manual_wrapped = build_omega(
        args.artifact, goal="AUTH-1", s0=s0, identities=identities
    )
    if manual.canonical_bytes(manual_direct) != manual.canonical_bytes(manual_wrapped):
        raise AssertionError("MANUAL default Omega changed")
    manual_direct_query, manual_direct_certificate = manual.encode_query(
        manual_direct, drop_producer=True, backend_option="BASE"
    )
    manual_wrapped_query, manual_wrapped_certificate = encode_query(
        manual_wrapped, drop_producer=True, backend_option="BASE"
    )
    if (manual_direct_query != manual_wrapped_query or
            manual_direct_certificate != manual_wrapped_certificate):
        raise AssertionError("MANUAL default query or certificate changed")

    extracted = build_omega(
        args.artifact, goal="AUTH-1", s0=s0, identities=identities,
        consumer_model="EXTRACTED", relation_path=args.relation,
    )
    full_query, full_certificate = encode_query(
        extracted, consumer_model="EXTRACTED", drop_producer=False,
    )
    (prepared / "extracted-base-full.smt2").write_bytes(full_query)
    write_json(prepared / "extracted-base-full.certificate.json", full_certificate)
    full_parse = run_solver(args.solver, full_query, parse_only=True)
    if full_parse["returncode"] != 0:
        raise AssertionError(full_parse)

    manual_tarith, manual_tarith_certificate = encode_query(
        manual_wrapped, drop_producer=True, backend_option="T-ARITH"
    )
    extracted_tarith, extracted_tarith_certificate = encode_query(
        extracted, consumer_model="EXTRACTED", drop_producer=True,
        backend_option="T-ARITH",
    )
    (prepared / "extracted-tarith-drop.smt2").write_bytes(extracted_tarith)
    write_json(prepared / "extracted-tarith-drop.certificate.json", extracted_tarith_certificate)
    tarith_parse = run_solver(args.solver, extracted_tarith, parse_only=True)
    tarith_checks = {
        "manual_declares_one_fresh_fee": manual_tarith.count(
            b"(declare-const fee_amount (_ BitVec 256))") == 1,
        "extracted_declares_one_fresh_fee": extracted_tarith.count(
            b"(declare-const fee_amount (_ BitVec 256))") == 1,
        "manual_removes_concrete_fee_definition": b"(define-fun fee_amount" not in manual_tarith,
        "extracted_removes_concrete_fee_definition": b"(define-fun fee_amount" not in extracted_tarith,
        "same_backend_option": manual_tarith_certificate["backend_option"]
        == extracted_tarith_certificate["backend_option"] == "T-ARITH",
        "extracted_retains_22_paths": extracted_tarith_certificate[
            "path_families_serialized"] == 22,
        "extracted_query_parses": tarith_parse["returncode"] == 0,
    }
    if not all(tarith_checks.values()):
        raise AssertionError(tarith_checks)

    concrete_results = {}
    prior_comparison = load(Path(args.relation).parent / "five-execution-comparison.json")
    for name, case in concrete_cases(args.paper_root).items():
        omega = build_omega(
            args.artifact,
            goal="AUTH-1",
            s0=state_from_pre(case["proof"], case["pre"]),
            identities=identities,
            consumer_model="EXTRACTED",
            relation_path=args.relation,
        )
        base, certificate = encode_query(
            omega, consumer_model="EXTRACTED", drop_producer=True
        )
        query = fixed_terminal_query(
            base, words=words(case["proof"]), basefee=case["basefee"]
        )
        result = run_solver(args.solver, query)
        observed = result["stdout"].splitlines()[0] if result["stdout"] else ""
        expected = "sat" if case["expected_success"] else "unsat"
        prior = prior_comparison["cases"][name]
        checks = {
            "solver_matches_recorded_success": observed == expected,
            "prior_relation_path_matches": prior["selected_path"] == case["expected_path"],
            "prior_relation_had_no_disagreement": prior["disagreements"] == [],
            "query_balanced": manual.balanced_smt_parentheses(query)["balanced"],
        }
        if not all(checks.values()):
            raise AssertionError({"case": name, "result": result, "checks": checks})
        concrete_results[name] = {
            "expected_solver_result": expected,
            "observed_solver_result": observed,
            "selected_extracted_path": prior["selected_path"],
            "status": prior["status"],
            "checks": checks,
            "query_sha256": result["query_sha256"],
            "certificate_sha256": hashlib.sha256(
                manual.canonical_bytes(certificate)
            ).hexdigest(),
        }
    concrete_report = {
        "schema": "bindcheck.d1p20.concrete-validation/v1",
        "classification": "fixed archived execution validation; not a primary solver campaign",
        "cases": concrete_results,
        "all_checks_pass": True,
    }
    write_json(output / "concrete-executions.json", concrete_report)

    controls = {}
    policy_hashes = set()
    for control_id, target in CONTROL_VARIANTS.items():
        for polarity in ("positive", "negative"):
            omega = build_omega(
                args.artifact,
                goal="AUTH-1",
                s0=s0,
                identities=identities,
                consumer_model="EXTRACTED",
                relation_path=args.relation,
                control_id=control_id if polarity == "positive" else None,
            )
            base, certificate = encode_query(
                omega, consumer_model="EXTRACTED", drop_producer=True
            )
            query = fixed_terminal_query(
                base,
                words=[int(value) for value in fixture["public_words"]],
                basefee=int(fixture["environment"]["basefee"]),
                designated_goal=target,
            )
            slot = f"{control_id}{'P' if polarity == 'positive' else 'N'}"
            query_path = prepared / f"{slot.lower()}-{target.lower()}.smt2"
            query_path.write_bytes(query)
            result = run_solver(args.solver, query)
            observed = result["stdout"].splitlines()[0] if result["stdout"] else ""
            expected = "sat" if polarity == "positive" else "unsat"
            if observed != expected:
                raise AssertionError({"slot": slot, "expected": expected, "result": result})
            policy_hashes.add(manual.canonical_sha256(omega["policy"]))
            control_certificate = {
                "schema": "bindcheck.d1p20.control/v1",
                "slot": slot,
                "control": control_id,
                "polarity": polarity,
                "target": target,
                "expected": expected,
                "observed": observed,
                "base_transformation": certificate,
                "fixed_query_sha256": result["query_sha256"],
                "fixed_query_bytes": result["query_bytes"],
                "classification": "D1P-14D deterministic control replay over EXTRACTED adapter",
            }
            write_json(prepared / f"{slot.lower()}-certificate.json", control_certificate)
            controls[slot] = {
                "target": target,
                "expected": expected,
                "observed": observed,
                "query_sha256": result["query_sha256"],
                "returncode": result["returncode"],
                "stderr": result["stderr"],
            }
    if len(policy_hashes) != 1:
        raise AssertionError("policy changed across controls")
    controls_report = {
        "schema": "bindcheck.d1p20.d1p14d-controls/v1",
        "classification": "eight deterministic controls; not primary search or performance evidence",
        "policy_sha256": next(iter(policy_hashes)),
        "results": controls,
        "positive_sat": sum(item["observed"] == "sat" for key, item in controls.items() if key.endswith("P")),
        "negative_unsat": sum(item["observed"] == "unsat" for key, item in controls.items() if key.endswith("N")),
        "all_checks_pass": True,
    }
    write_json(output / "d1p14d-controls.json", controls_report)

    manual_comparison = load(Path(args.relation).parent / "manual-regression-comparison.json")
    differences = manual_comparison["disagreements"]
    expected_kinds = [
        "revert precedence and tentative trace",
        "producer/consumer boundary placement",
    ]
    if [item["kind"] for item in differences] != expected_kinds:
        raise AssertionError("manual differences changed")
    difference_report = {
        "schema": "bindcheck.d1p20.manual-differences/v1",
        "rule": "preserve and explain; do not force equality to the less-faithful manual summary",
        "differences": differences,
        "five_archived_execution_disagreements": manual_comparison["agreements"][
            "five_concrete_disagreements"
        ],
    }
    write_json(output / "manual-differences.json", difference_report)

    validation = {
        "schema": "bindcheck.d1p20.validation/v1",
        "status": "PASS",
        "consumer_models": ["MANUAL", "EXTRACTED"],
        "manual_default_unchanged": True,
        "extracted_relation_file_sha256": sha256(args.relation),
        "extracted_ir_sha256": sha256(output / "extracted-consumer-ir.json"),
        "full_extracted_query": {
            "path": "prepared/extracted-base-full.smt2",
            "sha256": sha256(prepared / "extracted-base-full.smt2"),
            "parse_only": full_parse,
            "certificate": full_certificate,
        },
        "t_arith": {
            "checks": tarith_checks,
            "parse_only": tarith_parse,
            "all_checks_pass": True,
        },
        "concrete_executions": {"count": 5, "all_checks_pass": True},
        "d1p14d_controls": {
            "count": 8, "positive_sat": 4, "negative_unsat": 4,
            "all_checks_pass": True,
        },
        "manual_differences_preserved": len(differences),
        "solver_accounting": {
            "primary_solver_calls": 0,
            "parse_only_calls": 2,
            "fixed_archived_execution_validation_calls": 5,
            "deterministic_control_calls": 8,
        },
        "claim_scope": "extraction replaces the manual consumer summary on the tested WarpToad mint fragment; automatic obligation derivation remains open",
    }
    write_json(output / "validation.json", validation)
    print(json.dumps({
        "status": "PASS",
        "concrete_cases": len(concrete_results),
        "controls": len(controls),
        "primary_solver_calls": 0,
        "output": str(output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
