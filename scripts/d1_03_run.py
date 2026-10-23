#!/usr/bin/env python3 -I
"""D1-03 joint-semantics orchestrator for synthetic cases.

Runs the full pipeline: ACIR parse → propagate → joint encode → solve goals → nargo replay.
Authored synthetic fixtures only (no third-party circuits).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1 import P
from bindcheck_d1.artifacts import Artifact, sha256_file
from bindcheck_d1.frontends import acir as acir_fe
from bindcheck_d1.analysis import propagate as pr
from bindcheck_d1.analysis import joint
from bindcheck_d1.policy import Policy
from bindcheck_d1.result import Result, unknown

NARGO = ROOT / "tools/noir-1.0.0-beta.14/nargo"
CASES = ROOT / "cases/d1/synth"
RAW = ROOT / "results/raw/D1-03"
TIMEOUT_MS = 60_000  # 60 s per query (well under 300 s protocol limit)


def run_case(case_name, producer_dir, policy_path, raw_dir):
    """Run analysis on one synthetic case. Returns Result."""
    print(f"\n{'='*60}")
    print(f"Case: {case_name}")
    print(f"{'='*60}")

    smt_dir = raw_dir / case_name / "smt"
    smt_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = raw_dir / case_name / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)

    # 1. Locate compiled artifacts
    target = producer_dir / "target"
    jsons = list(target.glob("*.json"))
    if len(jsons) != 1:
        return unknown(case_name, "FREE", "UNSUPPORTED_ACIR",
                       bounds={"note": f"expected 1 json, found {len(jsons)}"})
    abi_path = jsons[0]

    # Print ACIR
    acir_path = raw_dir / case_name / "acir.txt"
    r = subprocess.run([str(NARGO), "compile", "--program-dir", str(producer_dir), "--print-acir"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return unknown(case_name, "FREE", "UNSUPPORTED_ACIR",
                       bounds={"compile_error": r.stderr[:500]})
    acir_path.write_text(r.stdout)
    print(f"  ACIR printed: {acir_path.name} ({len(r.stdout)} bytes)")

    # 2. Parse ACIR
    try:
        prog = acir_fe.load(str(acir_path), str(abi_path))
    except acir_fe.Unsupported as e:
        return unknown(case_name, "FREE", f"UNSUPPORTED_ACIR:{e}")
    print(f"  Parsed: {len(prog.ops)} ops, public={prog.public}, private={prog.private}")
    print(f"  ABI table: {list(prog.table.keys())}")
    print(f"  Recursions: {len(prog.recursions)}, unmodeled: {len(prog.unmodeled)}")

    # 3. Load policy
    pol = Policy.load(str(policy_path))
    print(f"  Policy: n={pol.n}, grammar={pol.grammar.lengths}, uniform={pol.grammar.uniform}")

    # 4. Propagate (no fixed values for synthetic - all witnesses free)
    state = pr.State(prog.ops, {}).run()
    asserts, ranges, mem = state.residual()
    print(f"  Propagation: {len(state.val)} assigned, {len(asserts)} residual asserts, {len(ranges)} ranges, {len(mem)} mem")

    # 5. Joint encoder
    enc = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    try:
        enc.encode_producer()
    except acir_fe.Unsupported as e:
        return unknown(case_name, "FREE", f"UNSUPPORTED_ACIR:{e}")
    print("  Producer residual encoded")

    # 6. Goals
    goals = {}

    # 6a. AUTH-UNMATCHED
    print("  Solving AUTH-UNMATCHED...")
    t0 = time.time()
    auth_status, auth_info = enc.auth_unmatched(str(smt_dir))
    auth_secs = round(time.time() - t0, 2)
    goals["auth_unmatched"] = {"status": auth_status, "seconds": auth_secs}
    if "probes" in auth_info:
        goals["auth_unmatched"]["probes"] = auth_info["probes"]
    print(f"    AUTH-UNMATCHED: {auth_status} ({auth_secs}s)")
    if auth_status == "sat":
        model = auth_info.get("model", {})
        goals["auth_unmatched"]["model"] = model
        goals["auth_unmatched"]["slot"] = auth_info.get("slot")
        print(f"    Model slot {auth_info.get('slot')}: {model}")

    # 6b. COV-UNMATCHED
    print("  Solving COV-UNMATCHED...")
    t0 = time.time()
    enc2 = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc2.encode_producer()
    cov_status, cov_info = enc2.cov_unmatched(str(smt_dir))
    cov_secs = round(time.time() - t0, 2)
    goals["cov_unmatched"] = {"status": cov_status, "seconds": cov_secs}
    if "probes" in cov_info:
        goals["cov_unmatched"]["probes"] = cov_info["probes"]
    print(f"    COV-UNMATCHED: {cov_status} ({cov_secs}s)")

    # 6c. NONVACUITY
    print("  Solving NONVACUITY...")
    t0 = time.time()
    enc3 = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc3.encode_producer()
    nonvac_status, nonvac_info = enc3.nonvacuity(str(smt_dir))
    nonvac_secs = round(time.time() - t0, 2)
    goals["nonvacuity"] = {"status": nonvac_status, "seconds": nonvac_secs}
    print(f"    NONVACUITY: {nonvac_status} ({nonvac_secs}s)")
    if nonvac_status == "sat":
        goals["nonvacuity"]["model"] = nonvac_info.get("model", {})

    # 7. Replay with nargo execute
    replay_results = {}
    for goal_name, goal_data in goals.items():
        if goal_data["status"] != "sat" or "model" not in goal_data:
            continue
        model = goal_data["model"]
        print(f"  Replaying {goal_name} model with nargo execute...")
        replay_ok, replay_detail = nargo_replay(producer_dir, prog, model, replay_dir / goal_name)
        replay_results[goal_name] = {"ok": replay_ok, "detail": replay_detail}
        print(f"    Replay {goal_name}: {'PASS' if replay_ok else 'FAIL'} - {replay_detail}")

    # 8. Determine verdict
    verdict, grade, reasons, nonvac_label = determine_verdict(
        auth_status, cov_status, nonvac_status, replay_results, goals)

    artifacts = [
        Artifact.of("producer-acir", acir_path, tool=f"nargo {get_nargo_version()}"),
        Artifact.of("producer-abi", abi_path, tool=f"nargo {get_nargo_version()}"),
        Artifact.of("policy", policy_path),
    ]
    provenance = {
        "acir_sha256": artifacts[0].sha256,
        "abi_sha256": artifacts[1].sha256,
        "policy_sha256": artifacts[2].sha256,
        "source": str(producer_dir / "src/main.nr"),
        "source_sha256": sha256_file(producer_dir / "src/main.nr"),
    }

    result = Result(
        case=case_name,
        scope="FREE",
        verdict=verdict,
        evidence_grade=grade,
        reasons=reasons,
        assumptions=["A4", "A5", "A7"],
        bounds={"solver_timeout_ms": TIMEOUT_MS, "n": pol.n, "stride": pol.grammar.uniform},
        nonvacuity=nonvac_label,
        goals=goals,
        provenance=provenance,
    )
    print(f"\n  VERDICT: {verdict} (grade={grade}, nonvacuity={nonvac_label})")

    # Save result
    result_path = raw_dir / case_name / "result.json"
    result_path.write_text(result.to_json())
    print(f"  Result saved: {result_path}")

    return result


def nargo_replay(producer_dir, prog, model, out_dir):
    """Execute nargo with the given model as Prover.toml witness. Returns (success, detail)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build Prover.toml: authorized = private witnesses, messages = public witnesses
    lines = []
    auth_ws = prog.table["authorized"]
    msg_ws = prog.table["messages"]

    auth_vals = [model.get(w, 0) for w in auth_ws]
    msg_vals = [model.get(w, 0) for w in msg_ws]

    # Format as hex strings for Noir Field type
    auth_strs = [f'"0x{v:x}"' for v in auth_vals]
    msg_strs = [f'"0x{v:x}"' for v in msg_vals]

    prover = f"authorized = [{', '.join(auth_strs)}]\nmessages = [{', '.join(msg_strs)}]\n"
    prover_path = out_dir / "Prover.toml"
    prover_path.write_text(prover)

    # Copy Prover.toml to the producer directory for nargo execute
    target_prover = producer_dir / "Prover.toml"
    target_prover.write_text(prover)

    try:
        r = subprocess.run(
            [str(NARGO), "execute", "--program-dir", str(producer_dir)],
            capture_output=True, text=True, timeout=600)
        (out_dir / "stdout.txt").write_text(r.stdout)
        (out_dir / "stderr.txt").write_text(r.stderr)
        (out_dir / "returncode.txt").write_text(str(r.returncode))

        if r.returncode == 0:
            return True, "nargo execute succeeded (witness satisfies all circuit constraints)"
        else:
            err = r.stderr.strip()[-300:] if r.stderr else "(no stderr)"
            return False, f"nargo execute failed (rc={r.returncode}): {err}"
    except subprocess.TimeoutExpired:
        return False, "nargo execute timed out (600s)"
    finally:
        # Clean up Prover.toml from producer dir
        if target_prover.exists():
            target_prover.unlink()


def determine_verdict(auth_status, cov_status, nonvac_status, replays, goals):
    """Map goal results to a verdict per the research contract."""
    reasons = []

    # VIOLATION: auth_unmatched SAT with a successful replay
    if auth_status == "sat":
        replay = replays.get("auth_unmatched", {})
        if replay.get("ok"):
            return "VIOLATION", "CONCRETE_MODEL_REPLAYED", [], "NOT_CHECKED"
        else:
            reasons.append("CANDIDATE_NOT_CONCRETIZED")
            return "UNKNOWN", "ABSTRACT_MODEL", reasons, "NOT_CHECKED"

    # If auth is unsat, check for VERIFIED
    if auth_status == "unsat" and cov_status == "unsat":
        # Need non-vacuity for VERIFIED_WITHIN_SCOPE
        if nonvac_status == "sat":
            nonvac_replay = replays.get("nonvacuity", {})
            if nonvac_replay.get("ok"):
                return "VERIFIED_WITHIN_SCOPE", "CONCRETE_MODEL_REPLAYED", [], "SAT_REPLAYED"
            else:
                reasons.append("NONVACUITY_UNRESOLVED")
                return "UNKNOWN", "ABSTRACT_MODEL", reasons, "SAT"
        elif nonvac_status == "unsat":
            reasons.append("NONVACUITY_UNRESOLVED")
            return "UNKNOWN", "NONE", reasons, "UNSAT"
        else:
            reasons.append("NONVACUITY_UNRESOLVED")
            return "UNKNOWN", "NONE", reasons, "UNKNOWN"

    # Solver didn't finish or mixed results
    if auth_status == "unknown":
        reasons.append("SOLVER_UNKNOWN")
    if cov_status == "unknown":
        reasons.append("SOLVER_UNKNOWN")
    if not reasons:
        reasons.append("MATCHING_UNRESOLVED")
    return "UNKNOWN", "NONE", reasons, "NOT_CHECKED"


def get_nargo_version():
    r = subprocess.run([str(NARGO), "--version"], capture_output=True, text=True, timeout=10)
    for line in r.stdout.splitlines():
        if "nargo version" in line:
            return line.split("=")[1].strip()
    return "unknown"


def main():
    os.makedirs(RAW / "synthetic", exist_ok=True)

    policy_path = CASES / "policy.json"
    cases = [
        ("synth-faulty", CASES / "producer_faulty"),
        ("synth-repaired", CASES / "producer_repaired"),
    ]

    results = {}
    for name, pdir in cases:
        result = run_case(name, pdir, policy_path, RAW / "synthetic")
        results[name] = result

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"  {name}: {r.verdict} (grade={r.evidence_grade}, nonvac={r.nonvacuity})")
        if r.reasons:
            print(f"    reasons: {r.reasons}")

    # Save combined summary
    summary = {name: json.loads(r.to_json()) for name, r in results.items()}
    summary_path = RAW / "synthetic" / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary saved: {summary_path}")

    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if all(r.verdict != "UNKNOWN" for r in results.values()) else 1)
