#!/usr/bin/env python3
"""Synthetic soundness regressions only; no Payy/transfer cases are loaded.

Run with CVC5 pointing to the pinned finite-field build. Uses the real solver.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t22_v3_tailspec as T


def ir(text):
    return T.Acir(text)


def w(n):
    return [(1, [n])]


class SoundnessChecks(unittest.TestCase):
    def probe(self, text, messages):
        return T.probe_query(ir(text), messages, [([w(2)], w(0))], 10)

    def test_implied_goal_zero_is_unsat(self):
        result = self.probe("ASSERT 0 = w1 - w0*w1", [w(1)])
        self.assertEqual(result[0], "unsat")
        slot = result[5]["slots"][0]
        self.assertEqual(slot["original_goal_implied"], {"1": 0})
        self.assertEqual(slot["goal_after"], [])

    def test_nonzero_implied_goal_is_preserved(self):
        result = self.probe("ASSERT 0 = w1 - w0 - 7", [w(1)])
        self.assertEqual(result[0], "sat")
        self.assertEqual(result[5]["message_value"], 7)
        self.assertTrue(result[5]["sat_audit_passed"])

    def test_later_unchecked_slot_is_visited(self):
        result = self.probe("ASSERT 0 = w1 - w0*w1", [w(1), w(3)])
        self.assertEqual(result[0], "sat")
        self.assertEqual([s["solver"] for s in result[5]["slots"]], ["unsat", "sat"])
        self.assertEqual(result[5]["message_index"], 1)
        self.assertEqual(result[5]["goal_witnesses_in_implied"], [])

    def test_recomponentization_excludes_disconnected_range(self):
        a = ir("ASSERT 0 = w1*w2 - w0\nBLACKBOX::RANGE input: w1, bits: 3\n"
               "ASSERT 0 = w3*w4 - w0\nBLACKBOX::RANGE input: w3, bits: 3")
        reduced, selected, witnesses, fixed = T._specialize_probe_component(
            a, list(range(len(a.ops))), {0: 0}, {2})
        self.assertTrue(selected)
        self.assertIn(2, witnesses)
        self.assertNotIn(3, witnesses)
        self.assertNotIn(4, witnesses)

    def test_infeasible_premise_still_issues_general_queries(self):
        abi = {"parameters": [{"name": name, "type": {"kind": "field"}, "visibility": "private"}
                              for name in ("active", "message", "word")]}
        spec = {"messages": "abi:message", "streams": [{"source": "abi:word",
                "active_if_nonzero": "abi:active"}], "derivation": {"mode": "nonzero"}}
        result = T.run(spec, "ASSERT 0 = w0*w3 - 1", abi, 10)
        self.assertTrue(result["queries"]["probe"]["details"]["premise_infeasible"])
        self.assertEqual(set(result["queries"]), {"probe", "nonvacuous", "prefix", "tail"})
        # Active stream with word=0 permits L=0, despite impossible all-inactive premise.
        self.assertEqual(result["queries"]["tail"]["solver"], "sat")

    def test_blackbox_output_cannot_be_pruned_as_solvable(self):
        a = ir("BLACKBOX::OPAQUE outputs: [w2]\nASSERT 0 = w1 - w2")
        selected, witnesses = T.cone(a, {1})
        self.assertIn(1, selected)
        self.assertIn(2, witnesses)
        result = self.probe("BLACKBOX::OPAQUE outputs: [w2]\nASSERT 0 = w1 - w2", [w(1)])
        self.assertEqual(result[0], "unknown")
        self.assertIn("BLACKBOX::OPAQUE", result[5]["slots"][0]["unmodeled_blackboxes"])

    def test_unsubstituted_and_specialized_queries_agree(self):
        # Hand-selected independent equations exercise zero, nonzero, alias,
        # inverse and quadratic constraints. Compare to the original assertions,
        # without cone reduction or constant discovery.
        for text in ("ASSERT 0 = w1", "ASSERT 0 = w1 - 9",
                     "ASSERT 0 = w1 - w2\nASSERT 0 = w2",
                     "ASSERT 0 = w1*w2 - 1", "ASSERT 0 = w1*w1"):
            with self.subTest(text=text):
                a = ir(text)
                ff = T.FF(10000)
                T.encode(ff, a, list(range(len(a.ops))))
                ff.A(ff.eq(ff.var(0), ff.zero))
                ff.A(ff.ne(ff.var(1), ff.zero))
                original = ff.solve([ff.var(1)])[0]
                specialized = self.probe(text, [w(1)])[0]
                self.assertIn(original, ("sat", "unsat"))
                self.assertEqual(original, specialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
