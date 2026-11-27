#!/usr/bin/env python3
"""Fail-closed reproduction driver for the partial D2 development artifact.

This module intentionally has no third-party imports.  Read-only profiles never
write, and the sole writing profile is confined to a fresh direct child of
``artifact/work``.  It is not a Gate B runner and cannot open reserved data.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifact"
WORK = ARTIFACT / "work"
STATUS = "PARTIAL_DEVELOPMENT_ARTIFACT / FINAL_ARTIFACT_BLOCKED"
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

D2_01_ROLE_PATH = "src/bindcheck_d1/role_binding.py"
D2_01_ROLE_OLD_SHA256 = (
    "a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028"
)
D2_01_ROLE_OLD_SIZE = 41698
D2_01_ROLE_CURRENT_SHA256 = (
    "5bb3012b7d192e75e266cc3f5265e024046e8614c0cb63891c7acd5271eeaa71"
)
D2_01_ROLE_CURRENT_SIZE = 43263


class ArtifactError(RuntimeError):
    """A fail-closed artifact validation error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot load JSON {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ArtifactError(
            f"{label}: expected {expected!r}, observed {actual!r}"
        )


def validate_relpath(value: str, label: str) -> Path:
    require(bool(value), f"{label}: empty path")
    path = Path(value)
    require(not path.is_absolute(), f"{label}: absolute path is forbidden: {value}")
    require(".." not in path.parts, f"{label}: parent traversal is forbidden: {value}")
    require(path.as_posix() == value, f"{label}: non-canonical path: {value}")
    return path


def validated_work_path(run_id: str, *, work_root: Path = WORK) -> Path:
    require(bool(RUN_ID_RE.fullmatch(run_id)), f"unsafe run id: {run_id!r}")
    require(not work_root.is_symlink(), f"work root may not be a symlink: {work_root}")
    target = work_root / run_id
    require(target.parent == work_root, "run directory must be a direct work child")
    require(not target.exists() and not target.is_symlink(), f"output exists: {target}")
    return target


def source_root(args: argparse.Namespace) -> Path | None:
    if args.source == "current-workspace":
        require(args.sidecar_root is None, "--sidecar-root is invalid for current-workspace")
        return None
    require(args.source == "sidecar", f"unsupported source: {args.source}")
    require(args.sidecar_root is not None, "sidecar source requires --sidecar-root")
    sidecar = Path(args.sidecar_root)
    require(sidecar.is_absolute(), "sidecar root must be absolute")
    require(sidecar.exists() and sidecar.is_dir(), f"sidecar root is not a directory: {sidecar}")
    require(not sidecar.is_symlink(), "sidecar root may not be a symlink")
    return sidecar.resolve()


def sidecar_candidate(sidecar: Path, relative: str | Path) -> Path:
    sidecar = sidecar.resolve(strict=False)
    candidate = sidecar / relative
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise ArtifactError(f"cannot resolve sidecar path {candidate}: {exc}") from exc
    require(resolved.is_relative_to(sidecar), f"sidecar path escapes root: {candidate}")
    return candidate


def resolve_evidence_path(recorded: str, sidecar: Path | None) -> Path:
    """Resolve one recorded evidence path without guessing or materializing it."""
    path = Path(recorded)
    if path.is_absolute():
        if sidecar is None:
            return path
        require(
            path.name == "solc-0.8.29",
            f"unrecognized absolute sidecar input: {recorded}",
        )
        return sidecar_candidate(sidecar, "external/tools/solc-0.8.29")
    if recorded.startswith("../BindCheck/"):
        suffix = recorded[len("../BindCheck/") :]
        validate_relpath(suffix, "BindCheck sidecar suffix")
        if sidecar is None:
            return (ROOT / recorded).resolve()
        return sidecar_candidate(sidecar, Path("external/BindCheck") / suffix)
    relative = validate_relpath(recorded, "evidence path")
    if sidecar is not None and recorded.startswith("results/raw/"):
        return sidecar_candidate(sidecar, relative)
    return ROOT / relative


def check_record(path: Path, entry: Mapping[str, Any], label: str) -> dict[str, Any] | None:
    expected_sha = entry.get("sha256")
    expected_size = entry.get("size_bytes")
    require(isinstance(expected_sha, str) and SHA256_RE.fullmatch(expected_sha) is not None,
            f"{label}: invalid expected SHA-256")
    require(isinstance(expected_size, int) and expected_size >= 0,
            f"{label}: invalid expected size")
    if not path.exists():
        return {"path": entry.get("path"), "reason": "MISSING"}
    if not path.is_file() or path.is_symlink():
        return {"path": entry.get("path"), "reason": "NOT_REGULAR_FILE"}
    size = path.stat().st_size
    observed_sha = sha256_file(path)
    if size == expected_size and observed_sha == expected_sha:
        return None
    return {
        "path": entry.get("path"),
        "reason": "CONTENT_MISMATCH",
        "expected_sha256": expected_sha,
        "expected_size_bytes": expected_size,
        "observed_sha256": observed_sha,
        "observed_size_bytes": size,
    }


def validate_expected_live_d2_01_mismatch(mismatches: list[dict[str, Any]]) -> None:
    require_exact(len(mismatches), 1, "D2-01 live mismatch count")
    mismatch = mismatches[0]
    require_exact(mismatch.get("path"), D2_01_ROLE_PATH, "D2-01 live mismatch path")
    require_exact(mismatch.get("reason"), "CONTENT_MISMATCH", "D2-01 live mismatch reason")
    require_exact(mismatch.get("expected_sha256"), D2_01_ROLE_OLD_SHA256,
                  "D2-01 historical role-binding SHA-256")
    require_exact(mismatch.get("expected_size_bytes"), D2_01_ROLE_OLD_SIZE,
                  "D2-01 historical role-binding size")
    require_exact(mismatch.get("observed_sha256"), D2_01_ROLE_CURRENT_SHA256,
                  "D2-01 current role-binding SHA-256")
    require_exact(mismatch.get("observed_size_bytes"), D2_01_ROLE_CURRENT_SIZE,
                  "D2-01 current role-binding size")


def git_historical_bytes(commit: str, path: str) -> bytes:
    require(SHA256_RE.fullmatch(commit) is not None or re.fullmatch(r"[0-9a-f]{40}", commit),
            "invalid historical Git commit")
    validate_relpath(path, "historical Git path")
    proc = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise ArtifactError(
            f"cannot load historical byte {commit}:{path}: "
            f"{proc.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return proc.stdout


def historical_overlay_bytes(
    sidecar: Path | None, historical: Mapping[str, Any]
) -> tuple[bytes, str]:
    commit = historical["base_commit"]
    path = historical["path"]
    if sidecar is None:
        return git_historical_bytes(commit, path), "IMMUTABLE_GIT_OBJECT_IN_MEMORY"
    sidecar_path = sidecar_candidate(
        sidecar,
        Path("external/history") / commit / validate_relpath(path, "historical sidecar path"),
    )
    require(sidecar_path.is_file() and not sidecar_path.is_symlink(),
            f"missing historical sidecar byte: {sidecar_path}")
    return sidecar_path.read_bytes(), "EXPLICIT_SIDECAR_BYTE_IN_MEMORY"


def crosscheck_historical_wrapper(historical: Mapping[str, Any]) -> dict[str, Any]:
    wrapper = historical["wrapper"]
    protocol = historical["protocol"]
    report = historical["report"]
    test = historical["test"]
    for entry in (wrapper, protocol, report, test):
        require_file_hash(entry["path"], entry["sha256"], None)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, wrapper["path"]],
        cwd=ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require_exact(proc.returncode, 0, "D2-01 historical wrapper exit code")
    try:
        result = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"invalid D2-01 wrapper JSON: {exc}") from exc
    require_exact(result.get("schema"),
                  "bindcheck.d2.d2-01-post-step8-historical-replay-result/v1",
                  "D2-01 wrapper schema")
    require_exact(result.get("status"), "PASS", "D2-01 wrapper status")
    live = result["direct_live_checkout_replay"]
    require_exact(live["status"], "EXPECTED_FAIL", "D2-01 wrapper live status")
    require_exact(live["checked_files"], 8134, "D2-01 wrapper live count")
    validate_expected_live_d2_01_mismatch(live["mismatches"])
    overlay = result["historical_overlay_replay"]
    require_exact(overlay["status"], "PASS", "D2-01 wrapper overlay status")
    require_exact(overlay["checked_files"], 8134, "D2-01 wrapper overlay count")
    require_exact(overlay["mismatch_count"], 0, "D2-01 wrapper overlay mismatches")
    require_exact(overlay["in_memory_substitution_count"], 1,
                  "D2-01 wrapper substitution count")
    require_exact(result["d2_00_retention_gap"]["status"],
                  "UNAVAILABLE_RETENTION_GAP_NOT_RECONSTRUCTED",
                  "D2-00 retention gap")
    require_exact(result["interpretation"]["current_checkout_equivalence"], False,
                  "D2-01 wrapper current equivalence")
    return {
        "status": "PASS",
        "schema": result["schema"],
        "live_status": live["status"],
        "live_mismatch_count": live["mismatch_count"],
        "overlay_status": overlay["status"],
        "overlay_checked_files": overlay["checked_files"],
        "d2_00_retention_gap": result["d2_00_retention_gap"]["status"],
    }


def verify_seal(
    seal_path: Path,
    sidecar: Path | None,
    *,
    byte_overrides: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    seal = load_json(seal_path)
    entries = seal.get("files")
    require(isinstance(entries, list) and entries, f"seal has no files: {seal_path}")
    seen: set[str] = set()
    mismatches: list[dict[str, Any]] = []
    byte_overrides = byte_overrides or {}
    for index, entry in enumerate(entries):
        require(isinstance(entry, dict), f"seal entry {index} is not an object")
        recorded = entry.get("path")
        require(isinstance(recorded, str), f"seal entry {index} has no path")
        require(recorded not in seen, f"duplicate seal path: {recorded}")
        seen.add(recorded)
        if recorded in byte_overrides:
            data = byte_overrides[recorded]
            observed_sha = sha256_bytes(data)
            observed_size = len(data)
            if observed_sha != entry.get("sha256") or observed_size != entry.get("size_bytes"):
                mismatches.append({
                    "path": recorded,
                    "reason": "OVERRIDE_CONTENT_MISMATCH",
                    "expected_sha256": entry.get("sha256"),
                    "expected_size_bytes": entry.get("size_bytes"),
                    "observed_sha256": observed_sha,
                    "observed_size_bytes": observed_size,
                })
            continue
        mismatch = check_record(resolve_evidence_path(recorded, sidecar), entry,
                                f"{seal_path}:{recorded}")
        if mismatch is not None:
            mismatches.append(mismatch)
    try:
        display_path = seal_path.relative_to(ROOT).as_posix()
    except ValueError:
        display_path = str(seal_path)
    return {
        "seal": display_path,
        "seal_sha256": sha256_file(seal_path),
        "checked_files": len(entries),
        "status": "PASS" if not mismatches else "FAIL",
        "mismatches": mismatches,
    }


def verify_external_manifest(sidecar: Path | None) -> dict[str, Any]:
    path = ROOT / "protocols/d2/d2-01-external-inputs-v1.json"
    manifest = load_json(path)
    require_exact(manifest.get("schema"), "bindcheck.d2.external-input-manifest/v1",
                  "D2-01 external manifest schema")
    entries = manifest.get("files")
    require(isinstance(entries, list), "D2-01 external files must be a list")
    require_exact(len(entries), 9, "D2-01 external file count")
    mismatches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        recorded = entry.get("path")
        require(isinstance(recorded, str) and recorded not in seen,
                f"invalid or duplicate external path: {recorded!r}")
        seen.add(recorded)
        mismatch = check_record(resolve_evidence_path(recorded, sidecar), entry,
                                f"external input {recorded}")
        if mismatch is not None:
            mismatches.append(mismatch)
    require(not mismatches, f"D2-01 external input mismatches: {mismatches}")
    return {
        "manifest": str(path.relative_to(ROOT)),
        "manifest_sha256": sha256_file(path),
        "checked_files": len(entries),
        "status": "PASS",
    }


def require_file_hash(relative: str, expected_sha: str, sidecar: Path | None) -> None:
    path = resolve_evidence_path(relative, sidecar)
    require(path.is_file() and not path.is_symlink(), f"missing bound file: {relative}")
    require_exact(sha256_file(path), expected_sha, f"SHA-256 {relative}")


def verify_retained_evidence(sidecar: Path | None) -> dict[str, Any]:
    inventory = load_json(ARTIFACT / "input-inventory-v1.json")
    require_exact(inventory.get("status"), STATUS, "input inventory status")
    seal_rows = inventory.get("controlling_seals")
    require(isinstance(seal_rows, list), "controlling seals must be a list")
    require_exact(len(seal_rows), 5, "controlling seal row count")
    require(all(isinstance(row, dict) and isinstance(row.get("path"), str)
                for row in seal_rows), "invalid controlling seal row")
    seals = {row["path"]: row for row in seal_rows}
    require_exact(len(seals), len(seal_rows), "unique controlling seal paths")
    expected_paths = {
        "protocols/d2/d2-01-seal-v1.json",
        "results/raw/D2-07-recovery-01/content-seal-v1.json",
        "results/raw/D2-08/content-seal-v1.json",
        "results/raw/D2-09/content-seal-v1.json",
        "results/raw/D2-10/run-02/content-seal-v1.json",
    }
    require_exact(set(seals), expected_paths, "controlling seal set")
    for relative, row in seals.items():
        require_file_hash(relative, row["sha256"], sidecar)

    d2_01_seal = ROOT / "protocols/d2/d2-01-seal-v1.json"
    live = verify_seal(d2_01_seal, sidecar)
    validate_expected_live_d2_01_mismatch(live["mismatches"])

    historical = inventory.get("d2_01_historical_overlay")
    require(isinstance(historical, dict), "missing D2-01 historical overlay contract")
    commit = historical.get("base_commit")
    path = historical.get("path")
    require(isinstance(commit, str) and isinstance(path, str),
            "invalid historical overlay binding")
    old_bytes, overlay_source = historical_overlay_bytes(sidecar, historical)
    require_exact(sha256_bytes(old_bytes), historical.get("sha256"),
                  "historical overlay byte SHA-256")
    require_exact(len(old_bytes), historical.get("size_bytes"),
                  "historical overlay byte size")
    overlay = verify_seal(d2_01_seal, sidecar, byte_overrides={path: old_bytes})
    require_exact(overlay["status"], "PASS", "D2-01 historical overlay replay")
    require_exact(overlay["checked_files"], 8134, "D2-01 overlay checked files")
    wrapper_crosscheck: dict[str, Any]
    if sidecar is None:
        wrapper_crosscheck = crosscheck_historical_wrapper(historical)
    else:
        wrapper_crosscheck = {
            "status": "NOT_RUN_SIDECAR_ROUTE",
            "reason": "The wrapper is current-workspace-specific; the same exact overlay semantics were replayed against the explicit sidecar.",
        }

    generic_results: list[dict[str, Any]] = []
    for relative in sorted(expected_paths - {"protocols/d2/d2-01-seal-v1.json"}):
        result = verify_seal(resolve_evidence_path(relative, sidecar), sidecar)
        require_exact(result["status"], "PASS", f"seal replay {relative}")
        require_exact(result["checked_files"], seals[relative]["files"],
                      f"sealed file count {relative}")
        generic_results.append(result)

    external = verify_external_manifest(sidecar)
    require_exact(external["manifest_sha256"], inventory["external_d2_01"]["manifest_sha256"],
                  "external manifest SHA-256")

    headline_hashes = inventory.get("retained_headline_hashes")
    require(isinstance(headline_hashes, list) and headline_hashes,
            "missing retained headline hash list")
    for entry in headline_hashes:
        require_file_hash(entry["path"], entry["sha256"], sidecar)

    return {
        "status": "PASS",
        "source": "sidecar" if sidecar is not None else "current-workspace",
        "d2_01_live_replay": {
            "status": "EXPECTED_FAIL",
            "checked_files": live["checked_files"],
            "mismatches": live["mismatches"],
        },
        "d2_01_historical_overlay_replay": {
            "status": "PASS",
            "checked_files": overlay["checked_files"],
            "base_commit": commit,
            "overlaid_path": path,
            "overlaid_sha256": sha256_bytes(old_bytes),
            "overlay_source": overlay_source,
            "current_checkout_equivalence": False,
            "d2_00_retention_gap": historical["d2_00_retention_gap"],
        },
        "historical_wrapper_crosscheck": wrapper_crosscheck,
        "external_inputs": external,
        "other_seals": generic_results,
        "headline_hashes": len(headline_hashes),
    }


def parse_sha256sums(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ArtifactError(f"cannot read {path}: {exc}") from exc
    require(lines, "SHA256SUMS is empty")
    result: dict[str, str] = {}
    for number, line in enumerate(lines, 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match is not None, f"invalid SHA256SUMS line {number}")
        digest, recorded = match.groups()
        validate_relpath(recorded, f"SHA256SUMS line {number}")
        require(recorded.startswith("artifact/"), f"non-artifact checksum path: {recorded}")
        require(recorded != "artifact/SHA256SUMS", "SHA256SUMS may not hash itself")
        require(recorded not in result, f"duplicate checksum path: {recorded}")
        result[recorded] = digest
    return result


def verify_own_checksums() -> dict[str, Any]:
    sums = parse_sha256sums(ARTIFACT / "SHA256SUMS")
    actual_paths: set[str] = set()
    for path in ARTIFACT.rglob("*"):
        if not path.is_file() or path == ARTIFACT / "SHA256SUMS":
            continue
        relative_to_artifact = path.relative_to(ARTIFACT)
        if relative_to_artifact.parts[0] == "work" or "__pycache__" in relative_to_artifact.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        actual_paths.add(relative)
    require_exact(set(sums), actual_paths, "artifact checksum coverage")
    for relative, expected in sums.items():
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"invalid checksummed file: {relative}")
        require_exact(sha256_file(path), expected, f"artifact checksum {relative}")
    return {"status": "PASS", "checked_files": len(sums)}


def verify_manifest() -> dict[str, Any]:
    path = ARTIFACT / "manifest-v1.json"
    manifest = load_json(path)
    require_exact(manifest.get("schema"), "bindcheck.d2.partial-development-artifact-manifest/v1",
                  "artifact manifest schema")
    require_exact(manifest.get("status"), STATUS, "artifact manifest status")
    require_exact(manifest.get("frozen_release"), False, "frozen release claim")
    require_exact(manifest.get("reserved_data_included"), False, "reserved data claim")
    bindings = manifest.get("bindings")
    require(isinstance(bindings, list) and bindings, "manifest bindings must be nonempty")
    seen: set[str] = set()
    for entry in bindings:
        relative = entry.get("path")
        require(isinstance(relative, str), "manifest binding without path")
        validate_relpath(relative, "manifest binding")
        require(relative not in seen, f"duplicate manifest binding: {relative}")
        seen.add(relative)
        path = ROOT / relative
        mismatch = check_record(path, entry, f"manifest binding {relative}")
        require(mismatch is None, f"manifest binding mismatch: {mismatch}")
    return {"status": "PASS", "checked_bindings": len(bindings)}


def markdown_primary_source_count() -> int:
    text = (ROOT / "paper/d2-status-sources.md").read_text(encoding="utf-8")
    start = text.index("## Primary related-work sources")
    end = text.index("## Access and citation limits")
    return len(re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", text[start:end]))


def unittest_method_count(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ArtifactError(f"cannot parse test source {path}: {exc}") from exc
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def metadata_profile() -> dict[str, Any]:
    status = load_json(ARTIFACT / "STATUS.json")
    expected = load_json(ARTIFACT / "expected-results-v1.json")
    inventory = load_json(ARTIFACT / "input-inventory-v1.json")
    platform = load_json(ARTIFACT / "platform-matrix-v1.json")
    for label, doc in (("status", status), ("expected", expected),
                       ("inventory", inventory), ("platform", platform)):
        require_exact(doc.get("status"), STATUS, f"{label} artifact status")
    require_exact(status.get("research_verdict"), "UNKNOWN", "research verdict")
    require_exact(status.get("gate_a"), "INCONCLUSIVE", "Gate A")
    require_exact(status.get("gate_b"), "NOT_EVALUATED", "Gate B")
    require_exact(status.get("gate_c"), "NOT_REACHED", "Gate C")
    require_exact(status.get("reserved_data_included"), False, "reserved data included")
    require_exact(status.get("frozen_release_claimed"), False, "frozen release claimed")
    require_exact(status.get("final_paper_artifact_claimed"), False,
                  "final paper artifact claimed")
    checksums = verify_own_checksums()
    manifest = verify_manifest()

    step18 = expected["step18"]
    ledger = load_json(ROOT / "docs/d2/claim-ledger-v2.json")
    map_doc = load_json(ROOT / "paper/d2-status-claim-map-v1.json")
    related = load_json(ROOT / "docs/d2/related-work-matrix-v2.json")
    require_exact(len(ledger["claims"]), step18["ledger_claims"], "Step 18 ledger claims")
    counts = collections.Counter(row["status"] for row in ledger["claims"])
    require_exact(dict(sorted(counts.items())), step18["claim_status_counts"],
                  "Step 18 claim status counts")
    require_exact(len(map_doc["entries"]), step18["claim_map_entries"],
                  "Step 18 claim-map entries")
    require_exact(len(related["works"]), step18["closest_works"], "Step 18 closest works")
    require_exact(markdown_primary_source_count(), step18["primary_source_records"],
                  "Step 18 primary-source links")
    require_exact(ledger["research_verdict"], step18["research_verdict"],
                  "Step 18 research verdict")
    require_exact(ledger["gate_a_result"], step18["gate_a"], "Step 18 Gate A")
    require_exact(ledger["submission_readiness"], step18["submission_readiness"],
                  "Step 18 submission readiness")
    return {
        "schema": "bindcheck.d2.partial-artifact-profile-result/v1",
        "profile": "metadata",
        "status": "PASS",
        "artifact_status": STATUS,
        "own_checksums": checksums,
        "manifest": manifest,
        "step18": {
            "ledger_claims": len(ledger["claims"]),
            "claim_status_counts": dict(sorted(counts.items())),
            "claim_map_entries": len(map_doc["entries"]),
            "closest_works": len(related["works"]),
            "primary_source_records": markdown_primary_source_count(),
        },
    }


def payy_extent(summary: Mapping[str, Any]) -> dict[str, bool]:
    rows = summary["results"]["payy_extent"]
    return {row["revision"]: row["observed_r_extent"] for row in rows}


def recompute_results(sidecar: Path | None) -> dict[str, Any]:
    retained = verify_retained_evidence(sidecar)
    expected = load_json(ARTIFACT / "expected-results-v1.json")
    steps = expected["steps"]

    d200 = load_json(resolve_evidence_path(
        "results/raw/D2-00/foundation-self-test-20261102-02/self-test-summary.json", sidecar))
    require_exact(d200["status"], steps["D2-00"]["self_test_status"], "D2-00 status")
    require_exact(d200["pre_tamper_verification"]["status"], "PASS", "D2-00 pre-tamper")
    require_exact(d200["post_tamper_verification"]["status"], "FAIL", "D2-00 post-tamper")
    require_exact(unittest_method_count(ROOT / "tests/test_d2_foundation.py"),
                  steps["D2-00"]["focused_unittest_count"],
                  "D2-00 focused unittest count")

    d201 = load_json(resolve_evidence_path("results/raw/D2-01-recovery-01/run-summary.json", sidecar))
    exp = steps["D2-01"]
    require_exact(exp["authoritative_namespace"], "results/raw/D2-01-recovery-01",
                  "D2-01 authoritative namespace")
    require_exact(retained["d2_01_live_replay"]["status"], exp["live_current_replay"],
                  "D2-01 live replay status")
    require_exact(len(retained["d2_01_live_replay"]["mismatches"]),
                  exp["live_mismatch_count"], "D2-01 live mismatch count")
    require_exact(retained["d2_01_historical_overlay_replay"]["status"],
                  exp["historical_overlay_replay"], "D2-01 overlay status")
    require_exact(retained["d2_01_historical_overlay_replay"]["checked_files"],
                  exp["historical_overlay_checked_files"], "D2-01 overlay count")
    require_exact(retained["d2_01_historical_overlay_replay"]
                  ["current_checkout_equivalence"], exp["current_checkout_equivalence"],
                  "D2-01 current checkout equivalence")
    require_exact(retained["d2_01_historical_overlay_replay"]["d2_00_retention_gap"],
                  exp["d2_00_retention_gap"], "D2-00 retention gap")
    require_exact(retained["d2_01_historical_overlay_replay"]["checked_files"],
                  exp["sealed_input_files"], "D2-01 sealed input files")
    require_exact(d201["status"], exp["status"], "D2-01 status")
    require_exact(d201["research_verdict"], exp["research_verdict"], "D2-01 verdict")
    require_exact(d201["results"]["case_rows"], exp["case_rows"], "D2-01 case rows")
    require_exact(d201["results"]["static_benchmark"], exp["static_benchmark"],
                  "D2-01 static benchmark")
    require_exact(d201["results"]["integrated_benchmark"], exp["integrated_benchmark"],
                  "D2-01 integrated benchmark")
    observed_ablation = {name: row["detections"] for name, row in d201["results"]["ablation"].items()}
    require_exact(observed_ablation, exp["ablation_detections"], "D2-01 ablation")
    unknown_ids = sorted({item for row in d201["results"]["ablation"].values()
                          for item in row["unknown_example_ids"]})
    require_exact(unknown_ids, exp["ablation_unknown_example_ids"], "D2-01 ablation unknowns")
    require_exact(payy_extent(d201), exp["payy_extent"], "D2-01 Payy extent")
    require_exact(all(d201["completion_checks"].values()), exp["completion_checks_all_true"],
                  "D2-01 completion checks")

    d202 = load_json(ROOT / "protocols/d2/d2-02-ecosystem-inventory-v1.json")
    exp = steps["D2-02"]
    population = d202["eligible_population"]
    history = d202["historical_transfer_reconciliation"]["attempt_counts"]
    d202_actual = {
        "research_verdict": d202["research_verdict"],
        "candidate_revisions": population["candidate_revision_count"],
        "repositories": population["unique_repository_count"],
        "architectural_lineages": population["architectural_lineage_count"],
        "current_variants": d202["development_case_collections"][0]["total"],
        "consumer_ast_blocked_variants": d202["development_case_collections"][0]
            ["first_stop_reasons"]["UNSUPPORTED_CONSUMER_AST_REQUIRED"],
        "nested_mapping_variants": d202["development_case_collections"][0]
            ["unsupported_split"]["Payy"]["target_variants"],
        "historical_attempts": history["analysis_attempts"],
        "historical_unique_projects": history["unique_projects"],
        "historical_repeat_attempts": history["repeat_attempts"],
    }
    require_exact(d202_actual, exp, "D2-02 selected results")

    d203 = load_json(ROOT / "docs/d2/claim-ledger-v1.json")
    d203_related = load_json(ROOT / "docs/d2/related-work-matrix-v1.json")
    require_exact({"research_verdict": "UNKNOWN", "claims": len(d203["claims"]),
                   "closest_works": len(d203_related["works"])}, steps["D2-03"],
                  "D2-03 selected results")

    d204 = load_json(ROOT / "protocols/d2/d2-04-taxonomy-preparation-v1.json")
    blank = load_json(ROOT / "docs/taxonomy/d2-blank-annotation-form-v1.json")
    require_exact(d204["status"], steps["D2-04"]["status"], "D2-04 status")
    require_exact(d204["research_verdict"], steps["D2-04"]["research_verdict"],
                  "D2-04 verdict")
    require_exact(blank["template_status"], "BLANK_NO_JUDGMENTS", "D2-04 blank status")
    for axis in ("causes", "consequences", "roles"):
        require(all(value is None for value in blank[axis].values()),
                f"D2-04 {axis} form is not blank")
    require(blank["rater"]["human_id"] is None and blank["relevance"] is None,
            "D2-04 contains a human judgment")
    require_exact(sum(value is not None for axis in ("causes", "consequences", "roles")
                      for value in blank[axis].values()),
                  steps["D2-04"]["human_ratings"], "D2-04 human ratings")
    require_exact(steps["D2-04"]["agreement_result"], False,
                  "D2-04 agreement result availability")

    d205 = load_json(ROOT / "protocols/d2/d2-05-early-comparison-draft-v1.json")
    require_exact(d205["status"], steps["D2-05"]["status"], "D2-05 status")
    require_exact(d205["research_verdict"], steps["D2-05"]["research_verdict"],
                  "D2-05 verdict")
    require_exact(d205["execution_boundary"]["scored_execution_authorized"], False,
                  "D2-05 score authorization")
    require("score_rows" not in d205, "D2-05 draft unexpectedly contains score rows")
    require_exact(steps["D2-05"]["scored_rows"], 0, "D2-05 scored rows")

    d206a = load_json(resolve_evidence_path(
        "results/raw/D2-06A/construction-03/run-summary.json", sidecar))
    exp = steps["D2-06A"]
    d206a_actual = {
        "status": d206a["status"],
        "research_verdict": d206a["research_verdict"],
        "scored": d206a["scored"],
        "baseline_case_arms": d206a["baseline_case_arms"],
        "construction_status_counts": d206a["baseline_construction_status_counts"],
        "transformations": d206a["transformation_counts"],
        "equal_policy_information": d206a["equal_policy_information"],
    }
    require_exact(d206a_actual, exp, "D2-06A selected results")

    d206b = load_json(resolve_evidence_path("results/raw/D2-06B/recovery-01/smoke-summary.json", sidecar))
    exp = steps["D2-06B"]
    d206b_actual = {
        "status": d206b["status"],
        "research_verdict": d206b["research_verdict"],
        "scored": d206b["scored"],
        "case_count": d206b["case_count"],
        "adapter_smoke_status": d206b["adapter_smoke_status"],
        "native_exit_codes": {row["case_id"]: row["exit_code"] for row in d206b["cases"]},
        "target_detection_denominator": d206b["target_detection_denominator"],
        "safe_control_denominator": d206b["safe_control_denominator"],
    }
    require_exact(d206b_actual, exp, "D2-06B selected results")

    d207 = load_json(resolve_evidence_path(
        "results/raw/D2-07-recovery-01/finalization-summary.json", sidecar))
    exp = steps["D2-07"]
    d207_actual = {
        "status": d207["status"],
        "research_verdict": d207["research_verdict"],
        "gate_a_decision": d207["gate_a_decision"],
        "candidate_case_count": d207["candidate_case_count"],
        "internal_arm_count": d207["internal_arm_count"],
        "external_inventory_count": d207["external_inventory_count"],
        "scored_arm_count": d207["scored_arm_count"],
        "blocker_codes": d207["blocker_codes"],
    }
    require_exact(d207_actual, exp, "D2-07 selected results")

    d208 = load_json(resolve_evidence_path("results/raw/D2-08/run-summary.json", sidecar))
    exp = steps["D2-08"]
    d208_actual = {
        "status": d208["status"],
        "research_verdict": d208["research_verdict"],
        "scored": d208["scored"],
        "bundle_count": d208["bundle_count"],
        "identities_per_bundle": d208["identities_per_bundle"],
        "facts_per_bundle": d208["facts_per_bundle"],
        "mapping_count": d208["mapping_count"],
        "negative_fixture_count": d208["negative_fixture_count"],
        "name_influence_audit": d208["name_influence_audit"],
    }
    require_exact(d208_actual, exp, "D2-08 selected results")

    d209 = load_json(resolve_evidence_path("results/raw/D2-09/summary.json", sidecar))
    exp = steps["D2-09"]
    d209_actual = {
        "status": d209["status"],
        "research_verdict": d209["research_verdict"],
        "case_count": d209["case_count"],
        "equal_input_arm_parity_count": d209["equal_input_arm_parity_count"],
        "mechanical_state_counts": d209["mechanical_state_counts"],
        "effective_state_counts": d209["effective_state_counts"],
        "score_rows": len(d209["score_rows"]),
    }
    require_exact(d209_actual, exp, "D2-09 selected results")

    d210 = load_json(resolve_evidence_path("results/raw/D2-10/run-02/run-summary.json", sidecar))
    inventory210 = load_json(resolve_evidence_path(
        "results/raw/D2-10/run-02/fact-type-inventory.json", sidecar))
    typed_inventory210 = load_json(resolve_evidence_path(
        "results/raw/D2-10/run-02/typed-inventory.json", sidecar))
    exp = steps["D2-10"]
    require_exact(exp["authoritative_namespace"], "results/raw/D2-10/run-02",
                  "D2-10 authoritative namespace")
    d210_actual = {
        "authoritative_namespace": exp["authoritative_namespace"],
        "status": d210["status"],
        "research_verdict": d210["research_verdict"],
        "fact_rows": len(inventory210["rows"]),
        "producer_guarantee": typed_inventory210["summary"]["producer_guarantee_count"],
        "derived_eligible_consumer_used": typed_inventory210["summary"]
            ["consumer_reliance_count"],
        "effective_result": d210["effective_result"],
        "identity_chain_status": d210["identity_chain_status"],
        "semantic_controls": d210["semantic_controls"],
        "adversarial_controls": d210["adversarial_controls"],
        "d1p40_regressions": d210["d1p40_regressions"],
        "equal_input_semantic_parity": d210["equal_input_semantic_parity"],
    }
    require_exact(d210_actual, exp, "D2-10 selected results")

    d211 = load_json(ROOT / "protocols/d2/d2-11-14-dependency-disposition-v1.json")
    require_exact(d211["status"], expected["downstream"]["steps_11_14"],
                  "Steps 11-14 disposition")
    d215 = load_json(ROOT / "protocols/d2/d2-15-17-readiness-v1.json")
    combined_15 = " / ".join((d215["status"], d215["execution_status"], d215["gate_c_status"]))
    require_exact(combined_15, expected["downstream"]["steps_15_17"],
                  "Steps 15-17 disposition")

    metadata = metadata_profile()
    return {
        "schema": "bindcheck.d2.partial-artifact-profile-result/v1",
        "profile": "recompute",
        "status": "PASS",
        "source": retained["source"],
        "retained_verification": retained,
        "selected_steps_recomputed": list(steps),
        "downstream_dispositions": "PASS",
        "step18": metadata["step18"],
        "research_verdict": "UNKNOWN",
    }


def run_command(argv: list[str], output_dir: Path, name: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (output_dir / f"{name}.stdout").write_bytes(proc.stdout)
    (output_dir / f"{name}.stderr").write_bytes(proc.stderr)
    result = {"name": name, "argv": argv, "returncode": proc.returncode}
    if proc.returncode != 0:
        raise ArtifactError(f"mechanical command failed: {result}")
    return result


def selected_mechanical_results(base: Path) -> dict[str, Any]:
    d208 = load_json(base / "D2-08/run-summary.json")
    d209 = load_json(base / "D2-09/summary.json")
    d210 = load_json(base / "D2-10/run-summary.json")
    inventory = load_json(base / "D2-10/fact-type-inventory.json")
    typed = load_json(base / "D2-10/typed-inventory.json")
    return {
        "D2-08": {
            "status": d208["status"], "research_verdict": d208["research_verdict"],
            "scored": d208["scored"], "bundle_count": d208["bundle_count"],
            "identities_per_bundle": d208["identities_per_bundle"],
            "facts_per_bundle": d208["facts_per_bundle"],
            "mapping_count": d208["mapping_count"],
            "negative_fixture_count": d208["negative_fixture_count"],
            "name_influence_audit": d208["name_influence_audit"],
        },
        "D2-09": {
            "status": d209["status"], "research_verdict": d209["research_verdict"],
            "case_count": d209["case_count"],
            "equal_input_arm_parity_count": d209["equal_input_arm_parity_count"],
            "mechanical_state_counts": d209["mechanical_state_counts"],
            "effective_state_counts": d209["effective_state_counts"],
            "score_rows": len(d209["score_rows"]),
        },
        "D2-10": {
            "status": d210["status"], "research_verdict": d210["research_verdict"],
            "fact_rows": len(inventory["rows"]),
            "producer_guarantee": typed["summary"]["producer_guarantee_count"],
            "derived_eligible_consumer_used": typed["summary"]["consumer_reliance_count"],
            "effective_result": d210["effective_result"],
            "identity_chain_status": d210["identity_chain_status"],
            "semantic_controls": d210["semantic_controls"],
            "adversarial_controls": d210["adversarial_controls"],
            "d1p40_regressions": d210["d1p40_regressions"],
            "equal_input_semantic_parity": d210["equal_input_semantic_parity"],
        },
    }


def rerun_mechanical(args: argparse.Namespace) -> dict[str, Any]:
    require(args.source == "current-workspace", "mechanical rerun supports current-workspace only")
    require(args.sidecar_root is None, "mechanical rerun does not accept a sidecar")
    target = validated_work_path(args.run_id)
    WORK.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    commands: list[dict[str, Any]] = []
    commands.append(run_command(
        [sys.executable, "scripts/d2_step7_gate_a.py", "--validate-only"],
        target, "step7-validate"))
    for step, script, protocol in (
        ("D2-08", "scripts/d2_step8_identity.py", "protocols/d2/d2-08-compiler-identity-v1.json"),
        ("D2-09", "scripts/d2_step9_authorization_boundary.py", "protocols/d2/d2-09-authorization-boundary-v1.json"),
        ("D2-10", "scripts/d2_step10_typed_extraction.py", "protocols/d2/d2-10-typed-extraction-v2.json"),
    ):
        commands.append(run_command(
            [sys.executable, script, "--protocol", protocol, "--validate-only"],
            target, f"{step.lower()}-validate"))
        commands.append(run_command(
            [sys.executable, script, "--protocol", protocol, "--out", str(target / step)],
            target, f"{step.lower()}-run"))
    actual = selected_mechanical_results(target)
    expected = load_json(ARTIFACT / "expected-results-v1.json")["steps"]
    for step in ("D2-08", "D2-09", "D2-10"):
        selected_expected = dict(expected[step])
        selected_expected.pop("authoritative_namespace", None)
        require_exact(actual[step], selected_expected, f"fresh {step} selected results")
    summary = {
        "schema": "bindcheck.d2.partial-artifact-mechanical-rerun/v1",
        "artifact_status": STATUS,
        "profile": "rerun-mechanical",
        "status": "PASS",
        "research_verdict": "UNKNOWN",
        "fixture_label": "UNREVIEWED_DEVELOPMENT_FIXTURE",
        "scored": False,
        "output_root": target.relative_to(ROOT).as_posix(),
        "commands": commands,
        "categorical_results": actual,
        "excluded_equality_fields": load_json(ARTIFACT / "expected-results-v1.json")
            ["comparison_policy"]["not_compared_for_fresh_reruns"],
    }
    (target / "profile-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="profile", required=True)
    subparsers.add_parser("metadata", help="validate packaged metadata only")
    for name in ("verify-retained", "recompute"):
        child = subparsers.add_parser(name)
        child.add_argument("--source", choices=("current-workspace", "sidecar"), required=True)
        child.add_argument("--sidecar-root")
    rerun = subparsers.add_parser("rerun-mechanical")
    rerun.add_argument("--source", choices=("current-workspace",), required=True)
    rerun.add_argument("--sidecar-root")
    rerun.add_argument("--run-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.profile == "metadata":
            result = metadata_profile()
        elif args.profile == "verify-retained":
            sidecar = source_root(args)
            result = {
                "schema": "bindcheck.d2.partial-artifact-profile-result/v1",
                "profile": "verify-retained",
                **verify_retained_evidence(sidecar),
            }
        elif args.profile == "recompute":
            result = recompute_results(source_root(args))
        elif args.profile == "rerun-mechanical":
            result = rerun_mechanical(args)
        else:  # pragma: no cover - argparse prevents this branch.
            raise ArtifactError(f"unsupported profile: {args.profile}")
    except ArtifactError as exc:
        json.dump({"profile": args.profile, "status": "FAIL", "error": str(exc)},
                  sys.stderr, indent=2, sort_keys=True)
        sys.stderr.write("\n")
        return 1
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
