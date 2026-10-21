#!/usr/bin/env python3
"""Measure a saved SMT query's child exit and peak RSS with wait4."""
import argparse
import hashlib
import json
import os
import resource
import signal
import subprocess
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=Path, required=True)
    ap.add_argument("--cvc5", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=300)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(args.cvc5.resolve()), "--lang=smt2", "--ff-solver=split", str(args.query.resolve())]
    cap = 4 * 1024**3

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))

    stdout_path = args.output.with_suffix(".stdout")
    stderr_path = args.output.with_suffix(".stderr")
    start = time.monotonic()
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        child = subprocess.Popen(command, stdout=out, stderr=err,
                                 preexec_fn=limit, start_new_session=True)
        timed_out = False
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - start >= args.seconds:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                _, status, usage = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            time.sleep(0.1)
    info = {"command": command, "query_sha256": hashlib.sha256(args.query.read_bytes()).hexdigest(),
            "memory_limit_bytes": cap, "time_limit_seconds": args.seconds,
            "timed_out": timed_out, "wall_seconds": round(time.monotonic() - start, 3),
            "exit_status": child.returncode, "maxrss_kib": usage.ru_maxrss,
            "user_cpu_seconds": round(usage.ru_utime, 3), "system_cpu_seconds": round(usage.ru_stime, 3),
            "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
            "stdout_sha256": hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_path.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__": main()
