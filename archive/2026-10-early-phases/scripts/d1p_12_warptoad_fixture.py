#!/usr/bin/env python3
"""D1P-12 WarpToad source/artifact preflight.

This standard-library-only checker is intentionally setup-only.  It verifies
the five WarpToad files preserved by D1P-11, inventories the pinned build and
proof inputs needed for the executable fixture, probes local tool identities,
and checks the existing ACIR reader's exact version gate when a compiled
artifact is available.  It never installs dependencies, builds, proves,
starts a chain, or mutates the supplied source tree.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
REVISION = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
READER_VERSION = "1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051"

EXPECTED_D1P11 = {
    "backend/circuits/withdraw/src/main.nr":
        "ce4bf56bb44e2e1106560251f3ff28dc8545fc9b7b7256c9d7695f6e28de192f",
    "backend/contracts/core/WarpToadCore.sol":
        "323a1cf26c7449f67cf277ff0a46c31e12f725c555f9fa165d5a60011e122c39",
    "backend/test/testL1ToL1.ts":
        "1c831d9e3832191ef6b1b1aac679c5c517ad89cdf3adfc708e4266a4780ff349",
    "backend/lib/proving.ts":
        "e1c7e4d209e82fe9b51b536605671bb32545e52f27bccf0240892f2c24d8323c",
    "backend/package.json":
        "01f2bae4590b1cbe14716c1ff1cd50209bd4b1cb5be9fc20e13da8801b0aa57b",
}

# These are source/build inputs, not a claim about the generated verifier's
# filename.  Verifier candidates are collected separately by glob.
REQUIRED_PATHS = [
    "README.md",
    "package.json",
    "pnpm-lock.yaml",
    "backend/package.json",
    "backend/hardhat.config.ts",
    "backend/circuits/withdraw/Nargo.toml",
    "backend/circuits/withdraw/src/main.nr",
    "backend/circuits/withdraw/target/withdraw.json",
    "backend/scripts/regenerateVerifier.ts",
    "backend/test/testL1ToL1.ts",
    "backend/test/helpers/setup.ts",
]

VERIFIER_GLOBS = [
    "backend/contracts/**/*Verifier*.sol",
    "backend/contracts/**/*verifier*.sol",
]

TOOL_COMMANDS = {
    "git": ["git", "--version"],
    "node": ["node", "--version"],
    "pnpm": ["pnpm", "--version"],
    "nargo": ["nargo", "--version"],
    "bb": ["bb", "--version"],
    "forge": ["forge", "--version"],
    "anvil": ["anvil", "--version"],
    "solc": ["solc", "--version"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(argv: list[str], cwd: Path | None = None) -> dict:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv, cwd=cwd, text=True, capture_output=True, timeout=10,
            check=False,
        )
        return {
            "argv": argv,
            "available": True,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "wall_seconds": round(time.monotonic() - started, 6),
        }
    except FileNotFoundError:
        return {
            "argv": argv,
            "available": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "executable not found on PATH",
            "wall_seconds": round(time.monotonic() - started, 6),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "available": True,
            "exit_code": None,
            "stdout": (exc.stdout or "").strip(),
            "stderr": "version probe timed out after 10 seconds",
            "wall_seconds": round(time.monotonic() - started, 6),
        }


def source_identity(source_root: Path) -> dict:
    git_dir = source_root / ".git"
    if not git_dir.exists():
        return {
            "kind": "hash-matched-source-slice",
            "revision": None,
            "revision_matches_pin": False,
            "note": "No Git metadata; five D1P-11 hashes do not establish a complete checkout.",
        }
    record = run(["git", "rev-parse", "HEAD"], cwd=source_root)
    revision = record["stdout"] if record["exit_code"] == 0 else None
    return {
        "kind": "git-checkout",
        "revision": revision,
        "revision_matches_pin": revision == REVISION,
        "git_probe": record,
    }


def read_declared_dependencies(source_root: Path) -> dict:
    path = source_root / "backend/package.json"
    if not path.is_file():
        return {"available": False}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": True, "parse_error": str(exc)}
    dependencies = payload.get("dependencies", {})
    return {
        "available": True,
        "noir_js": dependencies.get("@noir-lang/noir_js"),
        "bb_js": dependencies.get("@aztec/bb.js"),
        "hardhat": payload.get("devDependencies", {}).get("hardhat"),
        "solidity_pragma": "0.8.29",
        "package_sha256": sha256(path),
    }


def artifact_compatibility(source_root: Path) -> dict:
    candidates = []
    for relative in (
        "backend/circuits/withdraw/target/withdraw.json",
        "frontend/src/lib/circuits/withdraw.json",
    ):
        path = source_root / relative
        if path.is_file():
            candidates.append((relative, path))
    if not candidates:
        return {
            "status": "ARTIFACT_UNAVAILABLE",
            "reader_expected_noir_version": READER_VERSION,
            "note": "No compiled artifact was available, so the reader was not invoked.",
        }
    records = []
    for relative, path in candidates:
        record = {"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size}
        try:
            artifact = json.loads(path.read_text())
            version = artifact.get("noir_version")
            record["artifact_noir_version"] = version
            record["status"] = (
                "VERSION_GATE_MATCHES" if version == READER_VERSION
                else "INCOMPATIBLE_COMPILER_VERSION"
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            record.update(status="INVALID_OR_UNREADABLE_JSON", error=str(exc))
        records.append(record)
    statuses = {record["status"] for record in records}
    return {
        "status": (
            "INCOMPATIBLE" if "INCOMPATIBLE_COMPILER_VERSION" in statuses
            else "VERSION_GATE_MATCHES_DECODER_NOT_RUN"
        ),
        "reader_expected_noir_version": READER_VERSION,
        "artifacts": records,
        "note": "A version match alone would not establish opcode or semantic support.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    output = args.output.resolve()

    source_records = []
    matched = 0
    for relative, expected in EXPECTED_D1P11.items():
        path = source_root / relative
        actual = sha256(path) if path.is_file() else None
        matches = actual == expected
        matched += int(matches)
        source_records.append({
            "path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches_d1p11": matches,
            "bytes": path.stat().st_size if path.is_file() else None,
        })

    required = [{
        "path": relative,
        "present": (source_root / relative).is_file(),
        "sha256": sha256(source_root / relative)
        if (source_root / relative).is_file() else None,
    } for relative in REQUIRED_PATHS]

    verifier_candidates = {}
    for pattern in VERIFIER_GLOBS:
        for path in source_root.glob(pattern):
            if path.is_file():
                verifier_candidates[str(path.relative_to(source_root))] = {
                    "sha256": sha256(path), "bytes": path.stat().st_size,
                }

    tools = {name: run(argv) for name, argv in TOOL_COMMANDS.items()}
    identity = source_identity(source_root)
    dependencies = read_declared_dependencies(source_root)
    artifact = artifact_compatibility(source_root)
    missing = [record["path"] for record in required if not record["present"]]

    blockers = []
    if matched != len(EXPECTED_D1P11):
        blockers.append("D1P11_SOURCE_HASH_MISMATCH_OR_MISSING")
    if not identity["revision_matches_pin"]:
        blockers.append("FULL_PINNED_CHECKOUT_IDENTITY_UNAVAILABLE")
    if missing:
        blockers.append("PINNED_BUILD_OR_LOCK_INPUTS_MISSING")
    if artifact["status"] == "ARTIFACT_UNAVAILABLE":
        blockers.append("COMPILED_WITHDRAW_ARTIFACT_MISSING")
    elif artifact["status"] == "INCOMPATIBLE":
        blockers.append("EXISTING_ACIR_READER_INCOMPATIBLE")
    if not verifier_candidates:
        blockers.append("GENERATED_SOLIDITY_VERIFIER_MISSING")
    for tool in ("pnpm", "nargo", "bb"):
        if not tools[tool]["available"]:
            blockers.append(f"PINNED_{tool.upper()}_TOOL_UNAVAILABLE")

    payload = {
        "schema": "bindcheck.d1p12.preflight/v1",
        "task": "D1P-12",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_root": str(source_root),
        "pinned_revision": REVISION,
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "logical_cpus": os.cpu_count(),
            "free_disk_bytes": shutil.disk_usage(ROOT).free,
        },
        "source_identity": identity,
        "d1p11_source_hashes": {
            "matched": matched,
            "expected": len(EXPECTED_D1P11),
            "records": source_records,
        },
        "required_paths": required,
        "missing_required_paths": missing,
        "declared_dependencies": dependencies,
        "local_tools": tools,
        "verifier_candidates": verifier_candidates,
        "acir_reader_compatibility": artifact,
        "proof_generation_attempts": 0,
        "build_attempts": 0,
        "consumer_execution_attempts": 0,
        "status": "READY" if not blockers else "BLOCKED_SETUP",
        "blockers": blockers,
        "claim_boundary": (
            "Setup/provenance evidence only; no source/artifact/key correspondence, "
            "proof acceptance, consumer effect, performance, or D1 security result."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "matched_d1p11_hashes": matched,
        "missing_required_paths": len(missing),
        "blockers": blockers,
        "output": str(output),
    }, sort_keys=True))
    return 0 if payload["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
