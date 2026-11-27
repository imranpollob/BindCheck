#!/usr/bin/env python3
"""Capture the immutable D1P-14B baseline before prospective D1P-14C edits."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RAW_B = ROOT / "results/raw/D1P-14B"
RAW_C = ROOT / "results/raw/D1P-14C"
SNAPSHOT = RAW_C / "preserved-d1p14b-source"
OUTPUT = RAW_C / "d1p14b-preservation-baseline.json"
SOURCES = [
    ROOT / "src/bindcheck_d1/joint_warptoad.py",
    ROOT / "scripts/d1p_14b_joint_encoder.py",
    ROOT / "tests/d1/test_joint_warptoad.py",
]
TRACKED = [
    ROOT / "metadata/d1/d1p-14b-artifact-manifest.json",
    ROOT / "protocols/d1/d1p-14b-joint.json",
    ROOT / "reports/D1P-14B.md",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def record(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)), "sha256": digest(path),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    if OUTPUT.exists() or RAW_C.exists():
        raise SystemExit("D1P-14C namespace is not fresh")
    SNAPSHOT.mkdir(parents=True)
    raw_files = sorted(path for path in RAW_B.rglob("*") if path.is_file())
    aggregate = hashlib.sha256()
    raw_bytes = 0
    for path in raw_files:
        relative = str(path.relative_to(RAW_B))
        item_hash = digest(path)
        size = path.stat().st_size
        aggregate.update(f"{relative}\0{item_hash}\0{size}\n".encode())
        raw_bytes += size
    source_records = []
    for source in SOURCES:
        destination = SNAPSHOT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_records.append({
            "live": record(source), "snapshot": record(destination),
            "exact_copy": digest(source) == digest(destination),
        })
    payload = {
        "schema": "bindcheck.d1p14c.d1p14b-preservation/v1",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "d1p14b_raw_tree": {
            "path": "results/raw/D1P-14B", "file_count": len(raw_files),
            "regular_file_bytes": raw_bytes,
            "ordered_path_hash_size_sha256": aggregate.hexdigest(),
        },
        "tracked_evidence": [record(path) for path in TRACKED],
        "frozen_source_inputs": source_records,
        "d1p14b_manifest_expected_source_hashes": {
            "src/bindcheck_d1/joint_warptoad.py": "be74f98e3aa1fb40c9e4f514f0d866676001f45c3f37abf3f93f15afac24d93c",
            "scripts/d1p_14b_joint_encoder.py": "edb9b77c1237dcf6861790e272f0300a44dac03dbac1ff5277a8b57e2a0dd29e",
            "tests/d1/test_joint_warptoad.py": "788ae5b6c1ca40a56f5145beb830d262d80b08a1ad457e610a911856f8060ff1",
        },
        "git_status_before_d1p14c": subprocess.run(
            ["git", "status", "--short"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        ).stdout.splitlines(),
    }
    payload["all_source_snapshots_exact"] = all(
        item["exact_copy"] for item in source_records
    )
    temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, OUTPUT)


if __name__ == "__main__":
    main()
