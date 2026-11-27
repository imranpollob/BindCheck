"""Build self-contained, blind rater packets for set H (held-out sample) and set D (DEV).

Neutralizes tool-identifying text: every card gets a uniform warning kind (K1–K6)
and concern sentence instead of the tool's own rule statement.

Usage: python3 eval/build_rater_packet.py OUTPUT_DIR
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HELD_KEY = ROOT / "reports/heldout/warning-unblind-key.csv"
HELD_SAMPLE = ROOT / "review/heldout-sample/sample-manifest.json"
HELD_SHEET = ROOT / "review/heldout/BLIND-SHEET-rater-a.csv"
HELD_CARDS = ROOT / "review/heldout"
DEV_CARDS = ROOT / "review/warnings"
DEV_KEY = ROOT / "reports/groundtruth/warning-blind-key.csv"
DEV_CHECKOUTS = ROOT / "feasibility/work/full-dev"
DEV_RUN = ROOT / "results/raw/coverage/after-20261109T165844Z-58315"
PACKET = ROOT / "eval/rater-packet"

KINDS = {
    "K1": "Effect not bound (recipient / amount / identity / caller / call value / stored value)",
    "K2": "Replay key (nullifier) not bound to the proof",
    "K3": "Replay key aliasing through the field (no `< r` guard on the key position)",
    "K4": "Verifier lacks a public-input range check (`< r`)",
    "K5": "Verifier key forgeable (gamma = delta) or duplicate IC points",
    "K6": "Public-signal count or order mismatch",
}
SECTION = {"K1": "3 / K1", "K2": "3 / K2", "K3": "3 / K3", "K4": "3 / K4", "K5": "3 / K5", "K6": "3 / K6"}

# (regex on tool concern/reason text, kind, neutral concern sentence)
RULES = [
    (r"Gamma and delta are the same", "K5", "The verifier's gamma and delta key points are identical, so proofs can be forged."),
    (r"IC .*identical|DUPLICATE_IC", "K5", "Two IC points of the verification key are identical."),
    (r"field representatives|FIELD_ALIAS", "K3", "The verifier accepts a public signal and its field aliases (x + r) while the contract keys its replay mapping by the raw integer."),
    (r"replay key lacks a scalar-field guard|REPLAY_POSITION_FIELD_GUARD", "K3", "The public-signal position used as the replay key has no `< r` range check."),
    (r"canonical public-input field guard|CANONICALITY_GUARD", "K4", "No range check rejecting public signals `>= r` was found for every position in this verifier."),
    (r"replay key|REPLAY_KEY", "K2", "The value used as the replay (nullifier) key is not taken from, or tied to, the proof's public signals."),
    (r"public inputs but|public-vector length|ARITY|COUNT_MISMATCH|ORDER_MISMATCH", "K6", None),
    (r"caller receives|CALLER_NOT_PROVED", "K1", "The transaction sender receives or owns the effect, but the sender is not fixed by the proof."),
    (r"call value|CALL_VALUE", "K1", "The ETH value (`msg.value`) the function acts on is not fixed by the proof."),
    (r"state-write|STATE_WRITE", "K1", "A value written to contract storage after verification is not fixed by the proof."),
    (r"recipient|RECIPIENT", "K1", "The recipient of the effect is not fixed by the proof."),
    (r"amount|AMOUNT", "K1", "The amount of the effect is not fixed by the proof."),
    (r"identity|IDENTITY", "K1", "An identity the effect acts on is not fixed by the proof."),
    (r"protected effect|protected-effect|EFFECT_NOT_PROOF_BOUND|attacker-selectable", "K1",
     "A value deciding who benefits or how much (recipient, amount or identity) is not fixed by the proof."),
]


def classify(concern: str, code: str = "") -> tuple[str, str]:
    text = f"{concern} {code}"
    for pattern, kind, neutral in RULES:
        if re.search(pattern, text, re.I):
            if neutral is None:  # K6 keeps its concrete counts, which are tool-neutral
                neutral = re.sub(r"\bmatched verifier\b", "verifier", concern.strip())
                neutral = neutral.replace("generated verifier IC length", "verifier's number of IC points")
            return kind, neutral
    raise ValueError(f"unclassified warning text: {text!r}")


def slug(repo: str, commit: str) -> str:
    return f"{repo.replace('/', '__')}@{commit[:10]}"


def gh(repo: str, commit: str, path: str = "", line: str | int | None = None) -> str:
    if not path:
        return f"https://github.com/{repo}/tree/{commit}"
    anchor = f"#L{line}" if line not in (None, "", 0) else ""
    return f"https://github.com/{repo}/blob/{commit}/{path}{anchor}"


def section(text: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def family_context(triples: list[dict], repo: str, commit: str, local: set[str], src_prefix: str) -> str:
    circuits, verifiers, consumers = {}, {}, {}
    for t in triples:
        c, v, k = t.get("circuit") or {}, t.get("verifier") or {}, t.get("consumer") or {}
        if c.get("path"):
            circuits[c["path"]] = None
        if v.get("path"):
            verifiers[v["path"]] = None
        if k.get("path"):
            consumers[(k["path"], k.get("function", ""), k.get("line"))] = None
    lines = []

    def file_line(path: str, line=None, label: str = "") -> str:
        loc = f" — local copy: [`{src_prefix}/{path}`]({src_prefix}/{path})" if path in local else ""
        return f"- `{path}{':' + str(line) if line else ''}`{label} — [GitHub]({gh(repo, commit, path, line)}){loc}"

    if circuits:
        lines.append("**Circuits** (open on GitHub; count public signals per GUIDE §3 / K6):")
        lines += [file_line(p) for p in list(circuits)[:15]]
    if verifiers:
        lines.append("\n**Verifier contracts found in this project:**")
        lines += [file_line(p) for p in list(verifiers)[:15]]
    if consumers:
        lines.append("\n**Functions that call a verifier:**")
        lines += [file_line(p, ln, f" `{fn}()`") for (p, fn, ln) in list(consumers)[:15]]
    if not lines:
        lines.append("_No circuit/verifier list is available for this project; use the GitHub tree link._")
    return "\n".join(lines)


def held_cards(out: pathlib.Path) -> list[dict]:
    key = {r["card_id"]: r for r in csv.DictReader(HELD_KEY.open())}
    ids = json.loads(HELD_SAMPLE.read_text())["card_ids"]
    rows = []
    for cid in ids:
        k = key[cid]
        fam = pathlib.Path(k["raw_family_dir"].strip())
        repo, commit = k["repository"], k["commit"]
        s = slug(repo, commit)
        local: set[str] = set()
        ws = fam / "warning-sources.json"
        if ws.exists():
            for src in json.loads(ws.read_text()).get("sources", []):
                if src.get("status") == "COPIED" and src.get("retained_path"):
                    dst = out / "sources" / s / src["source_path"]
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(fam / src["retained_path"], dst)
                    local.add(src["source_path"])
        triples = []
        try:
            triples = json.loads((fam / "bindcheck-zk-raw.json").read_text()).get("triples", [])
        except (OSError, json.JSONDecodeError):
            pass
        card = (HELD_CARDS / f"{cid}.md").read_text()
        concern = section(card, "Reported concern")
        kind, neutral = classify(concern, k["reason_code"])
        path, line = k["source_path"], k["source_line"]
        prefix = f"../../sources/{s}"
        flagged_local = f" — local copy: [`{prefix}/{path}`]({prefix}/{path})" if path in local else ""
        code = section(card, "Code at reported location")
        verifier = section(card, "Matched verifier body")
        if "MISSING" in verifier:
            verifier += ("\n\n_The analysis could not show a verifier body here (it may have matched an interface). "
                         "Use the verifier list below or GitHub; see GUIDE §7._")
        text = f"""# Card {cid} (set H)

**Warning kind: {kind} — {KINDS[kind]}** (GUIDE §{SECTION[kind]})

**Concern:** {neutral}

- Project: `{repo}` at commit `{commit}` — [browse on GitHub]({gh(repo, commit)})
- Flagged location: `{path}:{line}` — [GitHub]({gh(repo, commit, path, line)}){flagged_local}

## Code at the flagged location

{code}

## Verifier the analysis matched

{verifier}

## Other files in this project

{family_context(triples, repo, commit, local, prefix)}

## Your label

Fill the row `{cid}` in `set-H/` sheet: `label` = TP / FP / unclear, `rater_reason` = one line citing file:line (GUIDE §4).
"""
        (out / "set-H/cards" / f"{cid}.md").write_text(text)
        rows.append({"warning_id": cid, "repository": repo, "commit": commit, "source_path": path,
                     "source_line": line, "kind": kind, "concern": neutral, "label": "", "rater_reason": ""})
    return rows


def dev_cards(out: pathlib.Path) -> list[dict]:
    key = {r["warning_id"]: r for r in csv.DictReader(DEV_KEY.open())}
    rows = []
    for card_path in sorted(DEV_CARDS.glob("W[0-9][0-9].md")):
        cid = card_path.stem
        text = card_path.read_text()
        m = re.search(r"Repository: `([^`]+)` @ `([0-9a-f]+)`", text)
        repo, commit = m.group(1), m.group(2)
        k = key[cid]
        path, line = k["path"], k["line"]
        s = slug(repo, commit)
        checkout = next(DEV_CHECKOUTS.glob(f"{k['row']}--*"))
        result = json.loads(next(DEV_RUN.glob(f"{k['row']}--result.json")).read_text())
        triples = result.get("triples", [])
        wanted = {path} | set(re.findall(r"`([^`]+\.(?:sol|circom))`", text))
        for t in triples:
            for part in ("circuit", "verifier", "consumer"):
                p = (t.get(part) or {}).get("path")
                if p and (part != "consumer" or p == path):
                    wanted.add(p)
        local: set[str] = set()
        for rel in sorted(wanted):
            src = checkout / rel
            if src.is_file():
                dst = out / "sources" / s / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
                local.add(rel)
        kind, neutral = classify(re.sub(r"^P\d [^:]*: ", "", re.search(r"^> (.*)$", text, re.M).group(1)), k["reason"])
        prefix = f"../../sources/{s}"
        body = re.sub(r"^- (Rule|Repository): .*\n", "", text, flags=re.M)
        body = re.sub(r"^> .*\n", "", body, flags=re.M)
        body = body.split("## Your judgment")[0].rstrip()
        body = body.replace(f"# {cid}\n", "", 1)
        flagged_local = f" — local copy: [`{prefix}/{path}`]({prefix}/{path})" if path in local else ""
        card = f"""# Card {cid} (set D)

**Warning kind: {kind} — {KINDS[kind]}** (GUIDE §{SECTION[kind]})

**Concern:** {neutral}

- Project: `{repo}` at commit `{commit}` — [browse on GitHub]({gh(repo, commit)})
- Flagged location: `{path}:{line}` — [GitHub]({gh(repo, commit, path, line)}){flagged_local}
{body}

## Other files in this project

{family_context(triples, repo, commit, local, prefix)}

## Your label

Fill the row `{cid}` in `set-D/` sheet: `label` = TP / FP / unclear, `rater_reason` = one line citing file:line (GUIDE §4).
"""
        (out / "set-D/cards" / f"{cid}.md").write_text(card)
        rows.append({"warning_id": cid, "repository": repo, "commit": commit, "source_path": path,
                     "source_line": line, "kind": kind, "concern": neutral, "label": "", "rater_reason": ""})
    return rows


def write_sheet(path: pathlib.Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    base = pathlib.Path(sys.argv[1]).resolve()
    for rater in ("A", "B"):
        out = base / f"bindcheck-labeling-rater-{rater}"
        if out.exists():
            shutil.rmtree(out)
        for sub in ("set-H/cards", "set-D/cards", "sources"):
            (out / sub).mkdir(parents=True)
        h, d = held_cards(out), dev_cards(out)
        sheet_h, sheet_d = f"LABELS-set-H-rater-{rater}.csv", f"LABELS-set-D-rater-{rater}.csv"
        write_sheet(out / "set-H" / sheet_h, h)
        write_sheet(out / "set-D" / sheet_d, d)
        shutil.copy(PACKET / "GUIDE.md", out / "GUIDE.md")
        readme = (PACKET / "README.md").read_text()
        for k, v in {"{RATER}": f"Rater {rater}", "{TOTAL}": str(len(h) + len(d)), "{N_H}": str(len(h)),
                     "{N_D}": str(len(d)), "{SHEET_H}": sheet_h, "{SHEET_D}": sheet_d}.items():
            readme = readme.replace(k, v)
        (out / "README.md").write_text(readme)
        print(rater, len(h), len(d), sum(1 for _ in (out / "sources").rglob("*") if _.is_file()))


if __name__ == "__main__":
    main()
