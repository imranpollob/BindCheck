"""D1-05 regression tests: consumer-directed abstraction-refinement (CEGAR).

Tests the CEGAR mechanism on synthetic fixtures: abstract → concretize → refine → repeat.
These tests require CVC5 and nargo; skip if unavailable.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

NARGO = ROOT / "tools/noir-1.0.0-beta.14/nargo"
CVC5 = Path(os.environ.get("CVC5", ROOT / "tools/cvc5-1.4.2-gpl/bin/cvc5"))
CASES = ROOT / "cases/d1/synth"
SKIP = not (NARGO.exists() and CVC5.exists())
TIMEOUT_MS = 60_000


def _load(case_name):
    from bindcheck_d1.frontends import acir as acir_fe
    from bindcheck_d1.analysis import propagate as pr
    from bindcheck_d1.policy import Policy
    producer_dir = CASES / case_name
    target = producer_dir / "target"
    jsons = list(target.glob("*.json"))
    acir_path = Path(f"/tmp/d1_05_test_{case_name}_acir.txt")
    r = subprocess.run([str(NARGO), "compile", "--program-dir", str(producer_dir), "--print-acir"],
                       capture_output=True, text=True, timeout=60)
    acir_path.write_text(r.stdout)
    prog = acir_fe.load(str(acir_path), str(jsons[0]))
    pol = Policy.load(str(CASES / "policy.json"))
    state = pr.State(prog.ops, {}).run()
    return prog, state, pol


@unittest.skipIf(SKIP, "CVC5 or nargo not available")
class TestRefinementEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("CVC5", str(CVC5))
        cls.prog_f, cls.state_f, cls.pol = _load("producer_faulty")
        cls.prog_r, cls.state_r, _ = _load("producer_repaired")

    def _engine(self, prog, state):
        from bindcheck_d1.analysis.refinement import RefinementEngine
        return RefinementEngine(prog, state, self.pol, TIMEOUT_MS)

    def test_initial_abstraction_has_no_constraints(self):
        eng = self._engine(self.prog_f, self.state_f)
        self.assertEqual(eng.included_asserts, set())
        self.assertEqual(eng.included_ranges, set())

    def test_faulty_constraint_count(self):
        eng = self._engine(self.prog_f, self.state_f)
        self.assertEqual(len(eng.all_asserts), 26)
        self.assertEqual(len(eng.all_ranges), 0)

    def test_repaired_constraint_count(self):
        eng = self._engine(self.prog_r, self.state_r)
        self.assertEqual(len(eng.all_asserts), 35)
        self.assertEqual(len(eng.all_ranges), 0)

    def test_witness_index_covers_all_constraints(self):
        eng = self._engine(self.prog_f, self.state_f)
        indexed = set()
        for keys in eng.w2a.values():
            indexed |= keys
        self.assertEqual(indexed, set(eng.all_asserts.keys()))


@unittest.skipIf(SKIP, "CVC5 or nargo not available")
class TestFaultyCEGAR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("CVC5", str(CVC5))
        cls.prog, cls.state, cls.pol = _load("producer_faulty")
        from bindcheck_d1.analysis.refinement import RefinementEngine
        cls.eng = RefinementEngine(cls.prog, cls.state, cls.pol, TIMEOUT_MS)
        smt_dir = Path("/tmp/d1_05_test_faulty_cegar")
        smt_dir.mkdir(parents=True, exist_ok=True)
        cls.status, cls.info = cls.eng.auth_unmatched_refine(str(smt_dir))

    def test_verdict_is_sat(self):
        self.assertEqual(self.status, "sat")

    def test_has_model(self):
        self.assertIn("model", self.info)
        self.assertTrue(len(self.info["model"]) > 0)

    def test_has_spurious_iteration(self):
        """At least one iteration should have a spurious candidate."""
        spurious = [e for e in self.eng.log if e.get("spurious")]
        self.assertGreaterEqual(len(spurious), 1)

    def test_confirmed_iteration(self):
        """The final iteration should confirm the violation."""
        last = self.eng.log[-1]
        self.assertEqual(last["result"], "CONFIRMED_VIOLATION")

    def test_nargo_replay(self):
        model = self.info["model"]
        out_dir = Path("/tmp/d1_05_test_faulty_replay")
        out_dir.mkdir(parents=True, exist_ok=True)
        auth_ws = self.prog.table["authorized"]
        msg_ws = self.prog.table["messages"]
        auth_strs = [f'"0x{model.get(w, 0):x}"' for w in auth_ws]
        msg_strs = [f'"0x{model.get(w, 0):x}"' for w in msg_ws]
        prover = f"authorized = [{', '.join(auth_strs)}]\nmessages = [{', '.join(msg_strs)}]\n"
        producer_dir = CASES / "producer_faulty"
        prover_path = producer_dir / "Prover.toml"
        prover_path.write_text(prover)
        try:
            r = subprocess.run([str(NARGO), "execute", "--program-dir", str(producer_dir)],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, f"nargo replay failed: {r.stderr[:300]}")
        finally:
            if prover_path.exists():
                prover_path.unlink()


@unittest.skipIf(SKIP, "CVC5 or nargo not available")
class TestRepairedCEGAR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("CVC5", str(CVC5))
        cls.prog, cls.state, cls.pol = _load("producer_repaired")
        from bindcheck_d1.analysis.refinement import RefinementEngine
        cls.eng = RefinementEngine(cls.prog, cls.state, cls.pol, TIMEOUT_MS)
        smt_dir = Path("/tmp/d1_05_test_repaired_cegar")
        smt_dir.mkdir(parents=True, exist_ok=True)
        cls.status, cls.info = cls.eng.auth_unmatched_refine(str(smt_dir))

    def test_verdict_is_unsat(self):
        self.assertEqual(self.status, "unsat")

    def test_has_spurious_iteration(self):
        spurious = [e for e in self.eng.log if e.get("spurious")]
        self.assertGreaterEqual(len(spurious), 1,
                                "Expected at least one spurious candidate on repaired case")

    def test_verified_after_refinement(self):
        last = self.eng.log[-1]
        self.assertEqual(last["result"], "VERIFIED")


@unittest.skipIf(SKIP, "CVC5 or nargo not available")
class TestConcretize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("CVC5", str(CVC5))
        cls.prog_f, cls.state_f, cls.pol = _load("producer_faulty")
        cls.prog_r, cls.state_r, _ = _load("producer_repaired")

    def test_faulty_real_model_is_sat(self):
        """A model from the full faulty encoder should be consistent with full ACIR."""
        from bindcheck_d1.analysis.refinement import RefinementEngine
        from bindcheck_d1.analysis.joint import JointEncoder
        enc = JointEncoder(self.prog_f, self.state_f, self.pol, TIMEOUT_MS)
        enc.encode_producer()
        smt_dir = Path("/tmp/d1_05_test_conc_faulty")
        smt_dir.mkdir(parents=True, exist_ok=True)
        status, info = enc.auth_unmatched(str(smt_dir))
        self.assertEqual(status, "sat")
        eng = RefinementEngine(self.prog_f, self.state_f, self.pol, TIMEOUT_MS)
        c_path = smt_dir / "concretize.smt2"
        c_status, c_secs, c_rec = eng.concretize(info["model"], c_path)
        self.assertEqual(c_status, "sat")

    def test_repaired_abstract_model_is_unsat(self):
        """An abstract model (no ACIR) on repaired should be spurious."""
        from bindcheck_d1.analysis.refinement import RefinementEngine
        from bindcheck_d1.analysis.joint import JointEncoder
        enc = JointEncoder(self.prog_r, self.state_r, self.pol, TIMEOUT_MS)
        smt_dir = Path("/tmp/d1_05_test_conc_repaired")
        smt_dir.mkdir(parents=True, exist_ok=True)
        status, info = enc.auth_unmatched(str(smt_dir))
        self.assertEqual(status, "sat")
        eng = RefinementEngine(self.prog_r, self.state_r, self.pol, TIMEOUT_MS)
        c_path = smt_dir / "concretize.smt2"
        c_status, c_secs, c_rec = eng.concretize(info["model"], c_path)
        self.assertEqual(c_status, "unsat")


@unittest.skipIf(SKIP, "CVC5 or nargo not available")
class TestPreservation(unittest.TestCase):
    """Both CEGAR verdicts match D1-03 verdicts."""

    def test_faulty_verdict_matches_d103(self):
        results_path = ROOT / "results/raw/D1-05/synthetic/synth-faulty/result.json"
        if not results_path.exists():
            self.skipTest("D1-05 results not generated")
        r = json.loads(results_path.read_text())
        self.assertEqual(r["verdict"], "VIOLATION")
        self.assertEqual(r["evidence_grade"], "CONCRETE_MODEL_REPLAYED")

    def test_repaired_verdict_matches_d103(self):
        results_path = ROOT / "results/raw/D1-05/synthetic/synth-repaired/result.json"
        if not results_path.exists():
            self.skipTest("D1-05 results not generated")
        r = json.loads(results_path.read_text())
        self.assertEqual(r["verdict"], "VERIFIED_WITHIN_SCOPE")
        self.assertEqual(r["evidence_grade"], "CONCRETE_MODEL_REPLAYED")
        self.assertEqual(r["nonvacuity"], "SAT_REPLAYED")


if __name__ == "__main__":
    unittest.main()
