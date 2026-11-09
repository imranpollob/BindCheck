#!/usr/bin/env python3
"""Rescore immutable native observations against the current case labels.

Usage: /opt/homebrew/bin/python3 benchmark/score.py --observations RUN/observations.jsonl --output RUN/scored
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark"

def read_json(path: pathlib.Path):
    return json.loads(path.read_text())

def score(case: dict, observation: dict, rules: dict) -> dict:
    reason = observation.get("reason")
    run_status = observation.get("run_status", "UNKNOWN")
    findings = observation.get("findings") or []
    target = []
    other = []
    expected = case.get("expected_pattern")
    location = case.get("expected_location_regex")
    for finding in findings:
        pattern = finding.get("pattern") or rules["finding_pattern_map"].get(finding.get("code"))
        grade = finding.get("evidence_grade", "E1")
        raw_loc = finding.get("location")
        if isinstance(raw_loc, dict):
            raw_loc = raw_loc.get("path", "") + (":" + str(raw_loc["line"]) if raw_loc.get("line") is not None else "")
        right = bool(finding.get("code") not in rules.get("excluded_finding_codes", [])
                     and grade in ("E1", "E2", "E3", "E4")
                     and expected and location and pattern == expected and raw_loc
                     and re.fullmatch(location, raw_loc))
        (target if right else other).append(finding)
    if case["label_status"] == "PENDING":
        outcome = "UNKNOWN"; reason = "LABEL_PENDING"
    elif run_status == "ERROR":
        outcome = "ERROR"; reason = reason or "TOOL_ERROR"
    elif run_status != "completed" or observation.get("verdict") == "UNKNOWN":
        outcome = "UNKNOWN"; reason = reason or run_status
    elif case["expected_state"] == "vulnerable":
        outcome = "DETECT" if target else "MISS"
    elif case["expected_state"] == "repaired":
        outcome = "FALSE-ALARM" if target else "CLEAR"
    else:
        outcome = "UNKNOWN"; reason = "PAIR_NOT_SPLIT"
    return {"tool":observation["tool"],"case_id":case["id"],"side":observation["side"],
            "origin":case["origin"],"label_status":case["label_status"],"family":case["family"],
            "expected_state":case["expected_state"],"expected_pattern":expected,
            "outcome":outcome,"reason":reason or "", "target_findings":len(target),
            "non_target_findings":len(other),
            "unsafe_certification":bool(outcome == "MISS" and observation.get("verdict") == "VERIFIED_WITHIN_SCOPE"),
            "source":observation.get("source", "")}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    rules = read_json(BENCH / "scoring-rules.json")
    manifest = read_json(BENCH / "manifest.json")
    cases = {item["id"]:read_json(BENCH / item["case"]) for item in manifest["cases"]}
    observations = [json.loads(line) for line in args.observations.read_text().splitlines() if line.strip()]
    keys = [(o["tool"],o["case_id"],o["side"]) for o in observations]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate tool/case/side observation")
    rows = []
    for obs in observations:
        case = cases[obs["case_id"]]
        if case["origin"] == "public-report":
            case = dict(case, expected_state="vulnerable" if obs["side"] == "vulnerable" else "repaired")
        rows.append(score(case,obs,rules))
    args.output.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else []
    with (args.output / "matrix.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    counts=collections.defaultdict(collections.Counter)
    for row in rows:counts[(row["label_status"],row["tool"])][row["outcome"]]+=1
    summary={f"{label}/{tool}":dict(counter) for (label,tool),counter in sorted(counts.items())}
    (args.output / "summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,sort_keys=True))

if __name__ == "__main__":main()
