#!/usr/bin/env python3
"""Attach lock, fetch, dependency, and reproducibility metadata to gate manifests."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "benchmark/public-triples"
RAW = ROOT / "results/raw/bench"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    try: return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return None


def main():
    rows = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    dep_records=[]
    for name in ("runs.json","runs-self.json"):
        dep_records.extend((load(RAW / "public-deps-20261109" / name) or {"records": []})["records"])
    dep_index = {(r["repository"],r["commit"]):r for r in dep_records}
    for row in rows:
        path = MANIFESTS / f"GATE-{row['row']}" / "manifest.json"
        manifest = load(path)
        manifest["repository_url"] = f"https://github.com/{row['repository']}.git"
        manifest["exposure"] = row["exposed"] or "NOT_MARKED"
        manifest["unscored_proposal"] = {
            "expected_pattern": row["proposed_expected_pattern"],
            "expected_location_regex": row["proposed_location_regex"],
            "source": "gate/GATE-MANIFEST.csv; reviewer card remains PENDING"}
        manifest["protocol_class"] = (
            "PLONK" if row["row"]=="22" else
            "NOIR_ULTRAHONK" if row["row"]=="24" else
            "CIRCOM_GROTH16_SOURCE_LINKED_KEY_UNPROVEN" if row["row"] in
            ("15","28","29","30","31","32","33","36","40","47") else
            "UNRESOLVED")
        manifest["reconstruction"] = {
            "script": "benchmark/fetch_public.py; benchmark/checkout_public.py; benchmark/audit_public.py",
            "fetch_ledger": "results/raw/bench/public-fetch-20261109/fetch.json",
            "checkout_ledger": "results/raw/bench/public-fetch-20261109/checkouts.json",
            "build_ledger": "results/raw/bench/public-audit-20261109/",
            "dependency_ledger": "results/raw/bench/public-deps-20261109/runs.json"}
        for side,rev in manifest["revisions"].items():
            source=pathlib.Path(rev["source"])
            if row["row"]=="21":
                rev["structural_blocker"]=("Verifier path is a symlink to ../build/verifier.sol; "
                    "target and ../build/verification_key.json are absent from the pinned Git tree. "
                    "semaphorejs/scripts/build_verifier.sh requires that key, so the original generated "
                    "verifier cannot be pinned from this commit.")
            rev["git_fetch_command"]=["git","fetch","--filter=blob:none","--no-tags","--depth=1",
                                      "origin",rev["commit"]]
            locks=[]
            for rel in ("yarn.lock","package-lock.json","pnpm-lock.yaml"):
                target=source/rel
                if target.is_file(): locks.append({"path":rel,"sha256":sha(target)})
            rev["locks"]=locks
            dep=dep_index.get((rev["repository"],rev["commit"]))
            rev["dependency_install"]={"status":"NOT_ATTEMPTED"} if dep is None else {
                "status":"TIMEOUT" if dep.get("timed_out") else "COMPLETED" if dep["exit_status"]==0 else "FAILED",
                "argv":dep["argv"],"lock_sha256":dep["lock_sha256"],
                "stdout":dep["stdout"],"stdout_sha256":dep["stdout_sha256"],
                "stderr":dep["stderr"],"stderr_sha256":dep["stderr_sha256"]}
            if row["row"]=="36":
                receipt=load(RAW/"public-deps-20261109/gate36/receipt.json")
                rev["dependency_install"]={
                    "status":"COMPLETED" if receipt and receipt["expected_integrity"]==receipt["observed_integrity"] else "UNKNOWN",
                    "receipt":"results/raw/bench/public-deps-20261109/gate36/receipt.json",
                    "package":"circomlib@2.0.2",
                    "integrity":receipt["observed_integrity"] if receipt else None}
            elif row["row"]=="22":
                rev["dependency_install"]={
                    "status":"COMPLETED",
                    "receipt":"results/raw/bench/e1-build-20261109-verified/build.json",
                    "package":"@openzeppelin/contracts@4.4.1"}
            builds={k:v.get("status") for k,v in rev.get("build",{}).items()
                    if k in ("circuit","verifier","consumer")}
            if rev.get("structural_blocker"):
                status="STRUCTURAL_BLOCKED"
            elif all(builds.get(k)=="BUILD_OK" for k in ("circuit","verifier","consumer")):
                status="BUILD_OK"
            elif "TIMEOUT" in builds.values():
                status="BUILD_TIMEOUT"
            elif any(s in ("BUILD_FAILED","FILE_MISSING","ROLE_MISSING","UNSUPPORTED_FRONTEND")
                     for s in builds.values()):
                status="BUILD_FAILED"
            else:
                status="UNKNOWN"
            rev["buildability"]={"status":status,"role_statuses":builds,
                                 "reason":rev.get("structural_blocker") or
                                 ("; ".join(f"{k}:{v}" for k,v in builds.items() if v!="BUILD_OK") or None)}
            repo=row["repository"]
            if repo=="zkemail/ether-email-auth":
                rev["source_correspondence"]="EmailAuth calls utils/Verifier.verifyEmailProof, which calls the committed generated Groth16Verifier; email_auth.circom is the selected main. Verifying-key identity against the circuit is unproved."
            elif repo=="selfxyz/self":
                rev["source_correspondence"]="IdentityVerificationHubImplV1 dispatches to a named generated verifier matching the selected main circuit family; verifying-key identity against the circuit is unproved."
            elif row["row"]=="36":
                rev["source_correspondence"]="SemaphoreCore._isValidProof calls the generated Verifier with root, nullifierHash, signalHash, and externalNullifier; circuits/semaphore.circom declares the corresponding public inputs. Verifying-key identity is unproved."
            else:
                rev["source_correspondence"]="No complete Circom/generated-Groth16/consumer source correspondence is established."
        path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
