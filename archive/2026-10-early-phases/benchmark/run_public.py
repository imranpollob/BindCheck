#!/usr/bin/env python3
"""Run all available E1 arms on exact pinned public source revisions."""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench/e1-public-20261109"
MANIFESTS = ROOT / "benchmark/public-triples"
ZKF = ROOT / "results/raw/bench/zkfuzz-setup-20261109/bin/zkfuzz"
CIRCOM = "/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom"
CIRCOMSPECT = "/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circomspect-src/target/release/circomspect"
PICUS = "/Users/imranpollob/Coding/bc/bindcheck-zk/tools/picus-src/run-picus"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, cwd, output, name, timeout, env=None):
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    environment = os.environ.copy()
    environment.update(env or {})
    try:
        proc = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            timed = True
        code = proc.returncode
    except OSError as exc:
        stdout, stderr, timed, code = b"", str(exc).encode(), False, None
    (output / f"{name}.stdout").write_bytes(stdout)
    (output / f"{name}.stderr").write_bytes(stderr)
    return {"argv": [str(x) for x in argv], "cwd": str(cwd),
            "exit_status": code, "timed_out": timed,
            "elapsed_seconds": time.monotonic() - start,
            "stdout": str(output / f"{name}.stdout"),
            "stdout_sha256": sha(output / f"{name}.stdout"),
            "stderr": str(output / f"{name}.stderr"),
            "stderr_sha256": sha(output / f"{name}.stderr")}


def one(row, side, only_zkfuzz=False):
    cid = f"GATE-{row['row']}"
    entry = json.loads((MANIFESTS / cid / "manifest.json").read_text())["revisions"][side]
    source = pathlib.Path(entry["source"])
    output = RAW / cid / side
    output.mkdir(parents=True, exist_ok=True)
    records = {"id": cid, "side": side, "commit": entry["commit"],
               "source": str(source), "triple_status": entry["status"], "commands": {}}
    if not source.is_dir() or entry.get("observed_head") != entry["commit"]:
        records["status"] = "SOURCE_UNAVAILABLE"
        return records
    env = {"PYTHONPATH": str(ROOT), "BINDCHECK_STRONG_CIRCOM": CIRCOM,
           "BINDCHECK_STRONG_CIRCOMSPECT": CIRCOMSPECT,
           "BINDCHECK_STRONG_PICUS": PICUS, "BINDCHECK_CIRCOM": CIRCOM}
    if not only_zkfuzz:
        records["commands"]["ABC"] = run(["/opt/homebrew/bin/python3", "-m", "baselines.strong.cli",
                                        source, "--output", output / "ABC",
                                        "--a-budget", "40", "--b-budget", "45"],
                                       ROOT, output, "ABC", 150, env)
        records["commands"]["BindCheck-F2"] = run([ROOT / "bindcheck-zk", "analyze", source],
                                                 ROOT, output, "bindcheck", 120, env)
    consumer = entry["roles"].get("consumer", {}).get("path")
    if not only_zkfuzz and consumer and (source / consumer).is_file():
        records["commands"]["Slither-default"] = run(["slither", source / consumer,
                                                        "--json", output / "slither.json"],
                                                       source, output, "slither", 90, env)
    elif not only_zkfuzz:
        records["commands"]["Slither-default"] = {"status": "CONSUMER_MISSING"}
    circuit = entry["roles"].get("circuit", {}).get("path")
    if circuit and circuit.endswith(".circom") and (source / circuit).is_file() and ZKF.is_file():
        records["commands"]["zkFuzz"] = run([ZKF, "--path_to_mutation_setting",
                                              ROOT / "benchmark/zkfuzz-settings.json",
                                              "-l", source / "node_modules", source / circuit],
                                             source, output, "zkfuzz", 90, env)
    else:
        records["commands"]["zkFuzz"] = {"status": "CIRCUIT_OR_BINARY_UNAVAILABLE"}
    if not only_zkfuzz:
        records["commands"]["ZKAP"] = {"status": "UNAVAILABLE_HOST_REQUIREMENTS",
                                       "source": "reports/bench/environment.json"}
    records["status"] = "attempted"
    return records


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--runs-name", default="runs.json")
    ap.add_argument("--only-zkfuzz", action="store_true")
    args = ap.parse_args()
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    if args.ids is not None:
        rows = [row for row in rows if row["row"] in args.ids]
    RAW.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(one, row, side, args.only_zkfuzz) for row in rows
                   for side in ("vulnerable", "repaired")]
        records = []
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            print(record["id"], record["side"], record["status"], flush=True)
    (RAW / args.runs_name).write_text(json.dumps({"schema": "bindcheck-benchmark.public-runs/v1",
        "records": sorted(records, key=lambda x: (x["id"], x["side"]))}, indent=2,
        sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
