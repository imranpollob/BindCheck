#!/usr/bin/env python3
"""Recreate the local pre-output freeze on a fresh checkout; never overwrite it.

Added after launching the original run to replace its inline freeze command.
--check only verifies an existing freeze's source checksums.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT = Path("results/raw/T22/33_v3_freeze")
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--check", action="store_true")
args = ap.parse_args()


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


if args.check:
    lines = (OUT / "00_sha256.txt").read_text().splitlines()
    for line in lines:
        expected, path = line.split("  ", 1)
        assert digest(Path(path)) == expected, path
    print(f"unchanged frozen inputs: {len(lines)}")
else:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing freeze: {OUT}")
    if Path("results/raw/T22/33_v3_primary").exists():
        raise SystemExit("refusing to create pre-output freeze after primary results exist")
    OUT.mkdir(parents=True)
    paths = [Path("scripts") / n for n in (
        "t22_v3_tailspec.py", "t22_v3_eval.py", "t22_v3.sh", "t22_v3_checks.py", "t22_v3_protocol.md")]
    paths += sorted(Path("scripts/t22_specs").glob("payy_*.json"))
    paths += [Path("scripts") / n for n in ("t22_tailspec.py", "t22_eval.py", "t22.sh", "t21_tailcheck.py")]
    (OUT / "00_sha256.txt").write_text("\n".join(f"{digest(p)}  {p}" for p in paths) + "\n")
    (OUT / "01_freeze.txt").write_text(
        "frozen_utc=" + datetime.datetime.now(datetime.timezone.utc).isoformat() + "\nrepository_head=" +
        subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() +
        "\nFresh-checkout local freeze; no analyzer invoked by this command.\n")
    old = {str(p): digest(p) for folder in ("31_v2_primary", "32_v2_diagnosis")
           for p in sorted((Path("results/raw/T22") / folder).rglob("*")) if p.is_file()}
    (OUT / "02_preserved_evidence.json").write_text(json.dumps(old, indent=2) + "\n")
    (OUT / "03_commands.txt").write_text(
        'CVC5="$PWD/tools/cvc5-1.4.2-gpl/bin/cvc5" python3 -I scripts/t22_v3_checks.py\n'
        'T22_RUN_ID=33_v3_primary TLIMIT=300 bash scripts/t22_v3.sh\n')
    print(f"freeze created; {len(paths)} source inputs and {len(old)} prior evidence files")
