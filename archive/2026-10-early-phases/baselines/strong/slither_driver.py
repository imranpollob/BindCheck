#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from slither.slither import Slither

from baselines.strong.slither_detectors import DETECTORS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=pathlib.Path)
    parser.add_argument("--root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    target = args.target.resolve()
    solc_args = f"--base-path {root} --optimize"
    slither = Slither(str(target), solc_args=solc_args)
    for detector in DETECTORS:
        slither.register_detector(detector)
    batches = slither.run_detectors()
    flattened = [item for batch in batches for item in batch]
    json.dump({"target": str(target), "detectors": flattened}, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
