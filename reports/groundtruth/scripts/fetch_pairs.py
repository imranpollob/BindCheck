#!/usr/bin/env python3
"""Fetch the relevant source files of each strict recall case at its pinned commits.

Reads reports/groundtruth/recall-card-spec.json (hand-authored: which files are
relevant for each case) and dataset/recall-set-v2.csv (pins). Downloads raw
files from raw.githubusercontent.com into
results/raw/groundtruth/pairs/<n>/<side>/<path> and writes a receipt with the
URL, HTTP status, byte count and SHA-256 of every file.

Proposed candidate commits that are *not* in the ledger (spec field
"candidate_fixed_commit" / "candidate_vulnerable_commit") are fetched into a
separate side named "candidate-fixed" / "candidate-vulnerable" so they can
never be confused with ledger pins.

Usage: python3 -I reports/groundtruth/scripts/fetch_pairs.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC = ROOT / "reports/groundtruth/recall-card-spec.json"
LEDGER = ROOT / "dataset/recall-set-v2.csv"
OUT = ROOT / "results/raw/groundtruth/pairs"
HEX40 = set("0123456789abcdef")


def is_sha(value: str) -> bool:
    return len(value) == 40 and set(value) <= HEX40


def fetch(repo: str, commit: str, path: str, dest: pathlib.Path) -> dict:
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    rec = {"url": url, "path": path, "commit": commit}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bindcheck-groundtruth-audit"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            rec["http_status"] = resp.status
    except urllib.error.HTTPError as exc:
        rec["http_status"] = exc.code
        rec["error"] = str(exc)
        return rec
    except Exception as exc:  # network failure is recorded, never treated as absence of code
        rec["http_status"] = None
        rec["error"] = repr(exc)
        return rec
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    rec["bytes"] = len(body)
    rec["sha256"] = hashlib.sha256(body).hexdigest()
    return rec


def main() -> int:
    spec = json.loads(SPEC.read_text())
    ledger = {r["case_id"]: (i, r) for i, r in enumerate(csv.DictReader(LEDGER.open(newline="")), 1)}
    receipts = []
    for case in spec["cases"]:
        row_no, row = ledger[case["case_id"]]
        repo = case.get("repo_override") or row["repository"]
        sides = {
            "vulnerable": row["vulnerable_commit"] if row["vulnerable_commit_status"] == "resolved" else "",
            "fixed": row["fixed_commit"] if row["fixed_commit_status"] == "resolved" else "",
            "candidate-fixed": case.get("candidate_fixed_commit", ""),
            "candidate-vulnerable": case.get("candidate_vulnerable_commit", ""),
        }
        for side, commit in sides.items():
            if not commit:
                continue
            if not is_sha(commit):
                receipts.append({"row": row_no, "side": side, "commit": commit, "error": "not a 40-hex commit"})
                continue
            for path in case.get("files", []):
                rec = fetch(repo, commit, path, OUT / str(row_no) / side / path)
                rec.update({"row": row_no, "case_id": case["case_id"], "side": side, "repository": repo})
                receipts.append(rec)
                print(row_no, side, commit[:8], path, rec.get("http_status"), rec.get("bytes"))
    (OUT / "receipts.json").write_text(json.dumps(receipts, indent=1) + "\n")
    bad = [r for r in receipts if r.get("http_status") != 200]
    print(f"files={len(receipts)} non200={len(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
