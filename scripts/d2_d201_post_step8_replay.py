#!/usr/bin/env python3
"""Non-destructive historical replay of the D2-01 content seal.

The current Step 8 role-binding implementation must remain untouched.  This
wrapper first proves that a direct live-checkout replay fails in exactly that
one member, retrieves the sealed historical byte sequence from the immutable
base commit, and substitutes those bytes only while hashing in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "protocols/d2/d2-01-post-step8-replay-v1.json"
PROTOCOL_SCHEMA = "bindcheck.d2.d2-01-post-step8-historical-replay/v1"
RESULT_SCHEMA = "bindcheck.d2.d2-01-post-step8-historical-replay-result/v1"
SEAL_SCHEMA = "bindcheck.d2.content-seal/v1"
OVERLAY_PATH = "src/bindcheck_d1/role_binding.py"
BASE_COMMIT = "544656abbfb535dcbe0f1157087240464f38cb0b"
HISTORICAL_SHA256 = "a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028"
CURRENT_SHA256 = "5bb3012b7d192e75e266cc3f5265e024046e8614c0cb63891c7acd5271eeaa71"
SEAL_SHA256 = "9f47676dd85a81ce0088c742a154f3919d9d94af78c1c8979bdd0386f56ddc06"
SEAL_MEMBER_COUNT = 8134
D2_00_MISSING_SHA256 = "afc86272b099d2bca73c785af3cee210b33f323d600cf0e5d96bbf2eb1ca47a0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _repository_path(relative: str) -> Path:
    candidate = Path(relative)
    _require(not candidate.is_absolute(), f"absolute sealed path is prohibited: {relative}")
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"sealed path escapes repository: {relative}") from exc
    return resolved


def _git(argv: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", *argv],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip()
        raise ValueError(f"git {' '.join(argv)} failed ({completed.returncode}): {detail}")
    return completed


def _validate_protocol(protocol: Mapping[str, Any]) -> None:
    _require(protocol.get("schema") == PROTOCOL_SCHEMA, "unexpected overlay protocol schema")
    source = protocol.get("source_seal", {})
    live = protocol.get("live_checkout_expectation", {})
    overlay = protocol.get("historical_overlay", {})
    _require(
        source.get("path") == "protocols/d2/d2-01-seal-v1.json",
        "unexpected D2-01 seal path",
    )
    _require(source.get("sha256") == SEAL_SHA256, "unexpected D2-01 seal hash")
    _require(source.get("member_count") == SEAL_MEMBER_COUNT, "unexpected D2-01 member count")
    _require(live.get("path") == OVERLAY_PATH, "live mismatch path is not the sole allowed overlay")
    _require(live.get("sealed_sha256") == HISTORICAL_SHA256, "unexpected historical hash")
    _require(live.get("sealed_size_bytes") == 41698, "unexpected historical size")
    _require(live.get("current_sha256") == CURRENT_SHA256, "unexpected current hash")
    _require(live.get("current_size_bytes") == 43263, "unexpected current size")
    _require(live.get("mismatch_count") == 1, "live mismatch count must be exactly one")
    _require(overlay.get("path") == OVERLAY_PATH, "overlay path is not allowed")
    _require(overlay.get("base_commit") == BASE_COMMIT, "overlay commit is not the immutable base")
    _require(
        overlay.get("git_object_spec") == f"{BASE_COMMIT}:{OVERLAY_PATH}",
        "overlay Git object is not the pinned path at the immutable base",
    )
    _require(overlay.get("expected_sha256") == HISTORICAL_SHA256, "overlay hash is not sealed hash")
    _require(overlay.get("expected_size_bytes") == 41698, "overlay size is not sealed size")
    _require(overlay.get("substitution_mode") == "IN_MEMORY_BYTES_ONLY", "overlay must be in-memory")
    _require(overlay.get("allowed_substitution_count") == 1, "only one overlay is permitted")
    _require(overlay.get("workspace_writes_allowed") is False, "workspace writes must be prohibited")
    gap = protocol.get("d2_00_retention_gap", {})
    _require(gap.get("pre_report_sha256") == D2_00_MISSING_SHA256, "unexpected D2-00 missing hash")
    _require(gap.get("included_in_overlay") is False, "D2-00 gap must not enter overlay")
    _require(
        gap.get("disposition") == "UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED",
        "D2-00 gap must remain unreconstructed",
    )


def _member_bytes(path: str) -> tuple[bytes | None, str | None]:
    candidate = _repository_path(path)
    if not candidate.is_file() or candidate.is_symlink():
        return None, "MISSING_OR_NOT_REGULAR"
    return candidate.read_bytes(), None


def _verify_members(
    seal: Mapping[str, Any], *, overlay_bytes: bytes | None = None
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    substitutions = 0
    files = seal.get("files", [])
    _require(isinstance(files, list), "seal files must be a list")
    for expected in files:
        _require(isinstance(expected, dict), "seal member must be an object")
        path = expected.get("path")
        _require(isinstance(path, str), "seal member path must be a string")
        if overlay_bytes is not None and path == OVERLAY_PATH:
            observed = overlay_bytes
            missing_reason = None
            substitutions += 1
        else:
            observed, missing_reason = _member_bytes(path)
        if missing_reason:
            mismatches.append({
                "path": path,
                "reason": missing_reason,
                "expected_sha256": expected.get("sha256"),
            })
            continue
        assert observed is not None
        observed_hash = _sha256_bytes(observed)
        observed_size = len(observed)
        if (observed_hash, observed_size) != (
            expected.get("sha256"), expected.get("size_bytes")
        ):
            mismatches.append({
                "path": path,
                "reason": "CONTENT_MISMATCH",
                "expected_sha256": expected.get("sha256"),
                "observed_sha256": observed_hash,
                "expected_size_bytes": expected.get("size_bytes"),
                "observed_size_bytes": observed_size,
            })
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "checked_files": len(files),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "in_memory_substitution_count": substitutions,
    }


def _historical_blob(protocol: Mapping[str, Any]) -> bytes:
    overlay = protocol["historical_overlay"]
    commit = overlay["base_commit"]
    _require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "base commit must be full SHA-1")
    resolved_commit = _git(["rev-parse", f"{commit}^{{commit}}"]).stdout.decode().strip()
    _require(resolved_commit == BASE_COMMIT, "base commit did not resolve exactly")
    blob = _git(["show", overlay["git_object_spec"]]).stdout
    _require(_sha256_bytes(blob) == HISTORICAL_SHA256, "historical Git blob hash mismatch")
    _require(len(blob) == overlay["expected_size_bytes"], "historical Git blob size mismatch")
    return blob


def _step8_provenance(protocol: Mapping[str, Any]) -> dict[str, Any]:
    provenance = protocol["step8_provenance"]
    checked: list[dict[str, Any]] = []
    for artifact in provenance["artifacts"]:
        path = _repository_path(artifact["path"])
        observed = _sha256_path(path)
        _require(observed == artifact["sha256"], f"Step 8 provenance drift: {artifact['path']}")
        checked.append({"path": artifact["path"], "sha256": observed})
    seal_path = _repository_path("results/raw/D2-08/content-seal-v1.json")
    step8_seal = _load_json(seal_path)
    role_entries = [
        item for item in step8_seal.get("files", [])
        if item.get("path") == OVERLAY_PATH
    ]
    _require(role_entries == [provenance["sealed_current_role_binding"]], "Step 8 role-binding seal entry mismatch")
    return {
        "status": "VERIFIED",
        "reason": provenance["reason"],
        "artifacts": checked,
        "sealed_current_role_binding": role_entries[0],
    }


def _d2_00_retention_gap(protocol: Mapping[str, Any]) -> dict[str, Any]:
    gap = protocol["d2_00_retention_gap"]
    report = _repository_path(gap["report_path"])
    _require(_sha256_path(report) == gap["report_sha256"], "D2-00 report drift")
    _require(gap["pre_report_sha256"] in report.read_text(), "D2-00 report no longer records missing hash")
    base_lookup = _git(
        ["cat-file", "-e", f"{BASE_COMMIT}:{gap['historical_path']}"],
        check=False,
    )
    _require(base_lookup.returncode != 0, "D2-00 historical status byte unexpectedly exists at base commit")
    current = _repository_path(gap["historical_path"])
    current_record: dict[str, Any] | None = None
    if current.is_file() and not current.is_symlink():
        current_hash = _sha256_path(current)
        current_record = {
            "path": gap["historical_path"],
            "sha256": current_hash,
            "size_bytes": current.stat().st_size,
            "matches_missing_pre_report_byte": current_hash == gap["pre_report_sha256"],
        }
    return {
        "status": gap["disposition"],
        "historical_path": gap["historical_path"],
        "pre_report_sha256": gap["pre_report_sha256"],
        "base_commit_lookup": "ABSENT",
        "current_observation": current_record,
        "reconstruction_attempted": False,
        "included_in_overlay": False,
    }


def run_replay(protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Run the direct and single-overlay verifications without writing files."""
    protocol = _load_json(protocol_path)
    _validate_protocol(protocol)
    source = protocol["source_seal"]
    seal_path = _repository_path(source["path"])
    _require(_sha256_path(seal_path) == SEAL_SHA256, "D2-01 seal bytes drifted")
    seal = _load_json(seal_path)
    _require(seal.get("schema") == SEAL_SCHEMA, "unexpected D2-01 seal schema")
    _require(len(seal.get("files", [])) == SEAL_MEMBER_COUNT, "unexpected D2-01 seal length")

    direct = _verify_members(seal)
    live = protocol["live_checkout_expectation"]
    expected_mismatch = {
        "path": live["path"],
        "reason": live["reason"],
        "expected_sha256": live["sealed_sha256"],
        "observed_sha256": live["current_sha256"],
        "expected_size_bytes": live["sealed_size_bytes"],
        "observed_size_bytes": live["current_size_bytes"],
    }
    _require(direct["status"] == "FAIL", "live D2-01 replay unexpectedly passed")
    _require(direct["checked_files"] == SEAL_MEMBER_COUNT, "live replay checked wrong member count")
    _require(direct["mismatches"] == [expected_mismatch], "live replay mismatch set is not exact")
    direct["status"] = "EXPECTED_FAIL"

    historical = _historical_blob(protocol)
    replay = _verify_members(seal, overlay_bytes=historical)
    _require(replay["status"] == "PASS", "historical in-memory replay did not pass")
    _require(replay["checked_files"] == SEAL_MEMBER_COUNT, "overlay replay checked wrong member count")
    _require(replay["mismatch_count"] == 0, "overlay replay retained mismatches")
    _require(replay["in_memory_substitution_count"] == 1, "overlay replay substitution count is not one")

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS",
        "protocol": {
            "path": protocol_path.resolve().relative_to(ROOT).as_posix(),
            "sha256": _sha256_path(protocol_path),
        },
        "source_seal": {
            "path": source["path"],
            "sha256": SEAL_SHA256,
            "member_count": SEAL_MEMBER_COUNT,
        },
        "direct_live_checkout_replay": direct,
        "historical_blob": {
            "git_object_spec": protocol["historical_overlay"]["git_object_spec"],
            "sha256": _sha256_bytes(historical),
            "size_bytes": len(historical),
            "materialization": "IN_MEMORY_ONLY",
        },
        "historical_overlay_replay": replay,
        "step8_provenance": _step8_provenance(protocol),
        "d2_00_retention_gap": _d2_00_retention_gap(protocol),
        "interpretation": {
            "historical_reproducibility_restored": True,
            "current_checkout_equivalence": False,
            "current_behavior_claim": False,
            "rescored_or_relabelled": False,
            "research_verdict": "UNKNOWN",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay D2-01 with one exact in-memory historical Git blob overlay."
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=DEFAULT_PROTOCOL,
        help="Pinned overlay protocol (default: protocols/d2/d2-01-post-step8-replay-v1.json)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_replay(args.protocol.resolve())
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"schema": RESULT_SCHEMA, "status": "ERROR", "reason": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
