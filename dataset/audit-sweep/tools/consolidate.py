#!/usr/bin/env python3
"""Consolidate acquisition passes (acquire, acquire2, acquire3; later passes override)
and triage (triage.csv + triage_delta.csv) onto merged/candidates.csv.
Writes merged/acquisition_final.csv. Run after tools/merge.py."""
import csv, pathlib
B = pathlib.Path(__file__).resolve().parents[1]
C = {c["finding_key"]: c for c in csv.DictReader(open(B / "merged/candidates.csv"))}
A = {}
for p in ["acquire", "acquire2", "acquire3"]:
    f = B / p / "acquisition.csv"
    if f.exists():
        for a in csv.DictReader(open(f)):
            a["_pass"] = p
            A[a["finding_key"]] = a
T = {}
for p in ["triage.csv", "triage_delta.csv"]:
    f = B / "triage" / p
    if f.exists():
        for t in csv.DictReader(open(f)):
            T[t["finding_key"]] = t
rows = []
for k, c in C.items():
    a, t = A.get(k, {}), T.get(k, {})
    cls = "scope-question" if c["flag"].startswith("scope-question") else c["group_best_decision"]
    rows.append({"group_id": c["group_id"], "finding_key": k, "class": cls, "flag": c["flag"],
                 "triage": t.get("triage", ""), "proof_system_soundness": t.get("proof_system_soundness", ""),
                 "pattern_guess": c["pattern_guess"], "proof_system": c.get("proof_system", ""),
                 "circuit_lang": a.get("circuit_lang") or c.get("circuit_lang", ""),
                 "repo": a.get("repo", c["repo"]), "vuln_commit": a.get("vuln_commit", ""),
                 "fix_commit": a.get("fix_commit", ""), "fix_confidence": a.get("fix_confidence", ""),
                 "acquirability": a.get("acquirability_after", c["acquirability"]),
                 "holdout_flag": a.get("holdout_flag", c["holdout_flag"]), "acq_pass": a.get("_pass", "none"),
                 "title": c["title"]})
w = csv.DictWriter(open(B / "merged/acquisition_final.csv", "w", newline=""), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", sum(1 for r in rows if r["acq_pass"] == "none"), "without acquisition;",
      sum(1 for r in rows if r["class"] == "BORDERLINE" and not r["flag"] and not r["triage"]), "plain BORDERLINE without triage")
