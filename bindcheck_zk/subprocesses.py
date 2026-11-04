from __future__ import annotations

import os
import pathlib
import subprocess
import time
from typing import Any


NETWORK_ENV_KEYS = {
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy",
}


def offline_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in NETWORK_ENV_KEYS}
    env.update({
        "NO_PROXY": "*",
        "no_proxy": "*",
        "HARDHAT_DISABLE_DOWNLOADS": "true",
        "FOUNDRY_OFFLINE": "true",
        "CARGO_NET_OFFLINE": "true",
        "NPM_CONFIG_OFFLINE": "true",
    })
    if extra:
        env.update(extra)
    return env


def run(
    argv: list[str],
    *,
    cwd: pathlib.Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=offline_environment(env),
            text=True,
            capture_output=True,
            timeout=max(0.05, timeout),
            check=False,
        )
        return {
            "argv": argv,
            "cwd": str(cwd),
            "exit_status": completed.returncode,
            "timed_out": False,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd": str(cwd),
            "exit_status": None,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
        }
