#!/usr/bin/env python3
"""T22 prototype: spec-driven check of "every public message after the prefix derived from verified inner-proof
outputs is zero", on the compiler's ACIR (nargo --print-acir) with cvc5 (finite-field theory). No source patterns are used.

usage: t22_tailspec.py --acir X.acir.txt --abi X.json --spec spec.json [--timeout 300] [--smt-dir DIR]

Spec (JSON) -- every field is an ANALYST ASSUMPTION and is echoed as such:
  messages        ref of the public message array            e.g. "abi:messages" | "return:commitments"
  streams[]       {source: ref, active_if_nonzero?: ref}       inner-proof output words, in prefix order
  derivation      {mode:"walk", records:{kind:len,...}} | {mode:"nonzero"}
  recursion_public_inputs_start  (only for flat `inputs:` recursion lines, nargo beta.14)
  instance        free text (e.g. scale) copied into the report
ref syntax: abi:path | return:path | rec:CALL[LO:HI]   (path = a.b[3].c, arrays expand to all elements)
Verdicts: SATISFIED_AT_SCOPE | VIOLATED | UNKNOWN.
"""
import argparse, json, os, re, sys, time
P = 21888242871839275222246405745257275088548364400416034343698204186575808495617

# ------------------------------------------------------------------ ACIR text
class Unsupported(Exception): pass

def parse_expr(s):
    s = s.replace(" ", "")
    if not s: raise Unsupported("empty expr")
    terms = []
    for sign, body in re.findall(r"([+-]?)([^+-]+)", s):
        coef, ws = (-1 if sign == "-" else 1), []
        for f in body.split("*"):
            if re.fullmatch(r"\d+", f): coef *= int(f)
            elif re.fullmatch(r"w\d+", f): ws.append(int(f[1:]))
            else: raise Unsupported(f"expr factor {f!r} in {s!r}")
        terms.append((coef, ws))
    return terms

def expr_wits(e): return {w for _, ws in e for w in ws}

def expr_smt(e):
    parts = []
    for c, ws in e:
        c = c % P
        if c > P // 2: c -= P
        fs = [str(c) if c >= 0 else f"(- {-c})"] + [f"w{w}" for w in ws]
        parts.append(fs[0] if len(fs) == 1 else "(* " + " ".join(fs) + ")")
    return "(mod (+ " + " ".join(parts) + f") {P})" if len(parts) > 1 else f"(mod {parts[0]} {P})"

def split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "[": depth += 1
        if ch == "]": depth -= 1
        if ch == "," and depth == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

def lst(s):
    s = s.strip()
    assert s[0] == "[" and s[-1] == "]", s
    return [x for x in split_top(s[1:-1]) if x]

class Acir:
    def __init__(self, text):
        self.ops, self.public, self.calldata, self.returndata = [], [], {}, None
        self.recs, self.unmodeled = [], []
        self.nblocks = {}
        mode = None
        for raw in text.split("\n"):
            line = raw.split("//")[0].strip()
            if not line: continue
            if line.startswith("unconstrained func") or re.match(r"^func [1-9]", line): break
            if line.startswith("public parameters:"):
                self.public = [int(x[1:]) for x in lst(line.split(":", 1)[1])]; continue
            if line.startswith(("private parameters:", "return values:", "Compiled ACIR", "func 0")): continue
            if re.match(r"^\d+: ", line): continue
            self._op(line)

    def _op(self, line):
        if line.startswith("ASSERT "):
            l, r = line[7:].split(" = ", 1)
            self.ops.append(("assert", parse_expr(l) + [(-c, w) for c, w in parse_expr(r)])); return
        if line.startswith("BRILLIG CALL"):
            outs = re.search(r"outputs: (\[.*\])\s*$", line)
            self.ops.append(("brillig", [int(x) for x in re.findall(r"w(\d+)", outs.group(1))] if outs else [])); return
        if line.startswith("BLACKBOX::RANGE"):
            m = re.match(r"BLACKBOX::RANGE input: (.*?), bits: (\d+)", line)
            self.ops.append(("range", parse_expr(m.group(1)), int(m.group(2)))); return
        if line.startswith("BLACKBOX::RECURSIVE_AGGREGATION"):
            kv = {k: v for k, v in re.findall(r"(\w+): (\[[^\]]*\]|[^,\[]+)", line)}
            if "public_inputs" in kv:
                pi = [parse_expr(x) for x in lst(kv["public_inputs"])]
            else:
                allin = [parse_expr(x) for x in lst(kv["inputs"])]
                pi = ("flat", allin)
            self.recs.append(pi); return
        if line.startswith("BLACKBOX::"):
            name = line.split()[0]
            m = re.search(r"outputs?: (\[[^\]]*\]|w\d+)", line)
            outs = [int(x) for x in re.findall(r"w(\d+)", m.group(1))] if m else []
            self.unmodeled.append((name, outs)); self.ops.append(("blackbox", outs)); return
        m = re.match(r"INIT (?:(CALLDATA \d+|RETURNDATA) )?b(\d+) = (\[.*\])", line)
        if m:
            els = [parse_expr(x) for x in lst(m.group(3))]
            self.ops.append(("init", int(m.group(2)), els))
            if m.group(1) == "RETURNDATA": self.returndata = [e for e in els]
            elif m.group(1): self.calldata[int(m.group(1).split()[1])] = els
            return
        m = re.match(r"READ (w\d+) = b(\d+)\[(.*)\]$", line)
        if m: self.ops.append(("read", int(m.group(2)), parse_expr(m.group(1)), parse_expr(m.group(3)))); return
        m = re.match(r"WRITE b(\d+)\[(.*?)\] = (.*)$", line)
        if m: self.ops.append(("write", int(m.group(1)), parse_expr(m.group(2)), parse_expr(m.group(3)))); return
        raise Unsupported(f"opcode not supported: {line[:80]}")

# ------------------------------------------------------------------ ABI -> witnesses
def flatten(ty, wit, out):
    k = ty["kind"]
    if k in ("field", "integer", "boolean"): out.append(next(wit))
    elif k == "array":
        for _ in range(ty["length"]): flatten(ty["type"], wit, out)
    elif k == "string":
        for _ in range(ty["length"]): out.append(next(wit))
    elif k == "struct":
        for f in ty["fields"]: flatten(f["type"], wit, out)
    elif k == "tuple":
        for t in ty["fields"]: flatten(t, wit, out)
    else: raise Unsupported(f"abi kind {k}")

def leaves(ty, prefix, wit, table):
    """table[path] = list of witnesses for every struct/array node, arrays also indexed per element"""
    start = []
    k = ty["kind"]
    if k == "struct":
        for f in ty["fields"]:
            sub = leaves(f["type"], prefix + "." + f["name"], wit, table); start += sub
    elif k == "array":
        for i in range(ty["length"]):
            start += leaves(ty["type"], f"{prefix}[{i}]", wit, table)
    elif k == "tuple":
        for i, t in enumerate(ty["fields"]): start += leaves(t, f"{prefix}.{i}", wit, table)
    else:
        flatten(ty, wit, start)
    table[prefix] = start
    return start

def abi_tables(abi, acir):
    import itertools
    wit = itertools.count(0)
    t_in = {}
    for p in abi["parameters"]:
        leaves(p["type"], p["name"], wit, t_in)
    t_ret = {}
    rt = abi.get("return_type")
    if rt and acir.returndata is not None:
        # return value witnesses come from the RETURNDATA block (databus) in flattened order
        rw = iter([e for e in acir.returndata])
        leaves(rt["abi_type"], "return", rw, t_ret)
    return t_in, t_ret

# ------------------------------------------------------------------ refs
def resolve(ref, acir, t_in, t_ret, spec):
    """-> list of expressions (term lists)"""
    kind, rest = ref.split(":", 1)
    if kind in ("abi", "return"):
        tab = t_in if kind == "abi" else t_ret
        key = rest if kind == "abi" else "return" + ("." + rest if rest else "")
        if key not in tab: raise Unsupported(f"unknown ref {ref!r}")
        ws = tab[key]
        return [w if isinstance(w, list) else [(1, [w])] for w in ws]
    if kind == "rec":
        m = re.fullmatch(r"(\d+)\[(\d+):(\d+)\]", rest)
        c, lo, hi = int(m.group(1)), int(m.group(2)), int(m.group(3))
        r = acir.recs[c]
        if isinstance(r, tuple):
            st = spec.get("recursion_public_inputs_start")
            if st is None: raise Unsupported("flat recursion inputs need recursion_public_inputs_start")
            r = r[1][st:]
        return r[lo:hi]
    raise Unsupported(f"ref kind {kind}")

# ------------------------------------------------------------------ cvc5 finite-field encoding
SMT_DIR = None
PROBE_SECONDS = int(os.environ.get("T22_PROBE_SECONDS", "60"))

def prune_dangling(acir, keep):
    """Exact simplification: drop `ASSERT w = linear-in-others` when w occurs in no other constraint, is not in `keep`, and
    appears only as a stand-alone degree-1 term (always solvable for w). Iterates to a fixpoint. Returns surviving op indices."""
    live = set(range(len(acir.ops)))
    occ = {}
    def wits(op):
        k = op[0]
        if k in ("assert", "range"): return expr_wits(op[1])
        if k == "init": return set().union(*[expr_wits(e) for e in op[2]]) if op[2] else set()
        if k in ("read", "write"): return expr_wits(op[2]) | expr_wits(op[3])
        return set()
    for i in live:
        for w in wits(acir.ops[i]): occ.setdefault(w, set()).add(i)
    changed = True
    while changed:
        changed = False
        for i in sorted(live):
            op = acir.ops[i]
            if op[0] != "assert": continue
            for cf, ws in op[1]:
                if len(ws) == 1 and (cf % P) != 0:
                    w = ws[0]
                    if w in keep or len(occ.get(w, ())) != 1: continue
                    if sum(1 for _, ws2 in op[1] if w in ws2) != 1: continue
                    live.discard(i)
                    for x in wits(op): occ[x].discard(i)
                    changed = True
                    break
    return live

def cone(acir, seeds):
    """connected components over constraint opcodes (brillig/unmodeled blackbox outputs are free, not linked)"""
    parent = {}
    live = prune_dangling(acir, seeds)
    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    opw = []
    for oi, op in enumerate(acir.ops):
        k = op[0]
        if oi not in live: ws = set()
        elif k in ("assert", "range"): ws = expr_wits(op[1])
        elif k == "init": ws = set().union(*[expr_wits(e) for e in op[2]]) if op[2] else set()
        elif k in ("read", "write"): ws = expr_wits(op[2]) | expr_wits(op[3])
        else: ws = set()
        if k in ("init", "read", "write"): ws = ws | {("blk", op[1])}
        opw.append(ws); ws = list(ws)
        for a in ws: f(a)
        for a in ws[1:]: parent[f(a)] = f(ws[0])
    roots = {f(s) for s in seeds if s in parent}
    sel = [i for i, ws in enumerate(opw) if ws and f(next(iter(ws))) in roots]
    wits = set(seeds)
    for i in sel: wits |= {w for w in opw[i] if isinstance(w, int)}
    return sel, wits

CVC5 = os.environ.get("CVC5", "cvc5")

def _run_killable(cmd, script, seconds):
    import subprocess, signal
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, _ = pr.communicate(script, timeout=seconds)
        return out.strip()
    except subprocess.TimeoutExpired:
        os.killpg(pr.pid, signal.SIGKILL); pr.communicate()
        return "timeout"

class FF:
    """SMT-LIB string builder for QF_FF + Bool (cvc5 finite-field theory)"""
    def __init__(self, timeout_ms):
        self.timeout_ms = timeout_ms; self.lines = []; self.w = set(); self.n = 0
        self.zero, self.one = self.c(0), self.c(1); self.T, self.Fa = "true", "false"
    def c(self, v): return f"(as ff{v % P} F)"
    def var(self, w):
        if w not in self.w:
            self.w.add(w); self.lines.append(f"(declare-const w{w} F)")
        return f"w{w}"
    def fresh(self, name="t"):
        self.n += 1; nm = f"{name}{self.n}"; self.lines.append(f"(declare-const {nm} F)"); return nm
    def let(self, term):      # name a subterm to keep the script linear in size
        self.n += 1; nm = f"d{self.n}"; self.lines.append(f"(define-fun {nm} () F {term})"); return nm
    def add(self, xs):
        xs = list(xs)
        if not xs: return self.zero
        return xs[0] if len(xs) == 1 else self.let("(ff.add " + " ".join(xs) + ")")
    def mul(self, xs): return xs[0] if len(xs) == 1 else self.let("(ff.mul " + " ".join(xs) + ")")
    def expr(self, e):
        ts = []
        for cf, ws in e:
            fs = ([self.c(cf)] if (cf % P != 1 or not ws) else []) + [self.var(w) for w in ws]
            ts.append(self.mul(fs))
        return self.add(ts)
    def eq(self, a, b): return f"(= {a} {b})"
    def ne(self, a, b): return f"(not (= {a} {b}))"
    def ite(self, c, a, b): return self.let(f"(ite {c} {a} {b})")
    def AND(self, *xs): return xs[0] if len(xs) == 1 else "(and " + " ".join(xs) + ")"
    def OR(self, *xs): return xs[0] if len(xs) == 1 else "(or " + " ".join(xs) + ")"
    def NOT(self, x): return f"(not {x})"
    def sub(self, a, b): return self.add([a, self.mul([self.c(-1), b])])
    def A(self, t): self.lines.append(f"(assert {t})")
    def bits(self, x, n):
        if n >= 254: return
        bs = [self.fresh("rb") for _ in range(n)]
        for b in bs: self.A(self.eq(self.mul([b, self.sub(b, self.one)]), self.zero))
        self.A(self.eq(x, self.add([self.mul([self.c(2 ** i), b]) if i else b for i, b in enumerate(bs)])))
    def parse_vals(self, out):
        body = out.split("\n", 1)[1] if "\n" in out else ""
        return [int(v) if int(v) < P // 2 else int(v) - P for v in re.findall(r"\(as ff(\d+) \(_ FiniteField", body)]
    def solve(self, getv, path=None):
        head = [f"(set-logic QF_FF)", f"(set-option :produce-models true)", f"(define-sort F () (_ FiniteField {P}))"]
        script = "\n".join(head + self.lines + ["(check-sat)", "(get-value (" + " ".join(getv) + "))"]) + "\n"
        if path: open(path, "w").write(script)
        import subprocess
        t0 = time.time()
        out = _run_killable([CVC5, "--lang=smt2"], script, self.timeout_ms / 1000)
        st = out.split("\n")[0].strip() if out else "error"
        return (st if st in ("sat", "unsat") else "unknown"), out, time.time() - t0

class IntFF(FF):
    """same builder interface, QF_NIA over Int with explicit `mod P` (z3). Range checks become plain bounds."""
    def c(self, v): return str(v % P)
    def var(self, w):
        if w not in self.w:
            self.w.add(w); self.lines.append(f"(declare-const w{w} Int)(assert (and (>= w{w} 0) (< w{w} {P})))")
        return f"w{w}"
    def fresh(self, name="t"):
        self.n += 1; nm = f"{name}{self.n}"; self.lines.append(f"(declare-const {nm} Int)"); return nm
    def let(self, term):
        self.n += 1; nm = f"d{self.n}"; self.lines.append(f"(define-fun {nm} () Int {term})"); return nm
    def add(self, xs):
        xs = list(xs)
        if not xs: return "0"
        return xs[0] if len(xs) == 1 else self.let("(+ " + " ".join(xs) + ")")
    def mul(self, xs): return xs[0] if len(xs) == 1 else self.let("(* " + " ".join(xs) + ")")
    def sub(self, a, b): return self.let(f"(- {a} {b})")
    def expr(self, e):
        ts = []
        for cf, ws in e:
            cf %= P
            if cf > P // 2: cf -= P
            cs = str(cf) if cf >= 0 else f"(- {-cf})"
            ts.append(self.mul([cs] + [self.var(w) for w in ws]) if (ws or cf) else "0")
        return self.let(f"(mod (+ {' '.join(ts)}) {P})") if len(ts) > 1 else self.let(f"(mod {ts[0]} {P})")
    def bits(self, x, n): self.A(f"(< {x} {2 ** n})")
    def solve(self, getv, path=None):
        head = ["(set-logic QF_NIA)", "(set-option :produce-models true)"]
        script = "\n".join(head + self.lines + ["(check-sat)", ("(get-value (" + " ".join(getv) + "))") if getv else ""]) + "\n"
        if path: open(path, "w").write(script)
        import subprocess
        t0 = time.time()
        out = _run_killable(["z3", "-smt2", "/dev/stdin"], script, self.timeout_ms / 1000)
        st = out.split("\n")[0].strip() if out else "error"
        return (st if st in ("sat", "unsat") else "unknown"), out, time.time() - t0
    def parse_vals(self, out):
        body = out.split("\n", 1)[1] if "\n" in out else ""
        vals = []
        for m in re.finditer(r"\(\w+ (\(- (\d+)\)|(\d+))\)", body):
            v = -int(m.group(3)) if m.group(3) else int(m.group(4))
            vals.append(v if abs(v) < P // 2 else v - P)
        return vals

BACKEND = os.environ.get("T22_BACKEND", "cvc5")
if BACKEND not in ("cvc5", "z3"):
    raise ValueError(f"unsupported T22_BACKEND: {BACKEND}")

def norm_terms(e):
    """canonical form: dict {tuple(sorted wits): coef mod P}"""
    d = {}
    for cf, ws in e:
        k = tuple(sorted(ws)); d[k] = (d.get(k, 0) + cf) % P
    return {k: v for k, v in d.items() if v}

def find_lemmas(acir, sel):
    """Generic gadget lemmas (exact, not project-specific):
       BOOL    x - x*x = 0                      =>  x in {0,1}
       ISZERO  r + d*i - 1 = 0  and  d*r = 0   =>  r in {0,1}, r=1 <=> d=0     (i occurs in no other constraint)
    Returns (bools, iszero list [(r, d)], consumed op indices)."""
    occ = {}
    for i in sel:
        op = acir.ops[i]
        ws = expr_wits(op[1]) if op[0] in ("assert", "range") else set()
        if op[0] == "init": ws = set().union(*[expr_wits(e) for e in op[2]]) if op[2] else set()
        if op[0] in ("read", "write"): ws = expr_wits(op[2]) | expr_wits(op[3])
        for w in ws: occ[w] = occ.get(w, 0) + 1
    bools, consumed, prod0, inv = set(), set(), {}, []
    for i in sel:
        op = acir.ops[i]
        if op[0] != "assert": continue
        nt = norm_terms(op[1]); P1 = P - 1
        if len(nt) == 2:
            for x in {w for k in nt for w in k}:
                if nt.get((x,)) in (1, P1) and nt.get((x, x)) == (P - nt[(x,)]) % P:
                    bools.add(x); consumed.add(i)
        if len(nt) == 1 and len(next(iter(nt))) == 2: prod0[next(iter(nt))] = i          # d*r = 0
        if len(nt) == 3 and () in nt:
            lin = [k for k in nt if len(k) == 1]; quad = [k for k in nt if len(k) == 2]
            if len(lin) == 1 and len(quad) == 1 and nt[lin[0]] in (1, P1) and nt[quad[0]] == nt[lin[0]] and nt[()] == (-nt[lin[0]]) % P:
                inv.append((i, lin[0][0], quad[0]))      # r + d*t - 1 = 0 (or its negation)
    isz = []
    for i, r, (a, b) in inv:
        for d, t in ((a, b), (b, a)):         # product is d*t where t is the hint
            if tuple(sorted((d, r))) in prod0 and occ.get(t, 0) == 1:
                isz.append((r, d)); consumed.add(i); consumed.add(prod0[tuple(sorted((d, r)))]); break
    return bools, isz, consumed

LEMMAS = os.environ.get("T22_LEMMAS", "1") == "1"

def encode(ff, acir, sel):
    ver = {}
    bools, isz, consumed = (find_lemmas(acir, sel) if (LEMMAS and isinstance(ff, IntFF)) else (set(), [], set()))
    for b in sorted(bools): ff.A(ff.OR(ff.eq(ff.var(b), ff.zero), ff.eq(ff.var(b), ff.one)))
    for r, d in isz:
        ff.A(ff.OR(ff.eq(ff.var(r), ff.zero), ff.eq(ff.var(r), ff.one)))
        ff.A(f"(= (= {ff.var(d)} 0) (= {ff.var(r)} 1))")
    ff.lemma_stats = (len(bools), len(isz))
    for i in sel:
        if i in consumed: continue
        op = acir.ops[i]; k = op[0]
        if k == "assert": ff.A(ff.eq(ff.expr(op[1]), ff.zero))
        elif k == "range": ff.bits(ff.expr(op[1]), op[2])
        elif k == "init": ver[op[1]] = [ff.expr(e) for e in op[2]]
        elif k in ("read", "write"):
            b = op[1]
            if b not in ver: raise Unsupported(f"block b{b} not initialised inside the cone")
            idx, els = ff.expr(op[3] if k == "read" else op[2]), ver[b]    # READ: (blk, result, index); WRITE: (blk, index, value)
            ff.A(ff.OR(*[ff.eq(idx, ff.c(j)) for j in range(len(els))]))
            if k == "read":
                ch = els[-1]
                for j in range(len(els) - 2, -1, -1): ch = ff.ite(ff.eq(idx, ff.c(j)), els[j], ch)
                ff.A(ff.eq(ff.expr(op[2]), ch))
            else:
                val = ff.expr(op[3]); ver[b] = [ff.ite(ff.eq(idx, ff.c(j)), val, v) for j, v in enumerate(els)]

def build(spec, acir, abi):
    t_in, t_ret = abi_tables(abi, acir)
    M = resolve(spec["messages"], acir, t_in, t_ret, spec)
    streams = []
    for s in spec["streams"]:
        words = resolve(s["source"], acir, t_in, t_ret, spec)
        act = None
        if s.get("active_if_nonzero"):
            a = resolve(s["active_if_nonzero"], acir, t_in, t_ret, spec)
            if len(a) != 1: raise Unsupported("active_if_nonzero must be a scalar")
            act = a[0]
        streams.append((words, act))
    return M, streams

def query(spec, acir, M, streams, q, timeout):
    N = len(M)
    seeds = set()
    for e in M: seeds |= expr_wits(e)
    for words, act in streams:
        for e in words: seeds |= expr_wits(e)
        if act: seeds |= expr_wits(act)
    sel, wits = cone(acir, seeds)
    free = [n for n, o in acir.unmodeled if set(o) & wits]
    ff = (IntFF if BACKEND == "z3" else FF)(timeout * 1000); encode(ff, acir, sel)
    D = spec["derivation"]; mv = [ff.expr(e) for e in M]
    def mat(qt):
        ch = mv[-1]
        for j in range(N - 2, -1, -1): ch = ff.ite(ff.eq(qt, ff.c(j)), mv[j], ch)
        return ch
    def inrange(qt): return ff.OR(*[ff.eq(qt, ff.c(j)) for j in range(N)])
    tot = ff.zero; recs = []; acts = []
    for t, (words, act) in enumerate(streams):
        a = ff.NOT(ff.eq(ff.expr(act), ff.zero)) if act else ff.T
        acts.append(a)
        prev_end, prev_rem, cum, ems, cums, ss = ff.Fa, ff.zero, ff.zero, [], [], []
        for j, e in enumerate(words):
            s = ff.expr(e); ss.append(s)
            if D["mode"] == "walk":
                ln = ff.zero
                for kd, l in sorted(D["records"].items(), reverse=True): ln = ff.ite(ff.eq(s, ff.c(int(kd))), ff.c(l), ln)
                lnz, remz = ff.ne(ln, ff.zero), ff.ne(prev_rem, ff.zero)
                em = ff.AND(ff.NOT(prev_end), ff.OR(remz, lnz))
                en = ff.OR(prev_end, ff.AND(ff.NOT(remz), ff.NOT(lnz)))
                rm = ff.ite(prev_end, ff.zero, ff.ite(remz, ff.sub(prev_rem, ff.one), ff.ite(lnz, ff.sub(ln, ff.one), ff.zero)))
                prev_end, prev_rem = en, rm
            else:
                em = ff.ne(s, ff.zero)
            ems.append(em); cums.append(cum); cum = ff.add([cum, ff.ite(em, ff.one, ff.zero)])
        recs.append((a, ems, cums, ss, tot)); tot = ff.add([tot, ff.ite(a, cum, ff.zero)])
    L = tot
    names = {}
    if q == "nonvacuous":
        ff.A(ff.OR(*[ff.eq(L, ff.c(l)) for l in range(1, N + 1)]))
    elif q == "probe":     # generic refutation probe: every stream inactive (empty prefix), exactly one message slot nonzero
        for a, ems, cums, ss, off in recs: ff.A(ff.NOT(a))
        ff.A(ff.OR(*[ff.AND(*[ff.eq(mv[j], ff.zero) if j != k else ff.ne(mv[j], ff.zero) for j in range(N)]) for k in range(N)]))
    elif q == "tail":      # some slot k >= L is nonzero
        cases = []
        for k in range(N):
            ge = ff.OR(*[ff.eq(L, ff.c(l)) for l in range(0, k + 1)])
            cases.append(ff.AND(ge, ff.ne(mv[k], ff.zero)))
        ff.A(ff.OR(*cases))
    elif q == "prefix":    # some emitted word differs from the slot the spec assigns it
        cases = []
        for a, ems, cums, ss, off in recs:
            for em, cu, s in zip(ems, cums, ss):
                pos = ff.add([off, cu])
                cases.append(ff.AND(a, em, ff.OR(ff.NOT(inrange(pos)), ff.ne(mat(pos), s))))
        ff.A(ff.OR(*cases))
    else: raise ValueError(q)
    getv = [L] + mv[:16] + [x for r_ in recs for x in r_[3][:16]]
    st, out, dt = ff.solve(getv, os.path.join(SMT_DIR, f"{q}.smt2") if SMT_DIR else None)
    info = {}
    if st == "sat":
        vals = ff.parse_vals(out)
        nm = min(16, len(mv)); info = {"L": vals[0], "messages": vals[1:1 + nm]}
        pos = 1 + nm
        for t, r_ in enumerate(recs):
            k = min(16, len(r_[3])); info[f"stream{t}_words"] = vals[pos:pos + k]; pos += k
    elif st == "unknown": info = {"raw": out[:200]}
    return st, dt, len(sel), len(wits), free, info, getattr(ff, "lemma_stats", None)

def run(spec, acir_text, abi, timeout=300, smt_dir=None):
    global SMT_DIR
    SMT_DIR = smt_dir
    if smt_dir: os.makedirs(smt_dir, exist_ok=True)
    rep = {"verdict": "UNKNOWN", "assumed": [], "checked": [], "notes": [], "queries": {}}
    try:
        acir = Acir(acir_text)
        M, streams = build(spec, acir, abi)
    except Unsupported as ex:
        rep["notes"].append(f"unsupported: {ex}"); return rep
    except (KeyError, IndexError, AttributeError) as ex:
        rep["notes"].append(f"spec/IR mismatch: {ex!r}"); return rep
    # CHECKED: ABI-derived witness numbering agrees with the databus blocks recorded in the IR
    t_in, _ = abi_tables(abi, acir)
    blocks = [[w for e in blk for _, ws in e for w in ws] for blk in acir.calldata.values()]
    for prm in abi["parameters"]:
        if prm.get("visibility") == "databus":
            flat = [w for w in t_in[prm["name"]]]
            if flat not in blocks:
                rep["notes"].append(f"ABI witness numbering of databus param {prm['name']} does not match any CALLDATA block"); return rep
            rep["checked"].append(f"ABI numbering of databus param `{prm['name']}` equals an IR CALLDATA block")
    rep["assumed"] += [f"message array = {spec['messages']} ({len(M)} words)", f"derivation = {json.dumps(spec['derivation'])}"]
    for s in spec["streams"]:
        rep["assumed"].append(f"inner stream {s['source']}" + (f" active iff {s['active_if_nonzero']} != 0" if s.get("active_if_nonzero") else " always active"))
        if s["source"].startswith("rec:"):
            rep["checked"].append(f"stream {s['source']} is literally an input of recursive-aggregation call {s['source'][4]} (by construction)")
        else:
            rep["assumed"].append(f"  stream {s['source']} is bound to a verified proof (not visible in ACIR; e.g. databus)")
    if "recursion_public_inputs_start" in spec: rep["assumed"].append(f"recursion public inputs start at flat offset {spec['recursion_public_inputs_start']}")
    if spec.get("instance"): rep["assumed"].append("instance: " + spec["instance"])
    res = {}
    try:
        pr = query(spec, acir, M, streams, "probe", min(timeout, PROBE_SECONDS))
        rep["queries"]["probe"] = {"solver": pr[0], "seconds": round(pr[1], 1), "opcodes_in_cone": pr[2], "witnesses": pr[3]}
        if pr[0] == "sat":
            rep["checked"].append("PROBE: satisfying witness with every inner stream inactive (empty prefix, L=0) and a nonzero message slot: " + json.dumps(pr[5]))
            rep["checked"].append(f"lemmas used: booleans/is-zero = {pr[6]}")
            rep["verdict"] = "VIOLATED" if not pr[4] else "UNKNOWN"
            rep["notes"].append(f"cone: {pr[2]} of {len(acir.ops)} opcodes after exact pruning; components outside the cone are assumed satisfiable")
            if pr[4]: rep["notes"].append("SAT may be spurious (unmodeled black-box outputs in cone): " + ", ".join(pr[4]))
            return rep
        for q in ("nonvacuous", "prefix", "tail"):
            res[q] = query(spec, acir, M, streams, q, timeout)
            st, dt, nops, nw, free, info = res[q][:6]
            rep["queries"][q] = {"solver": st, "seconds": round(dt, 1), "opcodes_in_cone": nops, "witnesses": nw}
    except Unsupported as ex:
        rep["notes"].append(f"unsupported: {ex}"); return rep
    nv, pf, tl = res["nonvacuous"][0], res["prefix"][0], res["tail"][0]
    free = res["tail"][4]
    rep["notes"].append(f"cone: {res['tail'][2]} of {len(acir.ops)} opcodes, {res['tail'][3]} witnesses; constraints outside the cone are assumed satisfiable")
    if free: rep["notes"].append("unmodeled black-box outputs in cone: " + ", ".join(free))
    if nv != "sat":
        rep["notes"].append(f"non-vacuity query returned {nv}: constraints with L>=1 not shown satisfiable (encoding bug, spec mismatch or timeout)"); return rep
    rep["checked"].append("non-vacuity: the cone's constraints are satisfiable with a non-empty prefix (L>=1)")
    if tl == "sat":
        rep["checked"].append("TAIL: counterexample = satisfying witness with a message slot >= L nonzero: " + json.dumps(res["tail"][5]))
        rep["verdict"] = "VIOLATED" if not free else "UNKNOWN"
        if free: rep["notes"].append("SAT may be spurious (unmodeled black-box outputs in cone)")
    elif tl == "unsat":
        if pf == "unsat":
            rep["checked"].append("PREFIX: no satisfying witness where an emitted inner word differs from the slot the spec assigns it (spec consistent with circuit)")
            rep["checked"].append("TAIL: no satisfying witness with any message slot >= L(spec) nonzero")
            rep["verdict"] = "SATISFIED_AT_SCOPE"
        else:
            rep["checked"].append(f"TAIL: unsat, but PREFIX query is {pf}: spec derivation does not match circuit, so L is not trustworthy")
            if pf == "sat": rep["checked"].append("PREFIX counterexample: " + json.dumps(res["prefix"][5]))
    else:
        rep["notes"].append(f"tail query returned {tl}")
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acir", required=True); ap.add_argument("--abi", required=True); ap.add_argument("--spec", required=True)
    ap.add_argument("--timeout", type=int, default=300); ap.add_argument("--smt-dir"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.spec)); abi = json.load(open(a.abi))["abi"]
    rep = run(spec, open(a.acir).read(), abi, a.timeout, a.smt_dir)
    if a.json: print(json.dumps(rep, indent=1)); return
    print(f"{rep['verdict']}  {a.acir}")
    for k in ("assumed", "checked", "notes"):
        for x in rep[k]: print(f"  [{k.upper()[:4]}] {x}")
    for q, v in rep["queries"].items(): print(f"  [QRY] {q}: {v}")

if __name__ == "__main__":
    main()
