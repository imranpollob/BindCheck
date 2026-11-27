#!/usr/bin/env python3
"""Freeze and execute D1P-14D deterministic controls and diagnostics."""

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

from bindcheck_d1.joint_warptoad import PUBLIC_INPUTS, balanced_smt_parentheses, canonical_bytes, file_sha256
from bindcheck_d1.joint_warptoad_d1p14d import (
    CONTROL_VARIANTS,
    audit_concrete_control,
    encode_concrete_control,
    expected_effect_records,
    fixture_words,
    freeze_honest_fixture,
)


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-14D"
RAW_B = ROOT / "results/raw/D1P-14B"
RAW_C = ROOT / "results/raw/D1P-14C"
WORKSPACE = RAW / "workspace/source"
PREPARED = RAW / "prepared"
COMMANDS = RAW / "command-records"
PARSE_LOGS = RAW / "parse-preflight-logs"
SOLVER_LOGS = RAW / "solver-logs"
VALIDATION = RAW / "validation"
PRESERVATION = RAW / "d1p14bc-preservation-baseline.json"
FIXTURE = RAW / "fixed-control-fixture.json"
EXPECTED = RAW / "expected-effects.json"
PREFLIGHT = RAW / "parse-preflight.json"
LEDGER = RAW / "solver-ledger.json"
VALIDATION_SUMMARY = RAW / "validation-summary.json"
AUDIT = RAW / "audit.json"

PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
D1P12R = ROOT / "results/raw/D1P-12R"
D1P13 = ROOT / "results/raw/D1P-13"
D1P14A = ROOT / "results/raw/D1P-14A"
C_MANIFEST = ROOT / "metadata/d1/d1p-14c-artifact-manifest.json"
ARTIFACT_SOURCE = D1P13 / "workspace/source/backend/circuits/withdraw/target/withdraw.json"
ARTIFACT = WORKSPACE / "backend/circuits/withdraw/target/withdraw.json"
PROOF_RECORD = D1P14A / "fc-pos-proof.json"
RECEIPT = D1P14A / "fc-pos-receipt.json"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
NARGO = D1P13 / "tools/nargo-beta22/nargo"
MONITOR_RUNNER = ROOT / "scripts/d1p_07_track_a.py"
BASE_MONITOR = ROOT / "scripts/d1p_05_validate.py"
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-07-resource-policy.json"
MODULE_C = ROOT / "src/bindcheck_d1/joint_warptoad.py"
MODULE_D = ROOT / "src/bindcheck_d1/joint_warptoad_d1p14d.py"
TEST_C = ROOT / "tests/d1/test_joint_warptoad.py"
TEST_D = ROOT / "tests/d1/test_joint_warptoad_d1p14d.py"
RUNNER_C = ROOT / "scripts/d1p_14c_joint_encoder.py"
PRESERVE_SCRIPT = ROOT / "scripts/d1p_14d_preserve.py"
CANDIDATE_TEMPLATE = ROOT / "scripts/fixtures/d1p_14c_candidate_exec.ts"
VECTOR_TEMPLATE = ROOT / "scripts/fixtures/D1P14BVectorVerifier.sol"
CANDIDATE_FIXTURE = WORKSPACE / "backend/test/d1p14c.candidate.fixture.ts"
VECTOR_CONTRACT = WORKSPACE / "backend/contracts/test/D1P14BVectorVerifier.sol"
PROTOCOL = ROOT / "protocols/d1/d1p-14d-deterministic-controls.json"
MANIFEST = ROOT / "metadata/d1/d1p-14d-artifact-manifest.json"
SEAL = RAW / "freeze-seal.json"

SOLVER_SHA256 = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGS = ["--lang=smt2", "--ff-solver=split", "--produce-models", "--dump-models"]
PARSE_ARGS = ["--lang=smt2", "--parse-only"]
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05
RELAYER = int("70997970c51812dc3a010c7d01b50e0d17dc79c8", 16)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def record(path: Path, base: Path = ROOT) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": file_sha256(path), "bytes": path.stat().st_size,
    }


def tree_identity(path: Path) -> dict[str, Any]:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256(); total = 0
    for item in files:
        relative, size, item_hash = str(item.relative_to(path)), item.stat().st_size, file_sha256(item)
        digest.update(f"{relative}\0{item_hash}\0{size}\n".encode()); total += size
    return {"path": str(path.relative_to(ROOT)), "file_count": len(files),
            "regular_file_bytes": total, "ordered_path_hash_size_sha256": digest.hexdigest()}


def verify_prior_preservation() -> dict[str, Any]:
    baseline = json.loads(PRESERVATION.read_text())
    for name, path in (("D1P-14B", RAW_B), ("D1P-14C", RAW_C)):
        current, expected = tree_identity(path), baseline["prior_raw_trees"][name]
        for key in ("file_count", "regular_file_bytes", "ordered_path_hash_size_sha256"):
            if current[key] != expected[key]:
                raise SystemExit(f"{name} raw evidence changed: {key}")
    for item in baseline["tracked_evidence"]:
        path = ROOT / item["path"]
        if file_sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"prior tracked evidence changed: {item['path']}")
    for item in baseline["frozen_d1p14c_source_inputs"]:
        live, snapshot = ROOT / item["live"]["path"], ROOT / item["snapshot"]["path"]
        if file_sha256(live) != item["live"]["sha256"] or live.read_bytes() != snapshot.read_bytes():
            raise SystemExit(f"D1P-14C frozen source changed: {item['live']['path']}")
    return baseline


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    COMMANDS.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path, result_path = (
        COMMANDS / f"{label}.stdout", COMMANDS / f"{label}.stderr", COMMANDS / f"{label}.json"
    )
    if any(path.exists() for path in (stdout_path, stderr_path, result_path)):
        raise SystemExit(f"command evidence already exists: {label}")
    env = os.environ.copy(); env.update(env_extra or {})
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        try:
            completed = subprocess.run(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                       timeout=timeout, check=False)
            exit_code, timed_out = completed.returncode, False
        except subprocess.TimeoutExpired:
            exit_code, timed_out = None, True
    value = {"schema": "bindcheck.d1p14d.command/v1", "label": label, "argv": argv,
             "cwd": str(cwd), "timeout_seconds": timeout, "exit_code": exit_code,
             "timed_out": timed_out, "wall_seconds": round(time.monotonic() - started, 6),
             "stdout": record(stdout_path, RAW), "stderr": record(stderr_path, RAW)}
    write_json(result_path, value); return value


def require_workspace() -> None:
    if not (WORKSPACE / ".git").exists():
        raise SystemExit("D1P-14D workspace absent")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=WORKSPACE,
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != PIN:
        raise SystemExit(f"workspace pin mismatch: {head}")


def stage_setup() -> int:
    verify_prior_preservation()
    setup_path = RAW / "setup.json"
    if setup_path.exists() or WORKSPACE.exists():
        raise SystemExit("D1P-14D setup already exists")
    clone = run_recorded("clone-pinned-project", ["git", "clone", "--no-hardlinks",
                           str(D1P12R / "workspace/source"), str(WORKSPACE)], ROOT, 600)
    if clone["exit_code"] != 0: return clone["exit_code"] or 1
    checkout = run_recorded("checkout-pinned-project", ["git", "checkout", "--detach", PIN], WORKSPACE, 300)
    if checkout["exit_code"] != 0: return checkout["exit_code"] or 1
    for relative in ("node_modules", "backend/node_modules"):
        (WORKSPACE / relative).symlink_to(D1P12R / "workspace/source" / relative, target_is_directory=True)
    shutil.copytree(RAW_C / "workspace/source/backend/artifacts", WORKSPACE / "backend/artifacts")
    shutil.copytree(RAW_C / "workspace/source/backend/cache", WORKSPACE / "backend/cache")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ARTIFACT_SOURCE, ARTIFACT)
    shutil.copy2(CANDIDATE_TEMPLATE, CANDIDATE_FIXTURE); shutil.copy2(VECTOR_TEMPLATE, VECTOR_CONTRACT)
    write_json(setup_path, {"schema": "bindcheck.d1p14d.setup/v1", "created_at_utc": utc_now(),
        "pinned_revision": PIN, "host": {"platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version.split()[0], "logical_cpus": os.cpu_count()},
        "network": {"kind": "Hardhat edr-simulated", "fork": False, "live_chain": False},
        "clone": clone, "checkout": checkout, "artifact": record(ARTIFACT),
        "candidate_fixture": record(CANDIDATE_FIXTURE), "vector_contract": record(VECTOR_CONTRACT),
        "prior_preservation": record(PRESERVATION),
        "bounds": {"proof_generation_calls": 0, "solver_calls": 0, "parse_only_calls": 0}})
    return 0


def identities() -> dict[str, Any]:
    c = json.loads(C_MANIFEST.read_text())["identities"]
    return {**c, "consumer": {**c["consumer"], "summary_classification": "MANUAL / ASSUMED"}}


def c_primary_records() -> dict[str, dict[str, Any]]:
    manifest = json.loads(C_MANIFEST.read_text())
    result = {item["id"]: item for item in manifest["schedule"] if item["kind"] == "primary"}
    if set(result) != {"Q1", "Q2", "Q3"}:
        raise SystemExit("unexpected D1P-14C primary schedule")
    return result


def stage_prepare() -> int:
    verify_prior_preservation(); require_workspace()
    if MANIFEST.exists() or SEAL.exists() or PREPARED.exists() or FIXTURE.exists() or EXPECTED.exists():
        raise SystemExit("D1P-14D preparation is not fresh")
    fixture = freeze_honest_fixture(json.loads(PROOF_RECORD.read_text()), json.loads(RECEIPT.read_text()))
    FIXTURE.write_bytes(canonical_bytes(fixture))
    expected = expected_effect_records(fixture); EXPECTED.write_bytes(canonical_bytes(expected))
    pytest = shutil.which("pytest")
    if not pytest: raise SystemExit("pytest unavailable")
    tests = run_recorded("focused-tests-before-freeze", [pytest, "-q", str(TEST_D.relative_to(ROOT)),
        str(TEST_C.relative_to(ROOT)), "tests/d1/test_acir_beta22.py"], ROOT, 240,
        {"PYTHONPATH": str(ROOT / "src")})
    if tests["exit_code"] != 0: return tests["exit_code"] or 1
    PREPARED.mkdir(parents=True)
    schedule: list[dict[str, Any]] = []
    omega_paths: dict[tuple[str, str], Path] = {}
    policy_hashes = set()
    for control in CONTROL_VARIANTS:
        for polarity in ("positive", "negative"):
            query, certificate, omega = encode_concrete_control(
                ARTIFACT, identities=identities(), fixture=fixture,
                control_id=control, polarity=polarity,
            )
            audit_concrete_control(query, certificate, fixture)
            omega_key = (control, polarity) if polarity == "positive" else ("BASE", "negative")
            if omega_key not in omega_paths:
                omega_path = PREPARED / (f"omega-{control.lower()}-positive.json" if polarity == "positive" else "omega-base-negative.json")
                omega_path.write_bytes(canonical_bytes(omega)); omega_paths[omega_key] = omega_path
            query_id = f"{control}{'P' if polarity == 'positive' else 'N'}"
            query_path = PREPARED / f"{query_id.lower()}-{CONTROL_VARIANTS[control][1].lower()}.smt2"
            query_path.write_bytes(query)
            certificate.update({"schedule_id": query_id, "query_path": str(query_path.relative_to(ROOT))})
            certificate_path = PREPARED / f"{query_id.lower()}-transformation.json"; write_json(certificate_path, certificate)
            policy_hashes.add(certificate["policy_sha256"])
            schedule.append({"id": query_id, "kind": "control", "control": control,
                "polarity": polarity, "target": CONTROL_VARIANTS[control][1],
                "expected": "SAT" if polarity == "positive" else "UNSAT", "timeout_seconds": 30,
                "omega": record(omega_paths[omega_key]), "query": record(query_path),
                "transformation": record(certificate_path)})
    if len(policy_hashes) != 1: raise SystemExit("control policy differs")
    c_queries = c_primary_records()
    for query_id in ("Q1", "Q2", "Q3"):
        source = ROOT / c_queries[query_id]["query"]["path"]
        if file_sha256(source) != c_queries[query_id]["query"]["sha256"]:
            raise SystemExit(f"D1P-14C {query_id} source hash mismatch")
        target = PREPARED / source.name; shutil.copy2(source, target)
        if file_sha256(target) != c_queries[query_id]["query"]["sha256"]:
            raise SystemExit(f"copied {query_id} differs from D1P-14C")
        schedule.append({"id": query_id, "kind": "primary", "timeout_seconds": 300,
            "expected": None, "query": record(target), "d1p14c_query": record(source),
            "d1p14c_manifest_hash": c_queries[query_id]["query"]["sha256"],
            "unchanged_from_d1p14c": True})
    hashed = [MODULE_C, MODULE_D, Path(__file__), TEST_C, TEST_D, PRESERVE_SCRIPT, PROTOCOL,
              C_MANIFEST, PROOF_RECORD, RECEIPT, ARTIFACT, FIXTURE, EXPECTED, PRESERVATION,
              SOLVER, NARGO, MONITOR_RUNNER, BASE_MONITOR, RESOURCE_POLICY,
              CANDIDATE_TEMPLATE, VECTOR_TEMPLATE]
    for item in schedule:
        hashed.append(ROOT / item["query"]["path"])
        if item["kind"] == "control":
            hashed.extend([ROOT / item["omega"]["path"], ROOT / item["transformation"]["path"]])
        else:
            hashed.append(ROOT / item["d1p14c_query"]["path"])
    manifest = {"schema": "bindcheck.d1p14d.frozen-manifest/v1", "frozen_at_utc": utc_now(),
        "pinned_revision": PIN, "fixture": record(FIXTURE), "expected_effects": record(EXPECTED),
        "schedule": schedule, "schedule_order": [item["id"] for item in schedule],
        "control_policy_sha256": next(iter(policy_hashes)),
        "controls": {"classification": "concrete encoder regressions, not search/performance evidence",
            "timeout_seconds": 30, "attempts_each": 1, "stop_on_failure": True,
            "requirements": "all four positive SAT and all four negative UNSAT"},
        "primaries": {"classification": "unchanged D1P-14C diagnostics", "timeout_seconds": 300,
            "attempts_each": 1, "gate": "all controls and parser checks pass", "post_freeze_tuning": False},
        "preflight": {"balanced_parentheses": True, "cvc5_arguments": PARSE_ARGS,
            "classification": "non-primary", "query_count": 11},
        "solver": {**record(SOLVER), "expected_sha256": SOLVER_SHA256,
            "version": "cvc5 1.4.2 git 282d5e0", "architecture": "arm64"},
        "solver_arguments": SOLVER_ARGS,
        "resource_policy": {"source": record(RESOURCE_POLICY), "monitor": record(MONITOR_RUNNER),
            "rss_cutoff_bytes": RSS_CUTOFF, "sample_interval_seconds": SAMPLE_INTERVAL},
        "candidate_validation": {"primary_sat": "existing amended section 6(b) V-EXEC route",
            "NONVAC-1": "SAT requires V-EXEC", "proof_generation_calls": 0},
        "consumer_summary": {"classification": "MANUAL / ASSUMED", "automatic_extraction_claim": False},
        "original_c2_timeout": {"status": "preserved and unresolved", "ledger": record(RAW_C / "solver-ledger.json")},
        "focused_tests": tests, "hash_complete_inputs": [record(path) for path in hashed],
        "claim_boundary": "Fixed-input regression polarity only; no general semantic equivalence, automatic extraction, search-performance, end-to-end vulnerability, or D1 verdict."}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); write_json(MANIFEST, manifest)
    write_json(SEAL, {"schema": "bindcheck.d1p14d.freeze-seal/v1", "manifest": record(MANIFEST),
        "parse_only_calls_at_freeze": 0, "scheduled_solver_calls_at_freeze": 0})
    return 0


def verify_frozen() -> dict[str, Any]:
    verify_prior_preservation()
    seal, manifest = json.loads(SEAL.read_text()), json.loads(MANIFEST.read_text())
    if seal["manifest"]["sha256"] != file_sha256(MANIFEST): raise SystemExit("manifest changed")
    for item in manifest["hash_complete_inputs"]:
        path = Path(item["path"]); path = path if path.is_absolute() else ROOT / path
        if not path.exists() or file_sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"frozen input mismatch: {item['path']}")
    return manifest


def stage_preflight() -> int:
    manifest = verify_frozen()
    if PREFLIGHT.exists() or PARSE_LOGS.exists(): raise SystemExit("preflight exists")
    PARSE_LOGS.mkdir(parents=True); results = []
    for item in manifest["schedule"]:
        query = ROOT / item["query"]["path"]; balance = balanced_smt_parentheses(query.read_bytes())
        stdout_path, stderr_path = PARSE_LOGS / f"{item['id'].lower()}.stdout", PARSE_LOGS / f"{item['id'].lower()}.stderr"
        started = time.monotonic()
        with query.open("rb") as source, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            try:
                completed = subprocess.run([str(SOLVER), *PARSE_ARGS], stdin=source, stdout=stdout,
                                           stderr=stderr, timeout=60, check=False)
                exit_code, timed_out = completed.returncode, False
            except subprocess.TimeoutExpired:
                exit_code, timed_out = None, True
        result = {"schema": "bindcheck.d1p14d.parse-call/v1", "id": item["id"],
            "classification": "non-primary parse-only", "balanced_parentheses": balance,
            "argv": [str(SOLVER), *PARSE_ARGS], "input": record(query), "exit_code": exit_code,
            "timed_out": timed_out, "wall_seconds": round(time.monotonic()-started, 6),
            "stdout": record(stdout_path, RAW), "stderr": record(stderr_path, RAW),
            "pass": balance["balanced"] and exit_code == 0 and not timed_out}
        write_json(PARSE_LOGS / f"{item['id'].lower()}.json", result); results.append(result)
    payload = {"schema": "bindcheck.d1p14d.parse-preflight/v1", "created_at_utc": utc_now(),
        "classification": "eleven non-primary parser checks", "results": results,
        "all_pass": all(item["pass"] for item in results), "parse_only_calls": len(results),
        "scheduled_solver_calls": 0}
    write_json(PREFLIGHT, payload); return 0 if payload["all_pass"] else 1


def load_monitor():
    spec = importlib.util.spec_from_file_location("d1p14d_d1p07", MONITOR_RUNNER)
    module = importlib.util.module_from_spec(spec); assert spec.loader is not None
    spec.loader.exec_module(module); return module


def solver_answer(call: dict[str, Any]) -> str:
    if call["status"] != "COMPLETED": return "UNKNOWN"
    output = (ROOT / call["stdout_path"]).read_text(errors="replace")
    for line in output.splitlines():
        if line.strip().lower() in {"sat", "unsat", "unknown"}: return line.strip().upper()
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
        for match in pattern.finditer(text): bv[match.group(1)] = int(match.group(2), base)
    ff = {int(match.group(1)): int(match.group(2) or match.group(3)) for match in FF_RE.finditer(text)}
    return bv, ff


def validate_control(call: dict[str, Any], item: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    answer, expected = call["answer"], item["expected"]
    value: dict[str, Any] = {"id": item["id"], "expected": expected, "observed": answer, "pass": False}
    if answer != expected:
        value["reason"] = f"expected {expected}, observed {answer} ({call['status']})"; return value
    if expected == "UNSAT":
        value.update({"pass": True, "reason": "original summary with fixed fixture contradicts designated violation"}); return value
    text = (ROOT / call["stdout_path"]).read_text(errors="replace"); bv, _ = parse_model(text)
    required = [f"pi{index}" for index in range(11)] + ["basefee"]
    fixed = {f"pi{index}": word for index, word in enumerate(fixture_words(fixture))}
    fixed["basefee"] = int(fixture["environment"]["basefee"])
    comparisons = {name: bv.get(name) == fixed[name] for name in required}
    expected_records = json.loads(EXPECTED.read_text())["records"][item["control"]]
    conditions = {"full_model_assignment": all(name in bv for name in required),
        "assignment_equals_frozen_fixture": all(comparisons.values()),
        "precomputed_positive_target_true": expected_records["positive"]["goals"][item["target"]] is True,
        "precomputed_negative_target_false": expected_records["negative"]["goals"][item["target"]] is False,
        "expected_effect_checks_pass": expected_records["all_checks_pass"]}
    value.update({"model_bitvectors": {name: str(bv[name]) for name in required if name in bv},
        "fixture_comparisons": comparisons, "conditions": conditions, "pass": all(conditions.values()),
        "reason": "SAT assignment equals frozen fixture and independently expected mutant effect" if all(conditions.values()) else "SAT assignment validation failed"})
    return value


def stage_run() -> int:
    manifest = verify_frozen(); preflight = json.loads(PREFLIGHT.read_text())
    if not preflight["all_pass"] or preflight["parse_only_calls"] != 11: raise SystemExit("preflight gate failed")
    if LEDGER.exists() or SOLVER_LOGS.exists(): raise SystemExit("schedule already started")
    fixture = json.loads(FIXTURE.read_text()); c_records = c_primary_records()
    d1p07 = load_monitor(); monitor = d1p07.D1P05.MacProcessTreeMonitor()
    ledger: dict[str, Any] = {"schema": "bindcheck.d1p14d.solver-ledger/v1",
        "started_at_utc": utc_now(), "manifest": record(MANIFEST), "preflight": record(PREFLIGHT),
        "schedule": manifest["schedule"], "calls": [], "control_validations": [],
        "scheduled_solver_calls": 0, "stopped": False, "stop_reason": None,
        "original_d1p14c_C2": "UNKNOWN/TIMEOUT at 60 seconds; preserved and not retroactively resolved"}
    controls_pass = True
    for index, item in enumerate(manifest["schedule"], start=1):
        verify_frozen(); query = ROOT / item["query"]["path"]
        if item["kind"] == "primary":
            if not controls_pass or len(ledger["control_validations"]) != 8:
                ledger["stopped"] = True; ledger["stop_reason"] = "control gate incomplete"; break
            expected_hash = c_records[item["id"]]["query"]["sha256"]
            source = ROOT / c_records[item["id"]]["query"]["path"]
            if file_sha256(query) != expected_hash or file_sha256(source) != expected_hash:
                ledger["stopped"] = True; ledger["stop_reason"] = f"D1P-14C hash mismatch before {item['id']}"; break
        call = d1p07.run_monitored(index=index, kind=item["kind"], name=item["id"],
            argv=[str(SOLVER), *SOLVER_ARGS], logs_dir=SOLVER_LOGS, monitor=monitor,
            input_path=query, timeout_seconds=float(item["timeout_seconds"]),
            rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL)
        call["answer"] = solver_answer(call); call["schedule_item"] = item
        ledger["calls"].append(call); ledger["scheduled_solver_calls"] += 1
        if item["kind"] == "control":
            validation = validate_control(call, item, fixture); ledger["control_validations"].append(validation)
            if not validation["pass"]:
                controls_pass = False; ledger["stopped"] = True
                ledger["stop_reason"] = f"control {item['id']} failed"; write_json(LEDGER, ledger); break
        write_json(LEDGER, ledger)
    ledger["finished_at_utc"] = utc_now()
    ledger["all_controls_pass"] = len(ledger["control_validations"]) == 8 and all(item["pass"] for item in ledger["control_validations"])
    ledger["primary_calls"] = sum(call["kind"] == "primary" for call in ledger["calls"])
    ledger["complete_schedule"] = ledger["scheduled_solver_calls"] == 11 and ledger["primary_calls"] == 3
    ledger["charged_solver_seconds"] = round(sum(min(float(call["elapsed_seconds"]), float(call["timeout_seconds"])) for call in ledger["calls"]), 6)
    ledger["answers"] = {call["name"]: call["answer"] for call in ledger["calls"]}
    write_json(LEDGER, ledger)
    return 0 if ledger["complete_schedule"] and ledger["all_controls_pass"] else 1


def prover_toml(public: list[int], private: list[int]) -> str:
    value = lambda item: f'"0x{item:x}"'
    lines = [f"{name} = {value(public[index])}" for index, name in enumerate(PUBLIC_INPUTS)]
    lines.extend([f"origin_local_root = {value(private[0])}",
        f"is_from_aztec = {'true' if private[1] else 'false'}",
        f"nullifier_preimage = {value(private[2])}", f"secret = {value(private[3])}", "",
        "[aztec_merkle_data]", f"leaf_index = {value(private[4])}",
        "hash_path = [" + ", ".join(value(item) for item in private[5:47]) + "]",
        f"leaf_nonce = {value(private[47])}", "", "[evm_merkle_data]",
        f"leaf_index = {value(private[48])}",
        "hash_path = [" + ", ".join(value(item) for item in private[49:81]) + "]", "",
        "[giga_merkle_data]", f"leaf_index = {value(private[81])}",
        "hash_path = [" + ", ".join(value(item) for item in private[82:87]) + "]"])
    return "\n".join(lines) + "\n"


def validate_primary_sat(call: dict[str, Any]) -> dict[str, Any]:
    name = call["name"]; output_dir = VALIDATION / name.lower(); output_dir.mkdir(parents=True, exist_ok=False)
    stdout = (ROOT / call["stdout_path"]).read_text(errors="replace"); bv, ff = parse_model(stdout)
    result: dict[str, Any] = {"query": name, "status": "UNKNOWN",
        "model": {"bitvectors": len(bv), "field_witnesses": len(ff)}}
    if any(f"pi{index}" not in bv for index in range(11)) or "basefee" not in bv:
        result["reason"] = "SAT model lacks full public/basefee assignment"; return result
    public = [bv[f"pi{index}"] for index in range(11)]
    honest = json.loads((D1P13 / "honest-witness.json").read_text())["witnesses"]
    private, fallback = [], []
    for index in range(11, 98):
        if index in ff: private.append(ff[index])
        else: private.append(int(honest[str(index)], 0)); fallback.append(index)
    candidate = {"schema": "bindcheck.d1p14d.candidate/v1", "query": name,
        "public_words": list(map(str, public)), "private_abi_witnesses_w11_w97": list(map(str, private)),
        "private_fallback_from_honest_anchor": fallback, "basefee": str(bv["basefee"]),
        "msg_sender": "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
        "intermediate_model_witnesses_ignored": True}
    candidate_path = output_dir / "candidate.json"; write_json(candidate_path, candidate)
    prover_name = f"D1P14D_{name}"; prover_path = WORKSPACE / "backend/circuits/withdraw" / f"{prover_name}.toml"
    prover_path.write_text(prover_toml(public, private))
    nargo = run_recorded(f"validate-{name.lower()}-nargo",
        [str(NARGO), "execute", f"d1p14d_{name.lower()}", "--prover-name", prover_name],
        WORKSPACE / "backend/circuits/withdraw", 600)
    result.update({"candidate": record(candidate_path), "prover_input": record(prover_path), "nargo": nargo})
    if nargo["exit_code"] != 0 or nargo["timed_out"]:
        result["reason"] = "pinned beta.22 nargo execute did not validate candidate"; return result
    execution_path = output_dir / "consumer-execution.json"
    consumer = run_recorded(f"validate-{name.lower()}-consumer",
        [str(WORKSPACE / "backend/node_modules/.bin/hardhat"), "test", "--network", "edr", "--no-compile", "test/d1p14c.candidate.fixture.ts"],
        WORKSPACE / "backend", 600,
        {"D1P14C_CANDIDATE": str(candidate_path), "D1P14C_EXECUTION": str(execution_path)})
    result["consumer_command"] = consumer
    if not execution_path.exists(): result["reason"] = "consumer stage produced no result"; return result
    execution = json.loads(execution_path.read_text()); result["consumer_execution"] = record(execution_path)
    if consumer["exit_code"] != 0 or not execution.get("accepted"):
        result["reason"] = "unchanged consumer did not commit candidate"; return result
    result["status"] = "VALIDATED_SAT"; result["reason"] = "existing section 6(b) V-EXEC route passed"
    return result


def stage_validate() -> int:
    verify_frozen(); ledger = json.loads(LEDGER.read_text())
    if not ledger["complete_schedule"] or not ledger["all_controls_pass"]: raise SystemExit("schedule incomplete")
    if VALIDATION_SUMMARY.exists(): raise SystemExit("validation exists")
    results = []
    for call in ledger["calls"]:
        if call["kind"] != "primary": continue
        if call["answer"] == "SAT":
            result = validate_primary_sat(call); write_json(VALIDATION / call["name"].lower() / "result.json", result)
        else:
            result = {"query": call["name"], "solver_answer": call["answer"],
                      "validation": "V-EXEC not applicable without SAT"}
        results.append(result)
    write_json(VALIDATION_SUMMARY, {"schema": "bindcheck.d1p14d.validation-summary/v1",
        "results": results, "NONVAC_sat_requires_vexec": True, "proof_generation_calls": 0})
    return 0


def stage_audit() -> int:
    manifest = verify_frozen(); preflight = json.loads(PREFLIGHT.read_text())
    ledger = json.loads(LEDGER.read_text()); validation = json.loads(VALIDATION_SUMMARY.read_text())
    checks = {"prior_D1P14B_C_preserved": True,
        "fixture_checks_pass": json.loads(FIXTURE.read_text())["all_checks_pass"],
        "expected_effect_checks_pass": json.loads(EXPECTED.read_text())["all_checks_pass"],
        "eleven_parser_checks_pass": preflight["all_pass"] and preflight["parse_only_calls"] == 11,
        "eight_control_polarities_pass": ledger["all_controls_pass"],
        "three_unchanged_primary_calls": ledger["primary_calls"] == 3 and ledger["complete_schedule"],
        "proof_generation_zero": validation["proof_generation_calls"] == 0,
        "original_C2_timeout_still_separate": "not retroactively resolved" in ledger["original_d1p14c_C2"]}
    write_json(AUDIT, {"schema": "bindcheck.d1p14d.audit/v1", "created_at_utc": utc_now(),
        "checks": checks, "all_checks_pass": all(checks.values()), "answers": ledger["answers"],
        "manifest": record(MANIFEST), "fixture": record(FIXTURE), "expected_effects": record(EXPECTED),
        "preflight": record(PREFLIGHT), "ledger": record(LEDGER), "validation": record(VALIDATION_SUMMARY),
        "D1P14B_tree": tree_identity(RAW_B), "D1P14C_tree": tree_identity(RAW_C),
        "claim_boundary": manifest["claim_boundary"], "D1_verdict": "UNKNOWN"})
    return 0 if all(checks.values()) else 1


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--stage", required=True,
        choices=["setup", "prepare", "preflight", "run", "validate", "audit"])
    stages = {"setup": stage_setup, "prepare": stage_prepare, "preflight": stage_preflight,
              "run": stage_run, "validate": stage_validate, "audit": stage_audit}
    raise SystemExit(stages[parser.parse_args().stage]())


if __name__ == "__main__":
    main()
