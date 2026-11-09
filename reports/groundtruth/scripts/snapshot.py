#!/usr/bin/env python3
"""Build reports/groundtruth/SNAPSHOT.json from the repository and retained raw evidence.

Read-only with respect to the analyzer: it hashes files with the same manifest
rule as bindcheck_zk/freeze.py but never imports or runs the analyzer.

Usage (from repository root):
    python3 -I reports/groundtruth/scripts/snapshot.py \
        --raw /Users/imranpollob/Coding/bc/bindcheck-zk/results/raw \
        --out reports/groundtruth/SNAPSHOT.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

ANALYZER_COMMITS = {
    "9ffc8c9": "Build unified bindcheck-zk analyzer (T23)",
    "4018053": "Complete full DEV coverage and freeze readiness (T24)",
    "cd56c24": "feat: report applicability and improve DEV decisions (T25)",
}

# Controlling-status assertions are copied from the cited report lines; the
# script verifies that each cited directory exists and recomputes its hash.
CONTROLLING = {
    "T23/run-20261104T030439Z-3115": ("controlling", "reports/T23.md:51"),
    "T23/run-20261104T030035Z-1983": ("non-controlling (accidental duplicate, no manifest)", "reports/T23.md:85-89"),
    "T24/before-20261105T020201Z-27822": ("controlling 'before'", "reports/T24.md:31"),
    "T24/after-20261105T023639Z-38427": ("controlling 'after'", "reports/T24.md:34"),
    "T24/after-20261106T153640Z-15958": ("non-controlling T25-era diagnostic stored under T24", "reports/T25.md:207-211"),
    "T24/after-20261106T155252Z-22241": ("non-controlling T25-era diagnostic stored under T24", "reports/T25.md:207-211"),
    "T25/after-20261106T155532Z-23564": ("controlling", "reports/T25.md:142"),
    "T26/dev-dry-run": ("non-controlling (sandbox DNS failure; no analyzer ran)", "reports/T26.md:99-101"),
    "T26/dev-dry-run-network": ("controlling five-family DEV harness run", "reports/T26.md:105-108"),
    "T26/eval-metadata-07210625783a": ("controlling metadata-only (no clone, no analysis)", "reports/T26.md:131-144"),
}

TRACKED_HASH_FILES = [
    "dataset/source-corpus-v2.csv",
    "dataset/recall-set-v2.csv",
    "dataset/recall-set-v2-summary.json",
    "eval/recall-expectations.csv",
    "reports/T24-full-dev-ledger.csv",
    "reports/T24-warning-adjudication.csv",
    "reports/T25-full-dev-ledger.csv",
    "reports/T25-warning-adjudication.csv",
    "dataset/onchain-census-summary.json",
    "dataset/EVAL-SAMPLE-PLAN-v2.md",
    "tests/controls/expected.json",
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def freeze_digest_at(commit: str) -> tuple[str, int]:
    """Re-implement bindcheck_zk/freeze.py's manifest rule on a commit's tree."""
    archive = git_bytes("archive", "--format=tar", commit, "bindcheck-zk", "requirements-bindcheck-zk.txt", "bindcheck_zk")
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                files[member.name] = tar.extractfile(member).read()  # type: ignore[union-attr]
    names = ["bindcheck-zk", "requirements-bindcheck-zk.txt"]
    names += sorted(n for n in files if re.fullmatch(r"bindcheck_zk/[^/]+\.py", n))
    names += ["bindcheck_zk/config.json", "bindcheck_zk/vendor-lock.json"]
    entries = [(n, hashlib.sha256(files[n]).hexdigest()) for n in names if n in files]
    payload = "".join(f"{d}  {n}\n" for n, d in entries).encode()
    return hashlib.sha256(payload).hexdigest(), len(entries)


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_directories(raw: pathlib.Path) -> list[dict]:
    rows = []
    pat = re.compile(rb'"content_sha256":\s*"([0-9a-f]{64})"')
    for task in ("T23", "T24", "T25", "T26"):
        base = raw / task
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            hashes: dict[str, int] = {}
            nfiles = 0
            for f in d.rglob("*"):
                if f.is_file():
                    nfiles += 1
                    if f.suffix == ".json":
                        for m in pat.finditer(f.read_bytes()):
                            h = m.group(1).decode()
                            hashes[h] = hashes.get(h, 0) + 1
            rel = f"{task}/{d.name}"
            status, cite = CONTROLLING.get(rel, ("not cited as controlling in any report", ""))
            rows.append({
                "directory": f"results/raw/{rel}",
                "files": nfiles,
                "tool_content_sha256_values": hashes,
                "status": status,
                "status_source": cite,
            })
    extras = {
        "feasibility-v2": ("produced by feasibility/v2/*.sh (E4 harnesses, circomspect, historical recall), not by bindcheck_zk; timestamps 2026-11-03T17:56Z-18:45Z predate commit 9ffc8c9", "feasibility/v2/REPORT.md"),
        "dataset-track-b": ("produced by dataset/run_track_b.sh (Track B protocol freeze), not by bindcheck_zk", "dataset/REPORT-v2.md"),
    }
    for extra, (status, cite) in extras.items():
        d = raw / extra
        if d.is_dir():
            rows.append({
                "directory": f"results/raw/{extra}",
                "files": sum(1 for f in d.rglob("*") if f.is_file()),
                "tool_content_sha256_values": {},
                "status": status,
                "status_source": cite,
            })
    return rows


def grep_lines(path: str, needle: str) -> list[int]:
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()
    return [i for i, line in enumerate(text, 1) if needle in line]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    a = ap.parse_args()

    head = git("rev-parse", "HEAD")
    base = git("rev-parse", "feb5c19")
    live_digest, live_n = freeze_digest_at("HEAD")
    versions = []
    for commit, subject in ANALYZER_COMMITS.items():
        digest, n = freeze_digest_at(commit)
        versions.append({"commit": git("rev-parse", commit), "subject": subject,
                         "commit_date": git("log", "-1", "--format=%cI", commit),
                         "BINDCHECK_ZK_CONTENT_SHA256": digest, "manifest_files": n})

    d1_files = sorted(p for p in (ROOT / "src/bindcheck_d1").rglob("*.py"))
    d1_payload = "".join(f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in d1_files).encode()

    controls = json.loads((ROOT / "tests/controls/expected.json").read_text())

    stale = []
    def flag(path: str, needle: str, problem: str) -> None:
        stale.append({"file": path, "lines": grep_lines(path, needle), "needle": needle, "problem": problem})

    flag("README.md", "bindcheck-d1-paper", "README opens by describing the D1/Noir relational project and names the bindcheck-d1-paper worktree as 'the current integration checkout'; the bindcheck_zk Circom/Solidity analyzer is a later section.")
    flag("README.md", "d8510859b918a5166d0f1629cf0d883e965fa0acb1be92a34987c24f1967ae13", "README calls d8510859 'the current analyzer content hash'; the live hash is " + live_digest + ".")
    flag("README.md", "105 prospective controls", "README cites 105 controls; T25 and tests/controls/expected.json give 24 + 98 = 122.")
    flag("eval/README.md", "d8510859b918a5166d0f1629cf0d883e965fa0acb1be92a34987c24f1967ae13", "Operator instructions tag the freeze with d8510859; eval/common.py:check_eval_gate compares the tag to the live freeze.sh digest, so following the README verbatim fails closed.")
    flag("reports/T26.md", "d8510859", "T26 states the analyzer hash is still d8510859; T26's own DEV dry run recorded d8510859 because the harness branch forked before cd56c24. The merged HEAD runs 2741c40e.")
    flag("reports/T26.md", "results/raw/T25/", "T26 cites results/raw/T25/dev-dry-run*, but the merge renamed outputs to results/raw/T26/ (merge commit feb5c19 message).")
    flag("docs/research-contract.md", "Noir/ACIR producer", "Research contract revision 3 sets the initial scope to a Noir/ACIR producer; the current analyzer and every T23-T26 result are Circom/Groth16-centred. No contract revision records this scope change.")
    flag("TOOL-REPORT.md", "BINDCHECK_ZK_CONTENT_SHA256=", "TOOL-REPORT.md accumulates sections for three analyzer hashes (60211ab6, d8510859, 2741c40e); section boundaries must be read to know which numbers belong to which version.")

    snapshot = {
        "schema": "bindcheck-groundtruth.snapshot/v1",
        "generated_by": "reports/groundtruth/scripts/snapshot.py",
        "repository": {"worktree": str(ROOT), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                       "head": head, "baseline_commit": base,
                       "note": "All tracked facts below are identical at the baseline commit; HEAD differs only by files under reports/groundtruth/, gate/ and review/."},
        "lineages": {
            "bindcheck_zk": {
                "role": "PRIMARY candidate artifact for the current paper (per synthesis-review Step 1 decision).",
                "language_scope": "Circom (+ partial Noir) circuits, Solidity consumers, generated Groth16/PLONK verifiers; regex/balanced-token extraction; R1CS connectivity check for commitments.",
                "entrypoint": "./bindcheck-zk (bindcheck_zk/cli.py)",
                "live_content_sha256": live_digest,
                "live_manifest_files": live_n,
                "hash_rule": "bindcheck_zk/freeze.py: sha256 over 'digest  path' lines for bindcheck-zk, requirements-bindcheck-zk.txt, bindcheck_zk/*.py, config.json, vendor-lock.json",
                "committed_versions": versions,
                "enabled_checks": {
                    "P1": "effect binding (analyzer.py:529 analyze_p1)",
                    "P2": "execution-context binding (analyzer.py:639 analyze_p2)",
                    "P3": "replay key / canonicality (analyzer.py:780 analyze_p3)",
                    "P4": "verifier invariants (p4.py analyze_source / analyze_runtime)",
                    "P5": "public-input count/order (analyzer.py:852 analyze_p5)",
                    "selection": "All five run unconditionally for every triple (analyzer.py:1197-1201, PATTERNS at analyzer.py:44); there is no CLI flag that disables a check.",
                },
                "baseline_adapters": "bindcheck_zk/baselines.py: slither, circomspect, picus, zkap; native results mapped to UNKNOWN pending adjudication (baselines.py:215).",
                "controls": {k: v for k, v in controls.items() if isinstance(v, (int, bool))},
                "controls_note": "legacy_track_b 24 + analyzer_controls 98 = 122 (reports/T25.md:44-45).",
            },
            "bindcheck_d1": {
                "role": "HISTORICAL relational analyzer (D1P-/D2- reports). Results must not be pooled with bindcheck_zk.",
                "language_scope": "Noir/ACIR producer, Solidity/EVM consumer; conditional-extent (R-EXTENT) and typed-role (R-ROLE) relations.",
                "source": "src/bindcheck_d1/ (" + str(len(d1_files)) + " .py files)",
                "lane_computed_source_sha256": hashlib.sha256(d1_payload).hexdigest(),
                "lane_computed_hash_rule": "sha256 over 'sha256  path' lines of sorted src/bindcheck_d1/**/*.py (this lane's rule; not a project-defined freeze hash)",
                "role_binding_py_sha256_live": sha256_file(ROOT / "src/bindcheck_d1/role_binding.py"),
                "role_binding_py_sha256_sealed_D2_01": "a516f0e339f6fec23fcd96efb52821e9933feb6837e740c99a6d5dbee7bd9028",
                "role_binding_status": "Live analyze_role_binding() fails closed (raises RoleBindingUnsupported; src/bindcheck_d1/role_binding.py:945-960). Retained D2-01 17/30 and D1P-43 7/7 role results were produced by the sealed earlier bytes, not the live file (reports/D2-19-artifact.md:72-82).",
                "raw_evidence": "/Users/imranpollob/Coding/bc/bindcheck-d1-paper/results/raw/{D1P-*,D2-*,X-*,TC02,TE04-06,REPAIR}",
            },
            "bindcheck_legacy_js": {
                "role": "HISTORICAL T01-T22 fixture checker and Payy experiment drivers (JavaScript).",
                "source": "bindcheck/checker.js, bindcheck/compare*.js, scripts/t*.sh",
                "raw_evidence": "/Users/imranpollob/Coding/bc/BindCheck/results/raw/T01..T22 (Payy E4: T15-T19)",
            },
        },
        "raw_result_directories": raw_directories(a.raw),
        "raw_result_note": "tool_content_sha256_values are the 'tool.content_sha256' fields written by bindcheck_zk into each result JSON (analyzer.py:1250). Values that match no committed version are uncommitted working-tree states during development.",
        "tracked_evidence_sha256": {p: sha256_file(ROOT / p) for p in TRACKED_HASH_FILES},
        "stale_or_inconsistent_documents": stale,
    }
    known = {v["BINDCHECK_ZK_CONTENT_SHA256"]: v["commit"][:7] for v in versions}
    for row in snapshot["raw_result_directories"]:
        row["matches_committed_version"] = {h: known.get(h, "UNCOMMITTED") for h in row["tool_content_sha256_values"]}
    a.out.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"live={live_digest} versions={[v['BINDCHECK_ZK_CONTENT_SHA256'][:8] for v in versions]} dirs={len(snapshot['raw_result_directories'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
