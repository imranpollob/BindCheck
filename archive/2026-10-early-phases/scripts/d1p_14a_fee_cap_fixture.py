#!/usr/bin/env python3
"""Reproducible D1P-14A WarpToad fee-cap fixture runner."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-14A"
SOURCE = RAW / "workspace/source"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
D1P12R = ROOT / "results/raw/D1P-12R"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
HARNESS_TEMPLATE = ROOT / "scripts/fixtures/d1p_14a_fee_cap_fixture.ts"
HARNESS = SOURCE / "backend/test/d1p14a.fixture.ts"
CONFIG_TEMPLATE = ROOT / "scripts/fixtures/d1p_14a_hardhat.config.ts"
CONFIG = SOURCE / "backend/d1p14a.hardhat.config.ts"
PROTOCOL = ROOT / "protocols/d1/d1p-14a-fee-cap.json"
ATTEMPT_LEDGER = RAW / "proof-attempts.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path, base: Path = ROOT) -> dict:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_json(path: Path, default: object) -> object:
    return json.loads(path.read_text()) if path.exists() else default


def process_tree_rss_kib(root_pid: int) -> int:
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,rss="], capture_output=True,
            text=True, check=True, timeout=5,
        ).stdout
        rows = [tuple(map(int, line.split())) for line in output.splitlines()
                if len(line.split()) == 3]
        wanted = {root_pid}
        changed = True
        while changed:
            changed = False
            for pid, ppid, _rss in rows:
                if ppid in wanted and pid not in wanted:
                    wanted.add(pid)
                    changed = True
        return sum(rss for pid, _ppid, rss in rows if pid in wanted)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 extra_env: dict[str, str] | None = None) -> dict:
    LOGS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    stdout_path = LOGS / f"{label}.stdout.txt"
    stderr_path = LOGS / f"{label}.stderr.txt"
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started_at = utc_now()
    started = time.monotonic()
    max_rss = 0
    min_free = shutil.disk_usage(ROOT).free
    timed_out = False
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
            text=True, start_new_session=True,
        )
        while proc.poll() is None:
            max_rss = max(max_rss, process_tree_rss_kib(proc.pid))
            min_free = min(min_free, shutil.disk_usage(ROOT).free)
            if time.monotonic() - started >= timeout:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(1)
        exit_code = proc.wait()
    payload = {
        "schema": "bindcheck.d1p14a.command/v1",
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "wall_seconds": round(time.monotonic() - started, 3),
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "max_process_tree_rss_kib_observed": max_rss,
        "min_free_disk_bytes_observed": min_free,
        "stdout": record(stdout_path, RAW),
        "stderr": record(stderr_path, RAW),
    }
    write_json(RECORDS / f"{label}.json", payload)
    return payload


def require_source() -> None:
    if not (SOURCE / ".git").exists():
        raise SystemExit("D1P-14A isolated source is absent; run --stage setup")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    if head != PIN:
        raise SystemExit(f"wrong WarpToad revision: {head}")


def hardhat_command(*, mine_reverts: bool = False) -> list[str]:
    command = [str(SOURCE / "backend/node_modules/.bin/hardhat")]
    if mine_reverts:
        command.extend(["--config", "d1p14a.hardhat.config.ts"])
    command.extend([
        "test",
        "--network", "edr", "--no-compile", "test/d1p14a.fixture.ts",
    ])
    return command


def stage_setup() -> int:
    if (RAW / "setup.json").exists():
        raise SystemExit("D1P-14A setup evidence already exists; refusing to overwrite it")
    RAW.mkdir(parents=True, exist_ok=True)
    preserve_paths = [
        "reports/D1P-12.md", "reports/D1P-12R.md", "reports/D1P-13.md",
        "metadata/d1/d1p-12-artifact-manifest.json",
        "metadata/d1/d1p-12r-artifact-manifest.json",
        "metadata/d1/d1p-13-artifact-manifest.json",
        "results/raw/D1P-12/preflight.json",
        "results/raw/D1P-12/commands.txt",
        "results/raw/D1P-12R/evidence-manifest.json",
        "results/raw/D1P-13/evidence-manifest.json",
        "results/raw/D1P-12R/honest-proof.json",
    ]
    preservation = [record(ROOT / relative) for relative in preserve_paths]
    resumed_partial_setup = SOURCE.exists()
    if resumed_partial_setup:
        require_source()
        clone = json.loads((RECORDS / "clone-pinned-project.json").read_text())
        checkout = json.loads((RECORDS / "checkout-pinned-project.json").read_text())
        if clone["exit_code"] != 0 or checkout["exit_code"] != 0:
            raise SystemExit("partial setup command records do not show a successful clone and checkout")
    else:
        clone = run_recorded(
            "clone-pinned-project",
            ["git", "clone", "--no-hardlinks", str(D1P12R / "workspace/source"), str(SOURCE)],
            ROOT, 600,
        )
        if clone["exit_code"] != 0:
            return clone["exit_code"] or 1
        checkout = run_recorded(
            "checkout-pinned-project", ["git", "checkout", "--detach", PIN], SOURCE, 300,
        )
        if checkout["exit_code"] != 0:
            return checkout["exit_code"] or 1
    for relative in ("node_modules", "backend/node_modules"):
        link = SOURCE / relative
        target = D1P12R / "workspace/source" / relative
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != target.resolve():
                raise SystemExit(f"unexpected dependency path in partial setup: {link}")
        else:
            link.symlink_to(target, target_is_directory=True)
    if not (SOURCE / "backend/artifacts").exists():
        shutil.copytree(
            D1P12R / "workspace/source/backend/artifacts",
            SOURCE / "backend/artifacts",
        )
    if not (SOURCE / "backend/cache").exists():
        shutil.copytree(
            D1P12R / "workspace/source/backend/cache",
            SOURCE / "backend/cache",
        )
    artifact = SOURCE / "frontend/src/lib/circuits/withdraw.json"
    target_artifact = SOURCE / "backend/circuits/withdraw/target/withdraw.json"
    target_artifact.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, target_artifact)
    shutil.copy2(HARNESS_TEMPLATE, HARNESS)
    shutil.copy2(CONFIG_TEMPLATE, CONFIG)

    d1p11 = json.loads((ROOT / "results/raw/D1P-11/retrieved-source-hashes.json").read_text())
    source_hashes = []
    for item in d1p11["sources"]:
        if item.get("application") != "warp-toad":
            continue
        path = SOURCE / item["path"]
        source_hashes.append({
            "path": item["path"], "expected_sha256": item["sha256"],
            "actual_sha256": sha256(path), "matches": sha256(path) == item["sha256"],
        })
    payload = {
        "schema": "bindcheck.d1p14a.setup/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "host": {
            "platform": platform.platform(), "machine": platform.machine(),
            "python": sys.version.split()[0], "logical_cpus": os.cpu_count(),
            "free_disk_bytes": shutil.disk_usage(ROOT).free,
        },
        "protocol": record(PROTOCOL),
        "preservation_baseline": preservation,
        "source_hashes": source_hashes,
        "source_hashes_all_match": all(item["matches"] for item in source_hashes),
        "workspace": {
            "source": str(SOURCE.relative_to(ROOT)),
            "head": PIN,
            "resumed_after_setup_only_manifest_path_correction": resumed_partial_setup,
            "clone": clone,
            "checkout": checkout,
            "dependency_links": [
                {"path": relative, "target": str((D1P12R / "workspace/source" / relative).relative_to(ROOT))}
                for relative in ("node_modules", "backend/node_modules")
            ],
            "copied_build_products": [
                record(SOURCE / "backend/artifacts/contracts/verifier/WithdrawVerifier.sol/HonkVerifier.json", SOURCE),
                record(SOURCE / "backend/cache/compile-cache.json", SOURCE),
            ],
            "committed_artifact": record(artifact, SOURCE),
            "target_artifact": record(target_artifact, SOURCE),
            "target_artifact_byte_identical": sha256(artifact) == sha256(target_artifact),
            "fixture_template": record(HARNESS_TEMPLATE),
            "fixture_installed": record(HARNESS, SOURCE),
            "execution_config_template": record(CONFIG_TEMPLATE),
            "execution_config_installed": record(CONFIG, SOURCE),
            "tracked_diff_empty": subprocess.run(["git", "diff", "--quiet"], cwd=SOURCE).returncode == 0,
        },
        "bounds": {
            "proof_generation_attempts_maximum": 2,
            "timeout_seconds_each": 1800,
            "parameter_search": False,
            "solver_calls": 0,
            "fork": False,
            "live_chain": False,
        },
    }
    write_json(RAW / "setup.json", payload)
    return 0 if payload["source_hashes_all_match"] and payload["workspace"]["tracked_diff_empty"] else 1


def stage_preflight() -> int:
    require_source()
    output = RAW / "preflight.json"
    if output.exists():
        raise SystemExit("preflight evidence exists; refusing to overwrite")
    result = run_recorded(
        "preflight", hardhat_command(), SOURCE / "backend", 300,
        {"D1P14A_MODE": "preflight", "D1P14A_RESULT": str(output)},
    )
    return result["exit_code"] or 0


def run_proof_fixture(mode: str) -> int:
    require_source()
    attempts = load_json(
        ATTEMPT_LEDGER,
        {"schema": "bindcheck.d1p14a.proof-attempts/v1", "maximum": 2, "attempts": []},
    )
    assert isinstance(attempts, dict)
    prior = attempts["attempts"]
    if len(prior) >= 2:
        raise SystemExit("D1P-14A proof-attempt limit exhausted")
    if mode == "fee-cap":
        if prior:
            raise SystemExit("FC-POS is attempt 1 and cannot run after a consumed attempt")
        result_path = RAW / "fee-cap-execution.json"
        proof_path = RAW / "fc-pos-proof.json"
        extra = {
            "D1P14A_POS": str(RAW / "fc-pos-receipt.json"),
            "D1P14A_NEG": str(RAW / "fc-neg-receipt.json"),
        }
        label = "proof-attempt-1-fc-pos"
        reason = "Generate the new FC-POS honest proof with max_fee below amount and a nonzero in-cap fee."
    else:
        if len(prior) != 1:
            raise SystemExit("zero-fee must be exactly proof attempt 2 after FC-POS")
        result_path = RAW / "zero-fee-execution.json"
        proof_path = RAW / "zero-fee-proof.json"
        extra = {"D1P14A_ZERO": str(RAW / "zero-fee-receipt.json")}
        label = "proof-attempt-2-zero-fee"
        reason = "A distinct proof is required for the supported zero-fee control because fee_factor is proof-bound."
    if result_path.exists() or proof_path.exists():
        raise SystemExit(f"{mode} evidence exists; refusing to regenerate")
    marker = RAW / f"{label}-marker.json"
    marker.unlink(missing_ok=True)
    env = {
        "D1P14A_MODE": mode,
        "D1P14A_RESULT": str(result_path),
        "D1P14A_PROOF": str(proof_path),
        "D1P14A_ATTEMPT_MARKER": str(marker),
        "D1P14A_ATTEMPT_NUMBER": str(len(prior) + 1),
        "D1P14A_ATTEMPT_REASON": reason,
        **extra,
    }
    command = run_recorded(
        label, hardhat_command(mine_reverts=mode == "fee-cap"),
        SOURCE / "backend", 1800, env,
    )
    if marker.exists():
        prior.append({
            "attempt": len(prior) + 1,
            "mode": mode,
            "reason": reason,
            "marker": json.loads(marker.read_text()),
            "command": command,
        })
        attempts["attempts"] = prior
        write_json(ATTEMPT_LEDGER, attempts)
    else:
        write_json(RAW / f"{label}-not-consumed.json", {
            "reason": "fixture ended before the createProof marker",
            "command": command,
        })
    return command["exit_code"] or 0


def stage_fee_cap_resume() -> int:
    """Reuse attempt 1's saved proof; this stage performs no proof generation."""
    require_source()
    attempts = load_json(ATTEMPT_LEDGER, {"attempts": []})
    assert isinstance(attempts, dict)
    if len(attempts.get("attempts", [])) != 1:
        raise SystemExit("fee-cap resume requires exactly one consumed proof attempt")
    source_proof = RAW / "fc-pos-proof.json"
    failed_result = RAW / "fee-cap-execution.json"
    if not source_proof.exists() or not failed_result.exists():
        raise SystemExit("attempt 1 saved proof/failure evidence is absent")
    if json.loads(failed_result.read_text()).get("status") != "FAIL":
        raise SystemExit("resume is only valid for the preserved attempt-1 RPC receipt failure")
    first_resume = RAW / "fee-cap-resumed-execution.json"
    if first_resume.exists():
        if json.loads(first_resume.read_text()).get("status") != "FAIL":
            raise SystemExit("a successful fee-cap resume already exists")
        result_path = RAW / "fee-cap-final-execution.json"
        proof_validation_path = RAW / "fc-pos-proof-reuse-validation-final.json"
        plan_path = RAW / "fee-cap-final-plan.json"
        label = "fee-cap-final-no-proof"
        prior_resume_failure = record(first_resume, RAW)
    else:
        result_path = first_resume
        proof_validation_path = RAW / "fc-pos-proof-reuse-validation.json"
        plan_path = RAW / "fee-cap-resume-plan.json"
        label = "fee-cap-resume-no-proof"
        prior_resume_failure = None
    outputs = [
        result_path, RAW / "fc-pos-receipt.json", RAW / "fc-neg-receipt.json",
        proof_validation_path,
    ]
    if any(path.exists() for path in outputs):
        raise SystemExit("fee-cap resume evidence exists; refusing to overwrite")
    shutil.copy2(HARNESS_TEMPLATE, HARNESS)
    shutil.copy2(CONFIG_TEMPLATE, CONFIG)
    write_json(plan_path, {
        "schema": "bindcheck.d1p14a.resume-plan/v1",
        "created_at_utc": utc_now(),
        "reason": "Attempt 1 produced and verified the real proof, but default Hardhat EDR returned a reverting transaction as an RPC error instead of mining a receipt.",
        "preserved_failure": record(failed_result, RAW),
        "preserved_prior_resume_failure": prior_resume_failure,
        "reused_proof": record(source_proof, RAW),
        "proof_generation_calls": 0,
        "execution_overlay": {
            "path": str(CONFIG_TEMPLATE.relative_to(ROOT)),
            "sha256": sha256(CONFIG_TEMPLATE),
            "only_change": "EDR throwOnTransactionFailures=false; throwOnCallFailures remains true",
            "consumer_source_changed": False,
            "verifier_changed": False,
        },
    })
    result = run_recorded(
        label, hardhat_command(mine_reverts=True),
        SOURCE / "backend", 600,
        {
            "D1P14A_MODE": "fee-cap-resume",
            "D1P14A_RESULT": str(result_path),
            "D1P14A_PROOF": str(proof_validation_path),
            "D1P14A_POS": str(RAW / "fc-pos-receipt.json"),
            "D1P14A_NEG": str(RAW / "fc-neg-receipt.json"),
            "D1P14A_REUSE_PROOF": str(source_proof),
        },
    )
    return result["exit_code"] or 0


def stage_audit() -> int:
    require_source()
    required = [
        "preflight.json", "fc-pos-proof.json",
        "fc-pos-receipt.json", "fc-neg-receipt.json",
        "zero-fee-execution.json", "zero-fee-proof.json", "zero-fee-receipt.json",
        "proof-attempts.json",
    ]
    missing = [relative for relative in required if not (RAW / relative).exists()]
    if missing:
        raise SystemExit(f"missing evidence: {missing}")
    fc_candidates = [
        RAW / "fee-cap-final-execution.json",
        RAW / "fee-cap-resumed-execution.json",
        RAW / "fee-cap-execution.json",
    ]
    successful_fc_path = next(
        (path for path in fc_candidates
         if path.exists() and json.loads(path.read_text()).get("status") == "PASS"),
        None,
    )
    if successful_fc_path is None:
        raise SystemExit("no successful fee-cap execution evidence exists")
    setup = json.loads((RAW / "setup.json").read_text())
    preservation = []
    for item in setup["preservation_baseline"]:
        path = ROOT / item["path"]
        preservation.append({
            **item, "actual_sha256": sha256(path),
            "matches": sha256(path) == item["sha256"],
        })
    first_fc = json.loads((RAW / "fee-cap-execution.json").read_text())
    first_resume_path = RAW / "fee-cap-resumed-execution.json"
    first_resume = json.loads(first_resume_path.read_text()) if first_resume_path.exists() else None
    fc = json.loads(successful_fc_path.read_text())
    pos = json.loads((RAW / "fc-pos-receipt.json").read_text())
    neg = json.loads((RAW / "fc-neg-receipt.json").read_text())
    zero = json.loads((RAW / "zero-fee-receipt.json").read_text())
    attempts = json.loads(ATTEMPT_LEDGER.read_text())
    checks = {
        "preflight_passed": json.loads((RAW / "preflight.json").read_text())["status"] == "PASS",
        "attempt_1_result_preserved": first_fc["status"] in ("PASS", "FAIL"),
        "optional_no_proof_diagnostic_preserved": first_resume is None or first_resume["status"] in ("PASS", "FAIL"),
        "fee_cap_fixture_passed": fc["status"] == "PASS",
        "zero_fee_fixture_passed": json.loads((RAW / "zero-fee-execution.json").read_text())["status"] == "PASS",
        "two_proof_attempts_exactly": len(attempts["attempts"]) == 2,
        "no_attempt_timed_out": all(not item["command"]["timed_out"] for item in attempts["attempts"]),
        "same_fc_proof": pos["proofSha256"] == neg["proofSha256"],
        "same_fc_calldata": pos["calldataSha256"] == neg["calldataSha256"],
        "positive_max_fee_below_amount": int(pos["fees"]["maxFee"]) < int(pos["fees"]["amount"]),
        "positive_fee_nonzero_within_cap": bool(pos["fees"]["nonzeroAndWithinCap"]),
        "positive_conservation": bool(pos["effects"]["conserved"]),
        "positive_nullifier_consumed": bool(pos["effects"]["nullifierConsumed"]),
        "negative_cap_exceeded": bool(neg["capExceeded"]),
        "negative_reverted": neg["receipt"]["status"] == "reverted",
        "negative_consumer_state_unchanged": bool(neg["consumerState"]["unchanged"]),
        "zero_no_fee_mint": bool(zero["effects"]["noFeeMint"]),
        "zero_conservation": bool(zero["effects"]["conserved"]),
        "zero_nullifier_consumed": bool(zero["effects"]["nullifierConsumed"]),
        "prior_evidence_unchanged": all(item["matches"] for item in preservation),
    }
    payload = {
        "schema": "bindcheck.d1p14a.audit/v1",
        "created_at_utc": utc_now(),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "preservation": preservation,
        "source": {
            "head": PIN,
            "tracked_diff_empty": subprocess.run(["git", "diff", "--quiet"], cwd=SOURCE).returncode == 0,
            "status_short": subprocess.run(
                ["git", "status", "--short"], cwd=SOURCE,
                capture_output=True, text=True, check=True,
            ).stdout.splitlines(),
        },
        "successful_fee_cap_execution": record(successful_fc_path, RAW),
        "execution_bounds": {
            "solver_calls": 0,
            "joint_encoder": False,
            "proof_generation_attempts": len(attempts["attempts"]),
            "proof_generation_attempts_maximum": 2,
            "per_attempt_timeout_seconds": 1800,
            "fork": False,
            "live_chain": False,
            "old_four_gib_cap_applied": False,
            "unsafe_resource_exhaustion": False,
        },
    }
    write_json(RAW / "audit.json", payload)
    return 0 if payload["all_checks_pass"] and payload["source"]["tracked_diff_empty"] else 1


def stage_finalize() -> int:
    required = [
        "setup.json", "preflight.json", "proof-attempts.json",
        "fee-cap-execution.json", "fc-pos-proof.json", "fc-pos-receipt.json",
        "fc-neg-receipt.json", "zero-fee-execution.json", "zero-fee-proof.json",
        "zero-fee-receipt.json", "audit.json",
    ]
    paths = [RAW / relative for relative in required]
    optional = [
        "fee-cap-resume-plan.json", "fee-cap-resumed-execution.json",
        "fee-cap-final-plan.json", "fee-cap-final-execution.json",
        "fc-pos-proof-reuse-validation.json",
        "fc-pos-proof-reuse-validation-final.json",
    ]
    paths.extend(RAW / relative for relative in optional if (RAW / relative).exists())
    paths.extend(sorted(RECORDS.glob("*.json")))
    paths.extend(sorted(LOGS.glob("*.txt")))
    paths.extend(sorted(RAW.glob("*-marker.json")))
    records = [record(path, RAW) for path in sorted(set(paths))]
    write_json(RAW / "evidence-manifest.json", {
        "schema": "bindcheck.d1p14a.raw-evidence-manifest/v1",
        "created_at_utc": utc_now(),
        "pinned_revision": PIN,
        "records": records,
        "record_count": len(records),
        "regular_file_bytes": sum(item["bytes"] for item in records),
        "workspace_exclusion": "The isolated Git checkout, dependency links, copied Hardhat cache and bulk artifacts are reproducible workspace state and are not recursively included.",
    })
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", required=True,
        choices=("setup", "preflight", "fee-cap", "fee-cap-resume", "zero-fee", "audit", "finalize"),
    )
    args = parser.parse_args()
    stages = {
        "setup": stage_setup,
        "preflight": stage_preflight,
        "fee-cap": lambda: run_proof_fixture("fee-cap"),
        "fee-cap-resume": stage_fee_cap_resume,
        "zero-fee": lambda: run_proof_fixture("zero-fee"),
        "audit": stage_audit,
        "finalize": stage_finalize,
    }
    return stages[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
