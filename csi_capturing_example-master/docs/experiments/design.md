# Design - Common Environment for All Experiments

Date: 2026-03-02

## 1) Design Intent

Standardize all experiment types around one environment contract now, while keeping extension path for multiple ESP32 platforms later.

Current baseline profile:

- `esp32s3_csi_v1`

## 2) Core Design Decisions

DD-01 Single source of truth for platform assumptions:

- Implemented in `csi_capture/core/environment.py`.
- Holds board/chip/firmware/default serial/default baud metadata.

DD-02 Config-driven environment selection:

- `target_profile` is supported in config-driven angle/distance runs.
- Unknown profile ids fail fast at config validation/normalization.

DD-03 Metadata propagation:

- `manifest.json` includes `target_profile` and `environment_profile`.
- static_sign run metadata includes the same information.

DD-04 Backward compatibility:

- Existing commands remain valid when `target_profile` is omitted.
- Default profile is auto-applied.

## 3) Diagram Set (PlantUML + PNG)

- System context: [`01_system_context.puml`](../design/plantuml/01_system_context.puml), [`01_system_context.png`](../design/plantuml/01_system_context.png)
- Component architecture: [`02_component_architecture.puml`](../design/plantuml/02_component_architecture.puml), [`02_component_architecture.png`](../design/plantuml/02_component_architecture.png)
- Capture sequence: [`03_capture_sequence.puml`](../design/plantuml/03_capture_sequence.puml), [`03_capture_sequence.png`](../design/plantuml/03_capture_sequence.png)
- Data model: [`04_data_model.puml`](../design/plantuml/04_data_model.puml), [`04_data_model.png`](../design/plantuml/04_data_model.png)
- Validation workflow: [`05_validation_workflow.puml`](../design/plantuml/05_validation_workflow.puml), [`05_validation_workflow.png`](../design/plantuml/05_validation_workflow.png)

## 4) Extension Path for Future Profiles

To add another board/platform:

1. Add one entry in `_ENVIRONMENT_PROFILES` (new `profile_id`).
2. Keep capture code unchanged unless hardware requires a new parser/transport.
3. Update docs/config templates and QA validation matrix.

## 5) Tradeoffs

- Chosen: simple in-repo registry (fast, explicit, easy review).
- Deferred: external registry/config service (unneeded complexity at current scale).
