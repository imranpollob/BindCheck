#!/usr/bin/env python3
"""Run a command in its own process group with a wall-clock limit and a polled peak-RSS limit.
Reports: exit code or TIMEOUT / RSS_LIMIT, elapsed seconds, peak summed RSS of the group (polled once a second, so a
lower bound), and ru_maxrss of the largest single child. Output goes to <log>. "Not completed within budget" means
the budget stopped the run; it does not mean the step is impossible.
usage: t10_run_limited.py <seconds> <max_rss_gib> <log> <status_json> -- cmd args..."""
import json, os, resource, signal, subprocess, sys, time
secs, max_gib, log, status = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], sys.argv[4]
cmd = sys.argv[sys.argv.index("--") + 1:]
t0 = time.time(); peak = 0; outcome = None
with open(log, "wb") as lf:
    lf.write(("$ " + " ".join(cmd) + "\n").encode()); lf.flush()
    p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
    pgid = p.pid
    while p.poll() is None:
        time.sleep(1)
        try:
            out = subprocess.run(["ps", "-g", str(pgid), "-o", "rss="], capture_output=True, text=True).stdout.split()
            peak = max(peak, sum(int(x) for x in out) * 1024)
        except Exception:
            pass
        if time.time() - t0 > secs: outcome = "TIMEOUT"
        elif peak > max_gib * 2**30: outcome = "RSS_LIMIT"
        if outcome:
            os.killpg(pgid, signal.SIGKILL); break
    p.wait()
    code = p.returncode
    lf.write(f"\nexit={code} outcome={outcome or 'finished'}\n".encode())
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
res = {"command": cmd, "outcome": outcome or "finished", "exit": code, "elapsed_s": round(time.time() - t0, 1),
       "polled_peak_group_rss_gib": round(peak / 2**30, 2), "largest_single_process_maxrss_gib": round(ru.ru_maxrss / 2**30, 2),
       "limits": {"seconds": secs, "max_rss_gib": max_gib}}
json.dump(res, open(status, "w"), indent=2); open(status, "a").write("\n")
print(json.dumps({k: v for k, v in res.items() if k != "command"}))
sys.exit(0 if outcome is None and code == 0 else 1)
