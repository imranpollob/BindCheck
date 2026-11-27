#!/usr/bin/env python3
"""Re-run the frozen D1P-31 validation routing over D1P-34 warnings."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bindcheck_d1.validation_v1 import validate  # noqa: E402

RAW = ROOT / "results/raw/D1P-34"
INDEX = ROOT / "protocols/d1/d1p-31-validation-index.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    run = json.loads((RAW / "analysis-run.json").read_text())
    records = []
    started = time.monotonic()
    budget = 45 * 60
    for target in run["targets"]:
        if target["kind"] != "mutant" or target["status"] != "PASS":
            continue
        analysis_path = RAW / f"analyses/{target['target']}.json"
        analysis = json.loads(analysis_path.read_text())
        for warning in analysis["warnings"]:
            if time.monotonic() - started >= budget:
                break
            result = validate(f"{analysis_path}#{warning['id']}", INDEX, ROOT)
            output = RAW / f"validations/{target['target']}-{warning['id']}.json"
            write_json(output, result)
            records.append({
                "target": target["target"], "warning": warning["id"], "rule": warning["rule"],
                "status": result["status"],
                "highest_evidence_level": result["highest_evidence_level"],
                "manual_steps": result.get("manual_steps", 0),
                "validation": {"path": str(output), "sha256": sha256(output)},
            })
    write_json(RAW / "validation-run.json", {
        "schema": "bindcheck.d1p34.validation-run/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget_seconds": budget, "runtime_seconds": round(time.monotonic() - started, 6),
        "index": {"path": str(INDEX), "sha256": sha256(INDEX)},
        "counts": {"attempted": len(records),
                   "E4": sum(item["highest_evidence_level"] == "E4" for item in records),
                   "E1": sum(item["highest_evidence_level"] == "E1" for item in records)},
        "records": records,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
