#!/usr/bin/env python3
"""D1P-17 bounded consumer-backend study and monitor repair evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from bindcheck_d1.joint_warptoad import (
    BACKEND_OPTIONS, balanced_smt_parentheses, canonical_sha256, encode_query,
)
from bindcheck_d1.process_runner_d1p17 import MacProcessTreeMonitor, run_monitored


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-17"
INPUTS = RAW / "inputs"
PREPARED = RAW / "prepared"
SOLVER = Path("/Users/imranpollob/Coding/bc/BindCheck/tools/cvc5-1.4.2-gpl/bin/cvc5")
SOURCE_RAW = Path("/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw")
SOURCE_14C = SOURCE_RAW / "D1P-14C"
SOURCE_14D = SOURCE_RAW / "D1P-14D"
PROTOCOL = ROOT / "protocols/d1/d1p-17-consumer-backends.json"
FREEZE = ROOT / "metadata/d1/d1p-17-primary-freeze.json"
PREPARATION = RAW / "preparation.json"
MONITOR_TESTS = RAW / "monitor-tests.json"
EQUIVALENCE = RAW / "overflow-equivalence.json"
CONTROLS = RAW / "control-ledger.json"
PRIMARY = RAW / "primary-ledger.json"
SOLVER_ARGS = ["--lang=smt2", "--ff-solver=split", "--produce-models", "--dump-models"]
SOLVER_SHA256 = "a083a7f56a3f61691583b699076322bbcbf6732decfb4f6dc41850dbcc3df027"
RSS_CUTOFF = 4 * 1024**3
SAMPLE_INTERVAL = 0.05

CONTROL_TARGETS = {"C1": "G1", "C2": "G3", "C3": "G4", "C4": "G5"}
BACKENDS = ("T-ARITH", "T-OVF")
PRIMARY_SCHEDULE = (
    ("T-ARITH", "Q1", True, "omega-auth1.json"),
    ("T-ARITH", "Q2", False, "omega-auth1.json"),
    ("T-OVF", "Q1", True, "omega-auth1.json"),
    ("T-OVF", "Q2", False, "omega-auth1.json"),
    ("T-OVF", "Q3", False, "omega-nonvac1.json"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    shown = str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)
    return {"path": shown, "sha256": sha256(resolved), "bytes": resolved.stat().st_size}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def command_version(argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=30)
    return {"argv": argv, "exit_status": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def solver_answer(call: dict[str, Any]) -> str:
    text = Path(call["stdout_path"]).read_text(errors="replace")
    for line in text.splitlines():
        answer = line.strip().upper()
        if answer in {"SAT", "UNSAT", "UNKNOWN"}:
            return answer
    return "UNKNOWN"


def fixture_words(fixture: dict[str, Any]) -> list[int]:
    return [int(value) for value in fixture["public_words"]]


def bv(value: int) -> str:
    return f"(_ bv{value} 256)"


def transformed_control(
    omega: dict[str, Any], fixture: dict[str, Any], *, control: str,
    polarity: str, backend: str,
) -> tuple[bytes, dict[str, Any]]:
    base, base_certificate = encode_query(
        omega, drop_producer=True, backend_option=backend,
    )
    terminal = b"(assert (or G1 G2 G3 G4 G5))\n(check-sat)\n"
    if base.count(terminal) != 1:
        raise RuntimeError("unexpected AUTH terminal")
    target = CONTROL_TARGETS[control]
    lines = [
        "; D1P-17 transformed deterministic control",
        f"; backend={backend} control={control} polarity={polarity} target={target}",
        *[f"(assert (= pi{index} {bv(value)}))"
          for index, value in enumerate(fixture_words(fixture))],
        f"(assert (= basefee {bv(int(fixture['environment']['basefee']))}))",
        f"(assert {target})", "(check-sat)",
    ]
    query = base.replace(terminal, ("\n".join(lines) + "\n").encode())
    parens = balanced_smt_parentheses(query)
    if not parens["balanced"]:
        raise RuntimeError(f"unbalanced control: {parens}")
    return query, {
        "schema": "bindcheck.d1p17.control-transformation/v1",
        "backend_option": backend, "control": control, "polarity": polarity,
        "target": target, "expected": "SAT" if polarity == "positive" else "UNSAT",
        "fixture_sha256": canonical_sha256(fixture),
        "omega_sha256": canonical_sha256(omega),
        "base_certificate": base_certificate,
        "query_sha256": hashlib.sha256(query).hexdigest(), "query_bytes": len(query),
        "classification": "fixed-input regression, not proof of transformation equivalence",
    }


def source_items() -> dict[str, Path]:
    result = {
        "fixture.json": SOURCE_14D / "fixed-control-fixture.json",
        "omega-base-negative.json": SOURCE_14D / "prepared/omega-base-negative.json",
        "omega-c1-positive.json": SOURCE_14D / "prepared/omega-c1-positive.json",
        "omega-c2-positive.json": SOURCE_14D / "prepared/omega-c2-positive.json",
        "omega-c3-positive.json": SOURCE_14D / "prepared/omega-c3-positive.json",
        "omega-c4-positive.json": SOURCE_14D / "prepared/omega-c4-positive.json",
        "omega-auth1.json": SOURCE_14C / "prepared/omega-auth1.json",
        "omega-nonvac1.json": SOURCE_14C / "prepared/omega-nonvac1.json",
        "d1p14d-q3-record.json": SOURCE_14D / "solver-logs/011_primary_Q3.json",
        "d1p14d-q3.stdout": SOURCE_14D / "solver-logs/011_primary_Q3.stdout",
        "d1p14d-q3.stderr": SOURCE_14D / "solver-logs/011_primary_Q3.stderr",
        "d1p14d-solver-ledger.json": SOURCE_14D / "solver-ledger.json",
    }
    return result


def make_equivalence_query(kind: str) -> bytes:
    if kind == "addition":
        old = "(bvuge (bvadd x y) x)"
        native = "(not (bvuaddo x y))"
    elif kind == "multiplication":
        old = "(= ((_ extract 511 256) (bvmul ((_ zero_extend 256) x) ((_ zero_extend 256) y))) (_ bv0 256))"
        native = "(not (bvumulo x y))"
    else:
        raise ValueError(kind)
    return ("\n".join([
        "; D1P-17 general symbolic equivalence at actual uint256 width",
        "(set-logic QF_BV)",
        "(declare-const x (_ BitVec 256))", "(declare-const y (_ BitVec 256))",
        f"(assert (xor {old} {native}))", "(check-sat)", "",
    ])).encode()


def stage_prepare() -> int:
    if RAW.exists() or FREEZE.exists():
        raise SystemExit("D1P-17 namespace or freeze already exists")
    if BACKEND_OPTIONS != {"BASE", "T-ARITH", "T-OVF"}:
        raise SystemExit(f"unexpected backend option set: {BACKEND_OPTIONS}")
    if sha256(SOLVER) != SOLVER_SHA256:
        raise SystemExit("solver hash mismatch")
    INPUTS.mkdir(parents=True)
    PREPARED.mkdir(parents=True)
    copied = []
    for name, source in source_items().items():
        if not source.is_file():
            raise SystemExit(f"required predecessor evidence missing: {source}")
        destination = INPUTS / name
        shutil.copy2(source, destination)
        if sha256(destination) != sha256(source):
            raise SystemExit(f"copy mismatch: {name}")
        copied.append({"destination": record(destination), "source": str(source),
                       "source_sha256": sha256(source)})

    fixture = load_json(INPUTS / "fixture.json")
    control_schedule = []
    for backend in BACKENDS:
        backend_dir = PREPARED / backend.lower()
        backend_dir.mkdir()
        for control, target in CONTROL_TARGETS.items():
            for polarity in ("positive", "negative"):
                omega_name = f"omega-{control.lower()}-positive.json" if polarity == "positive" else "omega-base-negative.json"
                omega = load_json(INPUTS / omega_name)
                query, certificate = transformed_control(
                    omega, fixture, control=control, polarity=polarity, backend=backend,
                )
                stem = f"{control.lower()}-{polarity}"
                query_path = backend_dir / f"{stem}.smt2"
                cert_path = backend_dir / f"{stem}.json"
                query_path.write_bytes(query); write_json(cert_path, certificate)
                control_schedule.append({
                    "backend": backend, "control": control, "polarity": polarity,
                    "target": target, "expected": certificate["expected"],
                    "timeout_seconds": 30, "query": record(query_path),
                    "certificate": record(cert_path),
                })

    primary_schedule = []
    for backend, query_id, dropped, omega_name in PRIMARY_SCHEDULE:
        omega = load_json(INPUTS / omega_name)
        query, certificate = encode_query(
            omega, drop_producer=dropped, backend_option=backend,
        )
        path = PREPARED / backend.lower() / f"{query_id.lower()}.smt2"
        cert_path = PREPARED / backend.lower() / f"{query_id.lower()}.json"
        path.write_bytes(query); write_json(cert_path, certificate)
        primary_schedule.append({
            "backend": backend, "id": query_id, "drop_producer": dropped,
            "timeout_seconds": 300, "query": record(path), "certificate": record(cert_path),
        })

    equivalence = []
    eq_dir = PREPARED / "equivalence"; eq_dir.mkdir()
    for kind in ("addition", "multiplication"):
        path = eq_dir / f"{kind}.smt2"
        path.write_bytes(make_equivalence_query(kind))
        equivalence.append({"kind": kind, "width": 256, "timeout_seconds": 60,
                            "expected": "UNSAT", "query": record(path)})

    parse_records = []
    for item in control_schedule + primary_schedule + equivalence:
        query = ROOT / item["query"]["path"]
        with query.open("rb") as source:
            parsed = subprocess.run(
                [str(SOLVER), "--lang=smt2", "--parse-only"], stdin=source,
                capture_output=True, timeout=60, check=False,
            )
        parse_records.append({"query": item["query"], "exit_status": parsed.returncode,
                              "stderr": parsed.stderr.decode(errors="replace")})
        if parsed.returncode != 0:
            raise SystemExit(f"parse preflight failed: {query}: {parsed.stderr.decode(errors='replace')}")

    q3 = load_json(INPUTS / "d1p14d-q3-record.json")
    q3_audit = {
        "source_record": record(INPUTS / "d1p14d-q3-record.json"),
        "chronology": [
            {"order": 1, "fact": "libproc sample reported root PID absent"},
            {"order": 2, "fact": "bounded wait did not confirm process exit"},
            {"order": 3, "fact": "process-group SIGKILL request failed with Operation not permitted"},
            {"order": 4, "fact": "wait reaped child with return code -9"},
        ],
        "record_crosscheck": {
            "status": q3["status"], "error": q3["error"], "exit_status": q3["exit_status"],
            "termination": q3["termination"], "stdout_sha256": q3["stdout_sha256"],
            "stderr_sha256": q3["stderr_sha256"],
        },
        "diagnosis": (
            "Root-process disappearance, cleanup access failure, and confirmed exit are "
            "distinct events. Return code -9 identifies SIGKILL termination but does not "
            "identify its cause; the old runner recorded no successful kill operation."
        ),
        "disposition": "D1P-14D Q3 remains UNKNOWN",
    }
    write_json(RAW / "d1p14d-q3-chronology-audit.json", q3_audit)
    payload = {
        "schema": "bindcheck.d1p17.preparation/v1",
        "task": "D1P-17", "host": {"platform": platform.platform(), "python": sys.version},
        "diagnosis_wording": "The current consumer-only encoding times out; nonlinear fee arithmetic is a suspected bottleneck.",
        "copied_predecessor_inputs": copied,
        "q3_audit": record(RAW / "d1p14d-q3-chronology-audit.json"),
        "backend_options": list(BACKENDS), "combined_option_available": False,
        "control_schedule": control_schedule, "equivalence_schedule": equivalence,
        "primary_schedule_draft": primary_schedule,
        "parse_preflight": parse_records,
        "solver": {**record(SOLVER), "version": command_version([str(SOLVER), "--version"])},
        "protocol": record(PROTOCOL),
    }
    write_json(PREPARATION, payload)
    print(json.dumps({"stage": "prepare", "controls": len(control_schedule),
                      "primary": len(primary_schedule), "parse_pass": len(parse_records)}, sort_keys=True), flush=True)
    return 0


def _child_absent(pid: int | None, seconds: float = 2.0) -> bool:
    if pid is None:
        return False
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True)
        if not result.stdout.strip():
            return True
        time.sleep(0.05)
    return False


class AccessDeniedMonitor:
    def sample(self, root_pid: int) -> dict[str, Any]:
        raise PermissionError(1, "Operation not permitted", root_pid)


class MissingRootMonitor:
    def sample(self, root_pid: int) -> dict[str, Any]:
        return {"root_present": False, "resident_bytes": 0, "process_count": 0, "pids": []}


def stage_monitor_tests() -> int:
    if not PREPARATION.exists() or MONITOR_TESTS.exists():
        raise SystemExit("prepare first; monitor evidence must be fresh")
    output = RAW / "monitor-tests"; logs = output / "calls"; output.mkdir()
    monitor = MacProcessTreeMonitor()
    python = sys.executable
    child_paths: dict[str, Path] = {}
    cases = [
        ("normal_exit", [python, "-I", "-c", "print('normal',flush=True)"], monitor, 2.0, 512 * 1024**2),
        ("timeout", [python, "-I", "-c", "import time;time.sleep(30)"], monitor, 0.25, 512 * 1024**2),
        ("memory_cutoff", [python, "-I", "-c", "import time;x=bytearray(96*1024*1024);time.sleep(30)"], monitor, 3.0, 48 * 1024**2),
    ]
    for name in ("child_spawn", "early_root_exit"):
        child_paths[name] = output / f"{name}.pid"
    spawn_code = (
        "import pathlib,subprocess,sys,time;"
        "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
        "pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)"
    )
    early_code = (
        "import pathlib,subprocess,sys;"
        "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
        "pathlib.Path(sys.argv[1]).write_text(str(p.pid));print('root-exit',flush=True)"
    )
    cases.extend([
        ("child_spawn", [python, "-I", "-c", spawn_code, str(child_paths["child_spawn"])], monitor, 0.35, 512 * 1024**2),
        ("early_root_exit", [python, "-I", "-c", early_code, str(child_paths["early_root_exit"])], monitor, 2.0, 512 * 1024**2),
        ("monitor_access_failure", [python, "-I", "-c", "import time;time.sleep(30)"], AccessDeniedMonitor(), 2.0, 512 * 1024**2),
        ("root_disappearance", [python, "-I", "-c", "import time;time.sleep(30)"], MissingRootMonitor(), 2.0, 512 * 1024**2),
    ])
    calls = []
    for index, (name, argv, selected_monitor, timeout, cutoff) in enumerate(cases, 1):
        calls.append(run_monitored(
            index=index, kind="helper", name=name, argv=argv, logs_dir=logs,
            monitor=selected_monitor, timeout_seconds=timeout,
            rss_cutoff_bytes=cutoff, sample_interval_seconds=0.01,
        ))
    by_name = {item["name"]: item for item in calls}
    child_pids = {name: int(path.read_text()) if path.exists() else None
                  for name, path in child_paths.items()}
    checks = {
        "normal_exit": by_name["normal_exit"]["status"] == "COMPLETED" and by_name["normal_exit"]["exit_status"] == 0,
        "timeout": by_name["timeout"]["status"] == "TIMEOUT" and by_name["timeout"]["confirmed_process_exit"],
        "memory_cutoff": by_name["memory_cutoff"]["status"] == "MEMORY_CUTOFF" and by_name["memory_cutoff"]["confirmed_process_exit"],
        "child_spawn": by_name["child_spawn"]["peak_tree_process_count"] == 2 and by_name["child_spawn"]["status"] == "TIMEOUT",
        "child_spawn_cleanup": _child_absent(child_pids["child_spawn"]),
        "early_root_exit": by_name["early_root_exit"]["status"] == "COMPLETED" and by_name["early_root_exit"]["exit_status"] == 0,
        "early_root_child_cleanup": _child_absent(child_pids["early_root_exit"]),
        "access_failure_distinct": by_name["monitor_access_failure"]["status"] == "MONITOR_ACCESS_FAILURE" and by_name["monitor_access_failure"]["monitor_access_failure"],
        "root_disappearance_distinct": by_name["root_disappearance"]["status"] == "ROOT_MONITOR_LOSS" and by_name["root_disappearance"]["root_process_disappearance"],
        "every_exit_confirmed": all(item["confirmed_process_exit"] for item in calls),
    }
    payload = {"schema": "bindcheck.d1p17.monitor-tests/v1", "calls": calls,
               "child_pids": child_pids, "checks": checks, "all_pass": all(checks.values())}
    write_json(MONITOR_TESTS, payload)
    print(json.dumps({"stage": "monitor-tests", "checks": checks, "all_pass": all(checks.values())}, sort_keys=True), flush=True)
    return 0 if all(checks.values()) else 1


def stage_equivalence() -> int:
    if not load_json(MONITOR_TESTS)["all_pass"] or EQUIVALENCE.exists():
        raise SystemExit("monitor tests must pass; equivalence evidence must be fresh")
    schedule = load_json(PREPARATION)["equivalence_schedule"]
    if len(schedule) != 2:
        raise SystemExit("equivalence call bound violated")
    logs = RAW / "equivalence-logs"; monitor = MacProcessTreeMonitor(); calls = []
    for index, item in enumerate(schedule, 1):
        call = run_monitored(
            index=index, kind="equivalence", name=item["kind"],
            argv=[str(SOLVER), "--lang=smt2"], logs_dir=logs, monitor=monitor,
            input_path=ROOT / item["query"]["path"], timeout_seconds=60,
            rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL,
        )
        call["answer"] = solver_answer(call); calls.append(call)
        if call["answer"] != "UNSAT":
            break
    resolved = len(calls) == 2 and all(item["answer"] == "UNSAT" for item in calls)
    payload = {"schema": "bindcheck.d1p17.overflow-equivalence/v1", "calls": calls,
               "calls_used": len(calls), "maximum_calls": 2,
               "status": "validated" if resolved else "equivalence unresolved",
               "identity": (
                   "For unsigned w-bit x,y: not bvumulo(x,y) iff the upper w bits of the "
                   "2w-bit product of zero-extended operands are zero; not bvuaddo(x,y) "
                   "iff bvadd(x,y) >=u x. Checks use symbolic x,y at w=256."
               )}
    write_json(EQUIVALENCE, payload)
    print(json.dumps({"stage": "equivalence", "status": payload["status"],
                      "answers": [item["answer"] for item in calls]}, sort_keys=True), flush=True)
    return 0 if resolved else 1


def stage_controls() -> int:
    equivalence_status = load_json(EQUIVALENCE)["status"]
    if equivalence_status not in {"validated", "equivalence unresolved"} or CONTROLS.exists():
        raise SystemExit("equivalence must be complete; controls must be fresh")
    schedule = load_json(PREPARATION)["control_schedule"]
    if len(schedule) != 16:
        raise SystemExit("expected sixteen controls")
    logs = RAW / "control-logs"; monitor = MacProcessTreeMonitor(); calls = []
    stopped = None
    for index, item in enumerate(schedule, 1):
        call = run_monitored(
            index=index, kind="control", name=f"{item['backend']}-{item['control']}-{item['polarity']}",
            argv=[str(SOLVER), *SOLVER_ARGS], logs_dir=logs, monitor=monitor,
            input_path=ROOT / item["query"]["path"], timeout_seconds=30,
            rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL,
        )
        call["answer"] = solver_answer(call); call["expected"] = item["expected"]
        call["polarity_pass"] = call["answer"] == item["expected"]
        calls.append(call)
        print(json.dumps({"control": call["name"], "answer": call["answer"],
                          "expected": call["expected"], "pass": call["polarity_pass"]}, sort_keys=True), flush=True)
        if not call["polarity_pass"]:
            stopped = call["name"]
            break
    all_pass = len(calls) == 16 and all(item["polarity_pass"] for item in calls)
    write_json(CONTROLS, {"schema": "bindcheck.d1p17.control-ledger/v1",
                          "calls": calls, "all_pass": all_pass,
                          "stopped_on_failure": stopped, "regression_only": True,
                          "overflow_equivalence_status": equivalence_status,
                          "t_ovf_validated": equivalence_status == "validated"})
    return 0 if all_pass else 1


def tracked_input_records() -> list[dict[str, Any]]:
    paths = [
        ROOT / "src/bindcheck_d1/joint_warptoad.py",
        ROOT / "src/bindcheck_d1/joint_warptoad_d1p14d.py",
        ROOT / "src/bindcheck_d1/process_runner_d1p17.py",
        Path(__file__), ROOT / "tests/d1/test_d1p17_backend.py",
        ROOT / "docs/research-contract.md", PROTOCOL, SOLVER,
        PREPARATION, MONITOR_TESTS, EQUIVALENCE, CONTROLS,
    ]
    paths.extend(path for path in sorted(INPUTS.rglob("*")) if path.is_file())
    paths.extend(path for path in sorted(PREPARED.rglob("*")) if path.is_file())
    return [record(path) for path in paths]


def stage_freeze() -> int:
    if FREEZE.exists() or not load_json(CONTROLS)["all_pass"]:
        raise SystemExit("all controls must pass and freeze must be fresh")
    draft = load_json(PREPARATION)["primary_schedule_draft"]
    if [(i["backend"], i["id"]) for i in draft] != [(a, b) for a, b, _c, _d in PRIMARY_SCHEDULE]:
        raise SystemExit("primary schedule mismatch")
    value = {
        "schema": "bindcheck.d1p17.primary-freeze/v1", "task": "D1P-17",
        "schedule": draft, "attempts_each": 1, "timeout_seconds_each": 300,
        "maximum_solver_seconds": 1500, "sequential": True,
        "combined_transformation": False, "post_freeze_tuning": False,
        "preconditions": {"monitor_tests": record(MONITOR_TESTS),
                          "equivalence": record(EQUIVALENCE), "controls": record(CONTROLS)},
        "heavy_job_gate": "before every primary call: no cvc5, nargo, cargo, rustc, clang, make, ninja, xcodebuild, or swift build process",
        "load_average": "record sysctl vm.loadavg before and after every primary call",
        "claim_scope": (
            "Both transformations are backend options available identically to all later "
            "method arms. Neither demonstrates a consumer-direction advantage."
        ),
        "hash_complete_inputs": tracked_input_records(),
    }
    write_json(FREEZE, value)
    print(json.dumps({"stage": "freeze", "path": str(FREEZE), "sha256": sha256(FREEZE)}, sort_keys=True), flush=True)
    return 0


HEAVY_NAMES = {"cvc5", "nargo", "cargo", "rustc", "clang", "make", "ninja", "xcodebuild", "swift"}


def heavy_processes() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,comm=,args="], capture_output=True, text=True, check=True,
    )
    current = os.getpid(); parent = os.getppid(); found = []
    for line in completed.stdout.splitlines():
        match = re.match(r"\s*(\d+)\s+(\d+)\s+(\S+)\s+(.*)", line)
        if not match:
            continue
        pid, ppid = int(match.group(1)), int(match.group(2))
        command, args = match.group(3), match.group(4)
        base = Path(command).name.lower()
        if pid in {current, parent}:
            continue
        is_heavy = base in HEAVY_NAMES or base.startswith("cvc5")
        if base == "swift" and " build" not in f" {args}":
            is_heavy = False
        if is_heavy:
            found.append({"pid": pid, "ppid": ppid, "command": command, "args": args})
    return found


def load_average() -> dict[str, Any]:
    completed = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True, check=False)
    return {"argv": ["sysctl", "-n", "vm.loadavg"], "exit_status": completed.returncode,
            "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def verify_freeze() -> dict[str, Any]:
    frozen = load_json(FREEZE)
    for item in frozen["hash_complete_inputs"]:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"frozen input changed: {item['path']}")
    return frozen


def stage_run() -> int:
    if not FREEZE.exists() or PRIMARY.exists():
        raise SystemExit("freeze first; primary evidence must be fresh")
    frozen = verify_freeze(); logs = RAW / "primary-logs"; monitor = MacProcessTreeMonitor()
    ledger = {"schema": "bindcheck.d1p17.primary-ledger/v1",
              "freeze": {**record(FREEZE), "freeze_sha256": sha256(FREEZE)},
              "calls": [], "stopped": False, "stop_reason": None}
    write_json(PRIMARY, ledger)
    for index, item in enumerate(frozen["schedule"], 1):
        verify_freeze()
        competing = heavy_processes()
        before = load_average()
        if competing:
            ledger["stopped"] = True
            ledger["stop_reason"] = f"heavy-job gate before {item['backend']} {item['id']}"
            ledger["blocked_call"] = {"item": item, "heavy_processes": competing,
                                      "load_average_before": before}
            write_json(PRIMARY, ledger)
            print(json.dumps({"stage": "primary", "stopped": ledger["stop_reason"],
                              "heavy_processes": competing}, sort_keys=True), flush=True)
            return 1
        print(json.dumps({"stage": "primary-start", "index": index,
                          "backend": item["backend"], "query": item["id"],
                          "load_average_before": before["stdout"]}, sort_keys=True), flush=True)
        call = run_monitored(
            index=index, kind="primary", name=f"{item['backend']}-{item['id']}",
            argv=[str(SOLVER), *SOLVER_ARGS], logs_dir=logs, monitor=monitor,
            input_path=ROOT / item["query"]["path"], timeout_seconds=300,
            rss_cutoff_bytes=RSS_CUTOFF, sample_interval_seconds=SAMPLE_INTERVAL,
        )
        call["answer"] = solver_answer(call)
        call["backend"] = item["backend"]; call["query_id"] = item["id"]
        call["load_average_before"] = before; call["load_average_after"] = load_average()
        call["heavy_processes_before"] = competing
        call["candidate_validation"] = (
            "not applicable; no SAT answer" if call["answer"] != "SAT" else
            "REQUIRED: validate original arithmetic, full producer relation, and consumer execution"
        )
        ledger["calls"].append(call); write_json(PRIMARY, ledger)
        print(json.dumps({"stage": "primary-finish", "index": index,
                          "backend": item["backend"], "query": item["id"],
                          "answer": call["answer"], "status": call["status"],
                          "elapsed_seconds": call["elapsed_seconds"],
                          "load_average_after": call["load_average_after"]["stdout"]}, sort_keys=True), flush=True)
        if call["answer"] == "SAT":
            ledger["stopped"] = True
            ledger["stop_reason"] = "SAT candidate requires original-relation validation before further interpretation"
            write_json(PRIMARY, ledger)
            return 2
    ledger["complete_schedule"] = len(ledger["calls"]) == 5
    ledger["charged_solver_seconds"] = round(sum(min(300, item["elapsed_seconds"]) for item in ledger["calls"]), 6)
    ledger["outcomes"] = {f"{item['backend']}-{item['query_id']}": item["answer"] for item in ledger["calls"]}
    write_json(PRIMARY, ledger)
    return 0 if ledger["complete_schedule"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "monitor-tests", "equivalence", "controls", "freeze", "run"])
    args = parser.parse_args()
    return {
        "prepare": stage_prepare, "monitor-tests": stage_monitor_tests,
        "equivalence": stage_equivalence, "controls": stage_controls,
        "freeze": stage_freeze, "run": stage_run,
    }[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
