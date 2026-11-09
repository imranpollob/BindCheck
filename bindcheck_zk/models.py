from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import time
from typing import Any


VERDICTS = {"VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN"}
GRADES = {"E0", "E1", "E2", "E3", "E4"}
APPLICABILITIES = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
UNKNOWN_REASON_CODES = {
    "MISSING_ARTIFACT",
    "BUILD_FAILURE",
    "AMBIGUOUS_CORRESPONDENCE",
    "UNSUPPORTED_CONSTRUCT",
    "CAP_OR_TIMEOUT",
    "OTHER",
}


def unknown_reason_code(reason: str) -> str:
    """Map detailed diagnostics to the fixed, reportable UNKNOWN taxonomy."""
    normalized = reason.upper()
    if normalized in {"COMPILED_RELATION_UNAVAILABLE", "COMPILED_RELATION_PARSE_FAILED"}:
        return "BUILD_FAILURE"
    if any(word in normalized for word in ("TIMEOUT", "MAX_FILES", "CAP_EXCEEDED", "CAP_OR_")):
        return "CAP_OR_TIMEOUT"
    if any(word in normalized for word in ("BUILD", "COMPILE", "REGENERATION_FAILED")) or normalized == "CIRCUIT_INTERFACE_INCOMPLETE":
        return "BUILD_FAILURE"
    if any(word in normalized for word in ("AMBIGUOUS", "CORRESPONDENCE", "MEANING_UNRESOLVED")):
        return "AMBIGUOUS_CORRESPONDENCE"
    if any(word in normalized for word in ("ARTIFACT_MISSING", "MISSING_ARTIFACT", "NOT_FOUND")):
        return "MISSING_ARTIFACT"
    if any(word in normalized for word in (
        "UNSUPPORTED", "PARSE_INCOMPLETE", "HELPER_UNRESOLVED",
        "EXPRESSION_UNRESOLVED", "DYNAMIC_PUBLIC_INPUT_LENGTH_UNRESOLVED",
        "UNRESOLVED_CONSUMER", "SCREEN_ONLY", "POSITION_UNRESOLVED",
    )):
        return "UNSUPPORTED_CONSTRUCT"
    return "OTHER"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def location(path: str | None, line: int | None = None, column: int | None = None) -> dict[str, Any] | None:
    if path is None:
        return None
    result: dict[str, Any] = {"path": path}
    if line is not None:
        result["line"] = line
    if column is not None:
        result["column"] = column
    return result


def result(
    pattern: str,
    verdict: str,
    reason: str,
    message: str,
    *,
    grade: str = "E1",
    where: dict[str, Any] | None = None,
    facts: list[dict[str, Any]] | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
    applicability: str = "APPLICABLE",
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"invalid verdict {verdict}")
    if grade not in GRADES:
        raise ValueError(f"invalid evidence grade {grade}")
    if applicability not in APPLICABILITIES:
        raise ValueError(f"invalid applicability {applicability}")
    return {
        "pattern": pattern,
        "verdict": verdict,
        "evidence_grade": grade,
        "reason": reason,
        "message": message,
        "location": where,
        "facts": facts or [],
        "assumptions": assumptions or [],
        "limitations": limitations or [],
        "applicability": applicability,
        "unknown_reason_code": unknown_reason_code(reason) if verdict == "UNKNOWN" else None,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, str]:
    applicable = [item for item in results if item.get("applicability", "APPLICABLE") == "APPLICABLE"]
    if applicable:
        applicability = "APPLICABLE"
    elif results and all(item.get("applicability") == "NOT_APPLICABLE" for item in results):
        applicability = "NOT_APPLICABLE"
    else:
        applicability = "UNKNOWN"
    if any(item["verdict"] == "VIOLATION" for item in applicable):
        verdict = "VIOLATION"
    elif applicable and all(item["verdict"] == "VERIFIED_WITHIN_SCOPE" for item in applicable):
        verdict = "VERIFIED_WITHIN_SCOPE"
    else:
        verdict = "UNKNOWN"
    grades = [item.get("evidence_grade", "E0") for item in results]
    grade = max(grades, key=lambda value: int(value[1:])) if grades else "E0"
    return {"verdict": verdict, "evidence_grade": grade, "applicability": applicability}


@dataclasses.dataclass
class Budget:
    seconds: float
    started: float = dataclasses.field(default_factory=time.monotonic)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def remaining(self) -> float:
        return max(0.0, self.seconds - self.elapsed)

    def check(self) -> None:
        if self.remaining <= 0:
            raise TimeoutError(f"analysis exceeded {self.seconds:.3f}s run budget")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
