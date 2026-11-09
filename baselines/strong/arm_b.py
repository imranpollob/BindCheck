from __future__ import annotations

import os
import pathlib
import re
import tempfile
import time
from typing import Any

from .common import executable_from_candidates, envelope, finding, retain_native, run_command, utc_now


EXTERNAL_TOOLS = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools")


def circuit_files(root: pathlib.Path, cap: int = 4) -> tuple[list[pathlib.Path], bool]:
    excluded = {".git", "node_modules", "vendor", "target", "build", "dist", "out", "artifacts", "cache", "test", "tests"}
    ranked: list[tuple[int, pathlib.Path]] = []
    total = 0
    for path in sorted(root.rglob("*.circom")):
        if any(part in excluded for part in path.parts) or not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        total += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        score = 10 if re.search(r"\bcomponent\s+main\b", text) else 0
        score += 2 if "signal input" in text else 0
        score += 1 if "public" in text else 0
        ranked.append((score, path))
    selected = [path for _, path in sorted(ranked, key=lambda item: (-item[0], str(item[1])))[:cap]]
    return selected, total > len(selected)


def source_signals(root: pathlib.Path, circuits: list[pathlib.Path]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for path in circuits:
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if "activeLength" in text and ("enabled[" in text or "active[" in text):
            signals.append(finding(
                "B_PREFIX_CONSTRAINT_PRESENT",
                "The circuit source contains an active-length/prefix constraint shape.",
                path=relative, facts={"scope": "circuit-only"}, source="circuit-source",
            ))
        if "maskA" in text and "maskB" in text:
            signals.append(finding(
                "B_MASKS_CONSTRAINED",
                "The circuit contains two activation-mask families; consumer multiplicity is not decided here.",
                path=relative,
                facts={"disjoint_constraint_present": bool(re.search(r"maskA\s*\[.*?\]\s*\*\s*maskB\s*\[.*?\]\s*===\s*0", text, re.S))},
                source="circuit-source",
            ))
        if re.search(r"signal\s+input\s+amount\b", text) and len(re.findall(r"\bamount\b", text)) <= 2:
            signals.append(finding(
                "B_UNUSED_AMOUNT_SIGNAL",
                "The amount signal has no recovered constraint use beyond declaration/interface occurrence.",
                path=relative, facts={"scope": "circuit-only"}, source="circuit-source",
            ))
        if re.search(r"signal\s+(?:input|output)\s+activeLength\b", text):
            signals.append(finding(
                "B_LENGTH_SIGNAL_PRESENT",
                "The circuit declares an active-length signal; consumer array use is outside this arm.",
                path=relative, facts={"scope": "circuit-only"}, source="circuit-source",
            ))
        if re.search(r"signal\s+(?:input|output)\s+(?:publicAlias|decodedAlias)\b", text):
            signals.append(finding(
                "B_PUBLIC_ALIAS_SIGNAL_PRESENT",
                "The circuit declares an alias-like public role; consumer equality is outside this arm.",
                path=relative, facts={"scope": "circuit-only"}, source="circuit-source",
            ))
    return signals


def _include_args(root: pathlib.Path, circuit: pathlib.Path, flag: str) -> list[str]:
    candidates = [
        root / "node_modules",
        circuit.parent / "node_modules",
        EXTERNAL_TOOLS.parent / "node_modules",
        EXTERNAL_TOOLS.parent / "node_modules" / "circomlib",
    ]
    output: list[str] = []
    seen: set[pathlib.Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.is_dir() and candidate not in seen:
            seen.add(candidate)
            output.extend([flag, str(candidate)])
    return output


def _tool_identity(executable: str | None, source: pathlib.Path | None) -> dict[str, Any]:
    identity: dict[str, Any] = {"executable": executable, "source_revision": None}
    if source and (source / ".git").is_dir():
        record = run_command(["git", "rev-parse", "HEAD"], cwd=source, timeout=10)
        if record["exit_status"] == 0:
            identity["source_revision"] = record["stdout"].strip()
    return identity


def analyze_arm_b(root: pathlib.Path, output_dir: pathlib.Path, budget_seconds: float = 180.0) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.monotonic()
    root = root.resolve()
    circuits, capped = circuit_files(root)
    native_signals = source_signals(root, circuits)
    circom = executable_from_candidates(
        os.environ.get("BINDCHECK_STRONG_CIRCOM", ""),
        EXTERNAL_TOOLS / "circom-src" / "target" / "release" / "circom",
        "circom",
    )
    circomspect = executable_from_candidates(
        os.environ.get("BINDCHECK_STRONG_CIRCOMSPECT", ""),
        EXTERNAL_TOOLS / "circomspect-src" / "target" / "release" / "circomspect",
        "circomspect",
    )
    picus = executable_from_candidates(
        os.environ.get("BINDCHECK_STRONG_PICUS", ""),
        EXTERNAL_TOOLS / "picus-src" / "run-picus",
        "picus",
    )
    zkap = executable_from_candidates(os.environ.get("BINDCHECK_STRONG_ZKAP", ""), "zkap")
    tools: dict[str, Any] = {
        "circom_inspect": {"identity": _tool_identity(circom, EXTERNAL_TOOLS / "circom-src"), "invocations": []},
        "circomspect": {"identity": _tool_identity(circomspect, EXTERNAL_TOOLS / "circomspect-src"), "invocations": []},
        "picus": {"identity": _tool_identity(picus, EXTERNAL_TOOLS / "picus-src"), "preprocessing": [], "invocations": []},
        "zkap": {"identity": _tool_identity(zkap, None), "invocations": []},
    }
    remaining = lambda: max(0.0, budget_seconds - (time.monotonic() - started))
    with tempfile.TemporaryDirectory(prefix="bindcheck-strong-b-") as temporary:
        temp_root = pathlib.Path(temporary)
        r1cs_paths: list[tuple[int, pathlib.Path]] = []
        for index, circuit in enumerate(circuits):
            if remaining() <= 0:
                break
            if circomspect:
                record = run_command(
                    [circomspect, "--verbose", *_include_args(root, circuit, "--library"), str(circuit)],
                    cwd=root,
                    timeout=min(45.0, max(0.1, remaining())),
                )
                tools["circomspect"]["invocations"].append(retain_native(record, output_dir / "native" / "circomspect", f"circuit-{index:02d}"))
            if circom:
                target_dir = temp_root / f"circuit-{index:02d}"
                target_dir.mkdir()
                record = run_command(
                    [circom, str(circuit), "--inspect", "--r1cs", "--sym", "--O0", "-o", str(target_dir), *_include_args(root, circuit, "-l")],
                    cwd=root,
                    timeout=min(45.0, max(0.1, remaining())),
                )
                retained = retain_native(record, output_dir / "native" / "circom-inspect", f"circuit-{index:02d}")
                tools["circom_inspect"]["invocations"].append(retained)
                r1cs = target_dir / f"{circuit.stem}.r1cs"
                if record["exit_status"] == 0 and r1cs.is_file():
                    r1cs_paths.append((index, r1cs))
                    tools["picus"]["preprocessing"].append({
                        "circuit": circuit.relative_to(root).as_posix(),
                        "r1cs_bytes": r1cs.stat().st_size,
                    })
            if zkap and remaining() > 0:
                record = run_command([zkap, str(circuit)], cwd=root, timeout=min(45.0, max(0.1, remaining())))
                tools["zkap"]["invocations"].append(retain_native(record, output_dir / "native" / "zkap", f"circuit-{index:02d}"))
        if picus:
            for index, r1cs in r1cs_paths:
                if remaining() <= 0:
                    break
                record = run_command(
                    [picus, "--json", "-", str(r1cs)],
                    cwd=root,
                    timeout=min(60.0, max(0.1, remaining())),
                    env={"PLTUSERHOME": str(EXTERNAL_TOOLS / "picus-racket")},
                )
                tools["picus"]["invocations"].append(retain_native(record, output_dir / "native" / "picus", f"circuit-{index:02d}"))
    for name, detail in tools.items():
        invocations = detail["invocations"]
        if detail["identity"]["executable"] is None:
            detail["status"] = "UNKNOWN"
            detail["reason"] = "BASELINE_TOOL_UNAVAILABLE"
        elif not circuits:
            detail["status"] = "UNKNOWN"
            detail["reason"] = "NO_SUPPORTED_CIRCUIT_INPUT"
        elif name == "picus" and not invocations:
            detail["status"] = "UNKNOWN"
            detail["reason"] = "CIRCOM_PREPROCESSING_FAILED"
        elif not invocations:
            detail["status"] = "UNKNOWN"
            detail["reason"] = "NO_INVOCATION_WITHIN_BUDGET"
        elif any(item["timed_out"] for item in invocations):
            detail["status"] = "UNKNOWN"
            detail["reason"] = "BASELINE_TIMEOUT"
        elif all(item["exit_status"] is not None for item in invocations):
            detail["status"] = "completed"
            detail["reason"] = None
        else:
            detail["status"] = "UNKNOWN"
            detail["reason"] = "BASELINE_FAILED"
    run_status = "completed" if circuits else "UNKNOWN"
    fatal_reason = None if circuits else "NO_SUPPORTED_CIRCUIT_INPUT"
    return envelope(
        "B", root,
        started_utc=started_utc,
        elapsed_seconds=time.monotonic() - started,
        run_status=run_status,
        findings=[],
        verdict="UNKNOWN",
        coverage={
            "circuits_discovered": len(circuits),
            "circuit_paths": [path.relative_to(root).as_posix() for path in circuits],
            "circuit_selection_capped": capped,
            "budget_seconds": budget_seconds,
            "budget_exhausted": remaining() <= 0,
        },
        native={"signals": native_signals, "tools": tools},
        limitations=[
            "Circuit-only diagnostics do not establish whether a consumer effect is authorized.",
            "A successful no-finding run is not promoted to an integration safety verdict.",
            "Tool absence, preprocessing failure, nonzero exit, or timeout remains UNKNOWN.",
            "At most four ranked entry-circuit candidates are analyzed per repository.",
        ],
        fatal_reason=fatal_reason,
    )
