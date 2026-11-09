#!/usr/bin/env python3
"""Capture exact final commands, versions, statuses, and output."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parents[2]
CIRCOM = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom")
SNARKJS = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/node_modules/snarkjs/cli.js")


def run(argv: list[str]) -> dict[str, object]:
    start = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, env={**os.environ, "BINDCHECK_CIRCOM": str(CIRCOM)}, text=True, capture_output=True)
    return {"argv": argv, "cwd": str(ROOT), "exit_status": p.returncode,
            "elapsed_seconds": time.monotonic() - start, "stdout": p.stdout, "stderr": p.stderr}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    commands = {
        "tests": run([sys.executable, "-m", "unittest", "tests.soundness.test_followup", "tests.soundness.test_verdict_soundness", "tests.test_bindcheck_zk_controls", "tests.test_bindcheck_zk_cli", "-v"]),
        "compileall": run([sys.executable, "-m", "compileall", "-q", "bindcheck_zk", "tests/soundness", "reports/soundness/render_followup.py", "reports/soundness/verify_followup.py"]),
        "diff_check": run(["git", "diff", "--check"]),
        "cached_diff_check": run(["git", "diff", "--cached", "--check"]),
        "freeze": run(["./freeze.sh"]),
    }
    payload = {
        "schema": "bindcheck-zk.soundness-followup-verification/v1",
        "revision": run(["git", "rev-parse", "HEAD"])["stdout"].strip(),
        "environment": {
            "python": run([sys.executable, "--version"]),
            "git": run(["git", "--version"]),
            "circom": run([str(CIRCOM), "--version"]),
            "circom_sha256": sha(CIRCOM),
            "snarkjs": run(["node", str(SNARKJS), "--version"]),
            "snarkjs_sha256": sha(SNARKJS),
        },
        "commands": commands,
    }
    out = ROOT / "results/raw/soundness/verification-2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return int(any(command["exit_status"] != 0 for command in commands.values()))


if __name__ == "__main__":
    raise SystemExit(main())
