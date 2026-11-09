#!/usr/bin/env python3
"""Fetch the README of every EVAL row belonging to a sampled family, at its pinned commit.

Metadata/README only: no clone, no analyzer, no on-chain or explorer request.
The README path recorded in source-corpus-v2 is used; when it is empty the
GitHub contents API `readme?ref=<commit>` endpoint is used instead.

Output: results/raw/groundtruth/readmes/<key>.md and receipts.json, where
key = sha256("repo@commit")[:16].

Usage: python3 -I reports/groundtruth/scripts/fetch_readmes.py --sample <selected-families.csv>
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "results/raw/groundtruth/readmes"


def key(repo: str, commit: str) -> str:
    return hashlib.sha256(f"{repo}@{commit}".encode()).hexdigest()[:16]


def raw_get(url: str) -> tuple[int | None, bytes | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "bindcheck-groundtruth-audit"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read(), ""
        except urllib.error.HTTPError as exc:
            return exc.code, None, str(exc)
        except Exception as exc:  # transient network errors are retried, then recorded
            err = repr(exc)
            time.sleep(2 * (attempt + 1))
    return None, None, err


def api_readme(repo: str, commit: str) -> tuple[int | None, bytes | None, str, str]:
    proc = subprocess.run(["gh", "api", f"repos/{repo}/readme?ref={commit}"], capture_output=True, text=True)
    if proc.returncode != 0:
        return None, None, "", proc.stderr.strip()[:200]
    data = json.loads(proc.stdout)
    return 200, base64.b64decode(data.get("content", "")), data.get("path", ""), ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True, type=pathlib.Path)
    a = ap.parse_args()
    with a.sample.open(newline="") as h:
        fams = {r["family_id"] for r in csv.DictReader(h)}
    with (ROOT / "dataset/source-corpus-v2.csv").open(newline="") as h:
        rows = [r for r in csv.DictReader(h) if r["split"] == "EVAL" and r["v2_family_id"] in fams]
    OUT.mkdir(parents=True, exist_ok=True)
    receipts, seen = [], set()
    for r in rows:
        ident = (r["repository"], r["commit"])
        if ident in seen:
            continue
        seen.add(ident)
        k = key(*ident)
        rec = {"repository": r["repository"], "commit": r["commit"], "key": k, "readme_path_ledger": r["readme_path"],
               "readme_sha256_ledger": r["readme_sha256"]}
        if r["readme_path"]:
            url = f"https://raw.githubusercontent.com/{r['repository']}/{r['commit']}/{urllib.parse.quote(r['readme_path'])}"
            status, body, err = raw_get(url)
            rec.update({"method": "raw", "url": url, "http_status": status, "error": err})
        else:
            status, body, path, err = api_readme(*ident)
            rec.update({"method": "api-readme", "url": f"https://api.github.com/repos/{r['repository']}/readme?ref={r['commit']}",
                        "http_status": status, "error": err, "readme_path_api": path})
        if body is not None:
            (OUT / f"{k}.md").write_bytes(body)
            rec["bytes"] = len(body)
            rec["sha256"] = hashlib.sha256(body).hexdigest()
            rec["matches_ledger_sha256"] = (rec["sha256"] == r["readme_sha256"]) if r["readme_sha256"] else None
        receipts.append(rec)
    (OUT / "receipts.json").write_text(json.dumps(receipts, indent=1) + "\n")
    ok = sum(1 for x in receipts if "sha256" in x)
    match = sum(1 for x in receipts if x.get("matches_ledger_sha256") is True)
    print(f"repos={len(receipts)} fetched={ok} matches_ledger_sha256={match}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
