#!/usr/bin/env python3
"""Render recall review cards, the gate manifest, and recall audit tables.

Inputs (all read-only):
  dataset/recall-set-v2.csv, dataset/source-corpus-v2.csv,
  reports/groundtruth/recall-card-spec.json (hand-authored proposals),
  results/raw/groundtruth/pairs/** (fetched by fetch_pairs.py),
  results/raw/groundtruth/sources/** (primary sources),
  <bindcheck-zk>/results/raw/T26/eval-metadata-07210625783a/selected-families.csv.

Outputs:
  review/recall/NN-<slug>.md, review/recall/INDEX.md
  gate/GATE-MANIFEST.csv
  reports/groundtruth/recall-audit.csv, reports/groundtruth/promoted-review.csv

Usage: python3 -I reports/groundtruth/scripts/render_recall.py --sample <selected-families.csv>
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
PAIRS = ROOT / "results/raw/groundtruth/pairs"
MAX_SIDE = 40

LANE_BRIEF_EXPOSED = {
    "zkdrops-nullifier-field-alias": "lane brief (zkDrops)",
    "semaphore-nullifier-field-alias": "lane brief (Semaphore field alias)",
    "payy-message-tail": "lane brief (Payy)",
}
# Retained development evidence directly naming the case (verified paths).
PRIOR_DEV_EVIDENCE = {
    "zkdrops-nullifier-field-alias": "results/raw/feasibility-v2/zkdrops-alias-e4-* (E4); T25 DEV-H01/H02",
    "semaphore-nullifier-field-alias": "T25 DEV-H03/H04",
    "payy-message-tail": "T15-T19 (BindCheck/results/raw), T25 DEV-H05/H06, D1P/D2 reports",
}


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def slug(case_id: str) -> str:
    tail = case_id.split("/")[-1]
    tail = re.sub(r"^(zksecurity|veridise|hashcloak|trailofbits|zellic|leastauthority)_", "", tail)
    return re.sub(r"[^a-z0-9]+", "-", tail.lower()).strip("-")[:60]


def render_source(src: dict) -> tuple[str, str]:
    """Return (markdown excerpt, provenance line). Excerpts are verbatim from local copies."""
    kind = src["type"]
    if kind == "missing":
        return "> **MISSING** — " + src["reason"], "MISSING"
    path = ROOT / src["file"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    if kind == "zkbugs":
        text = path.read_text(encoding="utf-8")
        m = re.search(r"## Short Description of the Vulnerability\s*(.*?)\s*## ", text, re.S)
        body = m.group(1).strip() if m else "MISSING (section not found)"
        loc = re.search(r"\* Location\s*\n(.*?)\n\* Source", text, re.S)
        src_link = re.search(r"Source Link: (\S+)", text)
        out = "> " + body.replace("\n", "\n> ")
        if loc:
            out += "\n>\n> zkbugs Location:\n> " + loc.group(1).strip().replace("\n", "\n> ")
        prov = f"zkbugs README @ ee4eb3ab (`{src['file']}`, sha256 {digest}…); report: {src_link.group(1) if src_link else 'MISSING'}"
        return out, prov
    if kind == "lines":
        # split on "\n" only: pdftotext emits form feeds (\x0c) that str.splitlines()
        # would count as extra lines, desynchronising from `sed -n` line numbers.
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        chunks = []
        for a, b in src["ranges"]:
            seg = [ln.replace("\x0c", "").rstrip() for ln in lines[a - 1:b]
                   if ln.strip("\x0c \t") and "Zellic ©" not in ln and "Back to Contents" not in ln
                   and "Comprehensive Security Assessment" not in ln]
            chunks.append("\n".join(seg))
        body = "\n[…]\n".join(chunks)
        ranges = ", ".join(f"{a}-{b}" for a, b in src["ranges"])
        return "```text\n" + re.sub(r"[ \t]{3,}", "  ", body) + "\n```", f"{src['label']}, pdftotext -layout lines {ranges} of `{src['file']}` (sha256 {digest}…)"
    if kind == "json":
        data = json.loads(path.read_text(encoding="utf-8"))
        body = (data.get(src["field"]) or "")[: src["chars"]]
        url = data.get(src.get("url_field", "html_url"), "")
        return "> " + body.strip().replace("\r", "").replace("\n", "\n> ") + " […]", f"{url} (API copy `{src['file']}`, sha256 {digest}…, first {src['chars']} chars)"
    if kind == "substr":
        text = path.read_text(encoding="utf-8", errors="replace")
        i = text.find(src["find"])
        body = text[i: i + src["chars"]] if i >= 0 else "MISSING (anchor text not found)"
        return "> " + body.strip() + " […]", f"{src['url']} (text extracted from HTML `{src['file']}`, sha256 {digest}…)"
    raise ValueError(kind)


def read_side(row_no: int, side: str, path: str) -> list[str] | None:
    f = PAIRS / str(row_no) / side / path
    return f.read_text(encoding="utf-8", errors="replace").splitlines() if f.is_file() else None


def map_range(old: list[str], new: list[str], a: int, b: int) -> tuple[int, int]:
    """Map 1-based old line range [a,b] to the covering range in new."""
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    starts, ends = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i2 < a - 1 or i1 > b - 1:
            continue
        if tag == "equal":
            lo, hi = max(i1, a - 1), min(i2, b)
            starts.append(j1 + (lo - i1)); ends.append(j1 + (hi - i1))
        else:
            starts.append(j1); ends.append(j2)
    if not starts:
        return a, b
    return min(starts) + 1, max(ends)


def pre(lines: list[str], start: int, end: int) -> str:
    body = "\n".join(f"{n:>4}  {lines[n - 1]}" for n in range(start, min(end, len(lines)) + 1))
    return "<pre>" + html.escape(body) + "</pre>"


def code_section(row_no: int, row: dict, case: dict) -> str:
    out = []
    fixed_side = "fixed" if row["fixed_commit_status"] == "resolved" else ("candidate-fixed" if case.get("candidate_fixed_commit") else None)
    fixed_commit = row["fixed_commit"] if fixed_side == "fixed" else case.get("candidate_fixed_commit", "")
    vuln_commit = row["vulnerable_commit"] if row["vulnerable_commit_status"] == "resolved" else ""
    if not case.get("files"):
        return "_No pinned source revision: vulnerable and fixed code are **MISSING**._\n"
    if case.get("candidate_fixed_note"):
        out.append("> **Candidate fixed commit (not a ledger pin):** " + case["candidate_fixed_note"] + "\n")
    for path in case["files"]:
        old = read_side(row_no, "vulnerable", path) if vuln_commit else None
        new = read_side(row_no, fixed_side, path) if fixed_side else None
        a, b = case.get("anchors", {}).get(path, [1, 40])
        out.append(f"#### `{path}`\n")
        if old is None:
            out.append("Vulnerable side: **MISSING**.\n")
            continue
        if b - a + 1 > MAX_SIDE and new is not None:
            diff = list(difflib.unified_diff(old, new, f"vulnerable@{vuln_commit[:8]}", f"{fixed_side}@{fixed_commit[:8]}", n=2, lineterm=""))
            shown = diff[:MAX_SIDE + 2]
            out.append(f"Large file: showing the first {len(shown)} of {len(diff)} unified-diff lines between the pinned revisions.\n")
            out.append("```diff\n" + "\n".join(shown) + "\n```\n")
            continue
        b = min(b, len(old))
        left = pre(old, a, b)
        if new is None:
            right = "<pre>MISSING (no resolved fixed commit)</pre>"
            hdr_r = "Fixed: MISSING"
        else:
            c, d = map_range(old, new, a, b)
            c, d = max(1, c), min(len(new), max(d, c))
            if d - c + 1 > MAX_SIDE:
                d = c + MAX_SIDE - 1
            right = pre(new, c, d)
            label = "Fixed" if fixed_side == "fixed" else "CANDIDATE fixed"
            hdr_r = f"{label} @ <code>{fixed_commit[:10]}</code>, lines {c}–{d}"
            same = old[a - 1:b] == new[c - 1:d]
            if same:
                hdr_r += " — <b>identical to vulnerable excerpt</b>"
        hdr_l = f"Vulnerable @ <code>{vuln_commit[:10]}</code>, lines {a}–{b}"
        out.append(f"<table><tr><th>{hdr_l}</th><th>{hdr_r}</th></tr>\n<tr><td valign=\"top\">{left}</td><td valign=\"top\">{right}</td></tr></table>\n")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True, type=pathlib.Path)
    args = ap.parse_args()

    recall = read_csv(ROOT / "dataset/recall-set-v2.csv")
    corpus = read_csv(ROOT / "dataset/source-corpus-v2.csv")
    sample = read_csv(args.sample)
    spec = {c["case_id"]: c for c in json.loads((ROOT / "reports/groundtruth/recall-card-spec.json").read_text())["cases"]}

    dev_repos = {r["repository"].lower(): r for r in corpus if r["split"] == "DEV"}
    dev_orgs = {}
    for r in corpus:
        if r["split"] == "DEV":
            dev_orgs.setdefault(r["repository"].split("/")[0].lower(), set()).add(r["repository"])
    family_of = {}
    for r in corpus:
        family_of.setdefault(r["repository"].lower(), set()).add(r["v2_family_id"])
    sampled = {s["family_id"]: s for s in sample}

    audit_rows, gate_rows, promoted_rows, index = [], [], [], []
    for n, row in enumerate(recall, 1):
        cid = row["case_id"]
        repo = row["repository"].lower()
        v1 = row["scope_class"] == "integration"
        v2 = row["v2_scope_class"] == "integration"
        promoted = v2 and not v1
        exposed_basis = []
        if repo and repo in dev_repos:
            exposed_basis.append("DEV row in source-corpus-v2 (" + repo + ")")
        if cid in PRIOR_DEV_EVIDENCE:
            exposed_basis.append(PRIOR_DEV_EVIDENCE[cid])
        if cid in LANE_BRIEF_EXPOSED:
            exposed_basis.append(LANE_BRIEF_EXPOSED[cid])
        org = repo.split("/")[0] if repo else ""
        related = sorted(r for r in dev_orgs.get(org, set()) if r.lower() != repo)
        overlap = sorted(f"rank {sampled[f]['rank']} ({sampled[f]['stratum']})" for f in family_of.get(repo, set()) if f in sampled)
        case = spec.get(cid, {})
        dsl_note = ""
        if cid == "payy-message-tail":
            dsl_note = "WRONG: Noir/Solidity (UltraHonk); see card"
        audit_rows.append({
            "row": n, "case_id": cid, "repository": row["repository"],
            "v1_scope_class": row["scope_class"], "v2_scope_class": row["v2_scope_class"],
            "v1_strict": int(v1), "v2_strict": int(v2), "promoted_v1_broader_to_v2_strict": int(promoted),
            "v2_row_origin": row["v2_row_origin"], "pair_status": row["v2_pair_status"],
            "dsl_ledger": row["dsl"], "dsl_audit": dsl_note,
            "exposed": "EXPOSED" if exposed_basis else "", "exposure_basis": "; ".join(exposed_basis),
            "related_dev_repos_same_org": "; ".join(related),
            "eval_sample_overlap": "; ".join(overlap),
            "l4_proposal": case.get("proposal", ""),
        })
        if promoted:
            promoted_rows.append({
                "row": n, "case_id": cid,
                "c1_boundary_value": case.get("boundary_value", ""),
                "c1_consumer_consequence": case.get("consumer_consequence", ""),
                "c1_fix_locus": case.get("fix_locus", ""),
                "c1_p1p5_mappable": case.get("p1p5_mappable", ""),
                "research_contract_scope": case.get("research_scope", ""),
                "proposal": case.get("proposal", ""), "rule": case.get("proposal_rule", ""),
                "card": f"review/recall/{n:02d}-{slug(cid)}.md",
            })
        if v2 and row["v2_pair_status"] == "vulnerable-and-fixed-resolved":
            gate_rows.append({
                "row": n, "case_id": cid, "repository": row["repository"],
                "vulnerable_commit": row["vulnerable_commit"], "fixed_commit": row["fixed_commit"],
                "family": next(iter(sorted(family_of.get(repo, {"NOT-IN-CORPUS"}))), "NOT-IN-CORPUS"),
                "dsl_ledger": row["dsl"], "dsl_audit": dsl_note,
                "v1_strict": int(v1), "v2_strict": int(v2), "promoted": int(promoted),
                "exposed": "EXPOSED" if exposed_basis else "", "exposure_basis": "; ".join(exposed_basis),
                "related_dev_repos_same_org": "; ".join(related), "eval_sample_overlap": "; ".join(overlap),
                "relational_class": case.get("relational_class", ""), "relational_basis": case.get("relational_basis", ""),
                "p1p5_mappable": case.get("p1p5_mappable", ""),
                "proposed_expected_pattern": case.get("proposed_expected_pattern", ""),
                "proposed_location_regex": case.get("proposed_location_regex", ""),
                "l4_proposal": case.get("proposal", ""),
                "pair_concerns": " | ".join(case.get("concerns", [])),
                "card": f"review/recall/{n:02d}-{slug(cid)}.md",
            })
        if not v2:
            continue

        # ---------- card ----------
        srcs = [render_source(s) for s in case.get("source", [])]
        expo = "**EXPOSED** — " + "; ".join(exposed_basis) if exposed_basis else "not exposed by C2"
        if related:
            expo += f"; RELATED DEV repos in same org: {', '.join(related)}"
        if overlap:
            expo += f"; **SAMPLE-OVERLAP** with 278-family EVAL draw: {', '.join(overlap)}"
        vlink = f"[{row['vulnerable_commit'][:10]}](https://github.com/{row['repository']}/tree/{row['vulnerable_commit']})" if row["vulnerable_commit_status"] == "resolved" else f"MISSING ({row['vulnerable_commit_status']})"
        flink = f"[{row['fixed_commit'][:10]}](https://github.com/{row['repository']}/tree/{row['fixed_commit']})" if row["fixed_commit_status"] == "resolved" else f"MISSING ({row['fixed_commit_status']})"
        lines = [
            f"# Recall card {n:02d} — {slug(cid)}",
            "",
            f"`{cid}`",
            "",
            "| Field | Value |", "|---|---|",
            f"| Repository | {row['repository'] or 'MISSING'} |",
            f"| DSL (ledger) | {row['dsl']}{' — **' + dsl_note + '**' if dsl_note else ''} |",
            f"| Ledger pattern / impact | {row['pattern']} / {row['impact']} |",
            f"| Class v1 → v2 | `{row['scope_class']}` → `{row['v2_scope_class']}`{' (**promoted**)' if promoted else ''} |",
            f"| Vulnerable → fixed | {vlink} → {flink} |",
            f"| Exposure | {expo} |",
            f"| L4 proposal | **{case.get('proposal', '')}** |",
            "",
            "## 1. Source report (verbatim)",
            "",
        ]
        for body, prov in srcs:
            lines += [body, "", f"<sub>Source: {prov}</sub>", ""]
        lines += ["## 2. Vulnerable vs fixed code", "", code_section(n, row, case), ""]
        lines += [
            "## 3. L4 analysis (proposal, not a decision)", "",
            f"- **Boundary value:** {case.get('boundary_value', '')}",
            f"- **Consumer consequence:** {case.get('consumer_consequence', '')}",
            f"- **Fix locus:** {case.get('fix_locus', '')}",
            f"- **P1–P5 mappable:** {case.get('p1p5_mappable', '')}",
            f"- **Research-contract scope:** {case.get('research_scope', '')}",
            f"- **Relational class:** {case.get('relational_class', '')} — {case.get('relational_basis', '')}",
            f"- **Proposed expected pattern:** `{case.get('proposed_expected_pattern', '')}`",
            f"- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `{case.get('proposed_location_regex', '')}`",
            f"- **Location basis:** {case.get('location_basis', '')}",
        ]
        if case.get("concerns"):
            lines += ["- **Concerns:**"] + [f"  - {c}" for c in case["concerns"]]
        lines += [
            "", "## 4. Reviewer decision", "",
            "| Field | Fill in |", "|---|---|",
            "| Decision | ☐ ACCEPT  ☐ EDIT  ☐ DROP |",
            "| Strict scope (keep / demote) | |",
            "| expected_pattern (P1–P5 or NONE) | |",
            "| expected_location_regex | |",
            "| Accept candidate commit? (if shown) | ☐ yes ☐ no ☐ n/a |",
            "| Reviewer | |", "| Date | |", "| Notes | |", "",
        ]
        card_path = ROOT / f"review/recall/{n:02d}-{slug(cid)}.md"
        card_path.parent.mkdir(parents=True, exist_ok=True)
        card_path.write_text("\n".join(lines), encoding="utf-8")
        index.append((n, cid, row["v2_pair_status"], bool(exposed_basis), promoted, case.get("proposal", ""), card_path.name))

    def write(path: pathlib.Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            w = csv.DictWriter(handle, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)

    write(ROOT / "reports/groundtruth/recall-audit.csv", audit_rows)
    write(ROOT / "reports/groundtruth/promoted-review.csv", promoted_rows)
    write(ROOT / "gate/GATE-MANIFEST.csv", gate_rows)

    idx = ["# Recall review cards", "",
           "One card per `v2_scope_class == integration` row of `dataset/recall-set-v2.csv` (27).",
           "Each card is a proposal from the L4 audit lane; the decision fields are blank.", "",
           "| Row | Card | Pair | Exposed | Promoted | L4 proposal |", "|---:|---|---|---|---|---|"]
    for n, cid, pair, exp, prom, prop, name in index:
        idx.append(f"| {n} | [{name}]({name}) | {'resolved' if pair.startswith('vulnerable-and') else 'incomplete'} | {'EXPOSED' if exp else ''} | {'yes' if prom else ''} | {prop} |")
    (ROOT / "review/recall/INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(f"cards={len(index)} gate_rows={len(gate_rows)} promoted={len(promoted_rows)} audit_rows={len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
