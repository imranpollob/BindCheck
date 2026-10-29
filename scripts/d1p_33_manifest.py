#!/usr/bin/env python3
"""Freeze the D1P-33 held-out scan identities and execution outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-33"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "bytes": path.stat().st_size,
        "sha256": sha256_bytes(path.read_bytes()),
    }


def output(argv: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def command_log(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    return {
        **file_record(path),
        "argv": value["argv"],
        "returncode": value["returncode"],
        "runtime_seconds": value["runtime_seconds"],
        "stderr_last_line": value["stderr"].strip().splitlines()[-1] if value["stderr"].strip() else "",
    }


def tool_record(path: Path) -> dict[str, Any]:
    completed = subprocess.run([str(path), "--version"], text=True, capture_output=True, check=False)
    return {**file_record(path), "version_output": (completed.stdout + completed.stderr).strip()}


def source_record(source: Path) -> dict[str, Any]:
    submodules = output(["git", "submodule", "status", "--recursive"], source)
    return {
        "origin": output(["git", "remote", "get-url", "origin"], source),
        "commit": output(["git", "rev-parse", "HEAD"], source),
        "tree": output(["git", "rev-parse", "HEAD^{tree}"], source),
        "commit_date": output(["git", "show", "-s", "--format=%cI", "HEAD"], source),
        "submodules": submodules.splitlines() if submodules else [],
        "working_tree_status": output(["git", "status", "--short"], source).splitlines(),
    }


def protected_files() -> dict[str, Any]:
    paths = output(["git", "ls-files", "src", "protocols"]).splitlines()
    records = []
    for name in paths:
        expected = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        actual = (ROOT / name).read_bytes()
        records.append({
            "path": name,
            "head_sha256": sha256_bytes(expected),
            "working_sha256": sha256_bytes(actual),
            "equal": expected == actual,
        })
    result = {
        "schema": "bindcheck.d1p33.protected-files/v1",
        "head": output(["git", "rev-parse", "HEAD"]),
        "tag": output(["git", "describe", "--tags", "--exact-match", "HEAD"]),
        "files": records,
        "all_equal": all(item["equal"] for item in records),
    }
    path = RAW / "protected-files.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return {**file_record(path), "all_equal": result["all_equal"], "count": len(records)}


def main() -> int:
    specs = {
        "nullproof": {
            "artifact": "circuit/target/nullproof_non_membership.json",
            "consumer": "contracts/src/ComplianceGate.sol",
            "contract_artifact": "contracts/out/ComplianceGate.sol/ComplianceGate.json",
            "build_logs": ["nargo-compile.json", "forge-build.json", "npm-install-bbjs-isolated.json"],
            "nargo": RAW / "tools/noir-beta19/bin/nargo",
            "solc": Path.home() / ".svm/0.8.33/solc-0.8.33",
            "bb": {
                "kind": "npm-package",
                "version": "5.0.0-nightly.20260522",
                "package": RAW / "tools/nullproof-bbjs/node_modules/@aztec/bb.js/package.json",
                "lock": RAW / "tools/nullproof-bbjs/package-lock.json",
            },
        },
        "privacy-preserving-ip-nft": {
            "artifact": "circuits/target/ip_nft_ownership.json",
            "consumer": "contracts/circuit/IPNFTOwnershipVerifier.sol",
            "contract_artifact": "out/IPNFTOwnershipVerifier.sol/IPNFTOwnershipVerifier.json",
            "build_logs": ["nargo-compile.json", "nargo-compile-beta3.json", "forge-build.json",
                           "forge-build-contracts-only.json"],
            "nargo": RAW / "tools/noir-beta3/bin/nargo",
            "solc": Path.home() / ".svm/0.8.30/solc-0.8.30",
            "bb": {
                "kind": "not-exactly-pinned",
                "declared": "@aztec/bb.js ^0.82.3; README says bbup without a version",
            },
        },
        "zkt-research": {
            "artifact": "noir-circuits/zkat_eligibility/target/zkat_eligibility.json",
            "consumer": "sc/src/DAO/ZKTCore.sol",
            "contract_artifact": "sc/out/ZKTCore.sol/ZKTCore.json",
            "build_logs": ["nargo-compile.json", "forge-build.json", "forge-build-official-solc.json"],
            "nargo": RAW / "tools/noir-beta21/bin/nargo",
            "solc": RAW / "tools/solc-0.8.31/solc",
            "bb": {
                "kind": "not-exactly-pinned",
                "declared": "README: Barretenberg v5.0.0-nightly (no nightly date/build identity)",
            },
        },
        "zkpassport-circuits": {
            "artifact": "target/outer_count_4.json",
            "consumer": "src/solidity/lib/zkpassport-packages/packages/registry-contracts/src/SubVerifier.sol",
            "contract_artifact": "src/solidity/out/SubVerifier.sol/SubVerifier.json",
            "build_logs": ["nargo-compile-outer-count-4.json", "forge-build.json"],
            "nargo": RAW / "tools/noir-beta22/bin/nargo",
            "solc": Path.home() / ".svm/0.8.30/solc-0.8.30",
            "bb": {
                "kind": "cli-binary",
                **tool_record(RAW / "tools/bb-5.0.0/bb"),
                "archive": file_record(RAW / "tools/bb-5.0.0/barretenberg-arm64-darwin.tar.gz"),
            },
        },
    }

    projects = []
    for name, spec in specs.items():
        source = RAW / name / "source"
        artifact = source / spec["artifact"]
        artifact_json = json.loads(artifact.read_text())
        consumer = source / spec["consumer"]
        analysis_log = RAW / name / "logs/bindcheck-analyze.json"
        analysis = json.loads(analysis_log.read_text())
        bb = dict(spec["bb"])
        if bb["kind"] == "npm-package":
            bb["package"] = file_record(bb["package"])
            bb["lock"] = file_record(bb["lock"])
        record = {
            "project": name,
            "source": source_record(source),
            "producer_artifact": {**file_record(artifact), "noir_version": artifact_json.get("noir_version")},
            "consumer_source": file_record(consumer),
            "contract_artifact": file_record(source / spec["contract_artifact"]),
            "toolchain": {
                "nargo": tool_record(spec["nargo"]),
                "solc": tool_record(spec["solc"]),
                "bb": bb,
            },
            "builds": [command_log(RAW / name / "logs" / item) for item in spec["build_logs"]],
            "analysis": {
                **command_log(analysis_log),
                "status": "UNSUPPORTED",
                "reason": analysis["stderr"].strip().removeprefix("bindcheck: error: "),
                "warning_count": 0,
                "warnings": [],
            },
            "validation": {
                "attempted": False,
                "reason": "no warning object was emitted",
            },
        }
        if name == "zkt-research":
            committed = subprocess.check_output(
                ["git", "show", "HEAD:noir-circuits/zkat_eligibility/target/zkat_eligibility.json"],
                cwd=source,
            )
            record["producer_artifact"]["committed_sha256_before_build"] = sha256_bytes(committed)
            record["producer_artifact"]["rebuilt_differs_from_committed"] = (
                sha256_bytes(committed) != record["producer_artifact"]["sha256"]
            )
        projects.append(record)

    protected = protected_files()
    tests = [
        command_log(RAW / "frozen-tool-tests.json"),
        command_log(RAW / "frozen-tool-tests-pythonpath.json"),
    ]
    result = {
        "schema": "bindcheck.d1p33.manifest/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tool": {
            "commit": output(["git", "rev-parse", "HEAD"]),
            "tag": output(["git", "describe", "--tags", "--exact-match", "HEAD"]),
            "protected_files": protected,
        },
        "scope": "first held-out scan; target-alone; local builds; no live-chain action",
        "retrieval": {
            "projects": [
                {
                    "origin": item["source"]["origin"],
                    "commit": item["source"]["commit"],
                    "destination": f"results/raw/D1P-33/{item['project']}/source",
                    "commands": [
                        f"git clone {item['source']['origin']} results/raw/D1P-33/{item['project']}/source",
                        "git submodule update --init --recursive",
                    ],
                }
                for item in projects
            ],
            "tool_sources": [
                "https://github.com/noir-lang/noirup/releases/latest/download/noirup",
                "https://github.com/AztecProtocol/aztec-packages/releases/download/v5.0.0/barretenberg-arm64-darwin.tar.gz",
                "https://github.com/ethereum/solidity/releases/download/v0.8.31/solc-macos",
                "npm:@aztec/bb.js@5.0.0-nightly.20260522",
            ],
        },
        "projects": projects,
        "counts": {
            "projects": len(projects),
            "supported_analyses": 0,
            "unsupported_analyses": len(projects),
            "warnings": 0,
            "validations_attempted": 0,
        },
        "tests": tests,
        "deliverables": [
            file_record(ROOT / "reports/D1P-33.md"),
            file_record(ROOT / "README.md"),
            file_record(ROOT / "docs/project-status.md"),
            file_record(ROOT / "scripts/d1p_33_run_command.py"),
            file_record(ROOT / "scripts/d1p_33_manifest.py"),
        ],
        "setup_notes": [
            "An exploratory `noirup --version` call was interpreted as an install and placed Noir 1.0.0-rc.7 under ~/.nargo before isolated NARGO_HOME directories were used.",
            "The ZKPassport nargo compile populated Noir's default dependency cache under ~/nargo; source and generated artifacts remain in the D1P-33 namespace.",
            "An initial npm prefix attempt walked to the repository package root; package.json was restored byte-for-byte before freeze, then the package was installed under results/raw/D1P-33/tools/nullproof-bbjs.",
        ],
        "claim_limits": [
            "UNSUPPORTED is not a miss and is not evidence that a target is safe.",
            "No warning was emitted, so there is no warning to triage or validate.",
            "No held-out target caused a frozen analyzer, protocol, or effect-table change.",
        ],
    }
    path = RAW / "manifest.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
