#!/usr/bin/env python3
"""Run D1P-04 equivalence queries with sampled macOS process-tree RSS.

The resource monitor uses macOS libproc rather than RLIMIT_AS.  It samples
resident memory and terminates the solver process group after an observed
4 GiB crossing.  Sampling can overshoot and is not a hard address-space cap.
"""

import argparse
import ctypes
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from ctypes.util import find_library
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CALLS_MAX = 152
SECONDS_PER_CALL = 30.0
SOLVER_WALL_SECONDS_MAX = 4560.0
RSS_CUTOFF_BYTES = 4 * 1024**3
SAMPLE_INTERVAL_SECONDS = 0.05
MAX_CHILDREN_PER_PROCESS = 4096
PROC_PIDTASKINFO = 4


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


class ProcTaskInfo(ctypes.Structure):
    """Darwin proc_taskinfo from <sys/proc_info.h>."""

    _fields_ = [
        ("pti_virtual_size", ctypes.c_uint64),
        ("pti_resident_size", ctypes.c_uint64),
        ("pti_total_user", ctypes.c_uint64),
        ("pti_total_system", ctypes.c_uint64),
        ("pti_threads_user", ctypes.c_uint64),
        ("pti_threads_system", ctypes.c_uint64),
        ("pti_policy", ctypes.c_int32),
        ("pti_faults", ctypes.c_int32),
        ("pti_pageins", ctypes.c_int32),
        ("pti_cow_faults", ctypes.c_int32),
        ("pti_messages_sent", ctypes.c_int32),
        ("pti_messages_received", ctypes.c_int32),
        ("pti_syscalls_mach", ctypes.c_int32),
        ("pti_syscalls_unix", ctypes.c_int32),
        ("pti_csw", ctypes.c_int32),
        ("pti_threadnum", ctypes.c_int32),
        ("pti_numrunning", ctypes.c_int32),
        ("pti_priority", ctypes.c_int32),
    ]


class MacProcessTreeMonitor:
    """Sample aggregate resident bytes for one PID and recursive children."""

    def __init__(self, library_path=None, child_capacity=MAX_CHILDREN_PER_PROCESS):
        if platform.system() != "Darwin":
            raise RuntimeError("D1P-05 monitor requires Darwin/macOS")
        self.library_path = library_path or find_library("proc")
        if not self.library_path:
            raise RuntimeError("macOS libproc not found")
        self.child_capacity = child_capacity
        self.lib = ctypes.CDLL(self.library_path, use_errno=True)
        self.lib.proc_listchildpids.argtypes = [
            ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
        ]
        self.lib.proc_listchildpids.restype = ctypes.c_int
        self.lib.proc_pidinfo.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
            ctypes.c_void_p, ctypes.c_int,
        ]
        self.lib.proc_pidinfo.restype = ctypes.c_int

    def _children(self, pid):
        buffer_type = ctypes.c_int * self.child_capacity
        buffer = buffer_type()
        ctypes.set_errno(0)
        count = self.lib.proc_listchildpids(
            pid, buffer, ctypes.sizeof(buffer),
        )
        error = ctypes.get_errno()
        if count < 0:
            raise RuntimeError(
                f"proc_listchildpids({pid}) failed: errno={error}"
            )
        if count >= self.child_capacity:
            raise RuntimeError(
                f"child PID buffer saturated for {pid}: {count}"
            )
        return [int(buffer[index]) for index in range(count) if buffer[index] > 0]

    def _rss(self, pid):
        info = ProcTaskInfo()
        ctypes.set_errno(0)
        returned = self.lib.proc_pidinfo(
            pid, PROC_PIDTASKINFO, 0, ctypes.byref(info), ctypes.sizeof(info),
        )
        error = ctypes.get_errno()
        if returned == ctypes.sizeof(info):
            return int(info.pti_resident_size)
        if returned == 0 and error in (0, 3):  # exited/ESRCH race
            return None
        raise RuntimeError(
            f"proc_pidinfo({pid}) returned {returned}/{ctypes.sizeof(info)}: "
            f"errno={error}"
        )

    def sample(self, root_pid):
        pending = [int(root_pid)]
        seen = set()
        resident = 0
        present = []
        while pending:
            pid = pending.pop()
            if pid in seen:
                continue
            seen.add(pid)
            rss = self._rss(pid)
            if rss is None:
                continue
            present.append(pid)
            resident += rss
            pending.extend(self._children(pid))
        return {
            "root_present": int(root_pid) in present,
            "resident_bytes": resident,
            "process_count": len(present),
            "pids": sorted(present),
        }


class FailingMonitor:
    """Infrastructure-only test double for monitor-failure cleanup."""

    library_path = "TEST_DOUBLE"

    def sample(self, root_pid):
        raise RuntimeError(f"intentional monitor failure for helper {root_pid}")


def kill_process_group(process):
    sent = False
    try:
        os.killpg(process.pid, signal.SIGKILL)
        sent = True
    except ProcessLookupError:
        pass
    return sent


def parse_solver_output(stdout_path):
    lines = Path(stdout_path).read_text(errors="replace").splitlines()
    parsed = lines[0].strip().lower() if lines else "missing"
    return parsed if parsed in ("sat", "unsat", "unknown") else "malformed"


def process_exists(monitor, pid):
    try:
        return monitor._rss(pid) is not None
    except (AttributeError, RuntimeError):
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False


def wait_for_cleanup(monitor, pids, seconds=1.0):
    deadline = time.monotonic() + seconds
    remaining = list(pids)
    while remaining and time.monotonic() < deadline:
        remaining = [pid for pid in remaining if process_exists(monitor, pid)]
        if remaining:
            time.sleep(0.02)
    return remaining


def run_monitored(*, index, kind, name, argv, logs_dir, monitor,
                  input_path=None, timeout_seconds=SECONDS_PER_CALL,
                  rss_cutoff_bytes=RSS_CUTOFF_BYTES,
                  sample_interval_seconds=SAMPLE_INTERVAL_SECONDS):
    """Run one command and always emit a structured record.

    This is also used by the pre-freeze helper checks.  It never invokes a
    shell.  Any launch or monitoring exception becomes evidence and causes the
    child process group, when one exists, to be killed.
    """
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
    status = "COMPLETED"
    error = None
    timed_out = False
    memory_cutoff = False
    monitor_failed = False
    kill_sent = False
    samples = 0
    peak_rss = 0
    peak_process_count = 0
    last_sample = None

    try:
        if input_path is not None:
            input_handle = Path(input_path).open("rb")
        with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
            try:
                process = subprocess.Popen(
                    [str(part) for part in argv],
                    stdin=input_handle if input_handle is not None else subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    start_new_session=True,
                )
            except Exception as exc:  # structured launch evidence is required
                status = "LAUNCH_ERROR"
                error = f"{type(exc).__name__}: {exc}"
            if process is not None:
                while True:
                    try:
                        sample = monitor.sample(process.pid)
                        if sample["root_present"]:
                            samples += 1
                            last_sample = sample
                            peak_rss = max(peak_rss, sample["resident_bytes"])
                            peak_process_count = max(
                                peak_process_count, sample["process_count"]
                            )
                            if sample["resident_bytes"] > rss_cutoff_bytes:
                                status = "MEMORY_CUTOFF"
                                memory_cutoff = True
                                kill_sent = kill_process_group(process)
                                break
                        elif process.poll() is None:
                            raise RuntimeError(
                                "monitor lost a live root process"
                            )
                    except Exception as exc:
                        status = "MONITOR_ERROR"
                        monitor_failed = True
                        error = f"{type(exc).__name__}: {exc}"
                        kill_sent = kill_process_group(process)
                        break

                    if process.poll() is not None:
                        break
                    if time.monotonic() - started >= timeout_seconds:
                        status = "TIMEOUT"
                        timed_out = True
                        kill_sent = kill_process_group(process)
                        break
                    time.sleep(sample_interval_seconds)
                process.wait()
    finally:
        if input_handle is not None:
            input_handle.close()

    elapsed = time.monotonic() - started
    exit_status = process.returncode if process is not None else None
    if status == "COMPLETED" and exit_status != 0:
        status = "PROCESS_ERROR"
    record = {
        "index": index,
        "kind": kind,
        "name": name,
        "status": status,
        "argv": [str(part) for part in argv],
        "started_utc": started_utc,
        "finished_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 6),
        "exit_status": exit_status,
        "process_launched": process is not None,
        "pid": process.pid if process is not None else None,
        "process_group": process.pid if process is not None else None,
        "process_group_sigkill_sent": kill_sent,
        "timed_out": timed_out,
        "memory_cutoff": memory_cutoff,
        "monitor_failed": monitor_failed,
        "error": error,
        "timeout_seconds": timeout_seconds,
        "memory_policy": {
            "metric": "sum of libproc proc_taskinfo resident bytes over root and recursive children",
            "cutoff_bytes": rss_cutoff_bytes,
            "sample_interval_seconds": sample_interval_seconds,
            "hard_address_space_cap": False,
            "sampling_can_overshoot": True,
        },
        "memory_samples": samples,
        "peak_tree_rss_bytes": peak_rss,
        "peak_tree_process_count": peak_process_count,
        "last_sample": last_sample,
        "stdout_path": relative(stdout_path),
        "stdout_sha256": sha256(stdout_path),
        "stderr_path": relative(stderr_path),
        "stderr_sha256": sha256(stderr_path),
        "record_path": relative(record_path),
    }
    if input_path is not None:
        record.update({
            "stdin": "exact input_path bytes",
            "input_path": relative(input_path),
            "input_sha256": sha256(input_path),
            "input_bytes": Path(input_path).stat().st_size,
        })
    write_json(record_path, record)
    return record


def helper_command(code, *args):
    return [sys.executable, "-I", "-c", code, *map(str, args)]


def infrastructure_check(output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"fresh infrastructure output required: {output}")
    output.mkdir(parents=True)
    logs = output / "calls"
    monitor = MacProcessTreeMonitor()
    records = []

    records.append(run_monitored(
        index=1, kind="helper", name="launch",
        argv=helper_command("print('launch-ok', flush=True)"),
        logs_dir=logs, monitor=monitor, timeout_seconds=1.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.02,
    ))

    with tempfile.TemporaryDirectory(prefix="d1p05-timeout-") as directory:
        child_file = Path(directory) / "child.pid"
        timeout_code = (
            "import pathlib,subprocess,sys,time;"
            "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));"
            "print(p.pid,flush=True);time.sleep(30)"
        )
        timeout_record = run_monitored(
            index=2, kind="helper", name="timeout_cleanup",
            argv=helper_command(timeout_code, child_file),
            logs_dir=logs, monitor=monitor, timeout_seconds=0.35,
            rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.02,
        )
        child_pid = int(child_file.read_text())
        survivors = wait_for_cleanup(
            monitor, [timeout_record["pid"], child_pid]
        )
        timeout_record["helper_child_pid"] = child_pid
        timeout_record["cleanup_survivors"] = survivors
        write_json(ROOT / timeout_record["record_path"], timeout_record)
        records.append(timeout_record)

    with tempfile.TemporaryDirectory(prefix="d1p05-memory-") as directory:
        child_file = Path(directory) / "child.pid"
        memory_code = (
            "import pathlib,subprocess,sys,time;"
            "child='import time; x=bytearray(64*1024*1024); print(len(x),flush=True); time.sleep(30)';"
            "p=subprocess.Popen([sys.executable,'-I','-c',child]);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));"
            "print(p.pid,flush=True);time.sleep(30)"
        )
        memory_record = run_monitored(
            index=3, kind="helper", name="tree_memory_cleanup",
            argv=helper_command(memory_code, child_file),
            logs_dir=logs, monitor=monitor, timeout_seconds=3.0,
            rss_cutoff_bytes=48 * 1024**2, sample_interval_seconds=0.02,
        )
        child_pid = int(child_file.read_text())
        survivors = wait_for_cleanup(
            monitor, [memory_record["pid"], child_pid]
        )
        memory_record["helper_child_pid"] = child_pid
        memory_record["cleanup_survivors"] = survivors
        write_json(ROOT / memory_record["record_path"], memory_record)
        records.append(memory_record)

    monitor_record = run_monitored(
        index=4, kind="helper", name="monitor_failure_cleanup",
        argv=helper_command("import time;time.sleep(30)"),
        logs_dir=logs, monitor=FailingMonitor(), timeout_seconds=3.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.02,
    )
    monitor_record["cleanup_survivors"] = wait_for_cleanup(
        monitor, [monitor_record["pid"]]
    )
    write_json(ROOT / monitor_record["record_path"], monitor_record)
    records.append(monitor_record)

    records.append(run_monitored(
        index=5, kind="helper", name="launch_exception",
        argv=[str(output / "does-not-exist")],
        logs_dir=logs, monitor=monitor, timeout_seconds=1.0,
        rss_cutoff_bytes=512 * 1024**2, sample_interval_seconds=0.02,
    ))

    checks = {
        "launch": (
            records[0]["status"] == "COMPLETED"
            and records[0]["exit_status"] == 0
            and (ROOT / records[0]["stdout_path"]).read_text() == "launch-ok\n"
        ),
        "timeout": records[1]["status"] == "TIMEOUT" and records[1]["timed_out"],
        "timeout_cleanup": not records[1]["cleanup_survivors"],
        "tree_memory_cutoff": (
            records[2]["status"] == "MEMORY_CUTOFF"
            and records[2]["peak_tree_process_count"] >= 2
            and records[2]["peak_tree_rss_bytes"] > 48 * 1024**2
        ),
        "memory_cleanup": not records[2]["cleanup_survivors"],
        "monitor_failure": (
            records[3]["status"] == "MONITOR_ERROR"
            and records[3]["monitor_failed"]
        ),
        "monitor_failure_cleanup": not records[3]["cleanup_survivors"],
        "launch_exception_structured": (
            records[4]["status"] == "LAUNCH_ERROR"
            and not records[4]["process_launched"]
            and records[4]["error"].startswith("FileNotFoundError:")
        ),
    }
    result = {
        "task": "D1P-05",
        "kind": "pre-freeze harmless-helper infrastructure check",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "research_result": False,
        "platform": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "monitor": {
            "library": monitor.library_path,
            "metric": "aggregate process-tree resident bytes",
            "production_sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
            "production_cutoff_bytes": RSS_CUTOFF_BYTES,
            "hard_address_space_cap": False,
            "sampling_can_overshoot": True,
        },
        "checks": checks,
        "records": records,
    }
    write_json(output / "infrastructure-check.json", result)
    print(json.dumps({"status": result["status"], "checks": checks}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


def expected_limits():
    return {
        "calls_max": CALLS_MAX,
        "seconds_per_call": SECONDS_PER_CALL,
        "solver_wall_seconds_max": SOLVER_WALL_SECONDS_MAX,
        "rss_cutoff_bytes": RSS_CUTOFF_BYTES,
        "rss_sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
        "hard_address_space_cap": False,
        "sampling_can_overshoot": True,
        "attempts_per_query": 1,
        "sequential": True,
    }


def verify_freeze(freeze, manifest_path, resource_policy_path):
    for item in freeze["frozen_files"]:
        path = ROOT / item["path"]
        actual = sha256(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"frozen file mismatch {item['path']}: {actual}")
    if sha256(manifest_path) != freeze["artifact_manifest"]["sha256"]:
        raise RuntimeError("D1P-04 artifact manifest mismatch")
    if sha256(resource_policy_path) != freeze["resource_policy"]["sha256"]:
        raise RuntimeError("resource policy mismatch")
    solver = Path(freeze["solver"]["path"])
    if sha256(solver) != freeze["solver"]["sha256"]:
        raise RuntimeError("solver binary mismatch")
    if freeze["limits"] != expected_limits():
        raise RuntimeError("unexpected frozen limits")
    actual_platform = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    if freeze["platform"] != actual_platform:
        raise RuntimeError(f"platform mismatch: {actual_platform}")
    return solver


def call_plan(manifest):
    planned = []
    for control in manifest["controls"]:
        planned.append({
            "kind": "control", "name": control["name"],
            "path": ROOT / control["path"], "sha256": control["sha256"],
            "expected": control["expected"],
        })
    for artifact in manifest["artifacts"]:
        planned.append({
            "kind": "cell", "name": artifact["slot"],
            "path": ROOT / artifact["equivalence"]["path"],
            "sha256": artifact["equivalence"]["sha256"],
            "expected": "unsat",
        })
    if len(planned) != CALLS_MAX:
        raise RuntimeError(f"unexpected call plan length: {len(planned)}")
    return planned


def unrun_record(index, item, reason):
    return {
        "index": index, "kind": item["kind"], "name": item["name"],
        "query_path": relative(item["path"]),
        "query_sha256": item["sha256"], "expected": item["expected"],
        "status": "UNRUN_STOPPED", "attempts": 0, "reason": reason,
    }


def build_ledger(*, freeze_path, manifest_path, resource_policy_path,
                 freeze, manifest, records, stop_reason, total_elapsed):
    executed = [r for r in records if r.get("attempts") == 1]
    controls = [r for r in executed if r["kind"] == "control"]
    cells = [r for r in executed if r["kind"] == "cell"]
    prefix_passes = sum(
        bool(a["producer_prefix_audit"]["ordered_bytes_identical"])
        for a in manifest.get("artifacts", [])
    )
    controls_pass = (
        len(controls) == 2 and all(r.get("ok") for r in controls)
    )
    cells_unsat = sum(
        r.get("status") == "COMPLETED" and r.get("parsed") == "unsat"
        and r.get("ok") for r in cells
    )
    eligible = controls_pass and len(cells) == 150 and cells_unsat == 150 \
        and prefix_passes == 150 and stop_reason is None
    return {
        "task": "D1P-05",
        "status": "VALIDATION_PASS" if eligible else "VALIDATION_INCOMPLETE",
        "research_verdict": "UNKNOWN",
        "partition_eligible_for_primary_use": eligible,
        "stop_reason": stop_reason,
        "freeze": {"path": relative(freeze_path), "sha256": sha256(freeze_path)},
        "artifact_manifest": {
            "path": relative(manifest_path), "sha256": sha256(manifest_path),
        },
        "resource_policy": {
            "path": relative(resource_policy_path),
            "sha256": sha256(resource_policy_path),
        },
        "solver": freeze["solver"],
        "platform": freeze["platform"],
        "limits": freeze["limits"],
        "resource_policy_limitation": (
            "Sampled RSS is not a hard address-space cap and can overshoot "
            "between samples before process-group termination."
        ),
        "counts": {
            "planned": CALLS_MAX,
            "executed": len(executed),
            "unrun": CALLS_MAX - len(executed),
            "controls_executed": len(controls),
            "controls_passed": sum(bool(r.get("ok")) for r in controls),
            "cells_executed": len(cells),
            "cells_unsat": cells_unsat,
            "cells_sat": sum(r.get("parsed") == "sat" for r in cells),
            "cells_unknown": sum(r.get("parsed") == "unknown" for r in cells),
            "cells_timeout": sum(r.get("status") == "TIMEOUT" for r in cells),
            "cells_memory_cutoff": sum(
                r.get("status") == "MEMORY_CUTOFF" for r in cells
            ),
            "cells_other_unusable": sum(
                not (r.get("status") == "COMPLETED" and r.get("parsed") == "unsat")
                for r in cells
            ),
            "producer_prefix_audits_passed": prefix_passes,
        },
        "elapsed_seconds": round(total_elapsed, 6),
        "solver_wall_seconds": round(sum(r["elapsed_seconds"] for r in executed), 6),
        "observed_peak_tree_rss_bytes": max(
            (r.get("peak_tree_rss_bytes", 0) for r in executed), default=0
        ),
        "records": records,
        "interpretation": (
            "Eligibility is transformation evidence only. No parent "
            "satisfiability, consumer-direction, proof, consumer, or D1 "
            "security verdict follows; the research verdict remains UNKNOWN."
        ),
    }


def execute(args):
    freeze_path = args.freeze.resolve()
    manifest_path = args.manifest.resolve()
    resource_policy_path = args.resource_policy.resolve()
    output = args.output.resolve()
    ledger_path = args.ledger.resolve()
    for path in (output, ledger_path):
        if path.exists():
            raise FileExistsError(f"fresh D1P-05 evidence required: {path}")
    output.mkdir(parents=True)
    logs = output / "calls"
    logs.mkdir()

    total_started = time.monotonic()
    records = []
    stop_reason = None
    freeze = json.loads(freeze_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    planned = call_plan(manifest)
    try:
        solver = verify_freeze(
            freeze, manifest_path, resource_policy_path
        )
        if manifest["counts"] != {
            "parents": 6, "cells_per_parent": 25,
            "specialized_queries": 150, "equivalence_queries": 150,
            "controls": 2,
        }:
            raise RuntimeError("unexpected D1P-04 artifact counts")
        for item in planned:
            actual = sha256(item["path"])
            if actual != item["sha256"]:
                raise RuntimeError(
                    f"planned query mismatch {item['name']}: {actual}"
                )
    except Exception as exc:
        stop_reason = f"preflight infrastructure failure: {type(exc).__name__}: {exc}"
        records = [
            unrun_record(index, item, stop_reason)
            for index, item in enumerate(planned, 1)
        ]
        ledger = build_ledger(
            freeze_path=freeze_path, manifest_path=manifest_path,
            resource_policy_path=resource_policy_path, freeze=freeze,
            manifest=manifest, records=records, stop_reason=stop_reason,
            total_elapsed=time.monotonic() - total_started,
        )
        write_json(output / "equivalence-ledger.json", ledger)
        write_json(ledger_path, ledger)
        print(json.dumps({"status": ledger["status"], **ledger["counts"]}, sort_keys=True))
        return 2

    try:
        monitor = MacProcessTreeMonitor()
    except Exception as exc:
        stop_reason = (
            f"monitor initialization failure: {type(exc).__name__}: {exc}"
        )
        records = [
            unrun_record(index, item, stop_reason)
            for index, item in enumerate(planned, 1)
        ]
        ledger = build_ledger(
            freeze_path=freeze_path, manifest_path=manifest_path,
            resource_policy_path=resource_policy_path, freeze=freeze,
            manifest=manifest, records=records, stop_reason=stop_reason,
            total_elapsed=time.monotonic() - total_started,
        )
        write_json(output / "equivalence-ledger.json", ledger)
        write_json(ledger_path, ledger)
        print(json.dumps({"status": ledger["status"], **ledger["counts"]}, sort_keys=True))
        return 2
    for index, item in enumerate(planned, 1):
        if stop_reason is not None:
            records.append(unrun_record(index, item, stop_reason))
            continue
        used = sum(
            record.get("elapsed_seconds", 0)
            for record in records if record.get("attempts") == 1
        )
        remaining = SOLVER_WALL_SECONDS_MAX - used
        if remaining <= 0:
            stop_reason = "aggregate solver wall budget exhausted"
            records.append(unrun_record(index, item, stop_reason))
            continue
        call_limit = min(SECONDS_PER_CALL, remaining)
        record = run_monitored(
            index=index, kind=item["kind"], name=item["name"],
            argv=[solver, *freeze["solver"]["arguments"]],
            logs_dir=logs, monitor=monitor, input_path=item["path"],
            timeout_seconds=call_limit,
            rss_cutoff_bytes=RSS_CUTOFF_BYTES,
            sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
        )
        record.update({
            "attempts": 1,
            "query_path": relative(item["path"]),
            "query_sha256": item["sha256"],
            "expected": item["expected"],
            "parsed": parse_solver_output(ROOT / record["stdout_path"]),
        })
        record["ok"] = (
            record["status"] == "COMPLETED"
            and record["exit_status"] == 0
            and record["parsed"] == item["expected"]
        )
        write_json(ROOT / record["record_path"], record)
        records.append(record)

        if item["kind"] == "control":
            if not record["ok"]:
                stop_reason = (
                    f"failed control {item['name']}: status={record['status']} "
                    f"parsed={record['parsed']} exit={record['exit_status']}"
                )
        elif record["status"] == "COMPLETED" and record["parsed"] == "sat":
            stop_reason = f"cell equivalence counterexample: {item['name']}"
        elif record["status"] in ("TIMEOUT", "MEMORY_CUTOFF"):
            pass  # unusable cell; continue the fixed schedule
        elif record["status"] == "COMPLETED" and record["parsed"] == "unknown":
            pass  # unusable cell; continue the fixed schedule
        elif not record["ok"]:
            stop_reason = (
                f"infrastructure/execution failure {item['name']}: "
                f"status={record['status']} parsed={record['parsed']} "
                f"exit={record['exit_status']}"
            )

        partial_records = records + [
            unrun_record(next_index, next_item, "campaign not yet executed")
            for next_index, next_item in enumerate(planned[len(records):], len(records) + 1)
        ]
        checkpoint = build_ledger(
            freeze_path=freeze_path, manifest_path=manifest_path,
            resource_policy_path=resource_policy_path, freeze=freeze,
            manifest=manifest, records=partial_records,
            stop_reason=stop_reason or "campaign in progress",
            total_elapsed=time.monotonic() - total_started,
        )
        write_json(output / "equivalence-ledger.partial.json", checkpoint)

    ledger = build_ledger(
        freeze_path=freeze_path, manifest_path=manifest_path,
        resource_policy_path=resource_policy_path, freeze=freeze,
        manifest=manifest, records=records, stop_reason=stop_reason,
        total_elapsed=time.monotonic() - total_started,
    )
    write_json(output / "equivalence-ledger.json", ledger)
    write_json(ledger_path, ledger)
    partial = output / "equivalence-ledger.partial.json"
    if partial.exists():
        partial.unlink()
    print(json.dumps({
        "status": ledger["status"], **ledger["counts"],
        "solver_wall_seconds": ledger["solver_wall_seconds"],
        "observed_peak_tree_rss_bytes": ledger["observed_peak_tree_rss_bytes"],
    }, sort_keys=True))
    return 0 if ledger["partition_eligible_for_primary_use"] else 2


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    infra = subparsers.add_parser("infrastructure-check")
    infra.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("execute")
    run.add_argument("--freeze", type=Path, required=True)
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--resource-policy", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "infrastructure-check":
        return infrastructure_check(args.output)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
