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
        [PYTHON,ROOT/"benchmark/score.py","--observations",OBS,"--output",OUT],
        [PYTHON,ROOT/"benchmark/metrics.py","--matrix",OUT/"matrix.csv","--build",BUILD,
         "--observations",OBS,"--synthetic-abc",ABC,"--local",LOCAL,"--zkfuzz",ZKF,
         "--zkfuzz-retry",ZKF_RETRY,
         "--output",OUT/"metrics.json"],
    ):
        subprocess.run([str(x) for x in argv],cwd=ROOT,check=True)

if __name__=="__main__":main()
