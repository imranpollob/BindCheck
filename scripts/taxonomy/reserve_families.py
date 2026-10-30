#!/usr/bin/env python3
"""Privately reserve family groups for D1P-C03.

Run this program only by the human custodian in a plain terminal outside an
agent session.  The output path must be outside every Git worktree.  Standard
output contains only the salted commitment; diagnostics go to standard error.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Any


SCHEMA_VERSION = "0.2.0"
DOMAIN = b"bindcheck-d1p-c03-family-reservation-v1\0"
COMMITMENT_SCHEME = "sha256-nonce-concat-canonical-manifest-v1"
DRAW_ALGORITHM = "hmac-sha256-private-seed-sort-v1"
GROUP_KEYS = {
    "group_id",
    "candidate_application_names",
    "newly_eligible",
    "exposed",
    "tool_transfer_eligibility",
    "stratum_id",
    "grouping_basis",
}
ROOT_KEYS = {"schema_version", "grouped_at", "rounding", "groups"}
# The v0.2.0 rule reserves half of each stratum. A different fraction must be
# fixed by a frozen protocol before the grouped list exists; it is recorded in
# the private manifest so the opening shows which rule was applied.
DEFAULT_FRACTION = Fraction(1, 2)


class InputError(ValueError):
    """The grouped candidate-list input is malformed."""


def canonical_json(value: Any) -> bytes:
    """Return the protocol's canonical UTF-8 JSON representation."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_unique_json(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise InputError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read grouped list: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("grouped list must be a JSON object")
    return value


def validate_grouped_list(value: dict[str, Any]) -> list[dict[str, Any]]:
    unknown = set(value) - ROOT_KEYS
    if unknown:
        raise InputError(f"unknown top-level fields: {sorted(unknown)}")
    if set(value) != ROOT_KEYS:
        raise InputError(f"required top-level fields: {sorted(ROOT_KEYS)}")
    if value["schema_version"] != SCHEMA_VERSION:
        raise InputError(f"schema_version must be {SCHEMA_VERSION}")
    if value["rounding"] not in {"ceil_per_stratum", "floor_per_stratum"}:
        raise InputError("rounding must be fixed as ceil_per_stratum or floor_per_stratum")
    if not isinstance(value["grouped_at"], str) or not value["grouped_at"]:
        raise InputError("grouped_at must be a non-empty ISO date/date-time string")
    groups = value["groups"]
    if not isinstance(groups, list) or not groups:
        raise InputError("groups must be a non-empty array")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or set(group) != GROUP_KEYS:
            raise InputError(f"group {index} must contain exactly {sorted(GROUP_KEYS)}")
        group_id = group["group_id"]
        if not isinstance(group_id, str) or not group_id:
            raise InputError(f"group {index} has an invalid group_id")
        if group_id in seen:
            raise InputError(f"duplicate group_id: {group_id}")
        seen.add(group_id)
        names = group["candidate_application_names"]
        if not isinstance(names, list) or not names or not all(
            isinstance(name, str) and name for name in names
        ):
            raise InputError(f"group {group_id} needs name-only candidate_application_names")
        if len(names) != len(set(names)):
            raise InputError(f"group {group_id} repeats an application name")
        for field in ("newly_eligible", "exposed"):
            if not isinstance(group[field], bool):
                raise InputError(f"group {group_id}.{field} must be boolean")
        eligibility = group["tool_transfer_eligibility"]
        if eligibility not in {"eligible", "ineligible", "unknown"}:
            raise InputError(f"group {group_id} has invalid tool_transfer_eligibility")
        stratum = group["stratum_id"]
        if not isinstance(stratum, str) or not stratum:
            raise InputError(f"group {group_id} has an invalid stratum_id")
        # Eligibility is part of each stratum identity so the reserved pool
        # cannot accidentally be concentrated in unsupported systems.
        if not stratum.endswith(f":{eligibility}"):
            raise InputError(
                f"group {group_id} stratum_id must end in :{eligibility}"
            )
        if not isinstance(group["grouping_basis"], str) or not group["grouping_basis"]:
            raise InputError(f"group {group_id} needs a conservative grouping_basis")
        normalized.append(group)
    return normalized


def parse_fraction(text: str) -> Fraction:
    """Parse an exact ``p/q`` reservation fraction strictly between 0 and 1."""
    match = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", text)
    if match is None:
        raise InputError("fraction must be written as p/q with positive integers")
    fraction = Fraction(int(match.group(1)), int(match.group(2)))
    if not 0 < fraction < 1:
        raise InputError("fraction must be strictly between 0 and 1")
    return fraction


def reserve_count(size: int, rounding: str, fraction: Fraction = DEFAULT_FRACTION) -> int:
    scaled = size * fraction.numerator
    if rounding == "ceil_per_stratum":
        return -(-scaled // fraction.denominator)
    return scaled // fraction.denominator


def build_manifest(
    grouped: dict[str, Any], seed: bytes, fraction: Fraction = DEFAULT_FRACTION
) -> dict[str, Any]:
    """Build the private selection manifest from already validated input."""
    groups = validate_grouped_list(grouped)
    eligible = [g for g in groups if g["newly_eligible"] and not g["exposed"]]
    if not any(g["tool_transfer_eligibility"] == "eligible" for g in eligible):
        raise InputError(
            "newly eligible unexposed pool needs at least one tool-transfer-eligible group"
        )
    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for group in eligible:
        by_stratum.setdefault(group["stratum_id"], []).append(group)

    selected: list[str] = []
    stratum_counts: list[dict[str, Any]] = []
    for stratum_id in sorted(by_stratum):
        pool = by_stratum[stratum_id]
        ranked = sorted(
            pool,
            key=lambda group: (
                hmac.new(
                    seed,
                    DOMAIN + stratum_id.encode("utf-8") + b"\0" + group["group_id"].encode("utf-8"),
                    hashlib.sha256,
                ).digest(),
                group["group_id"],
            ),
        )
        count = reserve_count(len(pool), grouped["rounding"], fraction)
        selected.extend(group["group_id"] for group in ranked[:count])
        stratum_counts.append(
            {
                "stratum_id": stratum_id,
                "tool_transfer_eligibility": pool[0]["tool_transfer_eligibility"],
                "eligible_group_count": len(pool),
                "reserved_group_count": count,
            }
        )

    selected_by_id = {group["group_id"]: group for group in eligible}
    if not any(
        selected_by_id[group_id]["tool_transfer_eligibility"] == "eligible"
        for group_id in selected
    ):
        raise InputError(
            "fixed rounding/strata would reserve no tool-transfer-eligible group"
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "draw_algorithm": DRAW_ALGORITHM,
        "rounding": grouped["rounding"],
        "grouped_at": grouped["grouped_at"],
        "grouped_list_sha256": hashlib.sha256(canonical_json(grouped)).hexdigest(),
        "private_seed_hex": seed.hex(),
        "eligible_group_count": len(eligible),
        "reserved_group_count": len(selected),
        "strata": stratum_counts,
        "reserved_family_group_ids": sorted(selected),
    }
    # Omitted for the default so default manifests stay byte-identical to
    # those produced before the fraction option existed.
    if fraction != DEFAULT_FRACTION:
        manifest["reservation_fraction"] = f"{fraction.numerator}/{fraction.denominator}"
    return manifest


def git_worktree_roots(start: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "worktree", "list", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InputError(f"cannot enumerate Git worktrees: {exc}") from exc
    return [
        Path(line.removeprefix("worktree ")).resolve()
        for line in result.stdout.splitlines()
        if line.startswith("worktree ")
    ]


def ensure_external_output(output: Path, roots: list[Path]) -> None:
    if not output.is_absolute():
        raise InputError("--output must be an absolute path")
    resolved = output.resolve(strict=False)
    for root in roots:
        if resolved == root or resolved.is_relative_to(root):
            raise InputError("--output must be outside every Git worktree")
    if output.exists():
        raise InputError("refusing to overwrite an existing output file")
    if not output.parent.is_dir():
        raise InputError("output parent directory must already exist")


def write_private(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.write(b"\n")
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grouped_list", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--fraction",
        default="1/2",
        help="exact p/q share of each stratum to reserve, fixed by the frozen protocol (default 1/2)",
    )
    args = parser.parse_args()
    try:
        fraction = parse_fraction(args.fraction)
        grouped = load_unique_json(args.grouped_list)
        validate_grouped_list(grouped)
        ensure_external_output(args.output, git_worktree_roots(Path(__file__).resolve().parent))
        seed = secrets.token_bytes(32)
        nonce = secrets.token_bytes(32)
        manifest = build_manifest(grouped, seed, fraction)
        manifest_bytes = canonical_json(manifest)
        commitment = hashlib.sha256(nonce + manifest_bytes).hexdigest()
        envelope = canonical_json(
            {
                "commitment_scheme": COMMITMENT_SCHEME,
                "commitment_sha256": commitment,
                "nonce_hex": nonce.hex(),
                "canonical_selection_manifest": manifest,
            }
        )
        write_private(args.output, envelope)
    except InputError as exc:
        print(f"reservation aborted: {exc}", file=sys.stderr)
        return 2
    # Required privacy boundary: stdout reveals no path, nonce, seed, member,
    # count, or diagnostic—only the commitment digest.
    print(commitment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
