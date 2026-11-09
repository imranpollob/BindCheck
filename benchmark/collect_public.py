#!/usr/bin/env python3
"""Normalize pinned public source runs while preserving PENDING labels."""
from __future__ import annotations

import argparse
import csv
import json
import pathlib

from collect import arm_obs, base, native_circuit
from collect_freeze2 import observation as bind_observation

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/bench/e1-public-20261109"
BENCH = ROOT / "benchmark"


def load(path):
    try:return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError):return None


def gate_binding(obs, eligible, status, protocol):
    if eligible:
        return obs
    obs["native_run_status"]=obs.get("run_status")
    obs["run_status"]="UNKNOWN"
    obs["verdict"]="UNKNOWN"
    obs["findings"]=[]
    obs["reason"]=f"TRIPLE_{status}_PROTOCOL_{protocol}"
    return obs


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=pathlib.Path,required=True)
    args=ap.parse_args()
    runs={}
    for path in (RAW/"runs-structural.json",RAW/"runs-email.json",RAW/"runs-self.json",
                 RAW/"runs-structural-zkfuzz.json"):
        data=load(path)
        if not data:continue
        for r in data["records"]:
            key=(r["id"],r["side"])
            if key not in runs:runs[key]=r
            else:runs[key]["commands"].update(r["commands"])
    observations=[]
    for row in csv.DictReader((ROOT/"gate/GATE-MANIFEST.csv").open()):
        cid=f"GATE-{row['row']}"
        case=load(BENCH/"cases"/cid/"case.json")
        manifest=load(BENCH/"public-triples"/cid/"manifest.json")
        for side in ("vulnerable","repaired"):
            record=runs.get((cid,side),{})
            commands=record.get("commands",{})
            revision=manifest["revisions"][side]
            buildability=revision.get("buildability",{}).get("status") or revision["status"]
            protocol=manifest.get("protocol_class","UNRESOLVED")
            eligible=buildability=="BUILD_OK" and protocol=="CIRCOM_GROTH16_SOURCE_LINKED_KEY_UNPROVEN"
            result_root=pathlib.Path(record.get("source_result_root") or RAW/cid/side)
            abc=result_root/"ABC"
            for tool in ("A","B","C"):
                name=f"{tool}-pinned"
                path=abc/f"{tool}.json"
                obs=arm_obs(name,cid,side,path)
                obs["buildability"]=buildability
                observations.append(gate_binding(obs,eligible,buildability,protocol))
            bind=result_root/"bindcheck.stdout"
            obs=bind_observation("BindCheck-F2",case,side,bind)
            obs["buildability"]=buildability
            observations.append(gate_binding(obs,eligible,buildability,protocol))
            slither=result_root/"slither.json"
            x=load(slither)
            retry2=RAW/cid/side/"slither-retry2.json"
            if (load(retry2) or {}).get("success"):
                slither=retry2
                x=load(retry2)
            retry=RAW/cid/side/"slither-retry.json"
            if not (x and x.get("success")) and (load(retry) or {}).get("success"):
                slither=retry
                x=load(retry)
            out=base("Slither-default-pinned",cid,side,"UNKNOWN",
                     "NO_BINDING_PROPERTY_INTERFACE" if x and x.get("success") else
                     "SLITHER_COMPILE_OR_SETUP_FAILED",slither)
            out["native_status"]="completed" if x and x.get("success") else "unavailable"
            out["buildability"]=buildability
            observations.append(out)
            for name,key in (("Circomspect-pinned","circomspect"),
                             ("Picus-pinned","picus"),("ZKAP-pinned","zkap")):
                out=native_circuit(name,cid,side,abc/"B.json",key)
                out["buildability"]=buildability
                observations.append(out)
            z=commands.get("zkFuzz",{})
            out=base("zkFuzz-pinned",cid,side,"UNKNOWN",
                     "CIRCUIT_ONLY_NO_INTEGRATION_VERDICT" if z.get("exit_status")==0 else
                     "TIMEOUT" if z.get("timed_out") else z.get("status","NATIVE_ERROR"),
                     result_root/"zkfuzz.stdout")
            out["native_status"]=("TIMEOUT" if z.get("timed_out") else
                                  "COMPLETED" if z.get("exit_status")==0 else
                                  z.get("status","ERROR"))
            out["buildability"]=buildability
            observations.append(out)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w") as file:
        for obs in observations:file.write(json.dumps(obs,sort_keys=True)+"\n")
    print(len(observations))


if __name__=="__main__":main()
