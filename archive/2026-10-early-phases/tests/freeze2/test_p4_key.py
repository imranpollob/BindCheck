"""Freeze-2 regression controls for P4 verification-key checks.

The freeze-1 BN254_G2 constant was off the curve (a dropped digit group), so the
default-key branch could never match real snarkjs output, and the VERIFIED rule
only rejected gamma == delta when both equalled that wrong constant.
"""
from __future__ import annotations

import pathlib
import unittest

from bindcheck_zk.p4 import BN254_G2, analyze_source

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
Q = 21888242871839275222246405745257275088696311157297823662689037894645226208583


def _mul(a, b):
    return ((a[0] * b[0] - a[1] * b[1]) % Q, (a[0] * b[1] + a[1] * b[0]) % Q)


def _on_twist(x1, x0, y1, y0) -> bool:
    inv = pow(82, Q - 2, Q)
    b2 = _mul((3, 0), (9 * inv % Q, (-inv) % Q))  # 3 / (9 + u)
    x, y = (x0, x1), (y0, y1)
    rhs = _mul(_mul(x, x), x)
    return _mul(y, y) == ((rhs[0] + b2[0]) % Q, (rhs[1] + b2[1]) % Q)


class P4KeyRegression(unittest.TestCase):
    def test_generator_constant_is_on_curve(self):
        self.assertTrue(_on_twist(*BN254_G2))

    def test_generator_matches_real_snarkjs_gamma(self):
        text = (FIXTURES / "snarkjs_0001_contributed_key.sol").read_text()
        for value in BN254_G2:
            self.assertIn(str(value), text)

    def test_real_snarkjs_default_key_is_violation(self):
        out = analyze_source((FIXTURES / "snarkjs_0000_default_key.sol").read_text(), "default.sol")
        self.assertEqual(out["gamma"], BN254_G2)
        self.assertEqual(out["finding"]["verdict"], "VIOLATION")
        self.assertEqual(out["finding"]["reason"], "GAMMA_EQUALS_DELTA_SOURCE_KEY")

    def test_real_snarkjs_contributed_key_is_verified(self):
        out = analyze_source((FIXTURES / "snarkjs_0001_contributed_key.sol").read_text(), "contributed.sol")
        self.assertNotEqual(out["gamma"], out["delta"])
        self.assertEqual(out["finding"]["verdict"], "VERIFIED_WITHIN_SCOPE")

    def test_non_generator_equal_gamma_delta_is_violation(self):
        text = (FIXTURES / "snarkjs_0001_contributed_key.sol").read_text()
        lines = text.splitlines()
        delta = {}
        for line in lines:
            for name in ("deltax1", "deltax2", "deltay1", "deltay2"):
                if f"constant {name} " in line:
                    delta[name] = line.split("=")[1].strip().rstrip(";")
        for g, d in (("gammax1", "deltax1"), ("gammax2", "deltax2"), ("gammay1", "deltay1"), ("gammay2", "deltay2")):
            lines = [
                f"    uint256 constant {g} = {delta[d]};" if f"constant {g} " in line else line
                for line in lines
            ]
        out = analyze_source("\n".join(lines), "equal.sol")
        self.assertNotEqual(out["gamma"], BN254_G2)
        self.assertEqual(out["finding"]["verdict"], "VIOLATION")
        self.assertEqual(out["finding"]["reason"], "GAMMA_EQUALS_DELTA_SOURCE_KEY")


if __name__ == "__main__":
    unittest.main()
