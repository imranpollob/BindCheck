#!/usr/bin/env python3
"""Author-gated, one-shot S5 reserve entry point. Never use the old EVAL draw."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import (ROOT, EvaluationError, GateError, atomic_write_json,
                         load_json, read_csv, sha256_file, utc_now)
from eval.prebuild_heldout import prebuild_checkout
from eval.run_heldout import (TOOLS, acquire_once, capture_warning_sources,
                              prepare_pinned_vendor, run_tool_once)
from scripts.check_holdout import norm, reserve_decision, reserved_index

MANIFEST_SHA256 = "b1752eede4ccabaf5dea45d827fbdd0c388346349a51129b2ace125322374278"
ANALYZER_SHA256 = "753c6e2a0f3f75255eb2fdc354402f3ef7aac1541206b0794a9d09cd7d485315"
CIRCOM_SHA256 = "1bacd5583e2cc79dc1e2deaefc9c7438f21957968651c5f93dc71073c58435e3"
MANIFEST = pathlib.Path("reports/S5/reserve-manifest.csv")
SPENT = pathlib.Path("reports/heldout/selected-families.csv")
AUTHORIZATION = pathlib.Path("reports/S5/AUTHORIZATION.json")
STRATUM = {"audited-production", "deployed-address-in-docs"}
FUNNEL = {"ACQUISITION_FAILED", "BUILD_FAILED", "HARNESS_TIMEOUT", "HARNESS_ERROR", "UNSUPPORTED", "ANALYZABLE"}
RUN_TAG = "s5-reserve-run"
# S5R-02: analyzer results that mean the harness, not the application, failed.
HARNESS_FAILURE_REASONS = {"HARNESS_SUBPROCESS_FAILED", "NON_JSON_OUTPUT"}
# S5R-03: harness code sealed into the gate record; must be committed and clean at HEAD.
HARNESS_FILES = ("eval/reserve.py", "eval/common.py", "eval/run_heldout.py",
                 "eval/prebuild_heldout.py", "scripts/check_holdout.py")


def load_manifest(root: pathlib.Path = ROOT) -> list[dict[str, str]]:
    path = root / MANIFEST
    if not path.is_file() or sha256_file(path) != MANIFEST_SHA256:
        raise GateError("reserve manifest SHA-256 mismatch or missing")
    rows = read_csv(path)
    if len(rows) != 1105:
        raise GateError(f"reserve manifest has {len(rows)} rows, expected 1105")
    spent = {(norm(row["repository"]), row["commit"].lower()) for row in read_csv(root / SPENT)}
    pairs: set[tuple[str, str]] = set()
    ids: set[str] = set()
    for row in rows:
        unit_id, repository, commit = row.get("unit_id", ""), row.get("repository", ""), row.get("commit", "")
        pair = (norm(repository), commit.lower())
        if not re.fullmatch(r"reserve-\d{4}", unit_id) or unit_id in ids:
            raise GateError(f"invalid or duplicate reserve unit_id: {unit_id}")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
            raise GateError(f"invalid repository or commit in {unit_id}")
        if pair in pairs or pair in spent:
            raise GateError(f"duplicate or spent (repository, commit) in {unit_id}")
        if pair[0] == "warptoad/warp-toad":
            raise GateError("WarpToad is excluded from the reserve")
        pairs.add(pair)
        ids.add(unit_id)
    stratum_count = sum(row.get("maturity") in STRATUM for row in rows)
    if stratum_count != 390:
        raise GateError(f"reserve reporting stratum has {stratum_count} units, expected 390")
    print(f"RESERVE_STRATUM\t{stratum_count}", flush=True)
    return rows


def check_reserve_gate(root: pathlib.Path = ROOT) -> dict[str, str]:
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        if result.returncode:
            raise GateError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    head = git("rev-parse", "HEAD")
    # The run commit carries its own annotated tag; the analyzer must be
    # byte-identical to freeze 3 (oracle and harness commits may follow it).
    run_tag = git("rev-parse", f"refs/tags/{RUN_TAG}^{{}}")
    if head != run_tag:
        raise GateError(f"{RUN_TAG} tag does not equal HEAD")
    tag = git("rev-parse", "refs/tags/freeze-3^{}")
    diff = subprocess.run(["git", "diff", "--quiet", tag, head, "--", "bindcheck_zk", "freeze.sh"],
                          cwd=root, capture_output=True, check=False)
    if diff.returncode != 0:
        raise GateError("analyzer files differ from the freeze-3 tag")
    result = subprocess.run([sys.executable, "-m", "bindcheck_zk.freeze"], cwd=root,
                            text=True, capture_output=True, check=False)
    matches = re.findall(r"^BINDCHECK_ZK_CONTENT_SHA256=([0-9a-f]{64})$", result.stdout, re.M)
    if result.returncode or len(matches) != 1 or matches[0] != ANALYZER_SHA256:
        raise GateError("freeze-3 analyzer content hash mismatch")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *HARNESS_FILES],
                           cwd=root, text=True, capture_output=True, check=False)
    if dirty.returncode or dirty.stdout.strip():
        raise GateError("harness files have uncommitted changes at HEAD")
    harness = {name: sha256_file(root / name) for name in HARNESS_FILES}
    path = root / AUTHORIZATION
    if not path.is_file():
        raise GateError("author AUTHORIZATION.json is missing")
    try:
        authorization = load_json(path)
    except (OSError, ValueError) as exc:
        raise GateError("author AUTHORIZATION.json is invalid") from exc
    if not isinstance(authorization, dict) or authorization.get("manifest_sha256") != MANIFEST_SHA256:
        raise GateError("authorization manifest hash mismatch")
    if any(not isinstance(authorization.get(key), str) or not authorization[key].strip()
           for key in ("approved_by", "approved_on")):
        raise GateError("authorization lacks approved_by or approved_on")
    return {"head": head, "tag": tag, "analyzer_content_sha256": matches[0],
            "manifest_sha256": MANIFEST_SHA256, "authorization_sha256": sha256_file(path),
            "approved_by": authorization["approved_by"], "approved_on": authorization["approved_on"],
            "harness_sha256": json.dumps(harness, sort_keys=True)}


@dataclass(frozen=True)
class ReservePermit:
    root: pathlib.Path
    repositories: frozenset[str]
    gate: Mapping[str, str]
    pairs: frozenset[tuple[str, str]] = frozenset()

    def allows_pair(self, repository: str, commit: str) -> bool:
        """S5R-01: a unit must match a manifest (repository, commit) pair exactly."""
        return (norm(repository), commit.lower()) in self.pairs and self.allows(repository)

    def allows(self, repository: str) -> bool:
        # Recheck authorization, tag and analyzer at the moment of use.
        try:
            return (norm(repository) in self.repositories
                    and sha256_file(self.root / MANIFEST) == MANIFEST_SHA256
                    and norm(repository) in {norm(row["repository"]) for row in read_csv(self.root / MANIFEST)}
                    and dict(self.gate) == check_reserve_gate(self.root))
        except (GateError, OSError):
            return False


def authorized_repository(repository: str, permit: ReservePermit) -> bool:
    return reserve_decision(repository, permit) and norm(repository) in reserved_index()


def run_units(units: list[dict[str, str]], runner: Callable[[dict[str, str]], Mapping[str, Any]],
              output: pathlib.Path) -> list[dict[str, Any]]:
    """Persist one funnel row per declared unit, including runner exceptions."""
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    output.mkdir(parents=True, exist_ok=True)
    for unit in units:
        unit_id = unit["unit_id"]
        if unit_id in seen:
            raise EvaluationError(f"duplicate unit in run: {unit_id}")
        seen.add(unit_id)
        path = output / "units" / unit_id / "result.json"
        if path.exists():
            record = load_json(path)
            if record.get("repository") != unit["repository"] or record.get("commit") != unit["commit"]:
                raise EvaluationError(f"resume unit differs: {unit_id}")
        else:
            try:
                outcome = dict(runner(unit))
            except GateError:
                raise
            except Exception as exc:
                outcome = {"status": "HARNESS_ERROR", "reason": "HARNESS_INTERNAL_ERROR",
                           "detail": f"{type(exc).__name__}: {exc}"}
            if outcome.get("status") not in FUNNEL:
                raise EvaluationError(f"invalid funnel status for {unit_id}: {outcome.get('status')}")
            record = {"unit_id": unit_id, "repository": unit["repository"],
                      "commit": unit["commit"], "maturity": unit["maturity"], **outcome}
            atomic_write_json(path, record)
        records.append(record)
    if len(records) != len(units) or len({item["unit_id"] for item in records}) != len(units):
        raise EvaluationError("reserve funnel lost or duplicated a unit")
    atomic_write_json(output / "funnel.json", {
        "schema": "bindcheck-zk.reserve-funnel/v1", "manifest_sha256": MANIFEST_SHA256,
        "units": len(records), "stratum_units": sum(item["maturity"] in STRATUM for item in records),
        "status_counts": dict(sorted(Counter(item["status"] for item in records).items())),
        "results": records,
    })
    return records


def run_unit(unit: dict[str, str], output: pathlib.Path, circom: pathlib.Path,
             permit: ReservePermit) -> dict[str, Any]:
    if not authorized_repository(unit["repository"], permit):
        raise GateError(f"reserve guard refused {unit['unit_id']}")
    if not permit.allows_pair(unit["repository"], unit["commit"]):
        raise GateError(f"unit {unit['unit_id']} is not a manifest (repository, commit) pair")
    unit_dir = output / "units" / unit["unit_id"]
    unit_dir.mkdir(parents=True, exist_ok=True)
    checkout = output / "work" / unit["unit_id"]
    checkout.parent.mkdir(parents=True, exist_ok=True)
    try:
        acquisition = acquire_once(unit, unit_dir, checkout)
        if acquisition.get("status") != "ready":
            return {"status": "ACQUISITION_FAILED", "reason": acquisition.get("status")}
        prepare_pinned_vendor(checkout, unit_dir, ROOT / "node_modules/circomlib")
        prebuild = prebuild_checkout(unit, unit_dir, checkout, circom)
        atomic_write_json(unit_dir / "prebuild.json", prebuild)
        if prebuild["status"] == "BUILD_FAILED":
            return {"status": "BUILD_FAILED", "reason": "CIRCOM_PREBUILD_FAILED"}
        tools = {tool: run_tool_once(tool, checkout, unit_dir) for tool in TOOLS}
        analyzer = tools["bindcheck-zk"]
        if "HARNESS_TIMEOUT" in analyzer.get("reasons", []):
            return {"status": "HARNESS_TIMEOUT", "reason": "ANALYZER_TIMEOUT"}
        harness_failure = HARNESS_FAILURE_REASONS.intersection(analyzer.get("reasons", []))
        if harness_failure:
            return {"status": "HARNESS_ERROR", "reason": sorted(harness_failure)[0]}
        if analyzer.get("run_status") != "completed":
            return {"status": "UNSUPPORTED", "reason": analyzer.get("fatal_reason") or "ANALYZER_INCOMPLETE"}
        raw = unit_dir / "bindcheck-zk-raw.json"
        try:
            payload = load_json(raw)
        except (OSError, ValueError):
            return {"status": "HARNESS_ERROR", "reason": "ANALYZER_RAW_OUTPUT_MISSING_OR_CORRUPT"}
        # S5R-04: keep warning-location source before the checkout is deleted.
        sources = capture_warning_sources(checkout, unit_dir)
        if not payload.get("triples"):
            return {"status": "UNSUPPORTED", "reason": analyzer.get("fatal_reason") or "NO_RECOVERED_TRIPLE"}
        return {"status": "ANALYZABLE", "patterns": analyzer["patterns"], "warning_sources": sources,
                "tool_results": {name: result.get("raw_result") for name, result in tools.items()}}
    finally:
        if checkout.exists():
            shutil.rmtree(checkout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--circom", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        units = load_manifest()
        gate = check_reserve_gate()
        if not args.circom.is_file():
            raise GateError("explicit --circom executable is missing")
        circom_digest = sha256_file(args.circom)
        if circom_digest != CIRCOM_SHA256:
            raise GateError("Circom executable differs from pinned Linux 2.1.9 binary")
        permit = ReservePermit(ROOT, frozenset(norm(unit["repository"]) for unit in units), gate,
                               frozenset((norm(unit["repository"]), unit["commit"].lower()) for unit in units))
        output = ROOT / "results/raw/S5"
        output.mkdir(parents=True, exist_ok=True)
        gate_record = {**gate, "circom": str(args.circom.resolve()), "circom_sha256": circom_digest}
        gate_path = output / "reserve-gate.json"
        if gate_path.exists():
            prior = load_json(gate_path)
            if any(prior.get(key) != value for key, value in gate_record.items()):
                raise GateError("existing S5 output uses a different gate or toolchain")
        else:
            atomic_write_json(gate_path, {**gate_record, "started_utc": utc_now()})
        run_units(units, lambda unit: run_unit(unit, output, args.circom.resolve(), permit), output)
    except (EvaluationError, OSError, ValueError) as exc:
        print(f"RESERVE REFUSED: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
