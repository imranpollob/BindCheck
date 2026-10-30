#!/usr/bin/env python3
"""Automatic validation driver: warning -> synthesized witness -> E2/E3/E4.

Usage:
  python3 scripts/xav_run.py --warnings JSON --out DIR [--only MUTANT,...]
WARNINGS JSON: {"honest_toml": PATH, "items": [{"mutant": ID, "warning": {...}}]}

Per item, stages under OUT/build/<MUTANT>/:
  1. stage sources (mutant circuits/contracts via make_mutants output)
  2. synthesize attacker Prover.toml (witness_synth_v1 + synth_witness.mjs)
  3. nargo compile + execute                      -> E2
  4. bb.js prove + verify with mutant VK          -> E3 (nice -n 19, serial)
  5. hardhat EDR: honest control replay, then attack replay -> E4
Writes OUT/results.json rows {mutant, rule, location, E-level, times,
manual steps}. Anything unconstructible records E1 + missing prerequisite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from bindcheck_d1.witness_synth_v1 import plan_for, apply_bind_word, toml_get  # noqa: E402

NARGO22 = Path(os.environ.get(
    "BINDCHECK_NARGO_22", ROOT / "results/raw/artifact-tools/bin/nargo-beta22"
))
PIN_SRC = Path(os.environ.get(
    "BINDCHECK_WARPTOAD_BACKEND",
    ROOT / "results/raw/D1P-19/workspace/pinned-source/backend",
))
REF_NM = Path(os.environ.get(
    "BINDCHECK_WARPTOAD_NODE_MODULES",
    ROOT / "results/raw/D1P-19/workspace/source/backend/node_modules",
))
REF_BUILDINFO = Path(os.environ.get(
    "BINDCHECK_WARPTOAD_BUILDINFO",
    REF_NM.parent / "artifacts/build-info",
))

LOAD_LIMIT = 30.0  # do not start a proof above this 1-min load
IGNORE_LOAD = False


def sh(argv, cwd, timeout, log, extra_env=None, stdin_text=None):
    env = os.environ.copy()
    env.update(extra_env or {})
    t0 = time.monotonic()
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
                       input=stdin_text)
    wall = time.monotonic() - t0
    log.write_text(f"$ {' '.join(map(str, argv))}\nexit={p.returncode} wall={wall:.1f}s\n"
                   f"--- stdout ---\n{p.stdout[-3000:]}\n--- stderr ---\n{p.stderr[-3000:]}")
    return p, wall


def load1():
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0.0


def replace_section(toml_text, section, body_lines):
    pattern = re.compile(rf"^\[{section}\]\n(?:^[^\[\n][^\n]*\n?)+", re.MULTILINE)
    body = "".join(body_lines)
    replacement = f"[{section}]\n{body}"
    new, n = pattern.subn(replacement, toml_text, count=1)
    if n != 1:
        raise ValueError(f"section {section} match count {n}")
    return new


def compose_anchor(honest_toml, spec, word_updates=None, dest_override=None):
    out = honest_toml
    for word, value in (("nullifier_preimage", "0xA77AC4"), ("secret", "0x5EC2E7")):
        out = apply_bind_word(out, {word: value})
    out = apply_bind_word(out, {"nullifier": spec["attacker_nullifier"]})
    dest = toml_get(honest_toml, "destination_local_root") if dest_override == "honest" \
        else spec["attacker_root"]
    out = apply_bind_word(out, {"destination_local_root": dest,
                                "origin_local_root": spec["attacker_root"]})
    if word_updates:
        out = apply_bind_word(out, word_updates)
    evm = spec["evm_sections"]
    out = replace_section(out, "evm_merkle_data",
                          ["leaf_index = \"0x0\"\n",
                           "hash_path = [" + ", ".join(f'"{h}"' for h in evm["hash_path"]) + "]\n"])
    return out


def compose_aztec(honest_toml, spec):
    out = honest_toml
    for word, value in (("nullifier_preimage", "0xA77AC4"), ("secret", "0x5EC2E7")):
        out = apply_bind_word(out, {word: value})
    out = apply_bind_word(out, {"nullifier": spec["attacker_nullifier"]})
    out = apply_bind_word(out, {"destination_local_root": spec["attacker_root"],
                                "origin_local_root": spec["attacker_root"]})
    out = re.sub(r"^is_from_aztec = false$", "is_from_aztec = true", out, count=1, flags=re.MULTILINE)
    az = spec["aztec_sections"]
    out = replace_section(out, "aztec_merkle_data",
                          ["leaf_index = \"0x0\"\n",
                           "hash_path = [" + ", ".join(f'"{h}"' for h in az["hash_path"]) + "]\n",
                           "leaf_nonce = \"0x0\"\n",
                           f'contract_address = "{az["contract_address"]}"\n'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warnings", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--stop-after", default="E4", choices=["E2", "E3", "E4"])
    ap.add_argument("--ignore-load", action="store_true",
                    help="prove even above LOAD_LIMIT (still serial + nice -n 19)")
    args = ap.parse_args()
    args.out = args.out.resolve()
    spec = json.loads(args.warnings.read_text())
    honest_toml = Path(spec["honest_toml"]).read_text()
    only = set(args.only.split(",")) if args.only else None
    stop_after = args.stop_after
    global IGNORE_LOAD
    IGNORE_LOAD = args.ignore_load
    out = args.out
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "load.txt").write_text(f"{load1():.2f}\n")
    mutdir = out / "mutants"
    # Always regenerate: a stale partial dir silently yields pinned circuits.
    if mutdir.exists():
        shutil.rmtree(mutdir)
    r = subprocess.run([sys.executable, str(ROOT / "benchmarks/binding-mutants/make_mutants.py"),
                        "--baseline", str(ROOT / "benchmarks/binding-mutants/baselines"),
                        "--out", str(mutdir), "--record", str(out / "generation-record.json")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"make_mutants failed: {r.stderr[-1000:]}")
    got = sorted(p.name for p in mutdir.iterdir() if p.is_dir())
    want = {i["mutant"] for i in spec["items"]}
    if not want.issubset(set(got)):
        raise SystemExit(f"mutant dir incomplete: missing {sorted(want - set(got))}")

    results = []
    for item in spec["items"]:
        mid = item["mutant"]
        if only and mid not in only:
            continue
        warning = item["warning"]
        row = {"mutant": mid, "warning": warning["id"], "rule": warning["rule"],
               "location": warning.get("location"), "E": "E1", "manual_steps": [],
               "stages": {}, "times": {}}
        t_start = time.monotonic()
        try:
            run_one(mid, warning, honest_toml, out, row, stop_after)
        except Exception as exc:  # noqa: BLE001 - record, keep going
            row["stages"]["harness_error"] = f"{type(exc).__name__}: {exc}"[:300]
        row["times"]["total_wall_s"] = round(time.monotonic() - t_start, 1)
        results.append(row)
        print(json.dumps({k: row[k] for k in ("mutant", "warning", "rule", "E", "manual_steps")}), flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))


def stage_build(mid, out):
    b = out / "build" / mid
    if b.exists():
        shutil.rmtree(b)
    (b / "contracts").mkdir(parents=True)
    shutil.copytree(PIN_SRC / "circuits", b / "circuits_tmp", symlinks=True)
    for p in (b / "circuits_tmp").rglob("target"):
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
    shutil.move(str(b / "circuits_tmp"), str(b / "circuits"))
    for name in ("warptoad-withdraw-main.nr", "warptoad-nargo-hashing-lib.nr"):
        src = out / "mutants" / mid / name
        if src.exists() and "withdraw" in name:
            shutil.copy(src, b / "circuits/withdraw/src/main.nr")
        elif src.exists():
            shutil.copy(src, b / "circuits/nargo_hashing/src/lib.nr")
    # contracts: pinned tree, mutant overlay for WT-S*
    for sol in (PIN_SRC / "contracts").rglob("*.sol"):
        dest = b / "contracts" / sol.relative_to(PIN_SRC / "contracts")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(sol, dest)
    overlay = out / "mutants" / mid / "WarpToadCore.sol"
    if overlay.exists():
        shutil.copy(overlay, b / "contracts/core/WarpToadCore.sol")
    for pkg in ("poseidon-solidity",):
        shutil.copytree(REF_NM / pkg, b / "node_modules" / pkg, symlinks=True)
    for pkg in ("@zk-kit", "@openzeppelin"):
        (b / "node_modules" / pkg).mkdir(parents=True, exist_ok=True)
    for sub in (REF_NM / "@zk-kit").iterdir():
        (b / "node_modules/@zk-kit" / sub.name).symlink_to(sub)
    (b / "node_modules/@openzeppelin/contracts").symlink_to(REF_NM / "@openzeppelin/contracts")
    for f in ("replay.ts", "hardhat.config.ts", "MockGigaProvider.sol", "prove.mjs", "synth_witness.mjs"):
        shutil.copy(ROOT / "scripts/xav" / f, b / f)
    (b / "package.json").write_text(json.dumps({"name": f"xav-{mid}", "type": "module",
                                                "private": True}, indent=1))
    (b / "contracts/verifier").mkdir(parents=True, exist_ok=True)
    (b / "contracts/test").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "scripts/xav/MockGigaProvider.sol", b / "contracts/test/MockGigaProvider.sol")
    for sol in ("USDcoin.sol",):
        shutil.copy(PIN_SRC / "contracts/test" / sol, b / "contracts/test" / sol)
    (b / "node_modules").mkdir(exist_ok=True)
    for p in REF_NM.iterdir():
        dest = b / "node_modules" / p.name
        if not dest.exists():
            dest.symlink_to(p)
    return b


def run_one(mid, warning, honest_toml, out, row, stop_after="E4"):
    # Payy rows never take the WarpToad nargo/bb/EDR route: a shape plan that
    # looks WarpToad-compatible (e.g. R-POLARITY replay) would otherwise run
    # WarpToad artifacts against a Payy warning and misgrade it.
    if mid.startswith("PY-"):
        run_payy(mid, warning, out, row)
        return
    plan = plan_for(warning, mid)
    row["stages"]["plan"] = {"kind": plan.kind, "words": plan.word_updates, "notes": plan.notes}
    if plan.kind == "unsupported":
        row["stages"]["blocked"] = plan.blocked_reason
        row["manual_steps"] = ["build 2-proof aggregator witness harness"]
        return
    b = stage_build(mid, out)
    logs = out / "logs"
    # --- synthesize ---
    if plan.kind == "bind-word":
        atk_toml = apply_bind_word(honest_toml, plan.word_updates)
    elif plan.kind == "anchor-tree":
        (b / "honest.toml").write_text(honest_toml)
        cmd = ["node", "synth_witness.mjs", "anchor-tree", "--honest", "honest.toml",
               "--out", "anchor.json"]
        if plan.node_plan:
            if "amount_override" in plan.node_plan:
                cmd += ["--amount-override", plan.node_plan["amount_override"]]
            if "chain_override" in plan.node_plan:
                cmd += ["--chain-override", plan.node_plan["chain_override"]]
        p, _ = sh(cmd, cwd=b, timeout=120, log=logs / f"{mid}-synth.log")
        if p.returncode != 0:
            raise RuntimeError("anchor-tree synth failed")
        atk_toml = compose_anchor(honest_toml, json.loads((b / "anchor.json").read_text()),
                                  plan.word_updates or None,
                                  (plan.node_plan or {}).get("dest_override"))
    elif plan.kind == "aztec-branch":
        (b / "honest.toml").write_text(honest_toml)
        p, _ = sh(["node", "synth_witness.mjs", "aztec-branch", "--honest", "honest.toml",
                   "--out", "aztec.json", "--attacker-address", "0xdeadbeef"],
                  cwd=b, timeout=120, log=logs / f"{mid}-synth.log")
        if p.returncode != 0:
            raise RuntimeError("aztec-branch synth failed")
        atk_toml = compose_aztec(honest_toml, json.loads((b / "aztec.json").read_text()))
    elif plan.kind == "replay":
        atk_toml = honest_toml
    (b / "circuits/withdraw/Prover.toml").write_text(atk_toml)
    row["stages"]["synthesize"] = "PASS"
    # --- E2 ---
    p, wall = sh([str(NARGO22), "compile"], cwd=b / "circuits/withdraw", timeout=300,
                 log=logs / f"{mid}-compile.log")
    row["times"]["compile_s"] = round(wall, 1)
    if p.returncode != 0:
        row["stages"]["compile"] = "FAIL"
        return
    ok = execute_witness(b, atk_toml, logs / f"{mid}-execute.log", row, "execute_s")
    if not ok:
        row["stages"]["E2_execute"] = "FAIL"
        return
    row["stages"]["E2_execute"] = "PASS"
    row["E"] = "E2"
    if stop_after == "E2":
        return
    # --- E3 ---
    if load1() > LOAD_LIMIT and not IGNORE_LOAD:
        row["stages"]["E3_prove"] = f"SKIPPED: load {load1():.1f} > {LOAD_LIMIT}"
        return
    proof_hex = prove_witness(b, logs / f"{mid}-prove.log", row, "prove_s", "proof")
    if proof_hex is None:
        row["stages"]["E3_prove"] = "FAIL"
        return
    row["stages"]["E3_prove"] = "PASS"
    row["E"] = "E3"
    if stop_after == "E3":
        return
    # --- E4 ---
    if plan.kind == "aztec-branch":
        # Aztec-branch consumer effect is preserved D1P-15 evidence; check
        # correspondence of this fresh build to the proved artifact.
        prove_correspondence_c03(b, out, row)
        return
    run_replay(mid, b, out, row, plan, proof_hex, honest_toml, warning,
               twice=(plan.kind == "replay"))


def stage_payy_build(mid, out, rollup_src=None):
    """Compile mutant (or pinned, for control) consumer + mocks with pinned solc."""
    b = out / "payy-build" / mid
    if rollup_src is None and (b / "artifacts.json").exists():
        return b  # cached: same mutant consumer already compiled
    if b.exists():
        shutil.rmtree(b)
    (b / "contracts/rollup3").mkdir(parents=True)
    (b / "contracts/noir").mkdir(parents=True)
    (b / "contracts/mocks").mkdir(parents=True)
    (b / "stubs/proxy/utils").mkdir(parents=True)
    (b / "stubs/access").mkdir(parents=True)
    mutdir = out / "mutants"
    base = PAYY_REF / "eth/contracts"
    src = rollup_src or (mutdir / mid / "RollupV1.sol")
    if not isinstance(src, Path) or not src.exists():
        src = base / "rollup3/RollupV1.sol"
    shutil.copy(src, b / "contracts/rollup3/RollupV1.sol")
    for f in ("noir/IVerifier.sol",):
        shutil.copy(base / f, b / "contracts" / f)
    shutil.copy(ROOT / "benchmarks/binding-mutants/baselines/payy-IUSDC.sol", b / "contracts/IUSDC.sol")
    shutil.copy(ROOT / "scripts/xav/XAVProxy.sol", b / "contracts/XAVProxy.sol")
    shutil.copy(base / "mocks/MockUSDC.sol", b / "contracts/mocks/MockUSDC.sol")
    shutil.copy(base / "mocks/MockVerifier.sol", b / "contracts/mocks/MockVerifier.sol")
    shutil.copy(ROOT / "benchmarks/binding-mutants/_stubs/payy/proxy/utils/Initializable.sol",
                b / "stubs/proxy/utils/Initializable.sol")
    shutil.copy(ROOT / "benchmarks/binding-mutants/_stubs/payy/access/OwnableUpgradeable.sol",
                b / "stubs/access/OwnableUpgradeable.sol")
    # OZ sources are COPIED dereferenced: solc allow-paths cannot traverse the
    # reference tree's nested pnpm symlinks. tsx/viem use the node_modules symlink.
    oz_dst = b / "oz" / "@openzeppelin" / "contracts"
    oz_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REF_NM / "@openzeppelin/contracts", oz_dst, symlinks=False,
                    ignore_dangling_symlinks=True)
    return b


def payy_compile(b, logs, tag):
    """Compile via pinned solc CLI (offline) into combined-json; return {name: (abi, bin)}."""
    oz_src = REF_NM  # WarpToad backend OZ 5.x sources reused (same major as Payy 5.0.1)
    inp = {
        "language": "Solidity",
        "sources": {str(p.relative_to(b)): {"content": p.read_text()} for p in
                    list((b / "contracts").rglob("*.sol")) + list((b / "stubs").rglob("*.sol"))},
        "settings": {"optimizer": {"enabled": True, "runs": 200}, "viaIR": True,
                     "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}},
                     "remappings": ["@openzeppelin/=oz/@openzeppelin/",
                                    "@openzeppelin/contracts-upgradeable/=stubs/"]},
    }
    (b / "input.json").write_text(json.dumps(inp))
    nm_real = os.path.realpath(b / "node_modules")
    p, _ = sh([str(PAYY_SOLC), "--standard-json", "--base-path", str(b),
               "--allow-paths", f"{b},{nm_real},{oz_src},{PAYY_REF}/eth/contracts"],
              cwd=b, timeout=900, log=logs / f"{tag}-solc.log",
              stdin_text=(b / "input.json").read_text())
    out_json = json.loads(p.stdout)
    if p.returncode != 0 or "errors" in out_json and any(e.get("severity") == "error" for e in out_json["errors"]):
        raise RuntimeError("payy solc failed: " + json.dumps(out_json.get("errors", p.stderr))[:500])
    arts = {}
    for src, contracts in out_json["contracts"].items():
        for name, c in contracts.items():
            arts[name] = {"abi": c["abi"], "bytecode": "0x" + c["evm"]["bytecode"]["object"]}
    return arts


def run_payy(mid, warning, out, row, rollup_src=None):
    """Mock-verifier-scoped consumer replay (E2 max; verifier changed by design)."""
    import socket
    logs = out / "logs"
    t0 = time.monotonic()
    b = stage_payy_build(mid if rollup_src is None else f"{mid}-control", out,
                         rollup_src=rollup_src)
    cached = rollup_src is None and (b / "artifacts.json").exists()
    if not cached:
        # node_modules symlink for tsx/viem resolution
        if not (b / "node_modules").exists():
            (b / "node_modules").symlink_to(REF_NM, target_is_directory=True)
        shutil.copy(ROOT / "scripts/xav/payy_replay.ts", b / "payy_replay.ts")
    try:
        arts = json.loads((b / "artifacts.json").read_text()) if cached \
            else payy_compile(b, logs, f"{mid}-{warning['id']}")
    except RuntimeError as exc:
        row["stages"]["payy_compile"] = f"FAIL: {exc}"[:200]
        return
    row["stages"]["payy_compile"] = "PASS (cached)" if cached else "PASS"
    for name in ("RollupV1", "MockUSDC", "MockVerifier", "XAVProxy"):
        if name not in arts or arts[name]["bytecode"] == "0x":
            row["stages"]["payy_compile"] = f"FAIL: {name} empty"
            return
    if rollup_src is None:
        (b / "artifacts.json").write_text(json.dumps(arts))
    experiments = payy_experiments(mid, warning)
    if not experiments:
        row["stages"]["blocked"] = "no mock-verifier experiment for this shape"
        row["manual_steps"] = ["real inner-proof vector (Rust stack)"]
        return
    # anvil on a fixed high port
    port = 18549
    anv = subprocess.Popen(["anvil", "--port", str(port), "--silent"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        for exp in experiments:
            plan_doc = {"label": f"{mid}-{exp['name']}",
                        "consumer": arts["RollupV1"], "mockUsdc": arts["MockUSDC"],
                        "mockVerifier": arts["MockVerifier"], "proxy": arts["XAVProxy"],
                        "noteKind": PAYY_NOTE_KIND,
                        "vkHash": PAYY_VK_HASH, "messagesLen": exp["messages_len"],
                        "validatorKey": PAYY_VALIDATOR_KEY, **exp["plan"]}
            (b / "payy-plan.json").write_text(json.dumps(plan_doc))
            p, wall = sh(["npx", "--no-install", "tsx", "payy_replay.ts"], cwd=b, timeout=600,
                         log=logs / f"{mid}-{warning['id']}-{exp['name']}.log",
                         extra_env={"XAV_PAYY_PLAN": str((b / "payy-plan.json").resolve()),
                                    "XAV_PAYY_REPORT": str((b / f"payy-report-{exp['name']}.json").resolve()),
                                    "XAV_ANVIL_URL": f"http://127.0.0.1:{port}"})
            row["times"][f"payy_{exp['name']}_s"] = round(wall, 1)
            if p.returncode != 0:
                row["stages"][f"payy_{exp['name']}"] = "FAIL: harness"
                continue
            rep = json.loads((b / f"payy-report-{exp['name']}.json").read_text())
            verdict = exp["judge"](rep)
            row["stages"][f"payy_{exp['name']}"] = verdict
            if verdict.startswith("PASS"):
                row["E"] = "E2 (mock-verifier-scoped)"
    finally:
        anv.terminate()
    row["times"]["total_wall_s"] = round(row["times"].get("total_wall_s", 0) + (time.monotonic() - t0), 1)
    if row["E"] == "E1":
        row["manual_steps"] = ["real inner-proof vector (Rust stack) for anything above E2"]


def payy_experiments(mid, warning):
    """Return mock-verifier experiments for consumer-shaped Payy warnings."""
    H = "0x" + "ab" * 32
    V = "0x" + "0" * 60 + "03e8"  # 1000 as bytes32 (Payy mints carry bytes32 values)
    R_ADDR = "0x90f79bf6eb2c4f870365e785982e1f101e93b906"  # anvil account 3
    R = "0x" + "0" * 24 + R_ADDR[2:]  # bytes32-left-padded recipient word
    N1, N2, C0 = "0x" + "aa" * 32, "0x" + "bb" * 32, "0x" + "00" * 32
    mint_words = ["0x" + "00" * 31 + "02", PAYY_NOTE_KIND, V, H]
    burn_words = ["0x" + "00" * 31 + "03", PAYY_NOTE_KIND, V, H, R]
    S = lambda h, o, n, words: {"settle": {"height": h, "oldRoot": o, "newRoot": n,
                                           "commitHash": C0, "otherHash": PAYY_OTHER_HASH, "words": words}}
    loc, rule = warning.get("location", ""), warning["rule"]
    out = []
    is_mint_shape = (rule == "R-EFFECT" and loc in ("RollupV1.sol:842", "RollupV1.sol:850")) or \
                    (rule == "R-POLARITY" and loc == "RollupV1.sol:357")
    # Mint-shape experiments run for every mutant carrying such a warning: the mock
    # verifier stands in for "the circuit emitted attacker messages". For consumer
    # mutants (PY-S01/S02) that is the whole defect; for circuit mutants (PY-C02)
    # it shows the consumer-path effect contingent on the circuit defect.
    if mid in ("PY-S01", "PY-C02") and is_mint_shape:
        out.append({"name": "settle-unregistered", "messages_len": 4,
                    "plan": {"actions": [S(1, PAYY_EMPTY_ROOT, N1, mint_words)],
                             "watchHashes": [H], "watchBalances": []},
                    "judge": lambda rep: "PASS: unregistered mint settled" if _settle_ok(rep, 0)
                    else f"no effect: {rep.get('revert_0', rep.get('steps'))}"[:160]})
    if mid in ("PY-S02", "PY-C02") and is_mint_shape:
        out.append({"name": "settle-twice", "messages_len": 4,
                    "plan": {"actions": [{"register": {"hash": H, "value": V}},
                                         S(1, PAYY_EMPTY_ROOT, N1, mint_words),
                                         S(2, N1, N2, mint_words)],
                             "watchHashes": [H], "watchBalances": []},
                    "judge": lambda rep: "PASS: registered mint settled twice" if _settle_ok(rep, 1) and _settle_ok(rep, 2)
                    else f"no effect: {json.dumps(rep.get('steps'))}"[:160]})
    if mid in ("PY-S03",) and rule == "R-EFFECT":
        out.append({"name": "settle-burn", "messages_len": 5,
                    "plan": {"actions": [{"fund_rollup": {"value": V}},
                                         S(1, PAYY_EMPTY_ROOT, N1, burn_words)],
                             "watchHashes": [], "watchBalances": [R_ADDR, "0x" + PAYY_NOTE_KIND[-40:]]},
                    "judge": lambda rep: "PASS: burn payout misdirected (see balances)" if _settle_ok(rep, 1)
                    else "no effect"})
    if mid in ("PY-S04",) and rule == "R-EFFECT":
        k4 = ["0x" + "00" * 31 + "04", PAYY_NOTE_KIND, V, H, R]
        out.append({"name": "settle-kind4", "messages_len": 5,
                    "plan": {"actions": [{"fund_rollup": {"value": V}},
                                         S(1, PAYY_EMPTY_ROOT, N1, k4)],
                             "watchHashes": [], "watchBalances": [R_ADDR]},
                    "judge": lambda rep: "PASS: dead kind-4 settled as burn" if _settle_ok(rep, 1)
                    else "no effect"})
    return out


def _settle_ok(rep, idx):
    for s in rep.get("steps", []):
        for k, v in s.items():
            if k.startswith(f"{idx}_settle") and v == "success":
                return True
    return False


def prove_correspondence_c03(b, out, row):
    import hashlib as _hl
    pref = Path(os.environ.get(
        "BINDCHECK_MDOM_ARTIFACT",
        ROOT / "results/raw/D1P-15/artifacts/m-dom-withdraw.json",
    ))
    art = json.loads((b / "circuits/withdraw/target/withdraw.json").read_text())
    proved = json.loads(pref.read_text())
    same_bytecode = art.get("bytecode") == proved.get("bytecode")
    same_abi = art.get("abi") == proved.get("abi")
    same_ver = art.get("noir_version") == proved.get("noir_version")
    row["stages"]["E4_preserved_correspondence"] = {
        "bytecode_equal": same_bytecode, "abi_equal": same_abi,
        "noir_version_equal": same_ver,
        "proved_artifact_sha256": _hl.sha256(pref.read_bytes()).hexdigest()}
    if same_bytecode and same_abi and same_ver:
        row["E"] = "E4-preserved"
        row["manual_steps"] = ["associate preserved D1P-15 foreign-proof E4 chain",
                               "rely on prior fixtures (proof, verifier, replay)"]
        row["stages"]["E4_effect"] = ("PASS-preserved: fresh E3 proof on byte-identical artifact; "
                                      "consumer effect from D1P-15 foreign replay")


def execute_witness(b, toml_text, log_path, row, time_key):
    (b / "circuits/withdraw/Prover.toml").write_text(toml_text)
    p, wall = sh([str(NARGO22), "execute"], cwd=b / "circuits/withdraw", timeout=300, log=log_path)
    row["times"][time_key] = round(wall, 1)
    return p.returncode == 0 and "successfully solved" in p.stdout


def prove_witness(b, log_path, row, time_key, tag):
    p, wall = sh(["nice", "-n", "19", "node", "prove.mjs", "--artifact",
                  "circuits/withdraw/target/withdraw.json", "--witness",
                  "circuits/withdraw/target/withdraw.gz", "--out", tag],
                 cwd=b, timeout=2700, log=log_path)
    row["times"][time_key] = round(wall, 1)
    if p.returncode != 0:
        return None
    proof_out = json.loads(p.stdout.strip().splitlines()[-1])
    row["stages"].setdefault("E3_public_inputs", proof_out.get("publicInputs"))
    return (b / tag / "proof").read_bytes().hex()


PAYY_REF = Path(os.environ.get(
    "BINDCHECK_PAYY_EARLIER", ROOT / "tools/cases/payy-c4d2c90"
))
PAYY_SOLC = Path(os.environ.get(
    "BINDCHECK_SOLC_0_8_20", ROOT / "results/raw/artifact-tools/bin/solc-0.8.20"
))
PAYY_NOTE_KIND = "0x1111111111111111111111111111111111111111111111111111111111111111"
PAYY_VK_HASH = "0x2222222222222222222222222222222222222222222222222222222222222222"
PAYY_VALIDATOR_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
PAYY_OTHER_HASH = "0x3333333333333333333333333333333333333333333333333333333333333333"
PAYY_EMPTY_ROOT = "0x0577b5b4aa3eaba75b2a919d5d7c63b7258aa507d38e346bf2ff1d48790379ff"

S_SRC_BURNS = None


def src_burns():
    global S_SRC_BURNS
    if S_SRC_BURNS is None:
        states = json.loads(Path(os.environ.get(
            "BINDCHECK_CANONICAL_STATES",
            ROOT / "results/raw/D1P-19/canonical-states.json",
        )).read_text())
        S_SRC_BURNS = [{"preCommitment": x["preCommitment"], "amount": x["amount"]}
                       for x in states["S_SRC"]["burns"]]
    return S_SRC_BURNS


def _plan_word(plan):
    words = list((plan.word_updates or {}).keys())
    return words[0] if len(words) == 1 else None


def mint_calldata(b, plan, kind):
    toml = (b / "circuits/withdraw/Prover.toml").read_text()
    if kind in ("anchor-tree",):
        # The composed witness is authoritative (dest may be honest-overridden).
        root = toml_get(toml, "destination_local_root")
        giga = toml_get(toml, "giga_root")
    else:
        root = toml_get(toml, "destination_local_root")
        giga = toml_get(toml, "giga_root")
    toml = (b / "circuits/withdraw/Prover.toml").read_text()
    fee = {k: toml_get(toml, k) for k in ("nullifier", "amount", "fee_factor", "priority_fee",
                                          "max_fee", "relayer_address", "recipient_address")}

    def addr(h):
        # viem needs 20-byte addresses; the proof binds the field value.
        n = int(h, 16)
        return "0x" + n.to_bytes(20, "big").hex()

    return {"nullifier": fee["nullifier"], "amount": toml_get(toml, "amount"),
            "gigaRoot": giga, "localRoot": root, "feeFactor": fee["fee_factor"],
            "priorityFee": fee["priority_fee"], "maxFee": fee["max_fee"],
            "relayer": addr(fee["relayer_address"]), "recipient": addr(fee["recipient_address"])}


def run_replay(mid, b, out, row, plan, proof_hex, honest_toml, warning, twice):
    logs = out / "logs"
    verifier_sol = (b / "proof/verifier.sol").read_text()
    (b / "contracts/verifier/HonkVerifier.sol").write_text(verifier_sol)
    mint = mint_calldata(b, plan, plan.kind)
    giga = mint["gigaRoot"]
    aztec_addr = "0x0"
    mints = [{**mint, "proofHex": "0x" + proof_hex}]
    if twice and plan.kind == "replay":
        mints.append({**mint, "proofHex": "0x" + proof_hex})
    # Shape: nullifier-word BIND plans prove the real note still spends
    # after the attacker nullifier was recorded (double-spend shape).
    if plan.kind == "bind-word" and _plan_word(plan) == "nullifier":
        if execute_witness(b, honest_toml, logs / f"{mid}-execute-honest.log", row, "execute_honest_s"):
            h2 = prove_witness(b, logs / f"{mid}-prove-honest.log", row, "prove_honest_s", "proof-honest")
            if h2 is not None:
                hm = dict(mint)
                hwords = {k: toml_get(honest_toml, k) for k in
                          ("nullifier", "amount", "fee_factor", "priority_fee", "max_fee",
                           "relayer_address", "recipient_address")}
                hm.update({"nullifier": hwords["nullifier"]})
                mints.append({**hm, "proofHex": "0x" + h2})
                row["stages"]["honest_second_proof"] = "PASS"
            else:
                row["stages"]["honest_second_proof"] = "FAIL"
        else:
            row["stages"]["honest_second_proof"] = "FAIL: honest witness rejected by mutant"
    burns = src_burns()
    if plan.kind == "anchor-tree" and (plan.node_plan or {}).get("burn_attacker_note"):
        # Admit the attacker's own tree: burn the attacker note on-chain so
        # the chain root equals the witness root (admission passes; the
        # defective word stays attacker-chosen).
        spec = json.loads((b / "anchor.json").read_text())
        burns = [{"preCommitment": spec["attacker_pre_commitment"],
                  "amount": spec["attacker_amount"]}]
    elif plan.kind == "anchor-tree" and (warning["rule"] == "R-CONSUMER"):
        # Admission itself removed: nothing to seed; giga comes from the mock.
        burns = []
    plan_doc = {"label": mid, "mints": mints, "mint": mints[0], "proofHex": mints[0]["proofHex"],
                "gigaRoot": giga, "aztecAddress": aztec_addr,
                "burns": burns, "mintTwice": False}
    (b / "plan.json").write_text(json.dumps(plan_doc))
    p, wall = sh(["npx", "--no-install", "hardhat", "compile"], cwd=b, timeout=900,
                 log=logs / f"{mid}-hhcompile.log",
                 extra_env={"NODE_PATH": str(b / "node_modules")})
    row["times"]["hhcompile_s"] = round(wall, 1)
    if p.returncode != 0:
        row["stages"]["E4_harness"] = "FAIL: hardhat compile"
        return
    p, wall = sh(["npx", "--no-install", "hardhat", "run", "replay.ts"], cwd=b, timeout=1200,
                 log=logs / f"{mid}-replay.log",
                 extra_env={"XAV_PLAN": str((out / "build" / mid / "plan.json").resolve()),
                            "XAV_REPORT": str((out / "build" / mid / "report.json").resolve()),
                            "XAV_REF_BUILDINFO": str(REF_BUILDINFO)})
    row["times"]["replay_s"] = round(wall, 1)
    if p.returncode == 2:
        row["stages"]["E4_harness"] = "FAIL: harness error"
        return
    try:
        report = json.loads((b / "report.json").read_text())
    except (OSError, ValueError):
        row["stages"]["E4_harness"] = "FAIL: no report"
        return
    row["stages"]["E4_replay"] = report
    mints = [s for s in report.get("steps", []) if any(k.startswith("mint_") for k in s)]
    successes = sum(1 for s in mints if isinstance(list(s.values())[0], dict)
                    and list(s.values())[0].get("status") in ("0x1", "success"))
    # Expected successes, all by shape: replay kinds and nullifier-word
    # BIND plans need 2 (double-spend); reject/revert shapes expect 0.
    # R-BIND max_fee is contained (consumer re-checks); R-CONSUMER max_fee
    # is the defect itself (over-charge expected to succeed).
    need = 2 if (plan.kind == "replay" or row["stages"].get("honest_second_proof") == "PASS"
                 or _plan_word(plan) == "nullifier") else 1
    contained_shape = (plan.kind == "bind-word" and _plan_word(plan) in ("chain_id", "recipient_address"))
    contained_shape = contained_shape or (warning["rule"] == "R-BIND" and _plan_word(plan) == "max_fee")
    contained_shape = contained_shape or (warning["rule"] == "R-EFFECT")
    if contained_shape:
        row["stages"]["E4_effect"] = (
            "contained as predicted" if successes == 0
            else f"UNEXPECTED success ({successes}); see report")
        row["stages"]["E4_successes"] = successes
    elif successes >= need:
        row["E"] = "E4"
        row["stages"]["E4_effect"] = f"PASS: {successes}/{need} expected mints succeeded"
    else:
        row["stages"]["E4_effect"] = f"only {successes}/{need} mints succeeded; see reverts"


if __name__ == "__main__":
    main()
