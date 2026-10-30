#!/usr/bin/env python3
"""Repair checks for X-AV E4 rows (lane-x-muse validation task).

For each E4 (and E4-preserved) row: apply a minimal repair (producer- or
consumer-side) and show the recorded attack FAILS while honest behavior
SUCCEEDS. No new proofs are generated: circuit repairs are checked with
``nargo execute`` (attacker witness rejected, honest witness accepted) and
consumer repairs replay the RECORDED mutant proofs against the PINNED
consumer (attack reverts, honest mint succeeds).

Repairs restore exactly the removed source line, so the repaired file is
byte-identical to the pinned baseline (asserted by SHA-256). Warning-remains
then follows from the D1P-34 pinned-target analyses (WarpToad pinned: no
warning) plus the cited Payy precedent; it is labeled as derived, not
re-measured, where the analyzer inputs are not materialized locally.

Usage:
  python3 scripts/xav/repair_check.py --out results/raw/REPAIR

Writes $OUT/repair-report.json and per-step logs under $OUT/logs/.
Requires (read-only, env-overridable):
  BINDCHECK_NARGO_22        nargo beta.22 binary (default /private/tmp/n22/nargo)
  BINDCHECK_WARPTOAD_BACKEND pinned WarpToad backend (circuits+contracts)
  BINDCHECK_XAV_V11         v1.1 evidence dir (default results/raw/X-AV/v11)
  BINDCHECK_REF_BUILDINFO   Hardhat build-info dir for PoseidonT3/LazyIMT
  BINDCHECK_SOLC_0_8_29     solc 0.8.29 binary for Hardhat compiles
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import xav_run  # noqa: E402  (pure helpers + guarded main; safe to import)
from bindcheck_d1.witness_synth_v1 import apply_bind_word  # noqa: E402

NARGO = Path(os.environ.get("BINDCHECK_NARGO_22", "/private/tmp/n22/nargo"))
V11 = Path(os.environ.get("BINDCHECK_XAV_V11", ROOT / "results/raw/X-AV/v11"))
BASE = Path(os.environ.get(
    "BINDCHECK_WARPTOAD_BACKEND",
    "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/pinned-source/backend",
))
MUT_BASE = ROOT / "benchmarks/binding-mutants/baselines"
SIB_NM = Path(
    "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/node_modules")

# mutant -> repair side + file + baseline file (repaired == pinned bytes)
CIRCUIT_ROWS = {
    "WT-C01": {"words": {"nullifier": "0x1111111111111111111111111111111111111111111111111111111111111111"},
               "kind": "bind-word", "assert": "nullifier doesn't match inputs"},
    "WT-C02": {"words": {"max_fee": "0x0"},
               "kind": "bind-word", "assert": "max_fee higher than amount"},
    "WT-C04": {"kind": "anchor-tree", "dest_override": "honest",
               "assert": "giga membership"},
    "WT-C07": {"words": {"chain_id": "0x1"}, "kind": "anchor-tree",
               "assert": "commitment"},
    "WT-C08": {"words": {"recipient_address": "0x0"},
               "kind": "bind-word", "assert": "recipient_address cant be 0"},
    "WT-C03": {"kind": "aztec-branch", "assert": "aztec"},
    "WT-S02": {"words": {"giga_root": "0x1234"},
               "kind": "bind-word", "assert": None},  # consumer defect; circuit accepts
    "WT-S06": {"words": {"max_fee": "0x0"},
               "kind": "bind-word", "assert": None},  # consumer defect; circuit accepts
}
# consumer mutants: repair == restore pinned WarpToadCore.sol exactly
CONSUMER_ROWS = ["WT-S01", "WT-S02", "WT-S03", "WT-S06", "WT-S09"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def sh(argv, cwd, timeout, log):
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=os.environ.copy())
    wall = time.monotonic() - t0
    log.write_text(f"$ {' '.join(map(str, argv))}\nexit={p.returncode} wall={wall:.1f}s\n"
                   f"--- stdout ---\n{p.stdout[-2000:]}\n--- stderr ---\n{p.stderr[-2000:]}")
    return p, wall


def attacker_toml(mid: str) -> str:
    """Reconstruct the recorded attacker Prover.toml from saved material."""
    cfg = CIRCUIT_ROWS[mid]
    build = V11 / "build" / mid
    honest = (V11 / "build" / "WT-C04" / "honest.toml").read_text()
    if cfg["kind"] == "bind-word":
        return apply_bind_word(honest, cfg["words"])
    if cfg["kind"] == "anchor-tree":
        spec = json.loads((build / "anchor.json").read_text())
        return xav_run.compose_anchor(honest, spec, cfg.get("words") or None,
                                      cfg.get("dest_override"))
    if cfg["kind"] == "aztec-branch":
        spec = json.loads((build / "aztec.json").read_text())
        return xav_run.compose_aztec(honest, spec)
    raise AssertionError(mid)


def circuit_repair(mid: str, out: Path, row: dict) -> None:
    logdir = out / "logs"
    stage = Path(f"/tmp/repair-xav-circuits/{mid}")
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(V11 / "build" / mid / "circuits", stage, symlinks=True)
    for p in stage.rglob("target"):
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
    # minimal producer repair: restore pinned circuit files
    shutil.copy(MUT_BASE / "warptoad-withdraw-main.nr", stage / "withdraw/src/main.nr")
    if mid == "WT-C03":
        shutil.copy(MUT_BASE / "warptoad-nargo-hashing-lib.nr",
                    stage / "nargo_hashing/src/lib.nr")
    row["repaired_main_sha256"] = sha256(stage / "withdraw/src/main.nr")
    row["pinned_main_sha256"] = sha256(MUT_BASE / "warptoad-withdraw-main.nr")
    row["repair_is_pinned_bytes"] = row["repaired_main_sha256"] == row["pinned_main_sha256"]
    if not row["repair_is_pinned_bytes"]:
        row["verdict"] = "REPAIR-MISMATCH"
        return
    p, _ = sh([str(NARGO), "compile"], cwd=stage / "withdraw", timeout=600,
              log=logdir / f"{mid}-repair-compile.log")
    row["compile"] = "PASS" if p.returncode == 0 else f"FAIL exit={p.returncode}"
    if p.returncode != 0:
        row["verdict"] = "REPAIR-COMPILE-FAIL"
        return
    honest = (V11 / "build" / "WT-C04" / "honest.toml").read_text()
    (stage / "withdraw" / "Prover.toml").write_text(honest)
    p, _ = sh([str(NARGO), "execute"], cwd=stage / "withdraw", timeout=300,
              log=logdir / f"{mid}-repair-honest.log")
    row["honest_execute"] = "PASS" if (p.returncode == 0 and "successfully solved" in p.stdout) \
        else f"FAIL exit={p.returncode}"
    atk = attacker_toml(mid)
    (stage / "withdraw" / "Prover.toml").write_text(atk)
    p, _ = sh([str(NARGO), "execute"], cwd=stage / "withdraw", timeout=300,
              log=logdir / f"{mid}-repair-attack.log")
    blocked = p.returncode != 0
    row["attack_execute"] = ("BLOCKED" if blocked
                             else "UNEXPECTED-PASS (repair does not stop attack)")
    row["attack_stderr_tail"] = (p.stderr.strip().splitlines()[-1][:200]
                                 if p.stderr.strip() else p.stdout.strip().splitlines()[-1][:200])
    if row["honest_execute"] == "PASS" and blocked:
        row["verdict"] = "REPAIR-OK"
    else:
        row["verdict"] = "REPAIR-UNEXPECTED"


def consumer_repair(mid: str, out: Path, row: dict) -> None:
    logdir = out / "logs"
    src = V11 / "build" / mid
    stage = Path(f"/tmp/repair-xav-consumer/{mid}")
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(src, stage, symlinks=True)
    for d in ("hh-cache", "hh-artifacts"):
        p = stage / d
        if p.exists():
            shutil.rmtree(p)
    # minimal consumer repair: restore pinned WarpToadCore.sol exactly
    dst = stage / "contracts/core/WarpToadCore.sol"
    shutil.copy(MUT_BASE / "WarpToadCore.sol", dst)
    row["repaired_consumer_sha256"] = sha256(dst)
    row["pinned_consumer_sha256"] = sha256(MUT_BASE / "WarpToadCore.sol")
    row["repair_is_pinned_bytes"] = row["repaired_consumer_sha256"] == row["pinned_consumer_sha256"]
    if not row["repair_is_pinned_bytes"]:
        row["verdict"] = "REPAIR-MISMATCH"
        return
    env = os.environ.copy()
    env["BINDCHECK_SOLC_0_8_29"] = os.environ.get("BINDCHECK_SOLC_0_8_29",
                                                  "/private/tmp/solc-0.8.29")
    env["NODE_PATH"] = str(stage / "node_modules")
    env["PATH"] = str(SIB_NM / ".bin") + os.pathsep + env.get("PATH", "")
    ref_bi = os.environ.get(
        "BINDCHECK_REF_BUILDINFO",
        "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/D1P-19/workspace/source/backend/artifacts/build-info")
    env["XAV_REF_BUILDINFO"] = ref_bi
    t0 = time.monotonic()
    p = subprocess.run(["npx", "--no-install", "hardhat", "compile"],
                       cwd=stage, capture_output=True, text=True, timeout=900, env=env)
    (logdir / f"{mid}-repaired-hhcompile.log").write_text(
        f"exit={p.returncode} wall={time.monotonic()-t0:.1f}s\n--- stdout ---\n"
        f"{p.stdout[-2000:]}\n--- stderr ---\n{p.stderr[-2000:]}")
    row["hhcompile"] = "PASS" if p.returncode == 0 else f"FAIL exit={p.returncode}"
    if p.returncode != 0:
        row["verdict"] = "REPAIR-COMPILE-FAIL"
        return
    # attack replay: recorded mutant plan against the pinned consumer
    env["XAV_PLAN"] = str((stage / "plan.json").resolve())
    env["XAV_REPORT"] = str((stage / "report-repaired.json").resolve())
    p = subprocess.run(["npx", "--no-install", "hardhat", "run", "replay.ts"],
                       cwd=stage, capture_output=True, text=True, timeout=1200, env=env)
    (logdir / f"{mid}-repaired-replay.log").write_text(
        f"exit={p.returncode}\n--- stdout ---\n{p.stdout[-2000:]}\n--- stderr ---\n{p.stderr[-2000:]}")
    try:
        rep = json.loads((stage / "report-repaired.json").read_text())
    except (OSError, ValueError):
        row["verdict"] = "REPAIR-HARNESS-FAIL"
        return
    row["repaired_replay"] = rep
    mints = [s for s in rep.get("steps", []) if any(k.startswith("mint_") for k in s)]
    ok = [list(s.values())[0].get("status") in ("0x1", "success")
          for s in mints if isinstance(list(s.values())[0], dict)]
    row["mint_outcomes_repaired"] = ok
    # honest-first-mint control: single-mint attacks need the C01 honest mint
    row["verdict"] = "see-mints"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/raw/REPAIR")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    out: Path = args.out
    (out / "logs").mkdir(parents=True, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None
    report = {"rows": [], "toolchain": {"nargo": subprocess.run(
        [str(NARGO), "--version"], capture_output=True, text=True).stdout.strip()}}
    ordered = list(dict.fromkeys(list(CIRCUIT_ROWS) + CONSUMER_ROWS))
    for mid in ordered:
        if only and mid not in only:
            continue
        row: dict = {"mutant": mid}
        try:
            if mid in CONSUMER_ROWS and mid not in CIRCUIT_ROWS:
                row["side"] = "consumer"
                consumer_repair(mid, out, row)
            elif mid in CONSUMER_ROWS and mid in CIRCUIT_ROWS:
                # S02/S06: circuit accepts by design; repair is consumer-side.
                row["side"] = "consumer (circuit accepts attacker word by design)"
                row["circuit_note"] = ("nargo execute of attacker word on pinned "
                                       "circuit is expected to PASS; containment "
                                       "must come from the consumer admission check")
                consumer_repair(mid, out, row)
            else:
                row["side"] = "producer"
                circuit_repair(mid, out, row)
        except Exception as exc:  # noqa: BLE001 - record, keep going
            row["verdict"] = f"HARNESS-ERROR: {type(exc).__name__}: {exc}"[:300]
        report["rows"].append(row)
        print(json.dumps({k: row.get(k) for k in ("mutant", "side", "verdict")}), flush=True)
    (out / "repair-report.json").write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
