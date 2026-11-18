#!/usr/bin/env python3
"""R2 census helper. Stdlib only.

  r2tool.py audit  KEY|protocol|auditor|date|report_url|repo|holdout|retrieved_utc|sha256|tvl_usd|tvl_source|notes
  r2tool.py add    (stdin lines) KEY|local_id|sev|class|mechanism|fixed|needs_circuit|reason|contract_only|page
  r2tool.py out    KEY|class-or-OUT-count|n_out      (records pure under-constraint OUT findings as counts only)
  r2tool.py stats  prints tables used in REPORT.md
"""
import csv, sys, pathlib, collections
D = pathlib.Path(__file__).resolve().parent
AUD = D / "audits_read.csv"
FND = D / "findings.csv"
AF = ["report_key","protocol","auditor_or_platform","report_date","report_url","protocol_repo","holdout_flag",
      "retrieved_utc","sha256","protocol_tvl_usd_at_report","tvl_source","findings_reviewed","included","out_count","notes"]
FF = ["finding_id","protocol","auditor_or_platform","report_date","severity","class","mechanism_one_line","fixed",
      "needs_circuit_to_detect","needs_circuit_reason","contract_only_tool_could_flag","protocol_tvl_usd_at_report",
      "tvl_source","finding_url","report_url","retrieved_utc","holdout_flag","label_source"]
SEV = {"C","H","M","L","I","UNKNOWN"}; CLS = {"P1","P2","P3","P4","P5"}; YN = {"yes","no","unclear"}

def load(p, f):
    if not p.exists(): return []
    with p.open(newline="") as h: return list(csv.DictReader(h))

def save(p, f, rows):
    with p.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=f, lineterminator="\n"); w.writeheader(); w.writerows(rows)

def main():
    cmd = sys.argv[1]
    A = load(AUD, AF); F = load(FND, FF); idx = {a["report_key"]: a for a in A}
    if cmd == "audit":
        v = sys.argv[2].split("|"); assert len(v) == 12, v
        row = dict(zip(["report_key","protocol","auditor_or_platform","report_date","report_url","protocol_repo",
            "holdout_flag","retrieved_utc","sha256","protocol_tvl_usd_at_report","tvl_source","notes"], v))
        old = idx.get(v[0], {}); row.update({k: old.get(k, "0") for k in ("findings_reviewed","included","out_count")})
        A = [a for a in A if a["report_key"] != v[0]] + [row]; save(AUD, AF, A)
    elif cmd == "add":
        for line in sys.stdin:
            line = line.strip()
            if not line or line.startswith("#"): continue
            v = line.split("|"); assert len(v) == 10, (len(v), line)
            key, lid, sev, cls, mech, fixed, nc, reason, co, page = v
            a = idx[key]; assert sev in SEV and cls in CLS and nc in YN and co in YN and fixed in {"yes","no","unknown"}, line
            fid = f"R2-{key}-{lid}"
            F = [x for x in F if x["finding_id"] != fid]
            url = a["report_url"] + (f"#page={page}" if page and page.isdigit() else (page if page.startswith("http") else ""))
            F.append(dict(finding_id=fid, protocol=a["protocol"], auditor_or_platform=a["auditor_or_platform"],
                report_date=a["report_date"], severity=sev, **{"class": cls}, mechanism_one_line=mech, fixed=fixed,
                needs_circuit_to_detect=nc, needs_circuit_reason=reason, contract_only_tool_could_flag=co,
                protocol_tvl_usd_at_report=a["protocol_tvl_usd_at_report"], tvl_source=a["tvl_source"],
                finding_url=url or a["report_url"], report_url=a["report_url"], retrieved_utc=a["retrieved_utc"],
                holdout_flag=a["holdout_flag"], label_source="AI"))
        save(FND, FF, F); sync(A, F)
    elif cmd == "reviewed":   # KEY n_reviewed n_out
        key, n, o = sys.argv[2:5]; idx[key]["findings_reviewed"] = n; idx[key]["out_count"] = o; save(AUD, AF, A); sync(A, F)
    elif cmd == "tvl":       # KEY usd source  (propagates to findings)
        key, usd, src = sys.argv[2:5]; idx[key]["protocol_tvl_usd_at_report"] = usd; idx[key]["tvl_source"] = src
        for x in F:
            if key_of(x["finding_id"], list(idx)) == key: x["protocol_tvl_usd_at_report"] = usd; x["tvl_source"] = src
        save(AUD, AF, A); save(FND, FF, F)
    elif cmd == "stats": stats(A, F)

def key_of(fid, keys):
    m = [k for k in keys if fid.startswith(f"R2-{k}-")]
    assert m, fid
    return max(m, key=len)

def sync(A, F):
    keys = [a["report_key"] for a in A]
    c = collections.Counter(key_of(x["finding_id"], keys) for x in F)
    for a in A: a["included"] = str(c.get(a["report_key"], 0))
    save(AUD, AF, A)

def stats(A, F):
    n = len(F); P = lambda k: f"{k} ({100*k/n:.1f}%)" if n else "0"
    print(f"audits read: {len(A)}; protocols: {len({a['protocol'] for a in A})}; findings included: {n}; "
          f"OUT (pure under-constraint, count only): {sum(int(a['out_count']) for a in A)}")
    sev = ["C","H","M","L","I","UNKNOWN"]
    print("| class | " + " | ".join(sev) + " | total |\n|---|" + "---:|"*(len(sev)+1))
    for c in ["P1","P2","P3","P4","P5"]:
        r = [sum(1 for x in F if x["class"]==c and x["severity"]==s) for s in sev]
        print(f"| {c} | " + " | ".join(map(str,r)) + f" | {sum(r)} |")
    r = [sum(1 for x in F if x["severity"]==s) for s in sev]; print("| total | " + " | ".join(map(str,r)) + f" | {n} |")
    for col in ["needs_circuit_to_detect","contract_only_tool_could_flag","fixed"]:
        cc = collections.Counter(x[col] for x in F); print(col, {k: P(v) for k, v in sorted(cc.items())})
    hc = [x for x in F if x["severity"] in ("C","H")]
    print("H/C:", len(hc), "binding P1-P3,P5 H/C:", sum(1 for x in hc if x["class"]!="P4"))
    for c in ["P1","P2","P3","P4","P5"]:
        s = [x for x in F if x["class"]==c]
        if s: print(c, "needs_circuit=yes:", sum(x["needs_circuit_to_detect"]=="yes" for x in s), "/", len(s),
                    "contract_only=yes:", sum(x["contract_only_tool_could_flag"]=="yes" for x in s))
    print("audits with >=1 included finding:", sum(1 for a in A if int(a["included"])>0),
          "audits with >=1 H/C binding finding:", len({key_of(x["finding_id"], [a["report_key"] for a in A]) for x in hc}))

if __name__ == "__main__": main()
