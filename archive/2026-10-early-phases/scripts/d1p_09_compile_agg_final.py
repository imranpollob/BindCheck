#!/usr/bin/env python3
"""One-shot, local-only reconstruction compile for the N=8 agg_final artifact.

This script exports the pinned Payy tree into an isolated ignored directory,
applies the reviewed 1000->8 and 1005->13 agg_final source scaling, and makes
exactly one bounded ``nargo compile`` call.  It does not prove, generate keys,
download dependencies, or modify the pinned checkout.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tarfile
import time


PINNED_REVISION = "dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
PINNED_COMPILER_VERSION = (
    "nargo 1.0.0-beta.14; "
    "noirc 1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051"
)
PINNED_COMPILER_SHA256 = (
    "a0528f1c7a070f51addcefc707f889f2f9cbd85b17261e43f4b8dcf3d1d81eb8"
)
PINNED_SOURCE_SHA256 = (
    "5e6493eb16e14f4aa47f206b3e39f5168e7647be8bb1a66c624f019ea8a5b624"
)
TIMEOUT_SECONDS = 600


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_readonly(command: list[str], cwd: Path | None = None) -> bytes:
    return subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout


def safe_extract_tar(data: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if root not in (target, *target.parents):
                raise ValueError(f"unsafe archive member: {member.name}")
        archive.extractall(destination, filter="data")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to reuse one-shot output: {output}")
    output.mkdir(parents=True)
    record: dict[str, object] = {
        "task": "D1P-09",
        "operation": "single authorized isolated N=8 agg_final reconstruction compile",
        "timeout_seconds": TIMEOUT_SECONDS,
        "downloads_authorized": False,
        "proof_generation": False,
        "key_generation": False,
        "source_revision": PINNED_REVISION,
        "compiler_version": PINNED_COMPILER_VERSION,
        "status": "PREPARING",
        "started_unix_seconds": time.time(),
    }
    record_path = output / "compile-record.json"

    try:
        actual_revision = run_readonly(
            ["git", "rev-parse", "HEAD"], args.source_repo
        ).decode().strip()
        if actual_revision != PINNED_REVISION:
            raise ValueError(f"source revision mismatch: {actual_revision}")
        if sha256(args.compiler) != PINNED_COMPILER_SHA256:
            raise ValueError("compiler hash mismatch")

        archive = run_readonly(
            ["git", "archive", "--format=tar", PINNED_REVISION, "noir"],
            args.source_repo,
        )
        source_root = output / "source"
        source_root.mkdir()
        safe_extract_tar(archive, source_root)
        source = source_root / "noir/agg_final/src/main.nr"
        before = source.read_bytes()
        if sha256_bytes(before) != PINNED_SOURCE_SHA256:
            raise ValueError("pinned agg_final source hash mismatch")

        before_text = before.decode("utf-8")
        after_text, count_1000 = re.subn(r"\b1000\b", "8", before_text)
        after_text, count_1005 = re.subn(r"\b1005\b", "13", after_text)
        if (count_1000, count_1005) != (2, 2):
            raise ValueError(
                f"unexpected scaling replacement counts: {(count_1000, count_1005)}"
            )
        source.write_text(after_text)
        (output / "source-transformation.diff").write_text("".join(
            difflib.unified_diff(
                before_text.splitlines(keepends=True),
                after_text.splitlines(keepends=True),
                fromfile=f"{PINNED_REVISION}:noir/agg_final/src/main.nr",
                tofile="isolated-N8:noir/agg_final/src/main.nr",
            )
        ))

        command = [str(args.compiler.resolve()), "compile", "--package", "agg_final",
                   "--print-acir"]
        record.update({
            "source_repo": str(args.source_repo.resolve()),
            "source_checkout_dirty_files_ignored_by_git_archive": True,
            "source_path": "source/noir/agg_final/src/main.nr",
            "source_sha256_before": sha256_bytes(before),
            "source_sha256_after": sha256(source),
            "transformation": {
                "path": "source/noir/agg_final/src/main.nr",
                "word_boundary_replacements": {"1000_to_8": count_1000,
                                                  "1005_to_13": count_1005},
                "diff_path": "source-transformation.diff",
            },
            "compiler_path": str(args.compiler.resolve()),
            "compiler_sha256": sha256(args.compiler),
            "command": command,
            "cwd": str((source_root / "noir").resolve()),
            "status": "RUNNING",
        })
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=source_root / "noir",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=os.environ.copy(),
        )
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate(timeout=5)
        elapsed = time.monotonic() - started
        (output / "compile.stdout").write_bytes(stdout)
        (output / "compile.stderr").write_bytes(stderr)
        artifact = source_root / "noir/target/agg_final.json"
        record.update({
            "elapsed_seconds": elapsed,
            "timed_out": timed_out,
            "exit_status": process.returncode,
            "stdout_path": "compile.stdout",
            "stdout_sha256": sha256(output / "compile.stdout"),
            "stderr_path": "compile.stderr",
            "stderr_sha256": sha256(output / "compile.stderr"),
            "artifact_path": (
                "source/noir/target/agg_final.json" if artifact.exists() else None
            ),
            "artifact_sha256": sha256(artifact) if artifact.exists() else None,
            "status": "PASS" if not timed_out and process.returncode == 0 and artifact.exists()
                      else "BLOCKED",
            "limitations": [
                "local reconstruction; not an artifact recovered from deployment",
                "does not establish deployed verification-key correspondence",
                "does not establish proof generation or verifier acceptance",
            ],
        })
        return 0 if record["status"] == "PASS" else 1
    except Exception as error:  # ensure the one-shot failure is preserved
        record.update({"status": "BLOCKED", "setup_error": repr(error)})
        return 1
    finally:
        record["finished_unix_seconds"] = time.time()
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
