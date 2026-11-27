#!/usr/bin/env python3
"""Check the frozen scorer, appended runs, and public PENDING boundary."""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def original(path: str) -> bytes:
    return subprocess.run(["git", "show", f"3928653:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def main() -> None:
    for path in ("benchmark/score.py", "benchmark/scoring-rules.json"):
        assert (ROOT / path).read_bytes() == original(path), path
    old = original("reports/bench/matrix.csv")
    matrix = (ROOT / "reports/bench/matrix.csv").read_bytes()
    assert matrix.startswith(old)
    rows = list(csv.DictReader(matrix.decode().splitlines()))
    f1 = [r for r in rows if r["tool"] == "BindCheck-F1" and
          r["origin"] != "public-report"]
    assert len(f1) == 52
    f2run = json.loads((RAW / "e1-freeze2-20261109/runs.json").read_text())
    assert len(f2run["records"]) == 52
    assert {r["id"] for r in f2run["records"]} == {r["case_id"] for r in f1}
    for record in f2run["records"]:
        assert record["scratch_removed"]
        for mode in ("full", "no-circuit"):
            run = record["modes"][mode]
            assert run["run_status"] == "completed" and not run["timed_out"]
            assert pathlib.Path(run["result"]).is_file()
    manifests = sorted((ROOT / "benchmark/public-triples").glob("GATE-*/manifest.json"))
    assert len(manifests) == 16
    for path in manifests:
        item = json.loads(path.read_text())
        assert item["label_status"] == "PENDING"
        assert set(item["revisions"]) == {"vulnerable", "repaired"}
        for rev in item["revisions"].values():
            assert rev["commit"] == rev["observed_head"]
            assert all("status" in rev["build"][role] for role in
                       ("circuit", "verifier", "consumer"))
    public = [r for r in rows if r["origin"] == "public-report" and
              (r["tool"].endswith("-pinned") or r["tool"] == "BindCheck-F2")]
    assert len(public) == 16 * 2 * 9
    assert all(r["label_status"] == "PENDING" and r["outcome"] == "UNKNOWN"
               and r["reason"] == "LABEL_PENDING" for r in public)
    assert len({(r["case_id"], r["side"], r["tool"]) for r in public}) == len(public)
    picus = []
    for path in (RAW / "e1-public-20261109").glob("GATE-*/*/ABC/B.json"):
        item = json.loads(path.read_text())
        picus.extend(item.get("native", {}).get("tools", {}).get("picus", {})
                     .get("invocations", []))
    assert all(run.get("temp_removed") is True for run in picus)
    result = {
        "original_matrix_sha256": digest(old),
        "frozen_prefix_identical": True,
        "scorer_and_rules_identical_to_3928653": True,
        "freeze1_case_count": len(f1),
        "freeze2_case_count": len(f2run["records"]),
        "public_manifest_count": len(manifests),
        "public_matrix_rows": len(public),
        "public_outcomes": dict(collections.Counter(r["outcome"] for r in public)),
        "picus_native_invocations_with_removed_temp": len(picus),
    }
    dest = RAW / "verification-freeze2-public-20261109.json"
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
