#!/usr/bin/env python3
"""TE04 part 2: compile pinned consumer + real verifiers, run E4 replay on anvil."""
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import xav_run as X  # noqa: E402  (reuse pinned solc build, sh(), REF_NM)

OUT = (ROOT / "build/TE04/e4").resolve()
OUT.mkdir(parents=True, exist_ok=True)
LOGS = ROOT / "results/raw/TE04"
LOGS.mkdir(parents=True, exist_ok=True)
t0 = time.monotonic()

# --- stage sources ---
b = OUT
for d in ("contracts/rollup3", "contracts/noir", "contracts/mocks", "contracts/verifiers",
          "stubs/proxy/utils", "stubs/access"):
    (b / d).mkdir(parents=True, exist_ok=True)
base = X.PAYY_REF / "eth/contracts"
shutil.copy(base / "rollup3/RollupV1.sol", b / "contracts/rollup3/RollupV1.sol")
shutil.copy(base / "noir/IVerifier.sol", b / "contracts/noir/IVerifier.sol")
shutil.copy(ROOT / "benchmarks/binding-mutants/baselines/payy-IUSDC.sol", b / "contracts/IUSDC.sol")
shutil.copy(base / "mocks/MockUSDC.sol", b / "contracts/mocks/MockUSDC.sol")
shutil.copy(ROOT / "benchmarks/binding-mutants/_stubs/payy/proxy/utils/Initializable.sol",
             b / "stubs/proxy/utils/Initializable.sol")
shutil.copy(ROOT / "benchmarks/binding-mutants/_stubs/payy/access/OwnableUpgradeable.sol",
             b / "stubs/access/OwnableUpgradeable.sol")
shutil.copy(ROOT / "scripts/xav/XAVProxy.sol", b / "contracts/XAVProxy.sol")
shutil.copy(ROOT / "build/TE04/verifier-mutant.sol", b / "contracts/verifiers/FinalVerifierMutant.sol")
shutil.copy(ROOT / "build/TE04/verifier-pinned.sol", b / "contracts/verifiers/FinalVerifierPinned.sol")
# bb names both verifier contracts HonkVerifier: rename to avoid the artifact collision.
for f, name in (("FinalVerifierMutant.sol", "HonkVerifierMutant"),
                ("FinalVerifierPinned.sol", "HonkVerifierPinned")):
    pth = b / "contracts/verifiers" / f
    t = pth.read_text()
    assert t.count("contract HonkVerifier ") >= 1
    pth.write_text(t.replace("contract HonkVerifier ", f"contract {name} "))
shutil.copy(ROOT / "scripts/xav/te04_replay.ts", b / "te04_replay.ts")
oz_dst = b / "oz" / "@openzeppelin" / "contracts"
if not oz_dst.exists():
    shutil.copytree(X.REF_NM / "@openzeppelin/contracts", oz_dst, symlinks=False,
                    ignore_dangling_symlinks=True)
if not (b / "node_modules").exists():
    (b / "node_modules").symlink_to(X.REF_NM, target_is_directory=True)

# --- compile: consumer stack with pinned solc 0.8.20; bb-generated verifiers
# need >=0.8.21, so they compile separately with solc 0.8.29 (recorded; the
# verifier is bb's artifact, not Payy's pinned consumer).
SOLC29 = Path("/Users/imranpollob/.svm/0.8.29/solc-0.8.29")
common_settings = {"optimizer": {"enabled": True, "runs": 200}, "viaIR": True,
                   "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}}}
inp20 = {
    "language": "Solidity",
    "sources": {str(p.relative_to(b)): {"content": p.read_text()} for p in
                list((b / "contracts").rglob("*.sol")) + list((b / "stubs").rglob("*.sol"))
                if "verifiers" not in p.parts},
    "settings": {**common_settings,
                 "remappings": ["@openzeppelin/=oz/@openzeppelin/",
                                "@openzeppelin/contracts-upgradeable/=stubs/"]},
}
p, wall = X.sh([str(X.PAYY_SOLC), "--standard-json", "--base-path", str(b),
                "--allow-paths", f"{b},{X.REF_NM},{X.PAYY_REF}/eth/contracts"],
               cwd=b, timeout=1800, log=LOGS / "te04-solc20.log",
               stdin_text=json.dumps(inp20))
print(f"solc20 exit={p.returncode} wall={wall:.1f}s")
o = json.loads(p.stdout)
errs = [e for e in o.get("errors", []) if e.get("severity") == "error"]
assert p.returncode == 0 and not errs, json.dumps(errs)[:800]
arts = {n: {"abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"]}
        for s, cs in o["contracts"].items() for n, c in cs.items()}
inp29 = {
    "language": "Solidity",
    "sources": {str(p.relative_to(b)): {"content": p.read_text()} for p in
                (b / "contracts/verifiers").rglob("*.sol")},
    # Legacy codegen: via-IR hits stack-too-deep on the 2.4k-line verifier.
    # runs=1: runs=200 output (24.9 KB) exceeds EIP-170's 24,576 B contract
    # ceiling; size-optimized build stays deployable on a standard chain.
    "settings": {"optimizer": {"enabled": True, "runs": 1},
                 "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object",
                                                        "evm.bytecode.linkReferences"]}}},
}
p29, wall29 = X.sh([str(SOLC29), "--standard-json", "--base-path", str(b),
                    "--allow-paths", str(b)],
                   cwd=b, timeout=1800, log=LOGS / "te04-solc29.log",
                   stdin_text=json.dumps(inp29))
print(f"solc29 exit={p29.returncode} wall={wall29:.1f}s")
o29 = json.loads(p29.stdout)
errs29 = [e for e in o29.get("errors", []) if e.get("severity") == "error"]
assert p29.returncode == 0 and not errs29, json.dumps(errs29)[:800]
for s, cs in o29["contracts"].items():
    for n, c in cs.items():
        arts[n] = {"abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"]}
for s, cs in o29["contracts"].items():
    for n, c in cs.items():
        bc = c["evm"]["bytecode"]["object"]
        if "__$" in bc:
            idx = bc.index("__$")
            print(f"PLACEHOLDER in {n} ({s}): ...{bc[idx-30:idx+45]}")
            print("  linkRefs:", json.dumps(c["evm"]["bytecode"].get("linkReferences", {}))[:400])
# --- link verifier libraries: deploy libs via cast, patch placeholders ---
link_refs = {}  # (srcfile, libname) -> set of byte offsets in each verifier
verifier_src = {}
for s, cs in o29["contracts"].items():
    for n, c in cs.items():
        if n in ("HonkVerifierMutant", "HonkVerifierPinned"):
            verifier_src[n] = (s, c["evm"]["bytecode"].get("linkReferences", {}))
print("link refs:", {n: [(f, l) for f, libs in v[1].items() for l in libs] for n, v in verifier_src.items()})
port = 18549
anv = subprocess.Popen(["anvil", "--port", str(port), "--silent"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    lib_addr = {}
    for s, cs in o29["contracts"].items():
        for n, c in cs.items():
            if n in ("HonkVerifierMutant", "HonkVerifierPinned"):
                continue
            bc = c["evm"]["bytecode"]["object"]
            if "__$" in bc:
                continue  # resolved below if actually referenced
            # candidate library: deploy if any verifier references it
            for vn, (vsrc, refs) in verifier_src.items():
                if s in refs and n in refs[s]:
                    if (s, n) not in lib_addr:
                        r = subprocess.run(
                            ["cast", "send", "--rpc-url", f"http://127.0.0.1:{port}",
                             "--private-key",
                             "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                             "--create", "0x" + bc, "--json"],
                            capture_output=True, text=True)
                        addr = json.loads(r.stdout)["contractAddress"]
                        lib_addr[(s, n)] = addr
                        print(f"deployed lib {n} ({s}) at {addr}")
    # patch verifier bytecodes
    for vn, (vsrc, refs) in verifier_src.items():
        bc = arts[vn]["bytecode"][2:]
        for s, libs in refs.items():
            for lib, fixups in libs.items():
                addr = lib_addr[(s, lib)].lower().replace("0x", "")
                for fx in fixups:
                    off = fx["start"] * 2
                    assert bc[off:off + 40] == "__$" + bc[off + 3:off + 37] + "$__", (vn, lib, off)
                    bc = bc[:off] + addr + bc[off + 40:]
        assert "__$" not in bc, vn
        arts[vn]["bytecode"] = "0x" + bc
    (b / "artifacts.json").write_text(json.dumps(arts))
    print("verifiers linked")
    names = [n for n, a in arts.items() if a["bytecode"] != "0x"]
    print("compiled:", sorted(names))
    for need in ("RollupV1", "MockUSDC", "XAVProxy", "HonkVerifierMutant",
                   "HonkVerifierPinned"):
        assert need in arts and arts[need]["bytecode"] != "0x", need
    for n, a in arts.items():
        if n not in ("HonkVerifierMutant", "HonkVerifierPinned"):
            assert "__$" not in a["bytecode"], f"unlinked placeholder in {n}"
    (b / "artifacts.json").write_text(json.dumps(arts))

    # --- plan from the final proof ---
    pi = (ROOT / "build/TE04/proof-final/public_inputs").read_bytes()
    assert len(pi) == 1003 * 32, len(pi)
    pubs = ["0x" + pi[i * 32:(i + 1) * 32].hex() for i in range(1003)]
    proof = (ROOT / "build/TE04/proof-final/proof").read_bytes()
    final_vk = "0x" + open(ROOT / "build/TE04/vk-final-mutant/vk_hash", "rb").read().hex()
    # Pinned contrast hash: bb vk_hash of the COMMITTED agg_final program (cheap, CRS cached).
    pin_dir = OUT / "vk-final-pinned"
    pin_dir.mkdir(exist_ok=True)
    subprocess.run(["/Users/imranpollob/Coding/bc/BindCheck/tools/bb-3.0.0-manual.20251030/bb",
                    "write_vk", "--scheme", "ultra_honk", "--oracle_hash", "keccak",
                    "-b", str(X.PAYY_REF / "fixtures/circuits/agg_final/program.json"),
                    "-o", str(pin_dir), "-c", str(ROOT / "build/TE04/crs")], check=True)
    pinned_vk = "0x" + open(pin_dir / "vk_hash", "rb").read().hex()
    assert pinned_vk != final_vk
    print("finalVkHash:", final_vk)
    print("pinnedVkHash:", pinned_vk)
    plan = {"consumer": arts["RollupV1"], "usdc": arts["MockUSDC"],
            "verifiers": {"mutant": arts["HonkVerifierMutant"],
                          "pinned": arts["HonkVerifierPinned"]},
            "proxy": arts["XAVProxy"], "noteKind": pubs[3 + 1],
            "finalVkHash": final_vk, "pinnedVkHash": pinned_vk, "messagesLen": 1000,
            "validatorKey": X.PAYY_VALIDATOR_KEY,
            "proofHex": "0x" + proof.hex(), "publicInputs": pubs,
            "mint": {"hash": pubs[3 + 3], "value": pubs[3 + 2]},
            "watch": "0x000000000000000000000000000000000000dead"}
    (b / "te04-plan.json").write_text(json.dumps(plan))
    print("plan wrote; running replay on the same anvil")
    t1 = time.monotonic()
    p2, wall2 = X.sh(["npx", "--no-install", "tsx", "te04_replay.ts"], cwd=b, timeout=900,
                     log=LOGS / "te04-replay.log",
                     extra_env={"XAV_TE04_PLAN": str((b / "te04-plan.json").resolve()),
                                "XAV_TE04_REPORT": str((b / "te04-report.json").resolve()),
                                "XAV_ANVIL_URL": f"http://127.0.0.1:{port}"})
    print(f"replay exit={p2.returncode} wall={wall2:.1f}s total={time.monotonic() - t0:.1f}s")
    assert p2.returncode == 0, "replay harness failed"
    rep = json.loads((b / "te04-report.json").read_text())
    print(json.dumps(rep["steps"], indent=1)[:1200])
    print("state:", json.dumps(rep["state"], indent=1)[:800])
    print("reverts:", {k: v for k, v in rep.items() if k.startswith("revert")})
finally:
    anv.terminate()
