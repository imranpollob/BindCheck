#!/usr/bin/env python3
"""Freeze the E1 case inventory. This script reads sources, never tool outcomes."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark"
CASES = OUT / "cases"
ORIGINAL = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk")
GT = pathlib.Path("/Users/imranpollob/Coding/bc/bindcheck-zk-groundtruth/results/raw/groundtruth/pairs")
DEV = ORIGINAL / "feasibility/work/full-dev"
PATTERN = {
    1:"P1", 2:"P1", 3:"P1", 4:"P1", 5:"P1", 6:"P1", 7:"P1", 8:"P3",
    9:"P3", 10:"P5", 11:"R-EXTENT", 12:"R-MASK", 13:"P5", 14:"P3",
    15:"P3", 16:"R-COMMITMENT", 17:"R-COMMITMENT", 18:"R-EXTENT",
    19:"P3", 20:"P1", 21:"P1", 22:"P3", 23:"P1",
}
LOCUS = {11:"Consumer.sol", 12:"circuit.circom", 13:"Consumer.sol", 14:"circuit.circom",
         15:"circuit.circom", 16:"circuit.circom", 17:"circuit.circom",
         18:"Consumer.sol", 10:"Verifier.sol"}

def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def jwrite(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def revision(path: pathlib.Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()

def source_entry(path: pathlib.Path, rel: str) -> dict:
    return {"path": rel, "sha256": digest(path), "bytes": path.stat().st_size}

def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

def add_case(manifest: list, case: dict, files: dict[str, list[dict]]) -> None:
    case_dir = CASES / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    jwrite(case_dir / "case.json", case)
    jwrite(case_dir / "source.lock.json", {"schema":"bindcheck-benchmark.source-lock/v1", "revisions": files})
    manifest.append({"id": case["id"], "case": f"cases/{case['id']}/case.json",
                     "lock": f"cases/{case['id']}/source.lock.json",
                     "origin": case["origin"], "label_status": case["label_status"]})

def main() -> None:
    if CASES.exists():
        raise SystemExit("benchmark/cases already exists; refusing to overwrite frozen labels")
    manifest: list[dict] = []
    home_rev = revision(ROOT)
    expected = json.loads((ROOT / "redteam/adversarial/expected.json").read_text())
    for item in expected["cases"]:
        cid = item["id"]
        n = int(cid[-2:])
        source = ROOT / "redteam/adversarial" / cid
        destination = CASES / cid / "source"
        shutil.copytree(source, destination)
        files = [source_entry(p, p.relative_to(destination).as_posix()) for p in sorted(destination.rglob("*")) if p.is_file()]
        roles = {"circuit":"circuit.circom", "verifier":"Verifier.sol", "consumer":"Consumer.sol"}
        case = {"schema":"bindcheck-benchmark.case/v1", "id":cid, "origin":"synthetic", "protocol":"MOCK_VERIFIER",
                "family":item["family"], "exposure": "EXPOSED", "label_status":"AI-PROPOSED",
                "label_provenance":"redteam/adversarial/expected.json; same team authored arm C",
                "expected_state":"vulnerable" if item["label"] == "VULNERABLE" else "repaired",
                "expected_pattern":PATTERN[n], "expected_location_regex":f"^{re.escape(LOCUS.get(n,'Consumer.sol'))}(:[0-9]+)?$",
                "pair_id":f"ADV-{n:02d}", "revisions":{
                    "selected":{"commit":home_rev, "source_tree":f"benchmark/cases/{cid}/source",
                                "roles":roles, "verifier_kind":"synthetic interface, not generated Groth16"}},
                "limitations":["AI-authored fixture and label; mock verifier is not an end-to-end proof oracle"]}
        add_case(manifest, case, {"selected":files})
    gate = list(csv.DictReader((ROOT / "gate/GATE-MANIFEST.csv").open()))
    receipts = json.loads((GT / "receipts.json").read_text())
    for row in gate:
        cid = "GATE-" + row["row"].zfill(2)
        card = ORIGINAL / row["card"]
        text = card.read_text()
        # Reviewer decision fields are the only source of accepted labels.
        decision = re.search(r"^\| Decision \|\s*(.*?)\s*\|$", text, re.M)
        accepted = bool(decision and re.search(r"\bACCEPT\b", decision.group(1)) and "☐" not in decision.group(1))
        label = "HUMAN-ACCEPTED" if accepted else "PENDING"
        snapshots: dict[str,list[dict]] = {}
        for side, commit in (("vulnerable",row["vulnerable_commit"]),("repaired",row["fixed_commit"])):
            snapshots[side] = []
            for receipt in receipts:
                if str(receipt.get("row")) != row["row"] or receipt.get("side") not in (side, "fixed" if side == "repaired" else side):
                    continue
                src = GT / row["row"] / receipt["side"] / receipt["path"]
                if src.is_file() and digest(src) == receipt.get("sha256"):
                    dest = CASES / cid / "snapshots" / side / receipt["path"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    snapshots[side].append(source_entry(dest, receipt["path"]))
        revisions = {side:{"commit":commit if re.fullmatch(r"[0-9a-f]{40}",commit) else None,
                           "repository":row["repository"], "roles":{"circuit":None,"verifier":None,"consumer":None},
                           "snapshot_root":f"benchmark/cases/{cid}/snapshots/{side}",
                           "snapshot_only":True} for side,commit in (("vulnerable",row["vulnerable_commit"]),("repaired",row["fixed_commit"]))}
        case = {"schema":"bindcheck-benchmark.case/v1", "id":cid, "origin":"public-report", "protocol":"UNRESOLVED",
                "pair_id":cid,
                "source_case_id":row["case_id"], "family":row["family"], "exposure":row["exposed"] or "UNEXPOSED",
                "label_status":label, "label_provenance":str(card), "card_sha256":digest(card),
                "expected_state":"paired", "expected_pattern":None if label == "PENDING" else row["proposed_expected_pattern"],
                "expected_location_regex":None if label == "PENDING" else row["proposed_location_regex"],
                "proposal_pattern":row["proposed_expected_pattern"], "proposal_location_regex":row["proposed_location_regex"],
                "revisions":revisions, "limitations":["Source snapshots do not establish a matched buildable triple; reviewer decision pending" if label == "PENDING" else "Source snapshots do not establish a matched buildable triple"]}
        add_case(manifest,case,snapshots)
    dev_rows = []
    with (ROOT / "dataset/source-corpus-v2.csv").open() as f:
        for row in csv.DictReader(f):
            if row["split"] == "DEV": dev_rows.append(row)
    roles = {
      "zkdrops":{"circuit":"circuits/circuit.circom","verifier":"contracts/compiled/MerkVerifier.sol","consumer":"contracts/PrivateAirdrop.sol"},
      "semaphore":{"circuit":"semaphorejs/snark/semaphore.circom","verifier":"semaphorejs/build/verifier.sol","consumer":"semaphorejs/contracts/Semaphore.sol"},
      "payy":{"circuit":"noir/agg_agg/src/main.nr","verifier":"eth/noir/agg_agg.sol","consumer":"eth/contracts/rollup3/RollupV1.sol"},
    }
    for n in range(1,7):
        row = dev_rows[50+n-1]
        cid=f"DEV-H{n:02d}"
        group="zkdrops" if n<=2 else "semaphore" if n<=4 else "payy"
        checkout=list(DEV.glob(f"{cid}--*--{row['commit'][:12]}"))
        source = checkout[0] if len(checkout)==1 and revision(checkout[0])==row["commit"] else None
        files=[]
        if source:
            for rel in roles[group].values():
                p=source/rel
                if p.is_file():files.append(source_entry(p,rel))
        case={"schema":"bindcheck-benchmark.case/v1", "id":cid,"origin":"DEV-history",
              "protocol":"PLONK" if group=="zkdrops" else "MISSING_VERIFIER" if group=="semaphore" else "ULTRAHONK",
              "family":group,"exposure":"EXPOSED","label_status":"AI-PROPOSED",
              "label_provenance":"historical DEV pair; AI review, not human-adjudicated",
              "expected_state":"vulnerable" if n%2 else "repaired",
              "expected_pattern":"P3" if n<=4 else "R-EXTENT",
              "expected_location_regex":("^contracts/PrivateAirdrop\\.sol(:[0-9]+)?$" if n<=2 else
                  "^semaphorejs/contracts/Semaphore\\.sol(:[0-9]+)?$" if n<=4 else
                  "^noir/agg_agg/src/main\\.nr(:[0-9]+)?$"),
              "pair_id":f"DEV-H{(n+1)//2:02d}",
              "revisions":{"selected":{"commit":row["commit"],"repository":row["repository"],
                    "source_checkout":str(source) if source else None,"roles":roles[group],
                    "verifier_kind":"Noir UltraHonk, outside Circom/Groth16" if group=="payy" else
                    "matched verifier artifact absent" if group=="semaphore" else "snarkJS PLONK, outside Groth16"}},
              "limitations":(["matched verifier artifact absent in preserved checkout"] if group=="semaphore" else
                             ["Noir/UltraHonk is outside this benchmark frontend"] if group=="payy" else
                             ["Generated verifier declares PlonkVerifier; outside Groth16 subset"]) }
        add_case(manifest,case,{"selected":files})
    pairs=[]
    for n in range(1,24):pairs.append({"pair_id":f"ADV-{n:02d}","origin":"synthetic",
        "vulnerable_case":f"ADV-V{n:02d}","repaired_case":f"ADV-L{n:02d}"})
    for n in (1,3,5):pairs.append({"pair_id":f"DEV-H{(n+1)//2:02d}","origin":"DEV-history",
        "vulnerable_case":f"DEV-H{n:02d}","repaired_case":f"DEV-H{n+1:02d}"})
    for row in gate:pairs.append({"pair_id":"GATE-"+row["row"].zfill(2),"origin":"public-report",
        "vulnerable_case":"GATE-"+row["row"].zfill(2),"repaired_case":"GATE-"+row["row"].zfill(2),
        "revision_sides":["vulnerable","repaired"]})
    jwrite(OUT / "manifest.json", {"schema":"bindcheck-benchmark.manifest/v1",
           "source_revision":home_rev,"cases":manifest,"pairs":pairs,
           "note":"Case labels and scoring are frozen before E1 benchmark runs; public cards with blank reviewer fields remain PENDING."})

if __name__ == "__main__":
    main()
