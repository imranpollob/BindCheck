#!/usr/bin/env python3
"""Merge per-agent audit-sweep CSVs, group duplicate findings, and write the funnel.

Usage: python3 -I dataset/audit-sweep/tools/merge.py

Outputs go to dataset/audit-sweep/merged/:

- all_reports.csv: every report row from every agent.
- all_findings.csv: every finding row, plus group_id and canonical.
- candidates.csv: canonical KEEP and BORDERLINE findings, one per group.
- dup_groups.csv: multi-row groups, for orchestrator review.
- FUNNEL.md: per-source and overall counts.

Dedup rule. Rows describing the same audit finding share a group. Two rows are
merged when they have the same protocol core name AND either their quotes
overlap strongly or their titles are similar. The canonical row is the one from
the agent that owns the original report (a firm or contest agent over a
curated-list agent), then the row with the higher decision (KEEP over
BORDERLINE over DROP). Manual overrides are read from dedup_overrides.csv when
it exists (finding_key,group_with or finding_key,SPLIT).
"""
import csv, os, re, difflib, collections, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ["firms-1", "firms-2", "firms-3", "contests", "curated", "browser", "rescreen", "rescreen2"]
OUT = BASE / "merged"
OUT.mkdir(exist_ok=True)
OWNER_RANK = {"firms-1": 0, "firms-2": 0, "firms-3": 0, "contests": 0, "browser": 1, "rescreen": 1, "rescreen2": 1, "curated": 2}
DEC_RANK = {"KEEP": 0, "BORDERLINE": 1, "DROP": 2}

STOP = {"the", "audit", "report", "security", "review", "assessment", "of", "and",
        "protocol", "smart", "contracts", "contract", "circuits", "circuit", "zk", "v1",
        "v2", "v3", "final", "network", "labs", "xyz", "finance", "update"}


def core(name: str) -> str:
    toks = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t and t not in STOP and not t.isdigit()]
    return toks[0] if toks else name.lower()


def norm(s: str) -> str:
    s = re.sub(r"-\s+", "", s or "")  # rejoin hyphenated line breaks
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load(agent, fname):
    p = BASE / agent / fname
    if not p.exists():
        return []
    with open(p, newline="") as h:
        rows = list(csv.DictReader(h))
    for r in rows:
        r["_agent"] = agent
    return rows


reports, findings = [], []
for a in AGENTS:
    reports += load(a, "reports.csv")
    findings += load(a, "findings.csv")
# screen-1 corrections from the rescreen lane
for corr in [BASE / "rescreen" / "report_corrections.csv", BASE / "rescreen2" / "report_corrections.csv"]:
  if corr.exists():
      idx = collections.defaultdict(list)
      for r in reports:
          idx[r["report_key"]].append(r)
      for c in csv.DictReader(open(corr)):
          for r in idx.get(c["report_key"], []):  # apply to whichever agent owns the row
              if c["field"] in r:
                  r[c["field"]] = c["new"]
                  r["notes"] = (r.get("notes", "") + f" | corrected by rescreen: {c['field']} {c['old']}->{c['new']}").strip(" |")
rep_by_key = {(r["_agent"], r["report_key"]): r for r in reports}
rep_any = {r["report_key"]: r for r in reports}

for f in findings:
    r = rep_by_key.get((f["_agent"], f["report_key"])) or rep_any.get(f["report_key"], {})
    proto = r.get("protocol") or f["report_key"]
    f["_core"] = core(proto)
    f["_auditor"] = (r.get("auditor_or_platform") or "").lower()
    f["_q"] = norm(f.get("quote", ""))
    f["_t"] = norm(f.get("title", ""))

# ---- grouping (union-find) ----
parent = list(range(len(findings)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def union(i, j):
    parent[find(i)] = find(j)


def similar(a, b):
    if a["_q"] and b["_q"]:
        qa, qb = a["_q"], b["_q"]
        if qa[:60] in qb or qb[:60] in qa:
            return True
        if difflib.SequenceMatcher(None, qa, qb).ratio() > 0.75:
            return True
    if a["_t"] and b["_t"] and difflib.SequenceMatcher(None, a["_t"], b["_t"]).ratio() > 0.8:
        return True
    return False


# identical finding keys from different agents are always the same finding
same_key = collections.defaultdict(list)
for i, f in enumerate(findings):
    same_key[f["finding_key"]].append(i)
for idxs in same_key.values():
    for j in idxs[1:]:
        union(idxs[0], j)

by_core = collections.defaultdict(list)
for i, f in enumerate(findings):
    by_core[f["_core"]].append(i)
for idxs in by_core.values():
    for x in range(len(idxs)):
        for y in range(x + 1, len(idxs)):
            a, b = findings[idxs[x]], findings[idxs[y]]
            if a["_agent"] == b["_agent"] and a["report_key"] == b["report_key"]:
                continue  # different findings in the same report
            if similar(a, b):
                union(idxs[x], idxs[y])

# manual overrides
ov = BASE / "merged" / "dedup_overrides.csv"
key_idx = {f["finding_key"] + "@" + f["_agent"]: i for i, f in enumerate(findings)}
if ov.exists():
    for row in csv.DictReader(open(ov)):
        k = row["finding_key"]
        if k not in key_idx:
            continue
        if row["group_with"] == "SPLIT":
            parent[key_idx[k]] = key_idx[k]
        elif row["group_with"] in key_idx:
            union(key_idx[k], key_idx[row["group_with"]])

groups = collections.defaultdict(list)
for i in range(len(findings)):
    groups[find(i)].append(i)

gid = {}
for n, (root, members) in enumerate(sorted(groups.items(), key=lambda kv: min(kv[1]))):
    members.sort(key=lambda i: (OWNER_RANK.get(findings[i]["_agent"], 3),
                                DEC_RANK.get(findings[i]["decision"], 3)))
    for rank, i in enumerate(members):
        findings[i]["group_id"] = f"G{n:04d}"
        findings[i]["canonical"] = "yes" if rank == 0 else "no"
        findings[i]["group_size"] = str(len(members))
        # best decision in group (any member KEEP -> group is KEEP candidate)
        findings[i]["group_best_decision"] = min((findings[j]["decision"] for j in members),
                                                 key=lambda d: DEC_RANK.get(d, 3))

# ---- write outputs ----
def write(path, rows, extra):
    cols = ["agent"] + [c for c in rows[0].keys() if not c.startswith("_") and c not in extra] + extra
    with open(path, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r["agent"] = r["_agent"]
            w.writerow(r)


write(OUT / "all_reports.csv", reports, [])
write(OUT / "all_findings.csv", findings, ["group_id", "group_size", "canonical", "group_best_decision"])
# rescreen disagreements: findings another agent dropped that rescreen argues are P4.
# They are kept as candidates with a flag so the human labeling guide settles the
# proof-system-soundness vs integration boundary in one place.
disputed = {}
for dis_path in [BASE / "rescreen" / "disagreements.csv", BASE / "rescreen2" / "disagreements.csv"]:
    if dis_path.exists():
        for d in csv.DictReader(open(dis_path)):
            disputed[d["finding_key"]] = d["reason"]
disputed_groups = {f["group_id"] for f in findings if f["finding_key"] in disputed}
for f in findings:
    f["flag"] = ""
    if f["group_id"] in disputed_groups:
        f["flag"] = "scope-question: " + next(disputed[x["finding_key"]] for x in findings
                                               if x["group_id"] == f["group_id"] and x["finding_key"] in disputed)[:120]
    elif f["group_best_decision"] != f["decision"]:
        f["flag"] = "agents-disagree"
cands = [f for f in findings if f["canonical"] == "yes" and
         (f["group_best_decision"] in ("KEEP", "BORDERLINE") or f["group_id"] in disputed_groups)]
write(OUT / "candidates.csv", cands, ["group_id", "group_size", "canonical", "group_best_decision", "flag"])
dups = [f for f in findings if int(f["group_size"]) > 1]
dups.sort(key=lambda f: f["group_id"])
if dups:
    write(OUT / "dup_groups.csv", dups, ["group_id", "group_size", "canonical", "group_best_decision"])

# ---- funnel ----
lines = ["# Audit sweep funnel", "", "Generated by `tools/merge.py`. Counts are before human labeling; every label is AI (`label_source=AI`).", ""]
lines += ["## Per source", "", "| Agent | Source | Reports enumerated | IN | Findings logged | KEEP | BORDERLINE | DROP |", "|---|---|---|---|---|---|---|---|"]
# rows marked "dup-of:<key>" are the same audit enumerated twice; count each audit once
reports_f = [r for r in reports if "dup-of:" not in (r.get("notes") or "")]
src_rep = collections.defaultdict(list)
for r in reports_f:
    src_rep[(r["_agent"], r.get("auditor_or_platform") or r.get("source"))].append(r)
src_find = collections.defaultdict(list)
for f in findings:
    r = rep_by_key.get((f["_agent"], f["report_key"])) or rep_any.get(f["report_key"], {})
    src_find[(r.get("_agent", f["_agent"]), r.get("auditor_or_platform") or r.get("source"))].append(f)
for k in sorted(src_rep):
    rs, fs = src_rep[k], src_find.get(k, [])
    c = collections.Counter(f["decision"] for f in fs)
    lines.append(f"| {k[0]} | {k[1]} | {len(rs)} | {sum(r['screen1']=='IN' for r in rs)} | {len(fs)} | {c['KEEP']} | {c['BORDERLINE']} | {c['DROP']} |")
c_all = collections.Counter(f["decision"] for f in findings)
lines += ["", "## Overall", "",
          f"- Unique audits enumerated (all agents; {len(reports)-len(reports_f)} dup-of rows excluded): **{len(reports_f)}**",
          f"- Reports IN scope: **{sum(r['screen1']=='IN' for r in reports_f)}**",
          f"- Finding rows logged: **{len(findings)}** (KEEP {c_all['KEEP']}, BORDERLINE {c_all['BORDERLINE']}, DROP {c_all['DROP']})",
          f"- Unique finding groups after dedup: **{len(groups)}**",
          f"- Unique candidates (canonical, best decision KEEP or BORDERLINE): **{len(cands)}**"]
cc = collections.Counter(f["group_best_decision"] for f in cands)
lines.append(f"  - KEEP: {cc['KEEP']}, BORDERLINE: {cc['BORDERLINE']}, other (scope-question rows whose best decision is DROP): {sum(v for k,v in cc.items() if k not in ('KEEP','BORDERLINE'))}")
fl = collections.Counter(f["flag"].split(":")[0] for f in cands if f["flag"])
lines.append(f"  - flagged: {dict(fl)}")
acq = collections.Counter(f["acquirability"] for f in cands if f["group_best_decision"] == "KEEP")
pat = collections.Counter(f["pattern_guess"] for f in cands if f["group_best_decision"] == "KEEP")
lang = collections.Counter((f.get("circuit_lang") or "UNKNOWN") for f in cands if f["group_best_decision"] == "KEEP")
lines += ["", "### Unique KEEP candidates by acquirability", ""] + [f"- {k or 'blank'}: {v}" for k, v in acq.most_common()]
lines += ["", "### Unique KEEP candidates by pattern guess (AI)", ""] + [f"- {k or 'blank'}: {v}" for k, v in pat.most_common()]
lines += ["", "### Unique KEEP candidates by circuit language", ""] + [f"- {k}: {v}" for k, v in lang.most_common()]
(OUT / "FUNNEL.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines[-40:]))
print(f"\nwrote {OUT}")
