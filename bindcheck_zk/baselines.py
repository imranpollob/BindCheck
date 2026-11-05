from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import shutil
import tempfile
import time
from typing import Any

from .models import aggregate, result, sha256_file
from .subprocesses import run


COMMANDS = {
    "slither": ["slither"],
    "circomspect": ["circomspect"],
    "zkap": ["zkap"],
    "picus": ["picus"],
}


def _executable(tool: str) -> str | None:
    found = shutil.which(COMMANDS[tool][0])
    if found:
        return found
    project_root = pathlib.Path(__file__).resolve().parents[1]
    local = {
        "circomspect": project_root / "tools" / "circomspect-src" / "target" / "release" / "circomspect",
        "picus": project_root / "tools" / "picus-src" / "run-picus",
    }.get(tool)
    return str(local) if local is not None and local.is_file() else None


def _explicit(root: pathlib.Path, values: list[str] | None, suffixes: set[str]) -> list[pathlib.Path]:
    output: list[pathlib.Path] = []
    for raw in values or []:
        path = pathlib.Path(raw)
        path = path if path.is_absolute() else root / path
        path = path.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"baseline input escapes repository root: {raw}") from exc
        if not path.is_file() or path.suffix.lower() not in suffixes:
            raise ValueError(f"unsupported or missing baseline input: {raw}")
        output.append(path)
    return output


def _version(tool: str, executable: str, root: pathlib.Path, timeout: float) -> str | None:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    source_roots = {
        "circomspect": project_root / "tools" / "circomspect-src",
        "picus": project_root / "tools" / "picus-src",
    }
    source = source_roots.get(tool)
    if source is not None and source.joinpath(".git").is_dir():
        record = run(["git", "rev-parse", "HEAD"], cwd=source, timeout=min(5.0, timeout))
        if record["exit_status"] == 0:
            return "git:" + record["stdout"].strip()
    record = run([executable, "--version"], cwd=root, timeout=min(10.0, timeout))
    lines = (record["stdout"] or record["stderr"]).strip().splitlines()
    return lines[0] if record["exit_status"] == 0 and lines else None


def _unknown_patterns(reason: str, message: str) -> tuple[dict[str, Any], dict[str, Any]]:
    findings = {pattern: result(pattern, "UNKNOWN", reason, message, grade="E0") for pattern in ("P1", "P2", "P3", "P4", "P5")}
    summary = {pattern: {**aggregate([finding]), "results": 1, "reasons": [reason]} for pattern, finding in findings.items()}
    return findings, summary


def run_baseline(
    tool: str,
    root: pathlib.Path,
    timeout: float = 120.0,
    *,
    circuit_paths: list[str] | None = None,
    consumer_paths: list[str] | None = None,
) -> dict[str, Any]:
    started_utc = dt.datetime.now(dt.UTC).isoformat()
    started = time.monotonic()
    root = root.resolve()
    circuits_explicit = _explicit(root, circuit_paths, {".circom", ".nr"})
    consumers_explicit = _explicit(root, consumer_paths, {".sol"})
    executable = _executable(tool)
    temporary: tempfile.TemporaryDirectory[str] | None = None
    preprocessing: list[dict[str, Any]] = []
    inputs = []
    for path in sorted(root.rglob("*")):
        if len(inputs) >= 2500:
            break
        if path.is_file() and path.suffix.lower() in {".sol", ".circom", ".nr"} and path.stat().st_size <= 5_000_000:
            inputs.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    for path in [*circuits_explicit, *consumers_explicit]:
        relative = path.relative_to(root).as_posix()
        if not any(item["path"] == relative for item in inputs):
            inputs.append({"path": relative, "sha256": sha256_file(path)})
    if executable is None:
        reason = "BASELINE_TOOL_UNAVAILABLE"
        findings, patterns = _unknown_patterns(reason, f"{tool} is not installed locally.")
        invocations = []
        version = None
        status = "UNKNOWN"
    else:
        version = _version(tool, executable, root, timeout)
        if tool == "slither":
            targets = consumers_explicit or [root]
            argvs = []
            for target in targets:
                solc_args = ["--base-path", str(root), "--optimize", "--via-ir"]
                node_modules = [root / "node_modules"]
                if target.is_file():
                    for parent in target.parents:
                        if parent == root.parent:
                            break
                        node_modules.append(parent / "node_modules")
                for include in dict.fromkeys(node_modules):
                    if include.is_dir():
                        solc_args.extend(["--include-path", str(include)])
                argv = [
                    executable,
                    str(target),
                    "--compile-force-framework", "solc",
                    "--solc-args", " ".join(solc_args),
                ]
                remaps = [
                    f"@openzeppelin/={(include / '@openzeppelin').relative_to(root)}/"
                    for include in dict.fromkeys(node_modules)
                    if (include / "@openzeppelin").is_dir() and (include / "@openzeppelin").is_relative_to(root)
                ]
                if remaps:
                    argv.extend(["--solc-remaps", " ".join(remaps)])
                argvs.append(argv)
        elif tool in {"circomspect", "picus"}:
            circuits = circuits_explicit or [root / item["path"] for item in inputs if item["path"].endswith(".circom")][:4]
            if tool == "circomspect":
                libraries = [
                    project_root for project_root in (
                        pathlib.Path(__file__).resolve().parents[1] / "node_modules",
                        pathlib.Path(__file__).resolve().parents[1] / "node_modules" / "circomlib",
                    ) if project_root.is_dir()
                ]
                argvs = []
                for circuit in circuits:
                    argv = [executable, "--verbose"]
                    for library in [circuit.parent / "node_modules", *libraries]:
                        if library.is_dir():
                            argv.extend(["--library", str(library)])
                    argvs.append([*argv, str(circuit)])
            else:
                temporary = tempfile.TemporaryDirectory(prefix="bindcheck-zk-picus-")
                temp_root = pathlib.Path(temporary.name)
                circom = pathlib.Path(__file__).resolve().parents[1] / "tools" / "circom-src" / "target" / "release" / "circom"
                picus_targets: list[pathlib.Path] = []
                for index, circuit in enumerate(circuits):
                    output_dir = temp_root / str(index)
                    output_dir.mkdir()
                    compile_argv = [str(circom), str(circuit), "--r1cs", "--sym", "--O0", "-o", str(output_dir)]
                    include_candidates = [
                        pathlib.Path(__file__).resolve().parents[1] / "node_modules",
                        pathlib.Path(__file__).resolve().parents[1] / "node_modules" / "circomlib",
                    ]
                    for parent in circuit.parents:
                        if parent == root.parent:
                            break
                        include_candidates.extend([parent / "node_modules", parent / "node_modules" / "circomlib"])
                    for include in dict.fromkeys(include_candidates):
                        if include.is_dir():
                            compile_argv.extend(["-l", str(include)])
                    compile_record = run(compile_argv, cwd=root, timeout=min(30.0, timeout))
                    preprocessing.append(compile_record)
                    r1cs = output_dir / (circuit.stem + ".r1cs")
                    if compile_record["exit_status"] == 0 and r1cs.is_file():
                        picus_targets.append(r1cs)
                argvs = [[executable, "--json", "-", str(target)] for target in picus_targets]
        else:
            argvs = [[executable, str(root)]]
        remaining = timeout
        invocations = []
        for argv in argvs:
            tool_env = {
                "PATH": str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "circom-src" / "target" / "release") + os.pathsep + os.environ.get("PATH", ""),
            }
            if tool == "picus":
                tool_env["PLTUSERHOME"] = str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "picus-racket")
            invocation = run(
                argv,
                cwd=root,
                timeout=max(0.05, remaining),
                env=tool_env,
            )
            invocations.append(invocation)
            remaining = max(0.0, timeout - (time.monotonic() - started))
            if invocation["timed_out"] or remaining <= 0:
                break
        native_finding_codes = {"slither": {255}, "circomspect": {1}, "picus": {9}}
        native_success_codes = {"picus": {8}}
        circomspect_parse_error = tool == "circomspect" and any(
            re.search(r"\berror\[P\d+\]", item["stdout"] + "\n" + item["stderr"])
            for item in invocations
        )
        if not invocations and preprocessing and any(item["exit_status"] != 0 for item in preprocessing):
            reason = "BASELINE_FAILED"
            message = f"{tool} preprocessing failed; this is not a safe result."
        elif not invocations:
            reason = "BASELINE_NOT_APPLICABLE"
            message = f"{tool} had no supported explicit or discovered input."
        elif any(item["timed_out"] for item in invocations):
            reason = "BASELINE_TIMEOUT"
            message = f"{tool} timed out within the equal run budget."
        elif circomspect_parse_error:
            reason = "BASELINE_FAILED"
            message = "Circomspect reported a parse/include error; findings cannot be treated as a completed analysis."
        elif any(item["exit_status"] not in ({0} | native_finding_codes.get(tool, set()) | native_success_codes.get(tool, set())) for item in invocations):
            reason = "BASELINE_FAILED"
            message = f"{tool} had a non-analysis exit; this is not a safe result."
        elif any(item["exit_status"] in native_finding_codes.get(tool, set()) for item in invocations):
            reason = "BASELINE_NATIVE_FINDINGS"
            message = f"{tool} completed with native circuit-level findings; these do not establish a BindCheck integration-pattern verdict."
        elif tool == "picus" and any(item["exit_status"] == 0 for item in invocations):
            reason = "BASELINE_NATIVE_UNKNOWN"
            message = "Picus completed with a native unknown result; this is not a safe result."
        else:
            reason = "BASELINE_OUTPUT_REQUIRES_ADJUDICATION"
            message = f"{tool} completed; native diagnostics are retained but cannot be promoted to BindCheck pattern verdicts automatically."
        findings, patterns = _unknown_patterns(reason, message)
        status = "completed" if reason in {"BASELINE_NATIVE_FINDINGS", "BASELINE_OUTPUT_REQUIRES_ADJUDICATION"} else "UNKNOWN"
    output = {
        "schema": "bindcheck-zk.result/v1",
        "tool": {"name": tool, "version": version, "adapter": "bindcheck-zk baseline adapter"},
        "run": {
            "started_utc": started_utc, "elapsed_seconds": round(time.monotonic() - started, 6),
            "budget_seconds": timeout, "status": status, "fatal_reason": None,
        },
        "inputs": {"root": str(root), "mode": "baseline", "network_policy": "offline/no RPC", "files": inputs,
                   "explicit_circuits": circuit_paths or [], "explicit_consumers": consumer_paths or []},
        "discovery": {"circuits": sum(item["path"].endswith((".circom", ".nr")) for item in inputs), "verifiers": None, "consumers": None, "triples": 0},
        "triples": [],
        "runtime_bytecode_checks": [],
        "patterns": patterns,
        "coverage": {"files_inventoried": len(inputs), "preprocessing": preprocessing, "invocations": invocations, "skipped": [], "failures": [], "timeouts": []},
        "baseline_findings": findings,
        "limitations": [
            "Baseline diagnostics remain in the baseline's native semantics and require author adjudication.",
            "Tool absence, failure, or timeout is UNKNOWN and never safety evidence.",
        ],
    }
    if temporary is not None:
        temporary.cleanup()
    return output
