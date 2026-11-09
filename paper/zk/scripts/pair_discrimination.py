#!/usr/bin/env python3
"""Vulnerable/fixed pair discrimination on the three DEV historical pairs.

Read-only. For each pair (H01/H02 zkDrops, H03/H04 Semaphore, H05/H06 Payy)
records: arms A and C (red-team DEV campaign, analyzer-independent) as
verdict + finding codes; BindCheck at T25 (content 2741c40e) and at the frozen
controlling run (content 8ea6d223) as the pattern verdict the pair targets.

usage: pair_discrimination.py <redteam-dev-cases-dir> <frozen-run-dir> <out.json>
"""
import csv
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PAIRS = [("zkDrops field-alias nullifier", "DEV-H01", "DEV-H02", "P3"),
         ("Semaphore alias (snarkjs pin)", "DEV-H03", "DEV-H04", "P3"),
         ("Payy agg_agg message tail", "DEV-H05", "DEV-H06", None)]


def arm(cases, row, a):
    d = json.loads((cases / row / f"{a}.json").read_text())
    res = d.get("result") or {}
    return {"status": d["run"]["status"], "verdict": res.get("verdict"),
            "codes": sorted({f["code"] for f in res.get("findings", [])})}


def main():
    cases, run, out = map(pathlib.Path, sys.argv[1:4])
    t25 = {}
    with (REPO / "reports/T25-full-dev-ledger.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["phase"] == "after":
                t25[r["id"]] = r
    frozen = {r["id"]: r for r in json.loads((run / "per-row-ledger.json").read_text())}
    rows = []
    for name, vuln, fixed, pat in PAIRS:
        entry = {"pair": name, "vulnerable": vuln, "fixed": fixed, "pattern": pat}
        for a in ("A", "C"):
            va, fa = arm(cases, vuln, a), arm(cases, fixed, a)
            entry[f"arm_{a}"] = {"vulnerable": va, "fixed": fa,
                                 "identical_output": va == fa}
        pats = [pat] if pat else ["P1", "P2", "P3", "P4", "P5"]
        entry["bindcheck_t25"] = {p: [t25[vuln][f"{p}_verdict"], t25[fixed][f"{p}_verdict"]] for p in pats}
        entry["bindcheck_frozen"] = {p: [frozen[vuln]["verdicts"][p], frozen[fixed]["verdicts"][p]] for p in pats}
        rows.append(entry)
    pathlib.Path(out).write_text(json.dumps({
        "sources": {"redteam_cases": str(cases), "t25": "reports/T25-full-dev-ledger.csv (phase=after)",
                    "frozen": str(run / "per-row-ledger.json")},
        "pairs": rows}, indent=2) + "\n")
    for e in rows:
        print(e["pair"], "A same:", e["arm_A"]["identical_output"], "C same:", e["arm_C"]["identical_output"],
              "T25:", e["bindcheck_t25"], "frozen:", e["bindcheck_frozen"])


if __name__ == "__main__":
    main()
