#!/usr/bin/env python3
"""T21 prototype: source-based check that every public message word after the
verified-proof-derived prefix is constrained to zero (Noir circuits).

Usage: t21_tailcheck.py FILE.nr [--main main] [--message-array NAME] [--json]
Verdicts: SATISFIED | UNCONSTRAINED | UNKNOWN. Anything not understood -> UNKNOWN.
No upstream file is modified; the input is only read. See results/raw/T21/00_preregistration.md.
"""
import argparse, json, re, sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------- lexer
class Unsupported(Exception):
    pass

TOK = re.compile(r"""
  (?P<ws>\s+)|(?P<lc>//[^\n]*)|(?P<bc>/\*.*?\*/)
 |(?P<num>0x[0-9a-fA-F]+|\d+)|(?P<id>[A-Za-z_][A-Za-z_0-9]*)|(?P<str>"(?:\\.|[^"\\])*")
 |(?P<op>\.\.|::|==|!=|>=|<=|&&|\|\||\+=|-=|\*=|->|<<|>>|[-+*/%=<>!&|^.,;:(){}\[\]#])
""", re.X | re.S)

def lex(src):
    toks, pos, line = [], 0, 1
    while pos < len(src):
        m = TOK.match(src, pos)
        if not m:
            raise Unsupported(f"lex error at line {line}: {src[pos:pos+20]!r}")
        k, t = m.lastgroup, m.group()
        if k not in ("ws", "lc", "bc"):
            toks.append((k, t, line))
        line += t.count("\n")
        pos = m.end()
    toks.append(("eof", "", line))
    return toks

# ---------------------------------------------------------------- AST (tuples/dataclasses)
@dataclass
class Fn:
    name: str; params: list; body: list; is_test: bool; line: int
    unconstrained: bool = False
@dataclass
class Param:
    name: str; ty: object; pub: bool

# expressions: ('num',v) ('str',s) ('name',n) ('path',[..]) ('idx',base,i) ('fld',base,n)
# ('call',fn,args) ('mcall',base,n,args) ('bin',op,l,r) ('un',op,e) ('arr',[e]) ('rep',e,n)
# ('ife',cond,then,else) ('blk',stmts)
# statements: ('let',name,mut,init,line) ('asg',target,op,rhs,line) ('assert',cond,msg,line)
# ('for',var,lo,hi,body,line) ('if',cond,then,else,line) ('expr',e,line)

PREC = [("||",), ("&&",), ("==", "!=", "<", ">", "<=", ">="), ("|",), ("^",), ("&",),
        ("<<", ">>"), ("+", "-"), ("*", "/", "%")]

class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0
    def peek(self, o=0): return self.t[self.i + o]
    def line(self): return self.peek()[2]
    def next(self): tk = self.t[self.i]; self.i += 1; return tk
    def at(self, text, o=0): return self.peek(o)[1] == text and self.peek(o)[0] in ("op", "id")
    def eat(self, text):
        if self.at(text): return self.next()
        raise Unsupported(f"line {self.line()}: expected {text!r}, got {self.peek()[1]!r}")
    def ident(self):
        k, t, l = self.next()
        if k != "id": raise Unsupported(f"line {l}: expected identifier, got {t!r}")
        return t

    # ---- items
    def module(self):
        fns, structs, globs = {}, {}, {}
        while self.peek()[0] != "eof":
            attrs = []
            while self.at("#"):
                self.next(); self.eat("[")
                depth = 1; txt = []
                while depth:
                    k, t, _ = self.next()
                    depth += (t == "[") - (t == "]")
                    if depth: txt.append(t)
                attrs.append("".join(txt))
            if self.at("use"):
                while not self.at(";"): self.next()
                self.next(); continue
            if self.at("global"):
                self.next(); n = self.ident(); self.eat(":"); self.ty(); self.eat("=")
                globs[n] = self.expr(); self.eat(";"); continue
            if self.at("struct"):
                self.next(); n = self.ident(); self.eat("{"); fl = []
                while not self.at("}"):
                    fl.append(self.ident()); self.eat(":"); self.ty()
                    if self.at(","): self.next()
                self.eat("}"); structs[n] = fl; continue
            uncon = False
            if self.at("pub"): self.next()
            if self.at("unconstrained"): self.next(); uncon = True
            if self.at("fn"):
                f = self.fn(attrs); f.unconstrained = uncon; fns[f.name] = f; continue
            raise Unsupported(f"line {self.line()}: unsupported item {self.peek()[1]!r}")
        return fns, structs, globs

    def ty(self):
        if self.at("["):
            self.next(); e = self.ty(); self.eat(";")
            k, t, l = self.next()
            n = int(t, 0) if k == "num" else t
            self.eat("]"); return ("array", e, n)
        if self.at("pub"): self.next()
        n = self.ident()
        if self.at("<") : raise Unsupported(f"line {self.line()}: generics unsupported")
        return ("name", n)

    def fn(self, attrs):
        line = self.line(); self.eat("fn"); name = self.ident()
        if self.at("<"): raise Unsupported(f"line {line}: generic fn unsupported")
        self.eat("("); ps = []
        while not self.at(")"):
            n = self.ident(); self.eat(":")
            pub = False
            if self.at("pub"): self.next(); pub = True
            ps.append(Param(n, self.ty(), pub))
            if self.at(","): self.next()
        self.eat(")")
        if self.at("->"): self.next(); self.ty()
        body = self.block()
        return Fn(name, ps, body, any(a.startswith("test") for a in attrs), line)

    # ---- statements
    def block(self):
        self.eat("{"); out = []
        while not self.at("}"):
            out.append(self.stmt())
        self.eat("}"); return out

    def stmt(self):
        l = self.line()
        if self.at("let"):
            self.next(); mut = False
            if self.at("mut"): self.next(); mut = True
            n = self.ident()
            if self.at(":"): self.next(); self.ty()
            init = None
            if self.at("="): self.next(); init = self.expr()
            self.eat(";"); return ("let", n, mut, init, l)
        if self.at("for"):
            self.next(); v = self.ident(); self.eat("in")
            lo = self.expr(); self.eat(".."); hi = self.expr()
            return ("for", v, lo, hi, self.block(), l)
        if self.at("if"):
            c, th, el = self.if_parts()
            return ("if", c, th, el, l)
        if self.at("assert") and self.at("(", 1):
            self.next(); self.eat("("); c = self.expr(); msg = None
            if self.at(","):
                self.next()
                if self.at(")"): pass
                elif self.peek()[0] == "str": msg = self.next()[1]
                else: raise Unsupported(f"line {l}: assert message not a string")
            self.eat(")"); self.eat(";"); return ("assert", c, msg, l)
        e = self.expr()
        if self.peek()[1] in ("=", "+=", "-=", "*=") and self.peek()[0] == "op":
            op = self.next()[1]; rhs = self.expr(); self.eat(";")
            return ("asg", e, op, rhs, l)
        if self.at(";"): self.next()
        elif not self.at("}"): raise Unsupported(f"line {self.line()}: expected ';', got {self.peek()[1]!r}")
        return ("expr", e, l)

    def if_parts(self):
        self.eat("if"); c = self.expr(); th = self.block(); el = None
        if self.at("else"):
            self.next()
            if self.at("if"):
                c2, t2, e2 = self.if_parts(); el = [("if", c2, t2, e2, self.line())]
            else: el = self.block()
        return c, th, el

    # ---- expressions
    def expr(self, lvl=0):
        if lvl == len(PREC): return self.unary()
        l = self.expr(lvl + 1)
        while self.peek()[0] == "op" and self.peek()[1] in PREC[lvl]:
            op = self.next()[1]; r = self.expr(lvl + 1); l = ("bin", op, l, r)
        return l

    def unary(self):
        if self.peek()[0] == "op" and self.peek()[1] in ("!", "-"):
            op = self.next()[1]; return ("un", op, self.unary())
        e = self.atom()
        while True:
            if self.at("["):
                self.next(); i = self.expr(); self.eat("]"); e = ("idx", e, i)
            elif self.at(".") :
                self.next(); n = self.ident()
                if self.at("("):
                    e = ("mcall", e, n, self.args())
                else: e = ("fld", e, n)
            elif self.at("(") and e[0] in ("name", "path"):
                e = ("call", e, self.args())
            else: return e

    def args(self):
        self.eat("("); a = []
        while not self.at(")"):
            a.append(self.expr())
            if self.at(","): self.next()
        self.eat(")"); return a

    def atom(self):
        k, t, l = self.peek()
        if k == "num": self.next(); return ("num", int(t, 0))
        if k == "str": self.next(); return ("str", t)
        if self.at("("):
            self.next(); e = self.expr(); self.eat(")"); return e
        if self.at("["):
            self.next()
            if self.at("]"): self.next(); return ("arr", [])
            first = self.expr()
            if self.at(";"):
                self.next(); n = self.expr(); self.eat("]"); return ("rep", first, n)
            el = [first]
            while self.at(","):
                self.next()
                if self.at("]"): break
                el.append(self.expr())
            self.eat("]"); return ("arr", el)
        if self.at("if"):
            c, th, el = self.if_parts(); return ("ife", c, th, el)
        if self.at("{"): return ("blk", self.block())
        if k == "id":
            self.next(); path = [t]
            while self.at("::"):
                self.next(); path.append(self.ident())
            return ("path", path) if len(path) > 1 else ("name", t)
        raise Unsupported(f"line {l}: unsupported expression token {t!r}")

# ---------------------------------------------------------------- helpers
def show(e):
    k = e[0]
    if k == "num": return str(e[1])
    if k == "str": return e[1]
    if k == "name": return e[1]
    if k == "path": return "::".join(e[1])
    if k == "idx": return f"{show(e[1])}[{show(e[2])}]"
    if k == "fld": return f"{show(e[1])}.{e[2]}"
    if k == "call": return f"{show(e[1])}({', '.join(show(a) for a in e[2])})"
    if k == "mcall": return f"{show(e[1])}.{e[2]}({', '.join(show(a) for a in e[3])})"
    if k == "bin": return f"({show(e[2])} {e[1]} {show(e[3])})"
    if k == "un": return f"{e[1]}{show(e[2])}"
    if k == "arr": return "[" + ", ".join(show(x) for x in e[1]) + "]"
    if k == "rep": return f"[{show(e[1])}; {show(e[2])}]"
    if k == "ife": return f"if {show(e[1])} {{..}} else {{..}}"
    return k

def children(e):
    """direct sub-expressions (not statements) of expression e"""
    k = e[0]
    if k in ("idx", "bin"): return [e[1], e[2]] if k == "idx" else [e[2], e[3]]
    if k == "fld": return [e[1]]
    if k == "call": return list(e[2])
    if k == "mcall": return [e[1]] + list(e[3])
    if k == "un": return [e[2]]
    if k == "arr": return list(e[1])
    if k == "rep": return [e[1], e[2]]
    if k == "ife": return [e[1]]
    return []

def sub_blocks(e):
    if e[0] == "ife":
        return [e[2]] + ([e[3]] if e[3] else [])
    if e[0] == "blk": return [e[1]]
    return []

def walk_expr(e):
    yield e
    for c in children(e): yield from walk_expr(c)
    for b in sub_blocks(e):
        for s in b: yield from walk_stmt_exprs(s)

def stmt_exprs(s):
    k = s[0]
    if k == "let": return [s[3]] if s[3] else []
    if k == "asg": return [s[1], s[3]]
    if k == "assert": return [s[1]]
    if k == "for": return [s[2], s[3]]
    if k == "if": return [s[1]]
    if k == "expr": return [s[1]]
    return []

def stmt_blocks(s):
    k = s[0]
    if k == "for": return [s[4]]
    if k == "if": return [s[2]] + ([s[3]] if s[3] else [])
    return []

def walk_stmt_exprs(s):
    for e in stmt_exprs(s): yield from walk_expr(e)
    for b in stmt_blocks(s):
        for t in b: yield from walk_stmt_exprs(t)

def all_stmts(block):
    for s in block:
        yield s
        for b in stmt_blocks(s): yield from all_stmts(b)
        for e in stmt_exprs(s):
            for x in walk_expr(e):
                for b in sub_blocks(x): yield from all_stmts(b)

def names_in(e):
    return {x[1] for x in walk_expr(e) if x[0] == "name"}

def base_name(e):
    while e[0] in ("idx", "fld"): e = e[1]
    return e[1] if e[0] == "name" else None

# ---------------------------------------------------------------- analysis
class Report:
    def __init__(self, label):
        self.label, self.unknown, self.facts = label, [], []
    def u(self, code, msg): self.unknown.append(f"{code}: {msg}")
    def f(self, msg): self.facts.append(msg)

def decompose_counter_index(idx):
    """index of the form c / c + k / k + c -> (c, k); else None"""
    if idx[0] == "name": return idx[1], 0
    if idx[0] == "bin" and idx[1] == "+":
        a, b = idx[2], idx[3]
        if a[0] == "name" and b[0] == "num": return a[1], b[1]
        if b[0] == "name" and a[0] == "num": return b[1], a[1]
    return None

def is_zero(e): return e == ("num", 0)

def analyze(src, main="main", message_array=None, label="?"):
    R = Report(label)
    try:
        toks = lex(src)
        fns, structs, globs = Parser(toks).module()
    except Unsupported as ex:
        R.u("U1", f"parse/lex failure: {ex}"); R.verdict = "UNKNOWN"; return R
    if any(k == "id" and t in ("unsafe", "unconstrained", "oracle") for k, t, _ in toks):
        R.u("U8", "file contains unsafe/unconstrained/oracle")
    if main not in fns:
        R.u("U1", f"no fn {main}"); R.verdict = "UNKNOWN"; return R
    M_fn = fns[main]; body = M_fn.body
    pub_arrays = {p.name: p for p in M_fn.params if p.pub and p.ty[0] == "array"}

    # ---- E2: message array + counter
    mut_locals = {s[1] for s in all_stmts(body) if s[0] == "let" and s[2]}
    def counter_reads_of(name):
        out = []
        for s in all_stmts(body):
            for e in stmt_exprs(s):
                for x in walk_expr(e):
                    if x[0] == "idx" and x[1] == ("name", name):
                        d = decompose_counter_index(x[2])
                        if d and d[0] in mut_locals: out.append((x, d, s[-1]))
        return out
    if message_array:
        if message_array not in pub_arrays:
            R.u("U2", f"--message-array {message_array!r} is not a pub array param of {main}")
        cands = [message_array] if message_array in pub_arrays else []
    else:
        cands = [n for n in pub_arrays if counter_reads_of(n)]
        if len(cands) != 1:
            R.u("U2", f"need exactly one pub array param read at a counter-based index; found {cands}")
            cands = []
    if not cands:
        R.verdict = "UNKNOWN"; return R
    M = cands[0]; Mlen = pub_arrays[M].ty[2]
    if isinstance(Mlen, str): Mlen = globs.get(Mlen, (None, None))[1] if Mlen in globs else None
    R.f(f"message array: `{M}` (pub, declared length {Mlen}), param of {main}()")

    reads = counter_reads_of(M)
    counters = {d[0] for _, d, _ in reads}
    if len(counters) != 1:
        R.u("U3", f"counter-indexed reads use {sorted(counters)}; need exactly one counter")
        R.verdict = "UNKNOWN"; return R
    C = next(iter(counters))

    # ---- E3: counter writes
    decls = [s for s in all_stmts(body) if s[0] == "let" and s[1] == C]
    if len(decls) != 1 or not decls[0][2] or decls[0][3] != ("num", 0):
        R.u("U3", f"counter `{C}` must be declared once as `let mut {C} = 0`")
    writes = []   # (stmt, increment, enclosing conditions)
    def collect_writes(block, conds):
        for s in block:
            if s[0] == "asg" and base_name(s[1]) == C:
                if s[1] == ("name", C) and s[2] == "+=" and s[3][0] == "num":
                    writes.append((s, s[3][1], list(conds)))
                else:
                    R.u("U3", f"line {s[-1]}: write to `{C}` is not `+= const`: {show(s[1])} {s[2]} {show(s[3])}")
            if s[0] == "if":
                collect_writes(s[2], conds + [show(s[1])])
                if s[3]: collect_writes(s[3], conds + [f"!{show(s[1])}"])
            elif s[0] == "for": collect_writes(s[4], conds + [f"for {s[1]} in {show(s[2])}..{show(s[3])}"])
    collect_writes(body, [])
    R.f(f"prefix counter: `{C}` (init 0); writes: " +
        "; ".join(f"l.{w[0][-1]} += {w[1]}" + (f" [under {', '.join(w[2])}]" if w[2] else "") for w in writes))

    # ---- E4/E5: classify all occurrences of M in main
    tail_checks = []
    def is_len(e, alias): return e[0] == "mcall" and e[1] == ("name", alias) and e[2] == "len" and not e[3]

    def classify_uses(block, alias, calias, alen, fn_label, ctx_conds, top_stmt_idx, depth):
        """walk a block; ctx_conds = enclosing conditions (exprs) / loops; returns None. Fills tail_checks."""
        for s in block:
            handle_stmt(s, alias, calias, alen, fn_label, ctx_conds, top_stmt_idx, depth)

    def handle_stmt(s, alias, calias, alen, fn_label, ctx, top_idx, depth):
        k = s[0]
        line = s[-1]
        # recognised tail check: assert(alias[i] == 0) under for i in 0..len, if i >= counter
        if k == "assert" and s[1][0] == "bin" and s[1][1] == "==":
            l, r = s[1][2], s[1][3]
            if not is_zero(r):
                l = r if is_zero(l) else None
            if l is not None and l[0] == "idx" and l[1] == ("name", alias) and l[2][0] == "name":
                iv = l[2][1]
                shape = tail_shape(ctx, iv, calias, alen, alias)
                if shape is True:
                    tail_checks.append((fn_label, line, top_idx)); return
                R.u("U6", f"line {line} ({fn_label}): zero-assert on {alias}[{iv}] but {shape}")
                return
        if k == "if" or k == "for":
            for e in stmt_exprs(s): scan_expr(e, alias, calias, alen, fn_label, line, depth)
            if k == "for":
                sub = ctx + [("for", s[1], s[2], s[3])]
                classify_uses(s[4], alias, calias, alen, fn_label, sub, top_idx, depth)
            else:
                classify_uses(s[2], alias, calias, alen, fn_label, ctx + [("if", s[1])], top_idx, depth)
                if s[3]: classify_uses(s[3], alias, calias, alen, fn_label, ctx + [("else", s[1])], top_idx, depth)
            return
        for e in stmt_exprs(s): scan_expr(e, alias, calias, alen, fn_label, line, depth)

    def scan_expr(e, alias, calias, alen, fn_label, line, depth):
        # occurrences of Name(alias) must be: counter-index read (main only), .len(), or fn argument
        def rec(x, parent_ok):
            if x[0] == "idx" and x[1] == ("name", alias):
                if fn_label == main and decompose_counter_index(x[2]) and decompose_counter_index(x[2])[0] == C:
                    rec(x[2], True); return
                R.u("U4", f"line {line} ({fn_label}): `{show(x)}` is not a counter-based read"); rec(x[2], True); return
            if is_len(x, alias): return
            if x[0] == "call" and x[1][0] == "name" and any(a == ("name", alias) for a in x[2]):
                call_into(x, alias, calias, alen, fn_label, line, depth);
                for a in x[2]:
                    if a != ("name", alias): rec(a, True)
                return
            if x == ("name", alias):
                R.u("U4", f"line {line} ({fn_label}): `{alias}` used in an unexplained way inside `{show(e)}`"); return
            for c in children(x): rec(c, True)
            for b in sub_blocks(x):
                classify_uses(b, alias, calias, alen, fn_label, [], top_stmt_idx_holder[0], depth)
        rec(e, False)

    top_stmt_idx_holder = [0]
    def call_into(call, alias, calias, alen, fn_label, line, depth):
        fname = call[1][1]
        if fname not in fns or depth >= 3:
            R.u("U5", f"line {line}: `{alias}` passed to unresolved/too-deep function `{fname}`"); return
        callee = fns[fname]
        if len(callee.params) != len(call[2]):
            R.u("U5", f"line {line}: arity mismatch calling {fname}"); return
        bind_m = bind_c = None
        for p, a in zip(callee.params, call[2]):
            if a == ("name", alias): bind_m = p
            if calias and a == ("name", calias): bind_c = p
        if bind_m.ty[0] != "array" or bind_m.ty[2] != alen:
            R.u("U5", f"{fname}: param `{bind_m.name}` type is not [_; {alen}]"); return
        if bind_c is None:
            R.u("U5", f"{fname}: counter `{calias}` is not passed to the callee"); return
        # callee must not reassign its counter param
        for s in all_stmts(callee.body):
            if s[0] == "asg" and base_name(s[1]) == bind_c.name:
                R.u("U5", f"{fname}: reassigns its counter param"); return
        R.f(f"l.{line}: `{M}` passed to {fname}({bind_m.name}, {bind_c.name}) -> analysing callee")
        called_from.append((fname, line))
        classify_uses(callee.body, bind_m.name, bind_c.name, alen, fname, [], top_stmt_idx_holder[0], depth + 1)

    called_from = []
    def tail_shape(ctx, iv, calias, alen, alias):
        # exactly: for iv in 0..len(alias) { if iv >= calias { assert(alias[iv] == 0) } }
        if len(ctx) != 2: return f"enclosing context is {len(ctx)} levels deep, expected for+if"
        f, i = ctx
        if f[0] != "for" or f[1] != iv or not is_zero(f[2]): return "loop is not `for i in 0..hi` over the indexed variable"
        hi = f[3]
        if not (hi == ("num", alen) or is_len(hi, alias)):
            return f"loop upper bound `{show(hi)}` is not the full array length {alen}"
        if i[0] != "if": return "assert is not directly under an `if`"
        c = i[1]
        good = c[0] == "bin" and ((c[1] == ">=" and c[2] == ("name", iv) and c[3] == ("name", calias)) or
                                  (c[1] == "<=" and c[3] == ("name", iv) and c[2] == ("name", calias)))
        if not good: return f"guard `{show(c)}` is not exactly `{iv} >= {calias}` (slot {calias} itself would not be covered, or boundary differs)"
        return True

    # classify main body, remembering the top-level statement index for placement
    for ti, s in enumerate(body):
        top_stmt_idx_holder[0] = ti
        handle_stmt(s, M, C, Mlen, main, [], ti, 0)
    R.f("tail checks found: " + (", ".join(f"{fl}@l.{ln}" for fl, ln, _ in tail_checks) or "none"))

    # ---- E5 read coverage
    def cov(block):
        pend = []
        for s in block:
            for e in stmt_exprs(s):
                for x in walk_expr(e):
                    if x[0] == "idx" and x[1] == ("name", M):
                        d = decompose_counter_index(x[2])
                        if d and d[0] == C: pend.append((d[1], s[-1]))
                    for b in sub_blocks(x): pend += cov(b)
            if s[0] == "asg" and s[1] == ("name", C) and s[2] == "+=" and s[3][0] == "num":
                n = s[3][1]; pend = [(o - n, l) for o, l in pend if o - n >= 0]
            for b in stmt_blocks(s): pend += cov(b)
        return pend
    left = cov(body)
    if left:
        for o, l in left: R.u("U5", f"read at l.{l} (offset {o} from `{C}`) not covered by a later increment in its block")
    else:
        R.f("read coverage: every counter read M[c+k] is followed (same block) by increments of c totalling > k => reads lie below final c")

    # ---- E7 placement
    placement_ok = True
    for fl, ln, ti in tail_checks:
        same_stmt_write = [w for w in writes if any(w[0] is x for x in all_stmts([body[ti]]))]
        last_write_top = max((top_of(body, w[0]) for w in writes), default=-1)
        if ti <= last_write_top:
            R.u("U6", f"tail check at {fl}@l.{ln} (top-level stmt #{ti}) is not after the last write to `{C}` (stmt #{last_write_top})")
            placement_ok = False
        elif same_stmt_write:
            R.u("U6", "tail-check statement also writes the counter"); placement_ok = False
        # the checking statement must be top level of main (unconditional)
        top = body[ti]
        if top[0] not in ("for", "expr"):
            R.u("U6", f"tail check sits inside a conditional/other top-level statement ({top[0]})"); placement_ok = False
    if tail_checks and placement_ok:
        R.f("tail check placement: top-level in main, after the last write to the counter, unconditional")

    # ---- E6 provenance
    prov = provenance(body, M, C, reads)
    prov_nodes = prov[1] if prov else []
    prov = prov[0] if prov else None
    if prov is None:
        R.u("U7", "no verify_proof(_with_type) call whose public-input argument is connected to a message read")
    else:
        R.f("prefix provenance: " + prov)
        R.f("prefix value origin: " + origins(body, M_fn, prov_nodes))

    # ---- verdict
    if R.unknown:
        R.verdict = "UNKNOWN"
    elif tail_checks:
        R.verdict = "SATISFIED"
    else:
        R.verdict = "UNCONSTRAINED"
    return R

def origins(body, M_fn, nodes):
    """for each non-M variable on the provenance path, follow `let v = expr` back to a main() parameter"""
    params = {p.name: p for p in M_fn.params}
    lets = {}
    for s in all_stmts(body):
        if s[0] == "let" and s[3]: lets.setdefault(s[1], s[3])
    out = []
    for n in nodes:
        if n.endswith("[..]") or n in params: continue
        chain, cur, seen = [], n, set()
        while cur in lets and cur not in seen:
            seen.add(cur); e = lets[cur]; chain.append(f"{cur} = {show(e)}")
            b = base_name(e)
            if b in params:
                p = params[b]; out.append(" <- ".join(chain) + f" <- param `{b}`" + (" (pub)" if p.pub else " (private witness)")); break
            cur = b
    return "; ".join(out) if out else "none found: path variables are not derived from a main() parameter (values flow from M into the proof's public inputs)"

def top_of(body, stmt):
    for i, s in enumerate(body):
        if any(x is stmt for x in all_stmts([s])): return i
    return -1

def value_exprs(e):
    """expressions whose value can be the result of e (if-expr: branch tails only, not the condition)"""
    if e[0] == "ife":
        out = []
        for blk in sub_blocks(e):
            if blk and blk[-1][0] == "expr": out += value_exprs(blk[-1][1])
            else: out.append(("arr", []))
        return out
    return [e]

def provenance(body, M, C, reads):
    """flow-insensitive undirected var graph (scopes ignored); an M-read links to the variables of the
    statement it appears in; assert(a == b) links a and b; sink = value args[2] of verify_proof*(...).
    Returns a labelled path or None."""
    adj = {}
    def link(a, b, why):
        if a == b: return
        for x, y in ((a, b), (b, a)): adj.setdefault(x, {})[y] = why
    def vars_of(e):
        out = set()
        for x in walk_expr(e):
            if x[0] == "name": out.add(x[1])
            if x[0] == "idx" and x[1] == ("name", M): out.add(f"{M}[..]")
        return out
    for s in all_stmts(body):
        if s[0] == "let" and s[3]:
            for v in vars_of(s[3]): link(s[1], v, f"l.{s[-1]}: let {s[1]} = {show(s[3])}"[:110])
        elif s[0] == "asg":
            b = base_name(s[1])
            if b:
                for v in vars_of(s[3]): link(b, v, f"l.{s[-1]}: {show(s[1])} {s[2]} {show(s[3])}"[:110])
        elif s[0] == "assert" and s[1][0] == "bin" and s[1][1] == "==":
            for a in vars_of(s[1][2]):
                for b in vars_of(s[1][3]): link(a, b, f"l.{s[-1]}: assert {show(s[1])}"[:110])
    sinks = set()
    for s in all_stmts(body):
        for e in stmt_exprs(s):
            for x in walk_expr(e):
                if x[0] == "call" and x[1][0] == "path" and x[1][1][-1] in ("verify_proof", "verify_proof_with_type") and len(x[2]) >= 3:
                    for v in value_exprs(x[2][2]): sinks |= vars_of(v)
    start = f"{M}[..]"
    if start not in adj or not sinks: return None
    prev, q = {start: None}, [start]
    while q:
        n = q.pop(0)
        if n in sinks and n != start:
            hops, nodes = [], [n]
            while prev[n] is not None:
                hops.append(f"{adj[prev[n]][n]}"); n = prev[n]; nodes.append(n)
            return " | ".join(reversed(hops)) + "  ==> value passed as public-inputs arg of verify_proof_with_type", nodes
        for m in sorted(adj.get(n, ())):
            if m not in prev: prev[m] = n; q.append(m)
    return None

def main_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("--main", default="main")
    ap.add_argument("--message-array"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    src = open(a.file).read()
    R = analyze(src, a.main, a.message_array, a.file)
    if a.json:
        print(json.dumps({"file": a.file, "verdict": R.verdict, "facts": R.facts, "unknown": R.unknown}, indent=1))
    else:
        print(f"{R.verdict}  {a.file}")
        for f in R.facts: print("  + " + f)
        print("  . note: provenance is variable connectivity only (flow/scope-insensitive); padding-proof public-input substitution is not reasoned about")
        for u in R.unknown: print("  ? " + u)
    return 0

if __name__ == "__main__":
    sys.exit(main_cli())
