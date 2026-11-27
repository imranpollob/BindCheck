import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/d1p_05_validate.py"
SPEC = importlib.util.spec_from_file_location("d1p_05_validate", MODULE_PATH)
D1P05 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D1P05)


class RunnerInfrastructureTests(unittest.TestCase):
    def setUp(self):
        raw = ROOT / "results/raw"
        raw.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(
            prefix="d1p05-unit-", dir=raw
        )
        self.logs = Path(self.temporary.name) / "calls"
        self.monitor = D1P05.MacProcessTreeMonitor()

    def tearDown(self):
        self.temporary.cleanup()

    def test_mac_monitor_observes_current_process(self):
        sample = self.monitor.sample(os.getpid())
        self.assertTrue(sample["root_present"])
        self.assertGreater(sample["resident_bytes"], 0)
        self.assertIn(os.getpid(), sample["pids"])

    def test_harmless_launch_is_logged(self):
        record = D1P05.run_monitored(
            index=1, kind="unit", name="launch",
            argv=D1P05.helper_command("print('ok', flush=True)"),
            logs_dir=self.logs, monitor=self.monitor,
            timeout_seconds=1.0, rss_cutoff_bytes=512 * 1024**2,
            sample_interval_seconds=0.02,
        )
        self.assertEqual(record["status"], "COMPLETED")
        self.assertEqual(record["exit_status"], 0)
        self.assertGreaterEqual(record["memory_samples"], 1)
        self.assertEqual((ROOT / record["stdout_path"]).read_text(), "ok\n")
        self.assertTrue((ROOT / record["record_path"]).is_file())

    def test_launch_exception_is_structured(self):
        record = D1P05.run_monitored(
            index=1, kind="unit", name="launch_error",
            argv=[str(Path(self.temporary.name) / "missing-command")],
            logs_dir=self.logs, monitor=self.monitor,
            timeout_seconds=1.0, rss_cutoff_bytes=512 * 1024**2,
            sample_interval_seconds=0.02,
        )
        self.assertEqual(record["status"], "LAUNCH_ERROR")
        self.assertFalse(record["process_launched"])
        self.assertIn("FileNotFoundError", record["error"])

    def test_timeout_kills_process_group_and_child(self):
        pid_file = Path(self.temporary.name) / "timeout-child.pid"
        code = (
            "import pathlib,subprocess,sys,time;"
            "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(30)']);"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));"
            "time.sleep(30)"
        )
        record = D1P05.run_monitored(
            index=1, kind="unit", name="timeout",
            argv=D1P05.helper_command(code, pid_file),
            logs_dir=self.logs, monitor=self.monitor,
            timeout_seconds=0.3, rss_cutoff_bytes=512 * 1024**2,
            sample_interval_seconds=0.02,
        )
        child_pid = int(pid_file.read_text())
        survivors = D1P05.wait_for_cleanup(
            self.monitor, [record["pid"], child_pid]
        )
        self.assertEqual(record["status"], "TIMEOUT")
        self.assertTrue(record["process_group_sigkill_sent"])
        self.assertEqual(survivors, [])

    def test_monitor_failure_kills_process_group(self):
        record = D1P05.run_monitored(
            index=1, kind="unit", name="monitor_failure",
            argv=D1P05.helper_command("import time;time.sleep(30)"),
            logs_dir=self.logs, monitor=D1P05.FailingMonitor(),
            timeout_seconds=1.0, rss_cutoff_bytes=512 * 1024**2,
            sample_interval_seconds=0.02,
        )
        survivors = D1P05.wait_for_cleanup(self.monitor, [record["pid"]])
        self.assertEqual(record["status"], "MONITOR_ERROR")
        self.assertTrue(record["monitor_failed"])
        self.assertTrue(record["process_group_sigkill_sent"])
        self.assertEqual(survivors, [])

    def test_resource_policy_is_sampled_not_rlimit(self):
        source = MODULE_PATH.read_text()
        self.assertNotIn("resource.setrlimit", source)
        self.assertNotIn("import resource", source)
        self.assertEqual(D1P05.RSS_CUTOFF_BYTES, 4 * 1024**3)
        self.assertEqual(D1P05.SECONDS_PER_CALL, 30.0)
        self.assertEqual(D1P05.SAMPLE_INTERVAL_SECONDS, 0.05)


if __name__ == "__main__":
    unittest.main()
