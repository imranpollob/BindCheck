#!/usr/bin/env python3
"""Minimal D2 run-manifest and content-seal infrastructure.

This module deliberately provides coordination primitives, not a research
runner.  Experiment-specific dispatch remains in the task runner registered in
``docs/d2/status-and-ownership.md``.  Seal manifests are never members of
their own file set, and mutable convenience indexes are excluded by name.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUN_SCHEMA = "bindcheck.d2.run-manifest/v1"
SEAL_SCHEMA = "bindcheck.d2.content-seal/v1"
VERIFY_SCHEMA = "bindcheck.d2.seal-verification/v1"
SELF_TEST_SCHEMA = "bindcheck.d2.foundation-self-test/v1"
MUTABLE_INDEX_NAMES = frozenset({".DS_Store", "latest.json", "run-index.json"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_new_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing record: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _run(argv: Sequence[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        list(argv), cwd=cwd, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(argv)}: {detail}")
    return completed.stdout.strip()


def _inside(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path is outside the declared root: {path}") from exc
    return resolved


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"expected a regular non-symlink file: {path}")
    resolved = _inside(path, root)
    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(f"expected a regular non-symlink file: {path}")
    return {
        "path": _relative(resolved, root),
        "sha256": sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _git_record(root: Path) -> dict[str, Any]:
    status = _run(["git", "status", "--porcelain=v1"], cwd=root).splitlines()
    return {
        "commit": _run(["git", "rev-parse", "HEAD"], cwd=root),
        "branch": _run(["git", "branch", "--show-current"], cwd=root),
        "dirty": bool(status),
        "status_porcelain": status,
    }


def _tool_record(name: str, executable: str, version: str | None) -> dict[str, Any]:
    candidate = shutil.which(executable) if os.sep not in executable else executable
    if candidate is None:
        raise FileNotFoundError(f"tool executable not found: {executable}")
    path = Path(candidate).resolve()
    if not path.is_file():
        raise ValueError(f"tool is not a regular file: {path}")
    return {
        "name": name,
        "executable": str(path),
        "sha256": sha256(path),
        "version": version,
    }


def prepare_run_manifest(
    *,
    root: Path,
    output: Path,
    run_id: str,
    experiment: str,
    inputs: Sequence[Path] = (),
    configurations: Sequence[Path] = (),
    tool_specs: Sequence[tuple[str, str, str | None]] = (),
    seeds: Sequence[str] = (),
    wall_seconds: int | None = None,
    memory_mib: int | None = None,
    max_calls: int | None = None,
) -> dict[str, Any]:
    """Create a fail-closed per-run preparation manifest."""
    root = root.resolve()
    python_tool = _tool_record("python", sys.executable, platform.python_version())
    git_path = shutil.which("git")
    if git_path is None:
        raise FileNotFoundError("git executable not found")
    git_tool = _tool_record(
        "git", git_path, _run([git_path, "--version"], cwd=root)
    )
    extra_tools = [_tool_record(*spec) for spec in tool_specs]
    names = [tool["name"] for tool in [python_tool, git_tool, *extra_tools]]
    if len(names) != len(set(names)):
        raise ValueError(f"duplicate tool name in manifest: {names}")
    manifest = {
        "schema": RUN_SCHEMA,
        "created_at_utc": utc_now(),
        "run_id": run_id,
        "experiment": experiment,
        "repository": _git_record(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
        },
        "tools": [python_tool, git_tool, *extra_tools],
        "configurations": [_file_record(path, root) for path in configurations],
        "inputs": [_file_record(path, root) for path in inputs],
        "seeds": list(seeds),
        "resource_budget": {
            "wall_seconds": wall_seconds,
            "memory_mib": memory_mib,
            "max_calls": max_calls,
            "unspecified_values_are_not_implicit_authorization": True,
        },
    }
    _write_new_json(output, manifest)
    return manifest


def _collect_seal_files(
    entries: Iterable[Path], *, root: Path, manifest_path: Path,
    excludes: Iterable[Path] = (),
) -> tuple[list[Path], list[str]]:
    root = root.resolve()
    manifest_resolved = manifest_path.resolve()
    excluded = {_inside(path, root) for path in excludes}
    selected: set[Path] = set()
    skipped: set[str] = set()
    for entry in entries:
        if entry.is_symlink():
            raise ValueError(f"seal member is not a regular non-symlink file: {entry}")
        resolved = _inside(entry, root)
        candidates = [resolved]
        if resolved.is_dir():
            candidates = sorted(path for path in resolved.rglob("*") if path.is_file())
        for candidate in candidates:
            if candidate.is_symlink():
                raise ValueError(f"seal member is not a regular non-symlink file: {candidate}")
            candidate = candidate.resolve()
            if candidate == manifest_resolved:
                skipped.add(_relative(candidate, root))
                continue
            if candidate in excluded or candidate.name in MUTABLE_INDEX_NAMES:
                skipped.add(_relative(candidate, root))
                continue
            if any(part in {".git", "__pycache__"} for part in candidate.parts):
                skipped.add(_relative(candidate, root))
                continue
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError(f"seal member is not a regular non-symlink file: {candidate}")
            selected.add(candidate)
    if not selected:
        raise ValueError("seal has no immutable file members")
    return sorted(selected, key=lambda path: _relative(path, root)), sorted(skipped)


def create_seal(
    *, root: Path, output: Path, version: str, entries: Sequence[Path],
    excludes: Sequence[Path] = (),
) -> dict[str, Any]:
    """Create a versioned seal without overwriting or self-hashing."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing seal: {output}")
    files, skipped = _collect_seal_files(
        entries, root=root, manifest_path=output, excludes=excludes,
    )
    seal = {
        "schema": SEAL_SCHEMA,
        "version": version,
        "created_at_utc": utc_now(),
        "repository_commit": _git_record(root)["commit"],
        "files": [_file_record(path, root) for path in files],
        "excluded": {
            "paths": skipped,
            "mutable_index_names": sorted(MUTABLE_INDEX_NAMES),
            "manifest_self_excluded": True,
        },
        "limits": [
            "This local manifest detects byte changes relative to this retained copy; it is not access control.",
            "The evaluator or custodian must retain the authoritative manifest outside the developer workspace.",
        ],
    }
    _write_new_json(output, seal)
    return seal


def verify_seal(*, root: Path, manifest: Path) -> dict[str, Any]:
    """Verify every sealed member and report all mismatches."""
    root = root.resolve()
    data = json.loads(manifest.read_text())
    if data.get("schema") != SEAL_SCHEMA:
        raise ValueError(f"unsupported seal schema: {data.get('schema')!r}")
    mismatches: list[dict[str, Any]] = []
    for expected in data.get("files", []):
        path = _inside(root / expected["path"], root)
        if not path.is_file() or path.is_symlink():
            mismatches.append({
                "path": expected["path"], "reason": "MISSING_OR_NOT_REGULAR",
                "expected_sha256": expected["sha256"],
            })
            continue
        observed_hash = sha256(path)
        observed_size = path.stat().st_size
        if (observed_hash, observed_size) != (
            expected["sha256"], expected["size_bytes"]
        ):
            mismatches.append({
                "path": expected["path"], "reason": "CONTENT_MISMATCH",
                "expected_sha256": expected["sha256"],
                "observed_sha256": observed_hash,
                "expected_size_bytes": expected["size_bytes"],
                "observed_size_bytes": observed_size,
            })
    return {
        "schema": VERIFY_SCHEMA,
        "manifest": str(manifest.resolve()),
        "manifest_sha256": sha256(manifest),
        "status": "PASS" if not mismatches else "FAIL",
        "checked_files": len(data.get("files", [])),
        "mismatches": mismatches,
    }


def foundation_self_test(*, root: Path, output_dir: Path) -> dict[str, Any]:
    """Exercise prepare/seal/verify/tamper detection on disposable files."""
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse self-test directory: {output_dir}")
    output_dir.mkdir(parents=True)
    payload = output_dir / "payload.txt"
    configuration = output_dir / "configuration.json"
    payload.write_text("bindcheck d2 disposable payload\n")
    configuration.write_text('{"mode":"foundation-self-test"}\n')
    run_manifest_path = output_dir / "run-manifest.json"
    prepare_run_manifest(
        root=root,
        output=run_manifest_path,
        run_id="D2-00-foundation-self-test",
        experiment="foundation-round-trip",
        inputs=[payload],
        configurations=[configuration],
        seeds=["none"],
        wall_seconds=60,
        memory_mib=256,
        max_calls=0,
    )
    seal_path = output_dir / "seal-v1.json"
    create_seal(
        root=root,
        output=seal_path,
        version="D2-00-disposable-v1",
        entries=[payload, configuration, run_manifest_path],
    )
    before = verify_seal(root=root, manifest=seal_path)
    payload.write_text("bindcheck d2 deliberately tampered disposable payload\n")
    after = verify_seal(root=root, manifest=seal_path)
    summary = {
        "schema": SELF_TEST_SCHEMA,
        "created_at_utc": utc_now(),
        "status": "PASS" if before["status"] == "PASS" and after["status"] == "FAIL" else "FAIL",
        "pre_tamper_verification": before,
        "post_tamper_verification": after,
        "tampered_file": _relative(payload, root),
        "note": "All files are disposable D2-00 infrastructure controls; no research input was modified.",
    }
    _write_new_json(output_dir / "self-test-summary.json", summary)
    return summary


def _parse_tool(value: str, versions: dict[str, str]) -> tuple[str, str, str | None]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--tool requires NAME=EXECUTABLE")
    name, executable = value.split("=", 1)
    if not name or not executable:
        raise argparse.ArgumentTypeError("--tool requires nonempty NAME=EXECUTABLE")
    return name, executable, versions.get(name)


def _name_values(values: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--tool-version requires NAME=VERSION")
        name, version = value.split("=", 1)
        if not name or not version or name in result:
            raise ValueError(f"invalid or duplicate tool version: {value}")
        result[name] = version
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-run", help="write a per-run preparation manifest")
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--experiment", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--input", type=Path, action="append", default=[])
    prepare.add_argument("--configuration", type=Path, action="append", default=[])
    prepare.add_argument("--tool", action="append", default=[])
    prepare.add_argument("--tool-version", action="append", default=[])
    prepare.add_argument("--seed", action="append", default=[])
    prepare.add_argument("--wall-seconds", type=int)
    prepare.add_argument("--memory-mib", type=int)
    prepare.add_argument("--max-calls", type=int)

    seal = sub.add_parser("seal", help="create a versioned content-hash seal")
    seal.add_argument("--version", required=True)
    seal.add_argument("--output", type=Path, required=True)
    seal.add_argument("--exclude", type=Path, action="append", default=[])
    seal.add_argument("paths", type=Path, nargs="+")

    verify = sub.add_parser("verify", help="verify a content-hash seal")
    verify.add_argument("manifest", type=Path)

    self_test = sub.add_parser("self-test", help="run a disposable integrity round trip")
    self_test.add_argument("--output-dir", type=Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare-run":
            versions = _name_values(args.tool_version)
            tools = [_parse_tool(value, versions) for value in args.tool]
            value = prepare_run_manifest(
                root=ROOT,
                output=args.output,
                run_id=args.run_id,
                experiment=args.experiment,
                inputs=args.input,
                configurations=args.configuration,
                tool_specs=tools,
                seeds=args.seed,
                wall_seconds=args.wall_seconds,
                memory_mib=args.memory_mib,
                max_calls=args.max_calls,
            )
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0
        if args.command == "seal":
            value = create_seal(
                root=ROOT, output=args.output, version=args.version,
                entries=args.paths, excludes=args.exclude,
            )
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            value = verify_seal(root=ROOT, manifest=args.manifest)
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0 if value["status"] == "PASS" else 2
        value = foundation_self_test(root=ROOT, output_dir=args.output_dir)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value["status"] == "PASS" else 2
    except Exception as exc:
        print(f"d2-foundation: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
