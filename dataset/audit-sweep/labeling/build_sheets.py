#!/usr/bin/env python3
"""Build the blind human-labeling sheets from the audit sweep.

Usage: python3 -I dataset/audit-sweep/labeling/build_sheets.py

Package membership (see labeling/README.md):
  KEEP, scope-question, agents-disagree, triage LIKELY-BINDING / UNSURE,
  and the seeded LIKELY-NOT validation samples (triage/SAMPLE.md, SAMPLE_delta.md).

Tiers:
  FULL  - acquirable (PINNED / PINNED-PAIR), not proof-system soundness: full labels
  PSS   - flagged proof-system soundness or scope-question: is it PSS? + binding
  LIGHT - everything else: binding + pattern

Outputs (labeling/):
  sheet-rater-A.csv   every item, blind (no AI decision, pattern, triage, mechanism)
  sheet-rater-B.csv   seeded ~30% stratified overlap, blind, independently shuffled
  key/KEY.csv         item_id -> finding_key + AI labels (analysis only; raters must not open)
  key/MANIFEST.md     counts, seeds, input hashes
"""
import csv, hashlib, math, pathlib, random, re, collections

B = pathlib.Path(__file__).resolve().parents[1]
OUT = B / "labeling"
(OUT / "key").mkdir(parents=True, exist_ok=True)
SEED_ORDER, SEED_B = 20261124, 20261125
B_FRACTION = 0.30


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


acq = {r["finding_key"]: r for r in csv.DictReader(open(B / "merged/acquisition_final.csv"))}
cand = {r["finding_key"]: r for r in csv.DictReader(open(B / "merged/candidates.csv"))}
allf = {}
for r in csv.DictReader(open(B / "merged/all_findings.csv")):
    allf.setdefault(r["finding_key"], r)
reps = {}
for r in csv.DictReader(open(B / "merged/all_reports.csv")):
    reps.setdefault(r["report_key"], r)


def sample_keys(path):
    if not path.exists():
        return set()
    return set(re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`", path.read_text()))


ln_sample = sample_keys(B / "triage/SAMPLE.md") | sample_keys(B / "triage/SAMPLE_delta.md")

items = []
for k, a in acq.items():
    c = cand[k]
    if a["class"] == "scope-question":
        why = "scope-question"
    elif c["flag"] == "agents-disagree":
        why = "agents-disagree"
    elif a["class"] == "KEEP":
        why = "KEEP"
    elif a["triage"] in ("LIKELY-BINDING", "UNSURE"):
        why = "triage-" + a["triage"]
    elif a["triage"] == "LIKELY-NOT" and k in ln_sample:
        why = "triage-LN-sample"
    else:
        continue
    pss = a["proof_system_soundness"] == "yes" or why == "scope-question"
    if pss:
        tier = "PSS"
    elif a["acquirability"] in ("PINNED", "PINNED-PAIR"):
        tier = "FULL"
    else:
        tier = "LIGHT"
    f = allf.get(k, c)
    r = reps.get(f["report_key"], {})
    items.append({"k": k, "why": why, "tier": tier, "a": a, "f": f, "r": r})

# blind sheet rows, shuffled within tier (FULL first, then LIGHT, then PSS)
rng = random.Random(SEED_ORDER)
order = []
for tier in ("FULL", "LIGHT", "PSS"):
    grp = sorted([i for i in items if i["tier"] == tier], key=lambda i: i["k"])
    rng.shuffle(grp)
    order += grp
for n, it in enumerate(order, 1):
    it["item_id"] = f"L{n:03d}"

FILL = ["binding", "proof_system_soundness", "pattern", "c1_proof_accepted", "c2_effect_committed",
        "c3_value_not_fixed", "effect", "unbound_value", "intended_policy", "confidence", "minutes", "notes"]


def blind_row(it):
    f, r, a = it["f"], it["r"], it["a"]
    full = it["tier"] == "FULL"
    row = {
        "item_id": it["item_id"], "tier": it["tier"],
        "auditor": r.get("auditor_or_platform", ""), "project": r.get("protocol", ""),
        "report_title": r.get("report_title", ""), "report_date": r.get("report_date", ""),
        "report_url": r.get("report_url", "") or f.get("finding_url", ""),
        "finding_id": f.get("finding_id", ""), "finding_title": f.get("title", ""),
        "severity": f.get("severity", ""), "where_in_report": f.get("page_or_anchor", ""),
        "auditor_quote": f.get("quote", ""),
        "repo": a["repo"] if full else "", "vuln_commit": a["vuln_commit"] if full else "",
        "fix_commit": a["fix_commit"] if full else "",
    }
    row.update({c: "" for c in FILL})
    return row


def write(path, rows):
    with open(path, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


write(OUT / "sheet-rater-A.csv", [blind_row(i) for i in order])

# rater B: stratified ~30% per tier, own shuffle
rngb = random.Random(SEED_B)
bset = []
for tier in ("FULL", "LIGHT", "PSS"):
    grp = sorted([i for i in order if i["tier"] == tier], key=lambda i: i["item_id"])
    bset += rngb.sample(grp, math.ceil(B_FRACTION * len(grp)))
rngb.shuffle(bset)
write(OUT / "sheet-rater-B.csv", [blind_row(i) for i in bset])

# key (analysis only)
key = []
for it in order:
    a = it["a"]
    key.append({"item_id": it["item_id"], "tier": it["tier"], "in_rater_B": "yes" if it in bset else "no",
                "why_included": it["why"], "finding_key": it["k"], "group_id": a["group_id"],
                "ai_class": a["class"], "ai_triage": a["triage"], "ai_pattern": a["pattern_guess"],
                "ai_pss": a["proof_system_soundness"], "acquirability": a["acquirability"],
                "holdout_flag": a["holdout_flag"], "flag": a["flag"]})
write(OUT / "key" / "KEY.csv", key)

cnt = collections.Counter(i["tier"] for i in order)
cb = collections.Counter(i["tier"] for i in bset)
why = collections.Counter(i["why"] for i in order)
inputs = ["merged/acquisition_final.csv", "merged/candidates.csv", "merged/all_findings.csv",
          "triage/SAMPLE.md", "triage/SAMPLE_delta.md"]
lines = ["# Labeling package manifest", "",
         f"- Items for rater A: **{len(order)}** (FULL {cnt['FULL']}, LIGHT {cnt['LIGHT']}, PSS {cnt['PSS']})",
         f"- Items for rater B (overlap, {int(B_FRACTION*100)}% per tier): **{len(bset)}** (FULL {cb['FULL']}, LIGHT {cb['LIGHT']}, PSS {cb['PSS']})",
         f"- Inclusion reasons: {dict(why)}",
         f"- LIKELY-NOT validation keys found in SAMPLE files: {len(ln_sample)}",
         f"- Seeds: order {SEED_ORDER}, rater-B sample {SEED_B}", "", "## Input hashes", ""]
lines += [f"- `{p}`: `{sha(B / p)}`" for p in inputs if (B / p).exists()]
(OUT / "key" / "MANIFEST.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines[:6]))
