#!/usr/bin/env python3
"""Summarize family-level BindCheck and baseline results without relabeling UNKNOWN."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
from collections import Counter
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import (  # noqa: E402
    APPLICABILITIES,
    PATTERNS,
    STRATA,
    VERDICTS,
    EvaluationError,
    atomic_write_json,
    atomic_write_text,
    load_json,
    tally_unknown_reasons,
    utc_now,
    validate_verdict,
)


DEFAULT_SEED = 20261103
DEFAULT_REPLICATES = 10_000


def percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _rates(records: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    total = len(records)
    applicable = sum(item["applicability"] == "APPLICABLE" for item in records)
    decided = sum(item["applicability"] == "APPLICABLE" and item["verdict"] in {"VIOLATION", "VERIFIED_WITHIN_SCOPE"} for item in records)
    violations = sum(item["applicability"] == "APPLICABLE" and item["verdict"] == "VIOLATION" for item in records)
    return {
        "applicable_rate": applicable / total if total else None,
        "decided_rate_among_applicable": decided / applicable if applicable else None,
        "violation_rate_among_applicable": violations / applicable if applicable else None,
        "violation_rate_among_decided": violations / decided if decided else None,
    }


def bootstrap_intervals(
    records: Sequence[Mapping[str, Any]], *, seed: int, replicates: int
) -> dict[str, dict[str, float] | None]:
    if not records or replicates <= 0:
        return {key: None for key in _rates(records)}
    randomizer = random.Random(seed)
    samples: dict[str, list[float]] = {key: [] for key in _rates(records)}
    for _ in range(replicates):
        drawn = [records[randomizer.randrange(len(records))] for _ in records]
        for key, value in _rates(drawn).items():
            if value is not None:
                samples[key].append(value)
    output: dict[str, dict[str, float] | None] = {}
    for key, values in samples.items():
        low = percentile(values, 0.025)
        high = percentile(values, 0.975)
        output[key] = None if low is None or high is None else {
            "low": low, "high": high
        }
    return output


def summarize_group(
    records: Sequence[Mapping[str, Any]], *, seed: int, replicates: int
) -> dict[str, Any]:
    for item in records:
        validate_verdict(str(item["verdict"]))
        if item.get("applicability") not in APPLICABILITIES:
            raise EvaluationError(f"invalid applicability: {item.get('applicability')!r}")
    counts = Counter(str(item["verdict"]) for item in records)
    matrix = {
        verdict: {applicability: sum(
            item["verdict"] == verdict and item["applicability"] == applicability
            for item in records
        ) for applicability in sorted(APPLICABILITIES)}
        for verdict in sorted(VERDICTS)
    }
    applicable = sum(item["applicability"] == "APPLICABLE" for item in records)
    decided = matrix["VIOLATION"]["APPLICABLE"] + matrix["VERIFIED_WITHIN_SCOPE"]["APPLICABLE"]
    def tally(field: str, *, unknown_only: bool = False) -> dict[str, int]:
        output: Counter[str] = Counter()
        for item in records:
            if unknown_only and item["verdict"] != "UNKNOWN":
                continue
            for value in set(map(str, item.get(field) or [])):
                output[value] += 1
        return dict(sorted(output.items()))
    return {
        "families": len(records),
        "applicable": applicable,
        "decided": decided,
        "verdict_by_applicability": matrix,
        "VIOLATION": counts["VIOLATION"],
        "VERIFIED_WITHIN_SCOPE": counts["VERIFIED_WITHIN_SCOPE"],
        "UNKNOWN": counts["UNKNOWN"],
        "NOT_APPLICABLE": sum(item["applicability"] == "NOT_APPLICABLE" for item in records),
        "applicability_unknown": sum(item["applicability"] == "UNKNOWN" for item in records),
        "by_reason": tally("reasons"),
        "unknown_by_reason": tally_unknown_reasons(records),
        "unknown_by_reason_code": tally("unknown_reason_codes", unknown_only=True),
        "rates": _rates(records),
        "family_bootstrap_95pct": bootstrap_intervals(
            records, seed=seed, replicates=replicates
        ),
    }


def load_family_results(run_dir: pathlib.Path) -> list[dict[str, Any]]:
    paths = sorted(run_dir.glob("families/*/family-result.json"))
    if not paths:
        raise EvaluationError(f"no family results found under {run_dir}")
    output: list[dict[str, Any]] = []
    for path in paths:
        payload = load_json(path)
        family = payload.get("family") or {}
        tools = payload.get("tools") or {}
        for tool, result in tools.items():
            verdict = result.get("verdict")
            if verdict not in VERDICTS:
                raise EvaluationError(f"{path}: {tool} has unsupported verdict {verdict!r}")
            if tool == "bindcheck-zk":
                for pattern in PATTERNS:
                    entry = (result.get("patterns") or {}).get(pattern)
                    if not isinstance(entry, dict) or entry.get("verdict") not in VERDICTS or entry.get("applicability") not in APPLICABILITIES:
                        raise EvaluationError(f"{path}: {tool} {pattern} lacks a valid verdict/applicability")
        output.append({"path": path, "family": family, "tools": tools})
    return output


def build_summary(
    families: Sequence[Mapping[str, Any]], *, seed: int, replicates: int
) -> dict[str, Any]:
    tools = sorted({tool for family in families for tool in family["tools"]})
    strata = [
        stratum for stratum in STRATA
        if any(item["family"].get("stratum") == stratum for item in families)
    ]
    strata.append("overall")
    tables: dict[str, Any] = {}
    for tool_index, tool in enumerate(tools):
        tables[tool] = {}
        scopes = PATTERNS if tool == "bindcheck-zk" else ("overall-tool",)
        for scope_index, scope in enumerate(scopes):
            tables[tool][scope] = {}
            for stratum_index, stratum in enumerate(strata):
                records = [
                    (item["tools"][tool]["patterns"][scope] if tool == "bindcheck-zk" else item["tools"][tool])
                    for item in families
                    if tool in item["tools"]
                    and (stratum == "overall" or item["family"].get("stratum") == stratum)
                ]
                tables[tool][scope][stratum] = summarize_group(
                    records,
                    seed=seed + tool_index * 1000 + scope_index * 100 + stratum_index,
                    replicates=replicates,
                )
    return {
        "schema": "bindcheck-zk.evaluation-summary/v2",
        "generated_utc": utc_now(),
        "families": len(families),
        "bootstrap": {"unit": "family", "seed": seed, "replicates": replicates, "interval": 0.95},
        "tools": tables,
    }


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Held-out evaluation summary", "",
        f"Families: {summary['families']}.", "",
        "`UNKNOWN` remains unresolved coverage. `NOT_APPLICABLE` is applicability, never a verdict.", "",
    ]
    for tool, scopes in summary["tools"].items():
        for scope, strata in scopes.items():
            lines.extend([
                f"## {tool} / {scope}", "",
                "| Stratum | Families | Applicable | Applicability unknown | Decided | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN | NOT_APPLICABLE |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ])
            for stratum, item in strata.items():
                lines.append(
                    f"| {stratum} | {item['families']} | {item['applicable']} | "
                    f"{item['applicability_unknown']} | {item['decided']} | {item['VIOLATION']} | "
                    f"{item['VERIFIED_WITHIN_SCOPE']} | {item['UNKNOWN']} | {item['NOT_APPLICABLE']} |"
                )
            overall = strata["overall"]
            for title, key in (("Reasons", "by_reason"), ("Unknown reasons", "unknown_by_reason"),
                               ("Unknown reason codes", "unknown_by_reason_code")):
                lines.extend(["", f"{title}:", ""])
                lines.extend(f"- `{reason}`: {count}" for reason, count in overall[key].items())
                if not overall[key]:
                    lines.append("- None")
            lines.append("")
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("run_dir", type=pathlib.Path)
    result.add_argument("--bootstrap-replicates", type=int, default=DEFAULT_REPLICATES)
    result.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    run_dir = args.run_dir.resolve()
    families = load_family_results(run_dir)
    summary = build_summary(
        families, seed=args.seed, replicates=args.bootstrap_replicates
    )
    atomic_write_json(run_dir / "summary.json", summary)
    markdown = render_markdown(summary)
    atomic_write_text(run_dir / "summary.md", markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
