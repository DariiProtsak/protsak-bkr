import json
import tempfile
import unittest
from pathlib import Path

from csi_capture.core.dataset import DatasetValidationError, load_static_sign_runs, validate_run_metadata


class DatasetSchemaTests(unittest.TestCase):
    def test_validate_run_metadata_accepts_valid_payload(self):
        payload = {
            "schema_version": 1,
            "experiment_name": "static_sign_v1",
            "label": "baseline",
            "run_id": "run_001",
            "subject_id": "s1",
            "environment_id": "lab_a",
            "device": "esp32_c3",
            "serial_dev": "/dev/esp32_csi",
            "start_time": "2026-03-02T00:00:00Z",
            "end_time": "2026-03-02T00:00:20Z",
            "sampling_params": {"duration_s": 20, "baud": 921600},
            "notes": "ok",
        }
        validate_run_metadata(payload)

    def test_validate_run_metadata_rejects_invalid_label(self):
        payload = {
            "schema_version": 1,
            "experiment_name": "static_sign_v1",
            "label": "jumping",
            "run_id": "run_001",
            "device": "esp32_c3",
            "serial_dev": "/dev/esp32_csi",
            "start_time": "2026-03-02T00:00:00Z",
            "end_time": "2026-03-02T00:00:20Z",
            "sampling_params": {"duration_s": 20},
        }
        with self.assertRaises(DatasetValidationError):
            validate_run_metadata(payload)

    def test_load_static_sign_runs_reads_metadata_and_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data" / "experiments" / "static_sign_v1" / "20260302" / "baseline" / "run_test"
            root.mkdir(parents=True)
            metadata = {
                "schema_version": 1,
                "experiment_name": "static_sign_v1",
                "label": "baseline",
                "run_id": "run_test",
                "subject_id": None,
                "environment_id": None,
                "device": "esp32_c3",
                "serial_dev": "/dev/esp32_csi",
                "start_time": "2026-03-02T00:00:00Z",
                "end_time": "2026-03-02T00:00:20Z",
                "sampling_params": {"duration_s": 20, "baud": 921600},
                "notes": None,
            }
            (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (root / "frames.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp": 1, "csi": [1, 2, 3, 4], "rssi": -20}),
                        json.dumps({"timestamp": 2, "csi": [2, 3, 4, 5], "rssi": -21}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            runs = load_static_sign_runs(Path(tmp) / "data" / "experiments" / "static_sign_v1" / "20260302")
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0].metadata["label"], "baseline")
            self.assertEqual(len(runs[0].frames), 2)


if __name__ == "__main__":
    unittest.main()
