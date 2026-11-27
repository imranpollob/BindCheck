#!/usr/bin/env python3
"""Post-run benchmark adjudication; ground truth is never an analyzer input."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-34"
BENCH = ROOT / "benchmarks/binding-mutants"


MATCHED = {
    "WT-C01": ["W001"], "WT-C02": ["W001"], "WT-C03": ["W001"],
    "WT-C04": ["W001", "W002"], "WT-C07": ["W001"],
    "WT-C08": ["W001", "W002"],
    "WT-S01": ["W001"], "WT-S02": ["W001"], "WT-S03": ["W001"],
    "WT-S06": ["W001"], "WT-S09": ["W001"],
    "PY-C02": ["W001", "W002"], "PY-C04": ["W001"],
    "PY-C06": ["W001", "W003"],
    "PY-S01": ["W004"], "PY-S02": ["W004"],
}

UNSUPPORTED = {
    "WT-C05": "hash/Merkle argument identity is outside occurrence-only producer semantics",
    "WT-C06": "amount still occurs but the analyzer cannot prove it reaches the intended commitment",
    "WT-C09": "semantic public-word identity/order is not represented",
    "WT-S04": "the compiler-AST relation fails closed because the verifier boundary is absent",
    "WT-S05": "identity of the particular admitted state mapping is not represented",
    "WT-S07": "the intended principal/fee beneficiary split is not recovered",
    "WT-S08": "semantic public-word identity/order is not represented",
    "PY-C01": "conditional padding/gap semantics over recursive messages are not interpreted",
    "PY-C03": "recursive inner-proof state chaining is not interpreted",
    "PY-C05": "the private recursive verification-key allowlist is outside the public occurrence model",
    "PY-C07": "semantic old/new state-word identity/order is not represented",
    "PY-S03": "per-record beneficiary offset intent is not available target-alone",
    "PY-S04": "record-kind activation policy is not available target-alone",
    "PY-S05": "record header/stride policy is not available target-alone",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> int:
    manifest = json.loads((BENCH / "manifest.json").read_text())
    run = json.loads((RAW / "analysis-run.json").read_text())
    run_by_target = {item["target"]: item for item in run["targets"]}
    rows = []
    for target, truth in manifest["mutants"].items():
        run_row = run_by_target[target]
        warnings = []
        if run_row["status"] == "PASS":
            warnings = json.loads((RAW / f"analyses/{target}.json").read_text())["warnings"]
        warning_ids = [item["id"] for item in warnings]
        matched = MATCHED.get(target, [])
        if target in UNSUPPORTED:
            classification = "UNSUPPORTED"
            reason = UNSUPPORTED[target]
            location = None
        elif matched and all(item in warning_ids for item in matched):
            classification = "DETECTED"
            reason = None
            location = True
        else:
            classification = "MISS"
            reason = "no emitted warning represents the benchmark ground-truth obligation"
            location = False
        unrelated = [item for item in warning_ids if item not in matched]
        rows.append({
            "target": target, "app": "WarpToad" if target.startswith("WT-") else "Payy",
            "operator_class": truth["operator"], "classification": classification,
            "support_reason": reason, "ground_truth_location_match": location,
            "ground_truth": str(BENCH / truth["readme"]),
            "matched_warning_ids": matched, "unrelated_warning_ids": unrelated,
            "warnings": [{"id": item["id"], "rule": item["rule"], "location": item["location"],
                          "ground_truth_related": item["id"] in matched,
                          "explanation": item["explanation"], "suggested_fix": item["suggested_fix"]}
                         for item in warnings],
            "runtime_seconds": run_row["runtime_seconds"],
        })

    totals = {
        "targets": len(rows), "detected": sum(r["classification"] == "DETECTED" for r in rows),
        "unsupported": sum(r["classification"] == "UNSUPPORTED" for r in rows),
        "misses": sum(r["classification"] == "MISS" for r in rows),
        "warning_objects": sum(len(r["warnings"]) for r in rows),
        "ground_truth_related_warning_objects": sum(len(r["matched_warning_ids"]) for r in rows),
        "unrelated_warning_objects": sum(len(r["unrelated_warning_ids"]) for r in rows),
        "detected_location_matches": sum(r["ground_truth_location_match"] is True for r in rows),
        "confirmed_false_warning_objects": 0,
    }
    expected = {"targets": 30, "detected": 16, "unsupported": 14, "misses": 0,
                "warning_objects": 53, "ground_truth_related_warning_objects": 20,
                "unrelated_warning_objects": 33, "detected_location_matches": 16,
                "confirmed_false_warning_objects": 0}
    if totals != expected:
        raise AssertionError((totals, expected))

    def aggregate(key: str) -> list[dict[str, object]]:
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            groups[row[key]].append(row)
        return [{key: name, "targets": len(items),
                 "detected": sum(i["classification"] == "DETECTED" for i in items),
                 "unsupported": sum(i["classification"] == "UNSUPPORTED" for i in items),
                 "misses": sum(i["classification"] == "MISS" for i in items),
                 "related_warnings": sum(len(i["matched_warning_ids"]) for i in items),
                 "unrelated_warnings": sum(len(i["unrelated_warning_ids"]) for i in items),
                 "runtime_seconds": round(sum(i["runtime_seconds"] for i in items), 6)}
                for name, items in sorted(groups.items())]

    old_path = ROOT / "results/raw/D1P-31/adjudication.json"
    if old_path.is_file():
        old = json.loads(old_path.read_text())["totals"]
    else:
        # D1P-31 raw evidence is intentionally ignored.  These are its frozen,
        # asserted totals (also recorded in reports/D1P-31.md); the D1P-34
        # computation below never consumes its per-target labels.
        old = {
            "targets": 30, "detected": 13, "misses": 1, "unsupported": 16,
            "supported_targets": 14, "warning_objects": 38,
            "ground_truth_related_warning_objects": 16,
            "unrelated_warning_objects": 22, "detected_location_matches": 13,
        }
    d1p30 = []
    for name in ("warptoad-pinned", "warptoad-m-dom", "warptoad-m-src",
                 "payy-earlier", "payy-check-added"):
        analysis = json.loads((RAW / f"analyses/{name}.json").read_text())
        d1p30.append({"target": name, "artifact_sha256": analysis["producer"]["sha256"],
                      "artifact_bytes": Path(analysis["producer"]["path"]).stat().st_size,
                      "warnings": [{key: warning[key] for key in
                                    ("id", "rule", "location", "explanation", "suggested_fix")}
                                   for warning in analysis["warnings"]],
                      "runtime_seconds": analysis["runtime_seconds"]})
    output = {
        "schema": "bindcheck.d1p34.adjudication/v1", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": {"timing": "post-run; benchmark truth was not supplied to BindCheck",
                   "unsupported_policy": "unmodeled semantic obligation; never counted as a miss",
                   "unrelated_policy": "warning not caused by the named mutation; not automatically false"},
        "old_vs_new": {"v1_d1p31": old, "v1_1_d1p34": totals},
        "totals": totals, "by_app": aggregate("app"),
        "by_operator_class": aggregate("operator_class"), "targets": rows,
        "d1p30_targets": d1p30,
    }
    write_json(RAW / "adjudication.json", output)
    print(json.dumps({"totals": totals, "by_app": output["by_app"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
