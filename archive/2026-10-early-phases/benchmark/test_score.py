import unittest

from benchmark.score import score


RULES = {"finding_pattern_map": {"A_REPLAY_KEY_UNBOUND": "P3"},
         "excluded_finding_codes": ["A_FOUNDRY_POLICY_COUNTEREXAMPLE"]}
CASE = {"id": "EXAMPLE", "origin": "synthetic", "family": "replay", "label_status": "AI-PROPOSED",
        "expected_state": "vulnerable", "expected_pattern": "P3",
        "expected_location_regex": r"^contracts/Consumer\.sol(:[0-9]+)?$"}


def observation(**changes):
    value = {"tool": "A", "side": "selected", "run_status": "completed", "verdict": "VIOLATION",
             "findings": [{"code": "A_REPLAY_KEY_UNBOUND",
                           "location": {"path": "contracts/Consumer.sol", "line": 40}}]}
    value.update(changes)
    return value


class ScoringRulesTest(unittest.TestCase):
    def test_pattern_and_location_required(self):
        self.assertEqual(score(CASE, observation(), RULES)["outcome"], "DETECT")
        self.assertEqual(score(CASE, observation(findings=[{"code": "A_REPLAY_KEY_UNBOUND",
            "location": {"path": "other.sol", "line": 40}}]), RULES)["outcome"], "MISS")
        self.assertEqual(score(CASE, observation(findings=[{"code": "OTHER",
            "location": {"path": "contracts/Consumer.sol", "line": 40}}]), RULES)["outcome"], "MISS")
        self.assertEqual(score(CASE, observation(findings=[{"code": "A_REPLAY_KEY_UNBOUND",
            "evidence_grade": "E0", "location": {"path": "contracts/Consumer.sol", "line": 40}}]), RULES)["outcome"], "MISS")

    def test_repaired_alarm_and_clean(self):
        fixed = dict(CASE, expected_state="repaired")
        self.assertEqual(score(fixed, observation(), RULES)["outcome"], "FALSE-ALARM")
        self.assertEqual(score(fixed, observation(verdict="VERIFIED_WITHIN_SCOPE", findings=[]), RULES)["outcome"], "CLEAR")

    def test_unavailable_and_pending_are_unknown(self):
        self.assertEqual(score(CASE, observation(run_status="TIMEOUT"), RULES)["outcome"], "UNKNOWN")
        self.assertEqual(score(CASE, observation(verdict="UNKNOWN"), RULES)["outcome"], "UNKNOWN")
        self.assertEqual(score(dict(CASE, label_status="PENDING"), observation(), RULES)["outcome"], "UNKNOWN")

    def test_unsafe_certification_is_separate(self):
        row = score(CASE, observation(verdict="VERIFIED_WITHIN_SCOPE", findings=[]), RULES)
        self.assertEqual(row["outcome"], "MISS")
        self.assertTrue(row["unsafe_certification"])


if __name__ == "__main__": unittest.main()
