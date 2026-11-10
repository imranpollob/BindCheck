#!/usr/bin/env python3
"""Read-only consistency audit for the E3 DEV warning cards."""

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "reports/freeze2/dev-ledger.csv"
RAW_ROOT = Path("/Users/imranpollob/Coding/bc/bindcheck-zk-coverage")
CARDS = ROOT / "review/dev-warnings"
HASH = "92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a"
LABELS = {"TRUE", "INTENDED-BEHAVIOUR", "FALSE-ALARM", "UNDECIDABLE"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = list(csv.DictReader(LEDGER.open(newline="")))
    violations = [r for r in rows if r["after_verdict"] == "VIOLATION"]
    index = (CARDS / "INDEX.md").read_text()
    found = []
    for line in index.splitlines():
        if not line.startswith("| DEV-"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        cell = cols[0].split()
        assert len(cell) == 2, line
        card_name = cols[1].split("](", 1)[1].split(")", 1)[0]
        label = cols[2]
        assert label in LABELS, line
        assert cols[3:] == ["", ""], line
        card = CARDS / card_name
        body = card.read_text()
        assert f"**AI opinion:** `{label}`" in body, card
        assert "**Human" in body and "____" in body, card
        found.append({"row": cell[0], "pattern": cell[1], "label": label,
                      "card": str(card.relative_to(ROOT)), "card_sha256": sha(card)})
    expected = {(r["row"], r["pattern"]) for r in violations}
    observed = {(r["row"], r["pattern"]) for r in found}
    assert len(found) == len(expected) and observed == expected, (expected - observed, observed - expected)
    assert len({r["card"] for r in found}) == len(found) - 1  # F34 joint card
    evidence = []
    for r in violations:
        raw = RAW_ROOT / r["after_raw"]
        data = json.loads(raw.read_text())
        assert data["tool"]["content_sha256"] == HASH, raw
        assert data["patterns"][r["pattern"]]["verdict"] == "VIOLATION", raw
        source = Path(r["repository"])
        rev = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        assert rev == r["source_revision"], (source, rev, r["source_revision"])
        evidence.append({"row": r["row"], "pattern": r["pattern"], "source_revision": rev,
                         "raw": str(raw), "raw_sha256": sha(raw)})
    result = {"schema": "bindcheck-zk.validate-audit/v1", "analyzer_sha256": HASH,
              "ledger": str(LEDGER), "ledger_sha256": sha(LEDGER),
              "violation_cells": len(violations), "cards": len({r["card"] for r in found}),
              "labels": dict(sorted(Counter(r["label"] for r in found).items())),
              "cells": found, "evidence": evidence}
    print(json.dumps(result, indent=2) + "\n", end="")


if __name__ == "__main__":
    main()
