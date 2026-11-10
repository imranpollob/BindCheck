#!/usr/bin/env python3
"""Audit E1 manifest, locks, matrix completeness, and Picus cleanup."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
BENCH=ROOT/"benchmark"
RAW=ROOT/"results/raw/bench"
REPORT=ROOT/"reports/bench"

def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest=load(BENCH/"manifest.json")
    cases=[load(BENCH/x["case"]) for x in manifest["cases"]]
    assert len({c["id"] for c in cases})==len(cases)
    assert all((BENCH/"cases"/c["id"]).is_dir() for c in cases)
    case_index={c["id"]:c for c in cases}
    assert len({p["pair_id"] for p in manifest["pairs"]})==len(manifest["pairs"])
    for pair in manifest["pairs"]:
        vulnerable=case_index[pair["vulnerable_case"]]
        repaired=case_index[pair["repaired_case"]]
        assert vulnerable["pair_id"]==repaired["pair_id"]==pair["pair_id"]
        if pair["origin"]=="public-report":
            assert {"vulnerable","repaired"}==set(vulnerable["revisions"])
        else:
            assert vulnerable["expected_state"]=="vulnerable"
            assert repaired["expected_state"]=="repaired"
    checked=0
    for item,c in zip(manifest["cases"],cases):
        lock=load(BENCH/item["lock"])
        assert set(lock["revisions"])==set(c["revisions"])
        for side,rev in c["revisions"].items():
            source=pathlib.Path(rev.get("source_tree") or rev.get("snapshot_root") or rev.get("source_checkout") or "")
            if not source.is_absolute():source=ROOT/source
            for f in lock["revisions"][side]:
                assert sha(source/f["path"])==f["sha256"],(c["id"],side,f["path"])
                checked+=1
    matrix=list(csv.DictReader((REPORT/"matrix.csv").open()))
    observations=[json.loads(line) for line in (RAW/"e1-observations-20261109.jsonl").read_text().splitlines()]
    expected={(o["tool"],o["case_id"],o["side"]) for o in observations}
    actual={(r["tool"],r["case_id"],r["side"]) for r in matrix}
    assert len(actual)==len(matrix)==len(observations)==len(expected)
    assert actual==expected
    allowed={"DETECT","MISS","FALSE-ALARM","CLEAR","UNKNOWN","ERROR"}
    assert all(r["outcome"] in allowed for r in matrix)
    assert all(r["outcome"]=="UNKNOWN" for r in matrix if r["label_status"]=="PENDING")
    build={(r["case_id"],r["side"]):r["status"] for r in load(RAW/"e1-build-20261109-verified/build.json")["records"]}
    assert all(r["outcome"]=="UNKNOWN" for r in matrix
               if build[r["case_id"],r["side"]] not in ("BUILD_OK","BUILD_OK_NON_GROTH16"))
    invocations=0
    for root in (RAW/"e1-synthetic-abc-20261109/cases",RAW/"e1-local-20261109"):
        for path in root.rglob("B.json"):
            detail=load(path).get("native",{}).get("tools",{}).get("picus",{})
            for item in detail.get("invocations",[]):
                invocations+=1
                assert item.get("temp_removed") is True
                assert not pathlib.Path(item["temp_path"]).exists()
    assert not (RAW/"zkfuzz-setup-20261109/src").exists()
    result={"schema":"bindcheck-benchmark.verification/v1","cases":len(cases),
            "locked_files_checked":checked,"matrix_rows":len(matrix),
            "picus_invocations_cleaned":invocations,"passed":True}
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
