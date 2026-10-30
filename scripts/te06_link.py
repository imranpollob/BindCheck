#!/usr/bin/env python3
"""TE06 link step: recompile the bb-generated verifiers and link their
libraries deterministically.

Background: the TE04 artifacts carry verifiers linked to Oct-29 library
addresses. Library addresses are deterministic per fresh chain (same
deployer, same nonce order), but TE06 replays never deployed the
libraries, so every proof-verification call delegatecalled into empty
accounts and reverted dataless. This script recompiles the identical
verifier sources with solc 0.8.29 (same settings as TE04) and links
freshly in SORTED (file, name) order — self-consistent for TE06, logic
unchanged. Replays must deploy `libraries` first, in listed order.
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

B = (ROOT / "build/TE06/e4").resolve()
B.mkdir(parents=True, exist_ok=True)
LOGS = ROOT / "results/raw/TE06"
LOGS.mkdir(parents=True, exist_ok=True)
SOLC29 = Path("/Users/imranpollob/.svm/0.8.29/solc-0.8.29")

shutil.copytree(ROOT / "build/TE04/e4/contracts/verifiers",
                B / "vsrc", dirs_exist_ok=True)
inp29 = {
    "language": "Solidity",
    "sources": {str(p.relative_to(B)): {"content": p.read_text()} for p in
                (B / "vsrc").rglob("*.sol")},
    "settings": {"optimizer": {"enabled": True, "runs": 1},
                 "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object",
                                                "evm.bytecode.linkReferences"]}}},
}
p29, wall29 = X.sh([str(SOLC29), "--standard-json", "--base-path", str(B),
                    "--allow-paths", str(B)],
                   cwd=B, timeout=1800, log=LOGS / "te06-solc29.log",
                   stdin_text=json.dumps(inp29))
print(f"solc29 exit={p29.returncode} wall={wall29:.1f}s")
o29 = json.loads(p29.stdout)
errs29 = [e for e in o29.get("errors", []) if e.get("severity") == "error"]
assert p29.returncode == 0 and not errs29, json.dumps(errs29)[:800]

verifiers = {}
wanted_libs = {}  # (srcfile, libname) -> object
for s, cs in o29["contracts"].items():
    for n, c in cs.items():
        obj = c["evm"]["bytecode"]["object"]
        if n in ("HonkVerifierMutant", "HonkVerifierPinned"):
            verifiers[n] = {"abi": c["abi"], "bytecode": obj,
                            "refs": c["evm"]["bytecode"].get("linkReferences", {})}
        else:
            for vn, v in verifiers.items():
                pass
            wanted_libs[(s, n)] = obj
print("verifiers:", sorted(verifiers))
# collect libs actually referenced, in sorted order
libs = []
for vn in sorted(verifiers):
    for s in sorted(verifiers[vn]["refs"]):
        for lib in sorted(verifiers[vn]["refs"][s]):
            if (s, lib) not in [(a, b) for a, b, _ in libs]:
                libs.append((s, lib, wanted_libs[(s, lib)]))
print("libs in link order:", [(a, b) for a, b, _ in libs])
for _, _, obj in libs:
    assert "__$" not in obj, "nested library placeholder (not handled)"

port = 18571
anv = subprocess.Popen(["anvil", "--port", str(port), "--silent"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    linked_libs = []
    for s, lib, obj in libs:
        r = subprocess.run(
            ["cast", "send", "--rpc-url", f"http://127.0.0.1:{port}",
             "--private-key",
             "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
             "--create", "0x" + obj, "--json"],
            capture_output=True, text=True)
        addr = json.loads(r.stdout)["contractAddress"]
        print(f"deployed lib {lib} ({s}) at {addr}")
        linked_libs.append({"file": s, "name": lib, "address": addr,
                            "bytecode": "0x" + obj})
    # patch verifier bytecodes (compute offsets from linkReferences)
    out_verifiers = {}
    for vn in sorted(verifiers):
        bc = verifiers[vn]["bytecode"]
        for s, libmap in verifiers[vn]["refs"].items():
            for lib, fixups in libmap.items():
                addr = next(x["address"] for x in linked_libs
                            if x["file"] == s and x["name"] == lib)
                addr = addr.lower().replace("0x", "")
                for fx in fixups:
                    off = fx["start"] * 2
                    assert bc[off:off + 40].startswith("__$"), (vn, lib, off)
                    bc = bc[:off] + addr + bc[off + 40:]
        assert "__$" not in bc, vn
        out_verifiers[vn] = {"abi": verifiers[vn]["abi"], "bytecode": "0x" + bc}
    (B / "artifacts-link.json").write_text(json.dumps(
        {"libraries": linked_libs, "verifiers": out_verifiers}, indent=0))
    print("wrote", B / "artifacts-link.json")
finally:
    anv.terminate()
