import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLISmokeTests(unittest.TestCase):
    def test_help_returns_zero(self):
        proc = subprocess.run(
            [sys.executable, "-m", "csi_capture.cli", "--help"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("capture", proc.stdout)
        self.assertIn("train", proc.stdout)
        self.assertIn("eval", proc.stdout)
        self.assertIn("list-target-profiles", proc.stdout)

    def test_validate_config_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "experiment": "static_sign_v1",
                "label": "baseline",
                "runs": 2,
                "duration_s": 10,
            }
            config_path = Path(tmp) / "capture.json"
            config_path.write_text(json.dumps(cfg), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "csi_capture.cli",
                    "validate-config",
                    "--experiment",
                    "static_sign_v1",
                    "--mode",
                    "capture",
                    "--config",
                    str(config_path),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("Config validation passed", proc.stdout)

    def test_list_target_profiles_returns_zero(self):
        proc = subprocess.run(
            [sys.executable, "-m", "csi_capture.cli", "--list-target-profiles"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Target environment profiles", proc.stdout)


if __name__ == "__main__":
    unittest.main()
