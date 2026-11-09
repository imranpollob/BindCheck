#!/usr/bin/env python3
"""Read-only census of verifier paths in the entire pinned source corpus.

This is a passive source download/classification, never an analyzer run.
Every inventory entry is retained, including unavailable source and paths that
do not contain a verifier function. Labels describe source shapes only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import PLAN_SOURCE_SHA256, ROOT, SOURCE_LEDGER, atomic_write_json, sha256_file
from eval.verifier_census import classify_verifier


FIELDS = (
    "corpus_line", "split", "repository", "commit", "verifier_path", "inventory_basis", "source_url",
    "fetch_status", "source_sha256", "source_cache", "contract", "function",
    "line", "generator", "range_class", "public_input_arity", "guarded_positions",
    "behavior", "evidence_json",
)
MAX_BYTES = 8 * 1024 * 1024


def inventory(path: pathlib.Path, dev_checkouts: pathlib.Path) -> tuple[int, list[dict[str, str]], int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    items: list[dict[str, str]] = []
    supplement_count = 0
    excluded = {".git", "node_modules", "artifacts", "build", "dist", "out", "cache", "target", "vendor", ".venv", "venv"}
    for line, row in enumerate(rows, 2):
        # v2 paths supersede v1 paths; using the union would double-count
        # known superseded candidate names on preserved DEV rows.
        paths = (row.get("v2_verifier_paths") or row.get("verifier_paths") or "").split("|")
        recorded = list(dict.fromkeys(path for path in paths if path))
        supplement: list[str] = []
        if row["split"] == "DEV":
            index = line - 1
            row_id = f"DEV-F{index:02d}" if index <= 50 else f"DEV-H{index-50:02d}"
            matches = list(dev_checkouts.glob(f"{row_id}--*--{row['commit'][:12]}"))
            if len(matches) != 1:
                raise RuntimeError(f"DEV checkout missing or ambiguous: {row_id}")
            checkout = matches[0]
            observed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout,
                                      capture_output=True, text=True, check=False)
            if observed.returncode != 0 or observed.stdout.strip() != row["commit"]:
                raise RuntimeError(f"DEV checkout revision mismatch: {row_id}")
            for directory, subdirs, files in os.walk(checkout):
                subdirs[:] = [name for name in subdirs if name not in excluded]
                for filename in files:
                    if not filename.lower().endswith(".sol"):
                        continue
                    source = pathlib.Path(directory) / filename
                    try:
                        if source.is_symlink() or source.stat().st_size > MAX_BYTES:
                            continue
                        text = source.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    if re.search(r"\bcontract\s+\w+", text) and re.search(r"\bfunction\s+(?:verify\w*Proof|verify|Verify)\s*\(", text):
                        supplement.append(source.relative_to(checkout).as_posix())
        for verifier_path in [*recorded, *(path for path in sorted(set(supplement)) if path not in recorded)]:
            basis = "RECORDED" if verifier_path in recorded else "DEV_SOURCE_SUPPLEMENT"
            supplement_count += basis == "DEV_SOURCE_SUPPLEMENT"
            items.append({
                "corpus_line": str(line), "split": row["split"],
                "repository": row["repository"], "commit": row["commit"],
                "verifier_path": verifier_path, "inventory_basis": basis,
            })
    return len(rows), items, supplement_count


def source_url(repository: str, commit: str, path: str) -> str:
    return "https://raw.githubusercontent.com/" + urllib.parse.quote(repository, safe="/") + "/" + commit + "/" + urllib.parse.quote(path, safe="/")


def fetch(ref: tuple[str, str, str], cache: pathlib.Path) -> dict[str, str]:
    repository, commit, path = ref
    key = hashlib.sha256("\0".join(ref).encode()).hexdigest()
    meta_path = cache / (key + ".json")
    body_path = cache / (key + ".sol.gz")
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    url = source_url(repository, commit, path)
    status = "MISSING"
    detail = ""
    data: bytes | None = None
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "bindcheck-heldout-passive-census/1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                status, detail, data = "TOO_LARGE", f"source exceeds {MAX_BYTES} bytes", None
            else:
                status = "FETCHED"
            break
        except urllib.error.HTTPError as exc:
            status, detail = f"HTTP_{exc.code}", str(exc)
            if exc.code in {404, 410, 451}:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            status, detail = "FETCH_ERROR", f"{type(exc).__name__}: {exc}"
    if data is not None:
        with gzip.open(body_path, "wb") as handle:
            handle.write(data)
    meta = {
        "status": status, "detail": detail, "url": url,
        "source_sha256": hashlib.sha256(data).hexdigest() if data is not None else "",
        "source_cache": str(body_path) if data is not None else "",
        "bytes": len(data) if data is not None else None,
        "attempts": attempt + 1,
    }
    atomic_write_json(meta_path, meta)
    return meta


def run(output: pathlib.Path, workers: int, source_cache: pathlib.Path, dev_checkouts: pathlib.Path) -> dict:
    if sha256_file(SOURCE_LEDGER) != PLAN_SOURCE_SHA256:
        raise RuntimeError("source corpus hash differs from preregistered bytes")
    corpus_rows, entries, supplement_count = inventory(SOURCE_LEDGER, dev_checkouts)
    output.mkdir(parents=True, exist_ok=True)
    cache = source_cache
    cache.mkdir(exist_ok=True)
    refs = sorted({(item["repository"], item["commit"], item["verifier_path"]) for item in entries})
    fetched: dict[tuple[str, str, str], dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_refs = {executor.submit(fetch, ref, cache): ref for ref in refs}
        for index, future in enumerate(as_completed(future_refs), 1):
            ref = future_refs[future]
            try:
                fetched[ref] = future.result()
            except Exception as exc:
                fetched[ref] = {"status": "FETCH_ERROR", "detail": f"{type(exc).__name__}: {exc}",
                                "url": source_url(*ref), "source_sha256": "", "source_cache": ""}
            if index % 250 == 0:
                print(f"FETCHED_REFS\t{index}/{len(refs)}", flush=True)
    ledger: list[dict[str, str]] = []
    for entry in entries:
        ref = entry["repository"], entry["commit"], entry["verifier_path"]
        meta = fetched[ref]
        base = {**entry, "source_url": meta["url"], "fetch_status": meta["status"],
                "source_sha256": meta["source_sha256"], "source_cache": meta["source_cache"]}
        if meta["status"] != "FETCHED":
            ledger.append({**base, "evidence_json": json.dumps({"fetch_detail": meta.get("detail", "")})})
            continue
        with gzip.open(meta["source_cache"], "rb") as handle:
            body = handle.read()
        try:
            classified = classify_verifier(body.decode("utf-8", errors="replace"))
        except Exception as exc:
            ledger.append({**base, "fetch_status": "CLASSIFIER_ERROR",
                           "evidence_json": json.dumps({"error": f"{type(exc).__name__}: {exc}"})})
            continue
        if not classified:
            ledger.append({**base, "fetch_status": "NO_VERIFIER_FUNCTION"})
        for verifier in classified:
            ledger.append({**base, "contract": verifier["contract"], "function": verifier["function"],
                           "line": str(verifier["line"]), "generator": verifier["generator"],
                           "range_class": verifier["range_class"],
                           "public_input_arity": "" if verifier["public_input_arity"] is None else str(verifier["public_input_arity"]),
                           "guarded_positions": json.dumps(verifier["guarded_positions"]),
                           "behavior": verifier["behavior"],
                           "evidence_json": json.dumps(verifier["evidence"], ensure_ascii=False)})
    ledger_path = output / "per-verifier.csv"
    with ledger_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ledger)
    classified = [item for item in ledger if item.get("contract")]
    summary = {
        "schema": "bindcheck-zk.passive-verifier-census/v1",
        "recorded_utc": dt.datetime.now(dt.UTC).isoformat(),
        "source_corpus_sha256": PLAN_SOURCE_SHA256,
        "corpus_rows": corpus_rows,
        "verifier_path_entries": len(entries),
        "dev_supplement_path_entries": supplement_count,
        "distinct_source_refs": len(refs),
        "ledger_rows": len(ledger),
        "classified_verifier_functions": len(classified),
        "status_counts": dict(sorted(Counter(item["fetch_status"] for item in ledger).items())),
        "by_split": {},
        "ledger_sha256": sha256_file(ledger_path),
        "workers": workers,
        "max_source_bytes": MAX_BYTES,
    }
    for split in ("DEV", "EVAL"):
        part = [item for item in classified if item["split"] == split]
        summary["by_split"][split] = {
            "denominator": len(part),
            "generator": dict(sorted(Counter(item["generator"] for item in part).items())),
            "range_class": dict(sorted(Counter(item["range_class"] for item in part).items())),
            "behavior": dict(sorted(Counter(item["behavior"] for item in part).items())),
        }
    atomic_write_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "results/raw/heldout/verifier-census-v1")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--source-cache", type=pathlib.Path)
    parser.add_argument("--dev-checkouts", type=pathlib.Path,
                        default=pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev"))
    args = parser.parse_args()
    if not 1 <= args.workers <= 32:
        parser.error("workers must be 1..32")
    cache = args.source_cache.resolve() if args.source_cache else args.output.resolve() / "sources"
    print(json.dumps(run(args.output.resolve(), args.workers, cache, args.dev_checkouts.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
