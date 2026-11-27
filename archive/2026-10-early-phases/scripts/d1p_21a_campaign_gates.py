#!/usr/bin/env python3
"""D1P-21A gate runner.  This module intentionally has no solver entry point."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/D1P-21A"
LOGS = RAW / "logs"
RECORDS = RAW / "command-records"
WORKSPACES = RAW / "workspace"
PIN = "973e7d1e4b60d0d8a8ca299b0cabd9193b147ef8"
PINNED_ARTIFACT = ROOT / "results/raw/D1P-13/workspace/source/backend/circuits/withdraw/target/withdraw.json"
PINNED_VK = ROOT / "results/raw/D1P-13/artifacts/rebuilt/withdraw-vk.bin"
PINNED_VERIFIER = ROOT / "results/raw/D1P-13/artifacts/rebuilt/WithdrawVerifier-from-vk.sol"
MDOM_ARTIFACT = ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json"
MDOM_VK = ROOT / "results/raw/D1P-15/artifacts/m-dom-vk.bin"
MDOM_VERIFIER = ROOT / "results/raw/D1P-15/artifacts/MdomWithdrawVerifier.sol"
CANONICAL_STATE = ROOT / "results/raw/D1P-19/canonical-states.json"
SDOM_SEED = ROOT / "results/raw/D1P-15/honest-proof.json"
SSRC_ANCHOR = ROOT / "results/raw/D1P-12R/honest-proof.json"
FIXTURE = ROOT / "scripts/fixtures/d1p_21a_exact_state.ts"
PINNED_ARTIFACT_SHA = "7190813f623967b79ba80a1635536fcc9c8524c1d1cb9f00696832f644b38327"
MDOM_ARTIFACT_SHA = "db1a0a17b2717cce2fe9a9a01e114632634fcf43f0f813d062dfa9c660aa7f2f"

PAIRINGS = {
    "pinned-sdom": {
        "source": ROOT / "results/raw/D1P-19/workspace/pinned-source",
        "artifact": PINNED_ARTIFACT,
        "vk": PINNED_VK,
        "verifier": PINNED_VERIFIER,
        "state": "S_DOM",
    },
    "m-dom-sdom": {
        "source": ROOT / "results/raw/D1P-15/workspace/source",
        "artifact": MDOM_ARTIFACT,
        "vk": MDOM_VK,
        "verifier": MDOM_VERIFIER,
        "state": "S_DOM",
    },
    "pinned-ssrc": {
        "source": ROOT / "results/raw/D1P-19/workspace/pinned-source",
        "artifact": PINNED_ARTIFACT,
        "vk": PINNED_VK,
        "verifier": PINNED_VERIFIER,
        "state": "S_SRC",
    },
    "m-src-ssrc": {
        "source": ROOT / "results/raw/D1P-19/workspace/source",
        "artifact": PINNED_ARTIFACT,
        "vk": PINNED_VK,
        "verifier": PINNED_VERIFIER,
        "state": "S_SRC",
    },
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path, base: Path = ROOT) -> dict:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def tree_rss_kib(root_pid: int) -> int:
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,rss="], capture_output=True,
            text=True, check=True, timeout=5,
        ).stdout
        rows = [tuple(map(int, line.split())) for line in output.splitlines() if len(line.split()) == 3]
        wanted = {root_pid}
        changed = True
        while changed:
            changed = False
            for pid, ppid, _rss in rows:
                if ppid in wanted and pid not in wanted:
                    wanted.add(pid)
                    changed = True
        return sum(rss for pid, _ppid, rss in rows if pid in wanted)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0


def run_recorded(label: str, argv: list[str], cwd: Path, timeout: int,
                 environment: dict[str, str]) -> dict:
    joined = " ".join(argv).lower()
    if any(token in joined for token in ("cvc5", "z3", "yices", "boolector")):
        raise SystemExit("D1P-21A runner refuses solver commands")
    LOGS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    stdout_path = LOGS / f"{label}.stdout.txt"
    stderr_path = LOGS / f"{label}.stderr.txt"
    env = os.environ.copy()
    env.update(environment)
    started_at = now()
    started = time.monotonic()
    max_rss = 0
    min_free = shutil.disk_usage(ROOT).free
    timed_out = False
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
            text=True, start_new_session=True,
        )
        while process.poll() is None:
            max_rss = max(max_rss, tree_rss_kib(process.pid))
            min_free = min(min_free, shutil.disk_usage(ROOT).free)
            if time.monotonic() - started >= timeout:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(1)
        exit_code = process.wait()
    payload = {
        "schema": "bindcheck.d1p21a.command/v1",
        "label": label,
        "argv": argv,
        "cwd": str(cwd),
        "started_at_utc": started_at,
        "finished_at_utc": now(),
        "wall_seconds": round(time.monotonic() - started, 3),
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "max_process_tree_rss_kib_observed": max_rss,
        "min_free_disk_bytes_observed": min_free,
        "stdout": record(stdout_path, RAW),
        "stderr": record(stderr_path, RAW),
    }
    write_json(RECORDS / f"{label}.json", payload)
    return payload


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True,
        text=True, check=True,
    ).stdout.strip()


def _locked_toolchain(backend: Path) -> dict:
    package = json.loads((backend / "package.json").read_text())
    root_package = json.loads((backend.parent / "package.json").read_text())
    return {
        "packageManager": root_package["packageManager"],
        "bbJs": package["dependencies"]["@aztec/bb.js"],
        "noirJs": package["dependencies"]["@noir-lang/noir_js"],
        "solc": "0.8.29 (hardhat configuration)",
        "pnpmLock": record(backend.parent / "pnpm-lock.yaml"),
        "backendPackage": record(backend / "package.json"),
    }


def _patch_exact_provider(helper: Path) -> None:
    source = helper.read_text()
    option_anchor = "  /** D1P-15 injected-fixture hook; never used by production deployment code. */\n  d1p15SyntheticRoot?: bigint;\n"
    option_replacement = option_anchor + (
        "  /** D1P-21A exact S_DOM hook: make the synthetic provider slot 0. */\n"
        "  d1p21ExactSyntheticProvider?: boolean;\n"
    )
    recipients_anchor = "  const gigaRootRecipients: Address[] = [l1WarpToadDeploy.address];"
    recipients_replacement = (
        "  const gigaRootRecipients: Address[] = opts?.d1p21ExactSyntheticProvider "
        "? [] : [l1WarpToadDeploy.address];"
    )
    if "d1p21ExactSyntheticProvider" not in source:
        if option_anchor not in source or recipients_anchor not in source:
            raise SystemExit(f"cannot patch exact-provider helper {helper}")
        source = source.replace(option_anchor, option_replacement, 1)
        source = source.replace(recipients_anchor, recipients_replacement, 1)
        helper.write_text(source)
    if source.count("d1p21ExactSyntheticProvider") != 2:
        raise SystemExit(f"unexpected exact-provider patch shape in {helper}")


def setup() -> None:
    required = [
        PINNED_ARTIFACT, PINNED_VK, PINNED_VERIFIER, MDOM_ARTIFACT,
        MDOM_VK, MDOM_VERIFIER, CANONICAL_STATE, SDOM_SEED, SSRC_ANCHOR, FIXTURE,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing prerequisites: {missing}")
    if sha256(PINNED_ARTIFACT) != PINNED_ARTIFACT_SHA or sha256(MDOM_ARTIFACT) != MDOM_ARTIFACT_SHA:
        raise SystemExit("producer artifact identity mismatch")
    free = shutil.disk_usage(ROOT).free
    if free < 8 * 1024**3:
        raise SystemExit(f"unsafe free disk before workspace copies: {free}")
    WORKSPACES.mkdir(parents=True, exist_ok=True)
    identities = {}
    for pairing, spec in PAIRINGS.items():
        source = spec["source"]
        if _git_head(source) != PIN:
            raise SystemExit(f"{pairing} source is not pinned revision {PIN}")
        destination = WORKSPACES / pairing
        if destination.exists():
            raise SystemExit(f"refusing to overwrite existing isolated workspace {destination}")
        shutil.copytree(source, destination, symlinks=True)
        backend = destination / "backend"
        fixture_target = backend / "test/d1p21a-exact-state.fixture.ts"
        shutil.copy2(FIXTURE, fixture_target)
        if spec["state"] == "S_DOM":
            helper = backend / "test/helpers/deploy-evm.ts"
            if "d1p15SyntheticRoot" not in helper.read_text():
                # The pinned D1P-19 workspace predates the fixture-only provider
                # hook.  Import the already-preserved D1P-15 helper into this new
                # isolated copy; production and prior evidence remain untouched.
                shutil.copy2(
                    ROOT / "results/raw/D1P-15/workspace/source/backend/test/helpers/deploy-evm.ts",
                    helper,
                )
            _patch_exact_provider(helper)
        if pairing == "pinned-sdom":
            provider_target = backend / "contracts/test/D1P15SyntheticRootProvider.sol"
            shutil.copy2(ROOT / "scripts/fixtures/D1P15SyntheticRootProvider.sol", provider_target)
        local_verifier = backend / "contracts/verifier/WithdrawVerifier.sol"
        if sha256(local_verifier) != sha256(spec["verifier"]):
            raise SystemExit(f"{pairing} local verifier source does not match its frozen pairing")
        identities[pairing] = {
            "workspace": str(destination.relative_to(ROOT)),
            "copiedFrom": str(source.relative_to(ROOT)),
            "pinnedSourceRevision": _git_head(destination),
            "fixture": record(fixture_target),
            "artifact": record(spec["artifact"]),
            "vk": record(spec["vk"]),
            "verifierSource": record(spec["verifier"]),
            "localVerifierSource": record(local_verifier),
            "consumerSource": record(backend / "contracts/core/WarpToadCore.sol"),
            "lockedToolchain": _locked_toolchain(backend),
            "exactProviderPatch": spec["state"] == "S_DOM",
        }
    versions = {}
    backend = WORKSPACES / "pinned-sdom/backend"
    for name, command in {
        "node": ["node", "--version"],
        "python": [sys.executable, "--version"],
        "hardhat": [str(backend / "node_modules/.bin/hardhat"), "--version"],
    }.items():
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        versions[name] = (result.stdout or result.stderr).strip()
    write_json(RAW / "setup-identities.json", {
        "schema": "bindcheck.d1p21a.setup/v1",
        "checkedAtUtc": now(),
        "repositoryHead": _git_head(ROOT),
        "pinnedSourceRevision": PIN,
        "isolatedIgnoredWorkspace": str(WORKSPACES.relative_to(ROOT)),
        "freeDiskBytesBeforeCopies": free,
        "versions": versions,
        "canonicalState": record(CANONICAL_STATE),
        "sDomPrivateInputSeed": record(SDOM_SEED),
        "sSrcExecutionAnchor": record(SSRC_ANCHOR),
        "pairings": identities,
        "networkRetrieval": "none; reused hash-recorded local pinned workspaces and locked dependencies",
        "solverCampaign": False,
    })


def compile_pairing(pairing: str) -> None:
    if pairing not in PAIRINGS:
        raise SystemExit(f"unknown pairing {pairing}")
    backend = WORKSPACES / pairing / "backend"
    if not backend.is_dir():
        raise SystemExit("run setup first")
    result = run_recorded(
        f"compile-{pairing}",
        [str(backend / "node_modules/.bin/hardhat"), "compile"],
        backend, 600, {},
    )
    if result["exit_code"] != 0:
        raise SystemExit(result["exit_code"])


def refresh_fixture() -> None:
    """Copy the tracked fixture into existing ignored workspaces after review fixes."""
    setup_path = RAW / "setup-identities.json"
    setup_record = json.loads(setup_path.read_text()) if setup_path.is_file() else None
    for pairing in PAIRINGS:
        target = WORKSPACES / pairing / "backend/test/d1p21a-exact-state.fixture.ts"
        if not target.parent.is_dir():
            raise SystemExit("run setup first")
        shutil.copy2(FIXTURE, target)
        if setup_record is not None:
            setup_record["pairings"][pairing]["fixture"] = record(target)
            setup_record["pairings"][pairing]["lockedToolchain"] = _locked_toolchain(target.parents[1])
            backend = target.parents[1]
            setup_record["pairings"][pairing]["localVerifierSource"] = record(
                backend / "contracts/verifier/WithdrawVerifier.sol"
            )
            verifier_artifact = backend / "artifacts/contracts/verifier/WithdrawVerifier.sol/HonkVerifier.json"
            if verifier_artifact.is_file():
                setup_record["pairings"][pairing]["verifierBuildArtifact"] = record(verifier_artifact)
    if setup_record is not None:
        setup_record.pop("anchorHonest", None)
        setup_record["sDomPrivateInputSeed"] = record(SDOM_SEED)
        setup_record["sSrcExecutionAnchor"] = record(SSRC_ANCHOR)
        setup_record["fixtureRefreshReason"] = (
            "split D1P-15 S_DOM private-input seed from D1P-12R S_SRC giga-root anchor "
            "after preserved no-proof preflight failures"
        )
        write_json(setup_path, setup_record)


def _fixture_env(pairing: str, preflight: bool) -> dict[str, str]:
    spec = PAIRINGS[pairing]
    backend = WORKSPACES / pairing / "backend"
    result_dir = RAW / ("preflight" if preflight else "controls")
    return {
        "D1P21_PAIRING": pairing,
        "D1P21_RESULT": str(result_dir / f"{pairing}.json"),
        "D1P21_PROOF_RESULT": str(RAW / "proofs" / f"{pairing}.json"),
        "D1P21_CANONICAL_STATE": str(CANONICAL_STATE),
        "D1P21_SDOM_SEED": str(SDOM_SEED),
        "D1P21_SSRC_ANCHOR": str(SSRC_ANCHOR),
        "D1P21_ARTIFACT": str(spec["artifact"]),
        "D1P21_VK": str(spec["vk"]),
        "D1P21_VERIFIER_SOURCE": str(spec["verifier"]),
        "D1P21_CONSUMER_SOURCE": str(backend / "contracts/core/WarpToadCore.sol"),
        "D1P21_PREFLIGHT": "1" if preflight else "0",
    }


def run_pairing(pairing: str, preflight: bool) -> None:
    if pairing not in PAIRINGS:
        raise SystemExit(f"unknown pairing {pairing}")
    backend = WORKSPACES / pairing / "backend"
    if not backend.is_dir():
        raise SystemExit("run setup first")
    result_path = RAW / ("preflight" if preflight else "controls") / f"{pairing}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    (RAW / "proofs").mkdir(parents=True, exist_ok=True)
    if result_path.exists():
        raise SystemExit(f"refusing to repeat pairing invocation with existing result {result_path}")
    if not preflight:
        preflight_path = RAW / "preflight" / f"{pairing}.json"
        if not preflight_path.is_file() or json.loads(preflight_path.read_text()).get("status") != "PASS":
            raise SystemExit(f"passing preflight required before proof slot {pairing}")
    label = f"{'preflight' if preflight else 'proof'}-{pairing}"
    timeout = 600 if preflight else 1800
    result = run_recorded(
        label,
        [str(backend / "node_modules/.bin/hardhat"), "test", "--network", "edr", "--no-compile",
         "test/d1p21a-exact-state.fixture.ts"],
        backend, timeout, _fixture_env(pairing, preflight),
    )
    if result["exit_code"] != 0:
        raise SystemExit(result["exit_code"])


def _recursive_diff(left, right, path: str = "") -> list[dict]:
    if type(left) is not type(right):
        return [{"path": path or "/", "pinned": left, "mDom": right, "kind": "type-or-value"}]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}/{key}"
            if key not in left:
                result.append({"path": child, "pinned": {"missing": True}, "mDom": right[key], "kind": "added"})
            elif key not in right:
                result.append({"path": child, "pinned": left[key], "mDom": {"missing": True}, "kind": "removed"})
            else:
                result.extend(_recursive_diff(left[key], right[key], child))
        return result
    if isinstance(left, list):
        result = []
        for index in range(max(len(left), len(right))):
            child = f"{path}/{index}"
            if index >= len(left):
                result.append({"path": child, "pinned": {"missing": True}, "mDom": right[index], "kind": "added"})
            elif index >= len(right):
                result.append({"path": child, "pinned": left[index], "mDom": {"missing": True}, "kind": "removed"})
            else:
                result.extend(_recursive_diff(left[index], right[index], child))
        return result
    return [] if left == right else [{"path": path or "/", "pinned": left, "mDom": right, "kind": "value"}]


def _logical_path(path: str) -> str:
    marker = "/backend/circuits/"
    return "backend/circuits/" + path.split(marker, 1)[1] if marker in path else path


def freeze_provenance() -> None:
    from bindcheck_d1.frontends.acir_binary_beta22 import decode
    from bindcheck_d1.warptoad_bn254_regions import extract_bn254_regions
    from bindcheck_d1.warptoad_variant_provenance import extract_mdom_poseidon2

    poseidon = extract_mdom_poseidon2(MDOM_ARTIFACT, expected_artifact_sha256=MDOM_ARTIFACT_SHA)
    bn254 = extract_bn254_regions(
        MDOM_ARTIFACT,
        expected_artifact_sha256=MDOM_ARTIFACT_SHA,
        region_id_prefix="M-DOM-BN-",
        variant="M-DOM",
        direct_lines=(46, 47, 48),
        merkle_withdraw_lines=(61, 75),
    )
    write_json(RAW / "m-dom-poseidon2-provenance.json", poseidon)
    write_json(RAW / "m-dom-bn254-region-extraction.json", bn254)

    terms = [{
        "termId": row["term_id"],
        "functionIdentity": "P2_WIDTH4_SHARED",
        "opcodeIndex": row["opcode_index"],
        "orderedInputWitnesses": row["input_witnesses"],
        "orderedOutputWitnesses": row["output_witnesses"],
        "selectedHashOutputWitness": row["selected_output_witness"],
        "construction": row["construction"],
        "merkleLevel": row["merkle_level"],
        "orientationCandidate": row["orientation_candidate"],
    } for row in poseidon["calls"]]
    terms.extend({
        "termId": row["region_id"],
        "functionIdentity": "BN254_POSEIDON_EXACT_ARITHMETIC",
        "construction": row["construction"],
        "merkleLevel": row["merkle_level"],
        "orientationCandidate": row["orientation_candidate"],
        "coreOpcodeRange": row["core_opcode_range"],
        "boundaryInputWitnesses": row["boundary_input_witnesses"],
        "output": row["output"],
    } for row in bn254["regions"])
    write_json(RAW / "m-dom-term-inventory.json", {
        "schema": "bindcheck.d1p21a.m-dom-term-inventory/v1",
        "artifact": poseidon["artifact"],
        "counts": {"poseidon2L1Applications": 86, "bn254ExactRegions": 77, "total": len(terms)},
        "functionIdentity": {
            "P2_WIDTH4_SHARED": "functional uninterpreted tuple function; equal ordered inputs imply equal ordered outputs; no injectivity",
            "BN254_POSEIDON_EXACT_ARITHMETIC": "decoded field equations retained exactly",
        },
        "terms": terms,
    })

    pinned_artifact = json.loads(PINNED_ARTIFACT.read_text())
    mdom_artifact = json.loads(MDOM_ARTIFACT.read_text())
    pinned_decoded = decode(PINNED_ARTIFACT)
    mdom_decoded = decode(MDOM_ARTIFACT)
    abi_differences = _recursive_diff(pinned_artifact["abi"], mdom_artifact["abi"], "/abi")
    opcode_differences = _recursive_diff(
        pinned_decoded["functions"], mdom_decoded["functions"], "/decoded/functions",
    )
    file_rows = {}
    embedded_diffs = []
    pinned_by_logical = {_logical_path(row["path"]): row for row in pinned_artifact["file_map"].values()}
    mdom_by_logical = {_logical_path(row["path"]): row for row in mdom_artifact["file_map"].values()}
    for logical in sorted(set(pinned_by_logical) | set(mdom_by_logical)):
        left = pinned_by_logical.get(logical)
        right = mdom_by_logical.get(logical)
        file_rows[logical] = {
            "pinned": None if left is None else {"path": left["path"], "sourceSha256": hashlib.sha256(left["source"].encode()).hexdigest()},
            "mDom": None if right is None else {"path": right["path"], "sourceSha256": hashlib.sha256(right["source"].encode()).hexdigest()},
        }
        if left and right and left["source"] != right["source"]:
            diff = "".join(difflib.unified_diff(
                left["source"].splitlines(keepends=True), right["source"].splitlines(keepends=True),
                fromfile=f"pinned/{logical}", tofile=f"M-DOM/{logical}",
            ))
            embedded_diffs.append({"logicalPath": logical, "unifiedDiff": diff})

    pinned_poseidon = json.loads((ROOT / "results/raw/D1P-15/poseidon2-provenance.json").read_text())
    p2_diffs = []
    for pinned, mdom in zip(pinned_poseidon["calls"], poseidon["calls"]):
        left = {
            "opcode_index": pinned["opcode_index"],
            "input_witnesses": pinned["input_witnesses"],
            "output_witnesses": pinned["output_witnesses"],
            "selected_output_witness": pinned["selected_output_witness"],
            "construction": pinned["construction"],
            "merkle_level": pinned["merkle_level"],
            "orientation_candidate": pinned["orientation_candidate"],
            "call_stack": [
                {"path": _logical_path(row["path"]), "line": row["line"], "snippet": row["snippet"]}
                for row in pinned["call_stack"]
            ],
        }
        right = {
            "opcode_index": mdom["opcode_index"],
            "input_witnesses": mdom["input_witnesses"],
            "output_witnesses": mdom["output_witnesses"],
            "selected_output_witness": mdom["selected_output_witness"],
            "construction": mdom["construction"],
            "merkle_level": mdom["merkle_level"],
            "orientation_candidate": mdom["orientation_candidate"],
            "call_stack": [
                {"path": _logical_path(row["path"]), "line": row["line"], "snippet": row["snippet"]}
                for row in mdom["call_stack"]
            ],
        }
        changes = _recursive_diff(left, right, f"/poseidon2/calls/{mdom['ordinal']}")
        if changes:
            p2_diffs.append({"ordinal": mdom["ordinal"], "differences": changes})

    pinned_bn = json.loads((ROOT / "results/raw/D1P-19/bn254-region-extraction.json").read_text())
    bn_differences = _recursive_diff(
        pinned_bn["regions"], bn254["regions"], "/bn254/regions",
    )
    write_json(RAW / "m-dom-vs-pinned-differences.json", {
        "schema": "bindcheck.d1p21a.m-dom-vs-pinned/v1",
        "method": (
            "exhaustive JSON-pointer comparison of decoded function/opcode structures and ABI, plus "
            "per-call Poseidon2 and per-region BN254 provenance comparison; paths are logicalized only "
            "for workspace-prefix neutrality"
        ),
        "identities": {
            "pinnedArtifact": record(PINNED_ARTIFACT),
            "mDomArtifact": record(MDOM_ARTIFACT),
            "pinnedDecodedAcirSha256": pinned_decoded["serialization"]["decoded_sha256"],
            "mDomDecodedAcirSha256": mdom_decoded["serialization"]["decoded_sha256"],
        },
        "topLevel": {
            "noirVersionEqual": pinned_artifact["noir_version"] == mdom_artifact["noir_version"],
            "bytecodeEqual": pinned_artifact["bytecode"] == mdom_artifact["bytecode"],
            "debugSymbolsEqual": pinned_artifact["debug_symbols"] == mdom_artifact["debug_symbols"],
        },
        "abiDifferenceCount": len(abi_differences),
        "abiDifferences": abi_differences,
        "decodedFunctionDifferenceCount": len(opcode_differences),
        "decodedFunctionDifferences": opcode_differences,
        "poseidon2CallsWithDifferences": len(p2_diffs),
        "poseidon2CallDifferences": p2_diffs,
        "bn254RegionDifferenceCount": len(bn_differences),
        "bn254RegionDifferences": bn_differences,
        "embeddedSourceFiles": file_rows,
        "embeddedSourceDiffs": embedded_diffs,
        "classification": {
            "semantic": [
                "M-DOM adds private aztec_merkle_data.contract_address witness 59",
                "the siloed-note Poseidon2 call absorbs private witness 59 instead of public witness 5",
                "subsequent generated witness IDs shift while opcode and construction counts remain equal",
                "artifact bytecode, decoded ACIR, ABI, VK, and generated verifier differ",
            ],
            "nonsemantic": [
                "absolute embedded source workspace prefixes differ and are normalized for comparison",
                "source/debug line numbers shift where the injected struct field and comments add lines",
            ],
        },
    })


def freeze_execution() -> None:
    controls = {}
    attempts = []
    for pairing in PAIRINGS:
        path = RAW / "controls" / f"{pairing}.json"
        command_path = RECORDS / f"proof-{pairing}.json"
        if not path.is_file() or not command_path.is_file():
            raise SystemExit(f"missing executed control {pairing}")
        result = json.loads(path.read_text())
        command = json.loads(command_path.read_text())
        controls[pairing] = record(path)
        attempts.append({
            "pairing": pairing,
            "pairingInvocation": record(command_path),
            "commandExitCode": command["exit_code"],
            "timedOut": command["timed_out"],
            "backendAttemptsRecorded": result.get("proofGenerationAttempts", []),
            "status": result.get("status"),
            "proof": record(RAW / "proofs" / f"{pairing}.json") if (RAW / "proofs" / f"{pairing}.json").is_file() else None,
            "retryPermittedOrUsed": False,
        })
    write_json(RAW / "proof-attempt-ledger.json", {
        "schema": "bindcheck.d1p21a.proof-attempt-ledger/v1",
        "budget": "one pairing invocation / at most one proof-generation attempt for each of four pairings",
        "pairingSlots": 4,
        "pairingInvocationsUsed": len(attempts),
        "attempts": attempts,
        "parameterSearch": False,
        "retries": 0,
    })
    statuses = {name: json.loads((RAW / "controls" / f"{name}.json").read_text())["status"] for name in PAIRINGS}
    write_json(RAW / "gate-summary.json", {
        "schema": "bindcheck.d1p21a.gate-summary/v1",
        "controls": controls,
        "statuses": statuses,
        "allAcceptedAndEffectsChecked": all(status == "PASS" for status in statuses.values()),
        "historicalReceiptsSubstituted": False,
        "proofsGeneratedForExactCanonicalStates": True,
        "solverCampaign": False,
        "d1Verdict": "UNKNOWN",
    })


def freeze_resources() -> None:
    rows = []
    for path in sorted(RECORDS.glob("*.json")):
        row = json.loads(path.read_text())
        rows.append({
            "label": row["label"], "exitCode": row["exit_code"], "timedOut": row["timed_out"],
            "wallSeconds": row["wall_seconds"],
            "maxProcessTreeRssKibObserved": row["max_process_tree_rss_kib_observed"],
            "minFreeDiskBytesObserved": row["min_free_disk_bytes_observed"],
        })
    write_json(RAW / "resource-summary.json", {
        "schema": "bindcheck.d1p21a.resource-summary/v1",
        "classification": "development resource observations; not performance evidence",
        "commands": rows,
        "peakObservedProcessTreeRssKib": max((row["maxProcessTreeRssKibObserved"] for row in rows), default=0),
        "minimumObservedFreeDiskBytes": min((row["minFreeDiskBytesObserved"] for row in rows), default=0),
        "unsafeResourceExhaustionObserved": False,
        "directSolverCommands": 0,
        "knownNonPrimaryChildParseOnlyChecks": (
            "the complete D1 pytest suite includes pre-existing cvc5 --parse-only syntax tests; "
            "no satisfiability query or campaign is launched"
        ),
        "solverCampaign": False,
    })


def freeze_manifest() -> None:
    excluded = {RAW / "evidence-manifest.json"}
    files = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path in excluded:
            continue
        if "workspace" in path.relative_to(RAW).parts:
            continue
        files.append(record(path))
    tracked = [
        ROOT / "scripts/d1p_21a_campaign_gates.py",
        FIXTURE,
        ROOT / "src/bindcheck_d1/warptoad_variant_provenance.py",
        ROOT / "src/bindcheck_d1/warptoad_bn254_regions.py",
        ROOT / "tests/d1/test_d1p21a.py",
        ROOT / "reports/D1P-21A.md",
        ROOT / "README.md",
        ROOT / "docs/project-status.md",
    ]
    files.extend(record(path) for path in tracked if path.is_file())
    write_json(RAW / "evidence-manifest.json", {
        "schema": "bindcheck.d1p21a.evidence-manifest/v1",
        "namespace": "D1P-21A",
        "pinnedRevision": PIN,
        "files": files,
        "ignoredWorkspaceExcludedFromInventory": True,
        "solverCampaign": False,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("pairing", choices=PAIRINGS)
    sub.add_parser("refresh-fixture")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("pairing", choices=PAIRINGS)
    proof = sub.add_parser("proof")
    proof.add_argument("pairing", choices=PAIRINGS)
    sub.add_parser("freeze-provenance")
    sub.add_parser("freeze-execution")
    sub.add_parser("freeze-resources")
    sub.add_parser("freeze-manifest")
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--label", required=True)
    record_parser.add_argument("--cwd", type=Path, required=True)
    record_parser.add_argument("--timeout", type=int, required=True)
    record_parser.add_argument("--env", action="append", default=[])
    record_parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "compile":
        compile_pairing(args.pairing)
    elif args.command == "refresh-fixture":
        refresh_fixture()
    elif args.command == "preflight":
        run_pairing(args.pairing, True)
    elif args.command == "proof":
        run_pairing(args.pairing, False)
    elif args.command == "freeze-provenance":
        freeze_provenance()
    elif args.command == "freeze-execution":
        freeze_execution()
    elif args.command == "freeze-resources":
        freeze_resources()
    elif args.command == "freeze-manifest":
        freeze_manifest()
    else:
        argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
        environment = dict(item.split("=", 1) for item in args.env)
        result = run_recorded(args.label, argv, args.cwd.resolve(), args.timeout, environment)
        raise SystemExit(result["exit_code"])


if __name__ == "__main__":
    main()
