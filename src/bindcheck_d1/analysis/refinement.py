"""Consumer-directed abstraction-refinement (CEGAR) for joint producer/consumer analysis.

Starts with a consumer-only abstract model (no ACIR producer constraints), solves authorization
goals, concretizes SAT candidates against the full producer constraints, and refines the abstract
model by adding relevant ACIR constraints when candidates are spurious.
"""
from collections import defaultdict
from pathlib import Path

from ..frontends import acir as acir_fe
from . import propagate as pr
from .joint import JointEncoder, _ff_module


def _poly_terms(poly):
    return [(c, list(m)) for m, c in poly.items()]


class RefinementEngine:
    """CEGAR engine: abstract → solve → concretize → refine → repeat."""

    def __init__(self, program, state, policy, timeout_ms):
        self.prog = program
        self.state = state
        self.pol = policy
        self.timeout_ms = timeout_ms

        asserts, ranges, mem = state.residual()
        if mem:
            kinds = {program.ops[i][0] for i in mem}
            raise acir_fe.Unsupported(f"unresolved memory ops: {kinds}")
        self.all_asserts = asserts
        self.all_ranges = ranges
        self._build_index()
        self.included_asserts = set()
        self.included_ranges = set()
        self.log = []

    def _build_index(self):
        self.w2a = defaultdict(set)
        self.w2r = defaultdict(set)
        for k, poly in self.all_asserts.items():
            for w in pr.unknowns(poly):
                self.w2a[w].add(k)
        for k, (poly, bits) in self.all_ranges.items():
            for w in pr.unknowns(poly):
                self.w2r[w].add(k)

    def constraint_counts(self):
        return {
            "included_asserts": len(self.included_asserts),
            "included_ranges": len(self.included_ranges),
            "total_asserts": len(self.all_asserts),
            "total_ranges": len(self.all_ranges),
        }

    def _make_abstract_encoder(self):
        """JointEncoder with only the currently included ACIR constraints."""
        enc = JointEncoder(self.prog, self.state, self.pol, self.timeout_ms)
        ff = enc.ff
        for k in self.included_asserts:
            poly = self.all_asserts[k]
            ff.A(ff.eq(ff.expr(_poly_terms(poly)), ff.zero))
        for k in self.included_ranges:
            poly, bits = self.all_ranges[k]
            ff.bits(ff.expr(_poly_terms(poly)), bits)
        return enc

    def concretize(self, model, smt_path):
        """Check if model values are consistent with full ACIR constraints.

        Returns (status, seconds, solver_record). Status 'sat' means the candidate
        is real (the producer can generate these values); 'unsat' means spurious.
        """
        M = _ff_module()
        ff = M.FF(self.timeout_ms)
        for poly in self.all_asserts.values():
            ff.A(ff.eq(ff.expr(_poly_terms(poly)), ff.zero))
        for poly, bits in self.all_ranges.values():
            ff.bits(ff.expr(_poly_terms(poly)), bits)
        for w, v in model.items():
            ff.A(ff.eq(ff.var(w), ff.c(v)))
        status, out, secs = ff.solve([], str(smt_path))
        return status, secs, dict(ff.solver_record)

    def refine(self, model):
        """Add ACIR constraints relevant to the model's witnesses (+ one transitive hop).

        Returns the number of newly added constraints.
        """
        witnesses = set(model.keys())
        new_a, new_r = set(), set()
        for w in witnesses:
            new_a |= self.w2a.get(w, set())
            new_r |= self.w2r.get(w, set())
        extra_w = set()
        for k in new_a:
            extra_w |= pr.unknowns(self.all_asserts[k])
        for k in new_r:
            poly, _ = self.all_ranges[k]
            extra_w |= pr.unknowns(poly)
        for w in extra_w:
            new_a |= self.w2a.get(w, set())
            new_r |= self.w2r.get(w, set())
        added = len(new_a - self.included_asserts) + len(new_r - self.included_ranges)
        self.included_asserts |= new_a
        self.included_ranges |= new_r
        return added

    def auth_unmatched_refine(self, smt_dir, max_iters=10):
        """CEGAR loop for auth_unmatched.

        Returns (status, info) where status is 'sat'/'unsat'/'unknown' and info
        contains the refinement log, iteration count, and (for sat) the model.
        """
        smt_dir = Path(smt_dir)
        smt_dir.mkdir(parents=True, exist_ok=True)
        for it in range(max_iters):
            iter_dir = smt_dir / f"iter{it}"
            iter_dir.mkdir(parents=True, exist_ok=True)

            enc = self._make_abstract_encoder()
            a_status, a_info = enc.auth_unmatched(str(iter_dir))

            entry = {"iteration": it, "abstract_status": a_status,
                     **self.constraint_counts()}

            if a_status == "unsat":
                entry["result"] = "VERIFIED"
                if "probes" in a_info:
                    entry["abstract_probes"] = len(a_info["probes"])
                self.log.append(entry)
                return "unsat", {"iterations": it + 1, "log": self.log,
                                 "probes": a_info.get("probes", [])}

            if a_status == "unknown":
                entry["result"] = "UNKNOWN"
                self.log.append(entry)
                return "unknown", {"iterations": it + 1, "log": self.log}

            model = a_info["model"]
            slot = a_info.get("slot")
            c_path = iter_dir / "concretize.smt2"
            c_status, c_secs, c_rec = self.concretize(model, c_path)

            entry["candidate_slot"] = slot
            entry["concretize_status"] = c_status
            entry["concretize_seconds"] = round(c_secs, 2)

            if c_status == "sat":
                entry["result"] = "CONFIRMED_VIOLATION"
                self.log.append(entry)
                return "sat", {"slot": slot, "model": model,
                               "iterations": it + 1, "log": self.log}

            if c_status == "unknown":
                entry["result"] = "CONCRETIZE_UNKNOWN"
                self.log.append(entry)
                return "unknown", {"iterations": it + 1, "log": self.log}

            added = self.refine(model)
            entry["spurious"] = True
            entry["refined_added"] = added
            self.log.append(entry)

            if added == 0:
                prev_total = len(self.included_asserts) + len(self.included_ranges)
                self.included_asserts = set(self.all_asserts.keys())
                self.included_ranges = set(self.all_ranges.keys())
                new_total = len(self.included_asserts) + len(self.included_ranges)
                if new_total == prev_total:
                    return "unknown", {"error": "all constraints included, still spurious",
                                       "iterations": it + 1, "log": self.log}

        return "unknown", {"error": "max iterations", "iterations": max_iters,
                           "log": self.log}
