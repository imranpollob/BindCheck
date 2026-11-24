#!/usr/bin/env python3
"""Freeze dataset v1 from the final rater labels and draw the dev/test split.

Usage: python3 -I dataset/labels-v1/build_v1.py /home/pollmix/Coding/labeling-a

Inputs (from the labeling repo, Pass 1 only; the Pass 2 code-review file and
discussion/ are NOT read here, they stay restricted until tool freeze):
  sheet-rater-A.labeled.csv   final adjudicated Pass 1 labels (AI-proposed, rater-adjudicated)
  project_map.csv             item -> project family
Also reads ../audit-sweep/labeling/key/KEY.csv for the candidate keys.

Split (by project FAMILY, never by item, so one project cannot sit in both sets):
  1. Families exposed to the orchestrator before the split (EXPOSURE.md, 2026-11-24) are forced to dev.
  2. Remaining families with >=1 FULL binding item are shuffled with SEED and assigned greedily
     to whichever set has fewer FULL binding items (tie -> test).
  3. Families with no FULL binding item are assigned by sha256(SEED:family) parity, so items
     pinned later inherit a stable, pre-committed split.
"""
import csv, hashlib, pathlib, random, sys, collections

SEED = 20261124
FORCED_DEV = {"Oxorio SAMM", "Taiko / Surge"}  # L001, L041, L019 seen by orchestrator
DUPS = {"L121": "L112", "L223": "L260", "L201": "L171", "L142": "L087"}
# fixed-version negatives that are not usable (from rater notes, 2026-11-24)
FIX_UNUSABLE = {
    "L016": "vuln commit already contains the fix",
    "L012": "fix commit not public", "L029": "fix commit not public",
    "L047": "fix commit not public (real fix is a squash)", "L049": "fix commit not reachable",
    "L027": "fix commit not a descendant of vuln commit",
    "L041": "fix does not touch the finding", "L051": "fix does not touch the finding",
    "L002": "fix does not touch the finding", "L031": "fix does not touch the finding",
    "L001": "partial fix", "L042": "partial fix", "L048": "partial fix",
}
NO_ZK_PATH = {"L022"}

src = pathlib.Path(sys.argv[1])
here = pathlib.Path(__file__).resolve().parent
key = {r["item_id"]: r for r in csv.DictReader(open(here.parent / "audit-sweep/labeling/key/KEY.csv"))}
fam = {r["item_id"]: r["family"] for r in csv.DictReader(open(src / "project_map.csv"))}
rows = list(csv.DictReader(open(src / "sheet-rater-A.labeled.csv")))

full_y = collections.Counter(fam[r["item_id"]] for r in rows if r["tier"] == "FULL" and r["binding"] == "Y")
split = {f: "dev" for f in FORCED_DEV}
cnt = {"dev": sum(full_y[f] for f in FORCED_DEV), "test": 0}
rest = sorted(f for f in full_y if f not in split)
random.Random(SEED).shuffle(rest)
for f in rest:
    s = "dev" if cnt["dev"] < cnt["test"] else "test"
    split[f] = s
    cnt[s] += full_y[f]
for f in set(fam.values()) - set(split):
    split[f] = "test" if int(hashlib.sha256(f"{SEED}:{f}".encode()).hexdigest(), 16) % 2 else "dev"

out = []
for r in rows:
    i = r["item_id"]
    o = dict(r)
    o.update({
        "family": fam[i], "split": split[fam[i]], "finding_key": key[i]["finding_key"],
        "dup_of": DUPS.get(i, ""), "holdout_flag": key[i]["holdout_flag"],
        "eval_vuln": "yes" if r["tier"] == "FULL" and r["binding"] in ("Y", "N") and i not in DUPS and i not in NO_ZK_PATH and key[i]["holdout_flag"] != "FORBIDDEN" else "no",
        "eval_fixed_negative": "yes" if r["tier"] == "FULL" and r["binding"] == "Y" and r["fix_commit"] and i not in FIX_UNUSABLE and key[i]["holdout_flag"] != "FORBIDDEN" else "no",
        "fix_note": FIX_UNUSABLE.get(i, ""),
        "label_provenance": "AI-proposed, rater-adjudicated (Pass 1, report-only)",
    })
    out.append(o)

with open(here / "LABELS-v1.csv", "w", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(out[0]))
    w.writeheader(); w.writerows(out)
with open(here / "SPLIT-v1.csv", "w", newline="") as h:
    w = csv.writer(h); w.writerow(["family", "split", "full_binding_items"])
    for f in sorted(split): w.writerow([f, split[f], full_y.get(f, 0)])

def c(pred): return sum(1 for o in out if pred(o))
summ = [
    "# Dataset v1 summary", "",
    f"- Items: {len(out)}; binding Y {c(lambda o:o['binding']=='Y')}, N {c(lambda o:o['binding']=='N')}, U {c(lambda o:o['binding']=='U')}; duplicates marked {len(DUPS)}",
    f"- Families: {len(split)} (dev {sum(1 for v in split.values() if v=='dev')}, test {sum(1 for v in split.values() if v=='test')})",
]
for s in ("dev", "test"):
    summ.append(f"- **{s}**: FULL binding (positives) {c(lambda o:o['split']==s and o['eval_vuln']=='yes' and o['binding']=='Y')}, "
                f"FULL not-binding (hard negatives) {c(lambda o:o['split']==s and o['eval_vuln']=='yes' and o['binding']=='N')}, "
                f"fixed-version negatives {c(lambda o:o['split']==s and o['eval_fixed_negative']=='yes')}, "
                f"LIGHT/PSS binding (characterization only) {c(lambda o:o['split']==s and o['tier']!='FULL' and o['binding']=='Y')}")
summ += ["", f"Seed {SEED}; forced dev families: {sorted(FORCED_DEV)}.",
         f"Input sha256: sheet `{hashlib.sha256((src/'sheet-rater-A.labeled.csv').read_bytes()).hexdigest()}`, "
         f"map `{hashlib.sha256((src/'project_map.csv').read_bytes()).hexdigest()}`"]
(here / "SUMMARY.md").write_text("\n".join(summ) + "\n")
print("\n".join(summ))
