#!/usr/bin/env python3
"""Run one D1P-33 command and preserve a machine-readable execution record."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")

    environment = os.environ.copy()
    overrides: dict[str, str] = {}
    for item in args.env:
        key, separator, value = item.partition("=")
        if not separator or not key:
            parser.error(f"invalid --env value: {item!r}")
        overrides[key] = value
        environment[key] = value

    started_at = utc_now()
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=args.cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    record = {
        "schema": "bindcheck.d1p33.command/v1",
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "cwd": str(args.cwd.resolve()),
        "argv": command,
        "environment_overrides": overrides,
        "returncode": completed.returncode,
        "runtime_seconds": round(time.monotonic() - started, 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=__import__("sys").stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
