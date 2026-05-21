from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np


class FeatureExtractionError(ValueError):
    """Raised when CSI feature extraction fails."""


@dataclass(frozen=True)
class WindowFeature:
    run_id: str
    label: str
    window_index: int
    window_start_ms: int
    window_end_ms: int
    frame_count: int
    mean_amp: float
    var_amp: float
    rms_amp: float
    entropy_amp: float


def parse_csi_array(record: dict[str, Any]) -> np.ndarray | None:
    csi = record.get("csi")
    if not isinstance(csi, list) or not csi:
        return None
    try:
        arr = np.asarray(csi, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if arr.ndim != 1 or arr.size < 2:
        return None
    if arr.size % 2 != 0:
        arr = arr[:-1]
    if arr.size < 2:
        return None
    return arr


def iq_to_amplitude(csi_interleaved: Sequence[float]) -> np.ndarray:
    arr = np.asarray(csi_interleaved, dtype=np.float32)
    if arr.ndim != 1 or arr.size < 2:
        raise FeatureExtractionError("CSI array must be 1D with at least two values")
    if arr.size % 2 != 0:
        arr = arr[:-1]
    i_vals = arr[0::2]
    q_vals = arr[1::2]
    return np.sqrt(i_vals * i_vals + q_vals * q_vals, dtype=np.float32)


def _entropy(values: np.ndarray, bins: int = 16) -> float:
    if values.size == 0:
        return 0.0
    hist, _ = np.histogram(values, bins=bins)
    total = float(np.sum(hist))
    if total <= 0.0:
        return 0.0
    probs = hist.astype(np.float64) / total
    probs = probs[probs > 0.0]
    if probs.size == 0:
        return 0.0
    return float(-np.sum(probs * np.log2(probs)))


def _window_ranges(timestamps_ms: np.ndarray, window_ms: int, overlap: float) -> list[tuple[int, int]]:
    if window_ms <= 0:
        raise FeatureExtractionError("window_ms must be > 0")
    if not (0.0 <= overlap < 1.0):
        raise FeatureExtractionError("overlap must be in [0, 1)")
    if timestamps_ms.size == 0:
        return []

    step_ms = max(1, int(math.floor(window_ms * (1.0 - overlap))))
    start = int(timestamps_ms.min())
    stop = int(timestamps_ms.max())
    windows: list[tuple[int, int]] = []

    current = start
    while current <= stop:
        windows.append((current, current + window_ms))
        current += step_ms

    return windows


def extract_window_features(
    frames: Iterable[dict[str, Any]],
    *,
    run_id: str,
    label: str,
    window_ms: int,
    overlap: float,
) -> list[WindowFeature]:
    rows: list[tuple[int, np.ndarray]] = []
    for frame in frames:
        timestamp = frame.get("timestamp")
        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            continue

        csi_array = parse_csi_array(frame)
        if csi_array is None:
            continue
        try:
            amp = iq_to_amplitude(csi_array)
        except FeatureExtractionError:
            continue
        if amp.size == 0:
            continue
        rows.append((ts, amp))

    if not rows:
        raise FeatureExtractionError("No valid CSI frames were available for feature extraction")

    rows.sort(key=lambda item: item[0])
    timestamps = np.asarray([item[0] for item in rows], dtype=np.int64)
    windows = _window_ranges(timestamps, window_ms=window_ms, overlap=overlap)

    features: list[WindowFeature] = []
    for idx, (start_ms, end_ms) in enumerate(windows):
        amps: list[np.ndarray] = []
        for ts, amp in rows:
            if start_ms <= ts < end_ms:
                amps.append(amp)
        if not amps:
            continue

        joined = np.concatenate(amps).astype(np.float32, copy=False)
        mean_amp = float(np.mean(joined))
        var_amp = float(np.var(joined))
        rms_amp = float(np.sqrt(np.mean(joined * joined)))
        entropy_amp = _entropy(joined)

        features.append(
            WindowFeature(
                run_id=run_id,
                label=label,
                window_index=idx,
                window_start_ms=start_ms,
                window_end_ms=end_ms,
                frame_count=len(amps),
                mean_amp=mean_amp,
                var_amp=var_amp,
                rms_amp=rms_amp,
                entropy_amp=entropy_amp,
            )
        )

    if not features:
        raise FeatureExtractionError(
            "No feature windows extracted; increase duration or reduce window size"
        )

    return features


def window_features_to_matrix(features: Sequence[WindowFeature]) -> np.ndarray:
    matrix = np.asarray(
        [
            [
                feat.mean_amp,
                feat.var_amp,
                feat.rms_amp,
                feat.entropy_amp,
            ]
            for feat in features
        ],
        dtype=np.float32,
    )
    if matrix.ndim != 2 or matrix.shape[1] != 4:
        raise FeatureExtractionError("Unexpected feature matrix shape")
    return matrix
