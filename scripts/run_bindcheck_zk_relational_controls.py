#!/usr/bin/env python3
"""Run and record the prospective relational plus inherited control suites."""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import time

from bindcheck_zk.freeze import freeze_manifest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "results" / "raw" / "relational"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    expected_path = ROOT / "tests" / "relational" / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    counts = collections.Counter(
        (case["dimension"], case["expected_verdict"])
        for case in expected["cases"]
    )
    run_id = dt.datetime.now(dt.UTC).strftime("controls-%Y%m%dT%H%M%SZ-") + str(os.getpid())
    output_dir = RAW_ROOT / run_id
    output_dir.mkdir(parents=True)
    command = [
        "python3", "-m", "unittest",
        "tests.test_bindcheck_zk_controls",
        "tests.test_bindcheck_zk_cli",
        "tests.test_bindcheck_zk_relational",
        "-v",
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    circom = pathlib.Path(os.environ.get("BINDCHECK_CIRCOM", ""))
    circom_version = subprocess.run(
        [str(circom), "--version"], cwd=ROOT, text=True, capture_output=True, check=False
    ) if circom.is_file() else None
    git_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    content_hash, freeze_entries = freeze_manifest(ROOT)
    manifest = {
        "schema": "bindcheck-zk.relational-controls/v1",
        "run_id": run_id,
        "git_revision": git_revision,
        "analyzer_content_sha256": content_hash,
        "expected_outcomes": {
            "path": expected_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(expected_path),
            "cases": len(expected["cases"]),
            "counts": {
                dimension: {
                    "VIOLATION": counts[(dimension, "VIOLATION")],
                    "VERIFIED_WITHIN_SCOPE": counts[(dimension, "VERIFIED_WITHIN_SCOPE")],
                }
                for dimension in expected["dimensions"]
            },
        },
        "command": command,
        "exit_status": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "stdout": stdout_path.relative_to(ROOT).as_posix(),
        "stdout_sha256": sha256(stdout_path),
        "stderr": stderr_path.relative_to(ROOT).as_posix(),
        "stderr_sha256": sha256(stderr_path),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "circom_path": str(circom) if circom.is_file() else None,
            "circom_sha256": sha256(circom) if circom.is_file() else None,
            "circom_version": circom_version.stdout.strip() if circom_version else None,
        },
        "freeze_entries": [{"path": path, "sha256": digest} for path, digest in freeze_entries],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": output_dir.relative_to(ROOT).as_posix(),
        "exit_status": completed.returncode,
        "analyzer_content_sha256": content_hash,
        "expected_cases": len(expected["cases"]),
        "manifest_sha256": sha256(manifest_path),
    }, indent=2, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
