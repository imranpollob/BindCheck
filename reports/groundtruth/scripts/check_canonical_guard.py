#!/usr/bin/env python3
"""Reproduce why P3 returns VERIFIED_WITHIN_SCOPE on the vulnerable zkDrops revision (DEV-H01).

Read-only use of the unmodified analyzer function bindcheck_zk.p4.canonical_guard
on a DEV file (a16z/zkdrops@4002962 contracts/compiled/MerkVerifier.sol, fetched
from raw.githubusercontent.com). No EVAL repository is touched.

Also reports, from the retained T25 output, the P3/P4 verdicts of DEV-H01..H04.

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 reports/groundtruth/scripts/check_canonical_guard.py \
      --t25 /Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/T25/after-20261106T155532Z-23564
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from bindcheck_zk import p4  # noqa: E402  (read-only import of the frozen analyzer)

URL = "https://raw.githubusercontent.com/a16z/zkdrops/4002962fb632578dd12477346d2e5c4159ffb2ef/contracts/compiled/MerkVerifier.sol"
LOCAL = ROOT / "results/raw/groundtruth/work/zkdrops-4002962fb632578dd12477346d2e5c4159ffb2ef/MerkVerifier.sol"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t25", required=True, type=pathlib.Path)
    a = ap.parse_args()
    if not LOCAL.is_file():
        LOCAL.parent.mkdir(parents=True, exist_ok=True)
        LOCAL.write_bytes(urllib.request.urlopen(URL, timeout=60).read())
    text = LOCAL.read_text(encoding="utf-8")
    pattern = r"\bcheckField\s*\([^;]*(?:inputs?|pubSignals?|publicInputs?)"  # p4.py:104, copied verbatim
    m = re.search(pattern, text, re.I)
    out = {
        "generated_by": "reports/groundtruth/scripts/check_canonical_guard.py",
        "file": URL, "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "canonical_guard": p4.canonical_guard(text),
        "matching_regex": pattern,
        "match_chars": len(m.group(0)) if m else None,
        "match_start_line": text[: m.start()].count("\n") + 1 if m else None,
        "match_end_line": text[: m.end()].count("\n") + 1 if m else None,
        "match_tail": m.group(0)[-60:] if m else None,
        "pubSignals_checkField_calls": len(re.findall(r"checkField\s*\(\s*mload\s*\(\s*add\s*\(\s*pubSignals", text)),
        "t25_rows": {},
    }
    for rid in ("DEV-H01", "DEV-H02", "DEV-H03", "DEV-H04"):
        d = json.loads((a.t25 / f"{rid}--result.json").read_text())
        t = d["triples"][0]
        out["t25_rows"][rid] = {
            "verifier_path": (t.get("verifier") or {}).get("path"),
            "P3": [t["patterns"]["P3"]["verdict"], t["patterns"]["P3"]["reason"]],
            "P4": [t["patterns"]["P4"]["verdict"], t["patterns"]["P4"]["reason"]],
            "tool_content_sha256": d["tool"]["content_sha256"],
        }
    dest = ROOT / "reports/groundtruth/canonical-guard-check.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
