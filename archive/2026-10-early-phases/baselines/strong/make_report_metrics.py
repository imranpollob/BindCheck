"""Score frozen synthetic labels and inventory DEV warnings without promoting UNKNOWN."""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib

from .common import ROOT, sha256_file, write_json


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _outcome(label: str, verdict: str, status: str) -> str:
    if status == "TIMEOUT":
        return "TIMEOUT"
    if status != "completed":
        return "SETUP_OR_RUN_FAILURE"
    if verdict == "UNKNOWN":
        return "UNKNOWN"
    if label == "VULNERABLE":
        return "DETECTION" if verdict == "VIOLATION" else "MISS"
    return "FALSE_ALARM" if verdict == "VIOLATION" else "NO_ALARM"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", type=pathlib.Path, required=True)
    parser.add_argument("--dev", type=pathlib.Path, required=True)
    parser.add_argument("--bindcheck", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.synthetic = args.synthetic.resolve()
    args.dev = args.dev.resolve()
    args.bindcheck = args.bindcheck.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    expected_path = ROOT / "redteam" / "adversarial" / "expected.json"
    cases = _load(expected_path)["cases"]
    bc_manifest = {item["id"]: item for item in _load(args.bindcheck / "manifest.json")["records"]}
    comparison = []
    counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    synthetic_subtool_rows = collections.defaultdict(collections.Counter)
    synthetic_native_exits = collections.defaultdict(collections.Counter)
    for case in cases:
        case_id, label, family = case["id"], case["label"], case["family"]
        line = {"id": case_id, "family": family, "expected": label}
        for arm in ("A", "B", "C"):
            path = args.synthetic / "cases" / case_id / f"{arm}.json"
            data = _load(path)
            verdict, status = data["result"]["verdict"], data["run"]["status"]
            outcome = _outcome(label, verdict, status)
            line[f"{arm}_verdict"] = verdict
            line[f"{arm}_outcome"] = outcome
            line[f"{arm}_codes"] = ";".join(item["code"] for item in data["result"]["findings"])
            line[f"{arm}_source"] = path.relative_to(ROOT).as_posix()
            counts[arm][family][(label, outcome)] += 1
            if arm == "A":
                for tool in ("custom_slither", "same_policy_foundry"):
                    synthetic_subtool_rows[tool][data.get("native", {}).get(tool, {}).get("status", "MISSING")] += 1
            if arm == "B":
                for tool, detail in data.get("native", {}).get("tools", {}).items():
                    synthetic_subtool_rows[tool][detail.get("status", "MISSING")] += 1
                    for invocation in detail.get("invocations", []):
                        synthetic_native_exits[tool][f"{invocation['exit_status']}/timeout={invocation['timed_out']}"] += 1
        record = bc_manifest[case_id]
        path = pathlib.Path(record["result_path"]) if record["result_path"] else None
        if path is not None:
            if sha256_file(path) != record["result_sha256"]:
                raise ValueError(f"BindCheck hash mismatch: {case_id}")
            data = _load(path)
            pattern_verdicts = {k: v["verdict"] for k, v in data["patterns"].items()}
            verdict = "VIOLATION" if "VIOLATION" in pattern_verdicts.values() else (
                "UNKNOWN" if "UNKNOWN" in pattern_verdicts.values() else "VERIFIED_WITHIN_SCOPE")
            status = data["run"]["status"]
        else:
            verdict = "UNKNOWN"
            status = record["run_status"]
            pattern_verdicts = {}
        outcome = _outcome(label, verdict, status)
        line["BindCheck_verdict"] = verdict
        line["BindCheck_outcome"] = outcome
        line["BindCheck_patterns"] = ";".join(f"{k}:{v}" for k, v in sorted(pattern_verdicts.items()))
        line["BindCheck_source"] = path.relative_to(ROOT).as_posix() if path else "MISSING"
        counts["BindCheck"][family][(label, outcome)] += 1
        comparison.append(line)
    with (output / "case-comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(comparison)
    dev_warnings = []
    dev_counts = {}
    picus_invocations = []
    native_tool_rows = collections.defaultdict(collections.Counter)
    dev_native_exits = collections.defaultdict(collections.Counter)
    for arm in ("A", "B", "C"):
        manifest = _load(args.dev / f"arm-{arm}-manifest.json")
        summary = collections.Counter()
        codes = collections.Counter()
        for record in manifest["records"]:
            result_path = ROOT / record["result_path"]
            if sha256_file(result_path) != record["result_sha256"]:
                raise ValueError(f"DEV manifest hash mismatch: {result_path}")
            result = _load(result_path)
            summary[(result["run"]["status"], result["result"]["verdict"])] += 1
            if arm == "A":
                for tool in ("custom_slither", "same_policy_foundry"):
                    native_tool_rows[tool][result.get("native", {}).get(tool, {}).get("status", "MISSING")] += 1
            if arm == "B":
                for tool, detail in result.get("native", {}).get("tools", {}).items():
                    native_tool_rows[tool][detail.get("status", "MISSING")] += 1
                    for invocation in detail.get("invocations", []):
                        dev_native_exits[tool][f"{invocation['exit_status']}/timeout={invocation['timed_out']}"] += 1
                for invocation in result.get("native", {}).get("tools", {}).get("picus", {}).get("invocations", []):
                    picus_invocations.append({"id": record["id"],
                                              "exit_status": invocation["exit_status"],
                                              "timed_out": invocation["timed_out"],
                                              "temp_bytes_before_cleanup": invocation.get("temp_bytes_before_cleanup"),
                                              "temp_removed": invocation.get("temp_removed"),
                                              "timeout_seconds": invocation.get("timeout_seconds"),
                                              "source": record["result_path"]})
            for finding in result["result"]["findings"]:
                codes[finding["code"]] += 1
                dev_warnings.append({"id": record["id"], "arm": arm, "code": finding["code"],
                                     "author_opinion": "UNCONFIRMED_SOURCE_PATTERN",
                                     "human_review_required": "true", "source": record["result_path"]})
        dev_counts[arm] = {"rows": len(manifest["records"]),
                           "status_verdict": {f"{a}/{b}": n for (a, b), n in sorted(summary.items())},
                           "warning_instances_by_code": dict(sorted(codes.items())),
                           "warning_instances": len([r for r in dev_warnings if r["arm"] == arm])}
    with (output / "dev-warning-opinions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "arm", "code", "author_opinion", "human_review_required", "source"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(dev_warnings)
    summary = {
        "schema": "bindcheck-redteam.report-metrics/v1",
        "sources": {"expected": expected_path.relative_to(ROOT).as_posix(),
                    "expected_sha256": sha256_file(expected_path),
                    "synthetic": str(args.synthetic), "dev": str(args.dev), "bindcheck": str(args.bindcheck)},
        "cases_present": len(cases),
        "synthetic_by_family": {
            arm: {family: {f"{label}/{outcome}": n for (label, outcome), n in sorted(counter.items())}
                  for family, counter in sorted(families.items())}
            for arm, families in sorted(counts.items())},
        "synthetic_subtool_row_statuses": {tool: dict(sorted(counter.items())) for tool, counter in sorted(synthetic_subtool_rows.items())},
        "synthetic_native_invocation_exits": {tool: dict(sorted(counter.items())) for tool, counter in sorted(synthetic_native_exits.items())},
        "dev": dev_counts,
        "dev_native_tool_row_statuses": {tool: dict(sorted(counter.items())) for tool, counter in sorted(native_tool_rows.items())},
        "dev_native_invocation_exits": {tool: dict(sorted(counter.items())) for tool, counter in sorted(dev_native_exits.items())},
        "dev_picus_invocations": picus_invocations,
        "case_comparison": "case-comparison.csv",
        "dev_warning_opinions": "dev-warning-opinions.csv",
    }
    write_json(output / "metrics.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
