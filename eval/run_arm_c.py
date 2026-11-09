#!/usr/bin/env python3
"""Run the frozen strong-composition arm and its required inputs on one checkout."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from baselines.strong.arm_a import analyze_arm_a
from baselines.strong.arm_b import analyze_arm_b
from baselines.strong.arm_c import analyze_arm_c
from baselines.strong.common import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    output = args.output.resolve()
    if not checkout.is_dir():
        parser.error("checkout does not exist")
    if os.environ.get("BINDCHECK_CIRCOM") and not os.environ.get("BINDCHECK_STRONG_CIRCOM"):
        os.environ["BINDCHECK_STRONG_CIRCOM"] = os.environ["BINDCHECK_CIRCOM"]
    output.mkdir(parents=True, exist_ok=True)
    a = analyze_arm_a(checkout, output / "A", 120.0)
    write_json(output / "A.json", a)
    b = analyze_arm_b(checkout, output / "B", 180.0)
    write_json(output / "B.json", b)
    c = analyze_arm_c(checkout, output / "C", a, b)
    write_json(output / "C.json", c)
    print(json.dumps(c, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
