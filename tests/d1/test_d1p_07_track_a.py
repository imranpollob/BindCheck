import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/d1p_07_track_a.py"
SPEC = importlib.util.spec_from_file_location("d1p_07_track_a", MODULE_PATH)
D1P07 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D1P07)


class ProcessExitRegressionTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "results/raw").mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(
            prefix="d1p07-unit-", dir=ROOT / "results/raw"
        )
        self.logs = Path(self.temporary.name) / "calls"
        self.monitor = D1P07.D1P05.MacProcessTreeMonitor()

    def tearDown(self):
        self.temporary.cleanup()

    def assert_logs(self, record):
        for key in ("stdout_path", "stderr_path", "record_path"):
            self.assertTrue((ROOT / record[key]).is_file(), key)

    def test_rapid_exit_is_reaped_and_memory_is_not_fabricated(self):
        record = D1P07.run_monitored(
            index=1, kind="unit", name="rapid_exit",
            argv=D1P07.helper_command("print('ok',flush=True)"),
            logs_dir=self.logs, monitor=self.monitor,
            timeout_seconds=1.0, sample_interval_seconds=0.01,
            rss_cutoff_bytes=512 * 1024**2,
        )
        self.assertEqual(record["status"], "COMPLETED")
        self.assertEqual(record["exit_status"], 0)
        self.assert_logs(record)
        if record["memory_samples"] == 0:
            self.assertIsNone(record["peak_tree_rss_bytes"])
            self.assertFalse(record["memory_observation_available"])

    def test_exit_during_sampling_is_normal_only_after_bounded_reap(self):
        record = D1P07.run_monitored(
            index=1, kind="unit", name="exit_during_sampling",
            argv=D1P07.helper_command(
                "import time;time.sleep(.03);print('done',flush=True)"
            ),
            logs_dir=self.logs, monitor=D1P07.ExitDuringSampleMonitor(),
            timeout_seconds=1.0, sample_interval_seconds=0.01,
            rss_cutoff_bytes=512 * 1024**2,
        )
        self.assertEqual(record["status"], "COMPLETED")
        self.assertEqual(record["exit_status"], 0)
        self.assertTrue(record["exit_confirmed_after_missing_root"])
        self.assertFalse(record["monitor_failed"])
        self.assert_logs(record)

    def test_live_process_monitor_failure_stops_and_preserves_logs(self):
        record = D1P07.run_monitored(
            index=1, kind="unit", name="live_monitor_failure",
            argv=D1P07.helper_command("import time;time.sleep(30)"),
            logs_dir=self.logs, monitor=D1P07.FailingMonitor(),
            timeout_seconds=1.0, sample_interval_seconds=0.01,
            rss_cutoff_bytes=512 * 1024**2,
        )
        survivors = D1P07.wait_cleanup(self.monitor, [record["pid"]])
        self.assertEqual(record["status"], "MONITOR_ERROR")
        self.assertTrue(record["monitor_failed"])
        self.assertTrue(record["termination"]["reaped"])
        self.assertEqual(survivors, [])
        self.assert_logs(record)

    def test_denied_group_cleanup_is_caught_bounded_and_falls_back(self):
        record = D1P07.run_monitored(
            index=1, kind="unit", name="denied_cleanup",
            argv=D1P07.helper_command("import time;time.sleep(30)"),
            logs_dir=self.logs, monitor=D1P07.FailingMonitor(),
            timeout_seconds=1.0, sample_interval_seconds=0.01,
            rss_cutoff_bytes=512 * 1024**2,
            group_kill=D1P07.denied_group_kill,
        )
        survivors = D1P07.wait_cleanup(self.monitor, [record["pid"]])
        self.assertEqual(record["status"], "MONITOR_ERROR")
        self.assertTrue(any(
            "PermissionError" in value for value in record["termination"]["errors"]
        ))
        self.assertTrue(record["termination"]["direct_kill_sent"])
        self.assertTrue(record["termination"]["reaped"])
        self.assertLess(record["elapsed_seconds"], 2.0)
        self.assertEqual(survivors, [])
        self.assert_logs(record)


class CampaignStructureTests(unittest.TestCase):
    def test_fresh_schedule_starts_at_one_and_has_166_unchanged_inputs(self):
        manifest, checked = D1P07.verify_inputs()
        schedule = D1P07.planned_rows(manifest)
        self.assertEqual(checked, 166)
        self.assertEqual(len(schedule), 166)
        self.assertEqual(schedule[0][0:2], ("control", "known_equivalence"))
        self.assertEqual(schedule[-1][0], "partitioned")

    def test_resource_and_budget_constants_match_d1p06(self):
        self.assertEqual(D1P07.RSS_CUTOFF, 4 * 1024**3)
        self.assertEqual(D1P07.SAMPLE_INTERVAL, 0.05)
        self.assertEqual(D1P07.UNSPLIT_SECONDS, 300.0)
        self.assertEqual(D1P07.PARTITION_SLOT_SECONDS, 300.0)
        self.assertEqual(D1P07.CELL_SECONDS, 12.0)
        self.assertEqual(D1P07.PRIMARY_AGGREGATE_SECONDS, 6000.0)
        self.assertEqual(D1P07.PRIMARY_CALLS_MAX, 164)

    def test_unrun_memory_is_unavailable_not_zero(self):
        item = {"path": "x", "sha256": "y"}
        record = D1P07.unrun(4, "goal_only", "slot", item, "stopped")
        self.assertIsNone(record["peak_tree_rss_bytes"])
        self.assertFalse(record["memory_observation_available"])


if __name__ == "__main__":
    unittest.main()
