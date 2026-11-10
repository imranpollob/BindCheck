#!/usr/bin/env python3
"""Render source-backed blind cards and blank human-rating sheets."""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import re
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.adjudicate import _warning_row, extract_warnings, write_sheet
from eval.common import EvaluationError, load_json


SEED = 20261109
RULE_TEXT = {
    "P1": "Protected recipient, amount, and state identity must be the same public input expressions or be equated by guards that dominate the protected effect on the supported path.",
    "P2": "A required live chain, consumer, or application context must be constructed into the verified public statement or equated by a guard that dominates the protected effect.",
    "P3": "A replay key must be proof bound, checked and consumed; its exact public-input position must be canonicalized by a rejecting scalar-field guard or supported local domain separation.",
    "P4": "A verifier source warning concerns parsed verification-key constants, duplicate IC points, or whether every public-input position has a recognized rejecting scalar-field guard. Source shape alone does not establish exploitability.",
    "P5": "Recovered consumer-vector count and order must agree with the verifier arity and complete circuit public-input count and semantic order.",
}


def _blind_message(message: str) -> str:
    return re.sub(r"(?i)bindcheck(?:[_-]zk)?|arm[ _-]?c\b", "the checker", message)


def verifier_body(source: str, function_name: str) -> str:
    match = re.search(rf"\bfunction\s+{re.escape(function_name)}\s*\(", source)
    if match is None:
        return "MISSING: verifier function body was not recovered"
    opening = source.find("{", match.end())
    semicolon = source.find(";", match.end())
    if opening < 0 or (semicolon >= 0 and semicolon < opening):
        return "MISSING: verifier declaration has no body"
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    return "MISSING: verifier body has unbalanced braces"


def _source(family_dir: pathlib.Path, source_path: str) -> tuple[str | None, dict[str, Any]]:
    manifest_path = family_dir / "warning-sources.json"
    if not manifest_path.is_file():
        return None, {"status": "SOURCE_MANIFEST_MISSING"}
    entries = {item["source_path"]: item for item in load_json(manifest_path).get("sources", [])}
    item = entries.get(source_path)
    if item is None:
        return None, {"status": "SOURCE_NOT_CAPTURED"}
    if item.get("status") not in {"COPIED", "HASH_MISMATCH"}:
        return None, item
    retained = family_dir / item["retained_path"]
    if not retained.is_file():
        return None, {**item, "status": "RETAINED_SOURCE_MISSING"}
    return retained.read_text(encoding="utf-8", errors="replace"), item


def _context(source: str | None, line: str) -> str:
    if source is None:
        return "MISSING: source code was not captured"
    lines = source.splitlines()
    try:
        center = int(line)
    except (TypeError, ValueError):
        return "MISSING: warning line was not recorded"
    if not 1 <= center <= len(lines):
        return "MISSING: warning line is outside the retained source"
    start, stop = max(1, center - 12), min(len(lines), center + 12)
    return "\n".join(f"{index:>5} {lines[index - 1]}" for index in range(start, stop + 1))


def _matched_verifier(family: dict[str, Any], payload: dict[str, Any], warning: dict[str, str]) -> tuple[str | None, str]:
    candidates: set[tuple[str, str]] = set()
    for triple in payload.get("triples", []) or []:
        if warning["tool"] == "bindcheck-zk":
            matched = any(_warning_row(family, item)["warning_id"] == warning["warning_id"]
                          for item in (triple.get("patterns") or {}).values())
        else:
            matched = (triple.get("consumer") or {}).get("path") == warning["source_path"]
        if matched:
            verifier = triple.get("verifier") or {}
            declarations = verifier.get("declarations") or []
            name = declarations[0].get("name", "verifyProof") if declarations else "verifyProof"
            if verifier.get("path"):
                candidates.add((str(verifier["path"]), str(name)))
    if len(candidates) == 1:
        return next(iter(candidates))
    if warning["tool"] == "arm-c" and not candidates:
        paths = {path for path in str(family.get("verifier_paths") or "").split("|") if path}
        if len(paths) == 1:
            return next(iter(paths)), "verifyProof"
    return None, "verifyProof"


def render(run_dir: pathlib.Path, card_dir: pathlib.Path, key_path: pathlib.Path) -> dict[str, Any]:
    if key_path.resolve().is_relative_to(card_dir.resolve()):
        raise EvaluationError("unblinding key must be outside the card directory")
    if card_dir.exists() and any(card_dir.iterdir()):
        raise EvaluationError(f"card directory is not empty: {card_dir}")
    warnings = extract_warnings(run_dir)
    random.Random(SEED).shuffle(warnings)
    family_dirs: dict[str, pathlib.Path] = {}
    for path in run_dir.glob("families/*/family.json"):
        family_dirs[load_json(path)["family_id"]] = path.parent
    card_dir.mkdir(parents=True, exist_ok=True)
    sheet_rows: list[dict[str, str]] = []
    keys: list[dict[str, str]] = []
    index = ["# Blind held-out warning cards", "", "Human raters should use separate blank sheets. Tool identity and confidence are omitted.", ""]
    for number, warning in enumerate(warnings, 1):
        card_id = f"W{number:04d}"
        family_dir = family_dirs[warning["family_id"]]
        family = load_json(family_dir / "family.json")
        raw_path = family_dir / "bindcheck-zk-raw.json"
        try:
            payload = load_json(raw_path) if raw_path.is_file() else {}
        except (OSError, ValueError):
            payload = {}
        verifier_path, function_name = _matched_verifier(family, payload, warning)
        if verifier_path is None and warning["source_path"].endswith(".sol"):
            verifier_path = warning["source_path"]
        location_source, location_meta = _source(family_dir, warning["source_path"])
        verifier_source, verifier_meta = _source(family_dir, verifier_path or "")
        body = verifier_body(verifier_source, function_name) if verifier_source is not None else "MISSING: matched verifier source was not captured"
        rule = RULE_TEXT.get(warning["pattern"],
                             "Native source heuristic: independently check the reported source shape, its proof relationship, and its effect before assigning a binding-flaw label.")
        warning_message = _blind_message(warning["message"])
        lines = [
            f"# Blind warning {card_id}", "",
            f"Repository: `{warning['repository']}` at `{warning['commit']}`", "",
            "## Code at reported location", "",
            f"`{warning['source_path']}:{warning['source_line']}`; retained source SHA-256: `{location_meta.get('source_sha256', 'MISSING')}`; status: `{location_meta.get('status', 'MISSING')}`", "",
            "````solidity", _context(location_source, warning["source_line"]), "````", "",
            "## Matched verifier body", "",
            f"`{verifier_path or 'MISSING'}`; retained source SHA-256: `{verifier_meta.get('source_sha256', 'MISSING')}`; status: `{verifier_meta.get('status', 'MISSING')}`", "",
            "````solidity", body, "````", "",
            "## Rule statement", "", rule, "",
            "## Reported concern", "", warning_message, "",
        ]
        (card_dir / f"{card_id}.md").write_text("\n".join(lines), encoding="utf-8")
        index.append(f"- [{card_id}]({card_id}.md)")
        sheet_rows.append({**warning, "warning_id": card_id, "reason_code": "", "message": warning_message,
                           "label": "", "rater_reason": ""})
        keys.append({"card_id": card_id, "tool": warning["tool"], "warning_id": warning["warning_id"],
                     "family_id": warning["family_id"], "repository": warning["repository"],
                     "commit": warning["commit"], "pattern": warning["pattern"],
                     "reason_code": warning["reason_code"], "source_path": warning["source_path"],
                     "source_line": warning["source_line"], "raw_family_dir": str(family_dir)})
    (card_dir / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    for rater in ("a", "b"):
        write_sheet(card_dir / f"BLIND-SHEET-rater-{rater}.csv", sheet_rows)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with key_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(keys[0]) if keys else (
            "card_id", "tool", "warning_id", "family_id", "repository", "commit", "pattern", "reason_code",
            "source_path", "source_line", "raw_family_dir"))
        writer.writeheader()
        writer.writerows(keys)
    return {"warnings": len(warnings), "cards": len(keys), "seed": SEED,
            "card_dir": str(card_dir), "unblinding_key": str(key_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=pathlib.Path)
    parser.add_argument("--cards", type=pathlib.Path, default=pathlib.Path("review/heldout"))
    parser.add_argument("--key", type=pathlib.Path, default=pathlib.Path("reports/heldout/warning-unblind-key.csv"))
    args = parser.parse_args()
    print(json.dumps(render(args.run_dir.resolve(), args.cards.resolve(), args.key.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
