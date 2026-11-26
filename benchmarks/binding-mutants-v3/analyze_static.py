"""Apply the frozen B3 MATCHING.md (B2 static rule + B3 sections 2-5) to static-tool outputs.

Usage:
  python3 analyze_static.py --static results/raw/B3/static-1 \
      --mythril-json results/raw/B3/static-1/mythril --mythril-log results/raw/B3/static-1-mythril-diag/mythril \
      --out results/raw/B3/static-1/analysis [--arm-label frozen]

--mythril-json: where the scored Mythril JSON comes from (missing targets fall back to --mythril-log's JSON).
--mythril-log : a run with identical analysis flags plus `-v 4`, used only to read creation status and coverage.
                A run whose log says "No contract was created" analysed nothing: it is UNSUPPORTED (analysis
                failure), never a miss and never "0 findings".
Writes matches.tsv, summary.tsv, targets.tsv, false-alarms.tsv, other-new.tsv into --out (raw, ignored dir).
Ported from benchmarks/binding-mutants-v2/analyze_static.py; differences are listed in RESULTS-static.md.
"""
import argparse, collections, difflib, importlib.util, json, math, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent.parent; R = ROOT / "results/raw/B3"
spec = importlib.util.spec_from_file_location("mm", HERE / "make_mutants.py"); mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
M = {m["id"]: m for m in mm.M}
HOSTS = ["zkerc20", "dark", "davinci", "kakushi", "xchain"]

# ---- MATCHING.md section 4: B2 mechanism lists, copied unchanged ----
STRICT = {
    "slither": {"P1": {"arbitrary-send-eth", "arbitrary-send-erc20"}, "P2": {"unused-return", "missing-zero-check"}, "P3": set(),
                "P4": {"unused-return", "unchecked-lowlevel", "unprotected-upgrade"}, "P5": set()},
    "mythril": {"P1": {"SWC-105"}, "P2": set(), "P3": set(), "P4": {"SWC-104", "SWC-105"}, "P5": set()},
    # B2: P2 = "warnings on signal assignment `<--`, unused signals/outputs"; P3 none; P1/P4/P5 n/a
    "circomspect": {"P1": set(), "P2": {"CS-ASSIGN", "CS-UNUSED"}, "P3": set(), "P4": set(), "P5": set()},
    "nargo": {p: set() for p in ("P1", "P2", "P3", "P4", "P5")},  # no list: loose only
}
BINDING = {t: set().union(*v.values()) for t, v in STRICT.items()}  # section 5 "binding warning"

# ---- MATCHING.md section 2: extra accepted locations (file basename, function) ----
EXTRA_LOC = {
    "ZK-S02": [("TransactionKeeper.sol", "_checkProof")], "ZK-S03": [("TransactionKeeper.sol", "_checkProof")],
    "DK-S01": [("DarkVault.sol", "withdraw")], "DV-S05": [("CouncilManager.sol", "deal")],
    "XC-S04": [("Connector.sol", "_verifyProof")],
    "XC-S07": [("Connector.sol", "_checkRouteImageId"), ("Connector.sol", "_verifyProof")],
    "XC-S05": [("Connector.sol", "_submitLockProofImpl")],
    "XC-S03": [("Connector.sol", "_submitLockProofImpl"), ("Connector.sol", "submitAckProof")],
}

# ---- MATCHING.md section 3: targets per tool (TID = ID or ID@part) ----
def sol_parts(tool, mid):
    """Analysis parts for a Solidity-supported id -> list of (part, primary?)."""
    h = M[mid]["host"] if mid in M else mid.split("-", 1)[1]
    edited = {os.path.basename(f) for f, *_ in mm.edits(M[mid])} if mid in M else set()
    if tool == "slither":
        if h == "dark": return [("", "DarkVault.sol" in edited or not edited), ("verifier", "Verifier.sol" in edited)]
        return [("", True)]
    if h == "dark": return [("", "DarkVault.sol" in edited or not edited), ("verifier", "Verifier.sol" in edited)]
    if h == "davinci": return [("", "DealVerifier.sol" not in edited), ("dealverifier", "DealVerifier.sol" in edited)]
    if h == "xchain": return [("", "Connector.sol" in edited or not edited), ("adapter", "RiscZeroAdapter.sol" in edited)]
    return [("", True)]

def supported(tool, mid):
    m = M[mid]
    if tool in ("slither", "mythril"): return m["side"] == "S"
    if tool == "circomspect": return m["side"] == "C" and m["host"] in ("zkerc20", "davinci")
    if tool == "nargo": return m["side"] == "C" and m["host"] in ("dark", "kakushi")
    return False

def tree(mid):
    h = M[mid]["host"] if mid in M else mid.split("-", 1)[1]
    if mid == "CLEAN-kakushi": return R / "run-0-clean-c/trees" / mid
    if mid.startswith("CLEAN-"): return R / "run-0-clean-b/trees" / mid
    if mid == "XC-S07": return R / "run-1-xchain-s07/trees" / mid
    return R / f"run-1-{h}/trees" / mid

# ---- readers: return (status, warnings) ; status in ok / unsupported:<why> / unknown:<why> ----
def fn_of(e):
    if e["type"] == "function": return e["name"]
    p = e.get("type_specific_fields", {}).get("parent", {})
    while p:
        if p.get("type") == "function": return p["name"]
        p = p.get("type_specific_fields", {}).get("parent", {})
    return ""

def read_slither(st, tid):
    f = st / "slither" / f"{tid}.json"
    if not f.exists(): return ("unsupported:crash-no-json" if f.with_suffix(".meta").exists() else "unsupported:no-output"), set()
    d = json.loads(f.read_text())
    if not d.get("success"): return "unsupported:slither-error", set()
    out = set()
    for r in d["results"].get("detectors", []):
        locs = {(os.path.basename(e.get("source_mapping", {}).get("filename_relative", "")).lower(), fn_of(e)) for e in r.get("elements", [])} or {("", "")}
        for fl, fu in locs: out.add((r["check"], fl, fu))
    return "ok", out

def mythril_diag(logdir, tid):
    f = logdir / f"{tid}.log"
    if not f.exists(): return None
    t = f.read_text(errors="replace")
    cov = [float(x) for x in re.findall(r"Achieved ([0-9.]+)% coverage", t)]
    st = re.search(r"Finished contract creation, found (\d+) open states", t)
    its = re.findall(r"Starting message call transaction, iteration: (\d+)", t)
    return {"created": "No contract was created" not in t and bool(st and int(st.group(1)) > 0), "coverage": cov,
            "open_states": int(st.group(1)) if st else 0, "iterations": len(its),
            "exec_timeout_hit": bool(re.search(r"execution timeout|Execution timeout", t, re.I))}

def read_mythril(jdir, logdir, tid):
    meta = None
    for d in (jdir, logdir):
        if (d / f"{tid}.json").exists(): jf = d / f"{tid}.json"; meta = d / f"{tid}.meta"; break
    else: return "unsupported:no-output", set(), None
    diag = mythril_diag(logdir, tid)
    ec = int(re.search(r"exit=(\d+)", meta.read_text()).group(1)) if meta.exists() else -1
    try: d = json.loads(jf.read_text() or "{}")
    except Exception: d = {}
    issues = {("SWC-" + str(i.get("swc-id", "")).replace("SWC-", ""), os.path.basename(i.get("filename") or "").lower(),
               (i.get("function") or "").split("(")[0]) for i in d.get("issues", [])}
    if ec == 124 and not issues: return "unknown:timeout", issues, diag
    if not d.get("success"): return "unsupported:mythril-error", issues, diag
    if diag is None: return "unsupported:creation-status-unverified", issues, diag
    if not diag["created"]: return "unsupported:no-contract-created", issues, diag
    return "ok", issues, diag

CS_RE = re.compile(r"^warning: (.*)\n\s+┌─ (\S+?):(\d+):\d+", re.M)
def cs_kind(msg):
    if "<--" in msg or "signal assignment" in msg.lower(): return "CS-ASSIGN"
    if re.search(r"(is|are) not used|not constrained in|never read|unused", msg): return "CS-UNUSED"
    return "CS-OTHER:" + re.sub(r"`[^`]*`", "`_`", msg)[:70]

def read_circuit(st, tool, tid):
    f = st / tool / f"{tid}.log"
    if not f.exists(): return "unsupported:no-output", []
    t = f.read_text(errors="replace")
    if tool == "circomspect":
        if not re.search(r"circomspect: (\d+|No) issues? found", t): return "unsupported:circomspect-error", []
        return "ok", [(cs_kind(m.group(1)), os.path.basename(m.group(2)), int(m.group(3)), m.group(1)) for m in CS_RE.finditer(t)]
    if re.search(r"^error", t, re.M): return "unsupported:nargo-error", []
    ws = []
    for m in re.finditer(r"^(warning|error): (.*)\n\s+┌─ (\S+?):(\d+):\d+", t, re.M):
        ws.append(("NARGO-" + m.group(1), m.group(3), int(m.group(4)), m.group(2)))
    return "ok", ws

def line_maps(mid):
    """Per edited file (path relative to host root): (edited lines in mutant coords, map mutant line -> baseline line)."""
    res = {}
    for fn, *_ in mm.edits(M[mid]):
        a = (HERE / "baselines" / M[mid]["host"] / fn).read_text().splitlines(); b = (tree(mid) / fn).read_text().splitlines()
        ed, mp = set(), {}
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == "equal":
                for k in range(j2 - j1): mp[j1 + k + 1] = i1 + k + 1
            else:
                ed |= set(range(j1 + 1, j2 + 1)) or {max(j1, 1), j1 + 1}  # deletion: lines around the deletion point
                for k in range(j1, j2): mp[k + 1] = i1 + 1
        res[fn] = (ed, mp)
    return res

def path_matches(warn_file, fn):  # circomspect gives absolute paths, nargo package-relative ones
    return warn_file.endswith(fn) or fn.endswith(warn_file) or os.path.basename(warn_file) == os.path.basename(fn)

def wilson(k, n):
    if n == 0: return "-"
    z = 1.96; p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return f"{max(0.0, (c - h) / d):.2f}-{min(1.0, (c + h) / d):.2f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", required=True); ap.add_argument("--mythril-json", required=True); ap.add_argument("--mythril-log", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--arm-label", default="frozen")
    ap.add_argument("--tools", default="slither,mythril,circomspect,picus,nargo")
    a = ap.parse_args()
    st = Path(a.static); jdir = Path(a.mythril_json); ldir = Path(a.mythril_log); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tools = a.tools.split(",")
    rows, trows, other, fa = [], [], [], []
    cache = {}

    def sol(tool, tid):
        if (tool, tid) not in cache:
            if tool == "slither": s, w = read_slither(st, tid); dg = None
            else: s, w, dg = read_mythril(jdir, ldir, tid)
            cache[(tool, tid)] = (s, w, dg)
            cov = "/".join(f"{c:.2f}" for c in dg["coverage"]) if dg else "-"
            if s != "unsupported:no-output": trows.append((a.arm_label, tool, tid, s, len(w), "-" if not dg else ("yes" if dg["created"] else "NO"),
                          "-" if not dg else dg["open_states"], "-" if not dg else dg["iterations"], cov))
        return cache[(tool, tid)]

    def sol_new(tool, mid):
        """Union of new warnings over the analysis parts; status from the primary (edited-file) part."""
        h = M[mid]["host"]; clean = f"CLEAN-{h}"; new, status = set(), "ok"
        for part, primary in sol_parts(tool, mid):
            sfx = f"@{part}" if part else ""
            ms, mw, _ = sol(tool, mid + sfx); cs, cw, _ = sol(tool, clean + sfx)
            if ms != "ok" or cs != "ok":
                if primary: status = ms if ms != "ok" else "clean-" + cs
                continue
            new |= {w for w in mw if not any(c[0] == w[0] and c[1] == w[1] and c[2] == w[2] for c in cw)}
        return status, new

    def circ_new(tool, mid):
        h = M[mid]["host"]; ms, mw = read_circuit(st, tool, mid); cs, cw = read_circuit(st, tool, f"CLEAN-{h}")
        if ms != "ok": return ms, [], {}
        if cs != "ok": return "clean-" + cs, [], {}
        maps = line_maps(mid) if mid in M else {}
        new = []
        for w in mw:
            fn = next((f for f in maps if path_matches(w[1], f)), None)
            bl = maps[fn][1].get(w[2], w[2]) if fn else w[2]
            if not any(c[0] == w[0] and os.path.basename(c[1]) == os.path.basename(w[1]) and abs(c[2] - bl) <= 3 for c in cw):
                new.append(w)
        return "ok", new, maps

    for tool in tools:
        for mid, m in M.items():
            if m["kind"] != "mutant": continue
            pat = m["pattern"]
            if tool == "picus":
                r = "unsupported:no-racket-runtime" if (m["side"] == "C" and m["host"] in ("zkerc20", "davinci")) else "unsupported-layer"
                rows.append((tool, mid, pat, r, 0, 0, 0, "-")); continue
            if not supported(tool, mid): rows.append((tool, mid, pat, "unsupported-layer", 0, 0, 0, "-")); continue
            if tool in ("slither", "mythril"):
                s, new = sol_new(tool, mid)
                if s != "ok": rows.append((tool, mid, pat, s if s.startswith(("unknown", "unsupported")) else "unsupported:" + s, 0, 0, 0, "-")); continue
                locs = {(m["gt_file"].lower(), m["gt_function"])} | {(f.lower(), fu) for f, fu in EXTRA_LOC.get(mid, [])}
                loose = [w for w in new if (w[1], w[2]) in locs]
                strict = [w for w in loose if w[0] in STRICT[tool][pat]]
                mech = [w for w in new if w[0] in STRICT[tool][pat]]
            else:
                s, new, maps = circ_new(tool, mid)
                if s != "ok": rows.append((tool, mid, pat, s if s.startswith("unsupported") else "unsupported:" + s, 0, 0, 0, "-")); continue
                loose = [w for w in new if any(path_matches(w[1], f) and any(abs(w[2] - e) <= 3 for e in maps[f][0]) for f in maps)]
                strict = [w for w in loose if w[0] in STRICT[tool][pat]]
                mech = [w for w in new if w[0] in STRICT[tool][pat]]
            res = "strict" if strict else "loose" if loose else "none"
            rows.append((tool, mid, pat, res, len(new), len(loose), len(new) - len(loose), "yes" if mech else "no"))
            for w in new:
                if w not in loose: other.append((tool, mid, *map(str, w[:3])))
        # section 5: clean hosts (absolute) and decoys (delta)
        for h in HOSTS:
            cid = f"CLEAN-{h}"
            if tool in ("slither", "mythril"):
                ws, stt = set(), []
                for part, _ in sol_parts(tool, cid):
                    s, w, _ = sol(tool, cid + (f"@{part}" if part else "")); stt.append(s)
                    if s == "ok": ws |= w
                if not any(x == "ok" for x in stt): fa.append((tool, cid, "clean", ";".join(stt), "-", "")); continue
                b = sorted(w for w in ws if w[0] in BINDING[tool])
            elif tool in ("circomspect", "nargo"):
                if (tool == "circomspect") != (h in ("zkerc20", "davinci")) or h == "xchain": continue
                s, w = read_circuit(st, tool, cid)
                if s != "ok": fa.append((tool, cid, "clean", s, "-", "")); continue
                b = [x for x in w if x[0] in BINDING[tool]]; stt = ["ok"]
            else: continue
            fa.append((tool, cid, "clean", ";".join(stt), len(b), "; ".join("|".join(map(str, x[:3])) for x in b)))
        for did, m in M.items():
            if m["kind"] != "decoy": continue
            ok = (tool in ("slither", "mythril") and m["side"] == "S") or (tool == "circomspect" and did == "DV-D01") or (tool == "nargo" and did == "KK-D01")
            if not ok: fa.append((tool, did, "decoy", "unsupported-layer", "-", "")); continue
            if tool in ("slither", "mythril"): s, new = sol_new(tool, did)
            else: s, new, _ = circ_new(tool, did)
            if s != "ok": fa.append((tool, did, "decoy", s, "-", "")); continue
            b = [w for w in new if w[0] in BINDING[tool]]
            fa.append((tool, did, "decoy", "ok", len(b), "; ".join("|".join(map(str, x[:3])) for x in b) + (f" (non-binding new: {len(new) - len(b)})" if len(new) - len(b) else "")))

    w = lambda name, hdr, rs: (out / name).write_text("\t".join(hdr) + "\n" + "".join("\t".join(map(str, r)) + "\n" for r in rs))
    w("matches.tsv", ["tool", "id", "pattern", "result", "new_warnings", "at_gt", "other_new", "mechanism_level"], rows)
    w("targets.tsv", ["arm", "tool", "target", "status", "n_warnings", "contract_created", "open_states_after_creation", "msg_call_iterations", "coverage_pct_per_bytecode"], sorted(set(trows)))
    w("other-new.tsv", ["tool", "id", "detector", "file", "function_or_line"], other)
    w("false-alarms.tsv", ["tool", "target", "kind", "status", "binding_warnings", "detail"], fa)
    agg = collections.defaultdict(collections.Counter)
    for tool, mid, pat, res, *_r in rows:
        c = agg[(tool, pat)]
        if res.startswith("unsupported"): c["unsupported"] += 1
        elif res.startswith("unknown"): c["unknown"] += 1
        else:
            c["supported"] += 1; c["loose"] += res in ("loose", "strict"); c["strict"] += res == "strict"; c["mech"] += _r[-1] == "yes"
    lines = ["tool\tpattern\tsupported\tloose\tstrict\tmechanism\tunknown\tunsupported\tloose_wilson95"]
    for (tool, pat), c in sorted(agg.items()):
        lines.append(f"{tool}\t{pat}\t{c['supported']}\t{c['loose']}\t{c['strict']}\t{c['mech']}\t{c['unknown']}\t{c['unsupported']}\t{wilson(c['loose'], c['supported'])}")
    (out / "summary.tsv").write_text("\n".join(lines) + "\n"); print("\n".join(lines))

if __name__ == "__main__":
    main()
