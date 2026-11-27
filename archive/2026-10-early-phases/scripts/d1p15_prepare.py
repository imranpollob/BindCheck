#!/usr/bin/env python3
"""Small reproducibility utilities for D1P-15 (never invokes a solver/prover)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1.warptoad_poseidon_provenance import trace_withdraw_poseidon2  # noqa: E402


def scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return json.dumps(str(value))
    if isinstance(value, str):
        return json.dumps(value)
    raise TypeError(f"unsupported TOML scalar {type(value).__name__}")


def typed_value(value, typ: dict) -> str:
    kind = typ["kind"]
    if kind in ("field", "integer", "boolean"):
        return scalar(value)
    if kind == "array":
        if len(value) != typ["length"]:
            raise ValueError(f"array length {len(value)} != ABI length {typ['length']}")
        return "[" + ", ".join(typed_value(item, typ["type"]) for item in value) + "]"
    raise TypeError(f"{kind} must be emitted as a TOML table")


def emit_struct(lines: list[str], table: str, value: dict, typ: dict) -> None:
    lines.extend(["", f"[{table}]"])
    nested = []
    for field in typ["fields"]:
        name, field_type = field["name"], field["type"]
        if field_type["kind"] == "struct":
            nested.append((name, value[name], field_type))
        else:
            lines.append(f"{name} = {typed_value(value[name], field_type)}")
    for name, child, child_type in nested:
        emit_struct(lines, f"{table}.{name}", child, child_type)


def prover_toml(artifact_path: Path, proof_path: Path, output_path: Path) -> None:
    artifact = json.loads(artifact_path.read_text())
    record = json.loads(proof_path.read_text())
    values = record.get("proofInputs", record)
    lines = ["# Generated from an existing frozen fixture by scripts/d1p15_prepare.py."]
    structs = []
    for parameter in artifact["abi"]["parameters"]:
        name, typ = parameter["name"], parameter["type"]
        if typ["kind"] == "struct":
            structs.append((name, values[name], typ))
        else:
            lines.append(f"{name} = {typed_value(values[name], typ)}")
    for name, value, typ in structs:
        emit_struct(lines, name, value, typ)
    output_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    provenance = sub.add_parser("provenance")
    provenance.add_argument("artifact", type=Path)
    provenance.add_argument("output", type=Path)
    prover = sub.add_parser("prover-toml")
    prover.add_argument("artifact", type=Path)
    prover.add_argument("proof_record", type=Path)
    prover.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "provenance":
        args.output.write_text(json.dumps(trace_withdraw_poseidon2(args.artifact), indent=2) + "\n")
    elif args.command == "prover-toml":
        prover_toml(args.artifact, args.proof_record, args.output)


if __name__ == "__main__":
    main()

