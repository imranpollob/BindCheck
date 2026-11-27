#!/usr/bin/env python3
"""TE05 part 2: replay the ACTIVE-prefix mutant block on anvil.

Reuses TE04's compiled artifacts (identical consumer + identical final VK).
Registers the CONTROL honest mint (0x1e05../100), NOT the attacker words:
the active-prefix attacker mint (0x..abababab) is unregistered by design,
so settlement must revert at consumer policy if the proof verifies.
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

OUT = (ROOT / "build/TE05/e4").resolve()
OUT.mkdir(parents=True, exist_ok=True)
LOGS = ROOT / "results/raw/TE05"
LOGS.mkdir(parents=True, exist_ok=True)
t0 = time.monotonic()

arts = json.loads((ROOT / "build/TE04/e4/artifacts.json").read_text())
for need in ("RollupV1", "MockUSDC", "XAVProxy", "HonkVerifierMutant",
             "HonkVerifierPinned"):
    assert need in arts and arts[need]["bytecode"] != "0x", need
shutil.copy(ROOT / "scripts/xav/te05_replay.ts", OUT / "te05_replay.ts")

te04plan = json.loads((ROOT / "build/TE04/e4/te04-plan.json").read_text())
pi = (ROOT / "build/TE05/proof-final/public_inputs").read_bytes()
assert len(pi) == 1003 * 32, len(pi)
pubs = ["0x" + pi[i * 32:(i + 1) * 32].hex() for i in range(1003)]
assert pubs[3 + 3].endswith("abababab"), pubs[3 + 3]  # attacker hash @ msg3
proof = (ROOT / "build/TE05/proof-final/proof").read_bytes()
ctl = json.loads((ROOT / "results/raw/TC02/mutant2/harness.json").read_text())
ctl_hash = ctl["active_words"][3]
assert ctl_hash.startswith("0x1e05"), ctl_hash
plan = {"consumer": arts["RollupV1"], "usdc": arts["MockUSDC"],
        "verifiers": {"mutant": arts["HonkVerifierMutant"],
                      "pinned": arts["HonkVerifierPinned"]},
        "proxy": arts["XAVProxy"], "noteKind": pubs[3 + 1],
        "finalVkHash": te04plan["finalVkHash"],
        "pinnedVkHash": te04plan["pinnedVkHash"], "messagesLen": 1000,
        "validatorKey": X.PAYY_VALIDATOR_KEY,
        "proofHex": "0x" + proof.hex(), "publicInputs": pubs,
        "mint": {"hash": ctl_hash, "value": pubs[3 + 2]},
        "watch": pubs[3 + 3]}
(OUT / "te05-plan.json").write_text(json.dumps(plan))
print("control mint:", plan["mint"], "watch:", plan["watch"])

port = 18559
anv = subprocess.Popen(["anvil", "--port", str(port), "--silent"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    if not (OUT / "node_modules").exists():
        (OUT / "node_modules").symlink_to(X.REF_NM, target_is_directory=True)
    p2, wall2 = X.sh(["npx", "--no-install", "tsx", "te05_replay.ts"], cwd=OUT,
                     timeout=900, log=LOGS / "te05-replay.log",
                     extra_env={"XAV_TE04_PLAN": str((OUT / "te05-plan.json").resolve()),
                                "XAV_TE04_REPORT": str((OUT / "te05-report.json").resolve()),
                                "XAV_ANVIL_URL": f"http://127.0.0.1:{port}"})
    print(f"replay exit={p2.returncode} wall={wall2:.1f}s total={time.monotonic() - t0:.1f}s")
    assert p2.returncode == 0, "replay harness failed"
    rep = json.loads((OUT / "te05-report.json").read_text())
    print(json.dumps(rep["steps"], indent=1)[:1200])
    print("state:", json.dumps(rep["state"], indent=1)[:800])
    print("reverts:", {k: v for k, v in rep.items() if k.startswith("revert")})
finally:
    anv.terminate()
