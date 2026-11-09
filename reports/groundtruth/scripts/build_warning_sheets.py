#!/usr/bin/env python3
"""Verifier-kind flags and a blind adjudication sheet for the 16 retained DEV warning groups.

Groups: the 15 rows of reports/T24-warning-adjudication.csv plus the one
`retained-new` row of reports/T25-warning-adjudication.csv.

Code excerpts are read with `git show HEAD:<path>` from the retained DEV
checkouts (whose HEAD equals the T25 ledger commit), so they are the pinned
bytes even if a working tree was modified. The matched verifier set of each
group comes from the controlling T25 result JSON.

Verifier kinds (PLAN.md C6) are assigned by the L4 lane after reading each
verifier; they are recorded in VERIFIER_KIND below with the line that justifies
them. AI-assisted classification is not independent annotation.

Outputs:
  reports/groundtruth/warning-verifier-flags.csv
  reports/groundtruth/warning-blind-key.csv          (DO NOT give to raters)
  review/warnings/BLIND-SHEET-rater-a.csv, BLIND-SHEET-rater-b.csv  (identical, blank)
  review/warnings/Wnn.md, review/warnings/README.md

Usage: python3 -I reports/groundtruth/scripts/build_warning_sheets.py \
          --t25 <bindcheck-zk>/results/raw/T25/after-20261106T155532Z-23564 \
          --checkouts <bindcheck-zk>/feasibility/work/full-dev
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = 20261108

# path -> (kind, evidence quoted from the file)
VERIFIER_KIND = {
    "evm-bridge/contracts/SolDepositVerifier.sol": ("REAL", "pairing precompile staticcall present; IC constants non-placeholder"),
    "shadow-credit-network/contracts/CreditDataZKVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "smart-contracts/contracts/Verifier.sol": ("SIMPLIFIED/STAND-IN", "'Mock verification condition: If proof element a[0] == 0 && a[1] == 0, mark invalid' ... 'return true'; no pairing"),
    "projects/ZKredential/packages/zk-contracts/contracts/core/CompositeProofVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "projects/ZKredential/packages/zk-contracts/contracts/verifiers/RealestateVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "projects/ZKredential/packages/zk-proof-server/circuits/keys/PropertyFyVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "projects/ZKredential/packages/zk-proof-server/circuits/keys/RealTVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "projects/ZKredential/packages/zk-proof-server/circuits/keys/RealestateVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "contract/DarkPoolVerifier.sol": ("SIMPLIFIED/STAND-IN", "'Stub verifier' ... 'return proof.length > 0 && commitments.length > 0'"),
    "hardhat/contracts/Verifier.sol": ("PLACEHOLDER", "'This is a placeholder' VK constants 0x1234...; 'we'll accept all proofs (always return true)'"),
    "blockchain/contracts/verifier.sol": ("FAIL-CLOSED", "'verifyProof FAILS CLOSED' ... 'return false'"),
    "blockchain/contracts/zkSTARKVerifier.sol": ("FAIL-CLOSED", "'Placeholder zk-STARK verifier' ... 'FAILS CLOSED' ... 'return false'"),
    "contracts/verifiers/AgeVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "contracts/verifiers/KYCVerifier.sol": ("REAL", "pairing precompile staticcall present"),
    "contracts/verifiers/ReputationVerifier.sol": ("PLACEHOLDER+FAIL-CLOSED", "'VK constants are PLACEHOLDER'; IC0..IC6 all (1,2); 'Always returns false'"),
    "privatecrypmix/packages/contracts/contracts/Verifier.sol": ("SIMPLIFIED/STAND-IN", "'This is a simplified version'; verifyProof requires non-empty data and 'return true'; no pairing"),
    "contracts/src/Verifier.sol": ("SIMPLIFIED/STAND-IN", "'Drop-in stand-in for snarkjs ... output'; structural checks then 'return true'; no pairing"),
}


def git_show(checkout: pathlib.Path, path: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(checkout), "show", f"HEAD:{path}"], capture_output=True, text=True, check=True).stdout
    return out.split("\n")


def function_span(lines: list[str], line: int, cap: int) -> tuple[int, int]:
    """Start at the nearest 'function' at/above line; end at its matching brace (capped)."""
    start = line
    for i in range(line, 0, -1):
        if re.search(r"\bfunction\b", lines[i - 1]):
            start = i
            break
    depth, seen, end = 0, False, start
    for i in range(start, len(lines) + 1):
        depth += lines[i - 1].count("{") - lines[i - 1].count("}")
        seen = seen or "{" in lines[i - 1]
        end = i
        if seen and depth <= 0:
            break
        if i - start + 1 >= cap:
            break
    return start, end


def block(lines: list[str], a: int, b: int, lang: str) -> str:
    return f"```{lang}\n" + "\n".join(f"{n:>4}  {lines[n - 1]}" for n in range(a, b + 1)) + "\n```"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t25", required=True, type=pathlib.Path)
    ap.add_argument("--checkouts", required=True, type=pathlib.Path)
    a = ap.parse_args()

    with (ROOT / "reports/T24-warning-adjudication.csv").open(newline="") as h:
        groups = [dict(g, source="T24", group_instances=g["instances"]) for g in csv.DictReader(h)]
    with (ROOT / "reports/T25-warning-adjudication.csv").open(newline="") as h:
        t25 = list(csv.DictReader(h))
    for g in t25:
        if g["status"] == "retained-new":
            groups.append(dict(g, source="T25 retained-new", group_instances=g["after_instances"]))
    expanded = {(g["row"], g["pattern"], g["path"], g["line"]): g["after_instances"] for g in t25 if g["status"] == "retained-expanded"}
    with (ROOT / "reports/T25-full-dev-ledger.csv").open(newline="") as h:
        ledger = {r["id"]: r for r in csv.DictReader(h) if r["phase"] == "after"}
    with (ROOT / "dataset/source-corpus-v2.csv").open(newline="") as h:
        family = {(r["repository"], r["commit"]): r["v2_family_id"] for r in csv.DictReader(h)}

    flags, key = [], []
    for idx, g in enumerate(groups, 1):
        g["group_index"] = idx
        k = (g["row"], g["pattern"], g["path"], g["line"])
        g["final_instances"] = expanded.get(k, g["group_instances"])
        result = json.loads((a.t25 / f"{g['row']}--result.json").read_text())
        verifiers = set()
        for t in result["triples"]:
            p = t["patterns"].get(g["pattern"], {})
            loc = p.get("location") or {}
            if g["reason"] in (p.get("reason") or "") and loc.get("path") == g["path"] and str(loc.get("line")) == g["line"]:
                verifiers.add((t.get("verifier") or {}).get("path") or "NO-VERIFIER-MATCHED")
        g["verifiers"] = sorted(verifiers)
        kinds = [VERIFIER_KIND.get(v, ("UNCLASSIFIED", ""))[0] for v in g["verifiers"]]
        if not kinds:
            agg = "NO-TRIPLE-MATCHED"
        elif len(set(kinds)) == 1:
            agg = kinds[0]
        else:
            agg = "MIXED(" + ",".join(sorted(set(kinds))) + ")"
        non_real = any(k != "REAL" for k in kinds)
        g["agg_kind"] = agg
        flags.append({
            "group_index": idx, "source": g["source"], "row": g["row"], "repository": ledger[g["row"]]["repository"],
            "commit": ledger[g["row"]]["commit"], "pattern": g["pattern"], "reason": g["reason"], "path": g["path"],
            "line": g["line"], "function": g["function"], "instances_final": g["final_instances"],
            "author_adjudication": g["adjudication"],
            "matched_verifiers": " | ".join(g["verifiers"]),
            "verifier_kinds": " | ".join(f"{v}={VERIFIER_KIND.get(v, ('UNCLASSIFIED',''))[0]}" for v in g["verifiers"]),
            "group_verifier_kind": agg,
            "flag_non_real_verifier": int(non_real),
            "flag_all_verifiers_non_real": int(bool(kinds) and all(k != "REAL" for k in kinds)),
            "evidence": " | ".join(f"{v}: {VERIFIER_KIND.get(v, ('', 'MISSING'))[1]}" for v in g["verifiers"]),
        })

    order = list(range(len(groups)))
    random.Random(SEED).shuffle(order)
    wdir = ROOT / "review/warnings"
    wdir.mkdir(parents=True, exist_ok=True)
    sheet = []
    for pos, gi in enumerate(order, 1):
        g = groups[gi]
        bid = f"W{pos:02d}"
        lrow = ledger[g["row"]]
        checkout = next(a.checkouts.glob(f"{g['row']}--*"))
        src = git_show(checkout, g["path"])
        line = int(g["line"])
        if g["pattern"] == "P4":
            vi = next((i for i, l in enumerate(src, 1) if re.search(r"function\s+verify", l)), 1)
            s, e = function_span(src, vi, 40)
            s = max(1, min(s, 1))
            head_end = min(len(src), 12)
            main_excerpt = block(src, 1, head_end, "solidity") + "\n\n" + block(src, *function_span(src, vi, 40), "solidity")
        else:
            s, e = function_span(src, line, 45)
            main_excerpt = block(src, s, e, "solidity")
        ver_parts = []
        if g["pattern"] != "P4":
            for v in g["verifiers"][:3]:
                if v == "NO-VERIFIER-MATCHED":
                    ver_parts.append("_No verifier artifact matched._")
                    continue
                vs = git_show(checkout, v)
                vi = next((i for i, l in enumerate(vs, 1) if re.search(r"function\s+verify", l)), 1)
                a2, b2 = function_span(vs, vi, 25)
                ver_parts.append(f"`{v}` (lines {a2}–{b2}):\n\n" + block(vs, a2, b2, "solidity"))
            if len(g["verifiers"]) > 3:
                ver_parts.append(f"_{len(g['verifiers']) - 3} further matched verifier file(s) not shown: {', '.join(g['verifiers'][3:])}_")
        rule = RULES[g["reason"]]
        md = [f"# {bid}", "",
              f"- Repository: `{lrow['repository']}` @ `{lrow['commit']}`",
              f"- Location: `{g['path']}:{g['line']}` (function `{g['function']}`)",
              f"- Rule: **{g['pattern']} / {g['reason']}**", "",
              f"> {rule}", "",
              "## Code at the reported location", "", main_excerpt, ""]
        if ver_parts:
            md += ["## Verifier(s) this consumer was matched to", ""] + ver_parts + [""]
        md += ["## Your judgment", "",
               "Label **TP** if the stated narrow source property is present at this location, **FP** if it is not, "
               "**unclear** if these artifacts do not let you decide. Record the label and a one-line reason in your own "
               "copy of the sheet (`warning_id` = this card's id). A TP is not an exploit or deployment claim.", ""]
        (wdir / f"{bid}.md").write_text("\n".join(md), encoding="utf-8")
        sheet.append({
            "warning_id": bid, "family_id": family.get((lrow["repository"], lrow["commit"]), "MISSING"),
            "repository": lrow["repository"], "commit": lrow["commit"], "pattern": g["pattern"],
            "reason_code": g["reason"], "source_path": g["path"], "source_line": g["line"],
            "message": rule, "label": "", "rater_reason": "",
        })
        key.append({"warning_id": bid, "group_index": g["group_index"], "source": g["source"], "row": g["row"],
                    "pattern": g["pattern"], "reason": g["reason"], "path": g["path"], "line": g["line"],
                    "function": g["function"], "author_adjudication": g["adjudication"],
                    "instances_final": g["final_instances"], "group_verifier_kind": g["agg_kind"]})

    def write(path: pathlib.Path, rows: list[dict]) -> None:
        with path.open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    write(ROOT / "reports/groundtruth/warning-verifier-flags.csv", flags)
    write(ROOT / "reports/groundtruth/warning-blind-key.csv", sorted(key, key=lambda r: r["warning_id"]))
    write(wdir / "BLIND-SHEET-rater-a.csv", sheet)
    write(wdir / "BLIND-SHEET-rater-b.csv", sheet)
    readme = ["# Blind warning adjudication (16 DEV warning groups)", "",
              "Each `Wnn.md` card shows one retained DEV warning group: the repository at its pinned commit, the reported",
              "location, the rule's stated property, the code at that location, and the verifier(s) the consumer was matched to.",
              "Cards are in a seeded random order. They omit the tool's verdict, confidence, instance counts, the author's",
              "label and the author's reason.", "",
              "Procedure (from `eval/ADJUDICATION.md`):", "",
              "1. Each rater receives only their own copy: `BLIND-SHEET-rater-a.csv` or `BLIND-SHEET-rater-b.csv`.",
              "2. Fill `label` with exactly `TP`, `FP`, or `unclear`, and `rater_reason` with one line. Do not change `warning_id`.",
              "3. Do not exchange labels before both sheets are sealed.",
              "4. Then: `python3 eval/adjudicate.py kappa rater-a.csv rater-b.csv --output agreement.json`.", "",
              "The un-blinding key is `reports/groundtruth/warning-blind-key.csv`; do not open it before sealing.", "",
              "## Rule texts", ""]
    for r, t in RULES.items():
        readme.append(f"- **{r}** — {t}")
    readme += ["", "## Cards", ""] + [f"- [{s['warning_id']}]({s['warning_id']}.md) — `{s['repository']}` `{s['source_path']}:{s['source_line']}`" for s in sheet]
    (wdir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"groups={len(groups)} non_real={sum(f['flag_non_real_verifier'] for f in flags)} all_non_real={sum(f['flag_all_verifiers_non_real'] for f in flags)}")
    return 0


# Rule texts: the analyzer's own result messages (T25 output) for each reason code,
# prefixed by the narrow property the reason code names.
RULES = {
    "UNBOUND_EFFECT_AMOUNT": "P1 effect binding (amount): at least one protected effect role is attacker-selectable independently of the recovered verifier public vector.",
    "UNBOUND_EFFECT_RECIPIENT": "P1 effect binding (recipient): at least one protected effect role is attacker-selectable independently of the recovered verifier public vector.",
    "REPLAY_KEY_NOT_BOUND_TO_PROOF": "P3 replay key: the consumed replay key is caller-controlled but no supported binding to the verifier public inputs was recovered.",
    "FIELD_ALIAS_REPLAY_KEY": "P3 canonicality: the verifier accepts field representatives while Solidity keys replay state by an unguarded raw integer.",
    "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND": "P4 verifier invariant: no supported canonical public-input field guard (input < r) was recovered in this verifier.",
    "DUPLICATE_IC_SOURCE_WARNING": "P4 verifier invariant: two or more parsed IC (verification-key input-commitment) entries are identical.",
}

if __name__ == "__main__":
    raise SystemExit(main())
