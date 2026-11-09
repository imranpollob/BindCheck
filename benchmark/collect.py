#!/usr/bin/env python3
"""Normalize native outputs without upgrading unsupported results to decisions."""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
BENCH=ROOT/"benchmark"

def read(path):
    try:return json.loads(path.read_text())
    except (OSError,json.JSONDecodeError):return None

def arm_obs(tool,case,side,path):
    x=read(path)
    if x is None:return base(tool,case,side,"UNKNOWN","RESULT_MISSING",path)
    return {**base(tool,case,side,x.get("run",{}).get("status","UNKNOWN"),x.get("run",{}).get("fatal_reason"),path),
            "verdict":x.get("result",{}).get("verdict","UNKNOWN"),
            "findings":x.get("result",{}).get("findings",[])}

def base(tool,case,side,status,reason,path):
    return {"tool":tool,"case_id":case,"side":side,"run_status":status,
            "verdict":"UNKNOWN","reason":reason,"findings":[],"source":str(path)}

def bind_obs(case,side,path,expected):
    x=read(path)
    if x is None:return base("BindCheck-F1",case,side,"UNKNOWN","RESULT_MISSING",path)
    if expected not in ("P1","P2","P3","P4","P5"):
        return base("BindCheck-F1",case,side,"UNKNOWN","PROPERTY_UNSUPPORTED",path)
    pattern=x.get("patterns",{}).get(expected,{})
    findings=[]
    for triple in x.get("triples",[]):
        f=triple.get("patterns",{}).get(expected)
        if f and f.get("verdict")=="VIOLATION":
            findings.append({"code":f.get("reason"),"pattern":expected,"location":f.get("location"),
                             "evidence_grade":f.get("evidence_grade","E1")})
    status=x.get("run",{}).get("status","UNKNOWN")
    return {**base("BindCheck-F1",case,side,status,x.get("run",{}).get("fatal_reason"),path),
            "verdict":pattern.get("verdict","UNKNOWN"),"findings":findings,
            "reason":pattern.get("reasons",[None])[0] if pattern.get("reasons") else None}

def native_circuit(tool,case,side,path,key):
    x=read(path)
    if x is None:return base(tool,case,side,"UNKNOWN","ARM_B_RESULT_MISSING",path)
    d=x.get("native",{}).get("tools",{}).get(key,{})
    reason=d.get("reason") or "CIRCUIT_ONLY_NO_INTEGRATION_VERDICT"
    status=d.get("status","UNKNOWN")
    out=base(tool,case,side,"UNKNOWN",reason,path)
    out["native_status"]=status
    out["native_invocations"]=len(d.get("invocations",[]))
    return out

def slither_obs(case,side,path,run):
    x=read(path)
    if not x or not x.get("success"):
        return base("Slither-default",case,side,"UNKNOWN",
                    "SLITHER_COMPILE_OR_SETUP_FAILED" if run else "RESULT_MISSING",path)
    out=base("Slither-default",case,side,"UNKNOWN","NO_BINDING_PROPERTY_INTERFACE",path)
    out["native_status"]="completed"
    out["native_warnings"]=len(x.get("results",{}).get("detectors",[]))
    out["native_checks"]=[d.get("check") for d in x.get("results",{}).get("detectors",[])]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--synthetic-abc",type=pathlib.Path,required=True)
    ap.add_argument("--synthetic-bindcheck",type=pathlib.Path,required=True)
    ap.add_argument("--local",type=pathlib.Path,required=True)
    ap.add_argument("--build",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    args=ap.parse_args()
    manifest=read(BENCH/"manifest.json")
    builds={(r["case_id"],r["side"]):r for r in read(args.build)["records"]}
    native={(r["id"],r["side"]):r for r in read(args.local/"runs.json")["records"]}
    observations=[]
    for item in manifest["cases"]:
        case=read(BENCH/item["case"]);cid=case["id"]
        for side in case["revisions"]:
            b=builds[cid,side]
            allowed=b["status"] in ("BUILD_OK","BUILD_OK_NON_GROTH16")
            n=native[cid,side]
            abc=(args.synthetic_abc/"cases"/cid) if case["origin"]=="synthetic" else (args.local/cid/side/"ABC")
            bind=(args.synthetic_bindcheck/"cases"/cid/"result.json") if case["origin"]=="synthetic" else (args.local/cid/side/"bindcheck-command"/"stdout")
            for tool in ("A","B","C"):
                path=abc/f"{tool}.json"
                observations.append(arm_obs(tool,cid,side,path) if allowed else base(tool,cid,side,"UNKNOWN",b["status"],path))
            observations.append(bind_obs(cid,side,bind,case["expected_pattern"]) if allowed else base("BindCheck-F1",cid,side,"UNKNOWN",b["status"],bind))
            slither=args.local/cid/side/"slither.json"
            observations.append(slither_obs(cid,side,slither,n["commands"].get("Slither-default")) if allowed else base("Slither-default",cid,side,"UNKNOWN",b["status"],slither))
            for name,key in (("Circomspect","circomspect"),("Picus","picus"),("ZKAP","zkap")):
                path=abc/"B.json"
                observations.append(native_circuit(name,cid,side,path,key) if allowed else base(name,cid,side,"UNKNOWN",b["status"],path))
            observations.append(base("zkFuzz",cid,side,"UNKNOWN","CIRCUIT_ONLY_NO_INTEGRATION_VERDICT",args.local))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w") as f:
        for obs in observations:f.write(json.dumps(obs,sort_keys=True)+"\n")
    print(len(observations))

if __name__=="__main__":main()
