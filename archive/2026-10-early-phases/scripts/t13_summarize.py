#!/usr/bin/env python3
"""T13 proof summarizer: identifies the agg_final proof among the captured bb calls by the key hash bb received (committed dcd5d96 keys),
copies it out, verifies it again with the real pinned bb and the committed key, runs one tampered-public-input control, and decodes the single
mint message. usage: python3 -I t13_summarize.py <results_dir>"""
import hashlib, json, os, re, subprocess, sys

L = sys.argv[1]
ROOT = os.path.abspath(os.path.join(L, "..", "..", ".."))
H = os.path.join(ROOT, "tools/cases/payy-history")
REV = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
BB = os.path.join(ROOT, "tools/bb-3.0.0-manual.20251030/bb")
CAP = os.path.join(ROOT, "build/T13/capture")
OUTD = os.path.join(L, "agg_final_mint")
CONTRACT_INITIAL_ROOT = "0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff"  # RollupV1.initialize hard-coded

git_cat = lambda p: subprocess.run(["git", "-C", H, "cat-file", "-p", f"{REV}:{p}"], capture_output=True).stdout
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.load(open(p)) if os.path.exists(p) else None

keys = {sha(git_cat(f"fixtures/circuits/{c}/key")): c for c in ("utxo", "agg_utxo", "agg_agg", "agg_final")}
calls = []
for name in sorted(os.listdir(CAP)) if os.path.isdir(CAP) else []:
    d = os.path.join(CAP, name)
    rd = lambda f: open(os.path.join(d, f)).read() if os.path.exists(os.path.join(d, f)) else ""
    ru = rd("rusage.txt"); m = re.search(r"([\d.]+)\s+real", ru); r = re.search(r"(\d+)\s+maximum resident set size", ru)
    kp = os.path.join(d, "key")
    calls.append({"call": name, "exit": rd("exit.txt").strip(), "real_s": float(m.group(1)) if m else None,
                  "max_rss_gib": round(int(r.group(1)) / 2**30, 2) if r else None,
                  "circuit": keys.get(sha(open(kp, "rb").read())) if os.path.exists(kp) else None})
summary = {"revision": REV, "harness_run": load(f"{L}/30_harness_run.json"), "build": load(f"{L}/20_cargo_build.json"), "bb_calls": calls,
           "all_bb_calls_exit_0": bool(calls) and all(c["exit"] == "0" for c in calls)}
counts = {}
for c in calls:
    k = f"{c['call'].split('-', 1)[1]}:{c['circuit']}"; counts[k] = counts.get(k, 0) + 1
summary["bb_call_counts"] = counts

final = [c for c in calls if c["call"].endswith("-prove") and c["circuit"] == "agg_final" and c["exit"] == "0"]
if not final:
    summary["status"] = "NOT COMPLETED"
else:
    fc = final[-1]["call"]; src = os.path.join(CAP, fc, "out"); os.makedirs(OUTD, exist_ok=True)
    proof = open(os.path.join(src, "proof"), "rb").read(); pi = open(os.path.join(src, "public_inputs"), "rb").read()
    key = git_cat("fixtures/circuits/agg_final/key")
    for n, b in (("proof", proof), ("public_inputs", pi), ("agg_final_key_dcd5d96", key)): open(f"{OUTD}/{n}", "wb").write(b)
    open(f"{OUTD}/README.txt", "w").write("NEWLY GENERATED in T13 (single mint message) by the harness payy-harness/t13_mint.rs on the pinned bb. Not related to T10's artifacts or to any committed upstream fixture.\n")
    def verify(p, i):
        r = subprocess.run([BB, "verify", "--scheme", "ultra_honk", "--oracle_hash", "keccak", "-k", f"{OUTD}/agg_final_key_dcd5d96", "-p", p, "-i", i], capture_output=True, text=True)
        return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr).strip()[-160:]
    rc, out = verify(f"{OUTD}/proof", f"{OUTD}/public_inputs")
    bad = bytearray(pi); bad[5 * 32 + 31] ^= 1; open(f"{OUTD}/CONTROL_public_inputs_value_tampered", "wb").write(bytes(bad))   # index 5 = messages[2] = mint value
    rc2, out2 = verify(f"{OUTD}/proof", f"{OUTD}/CONTROL_public_inputs_value_tampered")
    f = [pi[i:i + 32] for i in range(0, len(pi), 32)]; hx = lambda b: "0x" + b.hex(); iv = lambda b: int.from_bytes(b, "big")
    msgs = f[3:1003]
    summary["agg_final_proof"] = {
        "call": fc, "dir": "results/raw/T13/agg_final_mint", "proof_bytes": len(proof), "proof_sha256": sha(proof),
        "public_inputs_bytes": len(pi), "public_inputs_fields": len(f), "public_inputs_sha256": sha(pi), "key_used_sha256": sha(key),
        "independent_native_verify": {"exit": rc, "tail": out}, "control_value_tampered_native_verify": {"exit": rc2, "tail": out2},
        "decoded": {"old_root": hx(f[0]), "new_root": hx(f[1]), "commit_hash": hx(f[2]),
                    "old_root_equals_consumer_initial_root": hx(f[0]) == CONTRACT_INITIAL_ROOT,
                    "messages_total": len(msgs), "messages_nonzero": sum(1 for m in msgs if iv(m)),
                    "mint_message": {"kind": iv(msgs[0]), "note_kind": hx(msgs[1]), "value": iv(msgs[2]), "mint_hash": hx(msgs[3])},
                    "words_after_the_4_mint_words_all_zero": all(iv(m) == 0 for m in msgs[4:]),
                    "public_input_indices": {"kind": 3, "note_kind": 4, "value": 5, "mint_hash": 6}}}
    summary["status"] = "COMPLETED: agg_final proof with one mint message generated and natively verified" if rc == 0 else "proof generated but native verification FAILED"
json.dump(summary, open(f"{L}/40_proof_summary.json", "w"), indent=2); open(f"{L}/40_proof_summary.json", "a").write("\n")
print(json.dumps({k: v for k, v in summary.items() if k != "bb_calls"}, indent=1)[:3000])
