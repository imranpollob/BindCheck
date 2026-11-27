#!/usr/bin/env python3
"""TE06 part 2: real-verifier contrasts for PY-S01/S02/S03 (TE06 report).

Zero mock components. Same real pinned-keyed proof submitted to mutant and
pinned consumers from identical initial state; only the consumer differs.
Rows: S01 mint-unregistered, S02 mint-double, S03 burn-misdirection.
S04 (dead kind-4) is recorded infeasible (no pinned-producible export).
"""
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xav_run as X  # noqa: E402

OUT = (ROOT / "build/TE06/e4").resolve()
OUT.mkdir(parents=True, exist_ok=True)
LOGS = ROOT / "results/raw/TE06"
LOGS.mkdir(parents=True, exist_ok=True)

te04plan = json.loads((ROOT / "build/TE04/e4/te04-plan.json").read_text())
PINNED_VK = te04plan["pinnedVkHash"]
TE04_ARTS = json.loads((ROOT / "build/TE04/e4/artifacts.json").read_text())
LINK = json.loads((ROOT / "build/TE06/e4/artifacts-link.json").read_text())
# Sanity: freshly linked pinned verifier logic matches TE04's build
# (same sources); only linked library addresses may differ by link order.
assert LINK["verifiers"]["HonkVerifierPinned"]["abi"] == TE04_ARTS["HonkVerifierPinned"]["abi"]


def load_block(att):
    pi = (ROOT / f"build/TE06/proof-{att}/public_inputs").read_bytes()
    assert len(pi) == 1003 * 32, len(pi)
    pubs = ["0x" + pi[i * 32:(i + 1) * 32].hex() for i in range(1003)]
    proof = (ROOT / f"build/TE06/proof-{att}/proof").read_bytes()
    return pubs, "0x" + proof.hex()


def base_plan(mutant, block, label):
    pubs, proof_hex = block
    marts = json.loads((ROOT / f"results/raw/X-AV/v11/payy-build/{mutant}/artifacts.json").read_text())
    return {
        "consumerMutant": marts["RollupV1"],
        "consumerPinned": TE04_ARTS["RollupV1"],
        "usdc": TE04_ARTS["MockUSDC"],
        "libraries": [{"name": l["name"], "address": l["address"],
                       "bytecode": l["bytecode"]} for l in LINK["libraries"]],
        "verifier": LINK["verifiers"]["HonkVerifierPinned"],
        "proxy": TE04_ARTS["XAVProxy"],
        "noteKind": pubs[4], "finalVkHash": PINNED_VK, "messagesLen": 1000,
        "validatorKey": X.PAYY_VALIDATOR_KEY,
        "proofHex": proof_hex, "publicInputs": pubs, "label": label,
    }


def run_row(name, plan, port):
    (OUT / "node_modules").unlink(missing_ok=True)
    if not (OUT / "node_modules").exists():
        (OUT / "node_modules").symlink_to(X.REF_NM, target_is_directory=True)
    shutil.copy(ROOT / "scripts/xav/te06_replay.ts", OUT / "te06_replay.ts")
    (OUT / f"te06-{name}-plan.json").write_text(json.dumps(plan))
    anv = subprocess.Popen(["anvil", "--port", str(port), "--silent"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        p, wall = X.sh(["npx", "--no-install", "tsx", "te06_replay.ts"], cwd=OUT,
                       timeout=900, log=LOGS / f"te06-{name}-replay.log",
                       extra_env={"XAV_TE06_PLAN": str((OUT / f"te06-{name}-plan.json").resolve()),
                                  "XAV_TE06_REPORT": str((OUT / f"te06-{name}-report.json").resolve()),
                                  "XAV_ANVIL_URL": f"http://127.0.0.1:{port}"})
        print(f"{name}: replay exit={p.returncode} wall={wall:.1f}s")
        assert p.returncode == 0, f"{name} harness failed"
        rep = json.loads((OUT / f"te06-{name}-report.json").read_text())
        print(json.dumps(rep["steps"], indent=0)[:900])
        print("state:", json.dumps(rep["state"], indent=0)[:900])
        print("reverts:", {k: v for k, v in rep.items() if k.startswith("revert")})
        return rep
    finally:
        anv.terminate()


def main() -> int:
    control = load_block("control")  # honest mint @0-3, zeros after
    burn = load_block("tail")        # honest mint @0-3, burn @4-8
    ctl_hash, ctl_value = control[0][6], control[0][5]
    # S03 burn record: messages[4..8] = [3, note_kind, 7, 0x67932, 0xdead].
    # The mutant binds the payout to messages[5] (note kind word); the
    # pinned consumer pays messages[8] (recipient). Addresses are the
    # low 20 bytes of each word.
    notekind_addr = "0x" + burn[0][8][-40:]
    recipient = "0x" + burn[0][11][-40:]

    # S01: unregistered mint settles on mutant, reverts on pinned.
    plan = base_plan("PY-S01", control, "TE06-S01")
    plan["submits"] = [{"side": "mutant", "height": 1, "tag": "mutant_unregistered"},
                       {"side": "pinned", "height": 1, "tag": "pinned_unregistered"}]
    plan["mintHash"] = ctl_hash
    run_row("S01", plan, 18561)

    # S02: registered mint settles twice on mutant; second reverts on pinned.
    plan = base_plan("PY-S02", control, "TE06-S02")
    plan["register"] = {"hash": ctl_hash, "value": ctl_value}
    plan["submits"] = [{"side": "mutant", "height": 1, "tag": "mutant_first"},
                       {"side": "pinned", "height": 1, "tag": "pinned_first"},
                       {"side": "mutant", "height": 2, "tag": "mutant_second"},
                       {"side": "pinned", "height": 2, "tag": "pinned_second"}]
    plan["mintHash"] = ctl_hash
    run_row("S02", plan, 18562)

    # S03: burn settles on both; payout destination differs.
    plan = base_plan("PY-S03", burn, "TE06-S03")
    plan["fund"] = {"hash": ctl_hash, "value": ctl_value}
    plan["submits"] = [{"side": "mutant", "height": 1, "tag": "mutant_burn"},
                       {"side": "pinned", "height": 1, "tag": "pinned_burn"}]
    plan["watch"] = [notekind_addr, recipient]
    run_row("S03", plan, 18563)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
