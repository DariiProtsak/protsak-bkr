from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from csi_capture.core.domain import CANONICAL_SCHEMA_NAME, CANONICAL_SCHEMA_VERSION

STATIC_SIGN_SCHEMA_VERSION = 1
STATIC_SIGN_LABELS = ("baseline", "hands_up")


@dataclass(frozen=True)
class RunCapture:
    run_dir: Path
    metadata: dict[str, Any]
    frames: list[dict[str, Any]]


@dataclass(frozen=True)
class NormalizedTrialCapture:
    trial_id: str
    packet_path: Path
    metadata: dict[str, Any]
    records: list[dict[str, Any]]


@dataclass(frozen=True)
class NormalizedRun:
    run_dir: Path
    manifest: dict[str, Any]
    packet_files: list[Path]
    trials: list[NormalizedTrialCapture]


class DatasetValidationError(ValueError):
    """Raised when dataset schema/content checks fail."""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise DatasetValidationError(f"Expected JSON object: {path}")
    return payload


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _iter_csv(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield dict(row)


def iter_packet_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Adapter reader supporting legacy/new packet files."""
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".txt"}:
        yield from _iter_jsonl(path)
        return
    if suffix == ".csv":
        yield from _iter_csv(path)
        return
    if suffix == ".json":
        payload = _read_json(path)
        records = payload.get("records") if isinstance(payload, dict) else None
        if isinstance(records, list):
            for row in records:
                if isinstance(row, dict):
                    yield row
            return
        yield payload
        return
    raise DatasetValidationError(f"Unsupported packet file extension: {path}")


def validate_run_metadata(
    metadata: dict[str, Any],
    *,
    expected_experiment: str = "static_sign_v1",
    allowed_labels: tuple[str, ...] = STATIC_SIGN_LABELS,
) -> None:
    required_str_fields = (
        "experiment_name",
        "label",
        "run_id",
        "device",
        "serial_dev",
        "start_time",
        "end_time",
    )
    for field in required_str_fields:
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DatasetValidationError(f"metadata.{field} must be a non-empty string")

    if metadata.get("experiment_name") != expected_experiment:
        raise DatasetValidationError(
            f"metadata.experiment_name must be '{expected_experiment}'"
        )

    label = str(metadata.get("label", "")).strip().lower()
    if label not in allowed_labels:
        raise DatasetValidationError(
            f"metadata.label must be one of {sorted(allowed_labels)}"
        )

    schema_version = metadata.get("schema_version")
    if schema_version != STATIC_SIGN_SCHEMA_VERSION:
        raise DatasetValidationError(
            f"metadata.schema_version must be {STATIC_SIGN_SCHEMA_VERSION}"
        )

    sampling_params = metadata.get("sampling_params")
    if not isinstance(sampling_params, dict):
        raise DatasetValidationError("metadata.sampling_params must be an object")

    for optional in ("subject_id", "environment_id", "notes", "target_profile", "chip"):
        value = metadata.get(optional)
        if value is not None and not isinstance(value, str):
            raise DatasetValidationError(f"metadata.{optional} must be string or null")

    environment_profile = metadata.get("environment_profile")
    if environment_profile is not None and not isinstance(environment_profile, dict):
        raise DatasetValidationError("metadata.environment_profile must be object or null")


def validate_canonical_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise DatasetValidationError("manifest must be an object")
    if manifest.get("schema_name") != CANONICAL_SCHEMA_NAME:
        raise DatasetValidationError(
            f"manifest.schema_name must be '{CANONICAL_SCHEMA_NAME}'"
        )
    if manifest.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        raise DatasetValidationError(
            f"manifest.schema_version must be '{CANONICAL_SCHEMA_VERSION}'"
        )
    experiment = manifest.get("experiment")
    if not isinstance(experiment, dict):
        raise DatasetValidationError("manifest.experiment must be an object")
    experiment_id = experiment.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise DatasetValidationError("manifest.experiment.experiment_id must be a non-empty string")
    for field in ("dataset_id", "run_id", "status", "created_at_utc"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DatasetValidationError(f"manifest.{field} must be a non-empty string")


def _packet_paths_from_manifest(run_dir: Path, manifest: dict[str, Any]) -> list[Path]:
    packet_files: list[Path] = []
    for trial in manifest.get("trials", []):
        if not isinstance(trial, dict):
            continue
        output_file = trial.get("output_file")
        if isinstance(output_file, str) and output_file.strip():
            packet_path = Path(output_file)
            candidates = [packet_path]
            if not packet_path.is_absolute():
                candidates.append(run_dir / packet_path)
            for candidate in candidates:
                if candidate.exists():
                    packet_files.append(candidate)
                    break
            continue
        packet_rel = trial.get("packet_path")
        if isinstance(packet_rel, str) and packet_rel.strip():
            packet_path = run_dir / packet_rel
            if packet_path.exists():
                packet_files.append(packet_path)
    if packet_files:
        return packet_files

    for candidate in (
        run_dir / "frames.jsonl",
        run_dir / "capture.jsonl",
        run_dir / "capture.csv",
    ):
        if candidate.exists():
            packet_files.append(candidate)
    if packet_files:
        return packet_files

    for path in sorted(run_dir.rglob("capture.jsonl")):
        packet_files.append(path)
    for path in sorted(run_dir.rglob("capture.csv")):
        if path not in packet_files:
            packet_files.append(path)
    for path in sorted(run_dir.rglob("frames.jsonl")):
        if path not in packet_files:
            packet_files.append(path)
    return packet_files


def _load_legacy_static_sign_manifest(meta_path: Path) -> dict[str, Any]:
    metadata = _read_json(meta_path)
    validate_run_metadata(metadata)
    run_dir = meta_path.parent
    frames_path = run_dir / "frames.jsonl"
    if not frames_path.exists():
        raise DatasetValidationError(f"Missing frames.jsonl for run: {run_dir}")
    label = str(metadata.get("label", "")).strip().lower()
    parts = list(run_dir.parts)
    dataset_id = run_dir.parent.parent.name
    try:
        experiment_index = parts.index("static_sign_v1")
    except ValueError:
        experiment_index = -1
    if experiment_index >= 0 and experiment_index + 1 < len(parts):
        dataset_id = parts[experiment_index + 1]
    environment_profile = metadata.get("environment_profile")
    return {
        "schema_name": CANONICAL_SCHEMA_NAME,
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "layout_style": "legacy_static_sign_v1",
        "dataset_id": dataset_id,
        "run_id": str(metadata["run_id"]),
        "status": "completed",
        "created_at_utc": str(metadata["start_time"]),
        "experiment": {
            "experiment_id": str(metadata["experiment_name"]),
            "display_name": "Static Gesture / Static Sign v1",
            "summary": "Legacy static sign capture imported into canonical manifest view.",
            "task_type": "classification",
            "modalities": ("csi", "rssi", "fusion"),
            "layout_style": "legacy_static_sign_v1",
            "target_profile_id": metadata.get("target_profile"),
            "supports_capture": True,
            "supports_preprocess": True,
            "supports_train": True,
            "supports_evaluate": True,
            "supports_report": False,
            "supports_inspect": False,
            "config_modes": ("capture", "train", "eval"),
            "label_set": {
                "label_set_id": "static_sign_binary_v1",
                "task_type": "classification",
                "labels": STATIC_SIGN_LABELS,
                "positive_label": "hands_up",
            },
        },
        "scenario": {
            "scenario_id": label,
            "tags": [label],
            "room_id": metadata.get("environment_id"),
            "notes": metadata.get("notes") or "",
        },
        "subject": {
            "subject_id": metadata.get("subject_id"),
            "cohort_id": None,
            "attributes": {},
        },
        "capture": metadata.get("sampling_params", {}),
        "provenance": {
            "git_commit": None,
            "git_dirty": None,
            "target_profile_id": metadata.get("target_profile"),
            "device_path": metadata.get("serial_dev"),
            "device_realpath": metadata.get("serial_realpath"),
            "notes": metadata.get("notes") or "",
            "tags": [label],
        },
        "trials": [
            {
                "trial_id": "capture",
                "repeat_index": 1,
                "ground_truth": {"label": label},
                "packet_path": frames_path.name,
                "output_file": str(frames_path),
            }
        ],
        "extra": {
            "legacy_metadata_path": str(meta_path),
            "records_captured": metadata.get("records_captured"),
            "environment_profile": environment_profile,
            "device": metadata.get("device"),
            "chip": metadata.get("chip"),
            "ended_at_utc": metadata.get("end_time"),
        },
    }


def load_normalized_runs(root: Path, *, experiment_name: str | None = None) -> list[NormalizedRun]:
    if not root.exists():
        raise DatasetValidationError(f"Dataset root does not exist: {root}")

    candidate_dirs: dict[Path, Path] = {}
    for manifest_path in sorted(root.rglob("manifest.json")):
        candidate_dirs[manifest_path.parent] = manifest_path
    for meta_path in sorted(root.rglob("metadata.json")):
        candidate_dirs.setdefault(meta_path.parent, meta_path)

    if not candidate_dirs:
        raise DatasetValidationError(f"No manifest.json or metadata.json files found under: {root}")

    runs: list[NormalizedRun] = []
    for run_dir, marker_path in sorted(candidate_dirs.items()):
        if marker_path.name == "manifest.json":
            manifest = _read_json(marker_path)
            validate_canonical_manifest(manifest)
        else:
            manifest = _load_legacy_static_sign_manifest(marker_path)

        experiment = manifest.get("experiment", {})
        experiment_id = experiment.get("experiment_id")
        if experiment_name and experiment_id != experiment_name:
            continue

        packet_files = _packet_paths_from_manifest(run_dir, manifest)
        if not packet_files:
            raise DatasetValidationError(f"No packet files found for run: {run_dir}")

        trials: list[NormalizedTrialCapture] = []
        trial_entries = manifest.get("trials", [])
        for index, packet_path in enumerate(packet_files):
            trial_meta = (
                trial_entries[index]
                if index < len(trial_entries) and isinstance(trial_entries[index], dict)
                else {"trial_id": f"trial_{index + 1:03d}"}
            )
            records = list(iter_packet_rows(packet_path))
            if not records:
                raise DatasetValidationError(f"No packet records found in {packet_path}")
            trial_id = str(trial_meta.get("trial_id", f"trial_{index + 1:03d}"))
            trials.append(
                NormalizedTrialCapture(
                    trial_id=trial_id,
                    packet_path=packet_path,
                    metadata=dict(trial_meta),
                    records=records,
                )
            )

        runs.append(
            NormalizedRun(
                run_dir=run_dir,
                manifest=manifest,
                packet_files=packet_files,
                trials=trials,
            )
        )

    if experiment_name and not runs:
        raise DatasetValidationError(
            f"No runs found for experiment '{experiment_name}' under: {root}"
        )
    return runs


def load_static_sign_runs(dataset_root: Path) -> list[RunCapture]:
    normalized_runs = load_normalized_runs(dataset_root, experiment_name="static_sign_v1")
    runs: list[RunCapture] = []
    for normalized in normalized_runs:
        manifest = normalized.manifest
        first_trial = normalized.trials[0]
        scenario = manifest.get("scenario", {})
        subject = manifest.get("subject", {})
        capture = manifest.get("capture", {})
        provenance = manifest.get("provenance", {})
        metadata = {
            "schema_version": STATIC_SIGN_SCHEMA_VERSION,
            "experiment_name": "static_sign_v1",
            "label": scenario.get("scenario_id"),
            "run_id": manifest.get("run_id"),
            "subject_id": subject.get("subject_id"),
            "environment_id": scenario.get("room_id"),
            "target_profile": provenance.get("target_profile_id"),
            "environment_profile": manifest.get("extra", {}).get("environment_profile"),
            "device": manifest.get("extra", {}).get("device")
            or (manifest.get("extra", {}).get("environment_profile") or {}).get("board"),
            "chip": manifest.get("extra", {}).get("chip")
            or (manifest.get("extra", {}).get("environment_profile") or {}).get("chip"),
            "serial_dev": provenance.get("device_path"),
            "serial_realpath": provenance.get("device_realpath"),
            "start_time": manifest.get("created_at_utc"),
            "end_time": manifest.get("extra", {}).get("ended_at_utc", manifest.get("created_at_utc")),
            "sampling_params": capture,
            "notes": provenance.get("notes"),
            "records_captured": manifest.get("extra", {}).get("records_captured"),
        }
        validate_run_metadata(metadata)
        runs.append(
            RunCapture(
                run_dir=normalized.run_dir,
                metadata=metadata,
                frames=first_trial.records,
            )
        )
    return runs
