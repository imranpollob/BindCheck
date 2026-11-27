"""Draw the seeded, stratified held-out adjudication sample (amendment 2026-11-09).

Run once; committed before any human label exists. Strata come from the
unblinding key (tool, pattern/reason); raters see only blind cards.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEY = ROOT / "reports/heldout/warning-unblind-key.csv"
SHEET = ROOT / "review/heldout/BLIND-SHEET-rater-a.csv"
OUT = ROOT / "review/heldout-sample"
SEED = 20261109
BINDCHECK_QUOTA = {  # stratum -> cards
    ("P1", None): 15,
    ("P3", None): 15,
    ("P4", "GAMMA_EQUALS_DELTA_SOURCE_KEY"): 10,
    ("P4", "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND"): 10,
    ("P5", None): 15,
}
ARM_C_TOTAL = 35


def stratum(row: dict) -> tuple[str, str]:
    if row["tool"] == "arm-c":
        return ("arm-c", row["reason_code"])
    if row["pattern"] == "P4":
        return ("bindcheck-zk", f"P4/{row['reason_code']}")
    return ("bindcheck-zk", row["pattern"])


def largest_remainder(sizes: dict[str, int], total: int) -> dict[str, int]:
    n = sum(sizes.values())
    base = {k: max(1, (v * total) // n) for k, v in sizes.items()}
    rest = total - sum(base.values())
    order = sorted(sizes, key=lambda k: (-(sizes[k] * total / n - (sizes[k] * total) // n), k))
    for k in order[:max(0, rest)]:
        base[k] += 1
    return {k: min(v, sizes[k]) for k, v in base.items()}


def main() -> None:
    rows = list(csv.DictReader(KEY.open()))
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault(stratum(row), []).append(row)
    quota: dict[tuple[str, str], int] = {}
    for (pattern, reason), n in BINDCHECK_QUOTA.items():
        quota[("bindcheck-zk", f"P4/{reason}" if pattern == "P4" else pattern)] = n
    arm_c = {k[1]: len(v) for k, v in groups.items() if k[0] == "arm-c"}
    for code, n in largest_remainder(arm_c, ARM_C_TOTAL).items():
        quota[("arm-c", code)] = n
    rng = random.Random(SEED)
    chosen: list[dict] = []
    strata = []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda r: r["card_id"])
        k = min(quota.get(key, 0), len(members))
        picked = rng.sample(members, k) if k else []
        chosen += picked
        strata.append({"tool": key[0], "stratum": key[1], "population": len(members), "sampled": k})
    ids = sorted(r["card_id"] for r in chosen)
    blind = {r["warning_id"]: r for r in csv.DictReader(SHEET.open())}
    fields = ["warning_id", "repository", "commit", "source_path", "source_line", "message", "label", "rater_reason"]
    for rater in ("a", "b"):
        with (OUT / f"SAMPLE-SHEET-rater-{rater}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for card in ids:
                src = blind[card]
                writer.writerow({f: ("" if f in ("label", "rater_reason") else src[f]) for f in fields})
    digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    (OUT / "sample-manifest.json").write_text(json.dumps(
        {"seed": SEED, "cards": len(ids), "card_ids_sha256": digest, "card_ids": ids, "strata": strata},
        indent=1) + "\n")
    print(len(ids), digest)


if __name__ == "__main__":
    main()
