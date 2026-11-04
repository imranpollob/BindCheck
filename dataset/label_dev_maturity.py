#!/usr/bin/env python3
"""Apply the recorded maturity heuristic to pinned DEV rows as well as EVAL."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import pathlib
import subprocess
import urllib.request

from collect_source_corpus import maturity


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
CORPUS = DATASET / "source-corpus.csv"
SUMMARY = DATASET / "source-corpus-summary.json"
RAW = DATASET / "raw" / "source-corpus-2026-11-03-v1" / "dev-readmes"


def readme(row):
    repo_dir = ROOT / "feasibility/work/v2/repos" / row["repository"].replace("/", "__", 1)
    if (repo_dir / ".git").exists():
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True, capture_output=True).stdout.strip()
        if head == row["commit"]:
            for name in ("README.md", "readme.md", "Readme.md", "README"):
                path = repo_dir / name
                if path.exists():
                    return path.read_text(errors="replace"), name
    for name in ("README.md", "readme.md", "Readme.md", "README"):
        url = f"https://raw.githubusercontent.com/{row['repository']}/{row['commit']}/{name}"
        try:
            request = urllib.request.Request(url, headers={"user-agent": "BindCheck-dataset/1"})
            return urllib.request.urlopen(request, timeout=20).read().decode(errors="replace"), name
        except Exception:
            pass
    return "", ""


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with CORPUS.open(newline="") as handle:
        reader = csv.DictReader(handle); fields = reader.fieldnames; rows = list(reader)
    cache = {}
    for row in rows:
        if row["split"] != "DEV":
            continue
        key = (row["repository"], row["commit"])
        if key not in cache:
            cache[key] = readme(row)
        text, path = cache[key]
        safe = row["repository"].replace("/", "__") + "--" + row["commit"][:12] + ".md"
        if text:
            (RAW / safe).write_text(text)
        label, basis = maturity({}, text, set(row["query_provenance"].split("|")))
        row["maturity"], row["maturity_basis"] = label, basis
        row["readme_path"] = path
        row["readme_sha256"] = hashlib.sha256(text.encode()).hexdigest() if text else ""
    with CORPUS.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)
    summary = json.loads(SUMMARY.read_text())
    summary["maturity_counts"] = dict(sorted(collections.Counter(row["maturity"] for row in rows).items()))
    summary["dev_maturity_counts"] = dict(sorted(collections.Counter(row["maturity"] for row in rows if row["split"] == "DEV").items()))
    summary["eval_maturity_counts"] = dict(sorted(collections.Counter(row["maturity"] for row in rows if row["split"] == "EVAL").items()))
    summary["output_sha256"] = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"dev_maturity_counts": summary["dev_maturity_counts"], "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
