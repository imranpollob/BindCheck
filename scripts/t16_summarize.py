#!/usr/bin/env python3
"""T16 summarizer (revision c4d2c90 only). Identifies the control and candidate agg_final prove/verify bb calls by the key
bytes bb received (compared with revision A's own committed agg_final key), independently re-verifies each with the pinned
bb (a fresh process, not the harness's own in-process verify), and decodes the final public inputs at the source-defined
offsets (old_root, new_root, commit_hash, then messages[1000]).
usage: python3 -I t16_summarize.py <checkout_dir> <capture_dir> <harness_out_dir> <out_dir>"""
import hashlib, json, os, re, subprocess, sys

H, CAP, HARNESS_OUT, OUT = sys.argv[1:5]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REV = "c4d2c9021b8fb9988816eb6987a734b830bfce15"
BB = os.path.join(ROOT, "tools/bb-3.0.0-manual.20251030/bb")
sha = lambda b: hashlib.sha256(b).hexdigest()
hx = lambda b: "0x" + b.hex(); iv = lambda b: int.from_bytes(b, "big")
git_cat = lambda p: subprocess.run(["git", "-C", H, "cat-file", "-p", f"{REV}:{p}"], capture_output=True, check=True).stdout
os.makedirs(OUT, exist_ok=True)

agg_final_key = git_cat("fixtures/circuits/agg_final/key"); open(f"{OUT}/agg_final_key_committed", "wb").write(agg_final_key)
key_sha = {sha(git_cat(f"fixtures/circuits/{c}/key")): c for c in ("utxo", "agg_utxo", "agg_agg", "agg_final")}

calls = []
for name in sorted(os.listdir(CAP)) if os.path.isdir(CAP) else []:
    d = os.path.join(CAP, name)
    rd = lambda f: open(os.path.join(d, f)).read() if os.path.exists(os.path.join(d, f)) else ""
    ru = rd("rusage.txt"); m = re.search(r"([\d.]+)\s+real", ru); r = re.search(r"(\d+)\s+maximum resident set size", ru)
    kp = os.path.join(d, "key")
    calls.append({"call": name, "exit": rd("exit.txt").strip(), "real_s": float(m.group(1)) if m else None,
                  "max_rss_gib": round(int(r.group(1)) / 2**30, 2) if r else None,
                  "circuit": key_sha.get(sha(open(kp, "rb").read())) if os.path.exists(kp) else None})
summary = {"revision": REV, "bb_calls": calls, "all_bb_calls_exit_0": bool(calls) and all(c["exit"] == "0" for c in calls)}

def verify(proof_path, pi_path):
    r = subprocess.run([BB, "verify", "--scheme", "ultra_honk", "--oracle_hash", "keccak", "-k", f"{OUT}/agg_final_key_committed", "-p", proof_path, "-i", pi_path], capture_output=True, text=True)
    return {"exit": r.returncode, "tail": re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr).strip()[-160:]}

harness = json.load(open(f"{HARNESS_OUT}/harness.json"))
for role in ("control", "candidate"):
    h = harness[role]
    entry = {"witness_satisfied_and_proof_generated": h["witness_satisfied_and_proof_generated"], "failure_stage": h["failure_stage"], "error": h["error"]}
    if h["witness_satisfied_and_proof_generated"]:
        src_proof, src_pi = f"{HARNESS_OUT}/{role}/proof", f"{HARNESS_OUT}/{role}/public_inputs"
        dst = f"{OUT}/{role}"; os.makedirs(dst, exist_ok=True)
        proof, pi = open(src_proof, "rb").read(), open(src_pi, "rb").read()
        open(f"{dst}/proof", "wb").write(proof); open(f"{dst}/public_inputs", "wb").write(pi)
        f = [pi[i:i + 32] for i in range(0, len(pi), 32)]
        entry.update({"proof_bytes": len(proof), "proof_sha256": sha(proof), "public_inputs_fields": len(f), "public_inputs_sha256": sha(pi),
                      "independent_native_verify": verify(f"{dst}/proof", f"{dst}/public_inputs")})
        msgs = f[3:]
        nz = [(k, hx(m)) for k, m in enumerate(msgs) if iv(m)]
        entry["decoded"] = {"old_root": hx(f[0]), "new_root": hx(f[1]), "commit_hash": hx(f[2]),
                            "nonzero_message_words": [{"message_index": k, "outer_public_input_index": k + 3, "value": v} for k, v in nz],
                            "nonzero_count": len(nz)}
        if nz:
            k = nz[-1][0]; bad = bytearray(pi); bad[(3 + k) * 32 + 31] ^= 1
            open(f"{dst}/CONTROL_public_inputs_last_nonzero_word_flipped", "wb").write(bytes(bad))
            entry["tamper_control_last_nonzero_word_flipped"] = {"message_index": k, **verify(f"{dst}/proof", f"{dst}/CONTROL_public_inputs_last_nonzero_word_flipped")}
    summary[role] = entry

# field-by-field diff between the two decoded public-input arrays (only meaningful if both proved)
if summary["control"]["witness_satisfied_and_proof_generated"] and summary["candidate"]["witness_satisfied_and_proof_generated"]:
    cpi = open(f"{OUT}/control/public_inputs", "rb").read(); kpi = open(f"{OUT}/candidate/public_inputs", "rb").read()
    cf = [cpi[i:i + 32] for i in range(0, len(cpi), 32)]; kf = [kpi[i:i + 32] for i in range(0, len(kpi), 32)]
    names = ["old_root", "new_root", "commit_hash"] + [f"messages[{i}]" for i in range(len(cf) - 3)]
    diffs = [{"field": names[i], "outer_index": i, "control": hx(cf[i]), "candidate": hx(kf[i])} for i in range(len(cf)) if cf[i] != kf[i]]
    summary["control_vs_candidate_public_input_differences"] = diffs

json.dump(summary, open(f"{OUT}/40_summary.json", "w"), indent=2); open(f"{OUT}/40_summary.json", "a").write("\n")
print(json.dumps({k: v for k, v in summary.items() if k != "bb_calls"}, indent=1)[:4000])
