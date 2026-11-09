#!/usr/bin/env python3
"""Audit exact gate revisions and attempt three-role builds without inventing triples."""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench/public-audit-20261109"
WORK = ROOT / "results/raw/bench/public-fetch-20261109/work"
OUT = ROOT / "benchmark/public-triples"
CIRCOM = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/tools/circom-src/target/release/circom")

EMAIL = {"circuit": "packages/circuits/src/email_auth.circom",
         "verifier": "packages/contracts/src/utils/Groth16Verifier.sol",
         "consumer": "packages/contracts/src/EmailAuth.sol",
         "intermediary": "packages/contracts/src/utils/Verifier.sol"}
SELF = {"circuit": "circuits/circuits/disclose/vc_and_disclose.circom",
        "verifier": "contracts/contracts/verifiers/disclose/Verifier_vc_and_disclose.sol",
        "consumer": "contracts/contracts/IdentityVerificationHubImplV1.sol",
        "target": "circuits/circuits/utils/crypto/merkle-trees/smt.circom"}
ROLES = {
    "14": {"circuit": "circuits/circom/tallyVotes.circom", "verifier": None,
           "consumer": "contracts/contracts/Poll.sol",
           "candidate_verifier": "circuits/ts/verifier_groth16.sol",
           "blocker": "Only a snarkJS Solidity template with <%contract_name%> and a dynamic-VK verifier are committed; no generated circuit-specific Groth16 verifier for tallyVotes is pinned. Gate card also identifies a different processMessages fix."},
    "15": SELF,
    "20": {"circuit": "circuits/set/membership.circom", "verifier": None,
           "consumer": "packages/contracts/contracts/vanchors/base/ZKVAnchorBase.sol",
           "blocker": "SetMembership is a template with no component main; committed generated VAnchor verifiers correspond to transaction circuits, with no identified membership-proof consumer/verifier."},
    "21": {"circuit": "semaphorejs/snark/semaphore.circom",
           "verifier": "semaphorejs/contracts/verifier.sol",
           "consumer": "semaphorejs/contracts/Semaphore.sol",
           "blocker": "Verifier path is a symlink to ../build/verifier.sol; target and ../build/verification_key.json are absent from the pinned Git tree. semaphorejs/scripts/build_verifier.sh requires that key, so the original generated verifier cannot be pinned from this commit."},
    "22": {"circuit": "circuits/circuit.circom",
           "verifier": "contracts/compiled/MerkVerifier.sol",
           "consumer": "contracts/PrivateAirdrop.sol",
           "blocker": "Committed snarkJS-generated verifier declares PlonkVerifier, not Groth16."},
    "24": {"circuit": "noir/agg_agg/src/main.nr",
           "verifier": "eth/contracts/AggregateVerifierV1.sol",
           "consumer": "eth/contracts/rollup3/RollupV1.sol",
           "blocker": "Pinned circuit is Noir and consumer uses UltraHonk; no Circom/Groth16 triple."},
    **{str(n): dict(EMAIL, target={30:"packages/circuits/src/regexes/invitation_code_with_prefix_regex.circom",
                                   32:"packages/circuits/src/utils/digit2int.circom",
                                   33:"packages/circuits/src/email_auth_template.circom"}.get(n))
       for n in (28,29,30,31,32,33,40)},
    "36": {"circuit": "circuits/semaphore.circom",
           "verifier": "contracts/base/Verifier.sol",
           "consumer": "contracts/base/SemaphoreCore.sol",
           "target": "contracts/base/SemaphoreGroups.sol"},
    "38": {"circuit": None, "verifier": None,
           "consumer": "src/EmailRecoveryManager.sol",
           "blocker": "Neither pinned revision contains a .circom source or generated Groth16 verifier; only a test mock verifier is present."},
    "47": {"circuit": "circuits/circuits/register_id/instances/register_id_sha256_sha256_sha256_rsa_65537_4096.circom",
           "verifier": "contracts/contracts/verifiers/register/Verifier_register_sha256_sha256_sha256_rsa_65537_4096.sol",
           "consumer": "contracts/contracts/IdentityVerificationHubImplV1.sol",
           "target": "circuits/circuits/register_id/register_id.circom"},
}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def command(argv, cwd, temp, name, timeout=90):
    start = time.monotonic()
    try:
        proc = subprocess.Popen([str(x) for x in argv], cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            timed_out = True
        code = proc.returncode
    except OSError as exc:
        stdout, stderr, timed_out, code = b"", str(exc).encode(), False, None
    (temp / f"{name}.stdout").write_bytes(stdout)
    (temp / f"{name}.stderr").write_bytes(stderr)
    return {"argv": [str(x) for x in argv], "cwd": str(cwd), "exit_status": code,
            "timed_out": timed_out, "elapsed_seconds": time.monotonic() - start,
            "stdout": str(temp / f"{name}.stdout"), "stdout_sha256": sha(temp / f"{name}.stdout"),
            "stderr": str(temp / f"{name}.stderr"), "stderr_sha256": sha(temp / f"{name}.stderr"),
            "stderr_excerpt": stderr.decode(errors="replace")[:1200]}


def one(row, side):
    cid = f"GATE-{row['row']}"
    commit = row["vulnerable_commit" if side == "vulnerable" else "fixed_commit"]
    source = WORK / row["repository"].replace("/", "__") / commit[:12]
    roles = ROLES[row["row"]]
    out_root = RAW / cid / side
    out_root.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while (out_root / f"attempt-{attempt:03d}").exists():
        attempt += 1
    out = out_root / f"attempt-{attempt:03d}"
    out.mkdir()
    result = {"commit": commit, "repository": row["repository"],
              "source": str(source), "roles": {}, "build": {},
              "structural_blocker": roles.get("blocker")}
    if not source.is_dir():
        result["status"] = "SOURCE_MISSING"
        return result
    head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    result["observed_head"] = head.stdout.strip() if head.returncode == 0 else None
    if result["observed_head"] != commit:
        result["status"] = "REVISION_MISMATCH"
        return result
    for role, rel in roles.items():
        if role == "blocker" or rel is None:
            continue
        path = source / rel
        if path.is_symlink():
            target = path.resolve()
            result["roles"][role] = {"path": rel, "type": "symlink",
                                     "link_target": os.readlink(path),
                                     "target_exists": target.is_file(),
                                     "sha256": sha(path) if target.is_file() else None}
        elif path.is_file():
            result["roles"][role] = {"path": rel, "type": "file", "sha256": sha(path)}
        else:
            result["roles"][role] = {"path": rel, "type": "missing", "sha256": None}
    with tempfile.TemporaryDirectory(prefix="build-", dir=out) as scratch:
        tmp = pathlib.Path(scratch)
        for role in ("circuit", "verifier", "consumer"):
            rel = roles.get(role)
            if not rel:
                result["build"][role] = {"status": "ROLE_MISSING"}
                continue
            path = source / rel
            if not path.is_file():
                result["build"][role] = {"status": "FILE_MISSING"}
                continue
            build_out = tmp / f"{role}-out"
            build_out.mkdir()
            if path.suffix == ".circom":
                argv = [CIRCOM, path, "--r1cs", "--sym", "--O0", "-o", build_out,
                        "-l", source / "node_modules", "-l",
                        pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk/node_modules")]
                if row["repository"] == "selfxyz/self":
                    argv.extend(["-l", source / "node_modules/circomlib/circuits"])
            elif path.suffix == ".sol":
                solc = (pathlib.Path("/Users/imranpollob/.solc-select/artifacts/solc-0.8.28/solc-0.8.28")
                        if row["repository"] == "selfxyz/self" else "solc")
                argv = [solc, "--bin", "--base-path", source,
                        "--include-path", source / "node_modules"]
                if row["row"] in ("20","22"):
                    argv.extend(["--include-path", ROOT / "results/raw/bench/deps-20261109/node_modules"])
                argv.extend(["-o", build_out, path])
            else:
                result["build"][role] = {"status": "UNSUPPORTED_FRONTEND", "path": rel}
                continue
            run = command(argv, source, out, role, timeout=90)
            run["status"] = "TIMEOUT" if run["timed_out"] else "BUILD_OK" if run["exit_status"] == 0 else "BUILD_FAILED"
            result["build"][role] = run
    result["status"] = "STRUCTURAL_BLOCKED" if result["structural_blocker"] else "BUILDS_ATTEMPTED"
    return result


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=None)
    args = ap.parse_args()
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    if args.ids is not None:
        rows = [row for row in rows if row["row"] in args.ids]
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {(row["row"], side): pool.submit(one, row, side)
                   for row in rows for side in ("vulnerable", "repaired")}
        result = {}
        for (number, side), future in futures.items():
            record = future.result()
            result[(number, side)] = record
            print(number, side, record["status"], flush=True)
    for row in rows:
        cid = f"GATE-{row['row']}"
        manifest = {"schema": "bindcheck-benchmark.public-triple/v1",
                    "id": cid, "origin": "public-report", "label_status": "PENDING",
                    "repository": row["repository"],
                    "gate_manifest": "gate/GATE-MANIFEST.csv",
                    "revisions": {side: result[(row["row"], side)]
                                  for side in ("vulnerable", "repaired")}}
        folder = OUT / cid
        folder.mkdir(exist_ok=True)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (RAW / "summary.json").write_text(json.dumps({"records": {f"{n}/{s}": result[(n,s)]["status"]
                              for n,s in sorted(result)}}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
