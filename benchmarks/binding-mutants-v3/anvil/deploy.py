"""Post-hoc Mythril arm (NOT pre-registered): deploy one B3 tree's analysis target(s) on a LOCAL Anvil node.

Usage: python3 deploy.py TREE_ID  ->  prints JSON {"part": address, ...} for the analysis parts.
Rules (identical for clean and mutant trees):
  * Anvil is reset first (anvil_reset), so deployment order and addresses are deterministic.
  * Runtime/creation code comes from the tree's own forge artifacts (out/), never recompiled,
    except the dark withdraw Verifier.sol, which forge does not build: it is compiled with solc 0.8.30
    --optimize --optimize-runs 200 (the frozen Mythril setting) into results/raw/B3/anvil-1/solc/<ID>/.
  * Consumer contracts are wired to the permissive stub AcceptAll for verifiers, hashers and oracles
    (and MockUSDG for dark's 6-decimal token). Verifier contracts are deployed and analysed standalone.
Anvil must run as: anvil --host 127.0.0.1 --port 8545 --chain-id 31337 --disable-code-size-limit --gas-limit 100000000
Local only: http://127.0.0.1:8545, Anvil's well-known test key #0. No other network.
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent; B3 = HERE.parent; R = B3.parent.parent / "results/raw/B3"
RPC = "http://127.0.0.1:8545"
KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # anvil default account #0 (public test key)
ME = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
STUB = "0x6080604052348015600e575f5ffd5b50604380601a5f395ff3fe608060405260015f5260205ff3fea26469706673582212206ba34cd3fd8c43eac0d090aeb3f22853652341e5f99a74edadcbdd462b0d4aa764736f6c634300081c0033"  # AcceptAll.sol, solc 0.8.28 --bin
SVM = pathlib.Path.home() / ".local/share/svm"

def sh(*a): return subprocess.run(a, check=True, capture_output=True, text=True).stdout.strip()

def tree(tid):
    h = {"ZK": "zkerc20", "DK": "dark", "DV": "davinci", "KK": "kakushi", "XC": "xchain"}.get(tid[:2]) or tid.split("-", 1)[1]
    if tid == "CLEAN-kakushi": return h, R / "run-0-clean-c/trees" / tid
    if tid.startswith("CLEAN-"): return h, R / "run-0-clean-b/trees" / tid
    if tid == "XC-S07": return h, R / "run-1-xchain-s07/trees" / tid
    return h, R / f"run-1-{h}/trees" / tid

def art(root, sol, name):
    d = json.loads((root / "out" / sol / f"{name}.json").read_text())
    assert not d["bytecode"].get("linkReferences"), f"{name} needs linking"
    return d["bytecode"]["object"]

def create(code, sig=None, *args):
    data = code if code.startswith("0x") else "0x" + code
    if sig: data += sh("cast", "abi-encode", sig, *args)[2:]
    out = json.loads(sh("cast", "send", "--private-key", KEY, "--rpc-url", RPC, "--gas-limit", "90000000", "--json", "--create", data))
    assert out["status"] in ("0x1", 1), out
    return out["contractAddress"]

def link(od, name, src, done):
    """Deploy solc-linked libraries depth-first (placeholder __$keccak(src:Lib)[:34]$__) and return linked bytecode."""
    import re
    code = (od / f"{name}.bin").read_text().strip().splitlines()[0]  # drop solc "// $..$ -> lib" comment lines
    for ph in sorted(set(re.findall(r"__\$([0-9a-f]{34})\$__", code))):
        lib = next(f.stem for f in od.glob("*.bin") if sh("cast", "keccak", f"{src}:{f.stem}")[2:36] == ph)
        if lib not in done: done[lib] = create(link(od, lib, src, done))
        code = code.replace(f"__${ph}$__", done[lib][2:].lower())
    return code

def ids(n): return [sh("cast", "keccak", f"b3-image-{i}") for i in range(n)]

def deploy(tid):
    sh("cast", "rpc", "anvil_reset", "--rpc-url", RPC)
    h, t = tree(tid); parts = {}
    if h == "xchain":
        root = t / "smart-contracts"; s = create(STUB); im = ids(6)
        a = create(art(root, "RiscZeroAdapter.sol", "RiscZeroAdapter"), "constructor(address,bytes32[])", s, "[" + ",".join(im) + "]")
        b = create(art(root, "SnarkAdapter.sol", "SnarkAdapter"), "constructor(address)", s)
        f = create(art(root, "WrappedTokenFactory.sol", "WrappedTokenFactory"), "constructor(uint64)", "86400")
        c = create(art(root, "Connector.sol", "Connector"), "constructor(address,address,uint64,bytes32[6],address)", a, b, "3600", "[" + ",".join(im) + "]", f)
        parts = {"": c, "adapter": a}
    elif h == "kakushi":
        root = t / "packages/contracts"; s = create(STUB)
        parts = {"": create(art(root, "KakushiPool.sol", "KakushiPool"), "constructor(address,address,uint256,address)", s, "0x0000000000000000000000000000000000000000", "1000000000000000000", s)}
    elif h == "davinci":
        root = t / "solidity"; s = create(STUB)
        parts = {"": create(art(root, "CouncilManager.sol", "CouncilManager"), "constructor(address,address,bytes32)", s, s, sh("cast", "keccak", "b3-release")),
                 "dealverifier": create(art(root, "DealVerifier.sol", "DealVerifier"))}
    elif h == "dark":
        root = t / "contracts"; s1 = create(STUB); s2 = create(STUB); s3 = create(STUB)
        usdg = create(art(root, "MockUSDG.sol", "MockUSDG"))
        reg = create(art(root, "DarkKeyRegistry.sol", "DarkKeyRegistry"), "constructor(address)", s3)
        caps = "(1000000,2500000000,10000000000,1,2500000000,250000000000)"
        parts[""] = create(art(root, "DarkVault.sol", "DarkVault"), "constructor(address,address,address,address,address,address,(uint64,uint64,uint64,uint64,uint64,uint64))",
                           usdg, reg, s1, s2, ME, ME, caps)
        od = R / "anvil-1/solc" / tid; od.mkdir(parents=True, exist_ok=True)
        vdir = t / "circuits/verifiers/withdraw"
        subprocess.run([str(SVM / "0.8.30/solc-0.8.30"), "--optimize", "--optimize-runs", "200", "--bin", "--overwrite", "-o", str(od), "Verifier.sol"], cwd=vdir, check=True, capture_output=True)
        parts["verifier"] = create(link(od, "HonkVerifier", "Verifier.sol", {}))
    elif h == "zkerc20":
        root = t; s = create(STUB)
        node = create(art(root, "Node.sol", "Node"), "constructor(address,address,address,address)", ME, s, s, s)
        zk = sh("cast", "call", node, "zkerc20()(address)", "--rpc-url", RPC)
        parts = {"": node, "zkerc20": zk, "verifier": sh("cast", "call", zk, "verifier()(address)", "--rpc-url", RPC)}
    return parts

if __name__ == "__main__":
    print(json.dumps(deploy(sys.argv[1])))
