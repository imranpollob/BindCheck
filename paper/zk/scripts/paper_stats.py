#!/usr/bin/env python3
"""Derive every computed number used by paper/zk from audited lane files.

Read-only over its inputs. Writes JSON and pgfplots .dat files under
paper/zk/data/. No number is rounded here; LaTeX prints values verbatim.

usage: paper_stats.py <controlling-run-dir>
  controlling-run-dir: .../bindcheck-zk-soundness/results/raw/soundness/
                       after-20261109T061325Z-77918  (analyzer 8ea6d223...)
"""
import csv
import json
import pathlib
import statistics
from decimal import Decimal
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parents[3]
DATA = REPO / "paper/zk/data"
PATTERNS = ["P1", "P2", "P3", "P4", "P5"]


def frozen_dev(run: pathlib.Path):
    rows = json.loads((run / "per-row-ledger.json").read_text())
    verdicts = {p: Counter() for p in PATTERNS}
    applicable = {p: Counter() for p in PATTERNS}
    violations = []
    for row in rows:
        for p in PATTERNS:
            v = row["verdicts"][p]
            a = row["applicability"][p]
            verdicts[p][v] += 1
            applicable[p][a] += 1
            if a == "APPLICABLE":
                applicable[p]["decided" if v != "UNKNOWN" else "undecided"] += 1
            if v == "VIOLATION":
                violations.append({"id": row["id"], "repository": row["repository"],
                                   "pattern": p, "reasons": row["reasons"][p]})
    runtimes = sorted(r["runtime_seconds"] for r in rows)
    return {
        "source": str(run / "per-row-ledger.json"),
        "rows": len(rows),
        "crashes": sum(bool(r["crash"]) for r in rows),
        "rows_with_triples": sum(r["triples"] > 0 for r in rows),
        "builds_ok": sum(r["builds_ok"] for r in rows),
        "builds_failed": sum(r["builds_failed"] for r in rows),
        "verdicts": {p: dict(verdicts[p]) for p in PATTERNS},
        "applicability": {p: dict(applicable[p]) for p in PATTERNS},
        "violation_rows": violations,
        "violation_reason_codes": sorted({c for v in violations for c in v["reasons"]}),
        "runtime_seconds": {
            "n": len(runtimes),
            "median": statistics.median(runtimes),
            "max": runtimes[-1],
            "min": runtimes[0],
            "sum": str(sum(Decimal(repr(t)) for t in runtimes)),
            "max_row": max(rows, key=lambda r: r["runtime_seconds"])["id"],
        },
    }, runtimes


def redteam():
    path = REPO / "reports/redteam/case-comparison.csv"
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    return rows


def main():
    run = pathlib.Path(sys.argv[1])
    DATA.mkdir(parents=True, exist_ok=True)
    dev, runtimes = frozen_dev(run)
    (DATA / "frozen-dev-stats.json").write_text(json.dumps(dev, indent=2) + "\n")
    with (DATA / "runtime-frozen-dev.dat").open("w") as fh:
        fh.write("rank seconds\n")
        for i, t in enumerate(runtimes, 1):
            fh.write(f"{i} {t}\n")

    # Red-team synthetic screening: per-arm outcome counts from metrics.json.
    metrics = json.loads((REPO / "reports/redteam/metrics.json").read_text())
    arms = {}
    for arm, fams in metrics["synthetic_by_family"].items():
        c = Counter()
        for fam in fams.values():
            c.update(fam)
        d = c["VULNERABLE/DETECTION"]
        m = c["VULNERABLE/MISS"]
        fa = c["LEGITIMATE/FALSE_ALARM"]
        n = c["LEGITIMATE/NO_ALARM"]
        total = sum(c.values())
        decided = d + m + fa + n
        arms[arm] = {
            "counts": dict(c), "total": total, "decided": decided,
            "warnings": d + fa, "warnings_on_vulnerable": d,
            "unsafe_certifications": m,
        }
    (DATA / "redteam-arms.json").write_text(json.dumps(
        {"source": "reports/redteam/metrics.json#synthetic_by_family",
         "analyzer_tree": "bindcheck_zk tree 56c0b5f3 (content 2741c40e), not the frozen 8ea6d223",
         "arms": arms}, indent=2) + "\n")
    with (DATA / "redteam-scatter.dat").open("w") as fh:
        fh.write("arm decided total warnings vuln_warnings decided_rate warn_precision\n")
        for arm, a in sorted(arms.items()):
            rate = a["decided"] / a["total"]
            prec = (a["warnings_on_vulnerable"] / a["warnings"]) if a["warnings"] else "nan"
            fh.write(f"{arm} {a['decided']} {a['total']} {a['warnings']} "
                     f"{a['warnings_on_vulnerable']} {rate} {prec}\n")

    # zk_voting q-vs-r alias margin (constants copied verbatim from the pinned
    # DEV-F34 Verifier.sol lines 25 and 27).
    r = 21888242871839275222246405745257275088548364400416034343698204186575808495617
    q = 21888242871839275222246405745257275088696311157297823662689037894645226208583
    margin = q - r
    (DATA / "zkvoting-alias.json").write_text(json.dumps({
        "source": "DEV-F34--avitenzer__zk_voting--18d3a277ccd8/contracts/Verifier.sol:25,27,61-64,158",
        "r_scalar": str(r), "q_base": str(q), "q_minus_r": str(margin),
        "q_minus_r_bit_length": margin.bit_length(),
        "r_bit_length": r.bit_length(),
        "alias_exists_iff": "nullifier n < q - r (then n + r < q passes checkField and maps to the same scalar)",
        "exponent_of_two_for_uniform_hit": f"(q-r)/r < 2^-{r.bit_length() - margin.bit_length() - 1}  (since q-r < 2^{margin.bit_length()} and r >= 2^{r.bit_length()-1})",
    }, indent=2) + "\n")
    print(json.dumps({"dev_verdicts": dev["verdicts"], "runtime": dev["runtime_seconds"],
                      "arms": {k: (v["decided"], v["warnings"], v["warnings_on_vulnerable"], v["unsafe_certifications"]) for k, v in arms.items()},
                      "margin_bits": margin.bit_length()}, indent=1))


if __name__ == "__main__":
    main()
