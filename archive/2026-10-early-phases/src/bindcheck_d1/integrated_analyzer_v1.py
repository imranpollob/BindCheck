"""Integrated BindCheck development analysis.

This module composes the audited static analyzer (including ``R-EXTENT``)
with the separately implemented typed role analysis (``R-ROLE``).  It does
not add a detection rule.  Its purpose is to make component support gates,
provenance, warning identity, and the research-contract outcome explicit in
one machine-readable record.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from .role_binding import RoleBindingUnsupported, analyze_role_binding
from .static_analyzer_v1 import analyze as analyze_static


SCHEMA = "bindcheck.integrated-analysis.v1"
_REMOVED = object()


def _source_location_key(key: object) -> bool:
    """Return whether ``key`` names source-coordinate metadata.

    Warning evidence carries several generations of source provenance.  The
    spelling is not uniform (for example ``effect_location``, ``sourceSpan``
    and ``start_line``), so normalize separators and camel case before
    classifying it.  Generic semantic ``offset``, ``range`` and ``position``
    fields are deliberately retained; only their explicitly source-qualified
    forms are coordinates rather than binding evidence.
    """
    if not isinstance(key, str):
        return False
    snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    snake = re.sub(r"[^A-Za-z0-9]+", "_", snake).strip("_").lower()
    parts = set(snake.split("_")) if snake else set()
    if parts.intersection({"location", "locations", "span", "spans"}):
        return True
    if snake in {"line", "lineno", "line_number", "column", "col", "colno",
                 "column_number", "loc"}:
        return True
    if parts.intersection({
        "line", "lines", "lineno", "column", "columns", "col", "colno",
    }):
        return True
    return snake in {
        "source_file", "source_filename", "source_path", "source_position",
        "source_range", "source_offset", "file_path", "filepath", "filename",
        "byte_span", "character_span", "text_span",
    }


def _without_source_locations(value: Any) -> Any:
    """Recursively remove source-only coordinates from stable-ID material.

    Containers that become empty solely because all of their contents were
    location metadata are removed too.  Pre-existing empty containers remain,
    since they can be part of the semantic evidence schema.
    """
    if isinstance(value, dict):
        cleaned: dict[Any, Any] = {}
        removed_child = False
        for key, child in value.items():
            if _source_location_key(key):
                removed_child = True
                continue
            normalized = _without_source_locations(child)
            if normalized is _REMOVED:
                removed_child = True
                continue
            cleaned[key] = normalized
        if not cleaned and value and removed_child:
            return _REMOVED
        return cleaned
    if isinstance(value, (list, tuple)):
        cleaned_items = []
        removed_child = False
        for child in value:
            normalized = _without_source_locations(child)
            if normalized is _REMOVED:
                removed_child = True
                continue
            cleaned_items.append(normalized)
        if not cleaned_items and value and removed_child:
            return _REMOVED
        return cleaned_items
    return value


def _stable_id_part(value: Any) -> Any:
    normalized = _without_source_locations(value)
    return {} if normalized is _REMOVED else normalized


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reason_code(message: str) -> str:
    """Return a stable leading reason token from a fail-closed diagnostic."""
    token = message.split(":", 1)[0].strip()
    return token or "UNSPECIFIED_ANALYSIS_FAILURE"


def _failure(error: ValueError | OSError) -> tuple[str, str]:
    """Normalize expected input/extraction failures without hiding code bugs."""
    if isinstance(error, FileNotFoundError):
        return "INPUT_FILE_NOT_FOUND", str(error)
    if isinstance(error, PermissionError):
        return "INPUT_PERMISSION_DENIED", str(error)
    if isinstance(error, OSError):
        return "INPUT_IO_ERROR", str(error)
    message = str(error)
    return _reason_code(message), message


def warning_stable_id(warning: dict[str, Any]) -> str:
    """Return a content identity independent of the warning's list ordinal.

    The identity is scoped to the analyzed artifact/consumer pair and the
    rule evidence.  The legacy ``WNNN``/``ROLENNN`` identifier remains in the
    output for compatibility with frozen validation records.
    """
    identity = {
        "target_identity": _stable_id_part(warning.get("target_identity", {})),
        "rule": warning.get("rule"),
        "evidence": _stable_id_part(warning.get("evidence", {})),
    }
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return "BC-" + hashlib.sha256(encoded).hexdigest()[:20].upper()


def _integrated_warning(warning: dict[str, Any], component: str) -> dict[str, Any]:
    result = deepcopy(warning)
    result["source_id"] = warning.get("id")
    result["stable_id"] = warning_stable_id(warning)
    result["analysis_component"] = component
    return result


def _input_record(
    artifact_path: Path,
    consumer_source: Path,
    relation_path: Path | None,
    producer_source: Path | None,
    producer_support_sources: Sequence[Path],
    mapping_bridge: Path | None,
) -> dict[str, Any]:
    def record(path: Path | None) -> dict[str, Any] | None:
        if path is None:
            return None
        resolved = path.resolve()
        return {
            "path": str(resolved),
            "sha256": _sha256(resolved) if resolved.is_file() else None,
            "present": resolved.is_file(),
        }

    return {
        "producer_artifact": record(artifact_path),
        "consumer_source": record(consumer_source),
        "checked_consumer_relation": record(relation_path),
        "producer_semantic_source": record(producer_source),
        "producer_support_sources": [record(path) for path in producer_support_sources],
        "recursive_mapping_bridge": record(mapping_bridge),
    }


def analyze_integrated(
    artifact_path: Path,
    consumer_source: Path,
    relation_path: Path | None = None,
    label: str | None = None,
    *,
    producer_source: Path | None = None,
    producer_support_sources: Sequence[Path] = (),
    mapping_bridge: Path | None = None,
    role_binding: bool | None = None,
) -> dict[str, Any]:
    """Run the current static and typed-role analyses behind one interface.

    ``role_binding=None`` enables role correspondence when a producer source
    is supplied and otherwise records it as ``NOT_REQUESTED``.  Passing
    ``True`` makes a missing or unsupported role analysis an explicit partial
    support gate.  Passing ``False`` records the component as intentionally
    disabled.  In all cases, a warning is E1 evidence and the research verdict
    remains ``UNKNOWN`` until separate validation establishes a higher grade.
    """
    started = time.monotonic()
    producer_support_sources = tuple(producer_support_sources)
    inputs = _input_record(
        artifact_path,
        consumer_source,
        relation_path,
        producer_source,
        producer_support_sources,
        mapping_bridge,
    )
    role_requested = producer_source is not None if role_binding is None else role_binding
    target = label or f"{artifact_path.stem}+{consumer_source.name}"

    try:
        static_result = analyze_static(
            artifact_path,
            consumer_source,
            relation_path,
            label,
            producer_source=producer_source,
            mapping_bridge=mapping_bridge,
        )
    except (ValueError, OSError) as error:
        reason_code, message = _failure(error)
        return {
            "schema": SCHEMA,
            "generated_at_utc": _utc_now(),
            "target": target,
            "support_status": "UNKNOWN",
            "components": {
                "static": {
                    "status": "UNKNOWN",
                    "reason_code": reason_code,
                    "reason": message,
                },
                "role_binding": {
                    "status": "NOT_RUN",
                    "reason_code": "STATIC_ANALYSIS_UNSUPPORTED",
                },
            },
            "inputs": inputs,
            "warnings": [],
            "warning_count": 0,
            "outcome": {
                "verdict": "UNKNOWN",
                "reason_code": reason_code,
                "evidence_grade": "E0",
                "validation_status": "NOT_RUN",
            },
            "runtime_seconds": round(time.monotonic() - started, 6),
        }

    warnings = [
        _integrated_warning(warning, "static")
        for warning in static_result["warnings"]
    ]
    role_component: dict[str, Any]
    role_result: dict[str, Any] | None = None
    support_status = "SUPPORTED"
    if not role_requested:
        role_component = {
            "status": "NOT_REQUESTED",
            "reason_code": "PRODUCER_SEMANTIC_SOURCE_NOT_SUPPLIED"
            if producer_source is None
            else "ROLE_BINDING_DISABLED",
        }
    elif producer_source is None:
        support_status = "UNKNOWN"
        role_component = {
            "status": "UNKNOWN",
            "reason_code": "PRODUCER_SEMANTIC_SOURCE_REQUIRED",
            "reason": "role binding was required without a producer semantic source",
        }
    else:
        try:
            role_result = analyze_role_binding(
                static_result,
                producer_source=producer_source,
                producer_support_sources=producer_support_sources,
            )
            role_component = {
                "status": "SUPPORTED",
                "schema": role_result["schema"],
                "warning_count": role_result["warning_count"],
            }
            warnings.extend(
                _integrated_warning(warning, "role_binding")
                for warning in role_result["warnings"]
            )
        except RoleBindingUnsupported as error:
            message = str(error)
            support_status = "UNKNOWN"
            role_component = {
                "status": "UNKNOWN",
                "reason_code": _reason_code(message),
                "reason": message,
            }

    stable_ids = [warning["stable_id"] for warning in warnings]
    if len(stable_ids) != len(set(stable_ids)):
        raise ValueError("DUPLICATE_STABLE_WARNING_ID")
    if support_status == "UNKNOWN":
        outcome_reason = role_component["reason_code"]
    elif warnings:
        outcome_reason = "E1_WARNINGS_REQUIRE_VALIDATION"
    else:
        outcome_reason = "NO_WARNING_NOT_VERIFIED"

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "target": static_result["target"],
        "support_status": support_status,
        "components": {
            "static": {
                "status": "SUPPORTED",
                "schema": static_result["schema"],
                "warning_count": static_result["warning_count"],
            },
            "role_binding": role_component,
        },
        "inputs": inputs,
        "rules": {
            **static_result["rules"],
            "R-ROLE": (
                "producer word roles correspond to consumer state, domain, polarity, "
                "and effect-authorization roles"
            ),
        },
        "static_analysis": static_result,
        "role_binding": role_result,
        "warnings": warnings,
        "warning_count": len(warnings),
        "outcome": {
            "verdict": "UNKNOWN",
            "reason_code": outcome_reason,
            "evidence_grade": "E1" if warnings else "E0",
            "validation_status": "NOT_RUN",
        },
        "manual_inputs": static_result.get("manual_inputs", []) + (
            [{
                "kind": "producer_semantic_source_routing",
                "path": str(producer_source.resolve()),
                "support_paths": [str(path.resolve()) for path in producer_support_sources],
            }]
            if role_requested and producer_source is not None
            else []
        ),
        "limitations": list(static_result.get("limitations", [])) + [
            "R-ROLE uses a bounded identifier-derived vocabulary and is UNKNOWN when its strict source/artifact interface is unsupported",
            "an integrated E1 warning is not a VIOLATION until the applicable validation route establishes the required evidence",
            "silence is not VERIFIED_WITHIN_SCOPE",
        ],
        "runtime_seconds": round(time.monotonic() - started, 6),
    }


def readable(result: dict[str, Any]) -> str:
    lines = [
        f"BindCheck integrated development analysis: {result['target']}",
        f"  support: {result['support_status']}  verdict: {result['outcome']['verdict']}",
        f"  warnings: {result['warning_count']}  runtime: {result['runtime_seconds']:.3f}s",
    ]
    for name, component in result["components"].items():
        detail = component.get("reason_code") or component.get("schema", "")
        lines.append(f"  {name}: {component['status']} {detail}".rstrip())
    for warning in result["warnings"]:
        lines.extend([
            "",
            f"{warning['id']} [{warning['stable_id']}] {warning['rule']} at {warning['location']}",
            f"  {warning['explanation']}",
            f"  Fix: {warning['suggested_fix']}",
        ])
    if not result["warnings"]:
        lines.append("  No warning in the supported components; this is not a safety verdict.")
    return "\n".join(lines)
