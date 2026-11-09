from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import tempfile
import time
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_LEDGER = ROOT / "dataset" / "source-corpus-v2.csv"
RECALL_LEDGER = ROOT / "dataset" / "recall-set-v2.csv"
RECALL_EXPECTATIONS = ROOT / "eval" / "recall-expectations.csv"
CLI = ROOT / "bindcheck-zk"

PLAN_SOURCE_SHA256 = "07210625783a21a6128ea3f99402fc4a48b36922056241649999547a374b0c95"
SAMPLE_SALT = "bindcheck-eval-v2-family-sample-2026-11-03|"
STRATA = (
    "verified-deployed",
    "deployed-address-in-docs",
    "audited-production",
    "hackathon-student",
    "unclassified",
)
STRATUM_QUOTA = 60
PATTERNS = ("P1", "P2", "P3", "P4", "P5")
VERDICTS = {"VIOLATION", "VERIFIED_WITHIN_SCOPE", "UNKNOWN"}
APPLICABILITIES = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
BASELINES = ("slither", "circomspect", "picus", "zkap")

# These are evaluation constants, not command-line tuning knobs. The analyzer
# has its own 120-second internal repository budget.
FETCH_TIMEOUT_SECONDS = 300.0
ANALYZER_TIMEOUT_SECONDS = 150.0
BASELINE_BUDGET_SECONDS = 120.0
BASELINE_TIMEOUT_SECONDS = 150.0
METADATA_TIMEOUT_SECONDS = 45.0


class EvaluationError(RuntimeError):
    """Fail-closed harness error."""


class GateError(EvaluationError):
    """The held-out execution authorization gate did not pass."""


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def atomic_write_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: pathlib.Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _row_sha256(row: Mapping[str, str]) -> str:
    return sha256_bytes(canonical_json(dict(row)).encode("utf-8"))


def select_families(
    rows: Sequence[dict[str, str]],
    split: str,
    *,
    max_families: int | None = None,
) -> list[dict[str, Any]]:
    """Apply the frozen EVAL rule, or a deterministic DEV-only smoke subset."""
    split = split.upper()
    if split not in {"DEV", "EVAL"}:
        raise EvaluationError(f"unsupported split: {split}")
    if split == "EVAL" and max_families is not None:
        raise EvaluationError("EVAL selection cannot be truncated or tuned")

    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        family = row.get("v2_family_id", "")
        if family:
            by_family[family].append(row)
    dev_families = {
        row["v2_family_id"]
        for row in rows
        if row.get("split") == "DEV" and row.get("v2_family_id")
    }
    canonical = [
        row
        for row in rows
        if row.get("split") == split and row.get("v2_disposition") == "in-scope"
    ]
    if split == "EVAL":
        canonical = [row for row in canonical if row["v2_family_id"] not in dev_families]

    counts: dict[str, int] = defaultdict(int)
    for row in canonical:
        counts[row["v2_family_id"]] += 1
    duplicates = sorted(family for family, count in counts.items() if count != 1)
    if duplicates:
        raise EvaluationError(f"eligible families lack one canonical row: {duplicates[:5]}")

    stratum_rank = {name: index for index, name in enumerate(STRATA)}
    selected: list[dict[str, Any]] = []
    for row in canonical:
        family = row["v2_family_id"]
        member_maturities = {
            member.get("v2_maturity") or member.get("maturity") or "unclassified"
            for member in by_family[family]
        }
        unknown = sorted(member_maturities - set(STRATA))
        if unknown:
            raise EvaluationError(f"family {family} has unknown maturity labels: {unknown}")
        maturity = min(member_maturities, key=lambda value: stratum_rank[value])
        sample_hash = sha256_bytes((SAMPLE_SALT + family).encode("utf-8"))
        selected.append({
            "family_id": family,
            "sample_hash": sample_hash,
            "stratum": maturity,
            "repository": row["repository"],
            "commit": row["commit"],
            "row_sha256": _row_sha256(row),
            "circuit_paths": row.get("v2_circuit_paths", ""),
            "verifier_paths": row.get("v2_verifier_paths", ""),
            "consumer_paths": row.get("v2_consumer_paths", ""),
        })

    if split == "EVAL":
        result: list[dict[str, Any]] = []
        for stratum in STRATA:
            members = sorted(
                (item for item in selected if item["stratum"] == stratum),
                key=lambda item: (item["sample_hash"], item["family_id"]),
            )
            result.extend(members[:STRATUM_QUOTA])
        selected = result
    else:
        selected.sort(key=lambda item: (item["sample_hash"], item["family_id"]))
        if max_families is not None:
            if max_families <= 0:
                raise EvaluationError("--max-families must be positive")
            selected = selected[:max_families]

    for rank, item in enumerate(selected, 1):
        item["rank"] = rank
    return selected


SELECTION_FIELDS = (
    "rank", "family_id", "sample_hash", "stratum", "repository", "commit",
    "row_sha256", "circuit_paths", "verifier_paths", "consumer_paths",
)


def selection_document(
    selected: Sequence[dict[str, Any]], *, split: str, dataset: pathlib.Path
) -> dict[str, Any]:
    return {
        "schema": "bindcheck-zk.family-selection/v1",
        "split": split.upper(),
        "dataset": dataset.relative_to(ROOT).as_posix() if dataset.is_relative_to(ROOT) else str(dataset),
        "dataset_sha256": sha256_file(dataset),
        "sample_salt": SAMPLE_SALT,
        "stratum_order": list(STRATA),
        "per_stratum_quota": STRATUM_QUOTA,
        "families": list(selected),
    }


def write_selection(output: pathlib.Path, document: dict[str, Any]) -> None:
    """Persist the immutable selection before any analyzer process starts."""
    json_path = output / "selected-families.json"
    csv_path = output / "selected-families.csv"
    if json_path.exists():
        if load_json(json_path) != document:
            raise EvaluationError(f"existing selection differs: {json_path}")
    else:
        atomic_write_json(json_path, document)

    rows = document["families"]
    lines: list[str] = []
    with tempfile.TemporaryFile(mode="w+", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SELECTION_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.seek(0)
        csv_text = handle.read()
    if csv_path.exists():
        if csv_path.read_text(encoding="utf-8") != csv_text:
            raise EvaluationError(f"existing selection CSV differs: {csv_path}")
    else:
        atomic_write_text(csv_path, csv_text)


def family_directory(output: pathlib.Path, family: Mapping[str, Any]) -> pathlib.Path:
    return output / "families" / f"{int(family['rank']):03d}-{family['sample_hash'][:12]}"


def run_command(
    argv: Sequence[str],
    *,
    cwd: pathlib.Path | None,
    timeout: float,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.monotonic()
    process_env = dict(os.environ)
    if env:
        process_env.update(env)
    process = subprocess.Popen(
        list(argv),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=process_env,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    return {
        "argv": list(argv),
        "cwd": str(cwd) if cwd else None,
        "started_utc": started_utc,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "timeout_seconds": timeout,
        "exit_status": None if timed_out else process.returncode,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }


def command_record_without_output(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}


def _git(root: pathlib.Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _tag_message(root: pathlib.Path, tag: str) -> str:
    object_type = _git(root, "cat-file", "-t", f"refs/tags/{tag}")
    if object_type != "tag":
        raise GateError(f"{tag} is lightweight; an annotated freeze tag is required")
    raw = _git(root, "cat-file", "-p", f"refs/tags/{tag}")
    return raw.split("\n\n", 1)[1] if "\n\n" in raw else ""


def _tagged_file_sha256(root: pathlib.Path, tag: str, path: pathlib.Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise GateError(f"tagged dataset path is outside repository: {path}") from exc
    completed = subprocess.run(
        ["git", "show", f"{tag}:{relative}"], cwd=root, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise GateError(f"{tag} does not contain {relative}")
    return sha256_bytes(completed.stdout)


def parse_tag_metadata(message: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in message.splitlines():
        match = re.fullmatch(r"([A-Z][A-Z0-9_]*)=([0-9a-f]{64})", line.strip())
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata


def freeze_digest(root: pathlib.Path) -> tuple[str, str]:
    completed = subprocess.run(
        [str(root / "freeze.sh")], cwd=root, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise GateError(f"freeze.sh failed: {completed.stderr.strip()}")
    matches = re.findall(r"^BINDCHECK_ZK_CONTENT_SHA256=([0-9a-f]{64})$", completed.stdout, re.M)
    if len(matches) != 1:
        raise GateError("freeze.sh did not emit exactly one content digest")
    return matches[0], sha256_bytes(completed.stdout.encode("utf-8"))


def check_eval_gate(
    root: pathlib.Path,
    source_ledger: pathlib.Path,
    *,
    environ: Mapping[str, str] | None = None,
    recall_ledger: pathlib.Path | None = None,
    recall_expectations: pathlib.Path | None = None,
) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    if environ.get("BINDCHECK_EVAL_AUTHORIZED") != "1":
        raise GateError("BINDCHECK_EVAL_AUTHORIZED must equal 1")
    head = _git(root, "rev-parse", "HEAD")
    tags = [
        tag for tag in _git(root, "tag", "--points-at", "HEAD", "--list", "bindcheck-zk-frozen-*").splitlines()
        if tag
    ]
    if not tags:
        raise GateError("no bindcheck-zk-frozen-* tag exists at HEAD")
    analyzer_digest, freeze_output_sha256 = freeze_digest(root)
    source_digest = sha256_file(source_ledger)
    recall_digest = sha256_file(recall_ledger) if recall_ledger else None
    expectations_digest = sha256_file(recall_expectations) if recall_expectations else None

    failures: list[str] = []
    valid: list[tuple[str, dict[str, str]]] = []
    for tag in sorted(tags):
        try:
            metadata = parse_tag_metadata(_tag_message(root, tag))
        except GateError as exc:
            failures.append(str(exc))
            continue
        expected = {
            "BINDCHECK_ZK_CONTENT_SHA256": analyzer_digest,
            "SOURCE_CORPUS_V2_SHA256": source_digest,
        }
        if recall_digest is not None:
            expected["RECALL_SET_V2_SHA256"] = recall_digest
        if expectations_digest is not None:
            expected["RECALL_EXPECTATIONS_SHA256"] = expectations_digest
        mismatches = [
            f"{key}: tag={metadata.get(key)!r} observed={value}"
            for key, value in expected.items()
            if metadata.get(key) != value
        ]
        if mismatches:
            failures.append(f"{tag}: " + "; ".join(mismatches))
        else:
            valid.append((tag, metadata))
    if not valid:
        raise GateError("no freeze tag at HEAD matches analyzer and dataset hashes: " + " | ".join(failures))
    tag, metadata = valid[-1]
    dataset_tags = [
        item for item in _git(root, "tag", "--list", "bindcheck-zk-dataset-v2-*").splitlines()
        if item
    ]
    valid_dataset_tags: list[str] = []
    dataset_failures: list[str] = []
    for dataset_tag in sorted(dataset_tags):
        try:
            dataset_metadata = parse_tag_metadata(_tag_message(root, dataset_tag))
            tagged_source_digest = _tagged_file_sha256(root, dataset_tag, source_ledger)
            if dataset_metadata.get("SOURCE_CORPUS_V2_SHA256") != source_digest:
                raise GateError(f"{dataset_tag} annotation has a different source-corpus hash")
            if tagged_source_digest != source_digest:
                raise GateError(f"{dataset_tag} contains different source-corpus bytes")
            if recall_digest is not None:
                tagged_recall_digest = _tagged_file_sha256(root, dataset_tag, recall_ledger)
                if dataset_metadata.get("RECALL_SET_V2_SHA256") != recall_digest:
                    raise GateError(f"{dataset_tag} annotation has a different recall-set hash")
                if tagged_recall_digest != recall_digest:
                    raise GateError(f"{dataset_tag} contains different recall-set bytes")
            valid_dataset_tags.append(dataset_tag)
        except GateError as exc:
            dataset_failures.append(str(exc))
    if not valid_dataset_tags:
        detail = " | ".join(dataset_failures) if dataset_failures else "none found"
        raise GateError(
            "no annotated bindcheck-zk-dataset-v2-* tag contains the current tagged dataset: "
            + detail
        )
    dataset_tag = valid_dataset_tags[-1]
    return {
        "authorized": True,
        "head": head,
        "tag": tag,
        "dataset_tag": dataset_tag,
        "all_matching_tags": [item[0] for item in valid],
        "tag_metadata": metadata,
        "analyzer_content_sha256": analyzer_digest,
        "freeze_output_sha256": freeze_output_sha256,
        "source_corpus_v2_sha256": source_digest,
        "recall_set_v2_sha256": recall_digest,
        "recall_expectations_sha256": expectations_digest,
    }


def aggregate_payload_verdict(payload: Mapping[str, Any], pattern: str) -> tuple[str, list[str]]:
    """Return one pattern's verdict and unresolved reasons, never a cross-pattern verdict."""
    if pattern not in PATTERNS:
        raise EvaluationError(f"unknown pattern: {pattern}")
    patterns = payload.get("patterns") or {}
    triples = payload.get("triples") or []
    item = patterns.get(pattern) or {}
    verdict = item.get("verdict", "UNKNOWN")
    reasons: list[str] = []
    if verdict not in VERDICTS:
        reasons.append(f"INVALID_VERDICT:{verdict}")
        verdict = "UNKNOWN"
    if verdict == "UNKNOWN":
        triple_reasons = {
            str(result.get("reason") or "UNKNOWN_UNSPECIFIED")
            for triple in triples
            for result in [(triple.get("patterns") or {}).get(pattern) or {}]
            if result.get("verdict") == "UNKNOWN"
        }
        reasons.extend(sorted(triple_reasons) if triple_reasons else
                       (str(reason) for reason in item.get("reasons", []) or ["UNKNOWN_UNSPECIFIED"]))
    fatal = (payload.get("run") or {}).get("fatal_reason")
    if verdict == "UNKNOWN" and fatal:
        reasons.append(str(fatal))
    return str(verdict), sorted(set(reasons))


def normalize_tool_payload(tool: str, payload: Mapping[str, Any], raw_path: str) -> dict[str, Any]:
    native_findings: list[Any] = []
    if tool == "arm-c":
        run = payload.get("run") or {}
        result = payload.get("result") or {}
        native_findings = list(result.get("findings") or [])
        completed = run.get("status") == "completed"
        raw_verdict = result.get("verdict", "UNKNOWN")
        verdict = raw_verdict if completed and raw_verdict in VERDICTS else "UNKNOWN"
        applicability = "APPLICABLE" if completed else "UNKNOWN"
        reasons = sorted({str(item.get("code")) for item in native_findings if item.get("code")})
        if not completed:
            reasons.append(str(run.get("fatal_reason") or "ARM_C_INCOMPLETE"))
        patterns = {}
    elif tool == "bindcheck-zk":
        patterns: dict[str, dict[str, Any]] = {}
        for pattern in PATTERNS:
            item = (payload.get("patterns") or {}).get(pattern) or {}
            verdict, unresolved_reasons = aggregate_payload_verdict(payload, pattern)
            applicability = item.get("applicability", "UNKNOWN")
            if applicability not in APPLICABILITIES:
                applicability = "UNKNOWN"
                unresolved_reasons.append("INVALID_APPLICABILITY")
            patterns[pattern] = {
                "verdict": verdict,
                "applicability": applicability,
                "reasons": sorted(set(map(str, item.get("reasons") or unresolved_reasons))),
                "unknown_reasons": unresolved_reasons if verdict == "UNKNOWN" else [],
                "unknown_reason_codes": sorted(set(map(str, item.get("unknown_reason_codes") or []))),
                "evidence_grade": item.get("evidence_grade"),
                "results": item.get("results"),
            }
        # A single verdict has no semantic meaning across P1–P5. This field
        # only indicates that a repository-level result requires pattern review.
        verdict, reasons, applicability = "UNKNOWN", ["PER_PATTERN_RESULT"], "UNKNOWN"
    else:
        raw_verdict = payload.get("verdict", "UNKNOWN")
        pattern_summaries = payload.get("patterns") or {}
        native_reasons = sorted({str(reason) for item in pattern_summaries.values()
                                 for reason in (item.get("reasons") or [])})
        reasons = sorted(set(map(str, payload.get("reasons") or [])) | set(native_reasons))
        if raw_verdict == "NOT_APPLICABLE" or "BASELINE_NOT_APPLICABLE" in reasons:
            applicability = "NOT_APPLICABLE"
        elif (payload.get("run") or {}).get("status") == "completed":
            applicability = "APPLICABLE"
        else:
            applicability = "UNKNOWN"
        verdict = raw_verdict if raw_verdict in VERDICTS else "UNKNOWN"
        if raw_verdict not in VERDICTS | {"NOT_APPLICABLE"}:
            applicability = "UNKNOWN"
            reasons.append(f"INVALID_VERDICT:{raw_verdict}")
        patterns = {}
    return {
        "schema": "bindcheck-zk.eval-tool-result/v1",
        "tool": tool,
        "verdict": verdict,
        "applicability": applicability,
        "reasons": reasons,
        "run_status": (payload.get("run") or {}).get("status"),
        "fatal_reason": (payload.get("run") or {}).get("fatal_reason"),
        "patterns": patterns,
        "native_findings": native_findings,
        "coverage": payload.get("coverage") or {},
        "raw_result": raw_path,
        "raw_schema": payload.get("schema"),
    }


def unknown_tool_result(tool: str, reason: str, detail: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "bindcheck-zk.eval-tool-result/v1",
        "tool": tool,
        "verdict": "UNKNOWN",
        "applicability": "UNKNOWN",
        "reasons": [reason],
        "run_status": "UNKNOWN",
        "fatal_reason": reason,
        "patterns": {
            pattern: {"verdict": "UNKNOWN", "applicability": "UNKNOWN",
                      "reasons": [reason], "unknown_reasons": [reason],
                      "unknown_reason_codes": [reason]}
            for pattern in PATTERNS
        } if tool == "bindcheck-zk" else {},
        "coverage": {"failures": [{"reason": reason, "detail": detail}]},
        "raw_result": None,
        "raw_schema": None,
    }
    return result


def pattern_locations(payload: Mapping[str, Any], pattern: str, verdict: str = "VIOLATION") -> list[str]:
    locations: set[str] = set()
    for triple in payload.get("triples", []) or []:
        result = (triple.get("patterns") or {}).get(pattern) or {}
        if result.get("verdict") != verdict:
            continue
        location = result.get("location") or {}
        path = location.get("path")
        if not path:
            continue
        value = str(path)
        if location.get("line") is not None:
            value += f":{location['line']}"
            if location.get("column") is not None:
                value += f":{location['column']}"
        locations.add(value)
    return sorted(locations)


def analyzer_build_success(payload: Mapping[str, Any]) -> bool:
    builds = (payload.get("coverage") or {}).get("builds", []) or []
    return any(
        (item.get("record") or {}).get("kind") == "existing"
        or (
            (item.get("record") or {}).get("exit_status") == 0
            and not (item.get("record") or {}).get("timed_out")
        )
        for item in builds
    )


def directory_bytes(path: pathlib.Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        try:
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        except FileNotFoundError:
            continue
    return total


def scrub_network_environment() -> dict[str, str]:
    return {
        "NO_PROXY": "*",
        "no_proxy": "*",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
        "http_proxy": "",
        "https_proxy": "",
        "all_proxy": "",
    }


def summarize_command(record: Mapping[str, Any], *, include_output_hashes: bool = True) -> dict[str, Any]:
    result = command_record_without_output(record)
    if include_output_hashes:
        result["stdout_sha256"] = sha256_bytes(str(record.get("stdout", "")).encode("utf-8"))
        result["stderr_sha256"] = sha256_bytes(str(record.get("stderr", "")).encode("utf-8"))
        result["stdout_bytes"] = len(str(record.get("stdout", "")).encode("utf-8"))
        result["stderr_bytes"] = len(str(record.get("stderr", "")).encode("utf-8"))
    return result


def require_relative_checkout(work_root: pathlib.Path, checkout: pathlib.Path) -> None:
    try:
        checkout.resolve().relative_to(work_root.resolve())
    except ValueError as exc:
        raise EvaluationError(f"checkout escapes work root: {checkout}") from exc


def tool_command(tool: str, checkout: pathlib.Path) -> tuple[list[str], float]:
    if tool == "bindcheck-zk":
        return [str(CLI), "analyze", str(checkout)], ANALYZER_TIMEOUT_SECONDS
    if tool not in BASELINES:
        raise EvaluationError(f"unknown tool: {tool}")
    return [
        str(CLI), "baseline", tool, str(checkout),
        "--timeout", str(int(BASELINE_BUDGET_SECONDS)),
    ], BASELINE_TIMEOUT_SECONDS


def validate_verdict(value: str) -> str:
    if value not in VERDICTS:
        raise EvaluationError(f"invalid evaluation verdict: {value}")
    return value


def tally_unknown_reasons(records: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        if record.get("verdict") != "UNKNOWN":
            continue
        reasons = record.get("reasons") or ["UNKNOWN_UNSPECIFIED"]
        for reason in set(map(str, reasons)):
            counts[reason] += 1
    return dict(sorted(counts.items()))
