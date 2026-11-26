"""Post-hoc Mythril arm (NOT pre-registered) on locally deployed B3 targets. Sequential, resumable.

Usage: python3 run_mythril.py OUT_DIR [ID ...]     (default: the full PLAN below)
Per (ID, part): OUT/<ID>[@part].{json,log,meta}; OUT/<ID>.deploy.json. A `.meta` means done (skip on rerun).
Flags (identical for every run): myth -v 4 analyze -a ADDR --rpc 127.0.0.1:8545 --execution-timeout 300
  --max-depth 128 (Mythril default) -t 2 (default) -o json; outer `timeout 420`; MemoryMax=8G.
CLEAN-<host>#2 is a second, independent clean run used to measure run-to-run noise.
"""
import json, pathlib, subprocess, sys, time
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import deploy
MY = deploy.R / "mvenv/bin/myth"
FLAGS = ["--execution-timeout", "300", "--max-depth", "128", "-t", "2", "-o", "json"]
PLAN = {}
for h, parts in {"xchain": ["", "adapter"], "kakushi": [""], "davinci": ["", "dealverifier"], "dark": ["", "verifier"], "zkerc20": ["", "zkerc20", "verifier"]}.items():
    PLAN[f"CLEAN-{h}"] = parts; PLAN[f"CLEAN-{h}#2"] = parts
PLAN.update({i: [""] for i in ["XC-S01", "XC-S02", "XC-S03", "XC-S05", "XC-S06"]})
PLAN.update({"XC-S04": ["adapter"], "XC-S07": ["", "adapter"], "XC-D01": ["adapter"]})
PLAN.update({f"KK-S0{i}": [""] for i in range(1, 9)})
PLAN.update({f"DV-S0{i}": [""] for i in range(1, 5)}); PLAN["DV-S05"] = ["dealverifier"]
PLAN.update({"DK-S01": ["verifier", ""], "DK-D01": [""]})
PLAN.update({"ZK-S01": ["zkerc20"], "ZK-S02": ["zkerc20", "verifier"], "ZK-S03": ["zkerc20", "verifier"],
             "ZK-S04": ["zkerc20"], "ZK-S05": ["zkerc20"], "ZK-D01": ["zkerc20"]})

def main():
    out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[2:] or list(PLAN)
    for tid in ids:
        todo = [p for p in PLAN[tid] if not (out / f"{tid}{'@' + p if p else ''}.meta").exists()]
        if not todo: print("skip", tid); continue
        try: addrs = deploy.deploy(tid.split("#")[0])
        except Exception as e:  # deployment failure = unsupported for this arm; recorded, not retried silently
            for p in todo: (out / f"{tid}{'@' + p if p else ''}.meta").write_text(f"tool=mythril-anvil id={tid} exit=DEPLOY-FAILED err={str(e)[:300]!r}\n")
            print(tid, "DEPLOY-FAILED", flush=True); continue
        (out / f"{tid}.deploy.json").write_text(json.dumps(addrs) + "\n")
        for p in todo:
            name = f"{tid}{'@' + p if p else ''}"
            # fresh chain state per analysed part: redeploy so earlier analysis cannot have changed anything
            if p != todo[0]: addrs = deploy.deploy(tid.split("#")[0])
            cmd = ["timeout", "420", "systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=8G", str(MY), "-v", "4", "analyze",
                   "-a", addrs[p], "--rpc", "127.0.0.1:8545", *FLAGS]
            t = time.time()
            with open(out / f"{name}.json", "w") as j, open(out / f"{name}.log", "w") as l:
                ec = subprocess.run(cmd, stdout=j, stderr=l).returncode
            (out / f"{name}.meta").write_text(f"tool=mythril-anvil id={name} exit={ec} seconds={round(time.time() - t)} addr={addrs[p]} cmd={' '.join(cmd)}\n")
            print(name, ec, round(time.time() - t), flush=True)

if __name__ == "__main__":
    main()
