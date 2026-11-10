#!/usr/bin/env python3
"""Reuse identical pinned email source runs and finish unique revisions."""
from __future__ import annotations

import csv
import hashlib
import json

from run_public import RAW, ROOT, one


def receipt(cid, side, commit):
    folder = RAW / cid / side
    commands = {}
    for tool, stem in (("ABC", "ABC"), ("BindCheck-F2", "bindcheck"),
                       ("Slither-default", "slither"), ("zkFuzz", "zkfuzz")):
        stdout = folder / f"{stem}.stdout"
        stderr = folder / f"{stem}.stderr"
        if stdout.is_file() and stderr.is_file():
            commands[tool] = {"status": "OUTPUT_PRESENT_EXIT_UNRECORDED",
                              "exit_status": None, "stdout": str(stdout),
                              "stdout_sha256": hashlib.sha256(stdout.read_bytes()).hexdigest(),
                              "stderr": str(stderr),
                              "stderr_sha256": hashlib.sha256(stderr.read_bytes()).hexdigest()}
    commands["ZKAP"] = {"status": "UNAVAILABLE_HOST_REQUIREMENTS"}
    return {"id": cid, "side": side, "commit": commit,
            "source_result_root": str(folder), "status": "recovered_native_outputs",
            "commands": commands,
            "outer_exit_status": "MISSING (campaign interrupted after completed case)"}


def main():
    rows = {r["row"]: r for r in csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open())}
    records = []
    for number in ("28", "29"):
        row = rows[number]
        for side in ("vulnerable", "repaired"):
            commit = row["vulnerable_commit" if side == "vulnerable" else "fixed_commit"]
            records.append(receipt(f"GATE-{number}", side, commit))
    source = records[0]
    original = json.loads((ROOT / "benchmark/public-triples/GATE-28/manifest.json").read_text())
    for number in ("30", "31", "32", "33"):
        row = rows[number]
        assert row["vulnerable_commit"] == source["commit"]
        target = json.loads((ROOT / f"benchmark/public-triples/GATE-{number}/manifest.json").read_text())
        for role in ("circuit", "verifier", "consumer"):
            assert original["revisions"]["vulnerable"]["roles"][role]["sha256"] == target["revisions"]["vulnerable"]["roles"][role]["sha256"]
        records.append({"id": f"GATE-{number}", "side": "vulnerable",
                        "commit": source["commit"],
                        "source_result_root": source["source_result_root"],
                        "reused_from": {"id": "GATE-28", "side": "vulnerable",
                                        "reason": "identical commit and pinned circuit/verifier/consumer hashes"},
                        "status": "reused_identical_revision",
                        "commands": source["commands"]})
    for number in ("30", "31", "32", "33", "40"):
        row = rows[number]
        sides = ("vulnerable", "repaired") if number == "40" else ("repaired",)
        for side in sides:
            record = one(row, side)
            records.append(record)
            print(record["id"], side, record["status"], flush=True)
    (RAW / "runs-email.json").write_text(json.dumps({
        "schema": "bindcheck-benchmark.public-runs/v1",
        "records": sorted(records, key=lambda x: (x["id"], x["side"]))
    }, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
