#!/usr/bin/env python3
"""Fail if generated LaTeX or JSON differs from the tracked-source render."""

import csv
import sys

sys.dont_write_bytecode = True

from build import OUTPUT, ROOT, render


def main():
    try:
        expected = render()
        destination = ROOT / OUTPUT
        actual = {path.name for path in destination.iterdir()
                  if path.suffix in {".tex", ".json"}} if destination.is_dir() else set()
        stale = sorted(name for name, data in expected.items()
                       if name not in actual or (destination / name).read_bytes() != data)
        unexpected = sorted(actual - expected.keys())
    except (OSError, ValueError, IndexError, KeyError, csv.Error) as error:
        print(f"paper tables: {error}", file=sys.stderr)
        return 1

    for name in stale:
        print(f"stale or missing: {OUTPUT / name}", file=sys.stderr)
    for name in unexpected:
        print(f"unexpected generated file: {OUTPUT / name}", file=sys.stderr)
    if stale or unexpected:
        return 1
    print(f"Verified {len(expected)} generated files against their sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
