#!/usr/bin/env python3
"""T15 summarizer for ONE revision. Reads the pass-through bb captures of the T15 harness run, identifies the agg_agg prove calls by the
key bytes bb received (compared with that revision's own committed agg_agg key), copies out the control and (if produced) candidate
proofs, re-verifies each independently with the pinned bb and that revision's committed key, runs tamper controls, and decodes the
message region of the public inputs.
usage: python3 -I t15_summarize.py <label> <revision> <checkout_dir> <capture_dir> <out_dir>
Never mixes revisions: keys come from <revision> in <checkout_dir> only."""
import hashlib, json, os, re, subprocess, sys

label, rev, H, CAP, OUT = sys.argv[1:6]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BB = os.path.join(ROOT, "tools/bb-3.0.0-manual.20251030/bb")
git_cat = lambda p: subprocess.run(["git", "-C", H, "cat-file", "-p", f"{rev}:{p}"], capture_output=True, check=True).stdout
sha = lambda b: hashlib.sha256(b).hexdigest()
hx = lambda b: "0x" + b.hex(); iv = lambda b: int.from_bytes(b, "big")
os.makedirs(OUT, exist_ok=True)

keys = {sha(git_cat(f"fixtures/circuits/{c}/key")): c for c in ("utxo", "agg_utxo", "agg_agg", "agg_final")}
agg_key = git_cat("fixtures/circuits/agg_agg/key"); open(f"{OUT}/agg_agg_key_committed", "wb").write(agg_key)
calls = []
for name in sorted(os.listdir(CAP)) if os.path.isdir(CAP) else []:
    d = os.path.join(CAP, name)
    rd = lambda f: open(os.path.join(d, f)).read() if os.path.exists(os.path.join(d, f)) else ""
    ru = rd("rusage.txt"); m = re.search(r"([\d.]+)\s+real", ru); r = re.search(r"(\d+)\s+maximum resident set size", ru)
    kp = os.path.join(d, "key")
    calls.append({"call": name, "exit": rd("exit.txt").strip(), "real_s": float(m.group(1)) if m else None,
                  "max_rss_gib": round(int(r.group(1)) / 2**30, 2) if r else None,
                  "circuit": keys.get(sha(open(kp, "rb").read())) if os.path.exists(kp) else None})
summary = {"label": label, "revision": rev, "bb_calls": calls, "all_bb_calls_exit_0": bool(calls) and all(c["exit"] == "0" for c in calls)}

def verify(p, i):
    r = subprocess.run([BB, "verify", "--scheme", "ultra_honk", "-k", f"{OUT}/agg_agg_key_committed", "-p", p, "-i", i], capture_output=True, text=True)
    return {"exit": r.returncode, "tail": re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr).strip()[-140:]}

proves = [c for c in calls if c["call"].endswith("-prove") and c["circuit"] == "agg_agg" and c["exit"] == "0"]
summary["agg_agg_prove_calls"] = [c["call"] for c in proves]
roles = ["control", "candidate"]
for role, c in zip(roles, proves):
    src = os.path.join(CAP, c["call"], "out"); dst = os.path.join(OUT, role); os.makedirs(dst, exist_ok=True)
    proof = open(os.path.join(src, "proof"), "rb").read(); pi = open(os.path.join(src, "public_inputs"), "rb").read()
    open(f"{dst}/proof", "wb").write(proof); open(f"{dst}/public_inputs", "wb").write(pi)
    f = [pi[i:i + 32] for i in range(0, len(pi), 32)]
    entry = {"call": c["call"], "proof_bytes": len(proof), "proof_sha256": sha(proof), "public_inputs_fields": len(f), "public_inputs_sha256": sha(pi),
             "prove_real_s": c["real_s"], "prove_max_rss_gib": c["max_rss_gib"], "key_sha256": sha(agg_key),
             "independent_native_verify": verify(f"{dst}/proof", f"{dst}/public_inputs")}
    if len(f) == 1005:   # vk_hash[2], old_root, new_root, commit_hash, messages[1000]
        msgs = f[5:]
        nz = [(k, iv(m)) for k, m in enumerate(msgs) if iv(m)]
        entry["decoded"] = {"verification_key_hashes": [iv(f[0]), iv(f[1])], "old_root": hx(f[2]), "new_root": hx(f[3]), "commit_hash": hx(f[4]),
                            "nonzero_message_words": [{"index": k, "value": hx(msgs[k])} for k, _ in nz], "nonzero_count": len(nz),
                            "last_nonzero_index": nz[-1][0] if nz else None}
        # tamper control: flip the low bit of one message word (first nonzero word, else none) and check bb rejects
        if nz:
            k = nz[-1][0]; bad = bytearray(pi); bad[(5 + k) * 32 + 31] ^= 1
            open(f"{dst}/CONTROL_public_inputs_last_nonzero_word_flipped", "wb").write(bytes(bad))
            entry["tamper_control_last_nonzero_word_flipped"] = {"index": k, **verify(f"{dst}/proof", f"{dst}/CONTROL_public_inputs_last_nonzero_word_flipped")}
    else:
        entry["decoded"] = f"unexpected public-input field count {len(f)}"
    summary[role] = entry
json.dump(summary, open(f"{OUT}/40_summary.json", "w"), indent=2); open(f"{OUT}/40_summary.json", "a").write("\n")
print(json.dumps({k: v for k, v in summary.items() if k != "bb_calls"}, indent=1)[:3500])
