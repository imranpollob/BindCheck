from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import time
from typing import Any


VERDICTS = {"VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN"}
GRADES = {"E0", "E1", "E2", "E3", "E4"}


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
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"invalid verdict {verdict}")
    if grade not in GRADES:
        raise ValueError(f"invalid evidence grade {grade}")
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
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, str]:
    if any(item["verdict"] == "VIOLATION" for item in results):
        verdict = "VIOLATION"
    elif results and all(item["verdict"] == "VERIFIED_WITHIN_SCOPE" for item in results):
        verdict = "VERIFIED_WITHIN_SCOPE"
    else:
        verdict = "UNKNOWN"
    grades = [item.get("evidence_grade", "E0") for item in results]
    grade = max(grades, key=lambda value: int(value[1:])) if grades else "E0"
    return {"verdict": verdict, "evidence_grade": grade}


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
