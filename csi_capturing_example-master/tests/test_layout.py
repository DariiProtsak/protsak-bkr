import unittest
from pathlib import Path

from csi_capture.core.layout import (
    LAYOUT_CANONICAL_V1,
    LAYOUT_LEGACY_DISTANCE_ANGLE_V1,
    LAYOUT_LEGACY_STATIC_SIGN_V1,
    build_run_layout,
)


class LayoutTests(unittest.TestCase):
    def test_build_run_layout_canonical(self):
        layout = build_run_layout(
            root=Path("experiments"),
            experiment_id="presence_v1",
            dataset_id="dataset_001",
            run_id="001",
            layout_style=LAYOUT_CANONICAL_V1,
        )
        self.assertEqual(
            layout.run_dir,
            Path("experiments") / "presence_v1" / "dataset_001" / "runs" / "run_001",
        )
        trial = layout.trial_paths("trial_a")
        self.assertEqual(
            trial.packet_path,
            Path("experiments")
            / "presence_v1"
            / "dataset_001"
            / "runs"
            / "run_001"
            / "trials"
            / "trial_trial_a"
            / "packets.jsonl",
        )

    def test_build_run_layout_legacy_distance_angle(self):
        layout = build_run_layout(
            root=Path("experiments"),
            experiment_id="distance",
            dataset_id="exp_demo",
            run_id="run01",
            layout_style=LAYOUT_LEGACY_DISTANCE_ANGLE_V1,
        )
        self.assertEqual(
            layout.run_dir,
            Path("experiments") / "exp_demo" / "distance" / "run_run01",
        )
        trial = layout.trial_paths("distance_1m_rep_001", output_format="csv")
        self.assertEqual(
            trial.packet_path,
            Path("experiments")
            / "exp_demo"
            / "distance"
            / "run_run01"
            / "trial_distance_1m_rep_001"
            / "capture.csv",
        )

    def test_build_run_layout_legacy_static_sign_requires_label(self):
        with self.assertRaises(ValueError):
            build_run_layout(
                root=Path("data/experiments"),
                experiment_id="static_sign_v1",
                dataset_id="20260302",
                run_id="abc",
                layout_style=LAYOUT_LEGACY_STATIC_SIGN_V1,
            )


if __name__ == "__main__":
    unittest.main()
