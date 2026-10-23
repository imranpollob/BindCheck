"""D1-03 regression tests on synthetic fixtures.

Tests the analyzer pipeline end-to-end against the authored faulty/repaired producers
with the uniform 3-word record grammar. These are deterministic: the solver models and
nargo replays must match the D1-03 evidence record.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bindcheck_d1 import P
from bindcheck_d1.artifacts import sha256_file
from bindcheck_d1.frontends import acir as acir_fe
from bindcheck_d1.analysis import propagate as pr
from bindcheck_d1.analysis import joint
from bindcheck_d1.policy import Policy

NARGO = ROOT / "tools/noir-1.0.0-beta.14/nargo"
CVC5 = ROOT / "tools/cvc5-1.4.2-gpl/bin/cvc5"
CASES = ROOT / "cases/d1/synth"
TIMEOUT_MS = 60_000

os.environ["CVC5"] = str(CVC5)

# ---- helpers ----------------------------------------------------------------

def get_acir_text(producer_dir):
    r = subprocess.run([str(NARGO), "compile", "--program-dir", str(producer_dir), "--print-acir"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"nargo compile failed: {r.stderr}"
    return r.stdout


def load_program(producer_dir, acir_text):
    acir_path = producer_dir / "target" / "acir.txt"
    acir_path.write_text(acir_text)
    jsons = list((producer_dir / "target").glob("*.json"))
    assert len(jsons) == 1
    return acir_fe.load(str(acir_path), str(jsons[0]))


def nargo_replay_model(producer_dir, prog, model, tmp_path):
    prover_path = tmp_path / "Prover.toml"
    auth_ws = prog.table["authorized"]
    msg_ws = prog.table["messages"]
    auth_strs = [f'"0x{model.get(w, 0):x}"' for w in auth_ws]
    msg_strs = [f'"0x{model.get(w, 0):x}"' for w in msg_ws]
    prover_path.write_text(f"authorized = [{', '.join(auth_strs)}]\nmessages = [{', '.join(msg_strs)}]\n")
    target_prover = producer_dir / "Prover.toml"
    target_prover.write_text(prover_path.read_text())
    try:
        r = subprocess.run([str(NARGO), "execute", "--program-dir", str(producer_dir)],
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0, r.stderr
    finally:
        if target_prover.exists():
            target_prover.unlink()


# ---- fixtures ---------------------------------------------------------------

@pytest.fixture(scope="module")
def policy():
    return Policy.load(str(CASES / "policy.json"))


@pytest.fixture(scope="module")
def faulty_program():
    acir = get_acir_text(CASES / "producer_faulty")
    return load_program(CASES / "producer_faulty", acir)


@pytest.fixture(scope="module")
def repaired_program():
    acir = get_acir_text(CASES / "producer_repaired")
    return load_program(CASES / "producer_repaired", acir)


# ---- ACIR structure tests ---------------------------------------------------

class TestACIRStructure:
    def test_faulty_opcode_counts(self, faulty_program):
        ops = faulty_program.ops
        assert sum(1 for o in ops if o[0] == "assert") == 26
        assert sum(1 for o in ops if o[0] == "brillig") == 3
        assert sum(1 for o in ops if o[0] == "range") == 0

    def test_repaired_opcode_counts(self, repaired_program):
        ops = repaired_program.ops
        assert sum(1 for o in ops if o[0] == "assert") == 35
        assert sum(1 for o in ops if o[0] == "brillig") == 3
        assert sum(1 for o in ops if o[0] == "range") == 0

    def test_witness_layout(self, faulty_program):
        assert faulty_program.private == list(range(9))
        assert faulty_program.public == list(range(9, 18))
        assert faulty_program.table["authorized"] == list(range(9))
        assert faulty_program.table["messages"] == list(range(9, 18))

    def test_no_recursion(self, faulty_program, repaired_program):
        assert len(faulty_program.recursions) == 0
        assert len(repaired_program.recursions) == 0


# ---- policy tests -----------------------------------------------------------

class TestPolicy:
    def test_uniform_stride(self, policy):
        assert policy.grammar.uniform == 3
        assert policy.n == 9

    def test_grammar_kinds(self, policy):
        assert policy.grammar.burn_kind == 3
        assert policy.grammar.mint_kind == 2
        assert policy.grammar.pad_kind == 0

    def test_field_offsets(self, policy):
        assert policy.grammar.burn_value_offset == 1
        assert policy.grammar.burn_recipient_offset == 2
        assert policy.grammar.mint_id_offset == 1


# ---- propagation tests ------------------------------------------------------

class TestPropagation:
    def test_faulty_all_residual(self, faulty_program):
        state = pr.State(faulty_program.ops, {}).run()
        asserts, ranges, mem = state.residual()
        assert len(state.val) == 0
        assert len(asserts) == 26
        assert len(ranges) == 0
        assert len(mem) == 0

    def test_repaired_all_residual(self, repaired_program):
        state = pr.State(repaired_program.ops, {}).run()
        asserts, ranges, mem = state.residual()
        assert len(state.val) == 0
        assert len(asserts) == 35
        assert len(ranges) == 0


# ---- joint encoder / goal tests --------------------------------------------

class TestFaultyGoals:
    @pytest.fixture(scope="class")
    def encoder(self, faulty_program, policy, tmp_path_factory):
        state = pr.State(faulty_program.ops, {}).run()
        smt_dir = tmp_path_factory.mktemp("smt_faulty")
        enc = joint.JointEncoder(faulty_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        return enc, str(smt_dir)

    def test_auth_unmatched_sat(self, encoder):
        enc, smt_dir = encoder
        status, info = enc.auth_unmatched(smt_dir)
        assert status == "sat", f"expected SAT, got {status}"
        model = info["model"]
        assert all(model.get(w, 0) == 0 for w in range(9)), "authorized stream should be all zeros"
        msgs = [model.get(w, 0) for w in range(9, 18)]
        assert msgs[0] == 3, "first message record should be a burn (kind=3)"
        assert msgs[1] != 0, "burn value should be nonzero (material condition)"


class TestRepairedGoals:
    @pytest.fixture(scope="class")
    def auth_result(self, repaired_program, policy, tmp_path_factory):
        state = pr.State(repaired_program.ops, {}).run()
        smt_dir = tmp_path_factory.mktemp("smt_repaired_auth")
        enc = joint.JointEncoder(repaired_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        return enc.auth_unmatched(str(smt_dir))

    @pytest.fixture(scope="class")
    def cov_result(self, repaired_program, policy, tmp_path_factory):
        state = pr.State(repaired_program.ops, {}).run()
        smt_dir = tmp_path_factory.mktemp("smt_repaired_cov")
        enc = joint.JointEncoder(repaired_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        return enc.cov_unmatched(str(smt_dir))

    @pytest.fixture(scope="class")
    def nonvac_result(self, repaired_program, policy, tmp_path_factory):
        state = pr.State(repaired_program.ops, {}).run()
        smt_dir = tmp_path_factory.mktemp("smt_repaired_nonvac")
        enc = joint.JointEncoder(repaired_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        return enc.nonvacuity(str(smt_dir))

    def test_auth_unmatched_unsat(self, auth_result):
        status, _ = auth_result
        assert status == "unsat"

    def test_cov_unmatched_unsat(self, cov_result):
        status, _ = cov_result
        assert status == "unsat"

    def test_nonvacuity_sat(self, nonvac_result):
        status, info = nonvac_result
        assert status == "sat"
        model = info["model"]
        msgs = [model.get(w, 0) for w in range(9, 18)]
        assert any(m != 0 for m in msgs), "nonvacuity witness must have active records"


# ---- nargo replay tests -----------------------------------------------------

class TestReplay:
    def test_faulty_violation_replay(self, faulty_program, policy, tmp_path):
        """VIOLATION model from AUTH-UNMATCHED must pass nargo execute on the faulty circuit."""
        state = pr.State(faulty_program.ops, {}).run()
        enc = joint.JointEncoder(faulty_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        smt_dir = tmp_path / "smt"
        smt_dir.mkdir()
        status, info = enc.auth_unmatched(str(smt_dir))
        assert status == "sat"
        ok, err = nargo_replay_model(CASES / "producer_faulty", faulty_program, info["model"], tmp_path)
        assert ok, f"nargo replay failed: {err}"

    def test_repaired_nonvacuity_replay(self, repaired_program, policy, tmp_path):
        """Non-vacuity witness must pass nargo execute on the repaired circuit."""
        state = pr.State(repaired_program.ops, {}).run()
        enc = joint.JointEncoder(repaired_program, state, policy, TIMEOUT_MS)
        enc.encode_producer()
        smt_dir = tmp_path / "smt"
        smt_dir.mkdir()
        status, info = enc.nonvacuity(str(smt_dir))
        assert status == "sat"
        ok, err = nargo_replay_model(CASES / "producer_repaired", repaired_program, info["model"], tmp_path)
        assert ok, f"nargo replay failed: {err}"
