#!/usr/bin/env python3
"""Run the unscored D2-06B Foundry same-policy construction smoke.

The runner deliberately accepts only the exposed pilot cases declared in the
Step-6b protocol.  It preserves native output and normalizes only invariant
names and native PASS/FAIL tokens; it never creates Gate A score classes or a
two-sided diagnosis.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-06b-comparator-smoke-v1.json"
DEFAULT_INVENTORY = ROOT / "docs/evaluation/d2-06b-comparator-inventory-v1.json"
DEFAULT_OUT = ROOT / "results/raw/D2-06B"
PINNED_BACKEND = ROOT / "results/raw/D1P-19/workspace/pinned-source/backend"
DEPENDENCY_SOURCE = ROOT / "results/raw/D1P-32/warptoad-policy-pinned/node_modules"
HARNESS = ROOT / "baselines/foundry/test/WarpToadPolicy.t.sol"
TEST_SOL = ROOT / "results/raw/D1P-22/harnesses/payy-policy/lib/forge-std/src/Test.sol"
REQUIRED_COMPARATORS = {
    "CMP-NOIR",
    "CMP-SLITHER",
    "CMP-MYTHRIL",
    "CMP-FOUNDRY",
    "CMP-ECHIDNA",
    "CMP-ZKAP",
    "CMP-CIVER",
    "CMP-CCC-CHECK",
    "CMP-PICUS",
    "CMP-SMARTAXE",
    "CMP-ELSA",
}
UNSCORED_STATUS = "CONSTRUCTION_SMOKE_ONLY_UNSEALED_DO_NOT_SCORE"
INVARIANT_PATTERN = re.compile(
    r"^\[(PASS|FAIL)(?::[^]]+)?\]\s+(invariant_[a-z0-9_]+)\s*$"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    """Hash file names and contents for a deterministic local input tree."""
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = child.relative_to(path).as_posix().encode()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(child)))
        digest.update(b"\0")
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def nonblank_noncomment_lines(path: Path) -> int:
    count = 0
    for raw in path.read_text().splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith(("#", "//")):
            count += 1
    return count


def harness_invariants(path: Path = HARNESS) -> list[str]:
    return sorted(set(re.findall(r"function\s+(invariant_[a-z0-9_]+)\s*\(", path.read_text())))


def parse_foundry_invariants(output: str) -> dict[str, str]:
    """Retain the last native PASS/FAIL token for each named invariant."""
    outcomes: dict[str, str] = {}
    for line in output.splitlines():
        match = INVARIANT_PATTERN.match(line.strip())
        if match:
            outcomes[match.group(2)] = match.group(1)
    return dict(sorted(outcomes.items()))


def resolve_from_root(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def validate_protocol(protocol: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    if protocol.get("status") != UNSCORED_STATUS:
        raise ValueError("protocol must remain an unscored construction smoke")
    if protocol.get("research_verdict") != "UNKNOWN":
        raise ValueError("research verdict must remain UNKNOWN")
    boundary = protocol.get("execution_boundary", {})
    if boundary.get("scored_execution_authorized") is not False:
        raise ValueError("scored execution must be false")
    if boundary.get("step_7_seal_present") is not False:
        raise ValueError("Step 7 seal must not be asserted by Step 6b")
    independence = protocol["same_policy"]["independence"]
    if independence.get("human_policy_author_status") != "UNRESOLVED":
        raise ValueError("missing human policy author must stay unresolved")
    if independence.get("different_human_reviewer_status") != "UNRESOLVED":
        raise ValueError("missing distinct human reviewer must stay unresolved")

    obligations = protocol["same_policy"]["obligations"]
    declared = sorted(item["invariant"] for item in obligations)
    implemented = harness_invariants()
    if declared != implemented:
        raise ValueError(f"policy/harness invariant mismatch: {declared} != {implemented}")
    if len(protocol.get("smoke_cases", [])) != 2:
        raise ValueError("construction smoke must contain exactly the two declared pilot cases")

    toolchain = protocol["toolchain"]
    checked_paths: list[dict[str, str]] = []
    for key in ("forge", "solc"):
        entry = toolchain[key]
        path = resolve_from_root(entry["path"])
        observed = sha256(path)
        if observed != entry["sha256"]:
            raise ValueError(f"{key} hash mismatch: {observed} != {entry['sha256']}")
        checked_paths.append({"role": key, "path": entry["path"], "sha256": observed})
    observed_harness = sha256(HARNESS)
    expected_harness = protocol["same_policy"]["implementation"]["sha256"]
    if observed_harness != expected_harness:
        raise ValueError(f"harness hash mismatch: {observed_harness} != {expected_harness}")
    if sha256(TEST_SOL) != toolchain["forge_std"]["test_sol_sha256"]:
        raise ValueError("forge-std Test.sol hash mismatch")

    for case in protocol["smoke_cases"]:
        source = resolve_from_root(case["source_path"])
        observed = sha256(source)
        if observed != case["source_sha256"]:
            raise ValueError(f"{case['id']} source hash mismatch")
    for transcript in protocol["historical_native_transcripts"]:
        path = resolve_from_root(transcript["path"])
        if sha256(path) != transcript["sha256"]:
            raise ValueError(f"historical transcript hash mismatch: {transcript['path']}")

    if inventory.get("status") != "CONSTRUCTION_INVENTORY_UNSEALED_DO_NOT_SCORE":
        raise ValueError("inventory must remain unsealed and unscored")
    inventory_ids = {item["id"] for item in inventory.get("comparators", [])}
    if inventory_ids != REQUIRED_COMPARATORS:
        raise ValueError(f"comparator inventory mismatch: {sorted(inventory_ids)}")
    elsa = next(item for item in inventory["comparators"] if item["id"] == "CMP-ELSA")
    if elsa["arms"].get("llm_supplement") != "NOT_SELECTED":
        raise ValueError("ELSA/LLM supplement must not be selected by Step 6b")

    return {
        "declared_invariants": declared,
        "checked_tool_paths": checked_paths,
        "comparator_ids": sorted(inventory_ids),
    }


def foundry_config(protocol: dict[str, Any]) -> str:
    solc = resolve_from_root(protocol["toolchain"]["solc"]["path"])
    forge_std = resolve_from_root(protocol["toolchain"]["forge_std"]["path"])
    config = protocol["smoke_configuration"]
    fail_on_revert = "true" if config["fail_on_revert"] else "false"
    return f'''[profile.default]
src = "contracts"
test = "test"
out = "out"
cache_path = "cache"
solc = "{solc}"
optimizer = true
optimizer_runs = 200
offline = true
remappings = [
  "forge-std/={forge_std}/",
  "poseidon-solidity/=node_modules/poseidon-solidity/",
  "@zk-kit/=node_modules/@zk-kit/",
  "@openzeppelin/=node_modules/@openzeppelin/"
]

[invariant]
runs = {config['runs']}
depth = {config['depth']}
fail_on_revert = {fail_on_revert}
'''


def stage_case(workspace: Path, case: dict[str, Any], config_text: str) -> None:
    shutil.copytree(PINNED_BACKEND / "contracts", workspace / "contracts")
    shutil.copytree(DEPENDENCY_SOURCE, workspace / "node_modules")
    (workspace / "test").mkdir(parents=True)
    shutil.copy2(HARNESS, workspace / "test/WarpToadPolicy.t.sol")
    source = resolve_from_root(case["source_path"])
    shutil.copy2(source, workspace / "contracts/core/WarpToadCore.sol")
    (workspace / "foundry.toml").write_text(config_text)


def run_native_case(
    protocol: dict[str, Any],
    case: dict[str, Any],
    workspace: Path,
    case_out: Path,
) -> dict[str, Any]:
    forge = resolve_from_root(protocol["toolchain"]["forge"]["path"])
    smoke = protocol["smoke_configuration"]
    command = [
        str(forge),
        "test",
        "--match-contract",
        "WarpToadPolicyInvariant",
        "-vv",
        "--fuzz-seed",
        smoke["seed"],
        "--invariant-workers",
        str(smoke["workers"]),
    ]
    environment = {
        **os.environ,
        "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1",
        "FOUNDRY_OFFLINE": "true",
    }
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=smoke["wall_seconds_per_case"],
            check=False,
            env=environment,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code: int | None = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        exit_code = None
    elapsed = round(time.monotonic() - started, 6)
    ended_utc = datetime.now(timezone.utc).isoformat()

    case_out.mkdir(parents=True)
    stdout_path = case_out / "native.stdout.txt"
    stderr_path = case_out / "native.stderr.txt"
    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)
    native_outcomes = parse_foundry_invariants(stdout + "\n" + stderr)
    declared = [item["invariant"] for item in protocol["same_policy"]["obligations"]]
    missing = sorted(set(declared) - set(native_outcomes))
    failed = sorted(name for name, status in native_outcomes.items() if status == "FAIL")
    expected_failed = sorted(case["expected_native_failed_invariants_for_adapter_self_check"])
    adapter_self_check = (
        not timed_out
        and not missing
        and failed == expected_failed
        and all(status in {"PASS", "FAIL"} for status in native_outcomes.values())
    )
    obligation_by_invariant = {
        item["invariant"]: item for item in protocol["same_policy"]["obligations"]
    }
    normalized_reports = []
    for name in failed:
        obligation = obligation_by_invariant[name]
        normalized_reports.append({
            "native_invariant": name,
            "native_status": "FAIL",
            "policy_obligation_id": obligation["id"],
            "policy_class": obligation["class"],
            "highest_evidence_grade": "E1",
            "source_location": None,
            "producer_explanation": None,
            "consumer_explanation": None,
            "two_sided_diagnosis": None,
            "gate_a_outcome": None,
        })

    record = {
        "schema": "bindcheck.d2.step6b-native-smoke/v1",
        "status": UNSCORED_STATUS,
        "case_id": case["id"],
        "exposure": case["exposure"],
        "source": {
            "path": case["source_path"],
            "sha256": case["source_sha256"],
        },
        "command": command,
        "working_directory": str(workspace),
        "started_at_utc": started_utc,
        "ended_at_utc": ended_utc,
        "elapsed_seconds": elapsed,
        "timeout_seconds": smoke["wall_seconds_per_case"],
        "timed_out": timed_out,
        "exit_code": exit_code,
        "native_stdout": {
            "path": str(stdout_path.relative_to(case_out.parents[1])),
            "bytes": stdout_path.stat().st_size,
            "sha256": sha256(stdout_path),
        },
        "native_stderr": {
            "path": str(stderr_path.relative_to(case_out.parents[1])),
            "bytes": stderr_path.stat().st_size,
            "sha256": sha256(stderr_path),
        },
        "native_invariants": native_outcomes,
        "missing_native_invariants": missing,
        "failed_native_invariants": failed,
        "expected_failed_invariants_for_adapter_self_check": expected_failed,
        "adapter_self_check": "PASS" if adapter_self_check else "FAIL",
        "normalized_failed_invariant_reports": normalized_reports,
        "highest_evidence_grade": "E1" if failed else "E0",
        "evidence_ceiling": "E1",
        "comparison_outcome": None,
        "safety_conclusion": None,
        "claim_limit": case["claim_limit"],
    }
    write_json(case_out / "command-and-normalized-result.json", record)
    return record


def write_checksums(out: Path) -> None:
    checksum_path = out / "checksums.sha256"
    rows = []
    for path in sorted(item for item in out.rglob("*") if item.is_file()):
        if path == checksum_path:
            continue
        rows.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    checksum_path.write_text("\n".join(rows) + "\n")


def execute(protocol_path: Path, inventory_path: Path, out: Path) -> dict[str, Any]:
    protocol = read_json(protocol_path)
    inventory = read_json(inventory_path)
    validation = validate_protocol(protocol, inventory)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite Step-6b evidence: {out}")
    out.mkdir(parents=True)
    config_text = foundry_config(protocol)
    (out / "foundry-smoke.toml").write_text(config_text)

    input_manifest = {
        "schema": "bindcheck.d2.step6b-input-manifest/v1",
        "status": UNSCORED_STATUS,
        "protocol": {
            "path": str(protocol_path.relative_to(ROOT)),
            "sha256": sha256(protocol_path),
        },
        "inventory": {
            "path": str(inventory_path.relative_to(ROOT)),
            "sha256": sha256(inventory_path),
        },
        "harness": {
            "path": str(HARNESS.relative_to(ROOT)),
            "sha256": sha256(HARNESS),
            "tree_role": "pre-existing independently documented policy implementation",
        },
        "pinned_backend_contracts": {
            "path": str((PINNED_BACKEND / "contracts").relative_to(ROOT)),
            "tree_sha256": tree_sha256(PINNED_BACKEND / "contracts"),
        },
        "dependency_tree": {
            "path": str(DEPENDENCY_SOURCE.relative_to(ROOT)),
            "tree_sha256": tree_sha256(DEPENDENCY_SOURCE),
        },
        "tool_validation": validation,
        "smoke_cases": [
            {
                "id": case["id"],
                "path": case["source_path"],
                "sha256": case["source_sha256"],
            }
            for case in protocol["smoke_cases"]
        ],
    }
    write_json(out / "input-manifest.json", input_manifest)
    write_json(out / "environment.json", {
        "schema": "bindcheck.d2.step6b-environment/v1",
        "status": UNSCORED_STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "network_calls_permitted": 0,
        "memory_limit_mib": protocol["smoke_configuration"]["memory_mib"],
        "memory_limit_status": protocol["smoke_configuration"]["memory_limit_status"],
        "scientific_retries": 0,
        "invocation": [sys.executable, *sys.argv],
    })

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bindcheck-d2-06b-") as temporary:
        temporary_root = Path(temporary)
        for case in protocol["smoke_cases"]:
            workspace = temporary_root / case["id"]
            stage_case(workspace, case, config_text)
            results.append(run_native_case(protocol, case, workspace, out / "cases" / case["id"]))

    smoke_pass = all(item["adapter_self_check"] == "PASS" for item in results)
    summary = {
        "schema": "bindcheck.d2.step6b-smoke-summary/v1",
        "status": UNSCORED_STATUS,
        "research_verdict": "UNKNOWN",
        "scored": False,
        "step_7_seal_used": False,
        "case_count": len(results),
        "adapter_smoke_status": "PASS" if smoke_pass else "FAIL",
        "cases": [
            {
                "case_id": item["case_id"],
                "exit_code": item["exit_code"],
                "timed_out": item["timed_out"],
                "failed_native_invariants": item["failed_native_invariants"],
                "missing_native_invariants": item["missing_native_invariants"],
                "adapter_self_check": item["adapter_self_check"],
                "highest_evidence_grade": item["highest_evidence_grade"],
                "elapsed_seconds": item["elapsed_seconds"],
            }
            for item in results
        ],
        "gate_a_outcomes": [],
        "target_detection_denominator": None,
        "safe_control_denominator": None,
        "human_policy_author_status": protocol["same_policy"]["independence"]["human_policy_author_status"],
        "different_human_reviewer_status": protocol["same_policy"]["independence"]["different_human_reviewer_status"],
        "step_7_eligibility": protocol["same_policy"]["independence"]["step_7_eligibility"],
        "claim_limit": "This is runner/adapter construction evidence on exposed material, not a comparison result."
    }
    write_json(out / "smoke-summary.json", summary)

    test_path = ROOT / "tests/test_d2_step6b_same_policy_smoke.py"
    effort = {
        "schema": "bindcheck.d2.step6b-effort/v1",
        "status": UNSCORED_STATUS,
        "historical_harness": protocol["effort_accounting"]["historical_shared_harness"],
        "step_6b_measured_artifact_counts": {
            "policy_obligations": len(protocol["same_policy"]["obligations"]),
            "pilot_cases": len(protocol["smoke_cases"]),
            "runner_nonblank_noncomment_lines": nonblank_noncomment_lines(Path(__file__)),
            "test_nonblank_noncomment_lines": nonblank_noncomment_lines(test_path),
            "protocol_nonblank_lines": sum(bool(line.strip()) for line in protocol_path.read_text().splitlines()),
            "inventory_nonblank_lines": sum(bool(line.strip()) for line in inventory_path.read_text().splitlines()),
        },
        "step_6b_human": {
            "policy_author_minutes": None,
            "policy_review_minutes": None,
            "adapter_review_minutes": None,
            "adjudication_minutes": None,
            "reason": "No independently timed human session or review occurred; zero is not imputed."
        },
        "step_6b_agent": {
            "artifact_authoring": "AI-agent-assisted",
            "active_minutes": None,
            "correction_count": None,
            "reason": "Agent activity was not independently timed or correction-coded; no human-time saving is inferred."
        },
        "machine_cases": [
            {
                "case_id": item["case_id"],
                "elapsed_seconds": item["elapsed_seconds"],
                "exit_code": item["exit_code"],
                "timed_out": item["timed_out"],
            }
            for item in results
        ],
    }
    write_json(out / "effort.json", effort)
    write_checksums(out)
    if not smoke_pass:
        raise RuntimeError("native runner/output adapter smoke did not match the predeclared parser expectations")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    protocol_path = args.protocol.resolve()
    inventory_path = args.inventory.resolve()
    protocol = read_json(protocol_path)
    inventory = read_json(inventory_path)
    validation = validate_protocol(protocol, inventory)
    if args.validate_only:
        print(json.dumps({"validation": "PASS", **validation}, indent=2, sort_keys=True))
        return 0
    summary = execute(protocol_path, inventory_path, args.out.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
