#!/usr/bin/env python3
"""Held-out v3 guard: refuse repositories that belong to unused EVAL families.

Usage:
    python3 scripts/check_holdout.py owner/repo [owner/repo ...]

Prints one line per argument. Exit status is 0 only when every argument is ALLOWED.

A repository is FORBIDDEN when it, or its family's canonical repository or fork
root, belongs to an in-scope dataset-v2 EVAL family that is not in the spent
freeze-2 sample (reports/heldout/selected-families.csv). Those families are
reserved for the held-out v3 run and must not be read before it.
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "dataset" / "source-corpus-v2.csv"
SPENT = ROOT / "reports" / "heldout" / "selected-families.csv"


def norm(name: str) -> str:
    name = name.strip().lower()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.rstrip("/").removesuffix(".git")


def reserved_index() -> dict[str, str]:
    csv.field_size_limit(sys.maxsize)
    with SPENT.open(newline="") as handle:
        spent = {row["family_id"] for row in csv.DictReader(handle)}
    index: dict[str, str] = {}
    with CORPUS.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] != "EVAL" or row["v2_disposition"] != "in-scope":
                continue
            family = row["v2_family_id"]
            if family in spent:
                continue
            for key in ("repository", "v2_family_canonical_repository", "v2_fork_root", "fork_root"):
                value = row.get(key) or ""
                if value:
                    index[norm(value)] = family
    return index


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 2
    index = reserved_index()
    ok = True
    for arg in argv:
        family = index.get(norm(arg))
        if family:
            ok = False
            print(f"FORBIDDEN\t{arg}\treserved held-out v3 family {family}")
        else:
            print(f"ALLOWED\t{arg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
