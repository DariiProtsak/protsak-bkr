"""Experiment-specific adapters and pipelines."""

from .angle import ANGLE_EXPERIMENT, ANGLE_PLUGIN
from .distance import run_distance_capture_config
from .distance import DISTANCE_EXPERIMENT, DISTANCE_PLUGIN
from .presence_v1 import PRESENCE_EXPERIMENT, PRESENCE_PLUGIN
from .registry import ExperimentPlugin, experiment_choices, get_experiment, iter_experiments, register_experiment
from .static_sign_v1 import (
    STATIC_SIGN_EXPERIMENT,
    STATIC_SIGN_LABELS,
    STATIC_SIGN_PLUGIN,
    build_feature_table,
    capture_static_sign_runs,
    dry_run_capture,
    evaluate_static_sign_model,
    train_static_sign_model,
    validate_static_sign_config,
)

for _plugin in (DISTANCE_PLUGIN, ANGLE_PLUGIN, STATIC_SIGN_PLUGIN, PRESENCE_PLUGIN):
    try:
        register_experiment(_plugin)
    except ValueError:
        pass

__all__ = [
    "ANGLE_EXPERIMENT",
    "DISTANCE_EXPERIMENT",
    "ExperimentPlugin",
    "PRESENCE_EXPERIMENT",
    "STATIC_SIGN_EXPERIMENT",
    "STATIC_SIGN_LABELS",
    "build_feature_table",
    "capture_static_sign_runs",
    "dry_run_capture",
    "experiment_choices",
    "evaluate_static_sign_model",
    "get_experiment",
    "iter_experiments",
    "run_distance_capture_config",
    "train_static_sign_model",
    "validate_static_sign_config",
]
