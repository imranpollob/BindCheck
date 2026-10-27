#!/usr/bin/env python3
"""Probe the pinned Halmos interfaces relevant to relation export."""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

from z3 import BitVec, Solver, UGT

from halmos.__main__ import MainResult, TestResult
from halmos.config import Config, default_config
from halmos.sevm import EventLog, Path as HalmosPath
from halmos.sevm import StorageWrite


def main() -> None:
    executable = Path(sys.prefix) / "bin" / "halmos"
    x = BitVec("calldata_word", 256)
    path = HalmosPath(Solver())
    path.append(UGT(x, 7), branching=True)
    smt = path.to_smt2(default_config())
    storage = StorageWrite(address=0xCAFE, slot=x, value=x + 1, transient=False)
    test_result_fields = [field.name for field in dataclasses.fields(TestResult)]
    main_result_fields = [field.name for field in dataclasses.fields(MainResult)]
    unknown_help = Config.__dataclass_fields__["uninterpreted_unknown_calls"].metadata["help"]
    result = {
        "schema": "bindcheck.d1p16.halmos-interface-probe.v1",
        "version": importlib.metadata.version("halmos"),
        "executable": str(executable),
        "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "path": {
            "public_methods": sorted(name for name in dir(HalmosPath) if not name.startswith("_")),
            "conditions_count": len(path.conditions),
            "to_smt2_return_type": type(smt).__name__,
            "to_smt2_fields": sorted(getattr(smt, "__dict__", {}).keys()),
            "smt_contains_symbol": "calldata_word" in str(smt),
        },
        "storage_write": {
            "fields": [field.name for field in dataclasses.fields(StorageWrite)],
            "sample": {name: str(getattr(storage, name)) for name in ("address", "slot", "value", "transient")},
        },
        "event_log": {
            "fields": [field.name for field in dataclasses.fields(EventLog)],
        },
        "cli_json_schema": {
            "MainResult": main_result_fields,
            "TestResult": test_result_fields,
            "exports_path_conditions": any(name in {"conditions", "path_conditions", "paths"} for name in test_result_fields),
            "exports_post_state": any("state" in name or "storage" in name for name in test_result_fields),
            "exports_events": any("event" in name or "log" in name for name in test_result_fields),
        },
        "unknown_call_boundary": {
            "option_value": default_config().uninterpreted_unknown_calls,
            "help": unknown_help,
            "cli_marks_option_deprecated_noop": "Deprecated; no-op" in unknown_help,
        },
        "conclusion": (
            "Internal objects retain path conditions and SSTORE records, but the stable CLI JSON result "
            "does not export conditions, post-state, or events. Its former unknown-external-call "
            "abstraction is a deprecated no-op, so a verifier relation boundary and relation serializer "
            "would require a Halmos patch or a custom internal-API driver."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
