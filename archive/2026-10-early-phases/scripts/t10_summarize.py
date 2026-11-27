#!/usr/bin/env python3
"""T10 summarizer. Reads the runner JSONs and the recorder capture, identifies the agg_final proof among the captured
bb calls by the SHA-256 of the key bb was given (committed dcd5d96 keys), verifies it again independently with the
real pinned bb, runs one tampered-public-input control, and decodes the public inputs using the circuit ABI.
usage: python3 -I t10_summarize.py <results_dir>"""
import hashlib, json, os, re, subprocess, sys

L = sys.argv[1]
ROOT = os.path.abspath(os.path.join(L, "..", "..", ".."))
H = os.path.join(ROOT, "tools/cases/payy-history")
REV = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
BB = os.path.join(ROOT, "tools/bb-3.0.0-manual.20251030/bb")
CAP = os.path.join(ROOT, "build/T10/capture")
OUTD = os.path.join(ROOT, "build/T10/agg_final_new")

def git_cat(path): return subprocess.run(["git", "-C", H, "cat-file", "-p", f"{REV}:{path}"], capture_output=True).stdout
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p):
    try: return json.load(open(p))
    except Exception: return None

summary = {"revision": REV, "build": load(f"{L}/20_cargo_build.json"), "test": load(f"{L}/30_test_agg_final.json")}
keys = {sha(git_cat(f"fixtures/circuits/{c}/key")): c for c in ("utxo", "agg_utxo", "agg_agg", "agg_final")}

calls = []
if os.path.isdir(CAP):
    for name in sorted(os.listdir(CAP)):
        d = os.path.join(CAP, name)
        if not os.path.isdir(d): continue
        rd = lambda f: open(os.path.join(d, f)).read() if os.path.exists(os.path.join(d, f)) else ""
        ru = rd("rusage.txt")
        m = re.search(r"([\d.]+)\s+real", ru); r = re.search(r"(\d+)\s+maximum resident set size", ru)
        key = os.path.join(d, "key")
        calls.append({"call": name, "exit": rd("exit.txt").strip(), "real_s": float(m.group(1)) if m else None,
                      "max_rss_gib": round(int(r.group(1)) / 2**30, 2) if r else None,
                      "circuit_by_key_hash": keys.get(sha(open(key, "rb").read())) if os.path.exists(key) else None})
summary["bb_calls"] = calls
with open(f"{L}/91_bb_calls.tsv", "w") as f:
    f.write("call\texit\treal_s\tmax_rss_gib\tcircuit_by_key_hash\n")
    for c in calls: f.write(f"{c['call']}\t{c['exit']}\t{c['real_s']}\t{c['max_rss_gib']}\t{c['circuit_by_key_hash']}\n")
by = {}
for c in calls:
    k = (c["call"].split("-", 1)[1], c["circuit_by_key_hash"]); by[f"{k[0]}:{k[1]}"] = by.get(f"{k[0]}:{k[1]}", 0) + 1
summary["bb_call_counts"] = by
summary["all_bb_calls_exit_0"] = bool(calls) and all(c["exit"] == "0" for c in calls)

final = [c for c in calls if c["call"].endswith("-prove") and c["circuit_by_key_hash"] == "agg_final" and c["exit"] == "0"]
if not final:
    summary["agg_final_proof"] = "not produced"
    summary["status"] = "NOT COMPLETED" + (f" ({(summary['test'] or summary['build'] or {}).get('outcome')})" if (summary["test"] or summary["build"]) else "")
else:
    fc = final[-1]["call"]; src = os.path.join(CAP, fc, "out")
    os.makedirs(OUTD, exist_ok=True)
    proof = open(os.path.join(src, "proof"), "rb").read(); pi = open(os.path.join(src, "public_inputs"), "rb").read()
    open(f"{OUTD}/proof", "wb").write(proof); open(f"{OUTD}/public_inputs", "wb").write(pi)
    key = git_cat("fixtures/circuits/agg_final/key"); open(f"{OUTD}/agg_final_key_dcd5d96", "wb").write(key)
    open(f"{OUTD}/README.txt", "w").write("NEWLY GENERATED in T10 by the upstream test_agg_final harness at dcd5d96. Not related to fixtures/proofs/agg_agg_final_evm_proof.proof.\n")
    def verify(p_path, i_path):
        r = subprocess.run([BB, "verify", "--scheme", "ultra_honk", "--oracle_hash", "keccak", "-k", f"{OUTD}/agg_final_key_dcd5d96", "-p", p_path, "-i", i_path], capture_output=True, text=True)
        return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout + r.stderr)).strip()[-200:]
    rc, out = verify(f"{OUTD}/proof", f"{OUTD}/public_inputs")
    # control: alter one byte of the first message field; native verification must reject
    bad = bytearray(pi); bad[3 * 32 + 31] ^= 1; open(f"{OUTD}/CONTROL_public_inputs_tampered", "wb").write(bytes(bad))
    rc2, out2 = verify(f"{OUTD}/proof", f"{OUTD}/CONTROL_public_inputs_tampered")
    abi = json.loads(git_cat("fixtures/circuits/agg_final/program.json"))["abi"]["parameters"]
    pub = [(p["name"], p["type"].get("length", 1)) for p in abi if p["visibility"] == "public"]
    fields = [pi[i:i + 32] for i in range(0, len(pi), 32)]
    n = len(fields); msg = fields[3:1003]
    summary["agg_final_proof"] = {
        "call": fc, "artifact_dir": "build/T10/agg_final_new",
        "proof_bytes": len(proof), "proof_sha256": sha(proof), "public_inputs_bytes": len(pi), "public_inputs_sha256": sha(pi),
        "key_used_sha256": sha(key), "oracle_hash": "keccak", "scheme": "ultra_honk",
        "independent_native_verify": {"exit": rc, "tail": out},
        "control_tampered_public_input_native_verify": {"exit": rc2, "tail": out2},
        "abi_public_parameters_in_order": pub, "public_input_field_count": n,
        "decoded": {"old_root": "0x" + fields[0].hex(), "new_root": "0x" + fields[1].hex(), "commit_hash": "0x" + fields[2].hex(),
                    "messages_nonzero_count": sum(1 for f in msg if int.from_bytes(f, "big") != 0), "messages_total": len(msg),
                    "trailing_fields_count": n - 1003, "trailing_fields_nonzero_count": sum(1 for f in fields[1003:] if int.from_bytes(f, "big") != 0),
                    "note": "layout from the ABI: old_root, new_root, commit_hash, messages[1000]. bb writes exactly 1003 public-input fields to the public_inputs file; the key header declares 1019, so the other 16 are not in this file (interpretation: pairing-point inputs carried inside the proof, not established here)"}}
    summary["status"] = "COMPLETED: agg_final proof generated and natively verified" if rc == 0 else "agg_final proof generated but native verification FAILED"
json.dump(summary, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps({k: v for k, v in summary.items() if k != "bb_calls"}, indent=1)[:3500])
