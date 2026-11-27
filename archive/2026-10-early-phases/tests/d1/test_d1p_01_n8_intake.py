"""Controls for the D1P-01 provenance and no-solver intake boundary."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import d1p_01_n8_intake as I  # noqa: E402
import t22_v3_tailspec as T  # noqa: E402


MANIFEST = ROOT / "metadata/d1/d1-01-execution-manifest.json"
COMPONENTS = I.Components(
    ROOT / "scripts/t22_v5_protocol.md",
    ROOT / "scripts/t22_v5_compact.py",
    ROOT / "scripts/t22_v3_tailspec.py",
    ROOT / "scripts/t22_specs/payy_agg_agg.json",
)


class IntakeTests(unittest.TestCase):
    def test_expected_identities_are_path_neutral(self):
        expected = I.load_expected(MANIFEST)
        self.assertEqual(expected["limits"]["N"], 8)
        self.assertEqual(len(expected["queries"]), 6)
        self.assertEqual(
            expected["inputs"]["check_added_acir"],
            "1743e5dcdeaf36172fbbde66fda165e79db9081f8a3a980ee4bbf31f61a2875a",
        )
        self.assertEqual(
            expected["queries"]["running_flag/tail"],
            "4d80a119dfe1f781eb2a47cb60490143afc930eb150dec2b4da980370d900a3c",
        )

    def test_missing_inputs_stop_before_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = I.InputBundle(*(root / name for name in ("a", "b", "c", "d")))
            generator = mock.Mock(side_effect=AssertionError("generation must not run"))
            result = I.perform_intake(
                MANIFEST, inputs, COMPONENTS, root / "output", generator=generator
            )
            self.assertEqual(result["artifact_status"], "BLOCKED")
            self.assertEqual(result["reason_codes"], ["REQUIRED_ARTIFACT_MISSING"])
            self.assertEqual(result["solver_processes_launched"], 0)
            generator.assert_not_called()
            self.assertFalse((root / "output").exists())

    def test_hash_mismatches_stop_before_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = [root / name for name in ("a", "b", "c", "d")]
            for path in paths:
                path.write_bytes(b"not a historical artifact")
            inputs = I.InputBundle(*paths)
            generator = mock.Mock(side_effect=AssertionError("generation must not run"))
            result = I.perform_intake(
                MANIFEST, inputs, COMPONENTS, root / "output", generator=generator
            )
            self.assertEqual(result["artifact_status"], "BLOCKED")
            self.assertEqual(result["reason_codes"], ["ARTIFACT_HASH_MISMATCH"])
            generator.assert_not_called()
            self.assertFalse((root / "output").exists())

    def test_serialization_sink_cannot_launch_or_return_solver_result(self):
        class FakeCompact:
            T = T

            @staticmethod
            def run_one(_acir, _messages, _streams, query, outdir, seconds, encode_acir):
                self = FakeCompact.T.FF(seconds * 1000)
                witness = self.var(1)
                self.A(self.eq(witness, self.one))
                return self.solve([witness], str(outdir / f"{query}.smt2"))

        with tempfile.TemporaryDirectory() as temp:
            outdir = Path(temp)
            with mock.patch.object(
                subprocess, "Popen", side_effect=AssertionError("solver process launched")
            ) as popen:
                data = I._generate_one(FakeCompact, None, None, None, "tail", outdir)
            popen.assert_not_called()
            self.assertEqual(data, (outdir / "tail.smt2").read_bytes())
            self.assertTrue(data.startswith(b"(set-logic QF_FF)\n"))
            self.assertTrue(data.endswith(b"(check-sat)\n(get-value (w1))\n"))
            self.assertFalse((outdir / "tail.smt2.solver.json").exists())

    def test_component_tamper_is_rejected(self):
        expected = I.load_expected(MANIFEST)
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "t22_v5_compact.py"
            changed.write_bytes(COMPONENTS.encoder.read_bytes() + b"\n# changed\n")
            components = I.Components(
                COMPONENTS.protocol, changed, COMPONENTS.parser, COMPONENTS.spec
            )
            checks = I.validate_files(
                expected,
                I.InputBundle(*(Path(temp) / name for name in ("a", "b", "c", "d"))),
                components,
            )
            encoder = next(row for row in checks if row["role"] == "encoder")
            self.assertEqual(encoder["status"], "MISMATCH")
            self.assertEqual(encoder["reason_code"], "ARTIFACT_HASH_MISMATCH")
            self.assertNotEqual(encoder["actual_sha256"], encoder["expected_sha256"])
            self.assertEqual(
                encoder["actual_sha256"], hashlib.sha256(changed.read_bytes()).hexdigest()
            )


if __name__ == "__main__":
    unittest.main()
