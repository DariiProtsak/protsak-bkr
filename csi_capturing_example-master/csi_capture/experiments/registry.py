from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from csi_capture.core.domain import ExperimentDefinition

CaptureHandler = Callable[[Any], int]
TrainHandler = Callable[[Any], int]
EvalHandler = Callable[[Any], int]
ReportHandler = Callable[[Any], int]
InspectHandler = Callable[[Any], int]
ValidateHandler = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class ExperimentPlugin:
    definition: ExperimentDefinition
    capture_handler: CaptureHandler | None = None
    train_handler: TrainHandler | None = None
    eval_handler: EvalHandler | None = None
    report_handler: ReportHandler | None = None
    inspect_handler: InspectHandler | None = None
    validate_handler: ValidateHandler | None = None
    aliases: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, action: str) -> bool:
        mapping = {
            "capture": self.capture_handler is not None and self.definition.supports_capture,
            "train": self.train_handler is not None and self.definition.supports_train,
            "eval": self.eval_handler is not None and self.definition.supports_evaluate,
            "report": self.report_handler is not None and self.definition.supports_report,
            "inspect": self.inspect_handler is not None and self.definition.supports_inspect,
            "validate-config": self.validate_handler is not None,
        }
        return mapping.get(action, False)


_REGISTRY: dict[str, ExperimentPlugin] = {}
_ALIASES: dict[str, str] = {}


def register_experiment(plugin: ExperimentPlugin) -> ExperimentPlugin:
    experiment_id = plugin.definition.experiment_id
    if experiment_id in _REGISTRY:
        raise ValueError(f"Experiment '{experiment_id}' is already registered")
    _REGISTRY[experiment_id] = plugin
    for alias in plugin.aliases:
        token = alias.strip()
        if not token:
            continue
        if token in _ALIASES:
            raise ValueError(f"Experiment alias '{token}' is already registered")
        _ALIASES[token] = experiment_id
    return plugin


def get_experiment(experiment_id: str) -> ExperimentPlugin:
    token = experiment_id.strip()
    resolved_id = _ALIASES.get(token, token)
    plugin = _REGISTRY.get(resolved_id)
    if plugin is None:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"Unknown experiment '{experiment_id}'. Available: {available}")
    return plugin


def iter_experiments() -> list[ExperimentPlugin]:
    return [_REGISTRY[key] for key in sorted(_REGISTRY)]


def experiment_choices() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
