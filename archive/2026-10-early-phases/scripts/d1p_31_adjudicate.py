#!/usr/bin/env python3
"""Post-run ground-truth adjudication for the frozen D1P-31 outputs.

This file is evaluation data, not an analyzer input.  The static run completed
before this mapping was created.  Unsupported means the required semantic fact
is outside the frozen v1 rule/frontend scope; MISS is reserved for PY-S02,
whose exact spent-key syntax is part of the advertised source-profile scope.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-31"
BENCH = ROOT / "benchmarks/binding-mutants"


MATCHED: dict[str, list[str]] = {
    "WT-C01": ["W001"],
    "WT-C02": ["W001"],
    "WT-C03": ["W001"],
    "WT-C04": ["W001", "W002"],
    "WT-C07": ["W001"],
    "WT-C08": ["W001", "W002"],
    "WT-S01": ["W001"],
    "WT-S02": ["W001"],
    "WT-S03": ["W001"],
    "WT-S09": ["W001"],
    "PY-C02": ["W001", "W002"],
    "PY-C04": ["W001"],
    "PY-C06": ["W001"],
}

UNSUPPORTED = {
    "WT-C05": "used Poseidon/Merkle argument identity and swapped hash construction are outside occurrence-only semantics",
    "WT-C06": "amount still occurs in fee/range constraints; v1 cannot prove that it reaches the note commitment dependency",
    "WT-C09": "semantic public-word identity/order comparison is not represented",
    "WT-S04": "checked extraction failed closed because the verifier boundary is absent; the fallback source profile does not support this consumer shape",
    "WT-S05": "identity of the particular admitted root-history mapping is not represented",
    "WT-S06": "the consumer fee-cap policy guard is not a v1 rule",
    "WT-S07": "the intended principal/fee beneficiary split is not supplied to or recovered by v1",
    "WT-S08": "semantic public-word identity/order comparison is not represented",
    "PY-C01": "conditional padding/gap semantics over recursive proof messages are not interpreted",
    "PY-C03": "recursive inner-proof root-chaining semantics are not interpreted",
    "PY-C05": "the private recursive verification-key allowlist is outside the public-occurrence model",
    "PY-C07": "semantic old/new-root word identity/order comparison is not represented",
    "PY-S01": "the conservative Payy source profile does not model mint-registration admission",
    "PY-S03": "the source profile does not recover per-record beneficiary word offsets",
    "PY-S04": "the source profile does not recover activation extent or record stride",
    "PY-S05": "the source profile does not recover the header-skip offset",
}

MISSES = {
    "PY-S02": (
        "R-POLARITY's advertised Payy spent-key syntax is present, but source-profile applicability is made "
        "conditional on finding the guard that the mutant removes; the remaining `.spent = true` write did "
        "not trigger a missing-guard warning"
    ),
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    manifest = json.loads((BENCH / "manifest.json").read_text())
    analysis_run = json.loads((RAW / "analysis-run.json").read_text())
    run_records = {row["target"]: row for row in analysis_run["targets"]}
    targets = []
    for mutant, truth in manifest["mutants"].items():
        analysis_path = RAW / f"analyses/{mutant}.json"
        analysis = json.loads(analysis_path.read_text())
        warnings = analysis["warnings"]
        matched = MATCHED.get(mutant, [])
        warning_ids = [warning["id"] for warning in warnings]
        if mutant in UNSUPPORTED:
            classification = "UNSUPPORTED"
            support_reason = UNSUPPORTED[mutant]
            location_match: bool | None = None
        elif mutant in MISSES:
            classification = "MISS"
            support_reason = MISSES[mutant]
            location_match = False
        else:
            classification = "DETECTED"
            support_reason = None
            location_match = True
        if classification == "DETECTED" and not matched:
            raise AssertionError(f"{mutant}: detected without matched warning")
        if any(warning_id not in warning_ids for warning_id in matched):
            raise AssertionError(f"{mutant}: matched warning missing from analysis")
        unrelated = [warning_id for warning_id in warning_ids if warning_id not in matched]
        records = []
        for warning in warnings:
            records.append({
                "id": warning["id"],
                "rule": warning["rule"],
                "location": warning["location"],
                "ground_truth_related": warning["id"] in matched,
                "explanation": warning["explanation"],
                "suggested_fix": warning["suggested_fix"],
            })
        targets.append({
            "target": mutant,
            "app": "WarpToad" if mutant.startswith("WT-") else "Payy",
            "side": "circuit" if "-C" in mutant else "consumer",
            "operator_class": truth["operator"],
            "binding_broken": truth["binding_broken"],
            "expected_effect": truth["expected_effect"],
            "ground_truth": str(BENCH / truth["readme"]),
            "classification": classification,
            "support_reason": support_reason,
            "ground_truth_location_match": location_match,
            "matched_warning_ids": matched,
            "unrelated_warning_ids": unrelated,
            "warnings": records,
            "runtime_seconds": analysis["runtime_seconds"],
            "manual_input_count": len(analysis["manual_inputs"]),
            "frontend_status": run_records[mutant]["frontend_status"],
            "frontend_reason": run_records[mutant]["frontend_reason"],
        })

    totals = {
        "targets": len(targets),
        "detected": sum(row["classification"] == "DETECTED" for row in targets),
        "misses": sum(row["classification"] == "MISS" for row in targets),
        "unsupported": sum(row["classification"] == "UNSUPPORTED" for row in targets),
        "supported_targets": sum(row["classification"] != "UNSUPPORTED" for row in targets),
        "warning_objects": sum(len(row["warnings"]) for row in targets),
        "ground_truth_related_warning_objects": sum(len(row["matched_warning_ids"]) for row in targets),
        "unrelated_warning_objects": sum(len(row["unrelated_warning_ids"]) for row in targets),
        "detected_location_matches": sum(row["ground_truth_location_match"] is True for row in targets),
    }
    if totals != {
        "targets": 30, "detected": 13, "misses": 1, "unsupported": 16,
        "supported_targets": 14, "warning_objects": 38,
        "ground_truth_related_warning_objects": 16, "unrelated_warning_objects": 22,
        "detected_location_matches": 13,
    }:
        raise AssertionError(f"unexpected totals: {totals}")

    def aggregate(key: str) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in targets:
            groups[row[key]].append(row)
        result = []
        for name in sorted(groups):
            rows = groups[name]
            result.append({
                key: name,
                "targets": len(rows),
                "detected": sum(row["classification"] == "DETECTED" for row in rows),
                "misses": sum(row["classification"] == "MISS" for row in rows),
                "unsupported": sum(row["classification"] == "UNSUPPORTED" for row in rows),
                "related_warnings": sum(len(row["matched_warning_ids"]) for row in rows),
                "unrelated_warnings": sum(len(row["unrelated_warning_ids"]) for row in rows),
                "runtime_seconds": round(sum(row["runtime_seconds"] for row in rows), 6),
            })
        return result

    d1p30_targets = []
    for name in ["warptoad-pinned", "warptoad-m-dom", "warptoad-m-src", "payy-earlier", "payy-check-added"]:
        analysis = json.loads((RAW / f"analyses/{name}.json").read_text())
        d1p30_targets.append({
            "target": name,
            "warnings": [
                {key: warning[key] for key in ("id", "rule", "location", "explanation", "suggested_fix")}
                for warning in analysis["warnings"]
            ],
            "warning_count": analysis["warning_count"],
            "runtime_seconds": analysis["runtime_seconds"],
            "manual_input_count": len(analysis["manual_inputs"]),
        })

    output = {
        "schema": "bindcheck.d1p31.adjudication/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": {
            "timing": "post-run; ground truth was not supplied to BindCheck",
            "location_criterion": "a warning names the broken semantic input/effect or consumer obligation described by the mutant markdown; literal edit-line accuracy is not scored because the ground-truth files do not provide line numbers",
            "unrelated_criterion": "a valid warning inherited from the already-vulnerable baseline but not caused by the named mutation",
            "unsupported_policy": "semantic relation absent from frozen v1 scope; never counted as a miss",
        },
        "totals": totals,
        "by_app": aggregate("app"),
        "by_operator_class": aggregate("operator_class"),
        "targets": targets,
        "d1p30_targets": d1p30_targets,
    }
    write_json(RAW / "adjudication.json", output)
    print(json.dumps({"totals": totals, "by_app": output["by_app"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
