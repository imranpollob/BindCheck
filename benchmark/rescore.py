#!/usr/bin/env python3
"""Recompute the case matrix and metrics after a reviewer changes case labels.

One command: /opt/homebrew/bin/python3 benchmark/rescore.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
PYTHON=pathlib.Path("/opt/homebrew/bin/python3")
RAW=ROOT/"results/raw/bench"
OUT=ROOT/"reports/bench"
OBS=RAW/"e1-observations-20261109.jsonl"
EXPANDED=RAW/"e1-observations-expanded-20261109.jsonl"
F2_OBS=RAW/"e1-freeze2-observations-20261109.jsonl"
PUBLIC_OBS=RAW/"e1-public-observations-20261109.jsonl"
F2_RUNS=RAW/"e1-freeze2-20261109/runs.json"
BUILD=RAW/"e1-build-20261109-verified/build.json"
ABC=RAW/"e1-synthetic-abc-20261109"
BC=RAW/"e1-synthetic-bindcheck-freeze1-20261109"
LOCAL=RAW/"e1-local-20261109"
ZKF=RAW/"e1-zkfuzz-20261109/runs.json"
ZKF_RETRY=RAW/"e1-zkfuzz-h-retry-20261109/runs.json"

def main():
    for argv in (
        [PYTHON,ROOT/"benchmark/collect.py","--synthetic-abc",ABC,"--synthetic-bindcheck",BC,
         "--local",LOCAL,"--build",BUILD,"--zkfuzz",ZKF,"--zkfuzz-retry",ZKF_RETRY,"--output",OBS],
    ):
        subprocess.run([str(x) for x in argv],cwd=ROOT,check=True)
    parts=[OBS.read_text()]
    if F2_RUNS.is_file():
        subprocess.run([str(x) for x in [PYTHON,ROOT/"benchmark/collect_freeze2.py",
                        "--runs",F2_RUNS,"--build",BUILD,"--output",F2_OBS]],cwd=ROOT,check=True)
        parts.append(F2_OBS.read_text())
    if (RAW/"e1-public-20261109/runs-email.json").is_file() and \
       (RAW/"e1-public-20261109/runs-self.json").is_file():
        subprocess.run([str(x) for x in [PYTHON,ROOT/"benchmark/collect_public.py",
                        "--output",PUBLIC_OBS]],cwd=ROOT,check=True)
        parts.append(PUBLIC_OBS.read_text())
    EXPANDED.write_text("".join(parts))
    for argv in (
        [PYTHON,ROOT/"benchmark/score.py","--observations",EXPANDED,"--output",OUT],
        [PYTHON,ROOT/"benchmark/metrics.py","--matrix",OUT/"matrix.csv","--build",BUILD,
         "--observations",EXPANDED,"--synthetic-abc",ABC,"--local",LOCAL,"--zkfuzz",ZKF,
         "--zkfuzz-retry",ZKF_RETRY,"--output",OUT/"metrics.json"],
        [PYTHON,ROOT/"benchmark/summarize_freezes.py"],
        [PYTHON,ROOT/"benchmark/summarize_public.py"],
    ):
        subprocess.run([str(x) for x in argv],cwd=ROOT,check=True)

if __name__=="__main__":main()
