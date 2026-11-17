#!/usr/bin/env python3
"""Recompute every R1 report table from reports/R1/incidents.csv.

Usage: python3 reports/R1/summarize.py [path/to/incidents.csv]

Sums only numeric cells; UNKNOWN cells are counted, never estimated.
The year for the timeline is date_incident, else date_disclosed, else UNKNOWN.
"""
import csv
import pathlib
import sys

CLASSES = ["P1", "P2", "P3", "P4", "P5", "OUT"]


def num(cell):
    try:
        return int(cell)
    except ValueError:
        return None


def money(total, unknown):
    return f"{total:,}" + (f" (+{unknown} UNKNOWN)" if unknown else "")


def main():
    default = pathlib.Path(__file__).with_name("incidents.csv")
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else default
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    print(f"rows: {len(rows)}\n")
    print("| Class | Cases | Exploited (yes) | Whitehat drain | Not exploited "
          "| Claimed loss USD | Confirmed loss USD | Recovered USD | Value at risk USD |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in CLASSES + ["ALL"]:
        sub = [r for r in rows if c == "ALL" or r["class"] == c]
        cells = [str(len(sub))]
        for e in ("yes", "whitehat", "no"):
            cells.append(str(sum(r["exploited"] == e for r in sub)))
        for col in ("loss_claimed_usd", "loss_confirmed_usd", "recovered_usd", "value_at_risk_usd"):
            vals = [num(r[col]) for r in sub]
            cells.append(money(sum(v for v in vals if v is not None), sum(v is None for v in vals)))
        print(f"| {c} | " + " | ".join(cells) + " |")

    years = {}
    for r in rows:
        d = r["date_incident"] if r["date_incident"] != "UNKNOWN" else r["date_disclosed"]
        y = d[:4] if d != "UNKNOWN" else "UNKNOWN"
        years.setdefault(y, {c: 0 for c in CLASSES})[r["class"]] += 1
    print("\n| Year | " + " | ".join(CLASSES) + " | Total |")
    print("|---|" + "---|" * (len(CLASSES) + 1))
    for y in sorted(years, key=lambda k: (k == "UNKNOWN", k)):
        counts = [years[y][c] for c in CLASSES]
        print(f"| {y} | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")

    print("\nExploited cases with a money figure (P1-P5 only):")
    for r in rows:
        if r["class"] != "OUT" and r["exploited"] in ("yes", "whitehat"):
            print(f"- {r['case_id']} {r['class']} {r['project']}: claimed {r['loss_claimed_usd']}, "
                  f"confirmed {r['loss_confirmed_usd']}, recovered {r['recovered_usd']}")


if __name__ == "__main__":
    main()
