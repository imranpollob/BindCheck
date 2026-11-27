import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = load("d1p_06_prepare", ROOT / "scripts/d1p_06_prepare.py")
RUNNER = load("d1p_06_track_a", ROOT / "scripts/d1p_06_track_a.py")


class D1P06PreparationTests(unittest.TestCase):
    def test_goal_only_derivation_excludes_producer_constraints(self):
        specializer = PREPARE.load_specializer()
        parent = specializer.parse_parent("check_added", "prefix")
        data = PREPARE.goal_only_text(parent)
        self.assertEqual(PREPARE.assertion_count(data), 1)
        self.assertNotIn(parent["producer_prefix"], data)
        self.assertIn(parent["walk"].encode("ascii"), data)
        self.assertIn(parent["goal_line"].encode("ascii"), data)

    def test_cone_only_is_exact_prefix_plus_check_sat(self):
        specializer = PREPARE.load_specializer()
        parent = specializer.parse_parent("running_flag", "tail")
        data = PREPARE.cone_only_text(parent)
        self.assertEqual(data, parent["producer_prefix"] + b"(check-sat)\n")
        self.assertEqual(
            PREPARE.assertion_count(data), parent["producer_assertions"]
        )

    def test_manifest_counts_and_every_hash(self):
        manifest, checked = RUNNER.verify_inputs()
        self.assertEqual(checked, 166)
        self.assertEqual(manifest["counts"]["primary_calls_max"], 164)
        self.assertEqual(manifest["counts"]["partitioned_cells"], 150)
        self.assertEqual(
            [group["slot"] for group in manifest["partitioned"]],
            [
                "check_added/nonvacuous", "check_added/prefix", "check_added/tail",
                "running_flag/nonvacuous", "running_flag/prefix", "running_flag/tail",
            ],
        )
        for group in manifest["partitioned"]:
            self.assertEqual([cell["index"] for cell in group["cells"]], list(range(25)))


class D1P06RunnerTests(unittest.TestCase):
    def test_equal_budget_and_sampled_policy_constants(self):
        self.assertEqual(RUNNER.UNSPLIT_SECONDS, 300.0)
        self.assertEqual(RUNNER.PARTITION_SLOT_SECONDS, 300.0)
        self.assertEqual(RUNNER.CELL_SECONDS, 12.0)
        self.assertEqual(RUNNER.PRIMARY_AGGREGATE_SECONDS, 6000.0)
        self.assertEqual(RUNNER.PRIMARY_CALLS_MAX, 164)
        self.assertEqual(RUNNER.RSS_CUTOFF, 4 * 1024**3)
        self.assertEqual(RUNNER.SAMPLE_INTERVAL, 0.05)
        policy = json.loads(RUNNER.RESOURCE_POLICY.read_text())
        self.assertFalse(policy["limitations"]["hard_address_space_cap"])
        self.assertTrue(policy["limitations"]["sampling_can_overshoot_cutoff"])

    def test_result_parser_requires_preserved_sat_payload(self):
        with tempfile.TemporaryDirectory(prefix="d1p06-parser-", dir=ROOT / "results/raw") as directory:
            path = Path(directory) / "stdout"
            path.write_text("sat\n((w0 (as ff0 F)))\n")
            self.assertEqual(RUNNER.parse_result(path), ("sat", True))
            path.write_text("sat\n")
            self.assertEqual(RUNNER.parse_result(path), ("sat", False))
            path.write_text("unsat\n")
            self.assertEqual(RUNNER.parse_result(path), ("unsat", False))
            path.write_text("warning\nsat\n")
            self.assertEqual(RUNNER.parse_result(path), ("malformed", False))

    def test_partition_aggregation_rules(self):
        unsat = [{"attempts": 1, "result": "UNSAT", "elapsed_seconds": 1,
                  "peak_tree_rss_bytes": 1} for _ in range(25)]
        summary = RUNNER.summarize_partition("x", unsat, 26)
        self.assertEqual(summary["result"], "UNSAT")
        unresolved = unsat[:-1] + [{"attempts": 1, "result": "UNKNOWN",
                                    "elapsed_seconds": 1, "peak_tree_rss_bytes": 1}]
        self.assertEqual(
            RUNNER.summarize_partition("x", unresolved, 26)["result"], "UNKNOWN"
        )
        sat = [{"attempts": 1, "result": "SAT", "elapsed_seconds": 1,
                "peak_tree_rss_bytes": 1, "sat_witness_output_preserved": True}]
        sat += [{"attempts": 0, "result": "UNRUN"} for _ in range(24)]
        self.assertEqual(RUNNER.summarize_partition("x", sat, 2)["result"], "SAT")

    def test_runner_reuses_exact_d1p05_monitor(self):
        self.assertEqual(RUNNER.sha256(RUNNER.D1P05_RUNNER), RUNNER.EXPECTED_D1P05_RUNNER)
        self.assertIs(RUNNER.D1P05.MacProcessTreeMonitor,
                      RUNNER.D1P05.MacProcessTreeMonitor)


if __name__ == "__main__":
    unittest.main()
