#!/usr/bin/env python3
"""Prepare blind warning sheets and compute two-rater Cohen's kappa."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import sys
from collections import Counter
from typing import Any, Iterable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import EvaluationError, load_json  # noqa: E402


LABELS = ("TP", "FP", "unclear")
FIELDS = (
    "warning_id", "family_id", "repository", "commit", "pattern",
    "reason_code", "source_path", "source_line", "message", "label", "rater_reason",
)
P4_WARNING_REASONS = {
    "DEFAULT_G2_GAMMA_DELTA_SOURCE_WARNING",
    "DUPLICATE_IC_SOURCE_WARNING",
    "DEFAULT_G2_RUNTIME_SIGNATURE",
    "PUBLIC_INPUT_CANONICALITY_GUARD_NOT_FOUND",
}


def _is_warning(result: Mapping[str, Any]) -> bool:
    return result.get("verdict") == "VIOLATION" or result.get("reason") in P4_WARNING_REASONS


def _warning_row(family: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, str]:
    location = result.get("location") or {}
    identity = "|".join([
        "bindcheck-zk",
        str(family.get("family_id", "")),
        str(result.get("pattern", "")),
        str(result.get("reason", "")),
        str(location.get("path", "")),
        str(location.get("line", "")),
        str(result.get("message", "")),
    ])
    return {
        "tool": "bindcheck-zk",
        "warning_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        "family_id": str(family.get("family_id", "")),
        "repository": str(family.get("repository", "")),
        "commit": str(family.get("commit", "")),
        "pattern": str(result.get("pattern", "")),
        "reason_code": str(result.get("reason", "")),
        "source_path": str(location.get("path", "")),
        "source_line": str(location.get("line", "")),
        "message": str(result.get("message", "")),
        "label": "",
        "rater_reason": "",
    }


def _arm_c_warning_row(family: Mapping[str, Any], finding: Mapping[str, Any]) -> dict[str, str]:
    location = finding.get("location") or {}
    code = str(finding.get("code") or "NATIVE_CODE_MISSING")
    message = str(finding.get("message") or "")
    identity = "|".join(("arm-c", str(family.get("family_id", "")), code,
                         str(location.get("path") or ""), str(location.get("line") or ""), message))
    return {
        "tool": "arm-c",
        "warning_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        "family_id": str(family.get("family_id", "")),
        "repository": str(family.get("repository", "")),
        "commit": str(family.get("commit", "")),
        "pattern": "",
        "reason_code": code,
        "source_path": str(location.get("path") or ""),
        "source_line": str(location.get("line") or ""),
        "message": message,
        "label": "", "rater_reason": "",
    }


def extract_warnings(run_dir: pathlib.Path) -> list[dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for family_path in sorted(run_dir.glob("families/*/family.json")):
        family_dir = family_path.parent
        raw_path = family_dir / "bindcheck-zk-raw.json"
        family = load_json(family_path)
        try:
            payload = load_json(raw_path) if raw_path.is_file() else {}
        except (OSError, ValueError):
            payload = {}
        candidates = []
        for triple in payload.get("triples", []) or []:
            candidates.extend((triple.get("patterns") or {}).values())
        candidates.extend(
            item.get("finding", {}) for item in payload.get("runtime_bytecode_checks", []) or []
        )
        for result in candidates:
            if _is_warning(result):
                row = _warning_row(family, result)
                output.setdefault(row["warning_id"], row)
        arm_c_path = family_dir / "arm-c-raw.json"
        if arm_c_path.is_file():
            try:
                arm_c = load_json(arm_c_path)
            except (OSError, ValueError):
                continue
            if (arm_c.get("run") or {}).get("status") == "completed":
                for finding in (arm_c.get("result") or {}).get("findings") or []:
                    row = _arm_c_warning_row(family, finding)
                    output.setdefault(row["warning_id"], row)
    return [output[key] for key in sorted(output)]


def write_sheet(path: pathlib.Path, rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_ratings(path: pathlib.Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise EvaluationError(f"rating sheet has no rows: {path}")
    output: dict[str, str] = {}
    for row in rows:
        warning_id = row.get("warning_id", "")
        label = row.get("label", "")
        if not warning_id or warning_id in output:
            raise EvaluationError(f"missing or duplicate warning_id in {path}: {warning_id!r}")
        if label not in LABELS:
            raise EvaluationError(f"invalid label in {path} for {warning_id}: {label!r}")
        if not row.get("rater_reason", "").strip():
            raise EvaluationError(f"missing rater_reason in {path} for {warning_id}")
        output[warning_id] = label
    return output


def cohen_kappa(first: Mapping[str, str], second: Mapping[str, str]) -> dict[str, Any]:
    if set(first) != set(second):
        missing_first = sorted(set(second) - set(first))
        missing_second = sorted(set(first) - set(second))
        raise EvaluationError(
            f"rating sheets cover different warnings; missing from first={missing_first}, "
            f"missing from second={missing_second}"
        )
    ids = sorted(first)
    n = len(ids)
    confusion = {left: {right: 0 for right in LABELS} for left in LABELS}
    for warning_id in ids:
        confusion[first[warning_id]][second[warning_id]] += 1
    observed = sum(confusion[label][label] for label in LABELS) / n
    first_counts = Counter(first.values())
    second_counts = Counter(second.values())
    expected = sum((first_counts[label] / n) * (second_counts[label] / n) for label in LABELS)
    kappa = None if expected == 1.0 else (observed - expected) / (1.0 - expected)
    return {
        "schema": "bindcheck-zk.adjudication-agreement/v1",
        "warnings": n,
        "labels": list(LABELS),
        "observed_agreement": round(observed, 6),
        "expected_agreement": round(expected, 6),
        "cohen_kappa": None if kappa is None else round(kappa, 6),
        "confusion_matrix": confusion,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("run_dir", type=pathlib.Path)
    prepare.add_argument("rater_a", type=pathlib.Path)
    prepare.add_argument("rater_b", type=pathlib.Path)
    kappa = commands.add_parser("kappa")
    kappa.add_argument("rater_a", type=pathlib.Path)
    kappa.add_argument("rater_b", type=pathlib.Path)
    kappa.add_argument("--output", type=pathlib.Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "prepare":
        rows = extract_warnings(args.run_dir.resolve())
        write_sheet(args.rater_a, rows)
        write_sheet(args.rater_b, rows)
        print(json.dumps({"warnings": len(rows), "rater_a": str(args.rater_a), "rater_b": str(args.rater_b)}, indent=2))
        return 0
    result = cohen_kappa(read_ratings(args.rater_a), read_ratings(args.rater_b))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
