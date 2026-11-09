#!/usr/bin/env python3
"""Select, fetch, and run the one-shot family-level held-out evaluation.

EVAL analysis is impossible unless the annotated freeze tag, analyzer content,
dataset content, and explicit environment authorization all agree. Metadata
existence checks deliberately do not execute or clone held-out code.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
from collections import Counter
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from eval.common import (  # noqa: E402
    BASELINES,
    FETCH_TIMEOUT_SECONDS,
    METADATA_TIMEOUT_SECONDS,
    PLAN_SOURCE_SHA256,
    PATTERNS,
    ROOT,
    SOURCE_LEDGER,
    EvaluationError,
    GateError,
    atomic_write_json,
    check_eval_gate,
    directory_bytes,
    family_directory,
    load_json,
    normalize_tool_payload,
    read_csv,
    require_relative_checkout,
    run_command,
    scrub_network_environment,
    select_families,
    selection_document,
    sha256_bytes,
    sha256_file,
    summarize_command,
    tool_command,
    unknown_tool_result,
    utc_now,
    write_selection,
)
from eval.adjudicate import P4_WARNING_REASONS


TOOLS = ("bindcheck-zk", *BASELINES, "arm-c")
ARM_C_TIMEOUT_SECONDS = 390.0
EXPOSED_RANK = 259


def execution_families(selected: list[dict[str, Any]], split: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep the original draw visible while excluding the predeclared exposed family."""
    if split != "EVAL":
        return selected, []
    excluded = [item for item in selected if item["rank"] == EXPOSED_RANK]
    if len(excluded) != 1 or excluded[0]["repository"] != "selfxyz/self":
        raise EvaluationError("predeclared exposed family is absent or changed")
    return [item for item in selected if item["rank"] != EXPOSED_RANK], excluded


def default_output(split: str, dataset: pathlib.Path, metadata_only: bool) -> pathlib.Path:
    prefix = sha256_file(dataset)[:12]
    if metadata_only:
        return ROOT / "results" / "raw" / "T26" / f"eval-metadata-{prefix}"
    if split == "DEV":
        return ROOT / "results" / "raw" / "T26" / "dev-dry-run"
    return ROOT / "results" / "raw" / "T26" / f"heldout-{prefix}"


def _save_acquisition(path: pathlib.Path, value: dict[str, Any]) -> None:
    atomic_write_json(path, value)


def acquire_once(
    family: Mapping[str, Any], family_dir: pathlib.Path, checkout: pathlib.Path
) -> dict[str, Any]:
    attempt_path = family_dir / "acquisition.json"
    if attempt_path.exists():
        attempt = load_json(attempt_path)
        if attempt.get("status") == "ready" and checkout.joinpath(".git").exists():
            observed = run_command(
                ["git", "rev-parse", "HEAD"], cwd=checkout, timeout=10.0
            )
            if observed["exit_status"] == 0 and observed["stdout"].strip() == family["commit"]:
                return attempt
            attempt["status"] = "revision-mismatch-on-resume"
            attempt["resume_check"] = summarize_command(observed)
            _save_acquisition(attempt_path, attempt)
        elif attempt.get("status") == "started":
            attempt["status"] = "interrupted-attempt"
            attempt["finished_utc"] = utc_now()
            _save_acquisition(attempt_path, attempt)
        return attempt

    require_relative_checkout(checkout.parent, checkout)
    attempt: dict[str, Any] = {
        "schema": "bindcheck-zk.acquisition/v1",
        "status": "started",
        "repository": family["repository"],
        "commit": family["commit"],
        "checkout": str(checkout),
        "started_utc": utc_now(),
        "steps": [],
    }
    _save_acquisition(attempt_path, attempt)
    checkout.mkdir(parents=True, exist_ok=False)
    commands = (
        (["git", "init", "--quiet", str(checkout)], ROOT, 30.0),
        (["git", "remote", "add", "origin", f"https://github.com/{family['repository']}.git"], checkout, 30.0),
        (["git", "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", family["commit"]], checkout, FETCH_TIMEOUT_SECONDS),
        (["git", "checkout", "--quiet", "--detach", family["commit"]], checkout, FETCH_TIMEOUT_SECONDS),
        (["git", "rev-parse", "HEAD"], checkout, 10.0),
        (["git", "rev-parse", "--is-shallow-repository"], checkout, 10.0),
    )
    failure_names = ("init", "remote", "fetch", "checkout", "revision", "shallow-check")
    for name, (argv, cwd, timeout) in zip(failure_names, commands, strict=True):
        record = run_command(argv, cwd=cwd, timeout=timeout)
        attempt["steps"].append({"name": name, **summarize_command(record)})
        _save_acquisition(attempt_path, attempt)
        if record["timed_out"] or record["exit_status"] != 0:
            attempt["status"] = f"{name}-failed"
            attempt["failure_stderr_tail"] = record["stderr"][-12000:]
            attempt["finished_utc"] = utc_now()
            _save_acquisition(attempt_path, attempt)
            return attempt
        if name == "revision" and record["stdout"].strip() != family["commit"]:
            attempt["status"] = "revision-mismatch"
            attempt["observed_head"] = record["stdout"].strip()
            attempt["finished_utc"] = utc_now()
            _save_acquisition(attempt_path, attempt)
            return attempt
        if name == "shallow-check" and record["stdout"].strip() != "true":
            attempt["status"] = "not-shallow"
            attempt["finished_utc"] = utc_now()
            _save_acquisition(attempt_path, attempt)
            return attempt
    attempt["status"] = "ready"
    attempt["observed_head"] = family["commit"]
    attempt["checkout_bytes"] = directory_bytes(checkout)
    attempt["finished_utc"] = utc_now()
    _save_acquisition(attempt_path, attempt)
    return attempt


def _recover_or_unknown(
    tool: str, family_dir: pathlib.Path, reason: str
) -> dict[str, Any]:
    normalized_path = family_dir / f"{tool}.json"
    raw_path = family_dir / f"{tool}-raw.json"
    if normalized_path.exists():
        return load_json(normalized_path)
    if raw_path.exists():
        try:
            payload = load_json(raw_path)
            normalized = normalize_tool_payload(tool, payload, raw_path.name)
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            normalized = unknown_tool_result(tool, reason, str(exc))
    else:
        normalized = unknown_tool_result(tool, reason)
    atomic_write_json(normalized_path, normalized)
    return normalized


def capture_warning_sources(checkout: pathlib.Path, family_dir: pathlib.Path) -> dict[str, Any]:
    """Retain code needed for later blind cards before deleting a checkout."""
    raw_path = family_dir / "bindcheck-zk-raw.json"
    wanted: dict[str, str | None] = {}
    if raw_path.is_file():
        payload = load_json(raw_path)
        for triple in payload.get("triples", []) or []:
            warnings = [item for item in (triple.get("patterns") or {}).values()
                        if item.get("verdict") == "VIOLATION" or item.get("reason") in P4_WARNING_REASONS]
            if not warnings:
                continue
            for item in warnings:
                path = (item.get("location") or {}).get("path")
                if path:
                    wanted[str(path)] = None
            verifier = triple.get("verifier") or {}
            if verifier.get("path"):
                wanted[str(verifier["path"])] = verifier.get("sha256")
        for check in payload.get("runtime_bytecode_checks", []) or []:
            item = check.get("finding") or {}
            if item.get("verdict") == "VIOLATION" or item.get("reason") in P4_WARNING_REASONS:
                path = (item.get("location") or {}).get("path")
                if path:
                    wanted[str(path)] = None
    source_dir = family_dir / "warning-sources"
    sources = []
    for source_path, expected_sha256 in sorted(wanted.items()):
        candidate = (checkout / source_path).resolve()
        try:
            candidate.relative_to(checkout.resolve())
        except ValueError:
            sources.append({"source_path": source_path, "status": "UNSAFE_PATH"})
            continue
        if not candidate.is_file():
            sources.append({"source_path": source_path, "status": "MISSING"})
            continue
        if candidate.stat().st_size > 8 * 1024 * 1024:
            sources.append({"source_path": source_path, "status": "TOO_LARGE"})
            continue
        source_dir.mkdir(exist_ok=True)
        destination = source_dir / (sha256_bytes(source_path.encode()) + candidate.suffix)
        shutil.copy2(candidate, destination)
        observed = sha256_file(destination)
        sources.append({
            "source_path": source_path,
            "status": "COPIED" if expected_sha256 in (None, observed) else "HASH_MISMATCH",
            "expected_sha256": expected_sha256,
            "source_sha256": observed,
            "retained_path": str(destination.relative_to(family_dir)),
        })
    manifest = {"schema": "bindcheck-zk.warning-sources/v1", "sources": sources}
    atomic_write_json(family_dir / "warning-sources.json", manifest)
    return manifest


def run_tool_once(tool: str, checkout: pathlib.Path, family_dir: pathlib.Path) -> dict[str, Any]:
    normalized_path = family_dir / f"{tool}.json"
    attempt_path = family_dir / f"{tool}-attempt.json"
    raw_path = family_dir / f"{tool}-raw.json"
    if normalized_path.exists():
        return load_json(normalized_path)
    if attempt_path.exists():
        attempt = load_json(attempt_path)
        reason = "INTERRUPTED_ATTEMPT" if attempt.get("status") == "started" else "UNNORMALIZED_ATTEMPT"
        return _recover_or_unknown(tool, family_dir, reason)
    if tool == "zkap" and shutil.which("zkap") is None:
        result = unknown_tool_result(tool, "BASELINE_TOOL_UNAVAILABLE", "zkap is not installed")
        atomic_write_json(normalized_path, result)
        return result

    if tool == "arm-c":
        argv, timeout = [sys.executable, str(ROOT / "eval/run_arm_c.py"), str(checkout), str(family_dir / "arm-c-native")], ARM_C_TIMEOUT_SECONDS
    else:
        argv, timeout = tool_command(tool, checkout)
    attempt = {
        "schema": "bindcheck-zk.tool-attempt/v1",
        "tool": tool,
        "status": "started",
        "started_utc": utc_now(),
        "argv": argv,
        "timeout_seconds": timeout,
    }
    atomic_write_json(attempt_path, attempt)
    if tool == "picus":
        with tempfile.TemporaryDirectory(prefix="picus-", dir=family_dir) as temporary:
            record = run_command(
                argv, cwd=ROOT, timeout=timeout,
                env={**scrub_network_environment(), "TMPDIR": temporary},
            )
    else:
        record = run_command(
            argv, cwd=ROOT, timeout=timeout, env=scrub_network_environment()
        )
    if tool == "arm-c":
        picus_temps = family_dir / "arm-c-native" / "B" / "picus-tmp"
        if picus_temps.exists():
            shutil.rmtree(picus_temps)
        record["picus_temp_removed"] = not picus_temps.exists()
    raw_text = record["stdout"]
    raw_path.write_text(raw_text, encoding="utf-8")
    attempt.update({
        "status": "finished",
        "finished_utc": utc_now(),
        "command": summarize_command(record),
        "stderr_tail": record["stderr"][-12000:],
        "raw_result": raw_path.name,
        "raw_result_sha256": sha256_file(raw_path),
    })
    atomic_write_json(attempt_path, attempt)
    if record["timed_out"]:
        normalized = unknown_tool_result(tool, "HARNESS_TIMEOUT")
    else:
        try:
            payload = json.loads(raw_text)
            normalized = normalize_tool_payload(tool, payload, raw_path.name)
            if record["exit_status"] not in (0, 2):
                normalized = unknown_tool_result(
                    tool, "HARNESS_SUBPROCESS_FAILED", f"exit status {record['exit_status']}"
                )
        except json.JSONDecodeError as exc:
            normalized = unknown_tool_result(tool, "NON_JSON_OUTPUT", str(exc))
    atomic_write_json(normalized_path, normalized)
    return normalized


def analyze_family(
    family: Mapping[str, Any], output: pathlib.Path
) -> dict[str, Any]:
    family_dir = family_directory(output, family)
    family_dir.mkdir(parents=True, exist_ok=True)
    result_path = family_dir / "family-result.json"
    if result_path.exists():
        return load_json(result_path)
    atomic_write_json(family_dir / "family.json", dict(family))
    work_root = output / "work"
    work_root.mkdir(parents=True, exist_ok=True)
    checkout = work_root / f"{int(family['rank']):03d}-{family['sample_hash'][:12]}"
    tools: dict[str, dict[str, Any]] = {}
    acquisition: dict[str, Any]
    try:
        acquisition = acquire_once(family, family_dir, checkout)
        if acquisition.get("status") != "ready":
            reason = "ACQUISITION_" + str(acquisition.get("status", "failed")).upper().replace("-", "_")
            for tool in TOOLS:
                tools[tool] = _recover_or_unknown(tool, family_dir, reason)
        else:
            for tool in TOOLS:
                tools[tool] = run_tool_once(tool, checkout, family_dir)
            try:
                capture_warning_sources(checkout, family_dir)
            except Exception as exc:
                atomic_write_json(family_dir / "warning-sources-error.json", {
                    "type": type(exc).__name__, "detail": str(exc), "recorded_utc": utc_now()
                })
    except Exception as exc:  # one family failure is coverage, not a changed-settings retry
        acquisition = load_json(family_dir / "acquisition.json") if family_dir.joinpath("acquisition.json").exists() else {"status": "harness-error"}
        for tool in TOOLS:
            tools[tool] = _recover_or_unknown(tool, family_dir, "HARNESS_INTERNAL_ERROR")
        atomic_write_json(family_dir / "harness-error.json", {
            "type": type(exc).__name__, "detail": str(exc), "recorded_utc": utc_now()
        })
    finally:
        require_relative_checkout(work_root, checkout)
        if checkout.exists():
            shutil.rmtree(checkout)

    result = {
        "schema": "bindcheck-zk.family-result/v1",
        "family": dict(family),
        "acquisition_status": acquisition.get("status"),
        "checkout_deleted": not checkout.exists(),
        "tools": tools,
        "completed_utc": utc_now(),
    }
    atomic_write_json(result_path, result)
    return result


def metadata_check_family(
    family: Mapping[str, Any], output: pathlib.Path
) -> dict[str, Any]:
    family_dir = family_directory(output, family)
    family_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(family_dir / "family.json", dict(family))
    result_path = family_dir / "metadata.json"
    if result_path.exists():
        return load_json(result_path)
    argv = [
        "gh", "api", "--method", "GET",
        f"repos/{family['repository']}/commits/{family['commit']}",
        "--jq", ".sha",
    ]
    attempt_path = family_dir / "metadata-attempt.json"
    if attempt_path.exists():
        result = {
            "schema": "bindcheck-zk.commit-metadata/v1",
            "status": "INTERRUPTED_ATTEMPT",
            "repository": family["repository"],
            "commit": family["commit"],
        }
        atomic_write_json(result_path, result)
        return result
    atomic_write_json(attempt_path, {
        "schema": "bindcheck-zk.metadata-attempt/v1", "status": "started",
        "started_utc": utc_now(), "argv": argv,
    })
    record = run_command(argv, cwd=ROOT, timeout=METADATA_TIMEOUT_SECONDS)
    observed = record["stdout"].strip()
    status = "EXISTS" if (
        not record["timed_out"]
        and record["exit_status"] == 0
        and observed.lower() == str(family["commit"]).lower()
    ) else "UNAVAILABLE"
    result = {
        "schema": "bindcheck-zk.commit-metadata/v1",
        "status": status,
        "repository": family["repository"],
        "commit": family["commit"],
        "observed_sha": observed,
        "command": summarize_command(record),
        "stderr_tail": record["stderr"][-4000:],
        "checked_utc": utc_now(),
        "clone_performed": False,
        "analysis_performed": False,
    }
    atomic_write_json(result_path, result)
    atomic_write_json(attempt_path, {
        "schema": "bindcheck-zk.metadata-attempt/v1", "status": "finished",
        "started_utc": load_json(attempt_path)["started_utc"], "finished_utc": utc_now(),
        "command": summarize_command(record),
    })
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--split", required=True, choices=("DEV", "EVAL"))
    result.add_argument("--dataset", type=pathlib.Path, default=SOURCE_LEDGER)
    result.add_argument("--output", type=pathlib.Path)
    result.add_argument("--max-families", type=int)
    result.add_argument("--metadata-only", action="store_true")
    result.add_argument("--preflight", action="store_true")
    result.add_argument("--selection-only", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    split = args.split.upper()
    dataset = args.dataset.resolve()
    if args.metadata_only and split != "EVAL":
        raise SystemExit("--metadata-only is EVAL-only")
    if args.max_families is not None and split != "DEV":
        raise SystemExit("--max-families is DEV-only")
    if args.preflight and split != "EVAL":
        raise SystemExit("--preflight is EVAL-only")

    gate = None
    if split == "EVAL" and not args.metadata_only and not args.selection_only:
        try:
            gate = check_eval_gate(ROOT, dataset)
        except GateError as exc:
            print(f"EVAL REFUSED: {exc}", file=sys.stderr)
            return 3
        if args.preflight:
            print(json.dumps(gate, indent=2, sort_keys=True))
            return 0
    if split == "EVAL" and args.metadata_only and sha256_file(dataset) != PLAN_SOURCE_SHA256:
        print(
            "EVAL metadata check refused: dataset differs from the preregistered plan hash",
            file=sys.stderr,
        )
        return 3

    output = (args.output or default_output(split, dataset, args.metadata_only)).resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = read_csv(dataset)
    selected = select_families(rows, split, max_families=args.max_families)
    executable, exclusions = execution_families(selected, split)
    selection = selection_document(selected, split=split, dataset=dataset)
    write_selection(output, selection)
    selection_hash = sha256_file(output / "selected-families.json")
    manifest_path = output / "run-manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        if manifest.get("selection_sha256") != selection_hash:
            raise SystemExit("existing run manifest has a different selection")
    else:
        manifest = {
            "schema": "bindcheck-zk.heldout-run/v1",
            "split": split,
            "mode": "metadata-only" if args.metadata_only else ("selection-only" if args.selection_only else "analysis"),
            "started_utc": utc_now(),
            "selection_sha256": selection_hash,
            "dataset_sha256": sha256_file(dataset),
            "draw_families": len(selected),
            "excluded_before_analysis": [
                {"rank": item["rank"], "family_id": item["family_id"],
                 "repository": item["repository"], "commit": item["commit"],
                 "reason": "EXPOSED_GATE_REVIEW"}
                for item in exclusions
            ],
            "gate": gate,
            "fixed_limits_seconds": {
                "fetch_each": FETCH_TIMEOUT_SECONDS,
                "checkout_each": FETCH_TIMEOUT_SECONDS,
                "analyzer_outer": 150.0,
                "baseline_inner": 120.0,
                "baseline_outer": 150.0,
                "arm_c_outer": ARM_C_TIMEOUT_SECONDS,
            },
            "no_retry_policy": "one attempt per acquisition/tool; interrupted or failed attempts become UNKNOWN",
        }
        atomic_write_json(manifest_path, manifest)
    if args.selection_only:
        print(json.dumps({"selection": str(output), "families": len(selected)}, indent=2))
        return 0

    results = []
    for family in (selected if args.metadata_only else executable):
        if args.metadata_only:
            item = metadata_check_family(family, output)
            print(f"METADATA\t{family['rank']:03d}\t{item['status']}\t{family['repository']}@{family['commit']}", flush=True)
        else:
            item = analyze_family(family, output)
            bindcheck = item["tools"]["bindcheck-zk"]
            pattern_status = ",".join(f"{pattern}:{bindcheck['patterns'][pattern]['verdict']}/{bindcheck['patterns'][pattern]['applicability']}" for pattern in PATTERNS)
            print(f"FAMILY\t{family['rank']:03d}\t{pattern_status}\t{family['repository']}@{family['commit']}", flush=True)
        results.append(item)

    if args.metadata_only:
        counts = Counter(item["status"] for item in results)
        completed = {
            "completed_utc": utc_now(), "families": len(results),
            "metadata_statuses": dict(sorted(counts.items())),
            "clone_performed": False, "analysis_performed": False,
        }
        exit_status = 0 if counts.get("EXISTS", 0) == len(results) else 1
    else:
        verdicts = {
            pattern: dict(sorted(Counter(
                (item["tools"]["bindcheck-zk"]["patterns"][pattern]["verdict"],
                 item["tools"]["bindcheck-zk"]["patterns"][pattern]["applicability"])
                for item in results
            ).items()))
            for pattern in PATTERNS
        }
        work_root = output / "work"
        completed = {
            "completed_utc": utc_now(), "families": len(results),
            "bindcheck_pattern_verdict_applicability": {
                pattern: {f"{verdict}/{applicability}": count for (verdict, applicability), count in counts.items()}
                for pattern, counts in verdicts.items()
            },
            "clones_remaining": len(list(work_root.iterdir())) if work_root.exists() else 0,
        }
        exit_status = 0
    manifest.update(completed)
    atomic_write_json(manifest_path, manifest)
    print(json.dumps(completed, indent=2, sort_keys=True))
    return exit_status


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
