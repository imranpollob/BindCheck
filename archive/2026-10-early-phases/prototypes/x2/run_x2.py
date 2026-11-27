"""X2 runner: solve every generic-template derived obligation on the
extracted consumer relation (producer dropped; candidate-level only).

For each variant (pinned, M-SRC) and each unique derived obligation, emit
the D1P-21B extracted-consumer query with the AUTH-1 goal replaced by the
derived goal, run pinned cvc5 once, and record sat/unsat/timeout.
Producer-dropped SAT is an abstract candidate, NOT E2 and NOT a verdict.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "prototypes/d1p21b")
sys.path.insert(0, "prototypes/x2")

from derive_obligations import derive  # noqa: E402
from joint_variant import build_omega, encode_query  # noqa: E402
from bindcheck_d1 import joint_warptoad as manual  # noqa: E402

PAPER = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper")
ARTIFACT = PAPER / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
OUT = Path("results/raw/X-02")
TIMEOUT_S = 120


def bv(n: int) -> str:
    return manual._bv(n)


def main() -> None:
    states = json.loads((PAPER / "results/raw/D1P-19/canonical-states.json").read_text())
    s_src = states["S_SRC"]
    local_roots = [int(b["root"]) for b in s_src["burns"]]
    giga_root = 19712377064642672829441595136074946683621277828620209496774504837737984048981
    s0 = {
        "giga_root_history": [str(giga_root)],
        "local_root_history": [str(r) for r in local_roots],
        "nullifiers": [],
        "total_supply": "10000000000000000000",
        "balances": {},
        "aztec_warptoad_address": "0",
    }
    identities = {"openzeppelin": {"version": "5.6.1",
                    "status": "EXTRACTED identity; versioned manual effect model"}}
    variants = {
        "pinned": PAPER / "results/raw/D1P-18/relation.json",
        "m-src": PAPER / "results/raw/D1P-21B/m-src-relation.json",
    }
    admitted_by_storage = {
        "gigaRootHistory": [giga_root],
        "localRootHistory": local_roots,
        "nullifiers": [],
    }
    results = []
    for name, rel_path in variants.items():
        relation = json.loads(rel_path.read_text())
        derived = derive(relation)
        omega = build_omega(ARTIFACT, goal="AUTH-1", s0=s0, identities=identities,
                            consumer_model="EXTRACTED", relation_path=rel_path,
                            environment={"chain_id": 31337})
        base, cert = encode_query(omega, consumer_model="EXTRACTED", drop_producer=True)
        text = base.decode()
        assert "(assert (or G1 G2 G3 G4 G5))" in text
        for ob in derived["unique_obligations"]:
            admitted = admitted_by_storage[ob["guard_storage"]]
            not_in = "(not (or " + " ".join(
                f"(= pi{ob['guard_word']} {bv(r)})" for r in admitted) + "))" if admitted \
                else "(not (= pi0 pi0))"  # empty admitted set: guard word is never admitted? see note
            if not admitted:
                not_in = "true"  # empty set: every value is outside it
            goal = (f"(assert (and consumer_success "
                    f"(not (= pi{ob['amount_word']} {bv(0)})) {not_in}))")
            query = text.replace("(assert (or G1 G2 G3 G4 G5))", goal)
            qbytes = query.encode()
            qpath = OUT / f"q-{name}-a{ob['amount_word']}-g{ob['guard_word']}.smt2"
            qpath.write_bytes(qbytes)
            t0 = time.time()
            try:
                proc = subprocess.run(["nice", "-n", "19", str(SOLVER), str(qpath)],
                                      capture_output=True, timeout=TIMEOUT_S)
                out = proc.stdout.decode(errors="replace").strip().splitlines()
                observed = out[0] if out else f"exit-{proc.returncode}-no-output"
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                observed, rc = "timeout", None
            wall = time.time() - t0
            results.append({
                "variant": name, "amount_word": ob["amount_word"],
                "amount_symbol": ob["amount_symbol"],
                "guard_storage": ob["guard_storage"], "guard_word": ob["guard_word"],
                "guard_symbol": ob["guard_symbol"], "observed": observed,
                "exit": rc, "wall_s": round(wall, 3),
                "query_sha256": hashlib.sha256(qbytes).hexdigest(),
                "classification": "producer-dropped abstract candidate check; not E2, not a verdict",
            })
            print(results[-1], flush=True)
    (OUT / "solver-results.json").write_text(json.dumps(results, indent=1))
    print(f"total {len(results)} queries")


if __name__ == "__main__":
    main()
