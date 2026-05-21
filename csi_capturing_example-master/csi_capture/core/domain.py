from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

CANONICAL_SCHEMA_NAME = "esp32-csi-platform"
CANONICAL_SCHEMA_VERSION = "v1"


@dataclass(frozen=True)
class DeviceProfile:
    profile_id: str
    transport: str
    parser: str
    default_serial_device: str
    default_baud: int
    supported_path_patterns: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubjectRef:
    subject_id: str | None = None
    cohort_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioRef:
    scenario_id: str
    tags: tuple[str, ...] = ()
    room_id: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabelSet:
    label_set_id: str
    task_type: str
    labels: tuple[str, ...] = ()
    positive_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GroundTruth:
    values: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(frozen=True)
class Geometry:
    coordinate_frame: str = ""
    transmitter: dict[str, Any] = field(default_factory=dict)
    receiver: dict[str, Any] = field(default_factory=dict)
    antenna_array: dict[str, Any] = field(default_factory=dict)
    measurement_positions: str = ""
    orientation_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcquisitionBlock:
    block_id: str
    modality: str
    packet_budget: int | None = None
    duration_s: float | None = None
    output_format: str = "jsonl"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrialDefinition:
    trial_id: str
    repeat_index: int
    ground_truth: GroundTruth = field(default_factory=GroundTruth)
    scenario: ScenarioRef | None = None
    subject: SubjectRef | None = None
    acquisition: AcquisitionBlock | None = None
    labels: LabelSet | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "trial_id": self.trial_id,
            "repeat_index": self.repeat_index,
            "ground_truth": self.ground_truth.to_dict(),
            "notes": self.notes,
        }
        if self.scenario is not None:
            payload["scenario"] = self.scenario.to_dict()
        if self.subject is not None:
            payload["subject"] = self.subject.to_dict()
        if self.acquisition is not None:
            payload["acquisition"] = self.acquisition.to_dict()
        if self.labels is not None:
            payload["labels"] = self.labels.to_dict()
        return payload


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    display_name: str
    summary: str
    task_type: str
    modalities: tuple[str, ...]
    layout_style: str
    target_profile_id: str
    supports_capture: bool = False
    supports_preprocess: bool = False
    supports_train: bool = False
    supports_evaluate: bool = False
    supports_report: bool = False
    supports_inspect: bool = False
    config_modes: tuple[str, ...] = ()
    label_set: LabelSet | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.label_set is not None:
            payload["label_set"] = self.label_set.to_dict()
        return payload


@dataclass(frozen=True)
class RunProvenance:
    git_commit: str | None = None
    git_dirty: bool | None = None
    target_profile_id: str | None = None
    device_path: str | None = None
    device_realpath: str | None = None
    notes: str = ""
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PacketRecord:
    timestamp: int
    esp_timestamp: int | None = None
    rssi: int | float | None = None
    csi: list[int] | list[float] | None = None
    mac: str | None = None
    experiment_id: str | None = None
    dataset_id: str | None = None
    run_id: str | None = None
    trial_id: str | None = None
    scenario_tags: tuple[str, ...] = ()
    ground_truth: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ground_truth"] = dict(self.ground_truth)
        payload["extra"] = dict(self.extra)
        return payload


@dataclass(frozen=True)
class RunManifest:
    experiment: ExperimentDefinition
    dataset_id: str
    run_id: str
    status: str
    created_at_utc: str
    layout_style: str
    schema_name: str = CANONICAL_SCHEMA_NAME
    schema_version: str = CANONICAL_SCHEMA_VERSION
    scenario: ScenarioRef | None = None
    subject: SubjectRef | None = None
    geometry: Geometry | None = None
    trials: tuple[TrialDefinition, ...] = ()
    provenance: RunProvenance = field(default_factory=RunProvenance)
    capture: dict[str, Any] = field(default_factory=dict)
    config_snapshot: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "layout_style": self.layout_style,
            "experiment": self.experiment.to_dict(),
            "dataset_id": self.dataset_id,
            "run_id": self.run_id,
            "status": self.status,
            "created_at_utc": self.created_at_utc,
            "trials": [trial.to_dict() for trial in self.trials],
            "provenance": self.provenance.to_dict(),
            "capture": dict(self.capture),
            "config_snapshot": dict(self.config_snapshot),
            "extra": dict(self.extra),
        }
        if self.scenario is not None:
            payload["scenario"] = self.scenario.to_dict()
        if self.subject is not None:
            payload["subject"] = self.subject.to_dict()
        if self.geometry is not None:
            payload["geometry"] = self.geometry.to_dict()
        return payload


@dataclass(frozen=True)
class DerivedFeatureSet:
    feature_set_id: str
    experiment_id: str
    dataset_id: str
    modality: str
    feature_columns: tuple[str, ...]
    artifact_path: str
    row_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrainedModelArtifact:
    model_id: str
    experiment_id: str
    dataset_id: str
    task_type: str
    model_name: str
    artifact_path: str
    feature_set_id: str | None = None
    metrics_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationReport:
    report_id: str
    experiment_id: str
    dataset_id: str
    task_type: str
    metrics: dict[str, Any]
    artifact_paths: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
