#!/usr/bin/env python3
"""Record bounded local validation and freeze without altering sealed evidence."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "results/raw/coverage/verification.json"
CIRCOM = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv: list[str], *, env: dict[str, str] | None = None) -> dict:
    started = time.monotonic()
    completed = subprocess.run(argv, cwd=ROOT, env={**os.environ, **(env or {})},
                               text=True, capture_output=True, timeout=300, check=False)
    return {"argv": argv, "cwd": str(ROOT), "exit_status": completed.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "stdout": completed.stdout, "stderr": completed.stderr}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tests = [sys.executable, "-m", "unittest", "tests.test_bindcheck_zk_cli",
             "tests.test_bindcheck_zk_controls", "tests.soundness.test_verdict_soundness",
             "tests.soundness.test_followup", "tests.coverage.test_rules", "-q"]
    results = {
        "started_utc": dt.datetime.now(dt.UTC).isoformat(),
        "source_revision_before_commit": command(["git", "rev-parse", "HEAD"]),
        "python": command([sys.executable, "--version"]),
        "git": command(["git", "--version"]),
        "circom": command([str(CIRCOM), "--version"]),
        "circom_sha256": sha256(CIRCOM),
        "tests": command(tests, env={"BINDCHECK_CIRCOM": str(CIRCOM)}),
        "compileall": command([sys.executable, "-m", "compileall", "-q", "bindcheck_zk"]),
        "diff_check": command(["git", "diff", "--check"]),
        "freeze": command(["./freeze.sh"]),
    }
    OUT.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({name: value["exit_status"] for name, value in results.items()
                      if isinstance(value, dict) and "exit_status" in value}, sort_keys=True))
    return 0 if all(value["exit_status"] == 0 for value in results.values()
                    if isinstance(value, dict) and "exit_status" in value) else 1


if __name__ == "__main__":
    raise SystemExit(main())
