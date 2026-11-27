#!/usr/bin/env python3
"""Mechanical provenance audit for the one-assertion SMT blocker."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("reduced", type=Path)
    ap.add_argument("metadata", type=Path)
    args = ap.parse_args()
    source = args.source.read_text().splitlines()
    reduced = args.reduced.read_text().splitlines()
    meta = json.loads(args.metadata.read_text())
    original_assertions = [x for x in source if x.startswith("(assert ")]
    kept_assertions = [x for x in reduced if x.startswith("(assert ")]
    assert len(kept_assertions) == 1
    assert kept_assertions[0] == original_assertions[-1]
    assert reduced[-1] == "(check-sat)"
    assert reduced[:3] == source[:3]
    src_lines = set(source)
    for line in reduced[3:-1]:
        assert line in src_lines, f"new or edited line: {line[:80]}"
        assert line.startswith(("(assert ", "(define-fun ", "(declare-const "))
    assert meta["retained_original_assertion_indices_0_based"] == [len(original_assertions) - 1]
    assert meta["source_sha256"] == sha(args.source.read_bytes())
    assert meta["query_sha256"] == sha(args.reduced.read_bytes())
    assert meta["timed_out"] and meta["wall_seconds"] >= 300
    result = {"status": "PASS", "original_assertions": len(original_assertions),
              "retained_assertions": 1, "all_retained_lines_byte_identical": True,
              "original_sha256": meta["source_sha256"], "reduced_sha256": meta["query_sha256"],
              "timeout_seconds": meta["wall_seconds"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
