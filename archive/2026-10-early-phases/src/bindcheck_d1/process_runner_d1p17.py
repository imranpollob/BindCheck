"""D1P-17 process runner with explicit observation/exit chronology.

The monitor is advisory.  A missing libproc root is not an exit, an access
failure is not a missing process, and only ``Popen.poll``/``wait`` confirms
the child status.  Cleanup events are recorded separately so a negative
return code is never used by itself to attribute the termination cause.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import signal
import subprocess
import time
from ctypes.util import find_library
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROC_PIDTASKINFO = 4
MAX_CHILDREN_PER_PROCESS = 4096


class ProcTaskInfo(ctypes.Structure):
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
    """Sample root and recursively visible children through macOS libproc."""

    def __init__(self, library_path: str | None = None) -> None:
        if platform.system() != "Darwin":
            raise RuntimeError("D1P-17 process monitoring requires macOS")
        path = library_path or find_library("proc")
        if not path:
            raise RuntimeError("macOS libproc not found")
        self.lib = ctypes.CDLL(path, use_errno=True)
        self.lib.proc_listchildpids.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        self.lib.proc_listchildpids.restype = ctypes.c_int
        self.lib.proc_pidinfo.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int,
        ]
        self.lib.proc_pidinfo.restype = ctypes.c_int

    def _children(self, pid: int) -> list[int]:
        values = (ctypes.c_int * MAX_CHILDREN_PER_PROCESS)()
        ctypes.set_errno(0)
        count = self.lib.proc_listchildpids(pid, values, ctypes.sizeof(values))
        error = ctypes.get_errno()
        if count < 0:
            if error in (1, 13):
                raise PermissionError(error, os.strerror(error), pid)
            raise RuntimeError(f"proc_listchildpids({pid}) failed: errno={error}")
        if count >= MAX_CHILDREN_PER_PROCESS:
            raise RuntimeError(f"child PID buffer saturated for {pid}: {count}")
        return [int(values[index]) for index in range(count) if values[index] > 0]

    def _rss(self, pid: int) -> int | None:
        info = ProcTaskInfo()
        ctypes.set_errno(0)
        returned = self.lib.proc_pidinfo(
            pid, PROC_PIDTASKINFO, 0, ctypes.byref(info), ctypes.sizeof(info),
        )
        error = ctypes.get_errno()
        if returned == ctypes.sizeof(info):
            return int(info.pti_resident_size)
        if returned == 0 and error in (0, 3):
            return None
        if returned == 0 and error in (1, 13):
            raise PermissionError(error, os.strerror(error), pid)
        raise RuntimeError(
            f"proc_pidinfo({pid}) returned {returned}/{ctypes.sizeof(info)}: errno={error}"
        )

    def sample(self, root_pid: int) -> dict[str, Any]:
        pending = [int(root_pid)]
        seen: set[int] = set()
        present: list[int] = []
        resident = 0
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
            "root_present": root_pid in present,
            "resident_bytes": resident,
            "process_count": len(present),
            "pids": sorted(present),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _probe_pid(pid: int) -> str:
    try:
        os.kill(pid, 0)
        return "EXISTS"
    except ProcessLookupError:
        return "ABSENT"
    except PermissionError:
        return "ACCESS_DENIED"


def run_monitored(
    *, index: int, kind: str, name: str, argv: list[str], logs_dir: Path,
    monitor: Any, input_path: Path | None = None, timeout_seconds: float = 30.0,
    rss_cutoff_bytes: int = 4 * 1024**3, sample_interval_seconds: float = 0.05,
    exit_confirm_seconds: float = 0.5, termination_wait_seconds: float = 0.5,
    group_kill: Callable[[int, int], None] = os.killpg,
) -> dict[str, Any]:
    """Run one process and record monitoring, cleanup, and exit as separate facts."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{index:03d}_{kind}_{name.replace('/', '__')}"
    stdout_path = logs_dir / f"{stem}.stdout"
    stderr_path = logs_dir / f"{stem}.stderr"
    record_path = logs_dir / f"{stem}.json"
    for path in (stdout_path, stderr_path, record_path):
        if path.exists():
            raise FileExistsError(f"fresh call evidence required: {path}")

    started_utc = _utc_now()
    started = time.monotonic()
    chronology: list[dict[str, Any]] = []

    def event(event_name: str, **details: Any) -> None:
        chronology.append({
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "event": event_name,
            **details,
        })

    process: subprocess.Popen[bytes] | None = None
    source = None
    status = "COMPLETED"
    error = None
    timed_out = False
    memory_cutoff = False
    monitor_access_failure = False
    root_process_disappearance = False
    confirmed_exit = False
    exit_confirmation = None
    peak_rss = None
    peak_process_count = None
    samples = 0
    termination_requested = False
    successful_runner_kill = False

    def confirm_wait(label: str, seconds: float) -> int | None:
        nonlocal confirmed_exit, exit_confirmation
        assert process is not None
        try:
            returncode = process.wait(timeout=seconds)
            confirmed_exit = True
            exit_confirmation = label
            event("confirmed_process_exit", method=label, returncode=returncode)
            return returncode
        except subprocess.TimeoutExpired:
            event("exit_not_confirmed", method=label, wait_seconds=seconds)
            return None

    def terminate(reason: str) -> None:
        nonlocal termination_requested, successful_runner_kill
        assert process is not None
        termination_requested = True
        event("termination_requested", reason=reason)
        try:
            group_kill(process.pid, signal.SIGKILL)
            successful_runner_kill = True
            event("process_group_sigkill_sent", pid=process.pid)
        except ProcessLookupError as exc:
            event("process_group_absent_during_cleanup", detail=str(exc))
        except PermissionError as exc:
            event("process_group_cleanup_access_failure", detail=str(exc), errno=exc.errno)
        except Exception as exc:  # evidence, followed by direct bounded fallback
            event("process_group_cleanup_error", detail=f"{type(exc).__name__}: {exc}")
        if confirm_wait("wait_after_group_cleanup", termination_wait_seconds) is not None:
            return
        try:
            process.kill()
            successful_runner_kill = True
            event("direct_sigkill_sent", pid=process.pid)
        except ProcessLookupError as exc:
            event("direct_cleanup_process_absent", detail=str(exc))
        except PermissionError as exc:
            event("direct_cleanup_access_failure", detail=str(exc), errno=exc.errno)
        except Exception as exc:
            event("direct_cleanup_error", detail=f"{type(exc).__name__}: {exc}")
        confirm_wait("wait_after_direct_cleanup", termination_wait_seconds)

    try:
        if input_path is not None:
            source = input_path.open("rb")
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            try:
                process = subprocess.Popen(
                    argv, stdin=source if source is not None else subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True,
                )
                event("process_launched", pid=process.pid, process_group=process.pid)
            except Exception as exc:
                status = "LAUNCH_ERROR"
                error = f"{type(exc).__name__}: {exc}"
                event("launch_error", detail=error)

            while process is not None and not confirmed_exit and not termination_requested:
                returncode = process.poll()
                if returncode is not None:
                    confirmed_exit = True
                    exit_confirmation = "poll"
                    event("confirmed_process_exit", method="poll", returncode=returncode)
                    break
                try:
                    sample = monitor.sample(process.pid)
                except PermissionError as exc:
                    monitor_access_failure = True
                    status = "MONITOR_ACCESS_FAILURE"
                    error = f"{type(exc).__name__}: {exc}"
                    event("monitor_access_failure", detail=str(exc), errno=exc.errno)
                    terminate(status)
                    break
                except Exception as exc:
                    status = "MONITOR_ERROR"
                    error = f"{type(exc).__name__}: {exc}"
                    event("monitor_error", detail=error)
                    terminate(status)
                    break

                if not sample["root_present"]:
                    root_process_disappearance = True
                    event("root_process_disappeared_from_monitor", sample=sample)
                    if confirm_wait("wait_after_root_disappearance", exit_confirm_seconds) is not None:
                        break
                    probe = _probe_pid(process.pid)
                    event("pid_zero_signal_probe", result=probe)
                    if probe == "ACCESS_DENIED":
                        monitor_access_failure = True
                        status = "MONITOR_ACCESS_FAILURE"
                        error = "root absent from libproc and zero-signal probe was not permitted"
                    else:
                        status = "ROOT_MONITOR_LOSS"
                        error = f"root absent from libproc without confirmed exit; pid probe={probe}"
                    terminate(status)
                    break

                samples += 1
                resident = sample.get("resident_bytes")
                count = sample.get("process_count")
                if resident is not None:
                    peak_rss = resident if peak_rss is None else max(peak_rss, resident)
                if count is not None:
                    peak_process_count = count if peak_process_count is None else max(peak_process_count, count)
                if resident is not None and resident > rss_cutoff_bytes:
                    memory_cutoff = True
                    status = "MEMORY_CUTOFF"
                    event("memory_cutoff_crossed", observed_bytes=resident, cutoff_bytes=rss_cutoff_bytes)
                    terminate(status)
                    break
                if time.monotonic() - started >= timeout_seconds:
                    timed_out = True
                    status = "TIMEOUT"
                    event("timeout_crossed", timeout_seconds=timeout_seconds)
                    terminate(status)
                    break
                time.sleep(sample_interval_seconds)

            if process is not None and not confirmed_exit and not termination_requested:
                if confirm_wait("final_wait", exit_confirm_seconds) is None:
                    status = "EXIT_WAIT_TIMEOUT"
                    error = "final bounded wait did not confirm process exit"
                    terminate(status)

            # A root may exit after spawning a same-session child.  Reap/confirm
            # the root first, then clean the residual process group explicitly.
            if process is not None and confirmed_exit and not termination_requested:
                try:
                    group_kill(process.pid, signal.SIGKILL)
                    successful_runner_kill = True
                    event("residual_process_group_sigkill_sent_after_root_exit", pid=process.pid)
                except ProcessLookupError:
                    event("no_residual_process_group_after_root_exit")
                except PermissionError as exc:
                    event("residual_group_cleanup_access_failure", detail=str(exc), errno=exc.errno)
                except Exception as exc:
                    event("residual_group_cleanup_error", detail=f"{type(exc).__name__}: {exc}")
    finally:
        if source is not None:
            source.close()

    for path in (stdout_path, stderr_path):
        if not path.exists():
            path.touch()
    returncode = process.returncode if process is not None else None
    if status == "COMPLETED" and confirmed_exit and returncode != 0:
        status = "PROCESS_ERROR"
    if process is not None and not confirmed_exit:
        status = "UNCONFIRMED_EXIT"
        error = (error + "; " if error else "") + "runner ended without confirmed process exit"
    signal_number = -returncode if returncode is not None and returncode < 0 else None
    termination_attribution = (
        "runner sent SIGKILL before confirmed exit"
        if signal_number == signal.SIGKILL and successful_runner_kill else
        "SIGKILL observed, source not identified by this record"
        if signal_number == signal.SIGKILL else
        "no SIGKILL exit status"
    )
    record = {
        "schema": "bindcheck.d1p17.process-call/v1",
        "index": index, "kind": kind, "name": name, "argv": argv,
        "started_utc": started_utc,
        "finished_utc": _utc_now(), "elapsed_seconds": round(time.monotonic() - started, 6),
        "status": status, "error": error, "pid": process.pid if process else None,
        "exit_status": returncode, "signal_number": signal_number,
        "confirmed_process_exit": confirmed_exit, "exit_confirmation": exit_confirmation,
        "root_process_disappearance": root_process_disappearance,
        "monitor_access_failure": monitor_access_failure,
        "timed_out": timed_out, "memory_cutoff": memory_cutoff,
        "termination_requested": termination_requested,
        "successful_runner_kill": successful_runner_kill,
        "termination_attribution": termination_attribution,
        "chronology": chronology,
        "timeout_seconds": timeout_seconds,
        "memory_policy": {
            "metric": "sum of libproc resident bytes over root and recursively visible children",
            "cutoff_bytes": rss_cutoff_bytes,
            "sample_interval_seconds": sample_interval_seconds,
            "hard_address_space_cap": False,
        },
        "memory_samples": samples, "peak_tree_rss_bytes": peak_rss,
        "peak_tree_process_count": peak_process_count,
        "stdout_path": str(stdout_path), "stdout_sha256": _sha256(stdout_path),
        "stderr_path": str(stderr_path), "stderr_sha256": _sha256(stderr_path),
    }
    if input_path is not None:
        record.update({
            "input_path": str(input_path), "input_sha256": _sha256(input_path),
            "input_bytes": input_path.stat().st_size,
        })
    _write_json(record_path, record)
    return record
