from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LAYOUT_CANONICAL_V1 = "canonical_v1"
LAYOUT_LEGACY_DISTANCE_ANGLE_V1 = "legacy_distance_angle_v1"
LAYOUT_LEGACY_STATIC_SIGN_V1 = "legacy_static_sign_v1"

DEFAULT_CAPTURE_ROOT = Path("experiments")
DEFAULT_ARTIFACT_ROOT = Path("artifacts")


@dataclass(frozen=True)
class TrialPaths:
    trial_dir: Path
    packet_path: Path


@dataclass(frozen=True)
class RunLayout:
    root: Path
    experiment_id: str
    dataset_id: str
    run_id: str
    layout_style: str
    run_dir: Path
    manifest_path: Path

    def trial_paths(self, trial_id: str, output_format: str = "jsonl") -> TrialPaths:
        extension = "jsonl" if output_format == "jsonl" else "csv"
        if self.layout_style == LAYOUT_CANONICAL_V1:
            trial_dir = self.run_dir / "trials" / f"trial_{trial_id}"
            packet_path = trial_dir / f"packets.{extension}"
        elif self.layout_style == LAYOUT_LEGACY_DISTANCE_ANGLE_V1:
            trial_dir = self.run_dir / f"trial_{trial_id}"
            packet_path = trial_dir / f"capture.{extension}"
        elif self.layout_style == LAYOUT_LEGACY_STATIC_SIGN_V1:
            trial_dir = self.run_dir
            packet_path = self.run_dir / ("frames.jsonl" if extension == "jsonl" else f"frames.{extension}")
        else:
            raise ValueError(f"Unsupported layout style: {self.layout_style}")
        return TrialPaths(trial_dir=trial_dir, packet_path=packet_path)


def build_run_layout(
    *,
    root: Path | str,
    experiment_id: str,
    dataset_id: str,
    run_id: str,
    layout_style: str = LAYOUT_CANONICAL_V1,
    label: str | None = None,
) -> RunLayout:
    root_path = Path(root)
    if layout_style == LAYOUT_CANONICAL_V1:
        run_dir = root_path / experiment_id / dataset_id / "runs" / f"run_{run_id}"
        manifest_path = run_dir / "manifest.json"
    elif layout_style == LAYOUT_LEGACY_DISTANCE_ANGLE_V1:
        run_dir = root_path / dataset_id / experiment_id / f"run_{run_id}"
        manifest_path = run_dir / "manifest.json"
    elif layout_style == LAYOUT_LEGACY_STATIC_SIGN_V1:
        if not label:
            raise ValueError("label is required for legacy_static_sign_v1 layout")
        run_dir = root_path / experiment_id / dataset_id / label / f"run_{run_id}"
        manifest_path = run_dir / "manifest.json"
    else:
        raise ValueError(f"Unsupported layout style: {layout_style}")

    return RunLayout(
        root=root_path,
        experiment_id=experiment_id,
        dataset_id=dataset_id,
        run_id=run_id,
        layout_style=layout_style,
        run_dir=run_dir,
        manifest_path=manifest_path,
    )


def feature_artifact_dir(
    *,
    root: Path | str,
    experiment_id: str,
    dataset_id: str,
    feature_set_id: str,
) -> Path:
    return Path(root) / experiment_id / dataset_id / "features" / feature_set_id


def model_artifact_dir(
    *,
    root: Path | str,
    experiment_id: str,
    dataset_id: str,
    model_id: str,
) -> Path:
    return Path(root) / experiment_id / dataset_id / "models" / model_id


def evaluation_artifact_dir(
    *,
    root: Path | str,
    experiment_id: str,
    dataset_id: str,
    report_id: str,
) -> Path:
    return Path(root) / experiment_id / dataset_id / "reports" / report_id
