#!/usr/bin/env python3
"""D1P-14B first WarpToad joint encoder and frozen three-query runner."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from bindcheck_d1.joint_warptoad import (
    FIELD_MODULUS, PUBLIC_INPUTS, build_omega, canonical_bytes,
    canonical_sha256, encode_query, file_sha256, lower_mint,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-14B"
WORKSPACE = RAW / "workspace/source"
PREPARED = RAW / "prepared"
LOGS = RAW / "solver-logs"
COMMANDS = RAW / "command-records"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
D1P12R = ROOT / "results/raw/D1P-12R"
D1P13 = ROOT / "results/raw/D1P-13"
D1P14A = ROOT / "results/raw/D1P-14A"
SOURCE_ARTIFACT = D1P13 / "workspace/source/backend/circuits/withdraw/target/withdraw.json"
ARTIFACT = WORKSPACE / "backend/circuits/withdraw/target/withdraw.json"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
NARGO = D1P13 / "tools/nargo-beta22/nargo"
SPEC = Path("/Users/imranpollob/Coding/bc/bindcheck-lane-b/docs/d1-paper/d1p-b01-design.md")
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-07-resource-policy.json"
MONITOR_RUNNER = ROOT / "scripts/d1p_07_track_a.py"
BASE_RUNNER = ROOT / "scripts/d1p_05_validate.py"
MODULE = ROOT / "src/bindcheck_d1/joint_warptoad.py"
TEST = ROOT / "tests/d1/test_joint_warptoad.py"
STATE_TEMPLATE = ROOT / "scripts/fixtures/d1p_14b_state_snapshot.ts"
VECTOR_TEMPLATE = ROOT / "scripts/fixtures/D1P14BVectorVerifier.sol"
CANDIDATE_TEMPLATE = ROOT / "scripts/fixtures/d1p_14b_candidate_exec.ts"
STATE_FIXTURE = WORKSPACE / "backend/test/d1p14b.state.fixture.ts"
VECTOR_CONTRACT = WORKSPACE / "backend/contracts/test/D1P14BVectorVerifier.sol"
CANDIDATE_FIXTURE = WORKSPACE / "backend/test/d1p14b.candidate.fixture.ts"
MANIFEST = ROOT / "metadata/d1/d1p-14b-artifact-manifest.json"
PROTOCOL = ROOT / "protocols/d1/d1p-14b-joint.json"
LEDGER = RAW / "solver-ledger.json"
SEAL = RAW / "freeze-seal.json"

SOLVER_SHA256 = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGS = ["--lang=smt2", "--ff-solver=split", "--produce-models", "--dump-models"]
TIMEOUT_SECONDS = 300.0
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def json_safe(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(json_safe(item) for item in value)
    if isinstance(value, dict):
        return {str(key): json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(child) for child in value]
    return value


def record(path: Path, base: Path = ROOT) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": file_sha256(path), "bytes": path.stat().st_size,
    }


def tree_records(paths: list[Path]) -> list[dict[str, Any]]:
    values = []
    for root in paths:
        if root.is_file():
            values.append(record(root))
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            values.append(record(path))
    return values


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    COMMANDS.mkdir(parents=True, exist_ok=True)
    stdout_path = COMMANDS / f"{label}.stdout"
    stderr_path = COMMANDS / f"{label}.stderr"
    result_path = COMMANDS / f"{label}.json"
    if any(path.exists() for path in (stdout_path, stderr_path, result_path)):
        raise SystemExit(f"command evidence already exists: {label}")
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        try:
            completed = subprocess.run(
                argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                timeout=timeout, check=False,
            )
            exit_code, timed_out = completed.returncode, False
        except subprocess.TimeoutExpired:
            exit_code, timed_out = None, True
    payload = {
        "schema": "bindcheck.d1p14b.command/v1", "label": label,
        "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout,
        "timed_out": timed_out, "exit_code": exit_code,
        "wall_seconds": round(time.monotonic() - started, 6),
        "stdout": record(stdout_path, RAW), "stderr": record(stderr_path, RAW),
    }
    write_json(result_path, payload)
    return payload


def require_workspace() -> None:
    if not (WORKSPACE / ".git").exists():
        raise SystemExit("run setup first")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    if head != PIN:
        raise SystemExit(f"workspace HEAD mismatch: {head}")


def hardhat_test(fixture: str) -> list[str]:
    return [
        str(WORKSPACE / "backend/node_modules/.bin/hardhat"), "test",
        "--network", "edr", "--no-compile", fixture,
    ]


def stage_setup() -> int:
    if (RAW / "setup.json").exists() or WORKSPACE.exists():
        raise SystemExit("D1P-14B setup namespace is not fresh")
    RAW.mkdir(parents=True)
    preserve_roots = [
        ROOT / "results/raw/D1P-12", D1P12R, D1P13, D1P14A,
        ROOT / "reports/D1P-12.md", ROOT / "reports/D1P-12R.md",
        ROOT / "reports/D1P-13.md", ROOT / "reports/D1P-14A.md",
    ]
    preservation = tree_records(preserve_roots)
    clone = run_recorded(
        "clone-pinned-project",
        ["git", "clone", "--no-hardlinks", str(D1P12R / "workspace/source"), str(WORKSPACE)],
        ROOT, 600,
    )
    if clone["exit_code"] != 0:
        return clone["exit_code"] or 1
    checkout = run_recorded(
        "checkout-pinned-project", ["git", "checkout", "--detach", PIN], WORKSPACE, 300,
    )
    if checkout["exit_code"] != 0:
        return checkout["exit_code"] or 1
    for relative in ("node_modules", "backend/node_modules"):
        link = WORKSPACE / relative
        target = D1P12R / "workspace/source" / relative
        link.symlink_to(target, target_is_directory=True)
    shutil.copytree(D1P12R / "workspace/source/backend/artifacts", WORKSPACE / "backend/artifacts")
    shutil.copytree(D1P12R / "workspace/source/backend/cache", WORKSPACE / "backend/cache")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_ARTIFACT, ARTIFACT)
    shutil.copy2(STATE_TEMPLATE, STATE_FIXTURE)
    shutil.copy2(VECTOR_TEMPLATE, VECTOR_CONTRACT)
    shutil.copy2(CANDIDATE_TEMPLATE, CANDIDATE_FIXTURE)

    compile_result = run_recorded(
        "compile-validation-overlay",
        [str(WORKSPACE / "backend/node_modules/.bin/hardhat"), "compile"],
        WORKSPACE / "backend", 1200,
    )
    if compile_result["exit_code"] != 0:
        return compile_result["exit_code"] or 1
    state_path = RAW / "fixed-s0.json"
    snapshot = run_recorded(
        "fixed-s0-snapshot", hardhat_test("test/d1p14b.state.fixture.ts"),
        WORKSPACE / "backend", 600, {"D1P14B_STATE": str(state_path)},
    )
    if snapshot["exit_code"] != 0 or not state_path.exists():
        return snapshot["exit_code"] or 1

    d1p11 = json.loads((ROOT / "results/raw/D1P-11/retrieved-source-hashes.json").read_text())
    source_checks = []
    for item in d1p11["sources"]:
        if item.get("application") != "warp-toad":
            continue
        path = WORKSPACE / item["path"]
        actual = file_sha256(path)
        source_checks.append({
            "path": item["path"], "expected_sha256": item["sha256"],
            "actual_sha256": actual, "matches": actual == item["sha256"],
        })
    setup = {
        "schema": "bindcheck.d1p14b.setup/v1", "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "host": {"platform": platform.platform(), "machine": platform.machine(),
                 "python": sys.version.split()[0], "logical_cpus": os.cpu_count()},
        "network": {"kind": "Hardhat edr-simulated", "fork": False, "live_chain": False},
        "preservation_baseline": preservation,
        "source_checks": source_checks,
        "source_checks_all_match": all(item["matches"] for item in source_checks),
        "workspace": {
            "head": PIN, "clone": clone, "checkout": checkout,
            "dependency_links": ["node_modules", "backend/node_modules"],
            "artifact": record(ARTIFACT), "overlay_compile": compile_result,
            "fixed_s0": record(state_path), "snapshot_command": snapshot,
            "overlays": [record(STATE_FIXTURE), record(VECTOR_CONTRACT), record(CANDIDATE_FIXTURE)],
        },
        "bounds": {"solver_calls": 0, "proof_generation_calls": 0},
    }
    write_json(RAW / "setup.json", setup)
    return 0 if setup["source_checks_all_match"] else 1


def words_from_inputs(inputs: dict[str, Any]) -> list[int]:
    return [int(inputs[name], 0) for name in PUBLIC_INPUTS]


def concrete_state(*, root: int, giga: int, total_supply: int,
                   relayer: int, recipient: int, nullifier: int | None = None) -> dict[str, Any]:
    return {
        "giga_roots": {giga}, "local_roots": {root},
        "nullifiers": set() if nullifier is None else {nullifier},
        "total_supply": total_supply, "balances": {relayer: 0, recipient: 0},
    }


def validate_controls() -> dict[str, Any]:
    honest = json.loads((D1P12R / "execution-result.json").read_text())
    honest_receipt = json.loads((D1P12R / "mint-receipt.json").read_text())
    relayer = int(honest["proofInputs"]["relayer_address"], 0)
    recipient = int(honest["proofInputs"]["recipient_address"], 0)
    nullifier = int(honest["proofInputs"]["nullifier"], 0)
    base_state = concrete_state(
        root=int(honest["proofInputs"]["destination_local_root"], 0),
        giga=int(honest["proofInputs"]["giga_root"], 0),
        total_supply=int(honest["mint"]["pre"]["totalSupply"]),
        relayer=relayer, recipient=recipient,
    )
    honest_lowered = lower_mint(
        words_from_inputs(honest["proofInputs"]),
        basefee=int(honest_receipt["block"]["baseFeePerGas"]), state=base_state,
        msg_sender=relayer,
    )
    replay_state = dict(base_state)
    replay_state["nullifiers"] = {nullifier}
    replay_lowered = lower_mint(
        words_from_inputs(honest["proofInputs"]),
        basefee=int(honest_receipt["block"]["baseFeePerGas"]), state=replay_state,
        msg_sender=relayer,
    )

    pos = json.loads((D1P14A / "fc-pos-receipt.json").read_text())
    neg = json.loads((D1P14A / "fc-neg-receipt.json").read_text())
    pos_proof = json.loads((D1P14A / "fc-pos-proof.json").read_text())
    pi = pos_proof["proofInputs"]
    pos_state = concrete_state(
        root=int(pi["destination_local_root"], 0), giga=int(pi["giga_root"], 0),
        total_supply=int(pos["pre"]["totalSupply"]),
        relayer=int(pi["relayer_address"], 0), recipient=int(pi["recipient_address"], 0),
    )
    pos_lowered = lower_mint(
        words_from_inputs(pi), basefee=int(pos["block"]["baseFeePerGas"]),
        state=pos_state, msg_sender=int(pi["relayer_address"], 0),
    )
    neg_lowered = lower_mint(
        words_from_inputs(pi), basefee=int(neg["block"]["baseFeePerGas"]),
        state=pos_state, msg_sender=int(pi["relayer_address"], 0),
    )

    zero = json.loads((D1P14A / "zero-fee-receipt.json").read_text())
    zi = zero["proofInputs"]
    zero_state = concrete_state(
        root=int(zi["destination_local_root"], 0), giga=int(zi["giga_root"], 0),
        total_supply=int(zero["pre"]["totalSupply"]),
        relayer=int(zi["relayer_address"], 0), recipient=int(zi["recipient_address"], 0),
    )
    zero_lowered = lower_mint(
        words_from_inputs(zi), basefee=int(zero["block"]["baseFeePerGas"]),
        state=zero_state, msg_sender=int(zi["relayer_address"], 0),
    )
    canonicality = json.loads((D1P12R / "canonicality.json").read_text())
    checks = {
        "honest_success": honest_lowered["success"],
        "honest_fee_exact": honest_lowered["aggregates"]["fee_amount"] == int(honest["mint"]["computedRelayerFee"]),
        "honest_conservation": honest_lowered["aggregates"]["total_minted"] == int(honest["proofInputs"]["amount"], 0),
        "honest_auth_goals_false": not honest_lowered["auth_violation"],
        "honest_nonvac_true": honest_lowered["nonvac"],
        "replay_reject_location": replay_lowered["revert_location"] == "WarpToadCore.sol:157",
        "replay_no_occurrences": replay_lowered["occurrences"] == [],
        "fc_pos_success": pos_lowered["success"],
        "fc_pos_amounts_exact": pos_lowered["aggregates"]["fee_amount"] == int(pos["effects"]["relayerDelta"])
                                and pos_lowered["aggregates"]["recipient_amount"] == int(pos["effects"]["recipientDelta"]),
        "fc_neg_cap_revert": neg_lowered["revert_location"] == "WarpToadCore.sol:166",
        "fc_neg_rollback": neg_lowered["occurrences"] == [] and neg["consumerState"]["unchanged"],
        "zero_success": zero_lowered["success"],
        "zero_recipient_only": [o["role"] for o in zero_lowered["occurrences"]] == ["RECIPIENT"],
        "canonicality_22_reverts": len(canonicality["cases"]) == 22 and all(case["behavior"] == "reverted" for case in canonicality["cases"]),
        "d1p13_supported_constraints_satisfied": json.loads((D1P13 / "semantic-check.json").read_text())["honest_supported_check"]["all_supported_constraints_satisfied"],
    }
    return {
        "schema": "bindcheck.d1p14b.lowering-validation/v1",
        "created_at_utc": utc_now(), "checks": checks,
        "all_checks_pass": all(checks.values()),
        "cases": {
            "D1P-12R_honest": json_safe(honest_lowered),
            "D1P-12R_replay": json_safe(replay_lowered),
            "D1P-14A_FC-POS": json_safe(pos_lowered),
            "D1P-14A_FC-NEG": json_safe(neg_lowered),
            "D1P-14A_zero-fee": json_safe(zero_lowered),
        },
        "evidence": [
            record(D1P12R / "execution-result.json"), record(D1P12R / "mint-receipt.json"),
            record(D1P12R / "canonicality.json"), record(D1P13 / "semantic-check.json"),
            record(D1P14A / "fc-pos-receipt.json"), record(D1P14A / "fc-neg-receipt.json"),
            record(D1P14A / "zero-fee-receipt.json"),
        ],
    }


def make_identities() -> dict[str, Any]:
    source = WORKSPACE / "backend/contracts/core/WarpToadCore.sol"
    lock = WORKSPACE / "pnpm-lock.yaml"
    oz = WORKSPACE / "node_modules/.pnpm/@openzeppelin+contracts@5.6.1/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol"
    source_tree = "\n".join(path.read_text(errors="replace") for path in sorted((WORKSPACE / "backend/contracts").rglob("*.sol")))
    override_matches = [line for line in source_tree.splitlines() if "function _update" in line]
    return {
        "specification": {**record(SPEC), "controlling_section": "amended section 6"},
        "consumer": {**record(source), "format_lines": "114-140", "mint_lines": "143-177"},
        "openzeppelin": {
            "status": "EXTRACTED", "requested": "^5.2.0", "resolved": "5.6.1",
            "lockfile": record(lock), "erc20_source": record(oz),
            "mint_lines": "ERC20.sol:214-218", "update_lines": "ERC20.sol:176-203",
            "warptoad_update_override": False,
            "override_search_note": "only the vendored backend/contracts/test/ERC206Dec.sol defines an unrelated _update; WarpToadCore/L1WarpToad do not override OpenZeppelin ERC20._update",
            "contract_tree_update_definition_count": len(override_matches),
        },
        "artifact": record(ARTIFACT),
        "decoder": record(ROOT / "src/bindcheck_d1/frontends/acir_binary_beta22.py"),
        "solver": {**record(SOLVER), "version": "cvc5 1.4.2 git 282d5e0", "architecture": "arm64", "expected_sha256": SOLVER_SHA256},
        "resource_policy": record(RESOURCE_POLICY),
        "monitor_runner": record(MONITOR_RUNNER), "base_monitor": record(BASE_RUNNER),
        "nargo": {**record(NARGO), "version": "1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7"},
    }


def stage_prepare() -> int:
    require_workspace()
    if MANIFEST.exists() or SEAL.exists():
        raise SystemExit("freeze already exists; preparation is immutable")
    PREPARED.mkdir(parents=True, exist_ok=True)
    if any(PREPARED.iterdir()):
        raise SystemExit("partial prepared query material exists; refusing to overwrite")
    controls_path = RAW / "lowering-validation.json"
    if controls_path.exists():
        controls = json.loads(controls_path.read_text())
    else:
        controls = validate_controls()
        write_json(controls_path, controls)
    if not controls["all_checks_pass"]:
        raise SystemExit("concrete lowering validation failed")
    first_test_record = COMMANDS / "focused-tests-before-freeze.json"
    test_label = "focused-tests-before-freeze-retry" if first_test_record.exists() else "focused-tests-before-freeze"
    pytest_executable = shutil.which("pytest")
    if not pytest_executable:
        raise SystemExit("pytest executable unavailable")
    tests = run_recorded(
        test_label,
        [pytest_executable, "-q", "tests/d1/test_joint_warptoad.py", "tests/d1/test_acir_beta22.py"],
        ROOT, 300, {"PYTHONPATH": str(ROOT / "src")},
    )
    if tests["exit_code"] != 0:
        return tests["exit_code"] or 1
    s0_raw = json.loads((RAW / "fixed-s0.json").read_text())
    s0 = {
        "provenance": record(RAW / "fixed-s0.json"),
        "giga_root_history": s0_raw["giga_root_history"],
        "local_root_history": s0_raw["local_root_history"],
        "nullifiers": s0_raw["nullifiers"], "total_supply": s0_raw["total_supply"],
        "fixed_assumption": "state immediately after the D1P-12R honest burn and before mint; includes the initialization root history entry",
    }
    identities = make_identities()
    if identities["solver"]["sha256"] != SOLVER_SHA256:
        raise SystemExit("pinned solver hash mismatch")
    auth = build_omega(ARTIFACT, goal="AUTH-1", s0=s0, identities=identities)
    nonvac = build_omega(ARTIFACT, goal="NONVAC-1", s0=s0, identities=identities)
    omega_auth_path = PREPARED / "omega-auth1.json"
    omega_nonvac_path = PREPARED / "omega-nonvac1.json"
    omega_auth_path.write_bytes(canonical_bytes(auth))
    omega_nonvac_path.write_bytes(canonical_bytes(nonvac))
    schedule = [
        ("Q1", auth, True, PREPARED / "q1-auth1-r-dropped.smt2"),
        ("Q2", auth, False, PREPARED / "q2-auth1-monolithic.smt2"),
        ("Q3", nonvac, False, PREPARED / "q3-nonvac1-monolithic.smt2"),
    ]
    transformations = []
    for name, omega, dropped, query_path in schedule:
        query, certificate = encode_query(omega, drop_producer=dropped)
        query_path.write_bytes(query)
        certificate.update({"query": name, "path": str(query_path.relative_to(ROOT))})
        certificate_path = PREPARED / f"{name.lower()}-transformation.json"
        write_json(certificate_path, certificate)
        transformations.append({
            "name": name, "goal": omega["goal"]["name"],
            "drop_producer": dropped, "omega": record(omega_auth_path if name != "Q3" else omega_nonvac_path),
            "query": record(query_path), "transformation": record(certificate_path),
        })
    anchor = json.loads((D1P13 / "honest-witness.json").read_text())
    anchor_check = {
        "schema": "bindcheck.d1p14b.anchor-check/v1",
        "scope_match": {
            "chain_id_31337": int(anchor["publicWitnesses"][1]["value"], 0) == 31337,
            "named_relayer": int(anchor["publicWitnesses"][9]["value"], 0) != 1,
            "nonzero_fee_factor": int(anchor["publicWitnesses"][6]["value"], 0) != 0,
            "public_vector_matches_accepted_proof": anchor["publicWitnessesMatchAcceptedProof"],
            "supported_constraints_satisfied": controls["checks"]["d1p13_supported_constraints_satisfied"],
            "real_verifier_accepted": json.loads((D1P12R / "execution-result.json").read_text())["verifier"]["accepted"],
            "real_consumer_execution_success": controls["checks"]["honest_success"],
            "auth_goals_all_false": controls["checks"]["honest_auth_goals_false"],
            "nonvac_true": controls["checks"]["honest_nonvac_true"],
        },
        "policy_match": "F2a/F4/F5 plus occurrence and nullifier linkage only; DRAFT policy; no F3 or F9",
        "grade": "real-proof anchor for the exact committed artifact/generated verifier/owned-local T_mint route",
        "limitation": "does not establish hash completeness, verifier soundness, cross-chain reachability, or a D1 verdict",
        "evidence": [record(D1P13 / "honest-witness.json"), record(D1P12R / "honest-proof.json"), record(D1P12R / "mint-receipt.json")],
    }
    anchor_check["all_scope_checks_pass"] = all(anchor_check["scope_match"].values())
    write_json(RAW / "anchor-check.json", anchor_check)
    if not anchor_check["all_scope_checks_pass"]:
        raise SystemExit("D1P-12R anchor mismatch")

    hashed_inputs = [
        MODULE, Path(__file__), TEST, STATE_TEMPLATE, VECTOR_TEMPLATE, CANDIDATE_TEMPLATE,
        PROTOCOL, SPEC, RESOURCE_POLICY, MONITOR_RUNNER, BASE_RUNNER, SOLVER, NARGO,
        ARTIFACT, WORKSPACE / "backend/contracts/core/WarpToadCore.sol",
        WORKSPACE / "pnpm-lock.yaml",
        WORKSPACE / "node_modules/.pnpm/@openzeppelin+contracts@5.6.1/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol",
        RAW / "fixed-s0.json", RAW / "lowering-validation.json", RAW / "anchor-check.json",
        omega_auth_path, omega_nonvac_path,
    ]
    for item in transformations:
        hashed_inputs.extend([ROOT / item["query"]["path"], ROOT / item["transformation"]["path"]])
    manifest = {
        "schema": "bindcheck.d1p14b.frozen-manifest/v1", "frozen_at_utc": utc_now(),
        "pinned_revision": PIN, "specification": record(SPEC),
        "canonical_serialization": "UTF-8 JSON, sorted keys, compact separators, ensure_ascii=false, allow_nan=false, no trailing LF",
        "omega": {"AUTH-1": record(omega_auth_path), "NONVAC-1": record(omega_nonvac_path)},
        "queries": transformations,
        "schedule": ["Q1 AUTH-1 with R_v dropped", "Q2 AUTH-1 monolithic", "Q3 NONVAC-1 monolithic"],
        "solver": identities["solver"], "solver_arguments": SOLVER_ARGS,
        "bounds": {"attempts_per_query": 1, "timeout_seconds_each": 300,
                   "solver_seconds_maximum": 900, "sequential": True,
                   "rss_sample_interval_seconds": SAMPLE_INTERVAL,
                   "observed_rss_cutoff_bytes": RSS_CUTOFF, "hard_address_space_cap": False,
                   "tuning_or_refinement_after_freeze": False},
        "validation": {
            "sat_candidates_per_query_maximum": 1, "nargo_timeout_seconds": 600,
            "consumer_timeout_seconds": 600,
            "route": "section 6(b): full ABI candidate -> pinned nargo execute -> fresh EDR S0 -> exact-vector verifier stub -> unchanged T_mint",
            "sat_without_complete_validation": "UNKNOWN",
        },
        "identities": identities,
        "hash_complete_inputs": [record(path) for path in hashed_inputs],
        "pre_solver_checks": {"focused_tests": tests, "lowering": record(RAW / "lowering-validation.json"),
                              "anchor": record(RAW / "anchor-check.json")},
        "claims_excluded": ["D1 verdict", "consumer direction", "hash completeness", "collision resistance", "knowledge soundness", "performance result"],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    write_json(MANIFEST, manifest)
    write_json(SEAL, {"schema": "bindcheck.d1p14b.freeze-seal/v1", "manifest": record(MANIFEST),
                      "solver_calls_at_freeze": 0, "frozen_at_utc": utc_now()})
    return 0


def verify_frozen_manifest() -> dict[str, Any]:
    if not MANIFEST.exists() or not SEAL.exists():
        raise SystemExit("frozen manifest/seal absent")
    seal = json.loads(SEAL.read_text())
    if seal["manifest"]["sha256"] != file_sha256(MANIFEST):
        raise SystemExit("manifest changed after freeze")
    manifest = json.loads(MANIFEST.read_text())
    for item in manifest["hash_complete_inputs"]:
        path = ROOT / item["path"] if not Path(item["path"]).is_absolute() else Path(item["path"])
        if not path.exists() or file_sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"frozen input mismatch: {item['path']}")
    if file_sha256(SOLVER) != SOLVER_SHA256:
        raise SystemExit("solver identity mismatch")
    return manifest


def load_monitor_module():
    spec = importlib.util.spec_from_file_location("d1p14b_d1p07_monitor", MONITOR_RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def solver_answer(record_value: dict[str, Any]) -> str:
    if record_value["status"] != "COMPLETED":
        return "UNKNOWN"
    stdout = (ROOT / record_value["stdout_path"]).read_text(errors="replace")
    for line in stdout.splitlines():
        value = line.strip().lower()
        if value in {"sat", "unsat", "unknown"}:
            return value.upper()
    return "UNKNOWN"


def stage_run() -> int:
    manifest = verify_frozen_manifest()
    if LEDGER.exists() or LOGS.exists():
        raise SystemExit("solver evidence already exists; exactly-one-attempt rule")
    d1p07 = load_monitor_module()
    monitor = d1p07.D1P05.MacProcessTreeMonitor()
    ledger: dict[str, Any] = {
        "schema": "bindcheck.d1p14b.solver-ledger/v1", "started_at_utc": utc_now(),
        "manifest": record(MANIFEST), "schedule": manifest["schedule"], "queries": [],
        "bounds": manifest["bounds"], "solver_calls": 0,
    }
    infrastructure_failure = None
    for index, query in enumerate(manifest["queries"], start=1):
        verify_frozen_manifest()
        query_path = ROOT / query["query"]["path"]
        call = d1p07.run_monitored(
            index=index, kind="primary", name=query["name"],
            argv=[str(SOLVER), *SOLVER_ARGS], logs_dir=LOGS,
            monitor=monitor, input_path=query_path,
            timeout_seconds=TIMEOUT_SECONDS, rss_cutoff_bytes=RSS_CUTOFF,
            sample_interval_seconds=SAMPLE_INTERVAL,
        )
        call["answer"] = solver_answer(call)
        call["query_role"] = query
        ledger["queries"].append(call)
        ledger["solver_calls"] += 1
        write_json(LEDGER, ledger)
        if call["status"] in {"LAUNCH_ERROR", "MONITOR_ERROR", "TERMINATION_ERROR", "EXIT_WAIT_TIMEOUT", "RUNNER_ERROR"}:
            infrastructure_failure = call["status"]
            break
    ledger["finished_at_utc"] = utc_now()
    ledger["infrastructure_failure"] = infrastructure_failure
    ledger["exactly_three_calls"] = ledger["solver_calls"] == 3
    ledger["charged_solver_seconds"] = round(sum(min(float(item["elapsed_seconds"]), 300.0) for item in ledger["queries"]), 6)
    ledger["within_900_solver_seconds"] = ledger["charged_solver_seconds"] <= 900.0
    ledger["answers"] = {item["name"]: item["answer"] for item in ledger["queries"]}
    write_json(LEDGER, ledger)
    return 0 if ledger["exactly_three_calls"] and ledger["within_900_solver_seconds"] else 1


BV_PATTERNS = [
    re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+#x([0-9a-fA-F]+)\)"),
    re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+#b([01]+)\)"),
    re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+\(_ bv(\d+) 256\)\)"),
]
FF_RE = re.compile(r"\(define-fun\s+w(\d+)\s+\(\)\s+(?:F|\(_ FiniteField \d+\))\s+(?:\(as ff(\d+) (?:F|\(_ FiniteField \d+\))\)|#f(\d+)m\d+)\)")


def parse_model(text: str) -> tuple[dict[str, int], dict[int, int]]:
    bv: dict[str, int] = {}
    for pattern_index, pattern in enumerate(BV_PATTERNS):
        for match in pattern.finditer(text):
            base = 16 if pattern_index == 0 else 2 if pattern_index == 1 else 10
            bv[match.group(1)] = int(match.group(2), base)
    ff = {int(match.group(1)): int(match.group(2) or match.group(3)) for match in FF_RE.finditer(text)}
    return bv, ff


def prover_toml(public: list[int], private: list[int]) -> str:
    value = lambda item: f'"0x{item:x}"'
    lines = [f"{name} = {value(public[index])}" for index, name in enumerate(PUBLIC_INPUTS)]
    lines.extend([
        f"origin_local_root = {value(private[0])}",
        f"is_from_aztec = {'true' if private[1] else 'false'}",
        f"nullifier_preimage = {value(private[2])}", f"secret = {value(private[3])}",
        "", "[aztec_merkle_data]", f"leaf_index = {value(private[4])}",
        "hash_path = [" + ", ".join(value(item) for item in private[5:47]) + "]",
        f"leaf_nonce = {value(private[47])}", "", "[evm_merkle_data]",
        f"leaf_index = {value(private[48])}",
        "hash_path = [" + ", ".join(value(item) for item in private[49:81]) + "]",
        "", "[giga_merkle_data]", f"leaf_index = {value(private[81])}",
        "hash_path = [" + ", ".join(value(item) for item in private[82:87]) + "]",
    ])
    return "\n".join(lines) + "\n"


def validate_sat(call: dict[str, Any]) -> dict[str, Any]:
    name = call["name"]
    output_dir = RAW / "validation" / name.lower()
    output_dir.mkdir(parents=True, exist_ok=False)
    stdout = (ROOT / call["stdout_path"]).read_text(errors="replace")
    bv, ff = parse_model(stdout)
    result: dict[str, Any] = {
        "schema": "bindcheck.d1p14b.sat-validation/v1", "query": name,
        "solver_output": record(ROOT / call["stdout_path"]),
        "model_parse": {"bitvectors": len(bv), "field_witnesses": len(ff)},
        "status": "UNKNOWN", "reason": None,
    }
    if any(f"pi{index}" not in bv for index in range(11)) or "basefee" not in bv:
        result["reason"] = "solver SAT output lacks the full public/basefee assignment"
        return result
    public = [bv[f"pi{index}"] for index in range(11)]
    honest = json.loads((D1P13 / "honest-witness.json").read_text())["witnesses"]
    private = []
    fallback = []
    for index in range(11, 98):
        if index in ff:
            private.append(ff[index])
        else:
            private.append(int(honest[str(index)], 0))
            fallback.append(index)
    candidate = {
        "schema": "bindcheck.d1p14b.candidate/v1", "query": name,
        "public_words": [str(item) for item in public],
        "private_abi_witnesses_w11_w97": [str(item) for item in private],
        "private_fallback_from_honest_anchor": fallback,
        "basefee": str(bv["basefee"]),
        "msg_sender": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
        "intermediate_solver_witnesses_ignored": True,
    }
    candidate_path = output_dir / "candidate.json"
    write_json(candidate_path, candidate)
    prover_name = f"D1P14B_{name}"
    prover_path = WORKSPACE / "backend/circuits/withdraw" / f"{prover_name}.toml"
    prover_path.write_text(prover_toml(public, private))
    nargo_result = run_recorded(
        f"validate-{name.lower()}-nargo",
        [str(NARGO), "execute", f"d1p14b_{name.lower()}", "--prover-name", prover_name],
        WORKSPACE / "backend/circuits/withdraw", 600,
    )
    result["candidate"] = record(candidate_path)
    result["prover_input"] = record(prover_path)
    result["nargo"] = nargo_result
    if nargo_result["exit_code"] != 0 or nargo_result["timed_out"]:
        result["reason"] = "pinned beta.22 nargo execute did not validate the candidate"
        return result
    execution_path = output_dir / "consumer-execution.json"
    consumer = run_recorded(
        f"validate-{name.lower()}-consumer", hardhat_test("test/d1p14b.candidate.fixture.ts"),
        WORKSPACE / "backend", 600,
        {"D1P14B_CANDIDATE": str(candidate_path), "D1P14B_EXECUTION": str(execution_path)},
    )
    result["consumer_command"] = consumer
    if not execution_path.exists():
        result["reason"] = "fresh EDR consumer validation produced no result"
        return result
    result["consumer_execution"] = record(execution_path)
    execution = json.loads(execution_path.read_text())
    if consumer["exit_code"] != 0 or not execution.get("accepted"):
        result["reason"] = "unchanged consumer did not commit the candidate under exact-vector verification"
        return result
    result["status"] = "VALIDATED_SAT"
    result["reason"] = "full ABI passed pinned nargo execute and unchanged T_mint committed in fresh EDR S0 with exact-vector verifier stub"
    return result


def stage_validate() -> int:
    verify_frozen_manifest()
    ledger = json.loads(LEDGER.read_text())
    validation_path = RAW / "validation-summary.json"
    if validation_path.exists():
        raise SystemExit("validation already exists")
    results = []
    for call in ledger["queries"]:
        if call["answer"] == "SAT":
            result = validate_sat(call)
            write_json(RAW / "validation" / call["name"].lower() / "result.json", result)
        else:
            result = {"query": call["name"], "solver_answer": call["answer"],
                      "validation": "not applicable; V-EXEC is required only for SAT"}
        results.append(result)
    write_json(validation_path, {
        "schema": "bindcheck.d1p14b.validation-summary/v1",
        "created_at_utc": utc_now(), "results": results,
        "rule": "Every SAT is promoted only after the complete amended section 6(b) route; failures remain UNKNOWN.",
        "proof_generation_calls": 0,
    })
    return 0


def stage_audit() -> int:
    manifest = verify_frozen_manifest()
    ledger = json.loads(LEDGER.read_text())
    validation = json.loads((RAW / "validation-summary.json").read_text())
    setup = json.loads((RAW / "setup.json").read_text())
    preservation = []
    for item in setup["preservation_baseline"]:
        path = ROOT / item["path"]
        actual = file_sha256(path)
        preservation.append({**item, "actual_sha256": actual, "matches": actual == item["sha256"]})
    checks = {
        "frozen_manifest_still_exact": SEAL.exists(),
        "exactly_three_solver_calls": ledger["exactly_three_calls"],
        "one_attempt_per_query": len({item["name"] for item in ledger["queries"]}) == len(ledger["queries"]) == 3,
        "within_900_solver_seconds": ledger["within_900_solver_seconds"],
        "fixed_order": [item["name"] for item in ledger["queries"]] == ["Q1", "Q2", "Q3"],
        "all_sat_candidates_processed": sum(item["answer"] == "SAT" for item in ledger["queries"]) == sum(
            item.get("query") in {call["name"] for call in ledger["queries"] if call["answer"] == "SAT"}
            for item in validation["results"]
        ),
        "prior_evidence_unchanged": all(item["matches"] for item in preservation),
        "proof_generation_calls_zero": validation["proof_generation_calls"] == 0,
    }
    audit = {
        "schema": "bindcheck.d1p14b.audit/v1", "created_at_utc": utc_now(),
        "checks": checks, "all_checks_pass": all(checks.values()),
        "answers": ledger["answers"], "query_records": ledger["queries"],
        "manifest": record(MANIFEST), "freeze_seal": record(SEAL),
        "validation": record(RAW / "validation-summary.json"),
        "preservation": preservation,
        "interpretation_boundary": "AUTH-1 is pipeline fidelity only, not consumer-direction evidence; D1 remains UNKNOWN.",
    }
    write_json(RAW / "audit.json", audit)
    return 0 if audit["all_checks_pass"] else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["setup", "prepare", "run", "validate", "audit"])
    args = parser.parse_args()
    result = {
        "setup": stage_setup, "prepare": stage_prepare, "run": stage_run,
        "validate": stage_validate, "audit": stage_audit,
    }[args.stage]()
    raise SystemExit(result)


if __name__ == "__main__":
    main()
