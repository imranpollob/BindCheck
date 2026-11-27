from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .arm_a import analyze_arm_a
from .arm_b import analyze_arm_b
from .arm_c import analyze_arm_c
from .common import write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bindcheck-strong")
    parser.add_argument("repo", type=pathlib.Path)
    parser.add_argument("--arm", choices=("A", "B", "C", "all"), default="all")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--a-budget", type=float, default=120.0)
    parser.add_argument("--b-budget", type=float, default=180.0)
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    if not root.is_dir():
        parser.error(f"repository directory does not exist: {root}")
    args.output.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    if args.arm in {"A", "C", "all"}:
        results["A"] = analyze_arm_a(root, args.output / "A", args.a_budget)
        write_json(args.output / "A.json", results["A"])
    if args.arm in {"B", "C", "all"}:
        results["B"] = analyze_arm_b(root, args.output / "B", args.b_budget)
        write_json(args.output / "B.json", results["B"])
    if args.arm in {"C", "all"}:
        results["C"] = analyze_arm_c(root, args.output / "C", results["A"], results["B"])
        write_json(args.output / "C.json", results["C"])
    selected = results if args.arm == "all" else {args.arm: results[args.arm]}
    json.dump(selected, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
