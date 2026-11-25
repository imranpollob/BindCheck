#!/usr/bin/env python3
"""Per-mutant/decoy evidence: apply the B3 edit(s) to a full copy of the host (from run_honest.sh's OUT/src,
pinned archives with tests) and run the host's own tests for that layer. Records which tests fail vs clean.

  python3 run_killtests.py --honest results/raw/B3/honest-1 --out results/raw/B3/kill-1 [--ids ID ...]

A mutant 'is killed' when >=1 host test that passes on clean fails. This is evidence that the edit removes
a tested binding check; it is not an exploit. Decoys are expected to keep the binding (they may still fail a
test that pins the removed line). Circom circuits have no runnable host circuit tests here (reported n/a).
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); import make_mutants as mm
ROOT = HERE.parent.parent
NARGO = ROOT / "tools/noir-1.0.0-beta.22/nargo"
MEM = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=8G", "env", f"PATH={os.environ['PATH']}"]

def cmd_for(m):
    h, side, f = m["host"], m["side"], m["file"]
    if side == "C":
        if h == "dark": return ("circuits", [str(NARGO), "test", "--workspace"])
        if h == "kakushi": return ("packages/zk/circuits/shielded_withdraw", [str(NARGO), "test"])
        return None
    if side == "G":
        crate = f.split("/")[2]
        return (f"zk-proofs/risc_zero/{crate}", ["cargo", "test", "-q", "-p", f.split("/")[2].replace("_event", "").replace("_", "-") + "-proof-core"])
    return {"zkerc20": ("circuits", ["npx", "hardhat", "test"]),
            "dark": ("circuits" if "verifiers" in f else "contracts", ["forge", "test"]),
            "davinci": ("solidity", ["forge", "test"]),
            "xchain": ("smart-contracts", ["forge", "test", "--offline", "--no-match-path", "test/fuzzing/*"]),
            "kakushi": ("packages/contracts", ["forge", "test", "--match-path", "test/privacy/*"])}[h]

def failing(log):
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    fails = set(re.findall(r"Testing ([\w:]+) \.\.\. FAIL", log))
    fails |= set(re.findall(r"\[FAIL[^\]]*\]\s+(\w+)", log)) | set(re.findall(r"^\s*\d+\) .*?\n\s+(.+?):\s*$", log, re.M))
    fails |= {x for x in re.findall(r"^\[(?:FAIL|fail)\].*?(\w+)$", log, re.M)}
    fails |= set(re.findall(r"^\[[\w_]+\] Testing (\w+)\.\.\. .*?FAIL", log, re.M))
    return sorted(fails)

def run(dirpath, cmd, logf, env_extra=None):
    t = time.time(); env = dict(os.environ, **(env_extra or {}))
    p = subprocess.run(MEM + cmd, cwd=dirpath, capture_output=True, text=True, env=env, timeout=1500)
    out = p.stdout + p.stderr; logf.write_text(out); return p.returncode, out, round(time.time() - t)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--honest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--ids", nargs="*"); a = ap.parse_args()
    src = pathlib.Path(a.honest).resolve() / "src"; out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    res_f = out / "kill-results.json"; res = json.loads(res_f.read_text()) if res_f.exists() else {}
    env_extra = {"CARGO_TARGET_DIR": str(ROOT / "results/raw/B3/hostbuild/xchain-target")}
    for m in mm.M:
        if a.ids and m["id"] not in a.ids: continue
        if m["id"] in res: print("resume-skip", m["id"]); continue   # resume state
        c = cmd_for(m)
        if c is None: res[m["id"]] = {"status": "n/a (no runnable host circuit tests)"}; res_f.write_text(json.dumps(res, indent=1)); continue
        sub, cmd = c
        base_key = f"CLEAN:{m['host']}:{sub}:{' '.join(cmd)}"
        if base_key not in res:
            ec, log, s = run(src / m["host"] / sub, cmd, out / f"CLEAN-{m['host']}-{sub.replace('/', '_')}.log", env_extra)
            res[base_key] = {"exit": ec, "fails": failing(log), "secs": s}; res_f.write_text(json.dumps(res, indent=1))
        work = out / "work" / m["id"]
        if work.exists(): shutil.rmtree(work)   # build dir only
        shutil.copytree(src / m["host"], work, symlinks=True)
        for fn, an, rp in mm.edits(m):
            p = work / fn; p.write_text(mm.apply_one(p.read_text(), m["id"], m["host"], fn, an, rp))
        ec, log, s = run(work / sub, cmd, out / f"{m['id']}.log", env_extra)
        clean_f = set(res[base_key]["fails"])
        newf = sorted(set(failing(log)) - clean_f)
        compiled = not re.search(r"Compiler run failed|error\[|Error: Compilation failed|HH600|aborting due to", log)
        res[m["id"]] = {"kind": m["kind"], "exit": ec, "new_failing_tests": newf, "compiled": compiled, "secs": s,
                        "killed": bool(newf) if compiled else None}
        res_f.write_text(json.dumps(res, indent=1)); print(m["id"], "killed" if newf else "survived", newf[:4], f"{s}s")
        shutil.rmtree(work)   # build dir only

if __name__ == "__main__": main()
