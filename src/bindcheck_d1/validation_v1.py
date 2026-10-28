"""Evidence-ordered BindCheck warning validation.

Plans are data, not rule-engine branches.  This lets the validator record
manual route registration and distinguish fresh execution from automatic
checks over preserved prior evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


SCHEMA = "bindcheck.validation-result.v1"
LEVELS = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get(value: Any, dotted: str) -> Any:
    for part in dotted.split(".") if dotted else []:
        if isinstance(value, list):
            value = value[int(part)]
        else:
            value = value[part]
    return value


def _check(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    path = Path(check["path"])
    if not path.is_absolute():
        path = root / path
    record: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        record.update({"pass": False, "reason": "missing evidence file"})
        return record
    record.update({"sha256": _sha256(path), "bytes": path.stat().st_size})
    if "sha256" in check and check["sha256"] != record["sha256"]:
        record.update({"pass": False, "reason": "sha256 mismatch"})
        return record
    if "json_path" in check:
        try:
            observed = _get(json.loads(path.read_text()), check["json_path"])
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            record.update({"pass": False, "reason": f"JSON check failed: {exc}"})
            return record
        record["json_path"] = check["json_path"]
        record["observed"] = observed
        if "equals" in check:
            record["pass"] = observed == check["equals"]
        elif check.get("truthy"):
            record["pass"] = bool(observed)
        else:
            record["pass"] = True
    elif "contains" in check:
        record["pass"] = check["contains"] in path.read_text(errors="replace")
    else:
        record["pass"] = path.stat().st_size > 0
    if not record["pass"]:
        record["reason"] = "evidence predicate false"
    return record


def select_warning(path_selector: str) -> tuple[Path, dict[str, Any]]:
    if "#" in path_selector:
        raw_path, wanted = path_selector.rsplit("#", 1)
    else:
        raw_path, wanted = path_selector, None
    path = Path(raw_path)
    document = json.loads(path.read_text())
    if document.get("schema") in {"bindcheck.static-analysis.v1", "bindcheck.static-analysis.v1.1"}:
        warnings = document["warnings"]
        if wanted:
            matches = [warning for warning in warnings if warning["id"] == wanted]
            if len(matches) != 1:
                raise ValueError(f"warning selector {wanted!r} matched {len(matches)} warnings")
            return path, matches[0]
        if len(warnings) != 1:
            raise ValueError("analysis contains multiple warnings; use analysis.json#W001")
        return path, warnings[0]
    if document.get("rule") and document.get("target_identity"):
        return path, document
    raise ValueError("input is neither a BindCheck analysis nor a standalone warning")


def validate(path_selector: str, index_path: Path, repository: Path) -> dict[str, Any]:
    started = time.monotonic()
    warning_path, warning = select_warning(path_selector)
    index = json.loads(index_path.read_text())
    identity = warning["target_identity"]
    routes = [route for route in index["routes"] if all(
        identity.get(key) == value for key, value in route["match"].items()
    )]
    stages = [{
        "name": "static_warning", "evidence_level": "E1", "status": "PASS",
        "mode": "fresh", "checks": [{"path": str(warning_path.resolve()), "pass": True}],
    }]
    if not routes:
        return {
            "schema": SCHEMA, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "warning": warning, "route": None, "stages": stages, "highest_evidence_level": "E1",
            "manual_steps": 0, "status": "NO_VALIDATION_ROUTE",
            "runtime_seconds": round(time.monotonic() - started, 6),
        }
    if len(routes) != 1:
        raise ValueError(f"validation route identity is ambiguous ({len(routes)} matches)")
    route = routes[0]
    preparation = None
    if route.get("prepare"):
        plan = route["prepare"]
        sentinel = repository / plan["sentinel"]
        if sentinel.is_file():
            preparation = {
                "status": "REUSED_CURRENT_NAMESPACE", "sentinel": str(sentinel),
                "command_executed": False,
            }
        else:
            for output in plan.get("outputs", []):
                (repository / output).parent.mkdir(parents=True, exist_ok=True)
            environment = os.environ.copy()
            environment.update({key: str(repository / value) if not Path(value).is_absolute() else value
                                for key, value in plan.get("env", {}).items()})
            command_started = time.monotonic()
            completed = subprocess.run(
                plan["argv"], cwd=repository / plan["cwd"], env=environment,
                capture_output=True, text=True, timeout=plan.get("timeout_seconds", 1800),
            )
            preparation = {
                "status": "PASS" if completed.returncode == 0 and sentinel.is_file() else "FAIL",
                "sentinel": str(sentinel), "command_executed": True,
                "argv": plan["argv"], "cwd": str(repository / plan["cwd"]),
                "exit_code": completed.returncode,
                "wall_seconds": round(time.monotonic() - command_started, 6),
                "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:],
            }
            if preparation["status"] != "PASS":
                return {
                    "schema": SCHEMA, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "warning": warning, "route": {"id": route["id"]}, "preparation": preparation,
                    "failed_routes": route.get("failed_routes", []), "stages": stages,
                    "highest_evidence_level": "E1", "manual_steps": route["manual_steps"],
                    "manual_inputs": route["manual_inputs"], "status": "PREPARATION_FAILED",
                    "runtime_seconds": round(time.monotonic() - started, 6),
                }
    highest = "E1"
    blocked = False
    alternatives = []
    for attempt in route.get("failed_routes", []):
        alternatives.append(dict(attempt))
    for stage in route["stages"]:
        checks = [_check(repository, check) for check in stage["checks"]]
        status = "PASS" if checks and all(check["pass"] for check in checks) else "FAIL"
        record = {
            "name": stage["name"], "evidence_level": stage["evidence_level"],
            "mode": stage["mode"], "status": status, "checks": checks,
            "explanation": stage["explanation"],
        }
        stages.append(record)
        if status == "PASS" and not blocked:
            if LEVELS[stage["evidence_level"]] > LEVELS[highest]:
                highest = stage["evidence_level"]
        else:
            blocked = True
            break
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": warning,
        "route": {"id": route["id"], "classification": route["classification"],
                  "fresh_execution": route["fresh_execution"]},
        "preparation": preparation,
        "failed_routes": alternatives,
        "stages": stages,
        "highest_evidence_level": highest,
        "manual_steps": route["manual_steps"],
        "manual_inputs": route["manual_inputs"],
        "status": "PASS" if not blocked else "FAIL",
        "scope_note": route["scope_note"],
        "runtime_seconds": round(time.monotonic() - started, 6),
    }


def readable(result: dict[str, Any]) -> str:
    lines = [f"BindCheck validation: {result['warning']['id']} {result['warning']['rule']}",
             f"  status: {result['status']}  highest: {result['highest_evidence_level']}",
             f"  manual steps: {result['manual_steps']}  runtime: {result['runtime_seconds']:.3f}s"]
    if result.get("route"):
        lines.append(f"  route: {result['route']['id']} ({result['route']['classification']})")
    for stage in result["stages"]:
        lines.append(f"  {stage['name']}: {stage['status']} [{stage['evidence_level']}, {stage['mode']}]")
    if result.get("scope_note"):
        lines.append(f"  Note: {result['scope_note']}")
    return "\n".join(lines)
