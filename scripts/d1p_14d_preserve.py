#!/usr/bin/env python3
"""Record immutable D1P-14B/C inputs before prospective D1P-14D work."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-14D"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict[str, object]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def tree_identity(path: Path) -> dict[str, object]:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    aggregate = hashlib.sha256()
    total = 0
    for item in files:
        relative = str(item.relative_to(path))
        item_hash = sha256(item)
        size = item.stat().st_size
        aggregate.update(f"{relative}\0{item_hash}\0{size}\n".encode())
        total += size
    return {
        "path": str(path.relative_to(ROOT)),
        "file_count": len(files),
        "regular_file_bytes": total,
        "ordered_path_hash_size_sha256": aggregate.hexdigest(),
    }


def main() -> None:
    output = RAW / "d1p14bc-preservation-baseline.json"
    snapshots = RAW / "preserved-d1p14c-source"
    if output.exists() or snapshots.exists():
        raise SystemExit("D1P-14D preservation baseline already exists")
    tracked = [
        ROOT / "metadata/d1/d1p-14b-artifact-manifest.json",
        ROOT / "protocols/d1/d1p-14b-joint.json",
        ROOT / "reports/D1P-14B.md",
        ROOT / "metadata/d1/d1p-14c-artifact-manifest.json",
        ROOT / "protocols/d1/d1p-14c-joint-repair.json",
        ROOT / "reports/D1P-14C.md",
        ROOT / "results/raw/D1P-14C/parse-preflight.json",
        ROOT / "results/raw/D1P-14C/solver-ledger.json",
        ROOT / "results/raw/D1P-14C/closure.json",
        ROOT / "results/raw/D1P-14C/audit.json",
    ]
    source_inputs = [
        ROOT / "src/bindcheck_d1/joint_warptoad.py",
        ROOT / "tests/d1/test_joint_warptoad.py",
        ROOT / "scripts/d1p_14c_joint_encoder.py",
        ROOT / "scripts/d1p_14c_preserve.py",
        ROOT / "scripts/fixtures/d1p_14c_candidate_exec.ts",
    ]
    frozen_sources = []
    for source in source_inputs:
        destination = snapshots / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        frozen_sources.append({
            "live": record(source),
            "snapshot": record(destination),
            "exact_copy": source.read_bytes() == destination.read_bytes(),
        })
    payload = {
        "schema": "bindcheck.d1p14d.d1p14bc-preservation/v1",
        "prior_raw_trees": {
            "D1P-14B": tree_identity(ROOT / "results/raw/D1P-14B"),
            "D1P-14C": tree_identity(ROOT / "results/raw/D1P-14C"),
        },
        "tracked_evidence": [record(path) for path in tracked],
        "frozen_d1p14c_source_inputs": frozen_sources,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, output)


if __name__ == "__main__":
    main()
