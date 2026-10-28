"""X2 cross-variant check: obligations derived from the PINNED relation's
generic template are applied unchanged to the M-SRC extracted relation.
This is the discovery configuration: derive once, apply to any variant.
Producer dropped throughout; SAT = abstract candidate only."""
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


def main() -> None:
    states = json.loads((PAPER / "results/raw/D1P-19/canonical-states.json").read_text())
    local_roots = [int(b["root"]) for b in states["S_SRC"]["burns"]]
    giga_root = 19712377064642672829441595136074946683621277828620209496774504837737984048981
    s0 = {"giga_root_history": [str(giga_root)],
          "local_root_history": [str(r) for r in local_roots],
          "nullifiers": [], "total_supply": "10000000000000000000",
          "balances": {}, "aztec_warptoad_address": "0"}
    identities = {"openzeppelin": {"version": "5.6.1",
                    "status": "EXTRACTED identity; versioned manual effect model"}}
    admitted = {"gigaRootHistory": [giga_root], "localRootHistory": local_roots,
                "nullifiers": []}
    pinned_rel = json.loads((PAPER / "results/raw/D1P-18/relation.json").read_text())
    derived = derive(pinned_rel)
    # Polarity fix: nullifiers is a must-NOT-be-in (single-use) check.
    # Single-call candidate for it is meaningless; exclude and record why.
    obligations = [o for o in derived["unique_obligations"]
                   if o["guard_storage"] != "nullifiers"]
    excluded = [o for o in derived["unique_obligations"]
                if o["guard_storage"] == "nullifiers"]
    msrc_path = PAPER / "results/raw/D1P-21B/m-src-relation.json"
    omega = build_omega(ARTIFACT, goal="AUTH-1", s0=s0, identities=identities,
                        consumer_model="EXTRACTED", relation_path=msrc_path,
                        environment={"chain_id": 31337})
    base, _ = encode_query(omega, consumer_model="EXTRACTED", drop_producer=True)
    text = base.decode()
    results = []
    for ob in obligations:
        roots = admitted[ob["guard_storage"]]
        not_in = "(not (or " + " ".join(
            f"(= pi{ob['guard_word']} {manual._bv(r)})" for r in roots) + "))"
        goal = (f"(assert (and consumer_success "
                f"(not (= pi{ob['amount_word']} {manual._bv(0)})) {not_in}))")
        qbytes = text.replace("(assert (or G1 G2 G3 G4 G5))", goal).encode()
        qpath = OUT / f"q-cross-msrc-a{ob['amount_word']}-g{ob['guard_word']}.smt2"
        qpath.write_bytes(qbytes)
        t0 = time.time()
        try:
            proc = subprocess.run(["nice", "-n", "19", str(SOLVER), str(qpath)],
                                  capture_output=True, timeout=120)
            out = proc.stdout.decode(errors="replace").strip().splitlines()
            observed = out[0] if out else f"exit-{proc.returncode}"
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            observed, rc = "timeout", None
        row = {"variant": "m-src(cross)", "amount_word": ob["amount_word"],
               "guard_storage": ob["guard_storage"], "guard_word": ob["guard_word"],
               "observed": observed, "exit": rc, "wall_s": round(time.time() - t0, 3),
               "query_sha256": hashlib.sha256(qbytes).hexdigest(),
               "classification": "producer-dropped abstract candidate; not E2, not a verdict"}
        results.append(row)
        print(row, flush=True)
    (OUT / "cross-results.json").write_text(json.dumps(
        {"applied": results,
         "excluded_single_use": excluded,
         "exclusion_reason": "nullifiers admission is must-not-be-in (single-use); "
         "a replay candidate needs a two-transition scope outside this fragment"},
        indent=1))


if __name__ == "__main__":
    main()
