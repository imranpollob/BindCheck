#!/usr/bin/env python3 -I
"""D1-05 consumer-directed refinement experiment.

Runs the CEGAR loop (abstract → concretize → refine) for auth_unmatched on both synthetic
cases. Runs cov_unmatched and nonvacuity with the full encoder (same as D1-03) for controls.
Replays SAT models with nargo.
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
from bindcheck_d1.analysis.refinement import RefinementEngine
from bindcheck_d1.policy import Policy
from bindcheck_d1.result import Result, unknown

NARGO = ROOT / "tools/noir-1.0.0-beta.14/nargo"
CASES = ROOT / "cases/d1/synth"
RAW = ROOT / "results/raw/D1-05"
TIMEOUT_MS = 60_000


def nargo_replay(producer_dir, prog, model, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    auth_ws = prog.table["authorized"]
    msg_ws = prog.table["messages"]
    auth_strs = [f'"0x{model.get(w, 0):x}"' for w in auth_ws]
    msg_strs = [f'"0x{model.get(w, 0):x}"' for w in msg_ws]
    prover = f"authorized = [{', '.join(auth_strs)}]\nmessages = [{', '.join(msg_strs)}]\n"
    prover_path = out_dir / "Prover.toml"
    prover_path.write_text(prover)
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
            return True, "nargo execute succeeded"
        return False, f"nargo execute failed (rc={r.returncode}): {r.stderr.strip()[-300:]}"
    except subprocess.TimeoutExpired:
        return False, "nargo execute timed out (600s)"
    finally:
        if target_prover.exists():
            target_prover.unlink()


def run_case(case_name, producer_dir, policy_path, raw_dir):
    print(f"\n{'='*60}")
    print(f"D1-05 CEGAR: {case_name}")
    print(f"{'='*60}")

    case_dir = raw_dir / case_name
    smt_dir = case_dir / "smt"
    smt_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = case_dir / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)

    # 1. Compile and parse ACIR
    target = producer_dir / "target"
    jsons = list(target.glob("*.json"))
    if len(jsons) != 1:
        return unknown(case_name, "FREE", "UNSUPPORTED_ACIR")
    abi_path = jsons[0]

    acir_path = case_dir / "acir.txt"
    r = subprocess.run([str(NARGO), "compile", "--program-dir", str(producer_dir), "--print-acir"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return unknown(case_name, "FREE", "UNSUPPORTED_ACIR")
    acir_path.write_text(r.stdout)
    print(f"  ACIR: {len(r.stdout)} bytes")

    try:
        prog = acir_fe.load(str(acir_path), str(abi_path))
    except acir_fe.Unsupported as e:
        return unknown(case_name, "FREE", f"UNSUPPORTED_ACIR:{e}")
    print(f"  Parsed: {len(prog.ops)} ops")

    pol = Policy.load(str(policy_path))

    # 2. Propagate
    state = pr.State(prog.ops, {}).run()
    asserts, ranges, mem = state.residual()
    print(f"  Residual: {len(asserts)} asserts, {len(ranges)} ranges")

    # 3. CEGAR for auth_unmatched
    print("\n  --- CEGAR auth_unmatched ---")
    t0 = time.time()
    engine = RefinementEngine(prog, state, pol, TIMEOUT_MS)
    print(f"  Total constraints: {len(engine.all_asserts)} asserts, {len(engine.all_ranges)} ranges")

    auth_status, auth_info = engine.auth_unmatched_refine(str(smt_dir / "auth_cegar"))
    auth_secs = round(time.time() - t0, 2)
    iters = auth_info.get("iterations", 0)
    print(f"  AUTH CEGAR: {auth_status} in {iters} iteration(s), {auth_secs}s total")

    for entry in engine.log:
        it = entry["iteration"]
        a_st = entry["abstract_status"]
        inc_a = entry["included_asserts"]
        inc_r = entry["included_ranges"]
        tot_a = entry["total_asserts"]
        tot_r = entry["total_ranges"]
        c_st = entry.get("concretize_status", "-")
        spur = entry.get("spurious", False)
        added = entry.get("refined_added", 0)
        result = entry.get("result", "?")
        print(f"    iter {it}: abstract={a_st}, constraints={inc_a}/{tot_a} asserts + {inc_r}/{tot_r} ranges, "
              f"concretize={c_st}, spurious={spur}, added={added} → {result}")

    goals = {"auth_unmatched_cegar": {
        "status": auth_status,
        "seconds": auth_secs,
        "iterations": iters,
        "log": engine.log,
        "final_constraints": engine.constraint_counts(),
    }}

    # 4. Replay auth model if SAT
    replay_results = {}
    if auth_status == "sat" and "model" in auth_info:
        model = auth_info["model"]
        goals["auth_unmatched_cegar"]["model"] = model
        goals["auth_unmatched_cegar"]["slot"] = auth_info.get("slot")
        print(f"  Replaying AUTH model (slot {auth_info.get('slot')})...")
        ok, detail = nargo_replay(producer_dir, prog, model, replay_dir / "auth")
        replay_results["auth_unmatched_cegar"] = {"ok": ok, "detail": detail}
        print(f"    Replay: {'PASS' if ok else 'FAIL'} - {detail}")

    # 5. Full-encoder cov_unmatched (control)
    print("\n  --- Full-encoder cov_unmatched (control) ---")
    cov_dir = smt_dir / "cov"
    cov_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    enc_cov = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc_cov.encode_producer()
    cov_status, cov_info = enc_cov.cov_unmatched(str(cov_dir))
    cov_secs = round(time.time() - t0, 2)
    goals["cov_unmatched"] = {"status": cov_status, "seconds": cov_secs}
    print(f"  COV: {cov_status} ({cov_secs}s)")

    # 6. Full-encoder nonvacuity (control)
    print("\n  --- Full-encoder nonvacuity (control) ---")
    nonvac_dir = smt_dir / "nonvac"
    nonvac_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    enc_nv = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc_nv.encode_producer()
    nv_status, nv_info = enc_nv.nonvacuity(str(nonvac_dir))
    nv_secs = round(time.time() - t0, 2)
    goals["nonvacuity"] = {"status": nv_status, "seconds": nv_secs}
    print(f"  NONVAC: {nv_status} ({nv_secs}s)")
    if nv_status == "sat":
        goals["nonvacuity"]["model"] = nv_info.get("model", {})
        print(f"  Replaying NONVAC model...")
        ok, detail = nargo_replay(producer_dir, prog, nv_info["model"], replay_dir / "nonvac")
        replay_results["nonvacuity"] = {"ok": ok, "detail": detail}
        print(f"    Replay: {'PASS' if ok else 'FAIL'} - {detail}")

    # 7. Determine verdict
    verdict, grade, reasons, nonvac_label = determine_verdict(
        auth_status, cov_status, nv_status, replay_results, goals)

    provenance = {
        "acir_sha256": sha256_file(acir_path),
        "source_sha256": sha256_file(producer_dir / "src/main.nr"),
        "policy_sha256": sha256_file(policy_path),
    }

    result = Result(
        case=case_name,
        scope="FREE",
        verdict=verdict,
        evidence_grade=grade,
        reasons=reasons,
        assumptions=["A4", "A5", "A7"],
        bounds={"solver_timeout_ms": TIMEOUT_MS, "n": pol.n, "stride": pol.grammar.uniform,
                "cegar_iterations": iters},
        nonvacuity=nonvac_label,
        goals=goals,
        provenance=provenance,
    )
    print(f"\n  VERDICT: {verdict} (grade={grade}, nonvac={nonvac_label})")

    result_path = case_dir / "result.json"
    result_path.write_text(result.to_json())
    print(f"  Result: {result_path}")
    return result


def determine_verdict(auth_status, cov_status, nv_status, replays, goals):
    reasons = []
    if auth_status == "sat":
        replay = replays.get("auth_unmatched_cegar", {})
        if replay.get("ok"):
            return "VIOLATION", "CONCRETE_MODEL_REPLAYED", [], "NOT_CHECKED"
        reasons.append("CANDIDATE_NOT_CONCRETIZED")
        return "UNKNOWN", "ABSTRACT_MODEL", reasons, "NOT_CHECKED"
    if auth_status == "unsat" and cov_status == "unsat":
        if nv_status == "sat":
            nv_replay = replays.get("nonvacuity", {})
            if nv_replay.get("ok"):
                return "VERIFIED_WITHIN_SCOPE", "CONCRETE_MODEL_REPLAYED", [], "SAT_REPLAYED"
            reasons.append("NONVACUITY_UNRESOLVED")
            return "UNKNOWN", "ABSTRACT_MODEL", reasons, "SAT"
        elif nv_status == "unsat":
            reasons.append("NONVACUITY_UNRESOLVED")
            return "UNKNOWN", "NONE", reasons, "UNSAT"
        else:
            reasons.append("NONVACUITY_UNRESOLVED")
            return "UNKNOWN", "NONE", reasons, "UNKNOWN"
    if auth_status == "unknown":
        reasons.append("SOLVER_UNKNOWN")
    if cov_status == "unknown":
        reasons.append("SOLVER_UNKNOWN")
    if not reasons:
        reasons.append("MATCHING_UNRESOLVED")
    return "UNKNOWN", "NONE", reasons, "NOT_CHECKED"


def main():
    os.makedirs(RAW / "synthetic", exist_ok=True)
    policy_path = CASES / "policy.json"
    cases = [
        ("synth-faulty", CASES / "producer_faulty"),
        ("synth-repaired", CASES / "producer_repaired"),
    ]
    results = {}
    for name, pdir in cases:
        results[name] = run_case(name, pdir, policy_path, RAW / "synthetic")

    print(f"\n{'='*60}")
    print("D1-05 SUMMARY")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"  {name}: {r.verdict} (grade={r.evidence_grade}, nonvac={r.nonvacuity})")
        cegar = r.goals.get("auth_unmatched_cegar", {})
        print(f"    CEGAR: {cegar.get('iterations', '?')} iterations, "
              f"{cegar.get('seconds', '?')}s, "
              f"final constraints: {cegar.get('final_constraints', {})}")

    summary = {name: json.loads(r.to_json()) for name, r in results.items()}
    summary_path = RAW / "synthetic" / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary: {summary_path}")
    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if all(r.verdict != "UNKNOWN" for r in results.values()) else 1)
