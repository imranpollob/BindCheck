from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
import time
from typing import Any

from .common import ROOT, envelope, retain_native, run_command, utc_now
from .solidity_scan import scan_repository, solidity_files


def _slither_python() -> str | None:
    override = os.environ.get("BINDCHECK_STRONG_SLITHER_PYTHON")
    if override and pathlib.Path(override).is_file():
        return override
    slither = shutil.which("slither")
    if not slither:
        return None
    try:
        first = pathlib.Path(slither).resolve().read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return None
    if first.startswith("#!") and pathlib.Path(first[2:]).is_file():
        return first[2:]
    return None


def _consumer_candidates(root: pathlib.Path, cap: int = 8) -> list[pathlib.Path]:
    files, _ = solidity_files(root)
    ranked: list[tuple[int, pathlib.Path]] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        score = 0
        score += 5 if any(token in text for token in ("verifyProof(", ".verify(", "validateProof(")) else 0
        score += 3 if any(token in text for token in (".transfer(", ".transferFrom(", "_mint(", "mint(", ".call{value:")) else 0
        score += 2 if any(token.lower() in text.lower() for token in ("nullifier", "spent", "usedProof")) else 0
        if score:
            ranked.append((score, path))
    return [path for _, path in sorted(ranked, key=lambda item: (-item[0], str(item[1])))[:cap]]


def _run_custom_slither(root: pathlib.Path, native_dir: pathlib.Path, budget_seconds: float) -> dict[str, Any]:
    python = _slither_python()
    candidates = _consumer_candidates(root)
    if python is None:
        return {
            "status": "UNKNOWN",
            "reason": "SLITHER_PYTHON_UNAVAILABLE",
            "targets": [path.relative_to(root).as_posix() for path in candidates],
            "invocations": [],
            "findings": [],
        }
    invocations: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    started = time.monotonic()
    for index, target in enumerate(candidates):
        remaining = budget_seconds - (time.monotonic() - started)
        if remaining <= 0:
            break
        record = run_command(
            [
                python,
                str(ROOT / "baselines" / "strong" / "slither_driver.py"),
                str(target),
                "--root",
                str(root),
            ],
            cwd=ROOT,
            timeout=max(0.1, remaining),
            env={"PYTHONPATH": str(ROOT)},
        )
        retained = retain_native(record, native_dir / "slither", f"target-{index:02d}")
        invocations.append(retained)
        if record["exit_status"] == 0 and not record["timed_out"]:
            try:
                payload = json.loads(record["stdout"])
            except json.JSONDecodeError:
                continue
            for detector in payload.get("detectors", []):
                item = detector.get("additional_fields", {}).get("strong_finding")
                if isinstance(item, dict):
                    copied = dict(item)
                    copied["source"] = "custom-slither-detector"
                    location = copied.get("location")
                    if isinstance(location, dict) and location.get("path"):
                        try:
                            location["path"] = pathlib.Path(location["path"]).resolve().relative_to(root).as_posix()
                        except ValueError:
                            pass
                    findings.append(copied)
    successes = sum(item["exit_status"] == 0 and not item["timed_out"] for item in invocations)
    if not candidates:
        status, reason = "UNKNOWN", "NO_SLITHER_CANDIDATE"
    elif successes:
        status, reason = "completed", None
    elif any(item["timed_out"] for item in invocations):
        status, reason = "UNKNOWN", "SLITHER_TIMEOUT"
    else:
        status, reason = "UNKNOWN", "SLITHER_COMPILE_FAILURE"
    return {
        "status": status,
        "reason": reason,
        "python": python,
        "targets": [path.relative_to(root).as_posix() for path in candidates],
        "invocations": invocations,
        "findings": findings,
    }


def _run_foundry_policy(root: pathlib.Path, native_dir: pathlib.Path, timeout: float) -> dict[str, Any]:
    policy = root / "policy.json"
    harness = root / "test" / "PolicyHarness.t.sol"
    forge = shutil.which("forge")
    pinned_solc = pathlib.Path.home() / ".svm" / "0.8.20" / "solc-0.8.20"
    solc = str(pinned_solc) if pinned_solc.is_file() else None
    if not policy.is_file() or not harness.is_file():
        return {"status": "UNKNOWN", "reason": "POLICY_OR_HARNESS_MISSING", "executed": False, "findings": []}
    if not forge or not solc:
        return {"status": "UNKNOWN", "reason": "FOUNDRY_OR_SOLC_UNAVAILABLE", "executed": False, "findings": []}
    with tempfile.TemporaryDirectory(prefix="bindcheck-strong-foundry-") as temporary:
        temp = pathlib.Path(temporary)
        record = run_command(
            [
                forge, "test", "--root", str(root), "--contracts", ".",
                "--out", str(temp / "out"), "--cache-path", str(temp / "cache"),
                "--offline", "--use", solc, "--match-path", "test/*.t.sol", "--json",
            ],
            cwd=ROOT,
            timeout=timeout,
        )
    retained = retain_native(record, native_dir / "foundry", "policy-harness")
    findings: list[dict[str, Any]] = []
    statuses: list[str] = []
    reasons: list[str] = []
    payload: dict[str, Any] = {}
    if not record["timed_out"]:
        try:
            payload = json.loads(record["stdout"])
        except json.JSONDecodeError:
            payload = {}
        for contract in payload.values() if isinstance(payload, dict) else []:
            for result in contract.get("test_results", {}).values():
                statuses.append(result.get("status"))
                if result.get("reason"):
                    reasons.append(str(result["reason"]))
        policy_reasons = {"unauthorized caller effect", "unauthorized multiplicity or extent"}
        if any(reason in policy_reasons for reason in reasons):
            findings.append({
                "code": "A_FOUNDRY_POLICY_COUNTEREXAMPLE",
                "message": "The same-policy mock-verifier harness committed an effect forbidden by the policy assertion.",
                "location": {"path": "test/PolicyHarness.t.sol", "line": None},
                "facts": {"test_statuses": statuses, "failure_reasons": reasons},
                "source": "same-policy-foundry-harness",
                "evidence_grade": "E1",
            })
        if statuses:
            status, reason = "completed", None
        elif record["exit_status"] == 0:
            status, reason = "UNKNOWN", "FOUNDRY_OUTPUT_UNRESOLVED"
        else:
            status, reason = "UNKNOWN", "FOUNDRY_SETUP_OR_COMPILE_FAILURE"
    elif record["timed_out"]:
        status, reason = "UNKNOWN", "FOUNDRY_TIMEOUT"
    return {
        "status": status,
        "reason": reason,
        "executed": True,
        "invocation": retained,
        "test_statuses": statuses,
        "failure_reasons": reasons,
        "findings": findings,
    }


def analyze_arm_a(root: pathlib.Path, output_dir: pathlib.Path, budget_seconds: float = 120.0) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.monotonic()
    root = root.resolve()
    lexical = scan_repository(root)
    foundry_budget = min(30.0, max(1.0, budget_seconds / 3))
    foundry = _run_foundry_policy(root, output_dir / "native", foundry_budget)
    slither = _run_custom_slither(root, output_dir / "native", max(1.0, budget_seconds - (time.monotonic() - started)))
    findings = [*lexical["findings"], *slither["findings"], *foundry["findings"]]
    stats = lexical["coverage"]["effect_analysis"]
    replay_stats = lexical["coverage"]["replay_analysis"]
    interface_stats = lexical["coverage"]["interface_analysis"]
    supported_interface = bool(interface_stats["verifier_public_counts"] and interface_stats["consumer_vector_lengths"])
    supported = stats["effects"] > 0 or replay_stats["replay_writes"] > 0 or supported_interface
    if findings:
        verdict = "VIOLATION"
    elif supported and not lexical["coverage"]["read_failures"] and not lexical["coverage"]["inventory_capped"]:
        verdict = "VERIFIED_WITHIN_SCOPE"
    else:
        verdict = "UNKNOWN"
    run_status = "completed" if not lexical["coverage"]["read_failures"] else "UNKNOWN"
    coverage = {
        "lexical_fallback": lexical["coverage"],
        "custom_slither": {key: value for key, value in slither.items() if key != "findings"},
        "same_policy_foundry": {key: value for key, value in foundry.items() if key != "findings"},
    }
    return envelope(
        "A", root,
        started_utc=started_utc,
        elapsed_seconds=time.monotonic() - started,
        run_status=run_status,
        findings=findings,
        verdict=verdict,
        coverage=coverage,
        native={"custom_slither": slither, "same_policy_foundry": foundry},
        limitations=[
            "The lexical fallback is a bounded heuristic and does not establish Solidity path semantics.",
            "A custom Slither detector result is E1 screening evidence, not an end-to-end exploit.",
            "Modifiers, proxies, assembly, reentrancy, and unsupported external rollback remain outside this arm.",
            "A same-policy Foundry harness uses a mock verifier and can test consumer policy only; it cannot carry a real-proof claim.",
        ],
    )
