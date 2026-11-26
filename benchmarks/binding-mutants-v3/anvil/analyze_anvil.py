"""Score the post-hoc Mythril Anvil arm (NOT pre-registered). Usage: analyze_anvil.py RUN_DIR

Fixed before reading any mutant result (2026-11-25):
  * Warning key: (part, SWC id, entry-point function signature). Address-mode issues have no source file,
    and the PC is not stable across bytecode edits, so neither is used.
  * Clean reference = union of the two clean runs (CLEAN-<host> and CLEAN-<host>#2). Run-to-run noise is
    reported as the symmetric difference of the two clean runs.
  * New warning = mutant key absent from the clean reference (B2 delta rule, address-mode form).
  * Mechanism-level = some new warning whose SWC is on the frozen B2 Mythril list for the mutant's pattern
    (P1: SWC-105; P4: SWC-104, SWC-105; P2/P3/P5: none).
  * Loose/strict are NOT COMPUTABLE: GT functions are often internal and address mode has no source map.
  * Run status: ok when JSON success and >=1 message-call iteration; exit 124 with no issue = UNKNOWN;
    deploy failure or Mythril error = unsupported. A mutant is scored on the parts that hold its edited file.
"""
import collections, json, math, pathlib, re, sys
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import run_mythril
import importlib.util
spec = importlib.util.spec_from_file_location("mm", HERE.parent / "make_mutants.py"); mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
M = {m["id"]: m for m in mm.M}
LIST = {"P1": {"SWC-105"}, "P2": set(), "P3": set(), "P4": {"SWC-104", "SWC-105"}, "P5": set()}
BIND = {"SWC-104", "SWC-105"}
D = pathlib.Path(sys.argv[1])

def run(name):
    meta = D / f"{name}.meta"
    if not meta.exists(): return "not-run", set(), {}
    mt = meta.read_text()
    if "DEPLOY-FAILED" in mt: return "unsupported:deploy-failed", set(), {}
    ec = int(re.search(r"exit=(\d+)", mt).group(1)); sec = int(re.search(r"seconds=(\d+)", mt).group(1))
    log = (D / f"{name}.log").read_text(errors="replace")
    info = {"seconds": sec, "exit": ec, "iterations": len(re.findall(r"Starting message call transaction, iteration", log)),
            "coverage": [float(x) for x in re.findall(r"Achieved ([0-9.]+)% coverage", log)]}
    try: d = json.loads((D / f"{name}.json").read_text() or "{}")
    except Exception: d = {}
    part = name.split("@")[1] if "@" in name else ""
    iss = {(part, "SWC-" + str(i.get("swc-id", "")).replace("SWC-", ""), i.get("function") or "") for i in d.get("issues", [])}
    if ec == 124 and not iss: return "unknown:timeout", iss, info
    if not d.get("success"): return "unsupported:mythril-error", iss, info
    if info["iterations"] == 0: return "unsupported:no-message-call", iss, info
    return "ok", iss, info

def nm(i, p): return f"{i}{'@' + p if p else ''}"

def wilson(k, n):
    if n == 0: return "-"
    z = 1.96; p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return f"{max(0, (c - h) / d):.2f}-{min(1, (c + h) / d):.2f}"

targets, rows, noise, fa = [], [], [], []
for tid, parts in run_mythril.PLAN.items():
    for p in parts:
        s, iss, info = run(nm(tid, p))
        targets.append((nm(tid, p), s, len(iss), info.get("seconds", "-"), info.get("iterations", "-"), "/".join(f"{c:.2f}" for c in info.get("coverage", [])) or "-"))
clean = {}
for h in ["zkerc20", "dark", "davinci", "kakushi", "xchain"]:
    for p in run_mythril.PLAN[f"CLEAN-{h}"]:
        a = run(nm(f"CLEAN-{h}", p)); b = run(nm(f"CLEAN-{h}#2", p))
        ok = [x for x in (a, b) if x[0] == "ok"]
        clean[(h, p)] = (set().union(*[x[1] for x in ok]) if ok else None)
        noise.append((h, p or "main", a[0], b[0], len(a[1]), len(b[1]), len(a[1] ^ b[1]) if len(ok) == 2 else "-"))
        if ok:
            bw = sorted(w for w in clean[(h, p)] if w[1] in BIND)
            fa.append((f"CLEAN-{h}", p or "main", "clean", len(bw), "; ".join(f"{w[1]} {w[2]}" for w in bw)))
for tid, parts in run_mythril.PLAN.items():
    if tid.startswith("CLEAN"): continue
    m = M[tid]; h = m["host"]; status = "ok"; new = set()
    for p in parts:
        s, iss, _ = run(nm(tid, p)); c = clean[(h, p)]
        if s != "ok": status = s; break
        if c is None: status = "unsupported:clean-failed"; break
        new |= iss - c
    if m["kind"] == "decoy":
        bw = sorted(w for w in new if w[1] in BIND)
        fa.append((tid, ",".join(p or "main" for p in parts), "decoy", len(bw) if status == "ok" else status,
                   "; ".join(f"{w[1]} {w[2]}" for w in bw) + (f" (non-binding new: {len(new) - len(bw)})" if status == "ok" and len(new) > len(bw) else "")))
        continue
    mech = [w for w in new if w[1] in LIST[m["pattern"]]]
    rows.append((tid, m["pattern"], ",".join(p or "main" for p in parts), status, len(new) if status == "ok" else "-",
                 ("yes" if mech else "no") if status == "ok" else "-", "; ".join(sorted(f"{w[0] or 'main'}:{w[1]} {w[2]}" for w in new)) if status == "ok" else ""))
out = D / "analysis"; out.mkdir(exist_ok=True)
w = lambda f, h, rs: (out / f).write_text("\t".join(h) + "\n" + "".join("\t".join(map(str, r)) + "\n" for r in rs))
w("targets.tsv", ["target", "status", "n_issues", "seconds", "msg_call_iterations", "coverage_pct"], targets)
w("mutants.tsv", ["id", "pattern", "parts", "status", "new_issues", "mechanism_level", "new_issue_list"], rows)
w("noise.tsv", ["host", "part", "run1", "run2", "issues_run1", "issues_run2", "symmetric_diff"], noise)
w("false-alarms.tsv", ["target", "parts", "kind", "binding_issues", "detail"], fa)
agg = collections.defaultdict(collections.Counter)
for tid, pat, _, s, n, mech, _ in rows:
    c = agg[pat]
    if s == "ok": c["supported"] += 1; c["mech"] += mech == "yes"; c["anynew"] += n > 0
    elif s.startswith("unknown"): c["unknown"] += 1
    else: c["unsupported"] += 1
lines = ["pattern\tsupported\tmechanism\tany_new_issue\tunknown\tunsupported\tmech_wilson95"]
for pat in sorted(agg): c = agg[pat]; lines.append(f"{pat}\t{c['supported']}\t{c['mech']}\t{c['anynew']}\t{c['unknown']}\t{c['unsupported']}\t{wilson(c['mech'], c['supported'])}")
(out / "summary.tsv").write_text("\n".join(lines) + "\n"); print("\n".join(lines))
