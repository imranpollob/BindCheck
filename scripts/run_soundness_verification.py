#!/usr/bin/env python3
"""Run and retain the bounded soundness verification commands."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import platform
import subprocess
import tarfile
import tempfile
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv: list[str], *, cwd: pathlib.Path = ROOT, env: dict[str, str] | None = None) -> dict[str, object]:
    started = time.monotonic()
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "exit_status": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--circom", required=True, type=pathlib.Path)
    parser.add_argument("--snarkjs", required=True, type=pathlib.Path)
    parser.add_argument("--prefixed-tests-commit", default="1dc60f977bd6c16a18d849d127353e1955a57810")
    args = parser.parse_args()
    circom_env = {"BINDCHECK_CIRCOM": str(args.circom)}

    pre_archive = subprocess.run(
        ["git", "archive", "--format=tar", args.prefixed_tests_commit],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="bindcheck-zk-prefixed-") as temp_name:
        temp = pathlib.Path(temp_name)
        with tarfile.open(fileobj=io.BytesIO(pre_archive), mode="r:") as archive:
            archive.extractall(temp, filter="data")
        pre_fix = run(
            [platform.python_implementation() == "CPython" and os.sys.executable or "python3", "-m", "unittest", "tests.soundness.test_verdict_soundness", "-v"],
            cwd=temp,
        )
    pre_fix_text = str(pre_fix["stdout"]) + str(pre_fix["stderr"])

    soundness = run([os.sys.executable, "-m", "unittest", "tests.soundness.test_verdict_soundness", "-v"])
    controls = run(
        [os.sys.executable, "-m", "unittest", "tests.test_bindcheck_zk_controls", "tests.test_bindcheck_zk_cli", "-v"],
        env=circom_env,
    )
    compileall = run([
        os.sys.executable, "-m", "compileall", "-q", "bindcheck_zk", "tests/soundness",
        "tests/test_bindcheck_zk_controls.py", "scripts/render_soundness_summary.py",
        "scripts/run_soundness_verification.py",
    ])
    diff_check = run(["git", "diff", "--check"])
    freeze = run(["./freeze.sh"])
    circom_version = run([str(args.circom), "--version"])
    snarkjs_version = run(["node", str(args.snarkjs), "--version"])
    git_version = run(["git", "--version"])

    controls_expected = json.loads((ROOT / "tests/controls/expected.json").read_text(encoding="utf-8"))
    soundness_expected = json.loads((ROOT / "tests/soundness/expected.json").read_text(encoding="utf-8"))
    payload = {
        "schema": "bindcheck-zk.soundness-verification/v1",
        "revision": run(["git", "rev-parse", "HEAD"])["stdout"].strip(),
        "lane_baseline_revision": run(
            ["git", "rev-parse", f"{args.prefixed_tests_commit}^"]
        )["stdout"].strip(),
        "environment": {
            "python": platform.python_version(),
            "python_executable": os.sys.executable,
            "git": git_version,
            "circom": circom_version,
            "circom_sha256": sha256(args.circom),
            "snarkjs": snarkjs_version,
            "snarkjs_sha256": sha256(args.snarkjs),
        },
        "declared_cases": {
            "legacy_track_b": len(controls_expected["legacy_track_b"]),
            "analyzer_controls": len(controls_expected["analyzer_controls"]),
            "existing_controls_total": len(controls_expected["legacy_track_b"]) + len(controls_expected["analyzer_controls"]),
            "soundness_cases": len(soundness_expected["cases"]),
        },
        "pre_fix": {
            "expectation_commit": args.prefixed_tests_commit,
            "observed_case_mismatches": pre_fix_text.count('"id": "SND-'),
            "command": pre_fix,
        },
        "commands": {
            "soundness": soundness,
            "existing_controls_and_cli": controls,
            "compileall": compileall,
            "git_diff_check": diff_check,
            "freeze": freeze,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed = [
        name for name, record in payload["commands"].items()
        if record["exit_status"] != 0
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
