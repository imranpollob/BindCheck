import hashlib
import json
from pathlib import Path

import pytest

from bindcheck_d1.joint_warptoad import BACKEND_OPTIONS, encode_query


ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "results/raw/D1P-17/inputs"


def omega(name: str):
    return json.loads((INPUTS / name).read_text())


def test_backend_options_are_exactly_declared_and_mutually_exclusive():
    assert BACKEND_OPTIONS == {"BASE", "T-ARITH", "T-OVF"}
    with pytest.raises(ValueError, match="unknown backend option"):
        encode_query(omega("omega-auth1.json"), drop_producer=True,
                     backend_option="T-ARITH+T-OVF")


def test_base_generation_remains_byte_identical_to_frozen_d1p14c_q1():
    query, certificate = encode_query(
        omega("omega-auth1.json"), drop_producer=True, backend_option="BASE",
    )
    assert hashlib.sha256(query).hexdigest() == "a188b4a155b41b92a2531d0ae7c92593baaaf373f64f61068c739c66d2a5fa2b"
    assert certificate["backend_option"] == "BASE"


def test_t_arith_frees_only_fee_value_and_keeps_success_guards():
    query, certificate = encode_query(
        omega("omega-auth1.json"), drop_producer=True, backend_option="T-ARITH",
    )
    text = query.decode()
    assert "(declare-const fee_amount (_ BitVec 256))" in text
    assert "(define-fun fee_amount" not in text
    assert "(define-fun fee_branch () Bool (not (= pi6 (_ bv0 256))))" in text
    assert "(assert (=> fee_branch (bvuge (bvadd basefee pi7) basefee)))" in text
    assert "((_ extract 511 256) (bvmul ((_ zero_extend 256) pi6)" in text
    assert "(assert (=> fee_branch (bvule fee_amount pi8)))" in text
    assert "(assert (=> fee_branch (bvule fee_amount pi2)))" in text
    assert "every concrete successful execution" in certificate["preservation_argument"]


def test_t_ovf_changes_only_overflow_predicates():
    base, _ = encode_query(omega("omega-auth1.json"), drop_producer=True,
                           backend_option="BASE")
    transformed, certificate = encode_query(
        omega("omega-auth1.json"), drop_producer=True, backend_option="T-OVF",
    )
    text = transformed.decode()
    assert "(define-fun fee_amount () (_ BitVec 256) (bvmul pi6 fee_base))" in text
    assert "(not (bvuaddo basefee pi7))" in text
    assert "(not (bvumulo pi6 fee_base))" in text
    assert "((_ extract 511 256) (bvmul ((_ zero_extend 256) pi6)" not in text
    normalized = text.replace("; D1P-17 backend_option=T-OVF\n", "").replace(
        "; BACKEND_OPTION T-OVF\n", ""
    ).replace("(not (bvuaddo basefee pi7))", "(bvuge (bvadd basefee pi7) basefee)").replace(
        "(not (bvumulo pi6 fee_base))",
        "(= ((_ extract 511 256) (bvmul ((_ zero_extend 256) pi6) ((_ zero_extend 256) fee_base))) (_ bv0 256))",
    )
    assert normalized.encode() == base
    assert "unsigned w-bit" in certificate["overflow_identity"]


@pytest.mark.parametrize("backend", ["T-ARITH", "T-OVF"])
def test_each_backend_is_available_to_all_three_later_query_arms(backend):
    auth = omega("omega-auth1.json")
    nonvac = omega("omega-nonvac1.json")
    cases = [(auth, True), (auth, False), (nonvac, False)]
    for value, dropped in cases:
        query, certificate = encode_query(
            value, drop_producer=dropped, backend_option=backend,
        )
        assert query
        assert certificate["backend_option"] == backend
