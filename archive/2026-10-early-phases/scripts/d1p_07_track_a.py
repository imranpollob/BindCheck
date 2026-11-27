#!/usr/bin/env python3
"""Race-safe native-macOS runner for the frozen D1P-07 Track A campaign."""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
D1P05_RUNNER = ROOT / "scripts/d1p_05_validate.py"
D1P06_RUNNER = ROOT / "scripts/d1p_06_track_a.py"
INPUT_MANIFEST = ROOT / "metadata/d1/d1p-06-input-manifest.json"
RESOURCE_POLICY = ROOT / "metadata/d1/d1p-07-resource-policy.json"
PROTOCOL = ROOT / "docs/d1-paper/d1p-07-protocol.md"
D1P06_LEDGER = ROOT / "metadata/d1/d1p-06-track-a-ledger.json"
EXPECTED_D1P05_RUNNER = "16cc0ae39e7ff3a01439b3c168e4bede93ab53b25bfc1d6b3d27efb3a8651d55"
EXPECTED_D1P06_INPUTS = "67f588f4e1254b28cc17e226b31039574c6d2b26db4b16214c9d63a813b0fef5"
EXPECTED_SOLVER = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
SOLVER_ARGUMENTS = ("--lang=smt2", "--ff-solver=split")
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05
EXIT_CONFIRM_SECONDS = 0.25
TERMINATION_WAIT_SECONDS = 0.25
CONTROL_SECONDS = 30.0
UNSPLIT_SECONDS = 300.0
PARTITION_SLOT_SECONDS = 300.0
CELL_SECONDS = 12.0
CONTROL_AGGREGATE_SECONDS = 60.0
PRIMARY_AGGREGATE_SECONDS = 6000.0
CONTROL_CALLS_MAX = 2
PRIMARY_CALLS_MAX = 164


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D1P05 = load_module("d1p_05_validate_for_d1p07", D1P05_RUNNER)
D1P06 = load_module("d1p_06_track_a_for_d1p07", D1P06_RUNNER)


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
    if sha256(manifest_path) != EXPECTED_D1P06_INPUTS:
        raise RuntimeError(f"D1P-06 input manifest changed: {sha256(manifest_path)}")
    manifest, checked = D1P06.verify_inputs(manifest_path)
    if checked != 166:
        raise RuntimeError(f"unexpected input count: {checked}")
    return manifest, checked


def available_max(values):
    observed = [value for value in values if value is not None]
    return max(observed) if observed else None


def termination_template():
    return {
        "requested": False, "reason": None,
        "group_sigkill_sent": False, "group_already_absent": False,
        "direct_kill_sent": False, "reaped": False,
        "returncode": None, "errors": [], "failed": False,
        "maximum_wait_seconds": 2 * TERMINATION_WAIT_SECONDS,
    }


def terminate_bounded(process, reason, group_kill=os.killpg):
    """Try group kill, then direct kill, with only bounded waits."""
    result = termination_template()
    result.update({"requested": True, "reason": reason})
    try:
        group_kill(process.pid, signal.SIGKILL)
        result["group_sigkill_sent"] = True
    except ProcessLookupError:
        result["group_already_absent"] = True
    except Exception as exc:
        result["errors"].append(f"group kill {type(exc).__name__}: {exc}")

    try:
        result["returncode"] = process.wait(timeout=TERMINATION_WAIT_SECONDS)
        result["reaped"] = True
        return result
    except subprocess.TimeoutExpired:
        result["errors"].append("bounded wait after group kill timed out")
    except Exception as exc:
        result["errors"].append(f"wait after group kill {type(exc).__name__}: {exc}")

    try:
        process.kill()
        result["direct_kill_sent"] = True
    except ProcessLookupError:
        result["group_already_absent"] = True
    except Exception as exc:
        result["errors"].append(f"direct kill {type(exc).__name__}: {exc}")

    try:
        result["returncode"] = process.wait(timeout=TERMINATION_WAIT_SECONDS)
        result["reaped"] = True
    except subprocess.TimeoutExpired:
        result["errors"].append("bounded wait after direct kill timed out")
    except Exception as exc:
        result["errors"].append(f"wait after direct kill {type(exc).__name__}: {exc}")
    result["failed"] = not result["reaped"]
    return result


def default_group_kill(pid, sig):
    os.killpg(pid, sig)


def run_monitored(*, index, kind, name, argv, logs_dir, monitor,
                  input_path=None, timeout_seconds=30.0,
                  rss_cutoff_bytes=RSS_CUTOFF,
                  sample_interval_seconds=SAMPLE_INTERVAL,
                  group_kill=default_group_kill):
    """Run once, safely resolving exit/monitor races and always recording."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "__")
    stem = f"{index:03d}_{kind}_{safe_name}"
    stdout_path = logs_dir / f"{stem}.stdout"
    stderr_path = logs_dir / f"{stem}.stderr"
    record_path = logs_dir / f"{stem}.json"
    for path in (stdout_path, stderr_path, record_path):
        if path.exists():
            raise FileExistsError(f"fresh call evidence required: {path}")

    started_utc = utc_now()
    started = time.monotonic()
    process = None
    input_handle = None
    stdout_handle = None
    stderr_handle = None
    status = "COMPLETED"
    error = None
    timed_out = False
    memory_cutoff = False
    monitor_failed = False
    exit_confirmed_after_missing_root = False
    samples = 0
    peak_rss = None
    peak_process_count = None
    last_sample = None
    termination = termination_template()

    try:
        stdout_handle = stdout_path.open("xb")
        stderr_handle = stderr_path.open("xb")
        if input_path is not None:
            input_handle = Path(input_path).open("rb")
        try:
            process = subprocess.Popen(
                [str(part) for part in argv],
                stdin=input_handle if input_handle is not None else subprocess.DEVNULL,
                stdout=stdout_handle, stderr=stderr_handle,
                start_new_session=True,
            )
        except Exception as exc:
            status = "LAUNCH_ERROR"
            error = f"{type(exc).__name__}: {exc}"

        while process is not None and process.returncode is None:
            if process.poll() is not None:
                break
            try:
                sample = monitor.sample(process.pid)
            except Exception as exc:
                status = "MONITOR_ERROR"
                monitor_failed = True
                error = f"{type(exc).__name__}: {exc}"
                termination = terminate_bounded(process, status, group_kill)
                break

            if sample["root_present"]:
                samples += 1
                last_sample = sample
                resident = sample.get("resident_bytes")
                count = sample.get("process_count")
                if resident is not None:
                    peak_rss = resident if peak_rss is None else max(peak_rss, resident)
                if count is not None:
                    peak_process_count = count if peak_process_count is None else max(
                        peak_process_count, count
                    )
            else:
                # The monitor can lose a child between sample and poll.  Only
                # accept that as normal after bounded wait() confirms/reaps it.
                try:
                    process.wait(timeout=EXIT_CONFIRM_SECONDS)
                    exit_confirmed_after_missing_root = True
                    break
                except subprocess.TimeoutExpired:
                    status = "MONITOR_ERROR"
                    monitor_failed = True
                    error = "monitor lost root and bounded exit confirmation timed out"
                    termination = terminate_bounded(process, status, group_kill)
                    break
                except Exception as exc:
                    status = "MONITOR_ERROR"
                    monitor_failed = True
                    error = f"exit confirmation {type(exc).__name__}: {exc}"
                    termination = terminate_bounded(process, status, group_kill)
                    break

            if peak_rss is not None and peak_rss > rss_cutoff_bytes:
                status = "MEMORY_CUTOFF"
                memory_cutoff = True
                termination = terminate_bounded(process, status, group_kill)
                break
            if time.monotonic() - started >= timeout_seconds:
                status = "TIMEOUT"
                timed_out = True
                termination = terminate_bounded(process, status, group_kill)
                break
            time.sleep(sample_interval_seconds)

        if process is not None and process.returncode is None and not termination["requested"]:
            try:
                process.wait(timeout=EXIT_CONFIRM_SECONDS)
            except subprocess.TimeoutExpired:
                status = "EXIT_WAIT_TIMEOUT"
                error = "bounded final exit wait timed out"
                termination = terminate_bounded(process, status, group_kill)
            except Exception as exc:
                status = "RUNNER_ERROR"
                error = f"final exit wait {type(exc).__name__}: {exc}"
                termination = terminate_bounded(process, status, group_kill)
    except Exception as exc:
        status = "RUNNER_ERROR"
        error = f"{type(exc).__name__}: {exc}"
        if process is not None and process.returncode is None:
            termination = terminate_bounded(process, status, group_kill)
    finally:
        if input_handle is not None:
            input_handle.close()
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()

    exit_status = process.returncode if process is not None else None
    if status == "COMPLETED" and exit_status != 0:
        status = "PROCESS_ERROR"
    if termination["requested"] and termination["failed"]:
        status = "TERMINATION_ERROR"
        suffix = "; ".join(termination["errors"])
        error = f"{error + '; ' if error else ''}termination failed: {suffix}"

    # Ensure even pre-launch input/runner errors leave both log files present.
    for path in (stdout_path, stderr_path):
        if not path.exists():
            path.touch()
    elapsed = time.monotonic() - started
    record = {
        "index": index, "kind": kind, "name": name,
        "status": status, "argv": [str(part) for part in argv],
        "started_utc": started_utc, "finished_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 6), "exit_status": exit_status,
        "process_launched": process is not None,
        "pid": process.pid if process is not None else None,
        "process_group": process.pid if process is not None else None,
        "timed_out": timed_out, "memory_cutoff": memory_cutoff,
        "monitor_failed": monitor_failed,
        "exit_confirmed_after_missing_root": exit_confirmed_after_missing_root,
        "error": error, "termination": termination,
        "timeout_seconds": timeout_seconds,
        "memory_policy": {
            "metric": "sum of libproc proc_taskinfo resident bytes over root and recursive children",
            "cutoff_bytes": rss_cutoff_bytes,
            "sample_interval_seconds": sample_interval_seconds,
            "hard_address_space_cap": False, "sampling_can_overshoot": True,
        },
        "memory_samples": samples,
        "peak_tree_rss_bytes": peak_rss,
        "peak_tree_process_count": peak_process_count,
        "memory_observation_available": peak_rss is not None,
        "last_sample": last_sample,
        "stdout_path": relative(stdout_path), "stdout_sha256": sha256(stdout_path),
        "stderr_path": relative(stderr_path), "stderr_sha256": sha256(stderr_path),
        "record_path": relative(record_path),
    }
    if input_path is not None:
        record.update({
            "stdin": "exact input_path bytes", "input_path": relative(input_path),
            "input_sha256": sha256(input_path),
            "input_bytes": Path(input_path).stat().st_size,
        })
    write_json(record_path, record)
    return record


class ExitDuringSampleMonitor:
    """Harmless test double that exposes the D1P-06 exit race."""

    def __init__(self):
        self.calls = 0

    def sample(self, root_pid):
        self.calls += 1
        if self.calls == 1:
            return {"root_present": True, "resident_bytes": 1,
                    "process_count": 1, "pids": [root_pid]}
        time.sleep(0.08)
        return {"root_present": False, "resident_bytes": None,
                "process_count": 0, "pids": []}


class FailingMonitor:
    def sample(self, root_pid):
        raise RuntimeError(f"intentional live-process monitor failure for {root_pid}")


def denied_group_kill(pid, sig):
    raise PermissionError(1, "intentional denied process-group cleanup")


def helper_command(code, *args):
    return [sys.executable, "-I", "-c", code, *map(str, args)]


def process_alive(monitor, pid):
    try:
        sample = monitor.sample(pid)
        return bool(sample["root_present"])
    except Exception:
        return False


def wait_cleanup(monitor, pids, seconds=1.0):
    deadline = time.monotonic() + seconds
    remaining = list(pids)
    while remaining and time.monotonic() < deadline:
        remaining = [pid for pid in remaining if process_alive(monitor, pid)]
        if remaining:
            time.sleep(0.02)
    return remaining


def infrastructure_check(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"fresh infrastructure output required: {output}")
    output.mkdir(parents=True)
    logs = output / "calls"
    real_monitor = D1P05.MacProcessTreeMonitor()
    records = []

    records.append(run_monitored(
        index=1, kind="helper", name="rapid_exit",
        argv=helper_command("print('rapid-ok',flush=True)"), logs_dir=logs,
        monitor=real_monitor, timeout_seconds=1.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
    ))
    records.append(run_monitored(
        index=2, kind="helper", name="exit_during_sampling",
        argv=helper_command("import time;time.sleep(.03);print('race-ok',flush=True)"),
        logs_dir=logs, monitor=ExitDuringSampleMonitor(), timeout_seconds=1.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
    ))

    with tempfile.TemporaryDirectory(prefix="d1p07-monitor-", dir=output) as directory:
        child_file = Path(directory) / "child.pid"
        code = (
            "import pathlib,subprocess,sys,time;"
            "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));"
            "time.sleep(30)"
        )
        monitor_failure = run_monitored(
            index=3, kind="helper", name="live_monitor_failure",
            argv=helper_command(code, child_file), logs_dir=logs,
            monitor=FailingMonitor(), timeout_seconds=2.0,
            rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
        )
        child_pid = int(child_file.read_text()) if child_file.exists() else None
        monitor_failure["helper_child_pid"] = child_pid
        monitor_failure["cleanup_survivors"] = wait_cleanup(
            real_monitor, [pid for pid in (monitor_failure["pid"], child_pid) if pid]
        )
        write_json(ROOT / monitor_failure["record_path"], monitor_failure)
        records.append(monitor_failure)

    denied = run_monitored(
        index=4, kind="helper", name="denied_group_cleanup",
        argv=helper_command("import time;time.sleep(30)"), logs_dir=logs,
        monitor=FailingMonitor(), timeout_seconds=2.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
        group_kill=denied_group_kill,
    )
    denied["cleanup_survivors"] = wait_cleanup(real_monitor, [denied["pid"]])
    write_json(ROOT / denied["record_path"], denied)
    records.append(denied)

    records.append(run_monitored(
        index=5, kind="helper", name="launch_error",
        argv=[str(output / "missing-command")], logs_dir=logs,
        monitor=real_monitor, timeout_seconds=1.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
    ))

    with tempfile.TemporaryDirectory(prefix="d1p07-timeout-", dir=output) as directory:
        child_file = Path(directory) / "child.pid"
        code = (
            "import pathlib,subprocess,sys,time;"
            "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)"
        )
        timeout_record = run_monitored(
            index=6, kind="helper", name="timeout_cleanup",
            argv=helper_command(code, child_file), logs_dir=logs,
            monitor=real_monitor, timeout_seconds=0.25,
            rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.01,
        )
        child_pid = int(child_file.read_text()) if child_file.exists() else None
        timeout_record["helper_child_pid"] = child_pid
        timeout_record["cleanup_survivors"] = wait_cleanup(
            real_monitor, [pid for pid in (timeout_record["pid"], child_pid) if pid]
        )
        write_json(ROOT / timeout_record["record_path"], timeout_record)
        records.append(timeout_record)

    with tempfile.TemporaryDirectory(prefix="d1p07-memory-", dir=output) as directory:
        child_file = Path(directory) / "child.pid"
        code = (
            "import pathlib,subprocess,sys,time;"
            "child='import time;x=bytearray(64*1024*1024);time.sleep(30)';"
            "p=subprocess.Popen([sys.executable,'-I','-c',child]);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)"
        )
        memory_record = run_monitored(
            index=7, kind="helper", name="tree_memory_cleanup",
            argv=helper_command(code, child_file), logs_dir=logs,
            monitor=real_monitor, timeout_seconds=3.0,
            rss_cutoff_bytes=48 * 1024**2, sample_interval_seconds=0.01,
        )
        child_pid = int(child_file.read_text()) if child_file.exists() else None
        memory_record["helper_child_pid"] = child_pid
        memory_record["cleanup_survivors"] = wait_cleanup(
            real_monitor, [pid for pid in (memory_record["pid"], child_pid) if pid]
        )
        write_json(ROOT / memory_record["record_path"], memory_record)
        records.append(memory_record)

    checks = {
        "rapid_exit": records[0]["status"] == "COMPLETED" and records[0]["exit_status"] == 0,
        "rapid_exit_logs": all((ROOT / records[0][key]).is_file()
                                for key in ("stdout_path", "stderr_path", "record_path")),
        "unavailable_memory_is_null": (
            records[0]["peak_tree_rss_bytes"] is None
            if records[0]["memory_samples"] == 0 else True
        ),
        "exit_during_sampling": (
            records[1]["status"] == "COMPLETED"
            and records[1]["exit_status"] == 0
            and records[1]["exit_confirmed_after_missing_root"]
        ),
        "live_monitor_failure": records[2]["status"] == "MONITOR_ERROR",
        "live_monitor_failure_cleanup": not records[2]["cleanup_survivors"],
        "denied_cleanup_caught": (
            records[3]["status"] == "MONITOR_ERROR"
            and any("PermissionError" in value for value in records[3]["termination"]["errors"])
            and records[3]["termination"]["direct_kill_sent"]
            and records[3]["termination"]["reaped"]
        ),
        "denied_cleanup_bounded": records[3]["elapsed_seconds"] < 2.0,
        "denied_cleanup_no_survivor": not records[3]["cleanup_survivors"],
        "launch_error_structured": records[4]["status"] == "LAUNCH_ERROR",
        "timeout_cleanup": records[5]["status"] == "TIMEOUT" and not records[5]["cleanup_survivors"],
        "memory_cleanup": records[6]["status"] == "MEMORY_CUTOFF" and not records[6]["cleanup_survivors"],
        "all_records_and_logs": all(
            all((ROOT / record[key]).is_file()
                for key in ("stdout_path", "stderr_path", "record_path"))
            for record in records
        ),
    }
    summary = {
        "task": "D1P-07", "kind": "pre-freeze harmless-helper infrastructure check",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "research_result": False, "solver_queries": 0,
        "platform": D1P06.platform_identity(),
        "limits": {"exit_confirm_seconds": EXIT_CONFIRM_SECONDS,
                   "termination_wait_seconds_each": TERMINATION_WAIT_SECONDS},
        "checks": checks, "records": records,
    }
    write_json(output / "infrastructure-check.json", summary)
    print(json.dumps({"status": summary["status"], "checks": checks}, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 2


def preflight(args):
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"fresh preflight namespace required: {output}")
    output.mkdir(parents=True)
    started = time.monotonic()
    checks = {}
    error = None
    solver = args.solver.resolve()
    checked = 0
    try:
        checks["native_macos_arm64"] = platform.system() == "Darwin" and platform.machine() == "arm64"
        checks["solver_exists"] = solver.is_file() and os.access(solver, os.X_OK)
        checks["solver_hash"] = checks["solver_exists"] and sha256(solver) == EXPECTED_SOLVER
        if not all(checks.values()):
            raise RuntimeError("platform or solver identity mismatch")
        _, checked = verify_inputs(args.manifest.resolve())
        checks["input_hashes"] = checked == 166
        policy = json.loads(args.resource_policy.read_text())
        checks["resource_policy"] = (
            policy["limitations"]["hard_address_space_cap"] is False
            and policy["monitor"]["sample_interval_seconds"] == SAMPLE_INTERVAL
        )
        helper_output = output / "helpers"
        helper_exit = infrastructure_check(helper_output)
        helper = json.loads((helper_output / "infrastructure-check.json").read_text())
        checks["harmless_helper_gate"] = helper_exit == 0 and helper["status"] == "PASS"
        inventory = D1P06.host_inventory(solver)
        checks["identity_commands"] = all(
            item["exit_status"] == 0 for item in inventory["commands"].values()
        )
        if not all(checks.values()):
            raise RuntimeError("one or more preflight checks failed")
        status = "PASS"
    except Exception as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {exc}"
        inventory = D1P06.host_inventory(solver) if solver.is_file() else {
            "platform": D1P06.platform_identity(), "commands": {}, "linked_libraries": []
        }
    helper_path = output / "helpers/infrastructure-check.json"
    record = {
        "task": "D1P-07", "kind": "pre-freeze native-macOS preflight",
        "status": status, "error": error, "research_result": False,
        "solver_queries": 0, "recorded_at_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "checks": checks, "inputs_checked": checked,
        "input_manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest)},
        "solver": {"path": str(solver), "sha256": sha256(solver) if solver.is_file() else None,
                   "arguments": list(SOLVER_ARGUMENTS),
                   "version": "cvc5 1.4.2 arm64 GPL/CoCoA (D1P-05 provenance)"},
        "environment": inventory,
        "resource_policy": {"path": relative(args.resource_policy),
                            "sha256": sha256(args.resource_policy)},
        "helper_check": ({"path": relative(helper_path), "sha256": sha256(helper_path)}
                         if helper_path.is_file() else None),
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
        "task": "D1P-07", "status": "FROZEN_BEFORE_FRESH_CAMPAIGN",
        "frozen_at_utc": utc_now(),
        "repository_head": D1P06.run_capture(["/usr/bin/git", "rev-parse", "HEAD"])["stdout"].strip(),
        "scope": "fresh native-macOS Track A campaign with race-safe runner",
        "fresh_campaign_authorization": {
            "start_call": 1, "repeat_controls": True,
            "repeat_all_track_a_queries": True,
            "reuse_d1p06_timings_in_comparison": False,
        },
        "reference_environment": preflight_record["environment"],
        "solver": preflight_record["solver"],
        "resource_policy": {"path": relative(args.resource_policy),
                            "sha256": sha256(args.resource_policy),
                            "hard_address_space_cap": False,
                            "sampling_can_overshoot": True},
        "preflight": {"path": relative(preflight_path), "sha256": sha256(preflight_path),
                      "status": "PASS", "solver_queries": 0},
        "input_manifest": {"path": relative(args.manifest), "sha256": sha256(args.manifest),
                           "inputs_checked": checked},
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
            "exit_confirm_seconds": EXIT_CONFIRM_SECONDS,
            "termination_wait_seconds_each": TERMINATION_WAIT_SECONDS,
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
        "preserved_d1p06": {"ledger_path": relative(D1P06_LEDGER),
                            "ledger_sha256": sha256(D1P06_LEDGER),
                            "timings_reused": False},
        "frozen_files": [
            {"path": relative(path), "sha256": sha256(path)} for path in (
                Path(__file__), ROOT / "tests/d1/test_d1p_07_track_a.py",
                PROTOCOL, args.resource_policy.resolve(), args.manifest.resolve(),
                D1P05_RUNNER, D1P06_RUNNER, D1P06_LEDGER,
            )
        ],
        "stop_rules": [
            "failed control, input corruption, genuine infrastructure failure, or validated contradiction stops",
            "confirmed child exit after a missing-root sample is normal completion",
            "timeout, sampled memory cutoff, UNKNOWN, or solver error is unresolved without retry",
            "partition SAT requires preserved witness output; partition UNSAT requires 25 UNSAT cells",
        ],
        "interpretation": (
            "D1P-07 compares only fresh native-Mac arms. D1P-06 timings are not "
            "comparison inputs. Track A does not establish a D1 verdict."
        ),
    }
    write_json(output, value)
    print(json.dumps({"status": value["status"], "inputs": len(flat),
                      "freeze": relative(output)}, sort_keys=True))
    return 0


def verify_freeze(freeze_record, manifest_path, resource_policy_path):
    if D1P06.platform_identity() != freeze_record["reference_environment"]["platform"]:
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
    if json.loads(preflight_path.read_text()).get("status") != "PASS":
        raise RuntimeError("frozen preflight is not PASS")
    return verify_inputs(manifest_path)


def parse_result(stdout_path):
    lines = Path(stdout_path).read_text(errors="replace").splitlines()
    if not lines:
        return "missing", False
    parsed = lines[0].strip().lower()
    if parsed not in ("sat", "unsat", "unknown"):
        return "malformed", False
    return parsed, parsed == "sat" and any(line.strip() for line in lines[1:])


def unrun(index, arm, name, item, reason, logical_slot=None):
    value = {
        "index": index, "arm": arm, "name": name,
        "query_path": item["path"], "query_sha256": item["sha256"],
        "attempts": 0, "status": "UNRUN", "result": "UNRUN",
        "reason": reason, "peak_tree_rss_bytes": None,
        "memory_observation_available": False,
    }
    if logical_slot is not None:
        value["logical_slot"] = logical_slot
    return value


def run_query(index, arm, name, item, timeout, solver, logs, monitor,
              logical_slot=None):
    record = run_monitored(
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
    if logical_slot is not None:
        record["logical_slot"] = logical_slot
    write_json(ROOT / record["record_path"], record)
    return record


def infrastructure_failure(record):
    return (
        record["status"] in {
            "LAUNCH_ERROR", "MONITOR_ERROR", "RUNNER_ERROR",
            "EXIT_WAIT_TIMEOUT", "TERMINATION_ERROR",
        }
        or record.get("termination", {}).get("failed", False)
        or bool(record.get("termination", {}).get("errors"))
    )


def result_counts(records):
    return {
        "sat": sum(r.get("result") == "SAT" for r in records),
        "unsat": sum(r.get("result") == "UNSAT" for r in records),
        "unknown": sum(r.get("attempts") == 1 and r.get("result") == "UNKNOWN" for r in records),
        "unrun": sum(r.get("attempts") == 0 for r in records),
    }


def planned_rows(manifest):
    rows = []
    for item in manifest["controls"]:
        rows.append(("control", item["name"], item, None))
    for arm in ("goal_only", "cone_only", "combined"):
        for item in manifest[arm]:
            rows.append((arm, item["slot"], item, None))
    for group in manifest["partitioned"]:
        for item in group["cells"]:
            rows.append(("partitioned", f"{group['slot']}/{item['id']}", item, group["slot"]))
    if len(rows) != 166:
        raise RuntimeError(f"unexpected schedule length: {len(rows)}")
    return rows


def build_ledger(*, freeze_path, freeze_record, manifest_path, checked,
                 records, stop_reason, unsplit_summaries,
                 partition_slot_elapsed, started, primary_started):
    controls = [r for r in records if r["arm"] == "control"]
    primary = [r for r in records if r["arm"] != "control"]
    attempted_controls = [r for r in controls if r.get("attempts") == 1]
    attempted_primary = [r for r in primary if r.get("attempts") == 1]
    partitions = []
    for family in ("check_added", "running_flag"):
        for query in ("nonvacuous", "prefix", "tail"):
            slot = f"{family}/{query}"
            cells = [r for r in primary if r.get("logical_slot") == slot]
            counts = result_counts(cells)
            sat_witness = any(r.get("result") == "SAT" and
                              r.get("sat_witness_output_preserved") for r in cells)
            result = "SAT" if sat_witness else ("UNSAT" if counts["unsat"] == 25 else "UNKNOWN")
            attempted = [r for r in cells if r.get("attempts") == 1]
            call_elapsed = sum(r.get("elapsed_seconds", 0) for r in attempted)
            slot_elapsed = partition_slot_elapsed.get(slot)
            partitions.append({
                "slot": slot, "result": result, "counts": counts,
                "slot_elapsed_seconds": slot_elapsed,
                "solver_call_elapsed_seconds": round(call_elapsed, 6),
                "charged_overhead_seconds": (
                    round(max(0, slot_elapsed - call_elapsed), 6)
                    if slot_elapsed is not None else None
                ),
                "observed_peak_tree_rss_bytes": available_max(
                    r.get("peak_tree_rss_bytes") for r in attempted
                ),
                "sat_witness_output_preserved": sat_witness,
                "validated_full_acir_evidence": False,
            })
    combined = {x["slot"]: x for x in unsplit_summaries if x["arm"] == "combined"}
    comparison = []
    for partition in partitions:
        unsplit = combined.get(partition["slot"])
        comparison.append({
            "slot": partition["slot"],
            "unsplit_result": unsplit["result"] if unsplit else "UNRUN",
            "unsplit_elapsed_seconds": unsplit["slot_elapsed_seconds"] if unsplit else None,
            "partitioned_result": partition["result"],
            "partitioned_elapsed_seconds": partition["slot_elapsed_seconds"],
            "cell_counts": partition["counts"],
            "unsplit_observed_peak_tree_rss_bytes": (
                unsplit["observed_peak_tree_rss_bytes"] if unsplit else None
            ),
            "partitioned_observed_peak_tree_rss_bytes": partition["observed_peak_tree_rss_bytes"],
            "unsplit_overhead_seconds": unsplit["charged_overhead_seconds"] if unsplit else None,
            "partitioned_overhead_seconds": partition["charged_overhead_seconds"],
            "validated_full_acir_evidence": False,
        })
    status = "CAMPAIGN_COMPLETE" if stop_reason is None else "CAMPAIGN_STOPPED"
    return {
        "task": "D1P-07", "status": status, "research_verdict": "UNKNOWN",
        "stop_reason": stop_reason, "recorded_at_utc": utc_now(),
        "fresh_campaign_started_at_call": 1,
        "d1p06_timings_reused_in_comparison": False,
        "freeze": {"path": relative(freeze_path), "sha256": sha256(freeze_path)},
        "input_manifest": {"path": relative(manifest_path), "sha256": sha256(manifest_path),
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
        "observed_peak_tree_rss_bytes": available_max(
            r.get("peak_tree_rss_bytes") for r in records if r.get("attempts") == 1
        ),
        "goal_only_diagnostics": [x for x in unsplit_summaries if x["arm"] == "goal_only"],
        "cone_only_diagnostics": [x for x in unsplit_summaries if x["arm"] == "cone_only"],
        "combined": [x for x in unsplit_summaries if x["arm"] == "combined"],
        "partitioned": partitions, "comparison": comparison,
        "records": records,
        "historical_linux_background": {
            "scope": "six exact combined queries only; background, not timing parity",
            "result": "six timeouts/UNKNOWN",
            "elapsed_seconds": [300.207, 300.131, 300.147, 300.167, 300.127, 300.192],
            "resource_policy": "4 GiB RLIMIT_AS on Linux x86_64",
        },
        "interpretation": (
            "D1P-07 compares fresh native-Mac producer-side arms only. Diagnostics "
            "are separate, SAT lacks validated full-ACIR/proof/consumer evidence, "
            "and the D1 security verdict remains UNKNOWN."
        ),
    }


def execute(args):
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    if output.exists() or ledger_path.exists():
        raise FileExistsError("fresh D1P-07 output namespace and ledger required")
    output.mkdir(parents=True)
    logs = output / "calls"
    logs.mkdir()
    started = time.monotonic()
    records = []
    unsplit_summaries = []
    partition_slot_elapsed = {}
    stop_reason = None
    checked = 0
    freeze_path = args.freeze.resolve()
    freeze_record = json.loads(freeze_path.read_text())
    manifest = json.loads(args.manifest.read_text())
    schedule = planned_rows(manifest)
    monitor = None
    solver = Path(freeze_record["solver"]["path"])
    try:
        manifest, checked = verify_freeze(
            freeze_record, args.manifest.resolve(), args.resource_policy.resolve()
        )
        monitor = D1P05.MacProcessTreeMonitor()
    except Exception as exc:
        stop_reason = f"pre-execution infrastructure failure: {type(exc).__name__}: {exc}"

    index = 0
    try:
        control_started = time.monotonic()
        for item in manifest["controls"]:
            index += 1
            if stop_reason:
                records.append(unrun(index, "control", item["name"], item, stop_reason))
                continue
            remaining = CONTROL_AGGREGATE_SECONDS - (time.monotonic() - control_started)
            if remaining <= 0:
                stop_reason = "control aggregate budget exhausted"
                records.append(unrun(index, "control", item["name"], item, stop_reason))
                continue
            record = run_query(index, "control", item["name"], item,
                               min(CONTROL_SECONDS, remaining), solver, logs, monitor)
            record["expected"] = item["expected"]
            record["control_pass"] = record["result"].lower() == item["expected"]
            write_json(ROOT / record["record_path"], record)
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
                    records.append(unrun(index, arm, name, item, stop_reason))
                    continue
                slot_started = time.monotonic()
                global_remaining = PRIMARY_AGGREGATE_SECONDS - (slot_started - primary_started)
                if global_remaining <= 0:
                    stop_reason = "primary aggregate budget exhausted"
                    records.append(unrun(index, arm, name, item, stop_reason))
                    continue
                record = run_query(index, arm, name, item,
                                   min(UNSPLIT_SECONDS, global_remaining), solver, logs, monitor)
                record["anticipated_result_not_observation"] = item["anticipated_result_not_observation"]
                slot_elapsed = time.monotonic() - slot_started
                record["slot_elapsed_seconds"] = round(slot_elapsed, 6)
                record["charged_overhead_seconds"] = round(
                    max(0.0, slot_elapsed - record["elapsed_seconds"]), 6
                )
                write_json(ROOT / record["record_path"], record)
                records.append(record)
                unsplit_summaries.append({
                    "arm": arm, "slot": name, "result": record["result"],
                    "slot_elapsed_seconds": record["slot_elapsed_seconds"],
                    "solver_call_elapsed_seconds": record["elapsed_seconds"],
                    "charged_overhead_seconds": record["charged_overhead_seconds"],
                    "observed_peak_tree_rss_bytes": record["peak_tree_rss_bytes"],
                    "memory_observation_available": record["memory_observation_available"],
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
            slot_stop = None
            cell_records = []
            for item in group["cells"]:
                index += 1
                name = f"{slot}/{item['id']}"
                if stop_reason or slot_stop:
                    record = unrun(index, "partitioned", name, item,
                                   stop_reason or slot_stop, logical_slot=slot)
                    records.append(record)
                    cell_records.append(record)
                    continue
                slot_remaining = PARTITION_SLOT_SECONDS - (time.monotonic() - slot_started)
                global_remaining = PRIMARY_AGGREGATE_SECONDS - (time.monotonic() - primary_started)
                if slot_remaining <= 0 or global_remaining <= 0:
                    reason = ("partitioned slot budget exhausted" if slot_remaining <= 0
                              else "primary aggregate budget exhausted")
                    record = unrun(index, "partitioned", name, item, reason, logical_slot=slot)
                    records.append(record)
                    cell_records.append(record)
                    continue
                record = run_query(index, "partitioned", name, item,
                                   min(CELL_SECONDS, slot_remaining, global_remaining),
                                   solver, logs, monitor, logical_slot=slot)
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
            partition_slot_elapsed[slot] = (
                round(time.monotonic() - slot_started, 6)
                if any(r.get("attempts") == 1 for r in cell_records) else None
            )
            counts = result_counts(cell_records)
            partition_result = (
                "SAT" if any(r.get("result") == "SAT" and
                             r.get("sat_witness_output_preserved") for r in cell_records)
                else ("UNSAT" if counts["unsat"] == 25 else "UNKNOWN")
            )
            if partition_result == "UNSAT" and combined_results.get(slot) == "SAT":
                stop_reason = f"equivalent-formula contradiction: combined SAT, partition UNSAT: {slot}"
    except Exception as exc:
        stop_reason = f"runner infrastructure exception: {type(exc).__name__}: {exc}"
        if "primary_started" not in locals():
            primary_started = time.monotonic()

    if "primary_started" not in locals():
        primary_started = time.monotonic()
    if len(records) < 166:
        for next_index, (arm, name, item, logical_slot) in enumerate(
                schedule[len(records):], len(records) + 1):
            records.append(unrun(next_index, arm, name, item,
                                 stop_reason or "campaign ended before call",
                                 logical_slot=logical_slot))
    if len(records) != 166:
        stop_reason = stop_reason or f"call ledger length mismatch: {len(records)}"
    ledger = build_ledger(
        freeze_path=freeze_path, freeze_record=freeze_record,
        manifest_path=args.manifest.resolve(), checked=checked,
        records=records, stop_reason=stop_reason,
        unsplit_summaries=unsplit_summaries,
        partition_slot_elapsed=partition_slot_elapsed,
        started=started, primary_started=primary_started,
    )
    write_json(output / "track-a-ledger.json", ledger)
    write_json(ledger_path, ledger)
    progress = output / "progress.json"
    if progress.exists():
        progress.unlink()
    print(json.dumps({"status": ledger["status"], **ledger["counts"],
                      "primary_solver_call_wall_seconds": ledger["primary_solver_call_wall_seconds"],
                      "stop_reason": stop_reason}, sort_keys=True))
    return 0 if ledger["status"] == "CAMPAIGN_COMPLETE" else 2


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    i = sub.add_parser("infrastructure-check")
    i.add_argument("--output", type=Path, required=True)
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
    if args.command == "infrastructure-check":
        return infrastructure_check(args.output)
    if args.command == "preflight":
        return preflight(args)
    if args.command == "freeze":
        return freeze(args)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
