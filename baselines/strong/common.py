from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[2]
VERDICTS = {"VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN"}
ARMS = {"A", "B", "C"}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative_or_absolute(path: pathlib.Path, root: pathlib.Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def command_version(argv: list[str], *, cwd: pathlib.Path | None = None) -> dict[str, Any]:
    return run_command(argv, cwd=cwd, timeout=20.0)


def run_command(
    argv: list[str],
    *,
    cwd: pathlib.Path | None = None,
    timeout: float = 120.0,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a subprocess without truncating either native output stream."""
    started_utc = utc_now()
    started = time.monotonic()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=merged_env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "cwd": str(cwd.resolve()) if cwd else None,
            "started_utc": started_utc,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "exit_status": completed.returncode,
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "argv": argv,
            "cwd": str(cwd.resolve()) if cwd else None,
            "started_utc": started_utc,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "exit_status": None,
            "timed_out": True,
            "stdout": stdout,
            "stderr": stderr,
        }


def retain_native(record: dict[str, Any], directory: pathlib.Path, stem: str) -> dict[str, Any]:
    """Persist full stdout/stderr and replace them with immutable references."""
    directory.mkdir(parents=True, exist_ok=True)
    retained = dict(record)
    for stream in ("stdout", "stderr"):
        data = retained.pop(stream, "")
        path = directory / f"{stem}.{stream}"
        path.write_text(data, encoding="utf-8")
        retained[f"{stream}_path"] = relative_or_absolute(path)
        retained[f"{stream}_sha256"] = sha256_file(path)
        retained[f"{stream}_bytes"] = path.stat().st_size
    return retained


def inventory(root: pathlib.Path, suffixes: Iterable[str], cap: int = 2500) -> tuple[list[dict[str, Any]], bool]:
    suffix_set = {item.lower() for item in suffixes}
    excluded_parts = {
        ".git", "node_modules", "vendor", "target", "build", "dist", "out",
        "artifacts", "cache", ".next", "coverage", "venv", ".venv",
    }
    output: list[dict[str, Any]] = []
    capped = False
    for path in sorted(root.rglob("*")):
        if any(part in excluded_parts for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in suffix_set:
            continue
        if path.stat().st_size > 5_000_000:
            continue
        if len(output) >= cap:
            capped = True
            break
        output.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        })
    return output, capped


def load_policy(root: pathlib.Path) -> dict[str, Any] | None:
    path = root / "policy.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finding(
    code: str,
    message: str,
    *,
    path: str | None = None,
    line: int | None = None,
    facts: dict[str, Any] | None = None,
    source: str = "heuristic",
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "location": {"path": path, "line": line} if path else None,
        "facts": facts or {},
        "source": source,
        "evidence_grade": "E1",
    }


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in findings:
        key = canonical_json({
            "code": item.get("code"),
            "location": item.get("location"),
            "facts": item.get("facts"),
        })
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def envelope(
    arm: str,
    root: pathlib.Path,
    *,
    started_utc: str,
    elapsed_seconds: float,
    run_status: str,
    findings: list[dict[str, Any]],
    verdict: str,
    coverage: dict[str, Any],
    native: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    fatal_reason: str | None = None,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unsupported arm {arm}")
    if verdict not in VERDICTS:
        raise ValueError(f"unsupported verdict {verdict}")
    files, capped = inventory(root, {".sol", ".circom", ".json", ".toml"})
    return {
        "schema": "bindcheck-redteam.strong-result/v1",
        "tool": {"name": "bindcheck-strong", "version": "0.1.0", "arm": arm},
        "run": {
            "started_utc": started_utc,
            "elapsed_seconds": round(elapsed_seconds, 6),
            "status": run_status,
            "fatal_reason": fatal_reason,
        },
        "inputs": {
            "root": str(root.resolve()),
            "network_policy": "offline during analysis; local synthetic assets or pinned public DEV source",
            "files": files,
            "inventory_capped": capped,
        },
        "result": {
            "verdict": verdict,
            "evidence_grade": "E1" if findings or verdict == "VERIFIED_WITHIN_SCOPE" else "E0",
            "findings": dedupe_findings(findings),
        },
        "coverage": coverage,
        "native": native or {},
        "limitations": limitations or [],
    }


def executable_from_candidates(*candidates: str | pathlib.Path) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, pathlib.Path):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def temporary_directory(prefix: str) -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix=prefix)
