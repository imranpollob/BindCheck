#!/usr/bin/env python3 -I
"""D1-04 baseline comparison: monolithic (no propagation) vs D1-03 propagated,
and summary-based modular check.

Runs B2 and B3 on both synthetic cases. B1 (Foundry) is run separately.
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
from bindcheck_d1.frontends import acir as acir_fe
from bindcheck_d1.analysis import propagate as pr
from bindcheck_d1.analysis import joint
from bindcheck_d1.policy import Policy

NARGO = ROOT / "tools/noir-1.0.0-beta.14/nargo"
CASES = ROOT / "cases/d1/synth"
RAW = ROOT / "results/raw/D1-04"
TIMEOUT_MS = 60_000


def get_acir_text(producer_dir):
    r = subprocess.run([str(NARGO), "compile", "--program-dir", str(producer_dir), "--print-acir"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
    return r.stdout


def load_program(producer_dir, acir_text):
    acir_path = producer_dir / "target" / "acir.txt"
    acir_path.write_text(acir_text)
    jsons = list((producer_dir / "target").glob("*.json"))
    return acir_fe.load(str(acir_path), str(jsons[0]))


def nargo_replay(producer_dir, prog, model, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    auth_ws = prog.table["authorized"]
    msg_ws = prog.table["messages"]
    auth_strs = [f'"0x{model.get(w, 0):x}"' for w in auth_ws]
    msg_strs = [f'"0x{model.get(w, 0):x}"' for w in msg_ws]
    prover = f"authorized = [{', '.join(auth_strs)}]\nmessages = [{', '.join(msg_strs)}]\n"
    (out_dir / "Prover.toml").write_text(prover)
    target_prover = producer_dir / "Prover.toml"
    target_prover.write_text(prover)
    try:
        r = subprocess.run([str(NARGO), "execute", "--program-dir", str(producer_dir)],
                           capture_output=True, text=True, timeout=600)
        (out_dir / "returncode.txt").write_text(str(r.returncode))
        return r.returncode == 0
    finally:
        if target_prover.exists():
            target_prover.unlink()


def run_goals(enc, smt_dir, label):
    """Run all three goals and return timing/verdict dict."""
    results = {}

    # AUTH-UNMATCHED
    t0 = time.time()
    auth_status, auth_info = enc.auth_unmatched(str(smt_dir))
    auth_secs = round(time.time() - t0, 2)
    results["auth_unmatched"] = {"status": auth_status, "seconds": auth_secs}
    if auth_status == "sat":
        results["auth_unmatched"]["model"] = auth_info.get("model", {})
        results["auth_unmatched"]["slot"] = auth_info.get("slot")
    print(f"    [{label}] AUTH-UNMATCHED: {auth_status} ({auth_secs}s)")

    return results, auth_status, auth_info


def run_full_goals(prog, state, pol, smt_dir, label):
    """Run all three goal types with fresh encoders."""
    all_results = {}

    # AUTH
    enc1 = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc1.encode_producer()
    smt_auth = smt_dir / "auth"
    smt_auth.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    auth_status, auth_info = enc1.auth_unmatched(str(smt_auth))
    auth_secs = round(time.time() - t0, 2)
    all_results["auth_unmatched"] = {"status": auth_status, "seconds": auth_secs}
    if auth_status == "sat":
        all_results["auth_unmatched"]["model"] = auth_info.get("model", {})
        all_results["auth_unmatched"]["slot"] = auth_info.get("slot")
    print(f"    [{label}] AUTH-UNMATCHED: {auth_status} ({auth_secs}s)")

    # COV
    enc2 = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc2.encode_producer()
    smt_cov = smt_dir / "cov"
    smt_cov.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cov_status, cov_info = enc2.cov_unmatched(str(smt_cov))
    cov_secs = round(time.time() - t0, 2)
    all_results["cov_unmatched"] = {"status": cov_status, "seconds": cov_secs}
    print(f"    [{label}] COV-UNMATCHED: {cov_status} ({cov_secs}s)")

    # NONVAC
    enc3 = joint.JointEncoder(prog, state, pol, TIMEOUT_MS)
    enc3.encode_producer()
    smt_nonvac = smt_dir / "nonvac"
    smt_nonvac.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    nonvac_status, nonvac_info = enc3.nonvacuity(str(smt_nonvac))
    nonvac_secs = round(time.time() - t0, 2)
    all_results["nonvacuity"] = {"status": nonvac_status, "seconds": nonvac_secs}
    if nonvac_status == "sat":
        all_results["nonvacuity"]["model"] = nonvac_info.get("model", {})
    print(f"    [{label}] NONVACUITY: {nonvac_status} ({nonvac_secs}s)")

    return all_results, auth_status, auth_info, nonvac_status, nonvac_info


# =============================================================================
# B3: Summary-based modular check
# =============================================================================

def run_b3_case(case_name, is_repaired, pol, smt_dir, timeout_ms):
    """Run B3 (summary-based) on one case.

    Manual summary (25 LOC of specification logic):
      For each record r: if any earlier record kind=0 ('ended'), then auth[r]=0;
      if not ended, msgs[r] = auth[r]; if ended AND repaired, msgs[r] = 0.
    Uses ff.ite for conditional constraints.
    """
    M = joint._ff_module()
    ff = M.FF(timeout_ms)

    N = pol.n  # 9
    S = pol.grammar.uniform  # 3
    R = N // S  # 3 records

    # Declare all variables: authorized=w0..w8, messages=w9..w17
    for i in range(2 * N):
        ff.var(i)

    # Build "ended at record r" as a cascading Bool
    ended = []
    for r in range(R):
        k = r * S
        is_pad = ff.eq(ff.var(k), ff.zero)
        ended.append(is_pad if r == 0 else ff.OR(ended[r - 1], is_pad))

    # Encode summary constraints using ite
    for r in range(R):
        k = r * S
        mk = k + N
        for offset in range(S):
            aw = ff.var(k + offset)
            mw = ff.var(mk + offset)
            # ended => auth[k+offset] = 0
            ff.A(ff.eq(ff.ite(ended[r], aw, ff.zero), ff.zero))
            # not ended => msgs = auth
            ff.A(ff.eq(ff.ite(ended[r], ff.zero, ff.sub(mw, aw)), ff.zero))
            if is_repaired:
                # ended => msgs = 0
                ff.A(ff.eq(ff.ite(ended[r], mw, ff.zero), ff.zero))

    msg_w = list(range(N, 2 * N))
    perm_w = list(range(N))
    return ff, msg_w, perm_w


def b3_walk(ff, pol, words):
    """Same symbolic walk as JointEncoder.walk but standalone."""
    g = pol.grammar
    n = pol.n
    L = g.uniform
    valid = sorted(g.lengths)
    starts = list(range(0, n - L + 1, L))

    def word(w):
        return ff.c(0) if False else ff.var(w)

    def blet(expr):
        ff.n += 1
        nm = f"b{ff.n}"
        ff.lines.append(f"(define-fun {nm} () Bool {expr})")
        return nm

    prefix_ok = ff.T
    rev_terms, burns, mints = [], [], []
    for i in starts:
        ki = ff.var(words[i])
        valid_here = ff.OR(*[ff.eq(ki, ff.c(k)) for k in valid])
        rev_terms.append(blet(ff.AND(prefix_ok, ff.NOT(valid_here))))
        is_burn = blet(ff.AND(prefix_ok, ff.eq(ki, ff.c(g.burn_kind))))
        burns.append((i, is_burn, ff.var(words[i + g.burn_value_offset]),
                       ff.var(words[i + g.burn_recipient_offset])))
        is_mint = blet(ff.AND(prefix_ok, ff.eq(ki, ff.c(g.mint_kind))))
        mints.append((i, is_mint, ff.var(words[i + g.mint_id_offset])))
        prefix_ok = blet(ff.AND(prefix_ok, valid_here))

    revert = blet(ff.OR(*rev_terms)) if rev_terms else ff.Fa
    return revert, burns, mints


def b3_auth_unmatched(ff, pol, msg_w, perm_w, smt_dir):
    """B3 version of auth_unmatched."""
    rev_m, burns_m, _ = b3_walk(ff, pol, msg_w)
    _, burns_a, _ = b3_walk(ff, pol, perm_w)

    results = []
    for (i, is_burn_m, val_m, recip_m) in burns_m:
        matches = [ff.AND(bj, ff.eq(va, val_m), ff.eq(ra, recip_m)) for (_, bj, va, ra) in burns_a]
        unmatched = ff.AND(*[ff.NOT(mm) for mm in matches]) if matches else ff.T
        material = ff.ne(val_m, ff.zero)
        goal = ff.AND(ff.NOT(rev_m), is_burn_m, material, unmatched)

        # Solve
        saved = list(ff.lines)
        ff.A(goal)
        getv = [f"w{w}" for w in sorted(set(msg_w) | set(perm_w)) if w in ff.w]
        smt_path = f"{smt_dir}/b3_auth_slot{i}.smt2" if smt_dir else None
        status, out, secs = ff.solve(getv, smt_path)
        model = {}
        if status == "sat":
            vals = ff.parse_vals(out)
            model = {int(name[1:]): v % P for name, v in zip(getv, vals)}
        ff.lines = saved

        results.append({"slot": i, "status": status, "seconds": round(secs, 2)})
        if status == "sat":
            return "sat", {"slot": i, "model": model, "probes": results}
        if status == "unknown":
            return "unknown", {"probes": results}

    return "unsat", {"probes": results}


def b3_nonvacuity(ff, pol, msg_w, smt_dir):
    """B3 version of nonvacuity."""
    rev_m, burns_m, mints_m = b3_walk(ff, pol, msg_w)
    effects = [b for (_, b, _, _) in burns_m] + [b for (_, b, _) in mints_m]
    goal = ff.AND(ff.NOT(rev_m), ff.OR(*effects)) if effects else ff.Fa

    saved = list(ff.lines)
    ff.A(goal)
    getv = [f"w{w}" for w in sorted(set(msg_w) | set(range(pol.n))) if w in ff.w]
    smt_path = f"{smt_dir}/b3_nonvac.smt2" if smt_dir else None
    status, out, secs = ff.solve(getv, smt_path)
    model = {}
    if status == "sat":
        vals = ff.parse_vals(out)
        model = {int(name[1:]): v % P for name, v in zip(getv, vals)}
    ff.lines = saved
    return status, {"model": model, "seconds": round(secs, 2)}


def main():
    pol = Policy.load(str(CASES / "policy.json"))
    cases = [
        ("synth-faulty", CASES / "producer_faulty", False),
        ("synth-repaired", CASES / "producer_repaired", True),
    ]

    all_results = {}

    for case_name, producer_dir, is_repaired in cases:
        print(f"\n{'='*60}")
        print(f"Case: {case_name}")
        print(f"{'='*60}")

        acir_text = get_acir_text(producer_dir)
        prog = load_program(producer_dir, acir_text)

        case_results = {}

        # ---- B2: Monolithic (no propagation) --------------------------------
        print("\n  B2: Monolithic (no propagation)")
        b2_dir = RAW / case_name / "B2"
        b2_dir.mkdir(parents=True, exist_ok=True)
        state_noprop = pr.State(prog.ops, {})
        # Don't call .run() — leave all constraints as residual
        # But we need to at least initialize the polys dict
        # Actually State.__init__ already populates self.polys from assert ops.
        # .run() does fixpoint + memory + small-domain passes. Skipping it means
        # no propagation happens.
        b2_results, b2_auth, b2_auth_info, b2_nonvac, b2_nonvac_info = run_full_goals(
            prog, state_noprop, pol, b2_dir / "smt", "B2")

        # Replay if SAT
        b2_replays = {}
        if b2_auth == "sat" and "model" in b2_results["auth_unmatched"]:
            ok = nargo_replay(producer_dir, prog, b2_results["auth_unmatched"]["model"],
                              b2_dir / "replay" / "auth")
            b2_replays["auth_unmatched"] = ok
            print(f"    [B2] Auth replay: {'PASS' if ok else 'FAIL'}")
        if b2_nonvac == "sat" and "model" in b2_results["nonvacuity"]:
            ok = nargo_replay(producer_dir, prog, b2_results["nonvacuity"]["model"],
                              b2_dir / "replay" / "nonvac")
            b2_replays["nonvacuity"] = ok
            print(f"    [B2] Nonvac replay: {'PASS' if ok else 'FAIL'}")

        case_results["B2"] = {"goals": b2_results, "replays": b2_replays}

        # ---- B3: Summary-based modular check --------------------------------
        print("\n  B3: Summary-based (manual specification)")
        b3_dir = RAW / case_name / "B3"
        b3_dir.mkdir(parents=True, exist_ok=True)
        smt_b3 = b3_dir / "smt"
        smt_b3.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        ff, msg_w, perm_w = run_b3_case(case_name, is_repaired, pol, str(smt_b3), TIMEOUT_MS)

        # Auth goal
        b3_auth_status, b3_auth_info = b3_auth_unmatched(ff, pol, msg_w, perm_w, str(smt_b3))
        b3_auth_secs = round(time.time() - t0, 2)
        print(f"    [B3] AUTH-UNMATCHED: {b3_auth_status} ({b3_auth_secs}s)")

        # Nonvacuity (fresh encoder)
        ff2, msg_w2, perm_w2 = run_b3_case(case_name, is_repaired, pol, str(smt_b3), TIMEOUT_MS)
        t0 = time.time()
        b3_nonvac_status, b3_nonvac_info = b3_nonvacuity(ff2, pol, msg_w2, str(smt_b3))
        b3_nonvac_secs = round(time.time() - t0, 2)
        print(f"    [B3] NONVACUITY: {b3_nonvac_status} ({b3_nonvac_secs}s)")

        # Replay
        b3_replays = {}
        if b3_auth_status == "sat":
            model = b3_auth_info.get("model", {})
            ok = nargo_replay(producer_dir, prog, model, b3_dir / "replay" / "auth")
            b3_replays["auth_unmatched"] = ok
            print(f"    [B3] Auth replay: {'PASS' if ok else 'FAIL'}")
        if b3_nonvac_status == "sat":
            model = b3_nonvac_info.get("model", {})
            ok = nargo_replay(producer_dir, prog, model, b3_dir / "replay" / "nonvac")
            b3_replays["nonvacuity"] = ok
            print(f"    [B3] Nonvac replay: {'PASS' if ok else 'FAIL'}")

        case_results["B3"] = {
            "goals": {
                "auth_unmatched": {"status": b3_auth_status, "seconds": b3_auth_secs},
                "nonvacuity": {"status": b3_nonvac_status, "seconds": b3_nonvac_secs},
            },
            "replays": b3_replays,
            "annotation_loc": 25,  # lines of manual summary specification
        }

        all_results[case_name] = case_results

    # Save results
    summary_path = RAW / "baseline_results.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nResults saved: {summary_path}")

    # Print comparison table
    print(f"\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Case':<16} {'Baseline':<8} {'Auth':<8} {'Auth(s)':<8} {'Cov':<8} {'Cov(s)':<8} {'NonVac':<8} {'NonVac(s)':<10} {'Replay'}")
    for case_name in all_results:
        for bl in ["B2", "B3"]:
            g = all_results[case_name][bl]["goals"]
            rp = all_results[case_name][bl]["replays"]
            auth_s = g.get("auth_unmatched", {}).get("status", "n/a")
            auth_t = g.get("auth_unmatched", {}).get("seconds", "n/a")
            cov_s = g.get("cov_unmatched", {}).get("status", "n/a")
            cov_t = g.get("cov_unmatched", {}).get("seconds", "n/a")
            nv_s = g.get("nonvacuity", {}).get("status", "n/a")
            nv_t = g.get("nonvacuity", {}).get("seconds", "n/a")
            rp_str = ",".join(f"{k}:{'ok' if v else 'FAIL'}" for k, v in rp.items()) or "n/a"
            print(f"{case_name:<16} {bl:<8} {auth_s:<8} {auth_t:<8} {cov_s:<8} {cov_t:<8} {nv_s:<8} {nv_t:<10} {rp_str}")


if __name__ == "__main__":
    main()
