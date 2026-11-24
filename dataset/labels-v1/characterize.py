#!/usr/bin/env python3
"""Characterization statistics for dataset v1 (all splits; report-level Pass 1 labels)."""
import csv, collections as C, pathlib, re
here = pathlib.Path(__file__).resolve().parent
rows = [r for r in csv.DictReader(open(here / "LABELS-v1.csv")) if not r["dup_of"] and r["binding"] != "U"]
Y = [r for r in rows if r["binding"] == "Y"]
def sev(s):
    s = s.lower()
    for k, v in (("crit", "Critical"), ("high", "High"), ("med", "Medium"), ("low", "Low"), ("info", "Info"), ("warn", "Info"), ("note", "Info")):
        if k in s: return v
    return "Unrated"
out = ["# Characterization (dataset v1, Pass 1 labels, duplicates and U removed)", "",
       f"- Findings: {len(rows)}; binding {len(Y)}; not binding {len(rows)-len(Y)}",
       f"- Binding with PSS = Y: {sum(r['proof_system_soundness']=='Y' for r in Y)}; tagged circuit-soundness (N): {sum(r['notes'].startswith('[circuit-soundness]') for r in rows)}",
       f"- Projects (families) with >=1 binding finding: {len({r['family'] for r in Y})} of {len({r['family'] for r in rows})}", ""]
pats = ["P1", "P2", "P3", "P4", "P5", "OTHER"]
sevs = ["Critical", "High", "Medium", "Low", "Info", "Unrated"]
t = C.Counter((r["pattern"], sev(r["severity"])) for r in Y)
out += ["## Binding findings: pattern x auditor severity", "", "| pattern | " + " | ".join(sevs) + " | total |", "|---" * (len(sevs) + 2) + "|"]
for p in pats:
    out.append(f"| {p} | " + " | ".join(str(t[(p, s)]) for s in sevs) + f" | {sum(t[(p, s)] for s in sevs)} |")
low = [r for r in Y if sev(r["severity"]) in ("Low", "Info")]
out += ["", f"- Binding findings the auditor rated Low/Info: {len(low)} of {len(Y)}", ""]
a = C.Counter(r["auditor"] for r in Y)
out += ["## Binding findings by auditor/source", ""] + [f"- {k}: {v}" for k, v in a.most_common()]
yrs = C.Counter((r["report_date"] or "")[:4] or "n/a" for r in Y)
out += ["", "## Binding findings by report year", ""] + [f"- {k}: {v}" for k, v in sorted(yrs.items())]
(here / "CHARACTERIZATION.md").write_text("\n".join(out) + "\n")
print("\n".join(out[:22]))
