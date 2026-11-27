#!/usr/bin/env python3
"""Deterministic agreement analysis for the D2 taxonomy design.

The input contains exactly two independent human ratings per canonical finding.
Relevance is a three-category nominal decision.  Cause, consequence, and role
axes are multilabel: each category is analyzed as a separate binary decision.
``uncertain``, ``unassessed``, omitted, and null values are missing rather than
negative.  The script deliberately reports one chance-corrected statistic
(Cohen's kappa) and prevalence diagnostics instead of searching over metrics.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols/d2/d2-04-taxonomy-preparation-v1.json"
SCHEMA = "bindcheck.d2.taxonomy-agreement/v1"
INPUT_SCHEMA = "bindcheck.d2.taxonomy-ratings/v1"
RELEVANCE = ("include", "exclude", "unresolved")
BINARY = ("present", "absent")
MISSING = ("uncertain", "unassessed", None)


def _number(value: float) -> float:
    return round(value, 12)


def _cohen_kappa(
    pairs: list[tuple[str, str]], categories: Iterable[str]
) -> tuple[float | None, str | None, float | None, float | None]:
    if not pairs:
        return None, "NO_COMPARABLE_PAIRS", None, None
    categories = tuple(categories)
    total = len(pairs)
    observed = sum(left == right for left, right in pairs) / total
    left_counts = Counter(left for left, _right in pairs)
    right_counts = Counter(right for _left, right in pairs)
    expected = sum(
        (left_counts[category] / total) * (right_counts[category] / total)
        for category in categories
    )
    if expected == 1:
        return None, "NO_CHANCE_VARIANCE", _number(observed), _number(expected)
    return (
        _number((observed - expected) / (1 - expected)),
        None,
        _number(observed),
        _number(expected),
    )


def _nominal_axis(
    values: list[tuple[Any, Any]], categories: tuple[str, ...]
) -> dict[str, Any]:
    comparable = [
        (left, right) for left, right in values
        if left in categories and right in categories
    ]
    kappa, reason, raw, expected = _cohen_kappa(comparable, categories)
    confusion = {
        left: {right: 0 for right in categories} for left in categories
    }
    for left, right in comparable:
        confusion[left][right] += 1
    return {
        "total_items": len(values),
        "comparable_items": len(comparable),
        "missing_pairs": len(values) - len(comparable),
        "rater_1_counts": dict(Counter(left for left, _right in comparable)),
        "rater_2_counts": dict(Counter(right for _left, right in comparable)),
        "confusion": confusion,
        "raw_agreement": raw,
        "chance_agreement": expected,
        "cohen_kappa": kappa,
        "cohen_kappa_null_reason": reason,
    }


def _binary_label(values: list[tuple[Any, Any]]) -> dict[str, Any]:
    result = _nominal_axis(values, BINARY)
    comparable = [
        (left, right) for left, right in values
        if left in BINARY and right in BINARY
    ]
    counts = Counter(comparable)
    both_present = counts[("present", "present")]
    left_only = counts[("present", "absent")]
    right_only = counts[("absent", "present")]
    both_absent = counts[("absent", "absent")]
    positive_denominator = 2 * both_present + left_only + right_only
    negative_denominator = 2 * both_absent + left_only + right_only
    result.update({
        "both_present": both_present,
        "rater_1_only_present": left_only,
        "rater_2_only_present": right_only,
        "both_absent": both_absent,
        "rater_1_positive_prevalence": (
            _number((both_present + left_only) / len(comparable))
            if comparable else None
        ),
        "rater_2_positive_prevalence": (
            _number((both_present + right_only) / len(comparable))
            if comparable else None
        ),
        "positive_agreement": (
            _number(2 * both_present / positive_denominator)
            if positive_denominator else None
        ),
        "positive_agreement_null_reason": (
            None if positive_denominator else "NO_POSITIVE_RATINGS"
        ),
        "negative_agreement": (
            _number(2 * both_absent / negative_denominator)
            if negative_denominator else None
        ),
        "negative_agreement_null_reason": (
            None if negative_denominator else "NO_NEGATIVE_RATINGS"
        ),
        "state_counts": {
            "rater_1": dict(Counter(
                "missing" if left not in BINARY else left for left, _right in values
            )),
            "rater_2": dict(Counter(
                "missing" if right not in BINARY else right for _left, right in values
            )),
        },
    })
    return result


def _protocol_axes() -> dict[str, tuple[str, ...]]:
    protocol = json.loads(PROTOCOL.read_text())
    return {
        axis: tuple(protocol["codebook"]["axes"][axis]["labels"])
        for axis in ("causes", "consequences", "roles")
    }


def _rating_value(rating: dict[str, Any], axis: str, label: str) -> Any:
    value = rating.get(axis, {}).get(label)
    if value not in (*BINARY, *MISSING):
        raise ValueError(f"invalid {axis}.{label} state: {value!r}")
    return value


def validate_input(data: dict[str, Any]) -> tuple[list[str], dict[str, tuple[str, ...]]]:
    if data.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"unsupported ratings schema: {data.get('schema')!r}")
    if data.get("codebook_version") != "0.3.0":
        raise ValueError("ratings must use frozen codebook version 0.3.0")
    if data.get("study_design") not in {"fresh_independent", "exposed_pilot"}:
        raise ValueError("study_design must be fresh_independent or exposed_pilot")
    if "adjudication" in data:
        raise ValueError("agreement input must contain sealed original ratings only")
    raters = data.get("raters", [])
    if len(raters) != 2:
        raise ValueError("exactly two fixed raters are required")
    rater_ids = [rater.get("id") for rater in raters]
    if any(not value for value in rater_ids) or len(set(rater_ids)) != 2:
        raise ValueError("rater IDs must be two distinct nonempty values")
    if any(rater.get("kind") != "human" for rater in raters):
        raise ValueError("AI systems cannot be taxonomy raters")
    if any(not rater.get("prior_exposure_summary") for rater in raters):
        raise ValueError("each human rater must disclose prior exposure")
    items = data.get("items", [])
    if not items:
        raise ValueError("ratings input has no items")
    item_ids = [item.get("item_id") for item in items]
    family_ids = [item.get("family_id") for item in items]
    if any(not value for value in item_ids) or len(set(item_ids)) != len(item_ids):
        raise ValueError("item IDs must be unique and nonempty")
    if any(not value for value in family_ids) or len(set(family_ids)) != len(family_ids):
        raise ValueError("primary agreement requires at most one scored item per family")
    if data["study_design"] == "fresh_independent" and any(
        item.get("prior_exposure") != "fresh_to_both_raters" for item in items
    ):
        raise ValueError("fresh_independent items must be fresh to both raters")
    axes = _protocol_axes()
    for item in items:
        ratings = item.get("ratings", {})
        if set(ratings) != set(rater_ids):
            raise ValueError(f"{item['item_id']}: ratings must cover both raters exactly")
        for rater_id in rater_ids:
            rating = ratings[rater_id]
            relevance = rating.get("relevance")
            if relevance not in (*RELEVANCE, *MISSING):
                raise ValueError(
                    f"{item['item_id']}:{rater_id}: invalid relevance {relevance!r}"
                )
            for axis, labels in axes.items():
                extra = set(rating.get(axis, {})).difference(labels)
                if extra:
                    raise ValueError(
                        f"{item['item_id']}:{rater_id}: unknown {axis} labels {sorted(extra)}"
                    )
                for label in labels:
                    _rating_value(rating, axis, label)
    return rater_ids, axes


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    rater_ids, axes = validate_input(data)
    items = data["items"]
    relevance_values = [
        (
            item["ratings"][rater_ids[0]].get("relevance"),
            item["ratings"][rater_ids[1]].get("relevance"),
        )
        for item in items
    ]
    axis_results: dict[str, Any] = {}
    exact_set: dict[str, Any] = {}
    for axis, labels in axes.items():
        axis_results[axis] = {}
        exact_comparable = 0
        exact_matches = 0
        for label in labels:
            values = [
                (
                    _rating_value(item["ratings"][rater_ids[0]], axis, label),
                    _rating_value(item["ratings"][rater_ids[1]], axis, label),
                )
                for item in items
            ]
            axis_results[axis][label] = _binary_label(values)
        for item in items:
            first = item["ratings"][rater_ids[0]]
            second = item["ratings"][rater_ids[1]]
            first_values = [_rating_value(first, axis, label) for label in labels]
            second_values = [_rating_value(second, axis, label) for label in labels]
            if not all(value in BINARY for value in first_values + second_values):
                continue
            exact_comparable += 1
            first_set = {
                label for label, value in zip(labels, first_values) if value == "present"
            }
            second_set = {
                label for label, value in zip(labels, second_values) if value == "present"
            }
            exact_matches += first_set == second_set
        exact_set[axis] = {
            "comparable_items": exact_comparable,
            "missing_pairs": len(items) - exact_comparable,
            "matching_items": exact_matches,
            "raw_exact_set_agreement": (
                _number(exact_matches / exact_comparable)
                if exact_comparable else None
            ),
        }
    return {
        "schema": SCHEMA,
        "codebook_version": data["codebook_version"],
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "study_design": data["study_design"],
        "rater_ids": rater_ids,
        "sampling_unit": "one canonical finding per family",
        "item_count": len(items),
        "family_count": len({item["family_id"] for item in items}),
        "relevance": _nominal_axis(relevance_values, RELEVANCE),
        "multilabel_axes": axis_results,
        "exact_set_agreement": exact_set,
        "uncertainty_intervals": {
            "status": "NOT_COMPUTED",
            "reason": (
                "The preparation task has no frozen fresh sample or defensible family-"
                "cluster resampling design. A future amendment must predeclare intervals "
                "before ratings are unsealed."
            ),
        },
        "interpretation_limits": [
            "Cohen's kappa is primary because the design fixes exactly two human raters.",
            "Per-label prevalence and positive/negative agreement accompany kappa; no alternative chance coefficient is selected post hoc.",
            "Uncertain, unassessed, omitted, and null ratings are missing rather than absent.",
            "Exact-set agreement is secondary and is computed only for complete axis pairs.",
            "Agreement describes rating reproducibility, not taxonomy validity or ecosystem prevalence.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ratings", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    ratings_bytes = args.ratings.read_bytes()
    result = analyze(json.loads(ratings_bytes))
    result["ratings_input"] = {
        "path": str(args.ratings.resolve()),
        "sha256": hashlib.sha256(ratings_bytes).hexdigest(),
        "size_bytes": len(ratings_bytes),
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite agreement output: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
