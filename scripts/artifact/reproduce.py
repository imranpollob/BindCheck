#!/usr/bin/env python3
"""One-command reproduction entry points for the paper artifact tables."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results/raw"
TOOLS = RAW / "artifact-tools"
BIN = TOOLS / "bin"
NPM = TOOLS / "npm/node_modules"
OUT = RAW / "artifact-reproduction"

HARNESS_HASHES = {
    "baselines/foundry/test/WarpToadPolicy.t.sol":
        "a33732d2262e8115bd4a1ef66cc5f075f5d015cfbe686df14c2fc58862670370",
    "baselines/foundry/foundry.toml":
        "0a7b8b389511a9508a444d9eca7c106e13f1bae419f082b659d0b63b8e28363d",
}

EXPECTED_FOUNDRY_FAILURE = {
    "pinned": set(),
    "m-dom": set(),
    "m-src": {"invariant_roots_are_admitted"},
    "WT-S01": {"invariant_roots_are_admitted"},
    "WT-S02": {"invariant_roots_are_admitted"},
    "WT-S03": {"invariant_nullifier_single_use"},
    "WT-S04": {"invariant_verifier_gates_mint"},
    "WT-S05": {"invariant_valid_relation_is_accepted"},
    "WT-S06": set(),
    "WT-S07": {"invariant_amount_and_beneficiary_bound"},
    "WT-S08": {"invariant_valid_relation_is_accepted"},
    "WT-S09": {"invariant_nullifier_single_use"},
}

GENERIC_INVARIANTS = {
    "invariant_nullifier_single_use",
    "invariant_reverts_roll_back",
    "invariant_supply_matches_transfer_events",
    "invariant_verifier_gates_mint",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv: list[str | Path], *, cwd: Path = ROOT, timeout: int = 7200,
        check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    printable = " ".join(str(item) for item in argv)
    print(f"+ {printable}", flush=True)
    completed = subprocess.run(
        [str(item) for item in argv], cwd=cwd, text=True, capture_output=True,
        timeout=timeout, check=False, env={**os.environ, **(env or {})},
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr,
              end="" if completed.stderr.endswith("\n") else "\n")
    if check and completed.returncode:
        raise RuntimeError(f"exit {completed.returncode}: {printable}")
    return completed


def prepare(profile: str) -> None:
    run([ROOT / "scripts/artifact/fetch_inputs.sh", "--profile", profile], timeout=7200)


def artifact_env() -> dict[str, str]:
    return {
        "BINDCHECK_ROOT": str(ROOT),
        "BINDCHECK_PAYY_ROOT": str(ROOT),
        "BINDCHECK_PAYY_EARLIER": str(ROOT / "tools/cases/payy-c4d2c90"),
        "BINDCHECK_NARGO_22": str(BIN / "nargo-beta22"),
        "BINDCHECK_NARGO_14": str(BIN / "nargo-beta14"),
        "BINDCHECK_SOLC_0_8_20": str(BIN / "solc-0.8.20"),
        "BINDCHECK_SOLC_0_8_29": str(BIN / "solc-0.8.29"),
        "BINDCHECK_WARPTOAD_NODE_MODULES": str(NPM),
        "BINDCHECK_WARPTOAD_BUILDINFO": str(TOOLS / "solidity-builds/pinned"),
        "BINDCHECK_CANONICAL_STATES": str(RAW / "D1P-19/canonical-states.json"),
        "CRS_PATH": str(TOOLS / "crs"),
        "PATH": str(BIN) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONPATH": str(ROOT / "src"),
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def benchmark_table() -> None:
    prepare("evaluation")
    env = artifact_env()
    run([sys.executable, ROOT / "scripts/d1p_34_evaluate.py"], env=env, timeout=3600)
    run([sys.executable, ROOT / "scripts/d1p_34_adjudicate.py"], env=env)
    adjudication = json.loads((RAW / "D1P-34/adjudication.json").read_text())
    expected = {
        "targets": 30, "detected": 16, "unsupported": 14, "misses": 0,
        "warning_objects": 53, "ground_truth_related_warning_objects": 20,
        "unrelated_warning_objects": 33, "detected_location_matches": 16,
        "confirmed_false_warning_objects": 0,
    }
    if adjudication["totals"] != expected:
        raise AssertionError((adjudication["totals"], expected))
    lines = [
        "# Reproduced BindCheck benchmark table", "",
        "| application | targets | detected | unsupported | misses | related warnings | unrelated warnings |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in adjudication["by_app"]:
        lines.append(
            f"| {row['app']} | {row['targets']} | {row['detected']} | "
            f"{row['unsupported']} | {row['misses']} | {row['related_warnings']} | "
            f"{row['unrelated_warnings']} |"
        )
    lines.append(
        f"| **Total** | **30** | **16** | **14** | **0** | **20** | **33** |"
    )
    write(OUT / "benchmark-table.md", "\n".join(lines) + "\n")
    print(f"PASS: {OUT / 'benchmark-table.md'}")


def portable_foundry_config() -> str:
    forge_std = TOOLS / "upstream/forge-std/src"
    return f'''[profile.default]
src = "contracts"
test = "test"
out = "out"
cache_path = "cache"
solc = "{BIN / 'solc-0.8.29'}"
optimizer = true
optimizer_runs = 200
remappings = [
  "forge-std/={forge_std}/",
  "poseidon-solidity/={NPM / 'poseidon-solidity'}/",
  "@zk-kit/={NPM / '@zk-kit'}/",
  "@openzeppelin/={NPM / '@openzeppelin'}/"
]

[invariant]
runs = 256
depth = 100
fail_on_revert = false
'''


def foundry_source(label: str) -> Path | None:
    if label in {"pinned", "m-dom"}:
        return None
    if label == "m-src":
        return RAW / "D1P-19/workspace/source/backend/contracts/core/WarpToadCore.sol"
    return RAW / f"X-BM/mutants/{label}/WarpToadCore.sol"


def stage_foundry(label: str) -> Path:
    destination = OUT / "foundry" / label
    if destination.exists():
        shutil.rmtree(destination)
    source_backend = RAW / "D1P-19/workspace/pinned-source/backend"
    shutil.copytree(source_backend / "contracts", destination / "contracts", symlinks=False)
    (destination / "test").mkdir(parents=True)
    shutil.copy2(ROOT / "baselines/foundry/test/WarpToadPolicy.t.sol",
                 destination / "test/WarpToadPolicy.t.sol")
    override = foundry_source(label)
    if override is not None:
        shutil.copy2(override, destination / "contracts/core/WarpToadCore.sol")
    write(destination / "foundry.toml", portable_foundry_config())
    return destination


def baseline_table() -> None:
    prepare("all")
    for relative, expected in HARNESS_HASHES.items():
        observed = sha256(ROOT / relative)
        if observed != expected:
            raise AssertionError(f"{relative}: {observed} != {expected}")
    report = (ROOT / "docs/baselines/d1p-32-benchmark.md").read_text()
    for digest in HARNESS_HASHES.values():
        if digest not in report:
            raise AssertionError(f"published D1P-32 report does not contain {digest}")

    rows = []
    forge = BIN / "forge"
    for label, expected_failures in EXPECTED_FOUNDRY_FAILURE.items():
        workspace = stage_foundry(label)
        started = time.monotonic()
        completed = run(
            [forge, "test", "--match-contract", "WarpToadPolicyInvariant", "-vv"],
            cwd=workspace, timeout=1800, check=False,
            env={"FOUNDRY_DISABLE_NIGHTLY_WARNING": "1"},
        )
        output = completed.stdout + completed.stderr
        failures = set(re.findall(r"invariant_[a-z_]+", "\n".join(
            line for line in output.splitlines() if "[FAIL" in line
        )))
        if failures != expected_failures:
            raise AssertionError(f"{label}: failures {failures} != {expected_failures}")
        rows.append({
            "target": label, "failures": sorted(failures),
            "generic": "detected" if failures & GENERIC_INVARIANTS else "missed",
            "same_policy": "detected" if failures else "missed",
            "exit_code": completed.returncode,
            "runtime_seconds": round(time.monotonic() - started, 3),
        })

    mutants = [row for row in rows if row["target"].startswith("WT-S")]
    generic_detected = sum(row["generic"] == "detected" for row in mutants)
    policy_detected = sum(row["same_policy"] == "detected" for row in mutants)
    if (generic_detected, policy_detected) != (3, 8):
        raise AssertionError((generic_detected, policy_detected))
    write(OUT / "foundry-baseline.json", json.dumps(rows, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Reproduced D1P-32 Foundry baseline rows", "",
        "The other baseline rows are frozen third-party-tool records; see ARTIFACT.md.", "",
        "| arm | detected | missed | unresolved (other benchmark inputs) | total |",
        "|---|---:|---:|---:|---:|",
        f"| Foundry G1/G2/G4/G5 | {generic_detected} | {9-generic_detected} | 21 | 30 |",
        f"| Foundry same-policy | {policy_detected} | {9-policy_detected} | 21 | 30 |",
    ]
    write(OUT / "baseline-table.md", "\n".join(lines) + "\n")
    print(f"PASS: {OUT / 'baseline-table.md'}")


def no_competing_provers() -> None:
    completed = subprocess.run(
        ["pgrep", "-fl", "(^|/)(bb|nargo)( |$)"], text=True,
        capture_output=True, check=False,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        raise RuntimeError("refusing to start while another bb/nargo job is active:\n" + completed.stdout)


def validation_table(ignore_load: bool) -> None:
    prepare("all")
    env = artifact_env()
    run([sys.executable, ROOT / "scripts/d1p_34_evaluate.py"], env=env, timeout=3600)
    analysis = json.loads((RAW / "D1P-34/analysis-run.json").read_text())
    items = []
    for target in analysis["targets"]:
        if target["kind"] != "mutant":
            continue
        for warning in target["warnings"]:
            items.append({"mutant": target["target"], "warning": warning})
    if len(items) != 53:
        raise AssertionError(f"expected 53 v1.1 warnings, got {len(items)}")
    warnings = OUT / "xav-warnings.json"
    write(warnings, json.dumps({
        "honest_toml": str(RAW / "D1P-15/workspace/source/backend/circuits/withdraw/D1P15_12R.toml"),
        "items": items,
    }, indent=2, sort_keys=True) + "\n")
    no_competing_provers()
    command: list[str | Path] = [
        sys.executable, ROOT / "scripts/xav_run.py", "--warnings", warnings,
        "--out", OUT / "xav-v11", "--stop-after", "E4",
    ]
    if ignore_load:
        command.append("--ignore-load")
    run(command, env=env, timeout=21600)
    results = json.loads((OUT / "xav-v11/results.json").read_text())
    counts = Counter(row["E"] for row in results)
    if len(results) != 53:
        raise AssertionError(f"validator returned {len(results)} rows")
    expected = Counter({
        "E4": 8,
        "E4-preserved": 1,
        "E3": 4,
        "E2 (mock-verifier-scoped)": 6,
        "E1": 34,
    })
    if counts != expected:
        raise AssertionError(f"X-AV evidence counts differ: {dict(counts)} != {dict(expected)}")
    lines = [
        "# Reproduced automatic-validation table", "",
        "| evidence level | warning rows |", "|---|---:|",
    ]
    for level in ("E4", "E4-preserved", "E3", "E2 (mock-verifier-scoped)", "E2", "E1"):
        if counts[level]:
            lines.append(f"| {level} | {counts[level]} |")
    lines += [
        "",
        "The tracked X-AV driver does not rerun the separate TC02 Rust-stack experiment. "
        "Its two post-run E3 promotions remain an explicitly archived/manual merge step.",
    ]
    write(OUT / "validation-table.md", "\n".join(lines) + "\n")
    print(f"PASS: {OUT / 'validation-table.md'}")


def ledger_table() -> None:
    """Corrected validation + repair table (ledger; RQ2 corrected claim).

    Does not rerun provers. Grades the preserved (or freshly reproduced)
    v1.1 driver rows with the tracked core, and asserts the TE05/REPAIR
    evidence files the corrected grades depend on.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from bindcheck_d1 import xav_core
    results = json.loads((RAW / "X-AV/v11/results.json").read_text())
    graded = xav_core.check_ledger(results)
    evidence = [
        RAW / "X-AV/v11/results.json",
        ROOT / "build/TE05/proof-final/proof",
        ROOT / "build/TE05/e4/te05-report.json",
        RAW / "REPAIR/repair-report.json",
        RAW / "REPAIR/s02-corrected/report-mutant-accepts.json",
        RAW / "REPAIR/s02-corrected/report-pinned-reverts.json",
    ]
    missing = [str(p) for p in evidence if not p.exists()]
    if missing:
        raise AssertionError(f"ledger evidence missing: {missing}")
    te05 = json.loads((ROOT / "build/TE05/e4/te05-report.json").read_text())
    if te05["state"].get("blockHeight") != "0":
        raise AssertionError(f"TE05 must show zero state change: {te05['state']}")
    reverts = {k: v for k, v in te05.items() if k.startswith("revert")}
    if len(reverts) < 2:
        raise AssertionError(f"TE05 must record both submits reverting: {reverts}")
    repair = json.loads((RAW / "REPAIR/repair-report.json").read_text())
    verdicts = {(r["mutant"]): r.get("verdict") for r in repair["rows"]}
    bad = {m: v for m, v in verdicts.items() if not (
        str(v).startswith("REPAIR-OK") or str(v).startswith("REPAIR-UNEXPECTED"))}
    if bad:
        raise AssertionError(f"repair rows without recorded verdict: {bad}")
    lines = [
        "# Reproduced corrected validation + repair table", "",
        "Raw driver grades are adjudicated by the tracked ledger core",
        "(`src/bindcheck_d1/xav_core.py`; E1+mock replaces the",
        "non-contract E2 label; PY-C02 corrected by TE05; WT-S02 by the",
        "corrected honest-seeded experiment).", "",
        "| ledger grade | warning rows |",
        "|---|---:|",
    ]
    for level in ("E4", "E4-preserved", "E3", "E1+mock", "E1"):
        if graded["counts"].get(level):
            lines.append(f"| {level} | {graded['counts'][level]} |")
    lines += [
        "",
        "Repairs: every WarpToad repair is pinned-byte-identical with the",
        "attack blocked and honest behavior succeeding (WT-C02 documents a",
        "warning-quality flag instead); PY-C02 repaired == pinned bytes",
        "with TE05 containment; the structural commit_hash warning remains",
        "by design. Held-out transfer (RQ4) has no reproduce command: it",
        "requires the custodian reservation (D1P-33/D1P-36 frozen runs).",
    ]
    write(OUT / "ledger-table.md", "\n".join(lines) + "\n")
    print(f"PASS: {OUT / 'ledger-table.md'} {graded['counts']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("claim", choices=("benchmark-table", "baseline-table", "validation-table", "ledger", "all"))
    parser.add_argument("--ignore-load", action="store_true",
                        help="allow serialized proving above X-AV's load threshold")
    args = parser.parse_args()
    if args.claim in {"benchmark-table", "all"}:
        benchmark_table()
    if args.claim in {"baseline-table", "all"}:
        baseline_table()
    if args.claim in {"validation-table", "all"}:
        validation_table(args.ignore_load)
    if args.claim in {"ledger", "all"}:
        ledger_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
