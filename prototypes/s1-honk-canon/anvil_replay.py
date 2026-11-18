#!/usr/bin/env python3
"""S1 Anvil replay: deploy each generated verifier on an owned local Anvil and
replay its honest proof with public input 0 encoded as x, x + r and x + k*r.

Records observed outcomes only (return value, revert data, gas, code size).
No expected verdict is encoded here.

Usage: anvil_replay.py <run_dir> <rpc_url>
Scans <run_dir>/honk/*/ (HonkVerifier.sol, proof, public_inputs) and
<run_dir>/snarkjs/*/ (Verifier.sol, calldata.txt). Writes
<run_dir>/anvil/results.json and results.tsv.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

R = 21888242871839275222246405745257275088548364400416034343698204186575808495617
# Anvil's default, publicly known test account 0 (synthetic, local chain only).
KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
GAS_LIMIT = "30000000"
EIP170 = 24576
FOUNDRY_TOML = """[profile.default]
src = "src"
out = "out"
libs = []
solc_version = "0.8.29"
evm_version = "cancun"
optimizer = true
optimizer_runs = 1
"""
SELECTORS = {}  # filled lazily: 4-byte selector -> error name


def run(cmd, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd[:3]} exit {p.returncode}: {p.stderr[-800:]}")
    return p


def selector(sig):
    return run(["cast", "sig", sig]).stdout.strip()


def known_errors(sol_text):
    names = set(re.findall(r"error\s+(\w+)\(\)", sol_text)) | {"ValueGeFieldOrder", "PublicInputsLengthWrong"}
    return {selector(f"{n}()"): n for n in names}


def variants(run_dir):
    out = []
    for d in sorted((run_dir / "honk").glob("*/")):
        if (d / "HonkVerifier.sol").exists() and (d / "proof").exists():
            pi = (d / "public_inputs").read_bytes()
            words = ["0x" + pi[i:i + 32].hex() for i in range(0, len(pi), 32)]
            out.append({"id": d.name, "kind": "honk", "sol": d / "HonkVerifier.sol", "contract": "HonkVerifier",
                        "sig": "verify(bytes,bytes32[])(bool)", "proof": "0x" + (d / "proof").read_bytes().hex(),
                        "pub": words})
    for d in sorted((run_dir / "snarkjs").glob("*/")):
        if not (d / "calldata.txt").exists():
            continue
        toks = re.findall(r"0x[0-9a-fA-F]+", (d / "calldata.txt").read_text())
        name = d.name
        contract = {"groth16": "Groth16Verifier", "plonk": "PlonkVerifier", "fflonk": "FflonkVerifier"}[name]
        if name == "groth16":
            proof, pub = toks[:8], toks[8:]
            sig = f"verifyProof(uint256[2],uint256[2][2],uint256[2],uint256[{len(pub)}])(bool)"
        elif name == "plonk":
            proof, pub = toks[:24], toks[24:]
            sig = f"verifyProof(uint256[24],uint256[{len(pub)}])(bool)"
        else:
            proof, pub = toks[:24], toks[24:]
            sig = f"verifyProof(bytes32[24],uint256[{len(pub)}])(bool)"
        out.append({"id": f"snarkjs_{name}", "kind": name, "sol": d / "Verifier.sol", "contract": contract,
                    "sig": sig, "proof": proof, "pub": pub})
    return out


def args_for(v, pub):
    if v["kind"] == "honk":
        return [v["proof"], "[" + ",".join(pub) + "]"]
    p = v["proof"]
    pubs = "[" + ",".join(pub) + "]"
    if v["kind"] == "groth16":
        return [f"[{p[0]},{p[1]}]", f"[[{p[2]},{p[3]}],[{p[4]},{p[5]}]]", f"[{p[6]},{p[7]}]", pubs]
    if v["kind"] == "fflonk":
        p = ["0x" + int(t, 16).to_bytes(32, "big").hex() for t in p]
    return ["[" + ",".join(p) + "]", pubs]


def compile_deploy(v, work, rpc):
    proj = work / v["id"]
    if proj.exists():
        shutil.rmtree(proj)
    (proj / "src").mkdir(parents=True)
    shutil.copy(v["sol"], proj / "src" / "V.sol")
    (proj / "foundry.toml").write_text(FOUNDRY_TOML)
    b = run(["forge", "build", "--root", str(proj)], check=False)
    (proj / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode != 0:
        return None, f"build exit {b.returncode}"
    deployed = {}
    linked = []

    def deploy(name):
        # Deploy an artifact, first deploying and linking any external libraries it references.
        if name in deployed:
            return deployed[name]
        art = json.loads((proj / "out" / "V.sol" / f"{name}.json").read_text())
        hexcode = art["bytecode"]["object"].removeprefix("0x")
        for _src, libs in art["bytecode"].get("linkReferences", {}).items():
            for lib, refs in libs.items():
                lib_addr = deploy(lib).removeprefix("0x").lower()
                linked.append(lib)
                for ref in refs:
                    s = ref["start"] * 2
                    hexcode = hexcode[:s] + lib_addr + hexcode[s + ref["length"] * 2:]
        assert "__$" not in hexcode, f"unresolved placeholder in {name}"
        d = run(["cast", "send", "--rpc-url", rpc, "--private-key", KEY, "--json", "--create", "0x" + hexcode])
        deployed[name] = json.loads(d.stdout)["contractAddress"]
        return deployed[name]

    try:
        addr = deploy(v["contract"])
    except (RuntimeError, AssertionError) as e:
        return None, f"deploy failed: {str(e)[-300:]}"
    v["linked_libraries"] = sorted(set(linked))
    return addr, None


def observe(v, addr, pub, rpc, errs):
    sig = v["sig"]
    a = args_for(v, pub)
    c = run(["cast", "call", "--rpc-url", rpc, addr, sig, *a], check=False)
    rec = {"call_exit": c.returncode}
    if c.returncode == 0:
        rec["returned"] = c.stdout.strip()
    else:
        m = re.search(r"data: \"?(0x[0-9a-fA-F]*)", c.stderr)
        data = m.group(1) if m else None
        rec["revert_data"] = data
        rec["revert_error"] = errs.get(data[:10]) if data and len(data) >= 10 else None
        rec["stderr_tail"] = c.stderr.strip()[-200:]
    s = run(["cast", "send", "--rpc-url", rpc, "--private-key", KEY, "--json", "--gas-limit", GAS_LIMIT,
             addr, sig.split(")(")[0] + ")", *a], check=False)
    if s.returncode == 0:
        r = json.loads(s.stdout)
        rec["tx_status"] = int(r["status"], 16)
        rec["gas_used"] = int(r["gasUsed"], 16)
    else:
        rec["tx_error"] = s.stderr.strip()[-200:]
    return rec


def main():
    run_dir, rpc = Path(sys.argv[1]), sys.argv[2]
    chain = run(["cast", "chain-id", "--rpc-url", rpc]).stdout.strip()
    assert chain == "31337", f"refusing: chain id {chain} is not local Anvil"
    assert re.match(r"http://(127\.0\.0\.1|localhost):\d+$", rpc), "refusing non-local RPC"
    work = run_dir / "anvil"
    work.mkdir(exist_ok=True)
    results = []
    for v in variants(run_dir):
        sol_text = Path(v["sol"]).read_text()
        errs = known_errors(sol_text)
        x = int(v["pub"][0], 16)
        k = (2**256 - 1 - x) // R
        rec = {"id": v["id"], "sol_sha256": run(["sha256sum", str(v["sol"])]).stdout.split()[0], "n": x, "max_k": k}
        addr, err = compile_deploy(v, work, rpc)
        if err:
            rec["error"] = err
            results.append(rec)
            print(v["id"], "ERROR", err, flush=True)
            continue
        size = (len(run(["cast", "code", "--rpc-url", rpc, addr]).stdout.strip()) - 2) // 2
        rec.update(address=addr, linked_libraries=v.get("linked_libraries", []), runtime_size=size, above_eip170=size > EIP170, cases={})
        for name, value in [("honest", x), ("plus_r", x + R), ("max_k", x + k * R)]:
            pub = ["0x" + value.to_bytes(32, "big").hex()] + v["pub"][1:]
            rec["cases"][name] = {"input": pub[0], **observe(v, addr, pub, rpc, errs)}
        results.append(rec)
        print(v["id"], {n: c.get("returned", c.get("revert_error") or c.get("revert_data")) for n, c in rec["cases"].items()}, flush=True)
    (work / "results.json").write_text(json.dumps(results, indent=2))
    with (work / "results.tsv").open("w") as f:
        f.write("id\tcase\tinput\tcall_result\trevert_error\ttx_status\tgas_used\truntime_size\n")
        for rec in results:
            for name, c in rec.get("cases", {}).items():
                f.write("\t".join(str(x) for x in [rec["id"], name, c["input"], c.get("returned", "REVERT"),
                                                     c.get("revert_error") or c.get("revert_data") or "",
                                                     c.get("tx_status", ""), c.get("gas_used", ""),
                                                     rec["runtime_size"]]) + "\n")
            if "error" in rec:
                f.write(f"{rec['id']}\t-\t-\tERROR: {rec['error']}\t\t\t\t\n")


if __name__ == "__main__":
    main()
