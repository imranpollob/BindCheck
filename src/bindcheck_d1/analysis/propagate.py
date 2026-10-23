"""Exact constraint propagation over parsed ACIR opcodes.

Invariant (checked by tests): (residual constraints) together with (assignment) is equisatisfiable with
(original constraints + fixed values), and every model of the residual extends, via the assignment, to a model of the
original. A constraint is only ever (a) kept, (b) discharged by ground evaluation, or (c) used to substitute a witness it
determines uniquely (a degree-1 unknown with a nonzero coefficient). Memory reads are replaced by an equivalent
equality only when the index and every earlier write to the block are known. Nothing is dropped silently; this is
the regression T22-v2 failed (implied goal constraints were discarded).
"""
from collections import defaultdict

from .. import P


class Contradiction(Exception):
    def __init__(self, op_index, why):
        super().__init__(f"op {op_index}: {why}")
        self.op_index, self.why = op_index, why


def norm(expr):
    """term list [(coef, [w..])] -> {monomial(tuple sorted wits): coef mod P} (0 coefficients removed)"""
    out = defaultdict(int)
    for c, ws in expr:
        out[tuple(sorted(ws))] = (out[tuple(sorted(ws))] + c) % P
    return {m: c for m, c in out.items() if c}


def subst(poly, val):
    out = defaultdict(int)
    for m, c in poly.items():
        rest = []
        for w in m:
            if w in val:
                c = c * val[w] % P
            else:
                rest.append(w)
        if c:
            out[tuple(rest)] = (out[tuple(rest)] + c) % P
    return {m: c for m, c in out.items() if c}


def unknowns(poly):
    return {w for m in poly for w in m}


class State:
    def __init__(self, ops, fixed):
        self.ops = ops
        self.val = {w: v % P for w, v in fixed.items()}
        self.why = {w: "fixed" for w in fixed}
        self.polys = {}            # op index -> current polynomial (asserts and derived read equalities)
        self.ranges = {}           # op index -> (poly, bits)
        self.mem = []              # op indices of memory ops (init/read/write) in program order
        self.resolved_reads = {}   # read op index -> derived equality poly
        self.occ = defaultdict(set)
        for i, op in enumerate(ops):
            k = op[0]
            if k == "assert":
                self._add_poly(i, norm(op[1]))
            elif k == "range":
                p = norm(op[1])
                self.ranges[i] = (p, op[2])
                for w in unknowns(p):
                    self.occ[w].add(i)
            elif k in ("init", "read", "write"):
                self.mem.append(i)

    def _add_poly(self, key, poly):
        self.polys[key] = poly
        for w in unknowns(poly):
            self.occ[w].add(key)

    def assign(self, w, v, why):
        if w in self.val:
            if self.val[w] != v % P:
                raise Contradiction(why, f"w{w} conflicting values")
            return
        self.val[w] = v % P
        self.why[w] = why

    def run(self):
        changed = True
        while changed:
            self._fixpoint()
            changed = self._memory_pass()
            changed = self._small_domain_pass() or changed
        self._check_ranges()
        return self

    SMALL_BITS = 4  # domain enumeration bound for the small-domain rule

    def _range_bits(self):
        """witness -> tightest range bits, from RANGE constraints on a single witness with coefficient 1."""
        rb = {}
        for i, (p, bits) in self.ranges.items():
            if bits < 254 and len(p) == 1:
                ((m, c),) = p.items()
                if len(m) == 1 and c == 1:
                    rb[m[0]] = min(bits, rb.get(m[0], 254))
        return rb

    def _small_domain_pass(self):
        """Exact rule: a linear constraint a*x + b*y + c = 0 with x range-bounded to <= SMALL_BITS bits and y range-bounded.
        Enumerate x; keep values whose y satisfies its range. Exactly one survivor determines x and y in every model;
        none is a contradiction; otherwise nothing changes. Uses only that constraint and the two RANGE constraints."""
        rb = self._range_bits()
        new = False
        for k, p in list(self.polys.items()):
            p = subst(p, self.val)
            u = unknowns(p)
            if len(u) != 2 or any(len(m) > 1 for m in p):
                continue
            for x in u:
                (y,) = u - {x}
                if rb.get(x, 254) > self.SMALL_BITS or y not in rb or not p.get((y,), 0):
                    continue
                inv_b = pow(p[(y,)], P - 2, P)
                sols = []
                for xv in range(1 << rb[x]):
                    yv = (-(p.get((), 0) + p.get((x,), 0) * xv)) * inv_b % P
                    if yv < (1 << rb[y]):
                        sols.append((xv, yv))
                if not sols:
                    raise Contradiction(k, "small-domain rule: no feasible value")
                if len(sols) == 1:
                    self.assign(x, sols[0][0], ("small", k))
                    self.assign(y, sols[0][1], ("small", k))
                    new = True
                break
        return new

    def _fixpoint(self):
        work = list(self.polys)
        seen_val = set(self.val)
        work_set = set(work)
        while work:
            k = work.pop()
            work_set.discard(k)
            p = subst(self.polys[k], self.val)
            self.polys[k] = p
            u = unknowns(p)
            if not u:
                if p.get((), 0) % P:
                    raise Contradiction(k, "ground constraint is nonzero")
                continue
            if len(u) == 1:
                (w,) = u
                if all(len(m) <= 1 for m in p) and p.get((w,), 0):
                    v = (-p.get((), 0)) * pow(p[(w,)], P - 2, P) % P
                    self.assign(w, v, k)
                    self.polys[k] = {}
                    for k2 in self.occ[w]:
                        if k2 in self.polys and k2 not in work_set:
                            work.append(k2)
                            work_set.add(k2)
        return seen_val != set(self.val)

    def _memory_pass(self):
        """Resolve reads whose index (and all earlier writes' indices) are known. Returns True if anything new."""
        blocks, dirty, new = {}, set(), False
        for i in self.mem:
            op = self.ops[i]
            if op[0] == "init":
                blocks[op[1]] = [norm(e) for e in op[2]]
                dirty.discard(op[1])
                continue
            b = op[1]
            if b not in blocks:
                raise Contradiction(i, f"block b{b} used before INIT")
            if b in dirty:
                continue
            idx_poly = subst(norm(op[3] if op[0] == "read" else op[2]), self.val)
            if unknowns(idx_poly):
                if op[0] == "write":
                    dirty.add(b)
                continue
            idx = idx_poly.get((), 0)
            if idx >= len(blocks[b]):
                raise Contradiction(i, f"memory index {idx} out of range for b{b}")
            if op[0] == "write":
                blocks[b][idx] = norm(op[3])
            elif i not in self.resolved_reads:
                eq = defaultdict(int)
                for m, c in norm(op[2]).items():
                    eq[m] = (eq[m] + c) % P
                for m, c in blocks[b][idx].items():
                    eq[m] = (eq[m] - c) % P
                eq = {m: c for m, c in eq.items() if c}
                self.resolved_reads[i] = eq
                self._add_poly(("read", i), eq)
                new = True
        return new

    def _check_ranges(self):
        for i, (p, bits) in self.ranges.items():
            q = subst(p, self.val)
            if not unknowns(q):
                v = q.get((), 0)
                if bits < 254 and v >= (1 << bits):
                    raise Contradiction(i, f"range {bits} violated by {v}")

    # ------------------------------------------------------------------ residual view
    def residual(self):
        """Remaining constraints as dict: asserts {key: poly}, ranges {i: (poly, bits)}, memory op indices."""
        asserts = {k: subst(p, self.val) for k, p in self.polys.items()}
        asserts = {k: p for k, p in asserts.items() if unknowns(p)}
        ranges = {}
        for i, (p, bits) in self.ranges.items():
            q = subst(p, self.val)
            if unknowns(q) and bits < 254:
                ranges[i] = (q, bits)
        mem = [i for i in self.mem if not (self.ops[i][0] == "read" and i in self.resolved_reads)]
        return asserts, ranges, mem


def value_of(expr_or_poly, val):
    p = expr_or_poly if isinstance(expr_or_poly, dict) else norm(expr_or_poly)
    q = subst(p, val)
    return None if unknowns(q) else q.get((), 0)
