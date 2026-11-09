#!/usr/bin/env python3
"""Cross-reference controlling-run P4 VERIFIED_WITHIN_SCOPE locations with
verifier files whose gamma == delta == EIP-197 G2 generator (lane P audit).

Inputs (read-only):
  argv[1]  paper/zk/data/p4-g2-constant-check.json (from check_p4_g2_constant.py)
  argv[2]  controlling L1 follow-up run directory
           (.../results/raw/soundness/after-20261109T061325Z-77918)
  argv[3]  output JSON path
"""
import json
import pathlib
import sys


def walk(obj):
    if isinstance(obj, dict):
        if obj.get("pattern") == "P4" and "verdict" in obj:
            yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def main():
    check = json.loads(pathlib.Path(sys.argv[1]).read_text())
    run = pathlib.Path(sys.argv[2])
    default_files = {
        (f["row"], f["path"].split("/", 1)[1])
        for f in check["files"]
        if f["eip197"][1] == "DEFAULT_G2_GAMMA_DELTA_SOURCE_WARNING"
    }
    hits = []
    for result_file in sorted(run.glob("DEV-*--result.json")):
        row = result_file.name.split("--", 1)[0]
        data = json.loads(result_file.read_text())
        seen = set()
        for finding in walk(data):
            loc = finding.get("location") or {}
            path = loc.get("path") if isinstance(loc, dict) else None
            key = (finding["verdict"], finding["reason"], path)
            if key in seen:
                continue
            seen.add(key)
            if finding["verdict"] == "VERIFIED_WITHIN_SCOPE" and (row, path) in default_files:
                hits.append({"row": row, "path": path, "verdict": finding["verdict"],
                             "reason": finding["reason"], "result_file": str(result_file)})
    out = {
        "controlling_run": str(run),
        "default_key_files": len(default_files),
        "unsafe_p4_certifications": hits,
        "unsafe_p4_certification_files": len(hits),
        "unsafe_p4_certification_rows": sorted({h["row"] for h in hits}),
    }
    pathlib.Path(sys.argv[3]).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in out if k != "unsafe_p4_certifications"}, indent=2))


if __name__ == "__main__":
    main()
