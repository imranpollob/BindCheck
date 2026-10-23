"""Joint producer/decoder/consumer query.

Encodes, in one finite-field + Bool SMT instance (cvc5, via the hash-pinned T22-v3 FF builder):
  * the residual producer constraints (after exact propagation), referencing the message and permission words;
  * a symbolic record walk over the public message stream (committed effects) and over the certified permission
    stream, using the policy grammar; and
  * one authorization / coverage / non-vacuity goal.

A SAT model is an abstract candidate until replayed (research contract §8). The encoder never reads the expected
verdict or a case label.
"""
import importlib.util
from pathlib import Path

from .. import P
from ..artifacts import sha256_file
from ..frontends import acir as acir_fe
from . import propagate as pr

_FF_PATH = Path(__file__).resolve().parents[3] / "scripts/t22_v3_tailspec.py"
_FF_SHA = "81a1cd43cd3e6e735dc325535f05d9b2a88c6c9794b434ab53e834061ff700c8"


def _ff_module():
    if sha256_file(_FF_PATH) != _FF_SHA:
        raise RuntimeError("pinned FF builder hash mismatch")
    spec = importlib.util.spec_from_file_location("t22_v3_ff_pinned", _FF_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _poly_terms(poly):
    """propagate poly {monomial-tuple: coef} -> FF term list [(coef, [w..])]"""
    return [(c, list(m)) for m, c in poly.items()]


class JointEncoder:
    def __init__(self, program, state, policy, timeout_ms):
        self.prog = program
        self.state = state
        self.pol = policy
        M = _ff_module()
        self.M = M
        self.ff = M.FF(timeout_ms)
        self.msg_w = program.table[policy.messages_ref.split(":", 1)[1]]
        self.perm_w = program.table[policy.permission_ref.split(":", 1)[1]]
        self._encoded = False

    # ---- producer residual --------------------------------------------------
    def encode_producer(self):
        ff = self.ff
        asserts, ranges, mem = self.state.residual()
        if mem:
            kinds = {self.prog.ops[i][0] for i in mem}
            raise acir_fe.Unsupported(f"unresolved memory ops in residual: {kinds}")
        for poly in asserts.values():
            ff.A(ff.eq(ff.expr(_poly_terms(poly)), ff.zero))
        for poly, bits in ranges.values():
            ff.bits(ff.expr(_poly_terms(poly)), bits)
        self._encoded = True

    def word(self, w):
        return self.ff.c(self.state.val[w]) if w in self.state.val else self.ff.var(w)

    def blet(self, expr):
        ff = self.ff
        ff.n += 1
        nm = f"b{ff.n}"
        ff.lines.append(f"(define-fun {nm} () Bool {expr})")
        return nm

    def kind_eq(self, words, i, k):
        return self.ff.eq(self.word(words[i]), self.ff.c(k))

    # ---- symbolic record walk -----------------------------------------------
    def walk(self, words):
        """Symbolic record walk over a stream. Returns (start[], revert, burns, mints).

        Supports a uniform record stride (every kind the same length), matching the synthetic fixed-stride grammar
        and the authored consumer's constant-step scan. Variable-length grammars are not yet supported here.
        burns/mints carry (slot, present_bool, ...terms). `revert` is true when a reachable record has an invalid
        kind or overruns the array (the consumer reverts, committing nothing)."""
        ff, g, n = self.ff, self.pol.grammar, self.pol.n
        L = g.uniform
        if L is None:
            raise acir_fe.Unsupported("non-uniform record stride not supported in D1-03")
        valid = sorted(g.lengths)
        # Record starts are 0, L, 2L, ... while within bounds and no earlier record reverted.
        starts = list(range(0, n - L + 1, L))
        tail_overrun = n % L != 0  # a trailing partial record would be read out of bounds
        prefix_ok = ff.T  # all earlier records had a valid kind
        start_flag, rev_terms, burns, mints = {}, [], [], []
        for i in starts:
            start_flag[i] = prefix_ok
            ki = self.word(words[i])
            valid_here = ff.OR(*[ff.eq(ki, ff.c(k)) for k in valid])
            rev_terms.append(self.blet(ff.AND(prefix_ok, ff.NOT(valid_here))))
            is_burn = self.blet(ff.AND(prefix_ok, self.kind_eq(words, i, g.burn_kind)))
            burns.append((i, is_burn, self.word(words[i + g.burn_value_offset]),
                          self.word(words[i + g.burn_recipient_offset])))
            is_mint = self.blet(ff.AND(prefix_ok, self.kind_eq(words, i, g.mint_kind)))
            mints.append((i, is_mint, self.word(words[i + g.mint_id_offset])))
            prefix_ok = self.blet(ff.AND(prefix_ok, valid_here))
        revert = self.blet(ff.OR(*rev_terms)) if (rev_terms or not tail_overrun) else ff.T
        if tail_overrun:
            revert = ff.T  # a stream whose length is not a multiple of the stride always reverts
        return start_flag, revert, burns, mints

    # ---- goals ---------------------------------------------------------------
    def _solve(self, assertion, smt_path):
        ff = self.ff
        saved = list(ff.lines)
        ff.A(assertion)
        getv = [f"w{w}" for w in sorted(set(self.msg_w) | set(self.perm_w)) if w in ff.w]
        status, out, secs = ff.solve(getv, smt_path)
        model = {}
        if status == "sat":
            vals = ff.parse_vals(out)
            model = {int(name[1:]): v % P for name, v in zip(getv, vals)}
        rec = dict(ff.solver_record)
        ff.lines = saved
        return status, model, secs, rec

    def auth_unmatched(self, smt_dir):
        """Probe each slot as a committed burn with no matching certified burn. Returns (status, info)."""
        ff = self.M
        f = self.ff
        _, rev_m, burns_m, _ = self.walk(self.msg_w)
        start_a, rev_a, burns_a, _ = self.walk(self.perm_w)
        results = []
        for (i, is_burn_m, val_m, recip_m) in burns_m:
            matches = [f.AND(bj, f.eq(va, val_m), f.eq(ra, recip_m)) for (_, bj, va, ra) in burns_a]
            unmatched = f.AND(*[f.NOT(mm) for mm in matches]) if matches else f.T
            material = f.ne(val_m, f.zero)  # a zero-value transfer commits no observable effect
            goal = f.AND(f.NOT(rev_m), f.NOT(rev_a), is_burn_m, material, unmatched)
            status, model, secs, rec = self._solve(goal, f"{smt_dir}/auth_unmatched_slot{i}.smt2" if smt_dir else None)
            results.append({"slot": i, "status": status, "seconds": round(secs, 2),
                            "timed_out": rec.get("timed_out"), "model": model})
            if status == "sat":
                return "sat", {"slot": i, "model": model, "probes": results}
            if status == "unknown":
                return "unknown", {"probes": results}
        return "unsat", {"probes": results}

    def cov_unmatched(self, smt_dir):
        f = self.ff
        _, rev_m, burns_m, _ = self.walk(self.msg_w)
        _, rev_a, burns_a, _ = self.walk(self.perm_w)
        results = []
        for (j, is_burn_a, val_a, recip_a) in burns_a:
            matches = [f.AND(bm, f.eq(vm, val_a), f.eq(rm, recip_a)) for (_, bm, vm, rm) in burns_m]
            unmatched = f.AND(*[f.NOT(mm) for mm in matches]) if matches else f.T
            goal = f.AND(f.NOT(rev_m), f.NOT(rev_a), is_burn_a, unmatched)
            status, model, secs, rec = self._solve(goal, f"{smt_dir}/cov_unmatched_slot{j}.smt2" if smt_dir else None)
            results.append({"slot": j, "status": status, "seconds": round(secs, 2), "timed_out": rec.get("timed_out")})
            if status == "sat":
                return "sat", {"slot": j, "model": model, "probes": results}
            if status == "unknown":
                return "unknown", {"probes": results}
        return "unsat", {"probes": results}

    def nonvacuity(self, smt_dir):
        f = self.ff
        _, rev_m, burns_m, mints_m = self.walk(self.msg_w)
        effects = [b for (_, b, _, _) in burns_m] + [b for (_, b, _) in mints_m]
        goal = f.AND(f.NOT(rev_m), f.OR(*effects)) if effects else f.Fa
        status, model, secs, rec = self._solve(goal, f"{smt_dir}/nonvacuity.smt2" if smt_dir else None)
        return status, {"model": model, "seconds": round(secs, 2), "timed_out": rec.get("timed_out")}


def prepare(acir_path, program_json, policy, fixed):
    prog = acir_fe.load(acir_path, program_json)
    state = pr.State(prog.ops, fixed).run()
    return prog, state
