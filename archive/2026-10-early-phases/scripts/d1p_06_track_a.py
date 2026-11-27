#!/usr/bin/env python3
"""Preflight, freeze, and execute the bounded native-macOS D1P-06 Track A.

The process launcher and sampled process-tree RSS monitor are imported from
the frozen D1P-05 runner.  This module adds the Track A schedule, equal slot
budgets, freezes, aggregate ledger, and equivalence-contradiction checks.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
D1P05_RUNNER = ROOT / "scripts/d1p_05_validate.py"
INPUT_MANIFEST = ROOT / "metadata/d1/d1p-06-input-manifest.json"
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-06-resource-policy.json"
PROTOCOL = ROOT / "docs/d1-paper/d1p-06-protocol.md"
D1P04_MANIFEST = ROOT / "metadata/d1/d1p-04-artifact-manifest.json"
D1P05_LEDGER = ROOT / "metadata/d1/d1p-05-equivalence-ledger.json"
EXPECTED_D1P05_RUNNER = "16cc0ae39e7ff3a01439b3c168e4bede93ab53b25bfc1d6b3d27efb3a8651d55"
EXPECTED_SOLVER = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGUMENTS = ("--lang=smt2", "--ff-solver=split")
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05
CONTROL_SECONDS = 30.0
UNSPLIT_SECONDS = 300.0
PARTITION_SLOT_SECONDS = 300.0
CELL_SECONDS = 12.0
CONTROL_AGGREGATE_SECONDS = 60.0
PRIMARY_AGGREGATE_SECONDS = 6000.0
CONTROL_CALLS_MAX = 2
PRIMARY_CALLS_MAX = 164


def load_d1p05():
    spec = importlib.util.spec_from_file_location("d1p_05_validate", D1P05_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D1P05 = load_d1p05()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def run_capture(argv):
    completed = subprocess.run(
        [str(part) for part in argv], capture_output=True, text=True,
        timeout=30, check=False,
    )
    return {
        "argv": [str(part) for part in argv], "exit_status": completed.returncode,
        "stdout": completed.stdout, "stderr": completed.stderr,
    }


def platform_identity():
    return {
        "platform": platform.platform(), "system": platform.system(),
        "release": platform.release(), "machine": platform.machine(),
        "python": platform.python_version(), "python_executable": sys.executable,
    }


def ordered_hash_digest(items):
    return sha256_bytes("".join(item["sha256"] + "\n" for item in items).encode())


def all_input_items(manifest):
    yield from manifest["controls"]
    yield from manifest["goal_only"]
    yield from manifest["cone_only"]
    yield from manifest["combined"]
    for group in manifest["partitioned"]:
        yield from group["cells"]


def verify_inputs(manifest_path=INPUT_MANIFEST):
    manifest = json.loads(Path(manifest_path).read_text())
    expected_counts = {
        "controls": 2, "goal_only": 6, "cone_only": 2, "combined": 6,
        "partitioned_slots": 6, "partitioned_cells": 150,
        "primary_calls_max": 164, "calls_with_controls_max": 166,
    }
    if manifest.get("counts") != expected_counts:
        raise RuntimeError(f"unexpected input counts: {manifest.get('counts')}")
    if sha256(D1P05_RUNNER) != EXPECTED_D1P05_RUNNER:
        raise RuntimeError("D1P-05 runner identity mismatch")
    d1p05 = json.loads(D1P05_LEDGER.read_text())
    if not d1p05.get("partition_eligible_for_primary_use"):
        raise RuntimeError("D1P-05 complete partition is not eligible")
    checked = 0
    for item in all_input_items(manifest):
        path = ROOT / item["path"]
        actual = sha256(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"input hash mismatch {item.get('slot', item.get('name'))}: {actual}")
        checked += 1
    if checked != 166:
        raise RuntimeError(f"unexpected checked input count: {checked}")
    return manifest, checked


def linked_libraries(solver):
    command = run_capture(["/usr/bin/otool", "-L", solver])
    libraries = []
    if command["exit_status"] == 0:
        for line in command["stdout"].splitlines()[1:]:
            install_name = line.strip().split(" (", 1)[0]
            candidate = None
            if install_name.startswith("@rpath/"):
                candidate = solver.parent.parent / "lib" / install_name[len("@rpath/"):]
            elif install_name.startswith("@loader_path/"):
                candidate = solver.parent / install_name[len("@loader_path/"):]
            elif install_name.startswith("/"):
                candidate = Path(install_name)
            entry = {"install_name": install_name, "resolved_path": None,
                     "sha256": None, "file_available": False}
            if candidate is not None:
                candidate = candidate.resolve()
                entry["resolved_path"] = str(candidate)
                if candidate.is_file():
                    entry["file_available"] = True
                    entry["sha256"] = sha256(candidate)
            libraries.append(entry)
    return command, libraries


def host_inventory(solver):
    hardware_raw = run_capture([
        "/usr/sbin/system_profiler", "SPHardwareDataType", "-json",
    ])
    hardware = {
        "argv": hardware_raw["argv"],
        "exit_status": hardware_raw["exit_status"],
        "stderr": hardware_raw["stderr"],
        "fields": {},
    }
    if hardware_raw["exit_status"] == 0:
        parsed = json.loads(hardware_raw["stdout"])["SPHardwareDataType"][0]
        hardware["fields"] = {
            key: parsed.get(key) for key in (
                "chip_type", "machine_model", "machine_name",
                "number_processors", "physical_memory",
            )
        }
    commands = {
        "sw_vers": run_capture(["/usr/bin/sw_vers"]),
        "uname": run_capture(["/usr/bin/uname", "-a"]),
        "hardware": hardware,
        "solver_file": run_capture(["/usr/bin/file", str(solver)]),
    }
    otool, libraries = linked_libraries(solver)
    commands["solver_otool"] = otool
    return {"platform": platform_identity(), "commands": commands,
            "linked_libraries": libraries}


def preflight(args):
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh preflight namespace required: {output}")
    output.mkdir(parents=True)
    started = time.monotonic()
    checks = {}
    failures = []
    solver = args.solver.resolve()
    try:
        checks["native_macos_arm64"] = (
            platform.system() == "Darwin" and platform.machine() == "arm64"
        )
        checks["solver_exists"] = solver.is_file() and os.access(solver, os.X_OK)
        if not checks["native_macos_arm64"]:
            failures.append("reference platform is not native macOS arm64")
        if not checks["solver_exists"]:
            failures.append(f"solver is missing or not executable: {solver}")
        if failures:
            raise RuntimeError("; ".join(failures))
        checks["solver_hash"] = sha256(solver) == EXPECTED_SOLVER
        if not checks["solver_hash"]:
            raise RuntimeError(f"solver hash mismatch: {sha256(solver)}")
        manifest, checked = verify_inputs(args.manifest.resolve())
        checks["input_hashes"] = checked == 166
        checks["resource_policy"] = (
            json.loads(args.resource_policy.read_text())["limitations"]["hard_address_space_cap"] is False
        )
        if not checks["resource_policy"]:
            raise RuntimeError("resource policy is not the sampled macOS policy")
        helper_output = output / "helpers"
        helper_exit = D1P05.infrastructure_check(helper_output)
        helper_summary = json.loads((helper_output / "infrastructure-check.json").read_text())
        checks["harmless_helper_gate"] = helper_exit == 0 and helper_summary["status"] == "PASS"
        if not checks["harmless_helper_gate"]:
            raise RuntimeError("harmless-helper infrastructure gate failed")
        inventory = host_inventory(solver)
        checks["identity_commands"] = all(
            value["exit_status"] == 0 for value in inventory["commands"].values()
        )
        if not checks["identity_commands"]:
            raise RuntimeError("one or more environment identity commands failed")
        status = "PASS"
        error = None
    except Exception as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {exc}"
        inventory = host_inventory(solver) if solver.is_file() else {
            "platform": platform_identity(), "commands": {}, "linked_libraries": []
        }
        manifest = None
        checked = 0
    record = {
        "task": "D1P-06", "kind": "pre-freeze native-macOS preflight",
        "status": status, "error": error, "research_result": False,
        "solver_queries": 0, "started_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "checks": checks, "inputs_checked": checked,
        "input_manifest": {"path": relative(args.manifest),
                           "sha256": sha256(args.manifest)},
        "solver": {"path": str(solver),
                   "sha256": sha256(solver) if solver.is_file() else None,
                   "arguments": list(SOLVER_ARGUMENTS),
                   "version": "cvc5 1.4.2 arm64 GPL/CoCoA (recorded D1P-05 provenance)"},
        "environment": inventory,
        "resource_policy": {"path": relative(args.resource_policy),
                            "sha256": sha256(args.resource_policy)},
        "helper_check": ({"path": relative(output / "helpers/infrastructure-check.json"),
                          "sha256": sha256(output / "helpers/infrastructure-check.json")}
                         if (output / "helpers/infrastructure-check.json").is_file() else None),
        "limitations": [
            "sampled RSS cutoff is not a hard address-space cap",
            "sampling can overshoot and miss short-lived activity",
            "this is a native-macOS reference, not historical Linux parity",
        ],
    }
    write_json(output / "preflight.json", record)
    print(json.dumps({"status": status, "checks": checks,
                      "inputs_checked": checked}, sort_keys=True))
    return 0 if status == "PASS" else 2


def freeze(args):
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh freeze required: {output}")
    preflight_path = args.preflight.resolve()
    preflight_record = json.loads(preflight_path.read_text())
    if preflight_record.get("status") != "PASS":
        raise RuntimeError("cannot freeze after failed preflight")
    manifest, checked = verify_inputs(args.manifest.resolve())
    solver = Path(preflight_record["solver"]["path"])
    if sha256(solver) != EXPECTED_SOLVER:
        raise RuntimeError("solver changed after preflight")
    flat = list(all_input_items(manifest))
    value = {
        "task": "D1P-06", "status": "FROZEN_BEFORE_SOLVER_EXECUTION",
        "frozen_at_utc": utc_now(),
        "repository_head": run_capture(["/usr/bin/git", "rev-parse", "HEAD"])["stdout"].strip(),
        "scope": "native-macOS reference Track A producer-decomposition experiment",
        "reference_environment": preflight_record["environment"],
        "historical_linux_timing_parity": False,
        "solver": preflight_record["solver"],
        "resource_policy": {
            "path": relative(args.resource_policy), "sha256": sha256(args.resource_policy),
            "metric": "sampled aggregate recursive process-tree RSS",
            "hard_address_space_cap": False, "sampling_can_overshoot": True,
        },
        "preflight": {"path": relative(preflight_path), "sha256": sha256(preflight_path),
                      "status": "PASS", "solver_queries": 0},
        "input_manifest": {"path": relative(args.manifest),
                           "sha256": sha256(args.manifest), "inputs_checked": checked},
        "limits": {
            "controls_max": CONTROL_CALLS_MAX, "control_seconds": CONTROL_SECONDS,
            "control_aggregate_seconds": CONTROL_AGGREGATE_SECONDS,
            "primary_calls_max": PRIMARY_CALLS_MAX,
            "primary_aggregate_seconds": PRIMARY_AGGREGATE_SECONDS,
            "unsplit_slot_seconds": UNSPLIT_SECONDS,
            "partitioned_slot_seconds": PARTITION_SLOT_SECONDS,
            "partitioned_cell_seconds": CELL_SECONDS,
            "rss_cutoff_bytes": RSS_CUTOFF,
            "rss_sample_interval_seconds": SAMPLE_INTERVAL,
            "attempts_per_query": 1, "sequential": True,
        },
        "call_order": manifest["ordering"],
        "ordered_input_hashes": {
            "count": len(flat), "sha256": ordered_hash_digest(flat),
            "controls": ordered_hash_digest(manifest["controls"]),
            "goal_only": ordered_hash_digest(manifest["goal_only"]),
            "cone_only": ordered_hash_digest(manifest["cone_only"]),
            "combined": ordered_hash_digest(manifest["combined"]),
            "partitioned": ordered_hash_digest([
                cell for group in manifest["partitioned"] for cell in group["cells"]
            ]),
        },
        "frozen_files": [
            {"path": relative(path), "sha256": sha256(path)} for path in (
                Path(__file__), ROOT / "scripts/d1p_06_prepare.py", PROTOCOL,
                args.resource_policy.resolve(), args.manifest.resolve(),
                D1P05_RUNNER, D1P04_MANIFEST, D1P05_LEDGER,
            )
        ],
        "stop_rules": [
            "controls first; failure stops",
            "identity corruption or launch/monitor failure stops",
            "timeout, sampled memory cutoff, UNKNOWN, or solver error is unresolved without retry",
            "contradiction between D1P-05-validated equivalent formulas stops",
            "partition SAT requires preserved witness output; partition UNSAT requires 25 UNSAT cells",
        ],
        "interpretation": (
            "Within-campaign macOS comparison only; historical Linux is background. "
            "Track A does not establish consumer-direction effectiveness or a D1 verdict."
        ),
    }
    write_json(output, value)
    print(json.dumps({"status": value["status"], "inputs": len(flat),
                      "freeze": relative(output)}, sort_keys=True))
    return 0


def verify_freeze(freeze_path, freeze_record, manifest_path, resource_policy_path):
    if platform_identity() != freeze_record["reference_environment"]["platform"]:
        raise RuntimeError("reference platform identity changed")
    for item in freeze_record["frozen_files"]:
        actual = sha256(ROOT / item["path"])
        if actual != item["sha256"]:
            raise RuntimeError(f"frozen file mismatch {item['path']}: {actual}")
    if sha256(manifest_path) != freeze_record["input_manifest"]["sha256"]:
        raise RuntimeError("input manifest changed")
    if sha256(resource_policy_path) != freeze_record["resource_policy"]["sha256"]:
        raise RuntimeError("resource policy changed")
    if sha256(freeze_record["solver"]["path"]) != freeze_record["solver"]["sha256"]:
        raise RuntimeError("solver binary changed")
    preflight_path = ROOT / freeze_record["preflight"]["path"]
    if sha256(preflight_path) != freeze_record["preflight"]["sha256"]:
        raise RuntimeError("preflight record changed")
    preflight_record = json.loads(preflight_path.read_text())
    if preflight_record.get("status") != "PASS":
        raise RuntimeError("frozen preflight is not PASS")
    manifest, checked = verify_inputs(manifest_path)
    return manifest, checked


def parse_result(stdout_path):
    lines = Path(stdout_path).read_text(errors="replace").splitlines()
    if not lines:
        return "missing", False
    parsed = lines[0].strip().lower()
    if parsed not in ("sat", "unsat", "unknown"):
        return "malformed", False
    witness = parsed == "sat" and any(line.strip() for line in lines[1:])
    return parsed, witness


def unrun(index, arm, name, path, digest, reason):
    return {
        "index": index, "arm": arm, "name": name, "query_path": path,
        "query_sha256": digest, "attempts": 0, "status": "UNRUN",
        "result": "UNRUN", "reason": reason,
    }


def run_query(index, arm, name, item, timeout, solver, logs, monitor):
    record = D1P05.run_monitored(
        index=index, kind=arm, name=name,
        argv=[solver, *SOLVER_ARGUMENTS], logs_dir=logs, monitor=monitor,
        input_path=ROOT / item["path"], timeout_seconds=timeout,
        rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL,
    )
    parsed, witness = parse_result(ROOT / record["stdout_path"])
    record.update({
        "arm": arm, "attempts": 1, "query_path": item["path"],
        "query_sha256": item["sha256"], "parsed": parsed,
        "sat_witness_output_preserved": witness,
        "validated_full_acir_evidence": False,
        "result": (parsed.upper() if record["status"] == "COMPLETED"
                   and record["exit_status"] == 0
                   and parsed in ("sat", "unsat", "unknown") else "UNKNOWN"),
    })
    D1P05.write_json(ROOT / record["record_path"], record)
    return record


def infrastructure_failure(record):
    return record["status"] in ("LAUNCH_ERROR", "MONITOR_ERROR")


def result_counts(records):
    return {
        "sat": sum(r.get("result") == "SAT" for r in records),
        "unsat": sum(r.get("result") == "UNSAT" for r in records),
        "unknown": sum(r.get("attempts") == 1 and r.get("result") in ("UNKNOWN",)
                       for r in records),
        "unrun": sum(r.get("attempts") == 0 for r in records),
    }


def summarize_partition(slot, records, slot_elapsed):
    counts = result_counts(records)
    sat_with_witness = any(
        r.get("result") == "SAT" and r.get("sat_witness_output_preserved")
        for r in records
    )
    if sat_with_witness:
        result = "SAT"
    elif counts["unsat"] == 25:
        result = "UNSAT"
    else:
        result = "UNKNOWN"
    attempted = [r for r in records if r.get("attempts") == 1]
    solver_elapsed = sum(r.get("elapsed_seconds", 0) for r in attempted)
    return {
        "slot": slot, "result": result, "counts": counts,
        "slot_elapsed_seconds": round(slot_elapsed, 6),
        "solver_call_elapsed_seconds": round(solver_elapsed, 6),
        "charged_overhead_seconds": round(max(0.0, slot_elapsed - solver_elapsed), 6),
        "observed_peak_tree_rss_bytes": max(
            (r.get("peak_tree_rss_bytes", 0) for r in attempted), default=0
        ),
        "sat_witness_output_preserved": sat_with_witness,
        "validated_full_acir_evidence": False,
    }


def execute(args):
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    if output.exists() or ledger_path.exists():
        raise FileExistsError("fresh execution namespace and ledger required")
    output.mkdir(parents=True)
    logs = output / "calls"
    logs.mkdir()
    started = time.monotonic()
    records = []
    partition_summaries = []
    unsplit_summaries = []
    stop_reason = None
    freeze_path = args.freeze.resolve()
    freeze_record = json.loads(freeze_path.read_text())
    try:
        manifest, checked = verify_freeze(
            freeze_path, freeze_record, args.manifest.resolve(),
            args.resource_policy.resolve(),
        )
        monitor = D1P05.MacProcessTreeMonitor()
        solver = Path(freeze_record["solver"]["path"])
    except Exception as exc:
        stop_reason = f"pre-execution infrastructure failure: {type(exc).__name__}: {exc}"
        manifest = json.loads(args.manifest.read_text())
        checked = 0
        monitor = None
        solver = Path(freeze_record["solver"]["path"])

    index = 0
    control_started = time.monotonic()
    for item in manifest["controls"]:
        index += 1
        if stop_reason:
            records.append(unrun(index, "control", item["name"], item["path"], item["sha256"], stop_reason))
            continue
        remaining = CONTROL_AGGREGATE_SECONDS - (time.monotonic() - control_started)
        if remaining <= 0:
            stop_reason = "control aggregate budget exhausted"
            records.append(unrun(index, "control", item["name"], item["path"], item["sha256"], stop_reason))
            continue
        record = run_query(index, "control", item["name"], item,
                           min(CONTROL_SECONDS, remaining), solver, logs, monitor)
        record["expected"] = item["expected"]
        record["control_pass"] = record["result"].lower() == item["expected"]
        D1P05.write_json(ROOT / record["record_path"], record)
        records.append(record)
        if not record["control_pass"]:
            stop_reason = (f"failed control {item['name']}: status={record['status']} "
                           f"result={record['result']} exit={record['exit_status']}")
        elif infrastructure_failure(record):
            stop_reason = f"control infrastructure failure: {item['name']}"

    primary_started = time.monotonic()
    combined_results = {}
    for arm, items in (("goal_only", manifest["goal_only"]),
                       ("cone_only", manifest["cone_only"]),
                       ("combined", manifest["combined"])):
        for item in items:
            index += 1
            name = item["slot"]
            if stop_reason:
                records.append(unrun(index, arm, name, item["path"], item["sha256"], stop_reason))
                continue
            slot_started = time.monotonic()
            global_remaining = PRIMARY_AGGREGATE_SECONDS - (slot_started - primary_started)
            if global_remaining <= 0:
                stop_reason = "primary aggregate budget exhausted"
                records.append(unrun(index, arm, name, item["path"], item["sha256"], stop_reason))
                continue
            record = run_query(index, arm, name, item,
                               min(UNSPLIT_SECONDS, global_remaining), solver, logs, monitor)
            record["anticipated_result_not_observation"] = item["anticipated_result_not_observation"]
            slot_elapsed = time.monotonic() - slot_started
            record["slot_elapsed_seconds"] = round(slot_elapsed, 6)
            record["charged_overhead_seconds"] = round(
                max(0.0, slot_elapsed - record["elapsed_seconds"]), 6
            )
            D1P05.write_json(ROOT / record["record_path"], record)
            records.append(record)
            unsplit_summaries.append({
                "arm": arm, "slot": name, "result": record["result"],
                "slot_elapsed_seconds": record["slot_elapsed_seconds"],
                "solver_call_elapsed_seconds": record["elapsed_seconds"],
                "charged_overhead_seconds": record["charged_overhead_seconds"],
                "observed_peak_tree_rss_bytes": record["peak_tree_rss_bytes"],
                "sat_witness_output_preserved": record["sat_witness_output_preserved"],
                "validated_full_acir_evidence": False,
            })
            if arm == "combined":
                combined_results[name] = record["result"]
            if infrastructure_failure(record):
                stop_reason = f"infrastructure failure in {arm}/{name}: {record['status']}"
            write_json(output / "progress.json", {
                "status": "IN_PROGRESS" if not stop_reason else "STOPPING",
                "last_index": index, "last_arm": arm, "last_name": name,
                "stop_reason": stop_reason,
            })

    for group in manifest["partitioned"]:
        slot = group["slot"]
        slot_started = time.monotonic()
        cell_records = []
        slot_stop = None
        for item in group["cells"]:
            index += 1
            name = f"{slot}/{item['id']}"
            if stop_reason or slot_stop:
                reason = stop_reason or slot_stop
                record = unrun(index, "partitioned", name, item["path"], item["sha256"], reason)
                records.append(record)
                cell_records.append(record)
                continue
            slot_remaining = PARTITION_SLOT_SECONDS - (time.monotonic() - slot_started)
            global_remaining = PRIMARY_AGGREGATE_SECONDS - (time.monotonic() - primary_started)
            if slot_remaining <= 0 or global_remaining <= 0:
                reason = ("partitioned slot budget exhausted" if slot_remaining <= 0
                          else "primary aggregate budget exhausted")
                record = unrun(index, "partitioned", name, item["path"], item["sha256"], reason)
                records.append(record)
                cell_records.append(record)
                continue
            record = run_query(
                index, "partitioned", name, item,
                min(CELL_SECONDS, slot_remaining, global_remaining),
                solver, logs, monitor,
            )
            records.append(record)
            cell_records.append(record)
            if infrastructure_failure(record):
                stop_reason = f"infrastructure failure in partitioned/{name}: {record['status']}"
            elif record["result"] == "SAT" and record["sat_witness_output_preserved"]:
                slot_stop = "partition SAT witness preserved; later cells not needed"
                if combined_results.get(slot) == "UNSAT":
                    stop_reason = f"equivalent-formula contradiction: combined UNSAT, cell SAT: {name}"
            write_json(output / "progress.json", {
                "status": "IN_PROGRESS" if not stop_reason else "STOPPING",
                "last_index": index, "last_arm": "partitioned", "last_name": name,
                "stop_reason": stop_reason, "slot_stop": slot_stop,
            })
        summary = summarize_partition(slot, cell_records, time.monotonic() - slot_started)
        partition_summaries.append(summary)
        if summary["result"] == "UNSAT" and combined_results.get(slot) == "SAT":
            stop_reason = f"equivalent-formula contradiction: combined SAT, partition UNSAT: {slot}"

    if index != 166:
        stop_reason = stop_reason or f"internal call-ledger size mismatch: {index}"
    controls = [r for r in records if r["arm"] == "control"]
    primary = [r for r in records if r["arm"] != "control"]
    attempted_controls = [r for r in controls if r.get("attempts") == 1]
    attempted_primary = [r for r in primary if r.get("attempts") == 1]
    combined_summary = {x["slot"]: x for x in unsplit_summaries if x["arm"] == "combined"}
    comparison = []
    for partition in partition_summaries:
        combined = combined_summary.get(partition["slot"], {
            "result": "UNRUN", "slot_elapsed_seconds": 0,
            "observed_peak_tree_rss_bytes": 0, "charged_overhead_seconds": 0,
        })
        comparison.append({
            "slot": partition["slot"],
            "unsplit_result": combined["result"],
            "unsplit_elapsed_seconds": combined["slot_elapsed_seconds"],
            "partitioned_result": partition["result"],
            "partitioned_elapsed_seconds": partition["slot_elapsed_seconds"],
            "cell_counts": partition["counts"],
            "unsplit_observed_peak_tree_rss_bytes": combined["observed_peak_tree_rss_bytes"],
            "partitioned_observed_peak_tree_rss_bytes": partition["observed_peak_tree_rss_bytes"],
            "unsplit_overhead_seconds": combined["charged_overhead_seconds"],
            "partitioned_overhead_seconds": partition["charged_overhead_seconds"],
            "validated_full_acir_evidence": False,
        })
    status = "CAMPAIGN_COMPLETE" if stop_reason is None else "CAMPAIGN_STOPPED"
    ledger = {
        "task": "D1P-06", "status": status, "research_verdict": "UNKNOWN",
        "stop_reason": stop_reason, "recorded_at_utc": utc_now(),
        "freeze": {"path": relative(freeze_path), "sha256": sha256(freeze_path)},
        "input_manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest),
                           "inputs_rechecked": checked},
        "reference_environment": freeze_record["reference_environment"],
        "solver": freeze_record["solver"], "resource_policy": freeze_record["resource_policy"],
        "limits": freeze_record["limits"],
        "counts": {
            "planned_controls": 2, "attempted_controls": len(attempted_controls),
            "passed_controls": sum(bool(r.get("control_pass")) for r in attempted_controls),
            "planned_primary_calls": 164, "attempted_primary_calls": len(attempted_primary),
            "unrun_primary_calls": sum(r.get("attempts") == 0 for r in primary),
            "primary_results": result_counts(primary),
        },
        "control_wall_seconds": round(sum(r["elapsed_seconds"] for r in attempted_controls), 6),
        "primary_solver_call_wall_seconds": round(sum(r["elapsed_seconds"] for r in attempted_primary), 6),
        "primary_campaign_elapsed_seconds": round(time.monotonic() - primary_started, 6),
        "total_campaign_elapsed_seconds": round(time.monotonic() - started, 6),
        "observed_peak_tree_rss_bytes": max(
            (r.get("peak_tree_rss_bytes", 0) for r in records if r.get("attempts") == 1), default=0
        ),
        "goal_only_diagnostics": [x for x in unsplit_summaries if x["arm"] == "goal_only"],
        "cone_only_diagnostics": [x for x in unsplit_summaries if x["arm"] == "cone_only"],
        "combined": [x for x in unsplit_summaries if x["arm"] == "combined"],
        "partitioned": partition_summaries,
        "comparison": comparison,
        "records": records,
        "historical_linux_background": {
            "scope": "six exact combined queries only; background, not timing parity",
            "result": "six timeouts/UNKNOWN",
            "elapsed_seconds": [300.207, 300.131, 300.147, 300.167, 300.127, 300.192],
            "resource_policy": "4 GiB RLIMIT_AS on Linux x86_64",
        },
        "interpretation": (
            "Track A compares producer-side decomposition on one native Mac reference. "
            "Diagnostics are separate, SAT lacks validated full-ACIR/proof/consumer evidence, "
            "and the D1 security verdict remains UNKNOWN."
        ),
    }
    write_json(output / "track-a-ledger.json", ledger)
    write_json(ledger_path, ledger)
    progress = output / "progress.json"
    if progress.exists():
        progress.unlink()
    print(json.dumps({"status": status, **ledger["counts"],
                      "primary_solver_call_wall_seconds": ledger["primary_solver_call_wall_seconds"],
                      "stop_reason": stop_reason}, sort_keys=True))
    return 0 if status == "CAMPAIGN_COMPLETE" else 2


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--solver", type=Path, required=True)
    p.add_argument("--manifest", type=Path, default=INPUT_MANIFEST)
    p.add_argument("--resource-policy", type=Path, default=RESOURCE_POLICY)
    p.add_argument("--output", type=Path, required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--preflight", type=Path, required=True)
    f.add_argument("--manifest", type=Path, default=INPUT_MANIFEST)
    f.add_argument("--resource-policy", type=Path, default=RESOURCE_POLICY)
    f.add_argument("--output", type=Path, required=True)
    e = sub.add_parser("execute")
    e.add_argument("--freeze", type=Path, required=True)
    e.add_argument("--manifest", type=Path, default=INPUT_MANIFEST)
    e.add_argument("--resource-policy", type=Path, default=RESOURCE_POLICY)
    e.add_argument("--output", type=Path, required=True)
    e.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        return preflight(args)
    if args.command == "freeze":
        return freeze(args)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
