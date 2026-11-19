#!/usr/bin/env python3
"""Pinned EVAL acquisition and Circom build preflight, with no analyzer call."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

if __package__ in {None, ""}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bindcheck_zk.circuits import Circuit, _tree_digest, is_entry_circuit, resolve_circom_includes
from eval.common import PLAN_SOURCE_SHA256, ROOT, SOURCE_LEDGER, atomic_write_json, read_csv, select_families, sha256_file, run_command, utc_now
from eval.run_heldout import acquire_once, prepare_pinned_vendor


SAMPLE = ROOT / "reports/heldout/selected-families.csv"
SAMPLE_SHA256 = "cf1b64bc68d90a790e63d965a3e3c607dc6f27e5250ba58d5968d4f792972d8b"
EXPOSED_RANK = 259
MAX_BUILDS = 2
BUILD_TIMEOUT = 30.0
VENDOR_TREE_SHA256 = "d359bab216fc262b406f468d87774ec1b6661e4438b38851fcd6a0a2e1e8a57a"


def selected() -> list[dict[str, str]]:
    if sha256_file(SOURCE_LEDGER) != PLAN_SOURCE_SHA256:
        raise RuntimeError("source corpus bytes differ from frozen selection")
    if sha256_file(SAMPLE) != SAMPLE_SHA256:
        raise RuntimeError("selected-family bytes differ from preregistration")
    frozen = read_csv(SAMPLE)
    computed = select_families(read_csv(SOURCE_LEDGER), "EVAL")
    if len(frozen) != len(computed) or any(
        row["family_id"] != item["family_id"] or row["commit"] != item["commit"]
        for row, item in zip(frozen, computed, strict=True)
    ):
        raise RuntimeError("selected-family copy differs from source-ledger selection")
    return frozen


def prebuild_checkout(family: dict[str, str], family_dir: pathlib.Path,
                      checkout: pathlib.Path, circom: pathlib.Path) -> dict:
    """Compile recorded Circom entry points in an already acquired checkout."""
    base = {"compile_attempts": []}
    paths = [checkout / path for path in family["circuit_paths"].split("|") if path.endswith(".circom")]
    entries = [path for path in paths if path.is_file() and is_entry_circuit(path)]
    base["recorded_circom_paths"] = len(paths)
    base["entry_circom_paths"] = len(entries)
    if not entries:
        base["status"] = "NO_ENTRY_CIRCOM"
        return base
    for path in entries[:MAX_BUILDS]:
        relative = path.relative_to(checkout).as_posix()
        circuit = Circuit(path, relative, "circom", sha256_file(path), [], None, False, [], [])
        with tempfile.TemporaryDirectory(prefix="prebuild-circom-", dir=family_dir) as temporary:
            temp = pathlib.Path(temporary)
            overlay = temp / "includes"
            include_dirs, include_resolution = resolve_circom_includes(circuit, checkout, overlay)
            include_dirs.extend([checkout / "node_modules", path.parent / "node_modules"])
            argv = [str(circom), str(path), "--r1cs", "--sym", "-o", str(temp)]
            seen: set[pathlib.Path] = set()
            for include in include_dirs:
                if include.is_dir() and include.resolve() not in seen:
                    seen.add(include.resolve())
                    argv.extend(["-l", str(include)])
            command = run_command(argv, cwd=checkout, timeout=BUILD_TIMEOUT)
            r1cs = temp / (path.stem + ".r1cs")
            sym = temp / (path.stem + ".sym")
            success = command["exit_status"] == 0 and not command["timed_out"] and r1cs.is_file() and sym.is_file()
            base["compile_attempts"].append({
                "circuit": relative, "source_sha256": circuit.sha256,
                "include_resolution": include_resolution,
                "command": command,
                "r1cs_bytes": r1cs.stat().st_size if r1cs.is_file() else None,
                "sym_bytes": sym.stat().st_size if sym.is_file() else None,
                "success": success,
            })
    base["status"] = "BUILT" if any(item["success"] for item in base["compile_attempts"]) else "BUILD_FAILED"
    return base


def prebuild_family(family: dict[str, str], output: pathlib.Path, circom: pathlib.Path) -> dict:
    rank = int(family["rank"])
    family_dir = output / "families" / f"{rank:03d}-{family['sample_hash'][:12]}"
    family_dir.mkdir(parents=True, exist_ok=True)
    record_path = family_dir / "prebuild.json"
    if record_path.exists():
        return json.loads(record_path.read_text())
    base = {"schema": "bindcheck-zk.prebuild/v1", "rank": rank,
            "family_id": family["family_id"], "repository": family["repository"],
            "commit": family["commit"], "started_utc": utc_now(), "compile_attempts": []}
    if rank == EXPOSED_RANK:
        record = {**base, "status": "EXPOSED_EXCLUDED", "checkout_deleted": True,
                  "finished_utc": utc_now()}
        atomic_write_json(record_path, record)
        return record
    work_root = output / "work"
    work_root.mkdir(exist_ok=True)
    checkout = work_root / f"{rank:03d}-{family['sample_hash'][:12]}"
    try:
        acquisition = acquire_once(family, family_dir, checkout)
        base["acquisition_status"] = acquisition.get("status")
        if acquisition.get("status") != "ready":
            base["status"] = "ACQUISITION_FAILED"
            return base
        base["dependency_setup"] = prepare_pinned_vendor(checkout, family_dir, ROOT / "node_modules/circomlib")
        base.update(prebuild_checkout(family, family_dir, checkout, circom))
        return base
    except Exception as exc:
        base["status"] = "PREFLIGHT_ERROR"
        base["error"] = f"{type(exc).__name__}: {exc}"
        return base
    finally:
        if checkout.exists():
            shutil.rmtree(checkout)
        base["checkout_deleted"] = not checkout.exists()
        base["finished_utc"] = utc_now()
        atomic_write_json(record_path, base)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=pathlib.Path, default=SAMPLE,
                        help="historical sample CSV; reserve uses eval/reserve.py")
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "results/raw/heldout/prebuild-v1")
    parser.add_argument("--circom", type=pathlib.Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.sample.resolve() != SAMPLE.resolve():
        parser.error("only the historical sample is accepted here; use eval/reserve.py for the reserve")
    if not args.circom.is_file() or not 1 <= args.jobs <= 2:
        parser.error("circom must exist and jobs must be 1 or 2")
    vendor = ROOT / "node_modules/circomlib"
    if not vendor.is_dir() or _tree_digest(vendor) != (VENDOR_TREE_SHA256, 144):
        parser.error("pinned circomlib@2.0.5 tree is missing or does not match vendor-lock.json")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    families = selected()
    records = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(prebuild_family, family, output, args.circom.resolve()): family for family in families}
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            print(f"PREBUILD\t{record['rank']:03d}\t{record['status']}\t{record['repository']}", flush=True)
    records.sort(key=lambda item: item["rank"])
    summary = {
        "schema": "bindcheck-zk.prebuild-summary/v1",
        "completed_utc": utc_now(), "sample_sha256": SAMPLE_SHA256,
        "source_corpus_sha256": sha256_file(SOURCE_LEDGER),
        "circom": str(args.circom.resolve()), "circom_sha256": sha256_file(args.circom),
        "jobs": args.jobs, "max_builds_per_family": MAX_BUILDS,
        "circomlib_tree_sha256": VENDOR_TREE_SHA256,
        "build_timeout_seconds": BUILD_TIMEOUT,
        "families": len(records),
        "status_counts": dict(sorted(Counter(item["status"] for item in records).items())),
        "checkout_remaining": len(list((output / "work").iterdir())) if (output / "work").exists() else 0,
    }
    atomic_write_json(output / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
