#!/usr/bin/env python3
"""Normalize freeze-2 full and circuit-withheld results for the frozen scorer."""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark"


def observation(tool, case, side, result, gate=None):
    source = str(result)
    out = {"tool": tool, "case_id": case["id"], "side": side,
           "run_status": "UNKNOWN", "verdict": "UNKNOWN", "reason": None,
           "findings": [], "source": source}
    if gate:
        out["reason"] = gate
        return out
    if not result or not result.is_file():
        out["reason"] = "RESULT_MISSING"
        return out
    try:
        parsed = json.loads(result.read_text())
    except (OSError, json.JSONDecodeError):
        out["reason"] = "RESULT_PARSE_FAILED"
        return out
    expected = case.get("expected_pattern")
    if expected not in ("P1", "P2", "P3", "P4", "P5"):
        out["reason"] = "PROPERTY_UNSUPPORTED"
        return out
    p = parsed.get("patterns", {}).get(expected, {})
    out["run_status"] = parsed.get("run", {}).get("status", "UNKNOWN")
    out["verdict"] = p.get("verdict", "UNKNOWN")
    out["reason"] = (p.get("reasons") or [None])[0]
    for triple in parsed.get("triples", []):
        finding = triple.get("patterns", {}).get(expected)
        if finding and finding.get("verdict") == "VIOLATION":
            out["findings"].append({"code": finding.get("reason"),
                                    "pattern": expected, "location": finding.get("location"),
                                    "evidence_grade": finding.get("evidence_grade", "E1")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=pathlib.Path, required=True)
    ap.add_argument("--build", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    manifest = json.loads((BENCH / "manifest.json").read_text())
    cases = {x["id"]: json.loads((BENCH / x["case"]).read_text()) for x in manifest["cases"]}
    builds = {(b["case_id"], b["side"]): b for b in json.loads(args.build.read_text())["records"]}
    records = {r["id"]: r for r in json.loads(args.runs.read_text())["records"]}
    result = []
    for item in manifest["cases"]:
        case = cases[item["id"]]
        if case["origin"] == "public-report":
            continue
        side = "selected"
        build = builds[case["id"], side]
        gate = None if build["status"] in ("BUILD_OK", "BUILD_OK_NON_GROTH16") else build["status"]
        for mode, tool in (("full", "BindCheck-F2"),
                           ("no-circuit", "BindCheck-F2-no-circuit")):
            path = pathlib.Path(records[case["id"]]["modes"][mode]["result"])
            result.append(observation(tool, case, side, path, gate))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as file:
        for row in result:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    print(len(result))


if __name__ == "__main__":
    main()
