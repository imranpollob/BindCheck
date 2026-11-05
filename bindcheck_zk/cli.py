from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from .analyzer import analyze
from .baselines import run_baseline


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="bindcheck-zk")
    subparsers = result.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="analyze a local repository")
    analyze_parser.add_argument("repo_dir", type=pathlib.Path)
    analyze_parser.add_argument("--circuit", action="append", default=[])
    analyze_parser.add_argument("--consumer", action="append", default=[])
    bundle_parser = subparsers.add_parser("analyze-bundle", help="analyze an offline verified-source bundle")
    bundle_parser.add_argument("directory", type=pathlib.Path)
    baseline_parser = subparsers.add_parser("baseline", help="run an installed baseline through the common envelope")
    baseline_parser.add_argument("tool", choices=("slither", "circomspect", "zkap", "picus"))
    baseline_parser.add_argument("repo_dir", type=pathlib.Path)
    baseline_parser.add_argument("--timeout", type=float, default=120.0)
    baseline_parser.add_argument("--circuit", action="append", default=[])
    baseline_parser.add_argument("--consumer", action="append", default=[])
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "analyze":
            output = analyze(
                args.repo_dir,
                explicit_circuits=args.circuit,
                explicit_consumers=args.consumer,
                bundle=False,
            )
        elif args.command == "analyze-bundle":
            output = analyze(args.directory, bundle=True)
        else:
            output = run_baseline(
                args.tool,
                args.repo_dir,
                args.timeout,
                circuit_paths=args.circuit,
                consumer_paths=args.consumer,
            )
    except Exception as exc:
        output: dict[str, Any] = {
            "schema": "bindcheck-zk.result/v1",
            "tool": {"name": "bindcheck-zk"},
            "run": {"status": "UNKNOWN", "fatal_reason": "CLI_INPUT_ERROR"},
            "inputs": {}, "discovery": {}, "triples": [], "runtime_bytecode_checks": [],
            "patterns": {
                pattern: {"verdict": "UNKNOWN", "evidence_grade": "E0", "results": 1, "reasons": ["CLI_INPUT_ERROR"]}
                for pattern in ("P1", "P2", "P3", "P4", "P5")
            },
            "coverage": {"failures": [{"type": type(exc).__name__, "detail": str(exc)}]},
            "limitations": ["The requested input could not be analyzed; no safe result is implied."],
        }
    json.dump(output, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if output.get("run", {}).get("fatal_reason") is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
