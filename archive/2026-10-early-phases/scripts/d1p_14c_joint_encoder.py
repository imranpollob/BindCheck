#!/usr/bin/env python3
"""D1P-14C repaired, preflighted WarpToad AUTH-1/NONVAC-1 diagnostic."""

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
    PUBLIC_INPUTS, balanced_smt_parentheses, build_omega, canonical_bytes,
    canonical_sha256, encode_query, file_sha256, lower_mint,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-14C"
RAW_B = ROOT / "results/raw/D1P-14B"
WORKSPACE = RAW / "workspace/source"
PREPARED = RAW / "prepared"
COMMANDS = RAW / "command-records"
PARSE_LOGS = RAW / "parse-preflight-logs"
SOLVER_LOGS = RAW / "solver-logs"
VALIDATION = RAW / "validation"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
D1P12R = ROOT / "results/raw/D1P-12R"
D1P13 = ROOT / "results/raw/D1P-13"
D1P14A = ROOT / "results/raw/D1P-14A"
ARTIFACT_SOURCE = D1P13 / "workspace/source/backend/circuits/withdraw/target/withdraw.json"
ARTIFACT = WORKSPACE / "backend/circuits/withdraw/target/withdraw.json"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
NARGO = D1P13 / "tools/nargo-beta22/nargo"
MONITOR_RUNNER = ROOT / "scripts/d1p_07_track_a.py"
BASE_MONITOR = ROOT / "scripts/d1p_05_validate.py"
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-07-resource-policy.json"
SPEC = Path("/Users/imranpollob/Coding/bc/bindcheck-lane-b/docs/d1-paper/d1p-b01-design.md")
RESEARCH_CONTRACT = ROOT / "docs/research-contract.md"
MODULE = ROOT / "src/bindcheck_d1/joint_warptoad.py"
TEST = ROOT / "tests/d1/test_joint_warptoad.py"
PRESERVE_SCRIPT = ROOT / "scripts/d1p_14c_preserve.py"
CANDIDATE_TEMPLATE = ROOT / "scripts/fixtures/d1p_14c_candidate_exec.ts"
VECTOR_TEMPLATE = ROOT / "scripts/fixtures/D1P14BVectorVerifier.sol"
CANDIDATE_FIXTURE = WORKSPACE / "backend/test/d1p14c.candidate.fixture.ts"
VECTOR_CONTRACT = WORKSPACE / "backend/contracts/test/D1P14BVectorVerifier.sol"
PROTOCOL = ROOT / "protocols/d1/d1p-14c-joint-repair.json"
MANIFEST = ROOT / "metadata/d1/d1p-14c-artifact-manifest.json"
SEAL = RAW / "freeze-seal.json"
PREFLIGHT = RAW / "parse-preflight.json"
LEDGER = RAW / "solver-ledger.json"

SOLVER_SHA256 = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGS = ["--lang=smt2", "--ff-solver=split", "--produce-models", "--dump-models"]
PARSE_ARGS = ["--lang=smt2", "--parse-only"]
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05
RELAYER = int("70997970c51812dc3a010c7d01b50e0d17dc79c8", 16)

CONTROL_VARIANTS = {
    "C1": ("C1_FULL_RECIPIENT_PLUS_FEE", "G1"),
    "C2": ("C2_FEE_TO_RECIPIENT", "G3"),
    "C3": ("C3_EXTRA_MINT", "G4"),
    "C4": ("C4_WRONG_NULLIFIER_WRITE", "G5"),
}


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
    return {"path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
            "sha256": file_sha256(path), "bytes": path.stat().st_size}


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 env_extra: dict[str, str] | None = None,
                 input_path: Path | None = None) -> dict[str, Any]:
    COMMANDS.mkdir(parents=True, exist_ok=True)
    stdout_path = COMMANDS / f"{label}.stdout"
    stderr_path = COMMANDS / f"{label}.stderr"
    result_path = COMMANDS / f"{label}.json"
    if any(path.exists() for path in (stdout_path, stderr_path, result_path)):
        raise SystemExit(f"command evidence already exists: {label}")
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    source = input_path.open("rb") if input_path else None
    started = time.monotonic()
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            try:
                completed = subprocess.run(
                    argv, cwd=cwd, env=env, stdin=source,
                    stdout=stdout, stderr=stderr, timeout=timeout, check=False,
                )
                exit_code, timed_out = completed.returncode, False
            except subprocess.TimeoutExpired:
                exit_code, timed_out = None, True
    finally:
        if source:
            source.close()
    payload = {
        "schema": "bindcheck.d1p14c.command/v1", "label": label,
        "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout,
        "timed_out": timed_out, "exit_code": exit_code,
        "wall_seconds": round(time.monotonic() - started, 6),
        "stdout": record(stdout_path, RAW), "stderr": record(stderr_path, RAW),
        "input": record(input_path) if input_path else None,
    }
    write_json(result_path, payload)
    return payload


def require_workspace() -> None:
    if not (WORKSPACE / ".git").exists():
        raise SystemExit("D1P-14C setup is absent")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=WORKSPACE,
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != PIN:
        raise SystemExit(f"workspace HEAD mismatch: {head}")


def d1p14b_tree_identity() -> dict[str, Any]:
    files = sorted(path for path in RAW_B.rglob("*") if path.is_file())
    aggregate = hashlib.sha256()
    total = 0
    for path in files:
        relative = str(path.relative_to(RAW_B))
        item_hash, size = file_sha256(path), path.stat().st_size
        aggregate.update(f"{relative}\0{item_hash}\0{size}\n".encode())
        total += size
    return {"file_count": len(files), "regular_file_bytes": total,
            "ordered_path_hash_size_sha256": aggregate.hexdigest()}


def stage_setup() -> int:
    setup_path = RAW / "setup.json"
    if setup_path.exists() or WORKSPACE.exists():
        raise SystemExit("D1P-14C setup already exists")
    baseline = json.loads((RAW / "d1p14b-preservation-baseline.json").read_text())
    if d1p14b_tree_identity() != {key: baseline["d1p14b_raw_tree"][key]
                                  for key in ("file_count", "regular_file_bytes", "ordered_path_hash_size_sha256")}:
        raise SystemExit("D1P-14B raw evidence changed after preservation snapshot")
    clone = run_recorded(
        "clone-pinned-project", ["git", "clone", "--no-hardlinks",
                                 str(D1P12R / "workspace/source"), str(WORKSPACE)], ROOT, 600,
    )
    if clone["exit_code"] != 0:
        return clone["exit_code"] or 1
    checkout = run_recorded("checkout-pinned-project", ["git", "checkout", "--detach", PIN], WORKSPACE, 300)
    if checkout["exit_code"] != 0:
        return checkout["exit_code"] or 1
    for relative in ("node_modules", "backend/node_modules"):
        (WORKSPACE / relative).symlink_to(D1P12R / "workspace/source" / relative, target_is_directory=True)
    shutil.copytree(RAW_B / "workspace/source/backend/artifacts", WORKSPACE / "backend/artifacts")
    shutil.copytree(RAW_B / "workspace/source/backend/cache", WORKSPACE / "backend/cache")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ARTIFACT_SOURCE, ARTIFACT)
    shutil.copy2(CANDIDATE_TEMPLATE, CANDIDATE_FIXTURE)
    shutil.copy2(VECTOR_TEMPLATE, VECTOR_CONTRACT)
    shutil.copy2(RAW_B / "fixed-s0.json", RAW / "fixed-s0.json")
    setup = {
        "schema": "bindcheck.d1p14c.setup/v1", "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "host": {"platform": platform.platform(), "machine": platform.machine(),
                 "python": sys.version.split()[0], "logical_cpus": os.cpu_count()},
        "network": {"kind": "Hardhat edr-simulated", "fork": False, "live_chain": False},
        "d1p14b_preservation": record(RAW / "d1p14b-preservation-baseline.json"),
        "d1p14b_tree_recheck": d1p14b_tree_identity(),
        "workspace": {"clone": clone, "checkout": checkout, "artifact": record(ARTIFACT),
                      "candidate_fixture": record(CANDIDATE_FIXTURE), "vector_source": record(VECTOR_CONTRACT),
                      "copied_artifact": record(WORKSPACE / "backend/artifacts/contracts/test/D1P14BVectorVerifier.sol/D1P14BVectorVerifier.json")},
        "bounds": {"proof_generation_calls": 0, "solver_calls": 0, "parse_only_calls": 0},
    }
    write_json(setup_path, setup)
    return 0


def words_from_inputs(inputs: dict[str, Any]) -> list[int]:
    return [int(inputs[name], 0) for name in PUBLIC_INPUTS]


def state_for(inputs: dict[str, Any], total_supply: int, nullifier_used: bool = False) -> dict[str, Any]:
    nullifier = int(inputs["nullifier"], 0)
    return {
        "giga_roots": {int(inputs["giga_root"], 0)},
        "local_roots": {int(inputs["destination_local_root"], 0)},
        "nullifiers": {nullifier} if nullifier_used else set(),
        "total_supply": total_supply,
        "balances": {int(inputs["relayer_address"], 0): 0, int(inputs["recipient_address"], 0): 0},
    }


def validate_concrete_support() -> dict[str, Any]:
    honest = json.loads((D1P12R / "execution-result.json").read_text())
    honest_receipt = json.loads((D1P12R / "mint-receipt.json").read_text())
    hi = honest["proofInputs"]
    honest_result = lower_mint(words_from_inputs(hi), basefee=int(honest_receipt["block"]["baseFeePerGas"]),
                               state=state_for(hi, int(honest["mint"]["pre"]["totalSupply"])), msg_sender=int(hi["relayer_address"], 0))
    replay_result = lower_mint(words_from_inputs(hi), basefee=int(honest_receipt["block"]["baseFeePerGas"]),
                               state=state_for(hi, int(honest["mint"]["pre"]["totalSupply"]), True), msg_sender=int(hi["relayer_address"], 0))
    pos = json.loads((D1P14A / "fc-pos-receipt.json").read_text())
    neg = json.loads((D1P14A / "fc-neg-receipt.json").read_text())
    pi = json.loads((D1P14A / "fc-pos-proof.json").read_text())["proofInputs"]
    pos_state = state_for(pi, int(pos["pre"]["totalSupply"]))
    pos_result = lower_mint(words_from_inputs(pi), basefee=int(pos["block"]["baseFeePerGas"]),
                            state=pos_state, msg_sender=int(pi["relayer_address"], 0))
    neg_result = lower_mint(words_from_inputs(pi), basefee=int(neg["block"]["baseFeePerGas"]),
                            state=pos_state, msg_sender=int(pi["relayer_address"], 0))
    zero = json.loads((D1P14A / "zero-fee-receipt.json").read_text())
    zi = zero["proofInputs"]
    zero_result = lower_mint(words_from_inputs(zi), basefee=int(zero["block"]["baseFeePerGas"]),
                             state=state_for(zi, int(zero["pre"]["totalSupply"])), msg_sender=int(zi["relayer_address"], 0))
    checks = {
        "D1P-12R-honest": honest_result["success"] and not honest_result["auth_violation"] and honest_result["nonvac"],
        "D1P-12R-replay": not replay_result["success"] and replay_result["revert_location"] == "WarpToadCore.sol:157" and replay_result["occurrences"] == [],
        "D1P-14A-FC-POS": pos_result["success"] and pos_result["aggregates"]["fee_amount"] == int(pos["effects"]["relayerDelta"]) and not pos_result["auth_violation"],
        "D1P-14A-FC-NEG": not neg_result["success"] and neg_result["revert_location"] == "WarpToadCore.sol:166" and neg_result["occurrences"] == [],
        "D1P-14A-zero-fee": zero_result["success"] and [item["role"] for item in zero_result["occurrences"]] == ["RECIPIENT"] and not zero_result["auth_violation"],
    }
    return {
        "schema": "bindcheck.d1p14c.manual-summary-differential/v1",
        "classification": "supporting evidence for a MANUAL / ASSUMED summary only; not automatic extraction",
        "checks": checks, "all_checks_pass": all(checks.values()),
        "results": {"D1P-12R-honest": json_safe(honest_result), "D1P-12R-replay": json_safe(replay_result),
                    "D1P-14A-FC-POS": json_safe(pos_result), "D1P-14A-FC-NEG": json_safe(neg_result),
                    "D1P-14A-zero-fee": json_safe(zero_result)},
    }


def identities() -> dict[str, Any]:
    source = WORKSPACE / "backend/contracts/core/WarpToadCore.sol"
    lock = WORKSPACE / "pnpm-lock.yaml"
    oz = WORKSPACE / "node_modules/.pnpm/@openzeppelin+contracts@5.6.1/node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol"
    return {
        "specification": {**record(SPEC), "controlling_section": "amended section 6"},
        "research_contract": {**record(RESEARCH_CONTRACT), "boundary": "section 6.3"},
        "consumer": {**record(source), "summary_classification": "MANUAL / ASSUMED"},
        "openzeppelin": {"status": "EXTRACTED dependency identity; behavior in consumer summary remains MANUAL / ASSUMED",
                         "requested": "^5.2.0", "resolved": "5.6.1", "lockfile": record(lock),
                         "erc20_source": record(oz), "warptoad_update_override": False},
        "artifact": record(ARTIFACT),
        "decoder": record(ROOT / "src/bindcheck_d1/frontends/acir_binary_beta22.py"),
        "solver": {**record(SOLVER), "expected_sha256": SOLVER_SHA256,
                   "version": "cvc5 1.4.2 git 282d5e0", "architecture": "arm64"},
        "resource_policy": record(RESOURCE_POLICY), "monitor_runner": record(MONITOR_RUNNER),
        "base_monitor": record(BASE_MONITOR),
        "nargo": {**record(NARGO), "version": "1.0.0-beta.22+c57152f91260ecdb9faad4efc20abb14b6d2ece7"},
    }


def stage_prepare() -> int:
    require_workspace()
    if MANIFEST.exists() or SEAL.exists() or PREPARED.exists():
        raise SystemExit("D1P-14C preparation is not fresh")
    differential = validate_concrete_support()
    write_json(RAW / "manual-summary-differential.json", differential)
    if not differential["all_checks_pass"]:
        raise SystemExit("manual summary differential checks failed")
    pytest = shutil.which("pytest")
    if not pytest:
        raise SystemExit("pytest executable unavailable")
    tests = run_recorded("focused-tests-before-freeze",
                         [pytest, "-q", "tests/d1/test_joint_warptoad.py", "tests/d1/test_acir_beta22.py"],
                         ROOT, 180, {"PYTHONPATH": str(ROOT / "src")})
    if tests["exit_code"] != 0:
        return tests["exit_code"] or 1
    PREPARED.mkdir(parents=True)
    s0_raw = json.loads((RAW / "fixed-s0.json").read_text())
    s0 = {"provenance": record(RAW / "fixed-s0.json"),
          "giga_root_history": s0_raw["giga_root_history"], "local_root_history": s0_raw["local_root_history"],
          "nullifiers": s0_raw["nullifiers"], "total_supply": s0_raw["total_supply"],
          "fixed_assumption": "D1P-12R owned-local state immediately after honest burn and before mint"}
    ids = identities()
    if ids["solver"]["sha256"] != SOLVER_SHA256:
        raise SystemExit("pinned solver hash mismatch")
    omegas: dict[str, tuple[dict[str, Any], Path]] = {}
    for control, (variant, _expected) in CONTROL_VARIANTS.items():
        value = build_omega(ARTIFACT, goal="AUTH-1", s0=s0, identities=ids,
                            implementation_variant=variant, control_id=control)
        path = PREPARED / f"omega-{control.lower()}.json"
        path.write_bytes(canonical_bytes(value)); omegas[control] = (value, path)
    auth = build_omega(ARTIFACT, goal="AUTH-1", s0=s0, identities=ids)
    nonvac = build_omega(ARTIFACT, goal="NONVAC-1", s0=s0, identities=ids)
    auth_path, nonvac_path = PREPARED / "omega-auth1.json", PREPARED / "omega-nonvac1.json"
    auth_path.write_bytes(canonical_bytes(auth)); nonvac_path.write_bytes(canonical_bytes(nonvac))
    omegas["Q1"] = omegas["Q2"] = (auth, auth_path); omegas["Q3"] = (nonvac, nonvac_path)
    schedule = []
    names = ["C1", "C2", "C3", "C4", "Q1", "Q2", "Q3"]
    files = {"C1": "c1-conservation.smt2", "C2": "c2-beneficiary.smt2",
             "C3": "c3-extra-mint.smt2", "C4": "c4-wrong-nullifier.smt2",
             "Q1": "q1-auth1-r-dropped.smt2", "Q2": "q2-auth1-monolithic.smt2",
             "Q3": "q3-nonvac1-monolithic.smt2"}
    for name in names:
        omega, omega_path = omegas[name]
        dropped = name in {"C1", "C2", "C3", "C4", "Q1"}
        query, certificate = encode_query(omega, drop_producer=dropped)
        query_path = PREPARED / files[name]; query_path.write_bytes(query)
        certificate.update({"schedule_id": name, "query_path": str(query_path.relative_to(ROOT))})
        certificate_path = PREPARED / f"{name.lower()}-transformation.json"
        write_json(certificate_path, certificate)
        schedule.append({"id": name, "kind": "control" if name.startswith("C") else "primary",
                         "timeout_seconds": 60 if name.startswith("C") else 300,
                         "expected": f"SAT/{CONTROL_VARIANTS[name][1]}" if name.startswith("C") else None,
                         "omega": record(omega_path), "query": record(query_path),
                         "transformation": record(certificate_path), "drop_producer": dropped})
    policy_hashes = {canonical_sha256(omegas[name][0]["policy"]) for name in names}
    if len(policy_hashes) != 1:
        raise SystemExit("control policy changed across schedule")
    hashed = [MODULE, Path(__file__), TEST, PRESERVE_SCRIPT, CANDIDATE_TEMPLATE, VECTOR_TEMPLATE,
              PROTOCOL, SPEC, RESEARCH_CONTRACT, RESOURCE_POLICY, MONITOR_RUNNER, BASE_MONITOR,
              SOLVER, NARGO, ARTIFACT, RAW / "fixed-s0.json", RAW / "manual-summary-differential.json",
              RAW / "d1p14b-preservation-baseline.json"]
    for item in schedule:
        hashed.extend([ROOT / item["omega"]["path"], ROOT / item["query"]["path"],
                       ROOT / item["transformation"]["path"]])
    manifest = {
        "schema": "bindcheck.d1p14c.frozen-manifest/v1", "frozen_at_utc": utc_now(),
        "pinned_revision": PIN, "schedule": schedule,
        "schedule_order": names, "policy_sha256": next(iter(policy_hashes)),
        "auth_scope_choice": "AUTH-1[G1-G5]; G4/G5 derived from explicit effect/write representation",
        "consumer_summary": {"classification": "MANUAL / ASSUMED", "automatic_extraction_claim": False,
                             "five_differential_checks": record(RAW / "manual-summary-differential.json")},
        "preflight": {"balanced_parentheses": True, "cvc5_arguments": PARSE_ARGS,
                      "classification": "non-primary", "required_before_solver_schedule": True},
        "solver": ids["solver"], "solver_arguments": SOLVER_ARGS,
        "bounds": {"control_attempts": 4, "control_seconds_each": 60, "stop_on_control_failure": True,
                   "primary_attempts": 3, "primary_seconds_each": 300, "attempts_per_query": 1,
                   "sequential": True, "post_freeze_tuning": False,
                   "rss_cutoff_bytes": RSS_CUTOFF, "sample_interval_seconds": SAMPLE_INTERVAL},
        "sat_validation": {"controls": "returned assignment evaluated against mutated manual summary and unchanged policy",
                           "primary": "amended section 6(b) V-EXEC", "NONVAC-1": "SAT must pass V-EXEC"},
        "identities": ids, "focused_tests": tests,
        "hash_complete_inputs": [record(path) for path in hashed],
        "claim_boundary": "Internal consistency and sensitivity of the MANUAL / ASSUMED model only; no Solidity equivalence, automatic discovery, end-to-end vulnerability, or D1 verdict.",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); write_json(MANIFEST, manifest)
    write_json(SEAL, {"schema": "bindcheck.d1p14c.freeze-seal/v1", "manifest": record(MANIFEST),
                      "parse_only_calls_at_freeze": 0, "scheduled_solver_calls_at_freeze": 0})
    return 0


def verify_frozen() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text()); manifest = json.loads(MANIFEST.read_text())
    if seal["manifest"]["sha256"] != file_sha256(MANIFEST):
        raise SystemExit("manifest changed after freeze")
    for item in manifest["hash_complete_inputs"]:
        path = Path(item["path"]); path = path if path.is_absolute() else ROOT / path
        if not path.exists() or file_sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"frozen input mismatch: {item['path']}")
    return manifest


def stage_preflight() -> int:
    manifest = verify_frozen()
    if PREFLIGHT.exists() or PARSE_LOGS.exists():
        raise SystemExit("parse preflight already exists")
    PARSE_LOGS.mkdir(parents=True)
    results = []
    for item in manifest["schedule"]:
        query = ROOT / item["query"]["path"]
        balance = balanced_smt_parentheses(query.read_bytes())
        stdout_path = PARSE_LOGS / f"{item['id'].lower()}.stdout"
        stderr_path = PARSE_LOGS / f"{item['id'].lower()}.stderr"
        record_path = PARSE_LOGS / f"{item['id'].lower()}.json"
        started = time.monotonic()
        with query.open("rb") as source, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            try:
                completed = subprocess.run([str(SOLVER), *PARSE_ARGS], stdin=source, stdout=stdout,
                                           stderr=stderr, timeout=60, check=False)
                exit_code, timed_out = completed.returncode, False
            except subprocess.TimeoutExpired:
                exit_code, timed_out = None, True
        result = {"schema": "bindcheck.d1p14c.parse-preflight-call/v1", "id": item["id"],
                  "classification": "non-primary parse-only", "balanced_parentheses": balance,
                  "argv": [str(SOLVER), *PARSE_ARGS], "input": record(query),
                  "exit_code": exit_code, "timed_out": timed_out,
                  "wall_seconds": round(time.monotonic() - started, 6),
                  "stdout": record(stdout_path, RAW), "stderr": record(stderr_path, RAW),
                  "pass": balance["balanced"] and exit_code == 0 and not timed_out}
        write_json(record_path, result); results.append(result)
    payload = {"schema": "bindcheck.d1p14c.parse-preflight/v1", "created_at_utc": utc_now(),
               "classification": "seven non-primary parse-only calls; not sensitivity/primary solves",
               "results": results, "all_pass": all(item["pass"] for item in results),
               "parse_only_calls": len(results), "scheduled_solver_calls": 0}
    write_json(PREFLIGHT, payload)
    return 0 if payload["all_pass"] else 1


def load_monitor():
    spec = importlib.util.spec_from_file_location("d1p14c_d1p07", MONITOR_RUNNER)
    module = importlib.util.module_from_spec(spec); assert spec.loader is not None
    spec.loader.exec_module(module); return module


def solver_answer(call: dict[str, Any]) -> str:
    if call["status"] != "COMPLETED":
        return "UNKNOWN"
    text = (ROOT / call["stdout_path"]).read_text(errors="replace")
    for line in text.splitlines():
        if line.strip().lower() in {"sat", "unsat", "unknown"}:
            return line.strip().upper()
    return "UNKNOWN"


BV_PATTERNS = [
    (re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+#x([0-9a-fA-F]+)\s*\)"), 16),
    (re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+#b([01]+)\s*\)"), 2),
    (re.compile(r"\(define-fun\s+(pi\d+|basefee)\s+\(\)\s+\(_ BitVec 256\)\s+\(_ bv(\d+) 256\)\s*\)"), 10),
]
FF_RE = re.compile(r"\(define-fun\s+w(\d+)\s+\(\)\s+(?:F|\(_ FiniteField \d+\))\s+(?:\(as ff(\d+) (?:F|\(_ FiniteField \d+\))\)|#f(\d+)m\d+)\s*\)")


def parse_model(text: str) -> tuple[dict[str, int], dict[int, int]]:
    bv: dict[str, int] = {}
    for pattern, base in BV_PATTERNS:
        for match in pattern.finditer(text):
            bv[match.group(1)] = int(match.group(2), base)
    ff = {int(match.group(1)): int(match.group(2) or match.group(3)) for match in FF_RE.finditer(text)}
    return bv, ff


def validate_control(call: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    stdout = (ROOT / call["stdout_path"]).read_text(errors="replace")
    bv, _ff = parse_model(stdout)
    result: dict[str, Any] = {"id": item["id"], "expected": item["expected"],
                              "model_bitvectors": len(bv), "pass": False}
    required = [f"pi{index}" for index in range(11)] + ["basefee"]
    if any(name not in bv for name in required):
        result["reason"] = "SAT model lacks required public/basefee assignment"; return result
    words = [bv[f"pi{index}"] for index in range(11)]
    s0 = json.loads((RAW / "fixed-s0.json").read_text())
    state = {"giga_roots": set(map(int, s0["giga_root_history"])),
             "local_roots": set(map(int, s0["local_root_history"])), "nullifiers": set(),
             "total_supply": int(s0["total_supply"]), "balances": {words[9]: 0, words[10]: 0}}
    variant, expected_goal = CONTROL_VARIANTS[item["id"]]
    evaluated = lower_mint(words, basefee=bv["basefee"], state=state,
                           msg_sender=RELAYER, implementation_variant=variant)
    conditions = {"successful_transition": evaluated["success"],
                  "expected_goal_true": evaluated.get("goals", {}).get(expected_goal) is True,
                  "auth_violation": evaluated.get("auth_violation") is True,
                  "variant_exact": evaluated["implementation_variant"] == variant}
    if item["id"] in {"C1", "C2"}:
        conditions["positive_fee"] = evaluated["aggregates"].get("fee_amount", 0) > 0 if evaluated["success"] else False
    if item["id"] == "C2":
        conditions["distinct_addresses"] = words[9] != words[10]
    result.update({"assignment": {"public_words": list(map(str, words)), "basefee": str(bv["basefee"])},
                   "evaluation": json_safe(evaluated), "conditions": conditions,
                   "pass": all(conditions.values()),
                   "reason": "returned assignment validates against mutated manual summary" if all(conditions.values()) else "assignment validation failed"})
    return result


def stage_run() -> int:
    manifest = verify_frozen()
    preflight = json.loads(PREFLIGHT.read_text())
    if not preflight["all_pass"] or preflight["scheduled_solver_calls"] != 0:
        raise SystemExit("parse preflight not passed")
    if LEDGER.exists() or SOLVER_LOGS.exists():
        raise SystemExit("solver schedule already started")
    d1p07 = load_monitor(); monitor = d1p07.D1P05.MacProcessTreeMonitor()
    ledger: dict[str, Any] = {"schema": "bindcheck.d1p14c.solver-ledger/v1",
        "started_at_utc": utc_now(), "manifest": record(MANIFEST), "preflight": record(PREFLIGHT),
        "schedule": manifest["schedule"], "calls": [], "control_validations": [],
        "scheduled_solver_calls": 0, "stopped": False, "stop_reason": None}
    for index, item in enumerate(manifest["schedule"], start=1):
        verify_frozen()
        query = ROOT / item["query"]["path"]
        call = d1p07.run_monitored(
            index=index, kind=item["kind"], name=item["id"], argv=[str(SOLVER), *SOLVER_ARGS],
            logs_dir=SOLVER_LOGS, monitor=monitor, input_path=query,
            timeout_seconds=float(item["timeout_seconds"]), rss_cutoff_bytes=RSS_CUTOFF,
            sample_interval_seconds=SAMPLE_INTERVAL,
        )
        call["answer"] = solver_answer(call); call["schedule_item"] = item
        ledger["calls"].append(call); ledger["scheduled_solver_calls"] += 1
        if item["kind"] == "control":
            validation = validate_control(call, item) if call["answer"] == "SAT" else {
                "id": item["id"], "expected": item["expected"], "pass": False,
                "reason": f"expected SAT, observed {call['answer']} ({call['status']})"}
            ledger["control_validations"].append(validation)
            if not validation["pass"]:
                ledger["stopped"] = True; ledger["stop_reason"] = f"control {item['id']} failed"
                write_json(LEDGER, ledger); break
        write_json(LEDGER, ledger)
    ledger["finished_at_utc"] = utc_now()
    ledger["all_controls_pass"] = len(ledger["control_validations"]) == 4 and all(item["pass"] for item in ledger["control_validations"])
    ledger["primary_calls"] = sum(call["kind"] == "primary" for call in ledger["calls"])
    ledger["complete_schedule"] = ledger["scheduled_solver_calls"] == 7 and ledger["primary_calls"] == 3
    ledger["charged_solver_seconds"] = round(sum(min(float(call["elapsed_seconds"]), float(call["timeout_seconds"])) for call in ledger["calls"]), 6)
    ledger["answers"] = {call["name"]: call["answer"] for call in ledger["calls"]}
    write_json(LEDGER, ledger)
    return 0 if ledger["complete_schedule"] and ledger["all_controls_pass"] else 1


def prover_toml(public: list[int], private: list[int]) -> str:
    value = lambda item: f'"0x{item:x}"'
    lines = [f"{name} = {value(public[index])}" for index, name in enumerate(PUBLIC_INPUTS)]
    lines.extend([f"origin_local_root = {value(private[0])}",
                  f"is_from_aztec = {'true' if private[1] else 'false'}",
                  f"nullifier_preimage = {value(private[2])}", f"secret = {value(private[3])}",
                  "", "[aztec_merkle_data]", f"leaf_index = {value(private[4])}",
                  "hash_path = [" + ", ".join(value(item) for item in private[5:47]) + "]",
                  f"leaf_nonce = {value(private[47])}", "", "[evm_merkle_data]",
                  f"leaf_index = {value(private[48])}",
                  "hash_path = [" + ", ".join(value(item) for item in private[49:81]) + "]",
                  "", "[giga_merkle_data]", f"leaf_index = {value(private[81])}",
                  "hash_path = [" + ", ".join(value(item) for item in private[82:87]) + "]"])
    return "\n".join(lines) + "\n"


def validate_primary_sat(call: dict[str, Any]) -> dict[str, Any]:
    name = call["name"]; output_dir = VALIDATION / name.lower(); output_dir.mkdir(parents=True, exist_ok=False)
    stdout = (ROOT / call["stdout_path"]).read_text(errors="replace")
    bv, ff = parse_model(stdout)
    result: dict[str, Any] = {"query": name, "status": "UNKNOWN", "model": {"bitvectors": len(bv), "field_witnesses": len(ff)}}
    if any(f"pi{index}" not in bv for index in range(11)) or "basefee" not in bv:
        result["reason"] = "SAT model lacks full public/basefee assignment"; return result
    public = [bv[f"pi{index}"] for index in range(11)]
    honest = json.loads((D1P13 / "honest-witness.json").read_text())["witnesses"]
    private, fallback = [], []
    for index in range(11, 98):
        if index in ff: private.append(ff[index])
        else: private.append(int(honest[str(index)], 0)); fallback.append(index)
    candidate = {"schema": "bindcheck.d1p14c.candidate/v1", "query": name,
                 "public_words": list(map(str, public)), "private_abi_witnesses_w11_w97": list(map(str, private)),
                 "private_fallback_from_honest_anchor": fallback, "basefee": str(bv["basefee"]),
                 "msg_sender": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8", "intermediate_model_witnesses_ignored": True}
    candidate_path = output_dir / "candidate.json"; write_json(candidate_path, candidate)
    prover_name = f"D1P14C_{name}"; prover_path = WORKSPACE / "backend/circuits/withdraw" / f"{prover_name}.toml"
    prover_path.write_text(prover_toml(public, private))
    nargo = run_recorded(f"validate-{name.lower()}-nargo",
                         [str(NARGO), "execute", f"d1p14c_{name.lower()}", "--prover-name", prover_name],
                         WORKSPACE / "backend/circuits/withdraw", 600)
    result.update({"candidate": record(candidate_path), "prover_input": record(prover_path), "nargo": nargo})
    if nargo["exit_code"] != 0 or nargo["timed_out"]:
        result["reason"] = "pinned beta.22 nargo execute did not validate candidate"; return result
    execution_path = output_dir / "consumer-execution.json"
    consumer = run_recorded(f"validate-{name.lower()}-consumer",
        [str(WORKSPACE / "backend/node_modules/.bin/hardhat"), "test", "--network", "edr", "--no-compile", "test/d1p14c.candidate.fixture.ts"],
        WORKSPACE / "backend", 600, {"D1P14C_CANDIDATE": str(candidate_path), "D1P14C_EXECUTION": str(execution_path)})
    result["consumer_command"] = consumer
    if not execution_path.exists():
        result["reason"] = "consumer stage produced no result"; return result
    execution = json.loads(execution_path.read_text()); result["consumer_execution"] = record(execution_path)
    if consumer["exit_code"] != 0 or not execution.get("accepted"):
        result["reason"] = "unchanged consumer did not commit candidate"; return result
    result["status"] = "VALIDATED_SAT"; result["reason"] = "section 6(b) route passed"
    return result


def stage_validate() -> int:
    verify_frozen(); ledger = json.loads(LEDGER.read_text())
    if not ledger["complete_schedule"]:
        raise SystemExit("primary schedule did not complete")
    summary_path = RAW / "validation-summary.json"
    if summary_path.exists(): raise SystemExit("validation already exists")
    results = []
    for call in ledger["calls"]:
        if call["kind"] != "primary": continue
        if call["answer"] == "SAT":
            result = validate_primary_sat(call); write_json(VALIDATION / call["name"].lower() / "result.json", result)
        else:
            result = {"query": call["name"], "solver_answer": call["answer"], "validation": "V-EXEC not applicable without SAT"}
        results.append(result)
    write_json(summary_path, {"schema": "bindcheck.d1p14c.validation-summary/v1", "results": results,
                              "NONVAC_sat_requires_vexec": True, "proof_generation_calls": 0})
    return 0


def stage_audit() -> int:
    manifest = verify_frozen(); ledger = json.loads(LEDGER.read_text()); preflight = json.loads(PREFLIGHT.read_text())
    validation = json.loads((RAW / "validation-summary.json").read_text())
    baseline = json.loads((RAW / "d1p14b-preservation-baseline.json").read_text())
    b_current = d1p14b_tree_identity()
    tracked = []
    for item in baseline["tracked_evidence"]:
        path = ROOT / item["path"]; tracked.append({**item, "actual_sha256": file_sha256(path), "matches": file_sha256(path) == item["sha256"]})
    snapshots = []
    for item in baseline["frozen_source_inputs"]:
        path = ROOT / item["snapshot"]["path"]
        snapshots.append({**item["snapshot"], "actual_sha256": file_sha256(path), "matches": file_sha256(path) == item["snapshot"]["sha256"]})
    checks = {"seven_parse_preflights_pass": preflight["all_pass"] and preflight["parse_only_calls"] == 7,
              "four_controls_sat_and_validated": ledger["all_controls_pass"],
              "three_primary_calls": ledger["primary_calls"] == 3,
              "complete_fixed_schedule": ledger["complete_schedule"],
              "policy_hash_single": bool(manifest["policy_sha256"]),
              "d1p14b_raw_unchanged": b_current == {key: baseline["d1p14b_raw_tree"][key] for key in b_current},
              "d1p14b_tracked_evidence_unchanged": all(item["matches"] for item in tracked),
              "d1p14b_source_snapshots_unchanged": all(item["matches"] for item in snapshots),
              "proof_generation_zero": validation["proof_generation_calls"] == 0}
    write_json(RAW / "audit.json", {"schema": "bindcheck.d1p14c.audit/v1", "created_at_utc": utc_now(),
        "checks": checks, "all_checks_pass": all(checks.values()), "answers": ledger["answers"],
        "manifest": record(MANIFEST), "preflight": record(PREFLIGHT), "ledger": record(LEDGER),
        "validation": record(RAW / "validation-summary.json"), "d1p14b_raw_current": b_current,
        "d1p14b_tracked": tracked, "d1p14b_source_snapshots": snapshots,
        "claim_boundary": manifest["claim_boundary"]})
    return 0 if all(checks.values()) else 1


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--stage", required=True,
        choices=["setup", "prepare", "preflight", "run", "validate", "audit"])
    stages = {"setup": stage_setup, "prepare": stage_prepare, "preflight": stage_preflight,
              "run": stage_run, "validate": stage_validate, "audit": stage_audit}
    raise SystemExit(stages[parser.parse_args().stage]())


if __name__ == "__main__":
    main()
