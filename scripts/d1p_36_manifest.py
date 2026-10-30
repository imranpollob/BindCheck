#!/usr/bin/env python3
"""Assemble the D1P-36 transfer-scan ledger without rerunning analysis."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-36"
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.model_v2 import Unsupported  # noqa: E402
from bindcheck_d1.static_analyzer_v1 import load_producer  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(relative: str) -> dict:
    path = ROOT / relative
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def source_identity(relative: str) -> dict:
    source = ROOT / relative
    return {
        "path": relative,
        "origin": subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=source, text=True,
        ).strip(),
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True,
        ).strip(),
        "tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=source, text=True,
        ).strip(),
        "status": subprocess.check_output(
            ["git", "status", "--short"], cwd=source, text=True,
        ).splitlines(),
    }


def line_evidence(relative: str, start: int, end: int) -> dict:
    path = ROOT / relative
    lines = path.read_text().splitlines()
    return {
        "path": relative,
        "sha256": sha256(path),
        "start_line": start,
        "end_line": end,
        "text": "\n".join(f"{number}: {lines[number - 1]}" for number in range(start, end + 1)),
    }


def producer_probe(relative: str) -> dict:
    try:
        result = load_producer(ROOT / relative)
        return {
            "status": "PASS",
            "decoder": result["decoder"],
            "opcode_count": result["opcode_count"],
            "opcode_counts": result["opcode_counts"],
            "public_leaf_count": len(result["public_leaves"]),
        }
    except Unsupported as exc:
        return {"status": "UNSUPPORTED", "reason": exc.reason, "detail": str(exc)}
    except Exception as exc:
        return {"status": "UNSUPPORTED", "reason": type(exc).__name__, "detail": str(exc)}


PROJECTS = [
    {
        "project": "NullProof", "set": "A", "exposure": "reserved, second attempt",
        "source_root": "results/raw/D1P-33/nullproof/source",
        "artifact": "results/raw/D1P-33/nullproof/source/circuit/target/nullproof_non_membership.json",
        "consumer": "results/raw/D1P-33/nullproof/source/contracts/src/ComplianceGate.sol",
        "contract_artifact": "results/raw/D1P-33/nullproof/source/contracts/out/ComplianceGate.sol/ComplianceGate.json",
        "analysis_log": "results/raw/D1P-36/set-a/nullproof/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-33/nullproof/logs/nargo-compile.json",
                   "results/raw/D1P-33/nullproof/logs/forge-build.json"],
        "source_evidence": (84, 105),
        "extra": ["results/raw/D1P-36/set-a/nullproof/frontend/extraction-attempt.json"],
    },
    {
        "project": "privacy-preserving-IP-NFT", "set": "A", "exposure": "reserved, second attempt",
        "source_root": "results/raw/D1P-33/privacy-preserving-ip-nft/source",
        "artifact": "results/raw/D1P-33/privacy-preserving-ip-nft/source/circuits/target/ip_nft_ownership.json",
        "consumer": "results/raw/D1P-33/privacy-preserving-ip-nft/source/contracts/circuit/IPNFTOwnershipVerifier.sol",
        "contract_artifact": "results/raw/D1P-33/privacy-preserving-ip-nft/source/out/IPNFTOwnershipVerifier.sol/IPNFTOwnershipVerifier.json",
        "analysis_log": "results/raw/D1P-36/set-a/privacy-preserving-ip-nft/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-33/privacy-preserving-ip-nft/logs/nargo-compile-beta3.json",
                   "results/raw/D1P-33/privacy-preserving-ip-nft/logs/forge-build-contracts-only.json"],
        "source_evidence": (9, 17), "extra": [],
    },
    {
        "project": "zkt-research", "set": "A", "exposure": "reserved, second attempt",
        "source_root": "results/raw/D1P-33/zkt-research/source",
        "artifact": "results/raw/D1P-33/zkt-research/source/noir-circuits/zkat_eligibility/target/zkat_eligibility.json",
        "consumer": "results/raw/D1P-33/zkt-research/source/sc/src/DAO/ZKTCore.sol",
        "contract_artifact": "results/raw/D1P-33/zkt-research/source/sc/out/ZKTCore.sol/ZKTCore.json",
        "analysis_log": "results/raw/D1P-36/set-a/zkt-research/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-33/zkt-research/logs/nargo-compile.json",
                   "results/raw/D1P-33/zkt-research/logs/forge-build-official-solc.json"],
        "source_evidence": (549, 590), "extra": [],
    },
    {
        "project": "ZKPassport circuits", "set": "A", "exposure": "reserved, second attempt",
        "source_root": "results/raw/D1P-33/zkpassport-circuits/source",
        "artifact": "results/raw/D1P-33/zkpassport-circuits/source/target/outer_count_4.json",
        "consumer": "results/raw/D1P-33/zkpassport-circuits/source/src/solidity/lib/zkpassport-packages/packages/registry-contracts/src/SubVerifier.sol",
        "contract_artifact": "results/raw/D1P-33/zkpassport-circuits/source/src/solidity/out/SubVerifier.sol/SubVerifier.json",
        "analysis_log": "results/raw/D1P-36/set-a/zkpassport-circuits/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-33/zkpassport-circuits/logs/nargo-compile-outer-count-4.json",
                   "results/raw/D1P-33/zkpassport-circuits/logs/forge-build.json"],
        "source_evidence": (205, 230), "extra": [],
    },
    {
        "project": "zk-panagram", "set": "B", "exposure": "unseen, non-reserved",
        "source_root": "results/raw/D1P-36/set-b/zk-panagram/source",
        "artifact": "results/raw/D1P-36/set-b/zk-panagram/source/target/zkpanagram.json",
        "consumer": "results/raw/D1P-36/set-b/zk-panagram/source/contracts/src/panagram.sol",
        "contract_artifact": "results/raw/D1P-36/set-b/zk-panagram/source/contracts/out/panagram.sol/Panagram.json",
        "analysis_log": "results/raw/D1P-36/set-b/zk-panagram/logs/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-36/set-b/zk-panagram/logs/nargo-compile.stderr",
                   "results/raw/D1P-36/set-b/zk-panagram/logs/forge-build.stderr"],
        "source_evidence": (61, 75), "extra": [],
    },
    {
        "project": "nachweis-app", "set": "B", "exposure": "unseen, non-reserved",
        "source_root": "results/raw/D1P-36/set-b/nachweis-app/source",
        "artifact": "results/raw/D1P-36/set-b/nachweis-app/source/circuits/pid-sdjwt/target/pid_sdjwt.json",
        "consumer": "results/raw/D1P-36/set-b/nachweis-app/source/contracts/src/noir/NoirPidVerifier.sol",
        "contract_artifact": "results/raw/D1P-36/set-b/nachweis-app/source/contracts/out/NoirPidVerifier.sol/NoirPidVerifier.json",
        "analysis_log": "results/raw/D1P-36/set-b/nachweis-app/logs/bindcheck-analyze.json",
        "builds": ["results/raw/D1P-36/set-b/nachweis-app/logs/nargo-compile.stderr",
                   "results/raw/D1P-36/set-b/nachweis-app/logs/forge-build.stderr"],
        "source_evidence": (81, 101), "extra": [],
    },
    {
        "project": "confidential-agent-policy-verdicts", "set": "B", "exposure": "unseen, non-reserved",
        "source_root": "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/source",
        "artifact": "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/source/noir/target/capv_allowlist.json",
        "consumer": "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/source/src/HonkVerifierAdapter.sol",
        "contract_artifact": "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/source/out/HonkVerifierAdapter.sol/HonkVerifierAdapter.json",
        "analysis_log": "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/logs/bindcheck-analyze.json",
        "builds": [
            "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/logs/nargo-compile-noir.stderr",
            "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/logs/nargo-compile-noir-deny.stderr",
            "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/logs/nargo-compile-noir-notallowed.stderr",
            "results/raw/D1P-36/set-b/confidential-agent-policy-verdicts/logs/forge-build.stderr",
        ],
        "source_evidence": (50, 78), "extra": [],
    },
    {
        "project": "e-votinng-diploma", "set": "B", "exposure": "unseen, non-reserved",
        "source_root": "results/raw/D1P-36/set-b/e-votinng-diploma/source",
        "artifact": "results/raw/D1P-36/set-b/e-votinng-diploma/source/circuits/target/circuts.json",
        "consumer": "results/raw/D1P-36/set-b/e-votinng-diploma/source/contracts/src/Voting.sol",
        "contract_artifact": "results/raw/D1P-36/set-b/e-votinng-diploma/source/contracts/out/Voting.sol/Voting.json",
        "analysis_log": "results/raw/D1P-36/set-b/e-votinng-diploma/logs/bindcheck-analyze.json",
        "builds": [
            "results/raw/D1P-36/set-b/e-votinng-diploma/logs/forge-build.stderr",
            "results/raw/D1P-36/set-b/e-votinng-diploma/logs/forge-build-voting.stderr",
            "results/raw/D1P-36/set-b/e-votinng-diploma/logs/forge-build-verifier.stderr",
            "results/raw/D1P-36/set-b/e-votinng-diploma/logs/nargo-compile.stderr",
        ],
        "source_evidence": (73, 99), "extra": [],
    },
]


def main() -> int:
    freeze = json.loads((ROOT / "results/raw/D1P-35/freeze-manifest.json").read_text())
    frozen_mismatches = []
    for item in freeze["frozen_files"]:
        observed = sha256(ROOT / item["path"])
        if observed != item["sha256"]:
            frozen_mismatches.append({"path": item["path"], "expected": item["sha256"],
                                      "observed": observed})
    if frozen_mismatches:
        raise SystemExit(f"frozen tool changed: {frozen_mismatches}")

    records = []
    for spec in PROJECTS:
        analysis_log = json.loads((ROOT / spec["analysis_log"]).read_text())
        artifact_json = json.loads((ROOT / spec["artifact"]).read_text())
        stderr_lines = [line for line in analysis_log["stderr"].splitlines() if line]
        records.append({
            "project": spec["project"], "set": spec["set"], "exposure": spec["exposure"],
            "source": source_identity(spec["source_root"]),
            "producer_artifact": {**record(spec["artifact"]),
                                  "noir_version": artifact_json.get("noir_version")},
            "consumer_source": record(spec["consumer"]),
            "contract_artifact": record(spec["contract_artifact"]),
            "build_evidence": [record(path) for path in spec["builds"]],
            "analysis": {
                **record(spec["analysis_log"]),
                "argv": analysis_log["argv"],
                "returncode": analysis_log["returncode"],
                "runtime_seconds": analysis_log["runtime_seconds"],
                "status": "UNSUPPORTED" if analysis_log["returncode"] else "PASS",
                "cli_reason": stderr_lines[-1] if stderr_lines else None,
                "warning_count": 0,
                "warnings": [],
            },
            "producer_probe": producer_probe(spec["artifact"]),
            "boundary_and_effect_evidence": line_evidence(
                spec["consumer"], *spec["source_evidence"]
            ),
            "extra_evidence": [record(path) for path in spec["extra"]],
            "triage": [],
            "validation": {"attempted": False, "reason": "no warning object was emitted"},
        })

    manifest = {
        "schema": "bindcheck.d1p36.transfer-scan/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_tool": {
            "version": "BindCheck v1.2",
            "freeze_manifest": record("results/raw/D1P-35/freeze-manifest.json"),
            "freeze_payload_sha256": freeze["freeze_payload_sha256"],
            "mismatches_after_scan": frozen_mismatches,
        },
        "counts": {
            "projects": len(records), "analysis_invocations": len(records),
            "supported_analyses": sum(item["analysis"]["status"] == "PASS" for item in records),
            "unsupported_analyses": sum(item["analysis"]["status"] == "UNSUPPORTED" for item in records),
            "warnings": 0, "validations_attempted": 0,
        },
        "projects": records,
        "claim_limits": [
            "UNSUPPORTED is not a miss and is not evidence that a target is safe.",
            "No rule ran to completion and no warning was emitted; therefore there is no warning triage or validation result.",
            "No analyzer, rule, threshold, use-count policy, Solidity extractor, or effect-table file changed after the v1.2 freeze.",
            "Set B was unseen and non-reserved before the recorded v1.2 freeze; Set A is explicitly a reserved second attempt.",
            "No live-chain action, maintainer contact, issue, or pull request occurred.",
        ],
    }
    output = RAW / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": record("results/raw/D1P-36/manifest.json"),
                      "counts": manifest["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
