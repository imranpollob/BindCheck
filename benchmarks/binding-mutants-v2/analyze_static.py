"""Apply MATCHING.md to the raw static-tool outputs of a B2 run. Usage: analyze_static.py RUN_DIR"""
import json, re, sys, glob, os, math
from pathlib import Path
RUN = Path(sys.argv[1]); ST = RUN / "static"
HERE = Path(__file__).resolve().parent
src = (HERE / "make_mutants.py").read_text()
import importlib.util
spec = importlib.util.spec_from_file_location("mm", HERE / "make_mutants.py"); mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
M = mm.M
CLEAN = {"redpacket": "CLEAN-redpacket", "privacyvaults": "CLEAN-privacyvaults", "orc": "CLEAN-orc"}
def gt_func(m):
    c = m["consumer"]; f = c.split("::")[1].strip().split(" ")[0].split("(")[0] if "::" in c else ""
    return os.path.basename(c.split("::")[0].strip()), f
STRICT = {  # MATCHING.md mechanism lists
 "slither": {"P1": {"arbitrary-send-eth", "arbitrary-send-erc20"}, "P2": {"unused-return", "missing-zero-check"}, "P3": set(), "P4": {"unused-return", "unchecked-lowlevel", "unprotected-upgrade"}, "P5": set()},
 "mythril": {"P1": {"SWC-105"}, "P2": set(), "P3": set(), "P4": {"SWC-104", "SWC-105"}, "P5": set()},
}
def slither_warnings(id_):
    f = ST / "slither" / f"{id_}.json"
    if not f.exists(): return None
    try: d = json.loads(f.read_text())
    except Exception: return None
    if not d.get("success"): return None
    out = set()
    for r in d["results"].get("detectors", []):
        funcs = set(); files = set(); lines=set()
        for e in r.get("elements", []):
            sm = e.get("source_mapping", {}); fn = os.path.basename(sm.get("filename_relative", ""))
            files.add(fn); lines.update(sm.get("lines", []))
            if e["type"] == "function": funcs.add(e["name"])
            else:
                p = e.get("type_specific_fields", {}).get("parent", {})
                while p:
                    if p.get("type") == "function": funcs.add(p["name"]); break
                    p = p.get("type_specific_fields", {}).get("parent", {})
        for fn in files or {""}:
            for fu in funcs or {""}: out.add((r["check"], fn, fu))
    return out
def mythril_warnings(id_):
    f = ST / "mythril" / f"{id_}.json"
    if not f.exists(): return None
    d = json.loads(f.read_text())
    if not d.get("success"): return None
    return {(i["swc-id"] and "SWC-" + i["swc-id"].replace("SWC-", ""), os.path.basename(i.get("filename") or ""), (i.get("function") or "").split("(")[0]) for i in d["issues"]}
def edited_lines(id_, m):
    # lines (1-based) in mutant file that differ from baseline, for circuits
    res = {}
    for f, *_ in m["edits"]:
        a = (HERE / "baselines" / m["host"] / f).read_text().splitlines(); b = (RUN / "trees" / id_ / f).read_text().splitlines()
        ch = set(i + 1 for i in range(min(len(a), len(b))) if a[i] != b[i]) or {min(len(a), len(b))}
        res[os.path.basename(f)] = ch
    return res
def wilson(k, n):
    if n == 0: return "-"
    z = 1.96; p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return f"{(c-h)/d:.2f}-{(c+h)/d:.2f}"
rows = []
for tool, getw in (("slither", slither_warnings), ("mythril", mythril_warnings)):
    for id_, m in M.items():
        if m["layer"] != "consumer": rows.append((tool, id_, m["pattern"], "unsupported-layer", 0, 0, 0)); continue
        cw = getw(CLEAN[m["host"]]); mw = getw(id_)
        if mw is None or cw is None: rows.append((tool, id_, m["pattern"], "unsupported-run-failed", 0, 0, 0)); continue
        new = mw - cw
        gfile, gfunc = gt_func(m)
        edit_files = {os.path.basename(f) for f, *_ in m["edits"]}
        loose = [w for w in new if w[1] in edit_files | {gfile} and (w[2] == gfunc or (gfile == "Verifier.sol" and w[2] in ("verify", "open")) or (m["host"] == "redpacket" and w[1] == "Verifier.sol" and w[2] in ("verify", "open")))]
        strict = [w for w in loose if w[0] in STRICT[tool][m["pattern"]]]
        rows.append((tool, id_, m["pattern"], "strict" if strict else "loose" if loose else "none", len(new), len(loose), len(new) - len(loose)))
# circuits
def cs_warn(id_):
    f = ST / "circomspect" / f"{id_}.log"
    if not f.exists(): return None
    t = f.read_text(); return [(m.group(1), int(m.group(2))) for m in re.finditer(r"warning: (.*)\n\s+┌─ .*passcode\.circom:(\d+):", t)]
def picus_verdict(id_):
    f = ST / "picus" / f"{id_}.log"
    if not f.exists(): return None
    t = f.read_text()
    return "safe" if "properly constrained" in t and "Cannot" not in t else "unknown" if "Cannot determine" in t else "unsafe" if "not uniquely" in t or "under-constrained" in t.lower() or "counterexample" in t.lower() else "other"
cw = cs_warn("CLEAN-redpacket"); mw = cs_warn("RP-C01"); ed = edited_lines("RP-C01", M["RP-C01"])["passcode.circom"]
new = [w for w in (mw or []) if w not in (cw or [])]; near = [w for w in new if any(abs(w[1] - e) <= 3 for e in ed)]
rows.append(("circomspect", "RP-C01", "P2", "strict" if any("signal assignment" in w[0] or "never read" in w[0] for w in near) else "loose" if near else "none", len(new), len(near), len(new) - len(near)))
pc, pm = picus_verdict("CLEAN-redpacket"), picus_verdict("RP-C01")
rows.append(("picus", "RP-C01", "P2", "strict" if pc == "safe" and pm in ("unsafe",) else "unknown" if pc == "safe" and pm == "unknown" else "none", 0, 0, 0))
# nargo check: diagnostics at edited lines
def nargo_diag(id_):
    f = ST / "nargo" / f"{id_}.log"
    return f.read_text() if f.exists() else None
for id_ in ("PV-C01", "PV-C02", "PV-C03"):
    m = M[id_]; t = nargo_diag(id_); ct = nargo_diag("CLEAN-privacyvaults")
    ed = edited_lines(id_, m); f = list(ed)[0]; lines = ed[f]
    hits = [int(x) for x in re.findall(rf"src/{re.escape(f)}:(\d+):", t)]
    chits = [int(x) for x in re.findall(rf"src/{re.escape(f)}:(\d+):", ct)]
    near = [h for h in hits if any(abs(h - e) <= 3 for e in lines)]
    cnear = [h for h in chits if any(abs(h - e) <= 3 for e in lines)]
    rows.append(("nargo-check", id_, m["pattern"], "loose" if near and not cnear else "none", len(hits), len(near), 0))
out = ["tool\tid\tpattern\tresult\tnew_warnings\tat_gt\tother_new"] + ["\t".join(map(str, r)) for r in rows]
(ST / "matches.tsv").write_text("\n".join(out) + "\n")
# summary per tool x pattern
import collections
agg = collections.defaultdict(lambda: collections.Counter())
for tool, id_, pat, res, *_ in rows:
    key = (tool, pat)
    if res.startswith("unsupported"): agg[key]["unsupported"] += 1
    elif res == "unknown": agg[key]["unknown"] += 1; agg[key]["supported"] += 1
    else:
        agg[key]["supported"] += 1
        if res in ("loose", "strict"): agg[key]["loose"] += 1
        if res == "strict": agg[key]["strict"] += 1
lines = ["tool\tpattern\tsupported\tloose\tstrict\tunknown\tunsupported\tloose_wilson95"]
for (tool, pat), c in sorted(agg.items()):
    lines.append(f"{tool}\t{pat}\t{c['supported']}\t{c['loose']}\t{c['strict']}\t{c['unknown']}\t{c['unsupported']}\t{wilson(c['loose'], c['supported'])}")
(ST / "summary.tsv").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
