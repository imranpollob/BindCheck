#!/usr/bin/env python3
"""Derive auditable held-out ledgers from a completed, immutable EVAL run.

This is reporting only: it neither runs an analyzer nor changes a verdict.
"""

from __future__ import annotations

import csv
import json
import pathlib
import statistics
from collections import Counter, defaultdict
from decimal import Decimal


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "results/raw/heldout/e2-freeze2-once"
PREBUILD = ROOT / "results/raw/heldout/prebuild-v3/families"
OUT = ROOT / "reports/heldout"
TOOLS = ("bindcheck-zk", "circomspect", "picus", "slither", "zkap", "arm-c")


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def relative(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def write_csv(path: pathlib.Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def distribution(values: list[Decimal]) -> dict:
    if not values:
        return {"recorded": 0, "min_seconds": None, "median_seconds": None, "max_seconds": None}
    return {
        "recorded": len(values),
        "min_seconds": str(min(values)),
        "median_seconds": str(statistics.median(values)),
        "max_seconds": str(max(values)),
    }


def main() -> None:
    manifest = read(RUN / "run-manifest.json")
    if not manifest.get("completed_utc") or manifest.get("clones_remaining") != 0:
        raise SystemExit("EVAL run manifest is incomplete")
    family_paths = sorted((RUN / "families").glob("*/family-result.json"))
    if len(family_paths) != manifest["families"]:
        raise SystemExit("family-result count differs from completed manifest")
    prebuild_by_id = {}
    for path in PREBUILD.glob("*/prebuild.json"):
        item = read(path)
        prebuild_by_id[item["family_id"]] = (item, path)

    family_rows = []
    runtime_rows = []
    artifacts = defaultdict(lambda: {"parsed": set(), "raw_paths": set(), "triple_ids": set(), "families": set()})
    counts = {"acquisition_status": Counter(), "prebuild_status": Counter(),
              "tool_run_status": {tool: Counter() for tool in TOOLS},
              "tool_verdict": {tool: Counter() for tool in TOOLS},
              "triple_count": Counter()}
    durations = defaultdict(list)
    timeouts = Counter()
    native_codes = Counter()
    unmatched_verifier_triples = 0
    raw_parse_failures = []

    for path in family_paths:
        item = read(path)
        family = item["family"]
        family_id = family["family_id"]
        folder = path.parent
        prebuild, prebuild_path = prebuild_by_id[family_id]
        counts["acquisition_status"][item["acquisition_status"]] += 1
        counts["prebuild_status"][prebuild["status"]] += 1
        row = {"rank": family["rank"], "family_id": family_id,
               "repository": family["repository"], "commit": family["commit"],
               "prebuild_status": prebuild["status"],
               "acquisition_status": item["acquisition_status"],
               "family_result": relative(path), "prebuild_record": relative(prebuild_path)}
        for tool in TOOLS:
            result = item["tools"].get(tool, {})
            status = result.get("run_status", "MISSING")
            counts["tool_run_status"][tool][status] += 1
            counts["tool_verdict"][tool][result.get("verdict", "MISSING")] += 1
            row[f"{tool}_run_status"] = status
            row[f"{tool}_verdict"] = result.get("verdict", "MISSING")
        raw_path = folder / "bindcheck-zk-raw.json"
        triples = []
        if raw_path.is_file():
            try:
                raw = read(raw_path)
                triples = raw.get("triples") or []
            except (OSError, ValueError) as exc:
                raw_parse_failures.append({"raw_path": relative(raw_path), "error": type(exc).__name__})
        row["triple_count"] = len(triples)
        row["bindcheck_raw"] = relative(raw_path) if raw_path.is_file() else "MISSING"
        counts["triple_count"]["with_triples" if triples else "no_triples"] += 1
        for pattern, result in (item["tools"]["bindcheck-zk"].get("patterns") or {}).items():
            row[f"{pattern}_verdict"] = result.get("verdict", "MISSING")
            row[f"{pattern}_applicability"] = result.get("applicability", "MISSING")
        family_rows.append(row)

        for triple in triples:
            verifier = triple.get("verifier") or {}
            verifier_path, source_sha = verifier.get("path"), verifier.get("sha256")
            if not verifier_path or not source_sha:
                unmatched_verifier_triples += 1
                continue
            key = (family["repository"], family["commit"], verifier_path, source_sha)
            artifact = artifacts[key]
            artifact["raw_paths"].add(relative(raw_path))
            artifact["triple_ids"].add(str(triple.get("id", "MISSING")))
            artifact["families"].add(family_id)
            facts = {fact.get("name"): fact.get("value") for fact in
                     (triple.get("patterns") or {}).get("P4", {}).get("facts", [])}
            gamma, delta = facts.get("gamma_g2"), facts.get("delta_g2")
            if isinstance(gamma, list) and isinstance(delta, list) and len(gamma) == len(delta) == 4:
                artifact["parsed"].add((tuple(map(str, gamma)), tuple(map(str, delta))))

        timing = {"rank": family["rank"], "family_id": family_id,
                  "family_result": relative(path), "prebuild_record": relative(prebuild_path)}
        acquisition_path = folder / "acquisition.json"
        acquisition = read(acquisition_path)
        acquisition_steps = acquisition.get("steps") or []
        acq_elapsed = sum((step.get("elapsed_seconds", Decimal(0)) for step in acquisition_steps), Decimal(0))
        timing["acquisition_seconds"] = str(acq_elapsed)
        timing["acquisition_record"] = relative(acquisition_path)
        durations["acquisition"].append(acq_elapsed)
        timeouts["acquisition"] += sum(bool(step.get("timed_out")) for step in acquisition_steps)
        compile_attempts = prebuild.get("compile_attempts") or []
        if compile_attempts:
            pre_elapsed = sum((attempt["command"].get("elapsed_seconds", Decimal(0))
                               for attempt in compile_attempts), Decimal(0))
            timing["prebuild_compile_seconds"] = str(pre_elapsed)
            durations["prebuild_compile"].append(pre_elapsed)
            timeouts["prebuild_compile"] += sum(bool(attempt["command"].get("timed_out"))
                                                for attempt in compile_attempts)
        else:
            timing["prebuild_compile_seconds"] = "MISSING"
        for tool in TOOLS:
            attempt_path = folder / f"{tool}-attempt.json"
            timing[f"{tool}_attempt_record"] = relative(attempt_path) if attempt_path.is_file() else "MISSING"
            if attempt_path.is_file():
                attempt = read(attempt_path)
                command = attempt.get("command") or {}
                elapsed = command.get("elapsed_seconds")
                if elapsed is not None:
                    timing[f"{tool}_seconds"] = str(elapsed)
                    durations[tool].append(elapsed)
                else:
                    timing[f"{tool}_seconds"] = "MISSING"
                timeouts[tool] += bool(command.get("timed_out"))
            else:
                timing[f"{tool}_seconds"] = "MISSING"
        runtime_rows.append(timing)
        arm_path = folder / "arm-c-raw.json"
        if arm_path.is_file():
            try:
                arm_raw = read(arm_path)
                if (arm_raw.get("run") or {}).get("status") == "completed":
                    for finding in (arm_raw.get("result") or {}).get("findings") or []:
                        native_codes[str(finding.get("code", "MISSING"))] += 1
            except (OSError, ValueError):
                pass

    gamma_rows = []
    gamma_status = Counter()
    for (repository, commit, verifier_path, source_sha), evidence in sorted(artifacts.items()):
        parsed = evidence["parsed"]
        if not parsed:
            status = "UNPARSED"
        elif len(parsed) > 1:
            status = "CONFLICT"
        else:
            gamma, delta = next(iter(parsed))
            status = "PARSED_EQUAL" if gamma == delta else "PARSED_DISTINCT"
        gamma_status[status] += 1
        if len(parsed) == 1:
            gamma_values, delta_values = next(iter(parsed))
            gamma_text = json.dumps(gamma_values)
            delta_text = json.dumps(delta_values)
        else:
            gamma_text = delta_text = "MISSING" if not parsed else "CONFLICT"
        gamma_rows.append({"repository": repository, "commit": commit,
                           "verifier_path": verifier_path, "source_sha256": source_sha,
                           "status": status, "gamma_g2": gamma_text, "delta_g2": delta_text,
                           "family_ids": "|".join(sorted(evidence["families"])),
                           "triple_ids": "|".join(sorted(evidence["triple_ids"])),
                           "raw_paths": "|".join(sorted(evidence["raw_paths"]))})

    family_fields = ["rank", "family_id", "repository", "commit", "prebuild_status",
                     "acquisition_status", "triple_count"]
    family_fields += [f"{tool}_{field}" for tool in TOOLS for field in ("run_status", "verdict")]
    family_fields += [f"{pattern}_{field}" for pattern in ("P1", "P2", "P3", "P4", "P5")
                      for field in ("verdict", "applicability")]
    family_fields += ["family_result", "prebuild_record", "bindcheck_raw"]
    write_csv(OUT / "measurement-family-ledger.csv", family_rows, family_fields)
    write_csv(OUT / "gamma-delta-ledger.csv", gamma_rows,
              ["repository", "commit", "verifier_path", "source_sha256", "status", "gamma_g2", "delta_g2",
               "family_ids", "triple_ids", "raw_paths"])
    timing_fields = ["rank", "family_id", "acquisition_seconds", "prebuild_compile_seconds"]
    timing_fields += [f"{tool}_seconds" for tool in TOOLS]
    timing_fields += ["family_result", "prebuild_record", "acquisition_record"]
    timing_fields += [f"{tool}_attempt_record" for tool in TOOLS]
    write_csv(OUT / "measurement-runtime-ledger.csv", runtime_rows, timing_fields)

    key_path = OUT / "warning-unblind-key.csv"
    with key_path.open(newline="", encoding="utf-8") as handle:
        warning_rows = list(csv.DictReader(handle))
    warning_counts = Counter((row["tool"], row["pattern"]) for row in warning_rows)
    warning_location = {tool: {
        "with_path_and_line": sum(row["tool"] == tool and bool(row["source_path"] and row["source_line"])
                                  for row in warning_rows),
        "missing_path_or_line": sum(row["tool"] == tool and not (row["source_path"] and row["source_line"])
                                    for row in warning_rows),
    } for tool in ("bindcheck-zk", "arm-c")}
    warning_location["total"] = {
        field: sum(warning_location[tool][field] for tool in ("bindcheck-zk", "arm-c"))
        for field in ("with_path_and_line", "missing_path_or_line")
    }
    card_rows = []
    card_missing = Counter()
    for key in warning_rows:
        card_path = ROOT / "review/heldout" / f"{key['card_id']}.md"
        if not card_path.is_file():
            raise SystemExit(f"missing blind card: {card_path}")
        card_text = card_path.read_text(encoding="utf-8")
        location_block = card_text.split("## Code at reported location", 1)[-1].split("## Matched verifier body", 1)[0]
        verifier_block = card_text.split("## Matched verifier body", 1)[-1].split("## Rule statement", 1)[0]
        location_missing = "MISSING:" in location_block
        verifier_missing = "MISSING:" in verifier_block
        card_missing["location_context_missing"] += location_missing
        card_missing["verifier_body_missing"] += verifier_missing
        card_rows.append({"card_id": key["card_id"], "tool": key["tool"],
                          "location_context_missing": location_missing,
                          "verifier_body_missing": verifier_missing,
                          "card_path": relative(card_path)})
    for rater in ("a", "b"):
        sheet = ROOT / "review/heldout" / f"BLIND-SHEET-rater-{rater}.csv"
        with sheet.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != len(warning_rows) or any(row["label"] or row["rater_reason"] for row in rows):
            raise SystemExit(f"rater sheet count or blankness mismatch: {sheet}")
        if {"tool", "confidence"} & set(rows[0] if rows else ()):
            raise SystemExit(f"rater sheet unblinding field: {sheet}")
    write_csv(OUT / "card-audit.csv", card_rows,
              ["card_id", "tool", "location_context_missing", "verifier_body_missing", "card_path"])
    summary = {
        "source_run_manifest": relative(RUN / "run-manifest.json"),
        "source_prebuild_summary": "reports/heldout/prebuild-summary-v3.json",
        "source_summary": relative(RUN / "summary.json"),
        "family_ledger": "reports/heldout/measurement-family-ledger.csv",
        "runtime_ledger": "reports/heldout/measurement-runtime-ledger.csv",
        "gamma_delta_ledger": "reports/heldout/gamma-delta-ledger.csv",
        "warning_key": relative(key_path),
        "card_audit": "reports/heldout/card-audit.csv",
        "card_missing": dict(sorted(card_missing.items())),
        "families": len(family_rows),
        "acquisition_status": dict(sorted(counts["acquisition_status"].items())),
        "prebuild_status": dict(sorted(counts["prebuild_status"].items())),
        "tool_run_status": {tool: dict(sorted(c.items())) for tool, c in counts["tool_run_status"].items()},
        "tool_verdict": {tool: dict(sorted(c.items())) for tool, c in counts["tool_verdict"].items()},
        "triple_count": dict(sorted(counts["triple_count"].items())),
        "gamma_delta": {"matched_artifacts": len(gamma_rows),
                        "parsed_denominator": gamma_status["PARSED_EQUAL"] + gamma_status["PARSED_DISTINCT"],
                        "equal_numerator": gamma_status["PARSED_EQUAL"],
                        "status": dict(sorted(gamma_status.items())),
                        "unmatched_verifier_triples": unmatched_verifier_triples},
        "runtime": {name: {**distribution(values), "timeouts": timeouts[name]}
                    for name, values in sorted(durations.items())},
        "native_arm_c_finding_codes": dict(sorted(native_codes.items())),
        "warning_counts": {f"{tool}/{pattern}": count for (tool, pattern), count in sorted(warning_counts.items())},
        "warning_location": warning_location,
        "warnings_total": len(warning_rows),
        "raw_parse_failures": raw_parse_failures,
    }
    (OUT / "measurement-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"families": len(family_rows), "gamma_delta": summary["gamma_delta"],
                      "warnings": len(warning_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
