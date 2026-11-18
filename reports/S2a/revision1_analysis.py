#!/usr/bin/env python3
"""Build the S2a revision-1 spent-family ledger and Set H recomputation.

The two analysed run directories are the freeze-2 one-shot run and the S2a
rerun.  The script reads retained JSON only; it never runs the analyzer or
touches the network.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

PATTERNS = ("P1", "P2", "P3", "P4", "P5")
VERDICTS = ("VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN")
P4_CANONICALITY = "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND"
P4_WARNING_REASONS = {
    "DEFAULT_G2_GAMMA_DELTA_SOURCE_WARNING",
    "DUPLICATE_IC_SOURCE_WARNING",
    "DEFAULT_G2_RUNTIME_SIGNATURE",
    P4_CANONICALITY,
}


def load(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: pathlib.Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def family_results(run: pathlib.Path) -> dict[int, dict[str, Any]]:
    output: dict[int, dict[str, Any]] = {}
    for path in sorted(run.glob("families/*/family-result.json")):
        item = load(path)
        output[int(item["family"]["rank"])] = item
    return output


def bindcheck(item: dict[str, Any]) -> dict[str, Any]:
    return item["tools"]["bindcheck-zk"]


def reasons_for(result: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if result.get("verdict") == "UNKNOWN":
        reasons.extend(str(value) for value in result.get("unknown_reasons") or [])
    reasons.extend(str(value) for value in result.get("reasons") or [])
    ordered = []
    for value in reasons:
        if value and value not in ordered:
            ordered.append(value)
    return "; ".join(ordered) or "NO_REASON_RECORDED"


def signature(result: Mapping[str, Any]) -> str:
    return f"{result.get('verdict')}/{result.get('applicability')}"


def all_pattern_results(family: Mapping[str, Any], payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return every recovered pattern result, including non-warning verdicts."""
    rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for triple in payload.get("triples", []) or []:
        candidates.extend((triple.get("patterns") or {}).values())
    for check in payload.get("runtime_bytecode_checks", []) or []:
        finding = check.get("finding")
        if isinstance(finding, dict):
            candidates.append(finding)
    for result in candidates:
        location = result.get("location") or {}
        rows.append({
            "family_id": str(family.get("family_id", "")),
            "pattern": str(result.get("pattern", "")),
            "reason_code": str(result.get("reason", "")),
            "source_path": str(location.get("path", "")),
            "source_line": str(location.get("line", "")),
            "verdict": str(result.get("verdict", "")),
            "message": str(result.get("message", "")),
            "is_warning": bool(
                result.get("verdict") == "VIOLATION"
                or result.get("reason") in P4_WARNING_REASONS
            ),
        })
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = (row["family_id"], row["pattern"], row["reason_code"],
               row["source_path"], row["source_line"], row["message"])
        unique.setdefault(key, row)
    return list(unique.values())


def line_number(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def match_result(card: Mapping[str, str], results: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    pattern = card["pattern"]
    family_id = card["family_id"]
    path = card["source_path"]
    line = card["source_line"]
    reason = card["reason_code"]
    pool = [
        item for item in results
        if item["family_id"] == family_id
        and item["pattern"] == pattern
        and item["source_path"] == path
    ]
    if pattern == "P4":
        pool = [item for item in pool if item["reason_code"] == reason]
    if not pool:
        return None, "NOT_EMITTED"
    exact = [item for item in pool if item["source_line"] == line]
    if exact:
        violation = [item for item in exact if item["verdict"] == "VIOLATION"]
        warning = [item for item in exact if item["is_warning"]]
        return (violation or warning or exact)[0], "SAME_LOCATION"
    target = line_number(line)
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in pool:
        observed = line_number(item["source_line"])
        if target is not None and observed is not None:
            scored.append((abs(observed - target), item))
        else:
            scored.append((10**9, item))
    scored.sort(key=lambda pair: (pair[0], pair[1]["verdict"] != "VIOLATION"))
    if scored and scored[0][0] < 10**9:
        return scored[0][1], f"MOVED_LINE_{scored[0][0]}"
    return pool[0], "SAME_PATH"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-run", type=pathlib.Path, required=True)
    parser.add_argument("--new-run", type=pathlib.Path, required=True)
    parser.add_argument("--labels", type=pathlib.Path, required=True)
    parser.add_argument("--key", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    selection = load(args.new_run / "selected-families.json")["families"]
    new_manifest = load(args.new_run / "run-manifest.json")
    excluded_ranks = {int(item["rank"]) for item in new_manifest.get("excluded_before_analysis") or []}
    old = family_results(args.old_run)
    new = family_results(args.new_run)

    ledger_rows: list[dict[str, Any]] = []
    changed_rows: list[dict[str, Any]] = []
    for family in selection:
        rank = int(family["rank"])
        base = {
            "rank": rank,
            "family_id": family["family_id"],
            "repository": family["repository"],
            "commit": family["commit"],
            "stratum": family["stratum"],
        }
        if rank in excluded_ranks:
            ledger_rows.append({
                **base,
                "status": "EXCLUDED_BEFORE_ANALYSIS",
                "old_status": "EXCLUDED_BEFORE_ANALYSIS",
                "new_status": "EXCLUDED_BEFORE_ANALYSIS",
            })
            continue
        old_item = old.get(rank)
        new_item = new.get(rank)
        if old_item is None or new_item is None:
            ledger_rows.append({
                **base,
                "status": "MISSING_RESULT",
                "old_status": "MISSING" if old_item is None else bindcheck(old_item).get("run_status"),
                "new_status": "MISSING" if new_item is None else bindcheck(new_item).get("run_status"),
            })
            continue
        old_bc = bindcheck(old_item)
        new_bc = bindcheck(new_item)
        new_ready = new_item.get("acquisition_status") == "ready"
        timed_out = "HARNESS_TIMEOUT" in json.dumps(new_bc)
        row: dict[str, Any] = {
            **base,
            "status": (
                "ACQUISITION_FAILED" if not new_ready
                else "HARNESS_TIMEOUT" if timed_out
                else "ANALYZED"
            ),
            "old_status": old_bc.get("run_status"),
            "new_status": new_bc.get("run_status"),
            "new_acquisition_status": new_item.get("acquisition_status"),
            "new_checkout_deleted": new_item.get("checkout_deleted"),
        }
        changes = []
        for pattern in PATTERNS:
            old_pattern = old_bc["patterns"][pattern]
            new_pattern = new_bc["patterns"][pattern]
            row[f"old_{pattern}"] = signature(old_pattern)
            row[f"new_{pattern}"] = signature(new_pattern)
            if signature(old_pattern) != signature(new_pattern):
                changes.append(pattern)
                new_reason_text = reasons_for(new_pattern)
                if "HARNESS_TIMEOUT" in new_reason_text:
                    change_kind = "COVERAGE_TIMEOUT"
                elif not new_ready:
                    change_kind = "COVERAGE_ACQUISITION"
                elif old_pattern.get("verdict") != new_pattern.get("verdict"):
                    change_kind = "SEMANTIC_VERDICT"
                else:
                    change_kind = "SEMANTIC_APPLICABILITY"
                changed_rows.append({
                    **base,
                    "pattern": pattern,
                    "old": signature(old_pattern),
                    "new": signature(new_pattern),
                    "old_reason": reasons_for(old_pattern),
                    "new_reason": (
                        "ACQUISITION_" + str(new_item.get("acquisition_status", "FAILED")).upper().replace("-", "_")
                        if not new_ready else reasons_for(new_pattern)
                    ),
                    "change": change_kind,
                })
        row["changed_patterns"] = ",".join(changes)
        ledger_rows.append(row)

    write_csv(args.out / "spent-family-ledger-278.csv", ledger_rows, list(ledger_rows[0]))
    write_csv(args.out / "spent-family-changed-verdicts.csv", changed_rows, [
        "rank", "family_id", "repository", "commit", "stratum", "pattern",
        "old", "new", "change", "old_reason", "new_reason",
    ])

    def build_delta(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
        delta: dict[str, dict[str, Counter[str]]] = {}
        for pattern in PATTERNS:
            delta[pattern] = {"old": Counter(), "new": Counter(), "changed": Counter()}
            for item in rows:
                old_value = item[f"old_{pattern}"]
                new_value = item[f"new_{pattern}"]
                old_verdict, old_app = old_value.split("/", 1)
                new_verdict, new_app = new_value.split("/", 1)
                delta[pattern]["old"][f"{old_app}:{old_verdict}"] += 1
                delta[pattern]["new"][f"{new_app}:{new_verdict}"] += 1
                if old_value != new_value:
                    delta[pattern]["changed"][f"{old_value}->{new_value}"] += 1
        return {
            pattern: {scope: dict(sorted(values.items())) for scope, values in scopes.items()}
            for pattern, scopes in delta.items()
        }

    complete_rows = [row for row in ledger_rows if row["status"] == "ANALYZED"]
    ready_rows = [row for row in ledger_rows if row["status"] in {"ANALYZED", "HARNESS_TIMEOUT"}]
    for name, rows in (("spent-family-delta.json", ready_rows),
                       ("spent-family-delta-complete.json", complete_rows)):
        (args.out / name).write_text(
            json.dumps(build_delta(rows), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    # Set H recomputation.
    key_rows = {row["card_id"]: row for row in read_csv(args.key)}
    labels = [
        row for row in read_csv(args.labels)
        if row.get("tool") == "bindcheck-zk"
    ]
    warnings_by_rank: dict[int, list[dict[str, Any]]] = {}
    family_status: dict[int, str] = {}
    family_by_id = {item["family_id"]: int(item["rank"]) for item in selection}
    for rank, item in new.items():
        if item.get("acquisition_status") != "ready":
            family_status[rank] = "ACQUISITION_FAILED"
        elif "HARNESS_TIMEOUT" in json.dumps(bindcheck(item)):
            family_status[rank] = "HARNESS_TIMEOUT"
        else:
            family_status[rank] = "ANALYZED"
        # raw_result is recorded relative to the run working directory; the
        # deterministic family directory is the canonical retained location.
        raw_path = args.new_run / "families" / f"{rank:03d}-{item['family']['sample_hash'][:12]}" / "bindcheck-zk-raw.json"
        try:
            payload = load(raw_path) if raw_path.is_file() else {}
        except (OSError, ValueError):
            payload = {}
        warnings_by_rank[rank] = all_pattern_results(item["family"], payload)

    set_h_rows = []
    for label in labels:
        key = key_rows.get(label["warning_id"])
        if key is None:
            continue
        stratum = label["stratum"]
        if stratum not in {"P1", "P3", "P5", "P4/PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND"}:
            continue
        if stratum.startswith("P4/"):
            pattern = "P4"
        else:
            pattern = stratum
        card = {
            "card_id": label["warning_id"],
            "family_id": key["family_id"],
            "repository": key["repository"],
            "commit": key["commit"],
            "pattern": pattern,
            "reason_code": key["reason_code"],
            "source_path": key["source_path"],
            "source_line": key["source_line"],
            "final": label["final"],
        }
        rank = family_by_id.get(card["family_id"])
        status = family_status.get(rank, "NO_NEW_FAMILY") if rank is not None else "NO_NEW_FAMILY"
        match, match_kind = (None, "NO_NEW_FAMILY")
        if rank is not None and status == "ANALYZED" and rank in warnings_by_rank:
            match, match_kind = match_result(card, warnings_by_rank[rank])
        elif status in {"HARNESS_TIMEOUT", "ACQUISITION_FAILED"}:
            match_kind = f"COVERAGE_{status}"
        is_warning = bool(match and match["is_warning"])
        set_h_rows.append({
            **card,
            "rank": rank if rank is not None else "",
            "family_status": status,
            "matched": "YES" if match else "NO",
            "match_kind": match_kind,
            "still_warning": "YES" if is_warning else "NO",
            "new_verdict": match["verdict"] if match else "UNKNOWN_COVERAGE",
            "new_reason": match["reason_code"] if match else status,
            "new_source_path": match["source_path"] if match else "",
            "new_source_line": match["source_line"] if match else "",
        })
    write_csv(args.out / "set-h-recomputed-cards.csv", set_h_rows, [
        "card_id", "family_id", "rank", "repository", "commit", "pattern",
        "reason_code", "source_path", "source_line", "final", "family_status",
        "matched", "match_kind", "still_warning", "new_verdict", "new_reason",
        "new_source_path", "new_source_line",
    ])

    summary: dict[str, Any] = {"strata": {}}
    for stratum in ("P1", "P3", "P4/PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND", "P5"):
        rows = [row for row in set_h_rows if (
            stratum if not stratum.startswith("P4/") else "P4"
        ) == row["pattern"] and (
            not stratum.startswith("P4/") or row["reason_code"] == P4_CANONICALITY
        )]
        retained = [row for row in rows if row["still_warning"] == "YES"]
        coverage = [row for row in rows if row["match_kind"].startswith("COVERAGE_")]
        analyzed = [row for row in rows if row["family_status"] == "ANALYZED"]
        tp = sum(row["final"] == "TP" for row in retained)
        fp = sum(row["final"] == "FP" for row in retained)
        summary["strata"][stratum] = {
            "cards": len(rows),
            "analyzed_cards": len(analyzed),
            "coverage_unavailable_cards": len(coverage),
            "coverage_unavailable": [
                {"card_id": row["card_id"], "final": row["final"],
                 "reason": row["match_kind"]}
                for row in coverage
            ],
            "retained_warnings": len(retained),
            "not_emitted": sum(row["match_kind"] == "NOT_EMITTED" for row in rows),
            "no_longer_warning_analyzed": sum(
                row["still_warning"] == "NO" and row["family_status"] == "ANALYZED"
                for row in rows
            ),
            "tp_retained": tp,
            "fp_retained": fp,
            "precision": (tp / (tp + fp)) if tp + fp else None,
            "tp_not_emitted_analyzed": [
                row["card_id"] for row in rows
                if row["final"] == "TP" and row["still_warning"] == "NO"
                and row["family_status"] == "ANALYZED"
            ],
            "fp_still_violation": [row["card_id"] for row in retained if row["final"] == "FP" and row["new_verdict"] == "VIOLATION"],
            "fp_no_longer_violation_analyzed": [
                row["card_id"] for row in rows
                if row["final"] == "FP" and row["family_status"] == "ANALYZED"
                and row["new_verdict"] != "VIOLATION"
            ],
            "tp_still_violation": [row["card_id"] for row in retained if row["final"] == "TP" and row["new_verdict"] == "VIOLATION"],
        }
    for stratum, values in summary["strata"].items():
        values["fp_no_longer_violation_analyzed_count"] = len(values["fp_no_longer_violation_analyzed"])
        values["fp_still_violation_count"] = len(values["fp_still_violation"])
        values["tp_still_violation_count"] = len(values["tp_still_violation"])
        values["precision_denominator"] = values["tp_retained"] + values["fp_retained"]
    p5 = summary["strata"]["P5"]
    p5["tp_remain_violation"] = len(p5["tp_still_violation"])
    p5["fp_total"] = p5["fp_still_violation_count"] + p5["fp_no_longer_violation_analyzed_count"] + p5["coverage_unavailable_cards"]
    summary["p5"] = p5
    (args.out / "set-h-recomputed-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ledger_rows": len(ledger_rows),
        "analyzed_rows": sum(row["status"] == "ANALYZED" for row in ledger_rows),
        "acquisition_failed_rows": sum(row["status"] == "ACQUISITION_FAILED" for row in ledger_rows),
        "timeout_rows": sum(row["status"] == "HARNESS_TIMEOUT" for row in ledger_rows),
        "excluded_rows": sum(row["status"] == "EXCLUDED_BEFORE_ANALYSIS" for row in ledger_rows),
        "semantic_verdict_changes": sum(row["change"] == "SEMANTIC_VERDICT" for row in changed_rows),
        "semantic_applicability_changes": sum(row["change"] == "SEMANTIC_APPLICABILITY" for row in changed_rows),
        "coverage_acquisition_changes": sum(row["change"] == "COVERAGE_ACQUISITION" for row in changed_rows),
        "coverage_timeout_changes": sum(row["change"] == "COVERAGE_TIMEOUT" for row in changed_rows),
        "set_h": summary,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
