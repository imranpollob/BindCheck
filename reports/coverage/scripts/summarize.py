#!/usr/bin/env python3
"""Deterministic before/after accounting for two retained DEV result runs."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib


PATTERNS = ("P1", "P2", "P3", "P4", "P5")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: pathlib.Path) -> dict[str, dict]:
    values = {path.name.split("--", 1)[0]: json.loads(path.read_text())
              for path in root.glob("DEV-*--result.json")}
    if len(values) != 56:
        raise ValueError(f"expected 56 DEV results in {root}, found {len(values)}")
    return values


def counts(values: dict[str, dict], pattern: str) -> dict[str, int]:
    findings = [value["patterns"][pattern] for value in values.values()]
    applicable = [finding for finding in findings if finding["applicability"] == "APPLICABLE"]
    verdicts = collections.Counter(finding["verdict"] for finding in applicable)
    return {
        "rows": len(findings),
        "applicable": len(applicable),
        "decided": verdicts["VIOLATION"] + verdicts["VERIFIED_WITHIN_SCOPE"],
        "VIOLATION": verdicts["VIOLATION"],
        "VERIFIED_WITHIN_SCOPE": verdicts["VERIFIED_WITHIN_SCOPE"],
        "UNKNOWN": verdicts["UNKNOWN"],
        "not_applicable": sum(f["applicability"] == "NOT_APPLICABLE" for f in findings),
        "unknown_applicability": sum(f["applicability"] == "UNKNOWN" for f in findings),
    }


def build_counts(values: dict[str, dict]) -> dict[str, int]:
    builds = [item.get("record") or {} for value in values.values()
              for item in value["coverage"]["builds"]]
    return {
        "build_attempts": len(builds),
        "builds_ok": sum(record.get("kind") == "existing" or
                         (record.get("exit_status") == 0 and not record.get("timed_out")) for record in builds),
        "builds_failed_or_timed_out": sum(record.get("kind") != "existing" and
                                          (record.get("exit_status") != 0 or record.get("timed_out")) for record in builds),
        "build_timeouts": sum(bool(record.get("timed_out")) for record in builds),
        "rows_with_triples": sum(bool(value["triples"]) for value in values.values()),
        "crashes": sum(value["run"]["status"] not in {"completed", "UNKNOWN"} or
                       value["run"].get("fatal_reason") is not None for value in values.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=pathlib.Path, required=True)
    parser.add_argument("--after", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    before, after = load(args.before), load(args.after)
    if set(before) != set(after):
        raise ValueError("DEV row identifiers differ")
    if len({value["tool"]["content_sha256"] for value in before.values()}) != 1:
        raise ValueError("before run contains multiple analyzer hashes")
    if len({value["tool"]["content_sha256"] for value in after.values()}) != 1:
        raise ValueError("after run contains multiple analyzer hashes")
    if any(before[row]["inputs"]["git_revision"] != after[row]["inputs"]["git_revision"] for row in before):
        raise ValueError("DEV source revisions differ")
    ledger = []
    changed = []
    for row in sorted(before):
        for pattern in PATTERNS:
            b, a = before[row]["patterns"][pattern], after[row]["patterns"][pattern]
            entry = {
                "row": row, "repository": after[row]["inputs"]["root"],
                "source_revision": after[row]["inputs"]["git_revision"], "pattern": pattern,
                "before_applicability": b["applicability"], "after_applicability": a["applicability"],
                "before_verdict": b["verdict"], "after_verdict": a["verdict"],
                "before_reasons": ";".join(b["reasons"]), "after_reasons": ";".join(a["reasons"]),
                "before_raw": str(args.before / f"{row}--result.json"),
                "after_raw": str(args.after / f"{row}--result.json"),
            }
            ledger.append(entry)
            if b["verdict"] != a["verdict"] or b["applicability"] != a["applicability"]:
                changed.append(entry)
    fields = list(ledger[0])
    for filename, rows in (("dev-ledger.csv", ledger), ("changed-verdicts.csv", changed)):
        with (args.out / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "before_raw": str(args.before), "after_raw": str(args.after),
        "before_manifest_sha256": sha256(args.before / "manifest.json"),
        "after_manifest_sha256": sha256(args.after / "manifest.json"),
        "before_analyzer_sha256": next(iter(before.values()))["tool"]["content_sha256"],
        "after_analyzer_sha256": next(iter(after.values()))["tool"]["content_sha256"],
        "patterns": {pattern: {"before": counts(before, pattern), "after": counts(after, pattern)}
                     for pattern in PATTERNS},
        "overall": {
            phase: {
                "applicable_pattern_rows": sum(counts(values, pattern)["applicable"] for pattern in PATTERNS),
                "decided_pattern_rows": sum(counts(values, pattern)["decided"] for pattern in PATTERNS),
            }
            for phase, values in (("before", before), ("after", after))
        },
        "builds": {"before": build_counts(before), "after": build_counts(after)},
        "changed_verdicts": len(changed),
        "changed_reasons_including_verdict_changes": sum(
            b["patterns"][p]["reasons"] != after[row]["patterns"][p]["reasons"]
            for row, b in before.items() for p in PATTERNS),
    }
    (args.out / "dev-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"changed_verdicts": len(changed), "patterns": summary["patterns"]}, sort_keys=True))


if __name__ == "__main__":
    main()
