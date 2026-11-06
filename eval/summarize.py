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
    applicable = sum(item["verdict"] != "NOT_APPLICABLE" for item in records)
    decided = sum(item["verdict"] in {"VIOLATION", "VERIFIED_WITHIN_SCOPE"} for item in records)
    violations = sum(item["verdict"] == "VIOLATION" for item in records)
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
            "low": round(low, 6), "high": round(high, 6)
        }
    return output


def summarize_group(
    records: Sequence[Mapping[str, Any]], *, seed: int, replicates: int
) -> dict[str, Any]:
    for item in records:
        validate_verdict(str(item["verdict"]))
    counts = Counter(str(item["verdict"]) for item in records)
    applicable = len(records) - counts["NOT_APPLICABLE"]
    decided = counts["VIOLATION"] + counts["VERIFIED_WITHIN_SCOPE"]
    return {
        "families": len(records),
        "applicable": applicable,
        "decided": decided,
        "VIOLATION": counts["VIOLATION"],
        "VERIFIED_WITHIN_SCOPE": counts["VERIFIED_WITHIN_SCOPE"],
        "UNKNOWN": counts["UNKNOWN"],
        "NOT_APPLICABLE": counts["NOT_APPLICABLE"],
        "unknown_by_reason": tally_unknown_reasons(records),
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
        for stratum_index, stratum in enumerate(strata):
            records = [
                item["tools"][tool]
                for item in families
                if tool in item["tools"]
                and (stratum == "overall" or item["family"].get("stratum") == stratum)
            ]
            tables[tool][stratum] = summarize_group(
                records,
                seed=seed + tool_index * 100 + stratum_index,
                replicates=replicates,
            )
    return {
        "schema": "bindcheck-zk.evaluation-summary/v1",
        "generated_utc": utc_now(),
        "families": len(families),
        "bootstrap": {"unit": "family", "seed": seed, "replicates": replicates, "interval": 0.95},
        "tools": tables,
    }


def _fmt_rate(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Held-out evaluation summary",
        "",
        f"Families: {summary['families']}. Bootstrap unit: family; "
        f"{summary['bootstrap']['replicates']} replicates; seed {summary['bootstrap']['seed']}.",
        "",
        "`UNKNOWN` remains unresolved coverage and is never counted as safe. "
        "`NOT_APPLICABLE` is excluded from applicable denominators.",
        "",
    ]
    for tool, strata in summary["tools"].items():
        lines.extend([
            f"## {tool}",
            "",
            "| Stratum | Families | Applicable | Decided | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN | NOT_APPLICABLE | Decided/applicable | Violation/applicable |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for stratum, item in strata.items():
            lines.append(
                f"| {stratum} | {item['families']} | {item['applicable']} | {item['decided']} | "
                f"{item['VIOLATION']} | {item['VERIFIED_WITHIN_SCOPE']} | {item['UNKNOWN']} | "
                f"{item['NOT_APPLICABLE']} | {_fmt_rate(item['rates']['decided_rate_among_applicable'])} | "
                f"{_fmt_rate(item['rates']['violation_rate_among_applicable'])} |"
            )
        lines.extend(["", "Unknown reasons:", ""])
        overall_reasons = strata["overall"]["unknown_by_reason"]
        if overall_reasons:
            lines.extend(f"- `{reason}`: {count}" for reason, count in overall_reasons.items())
        else:
            lines.append("- None")
        lines.append("")

    lines.extend([
        "## Overall baseline comparison",
        "",
        "| Tool | Applicable | Decided | VIOLATION | VERIFIED_WITHIN_SCOPE | UNKNOWN | NOT_APPLICABLE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for tool, strata in summary["tools"].items():
        item = strata["overall"]
        lines.append(
            f"| {tool} | {item['applicable']} | {item['decided']} | {item['VIOLATION']} | "
            f"{item['VERIFIED_WITHIN_SCOPE']} | {item['UNKNOWN']} | {item['NOT_APPLICABLE']} |"
        )
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
