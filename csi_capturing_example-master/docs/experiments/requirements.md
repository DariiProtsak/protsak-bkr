# Requirements Gathering - Unified RSSI/CSI Experiment Program

Date: 2026-03-02  
Scope: distance, angle, and static_sign_v1 experiments with one current hardware target profile and future multi-board support.

## 1) Problem Statement

The project needs one repeatable environment contract across all experiments so that:

- capture logic is reusable
- hardware/software assumptions are explicit
- experiment outputs are comparable across runs
- future ESP32 platform variants can be introduced without redesigning the full pipeline

## 2) Stakeholders

- Experiment operator (runs TX/RX setup and capture scripts)
- Data scientist (uses datasets + metadata for modeling)
- Maintainer (adds new experiment types and target boards)
- Reviewer/QA (validates reproducibility and schema quality)

## 3) Functional Requirements

FR-01 Common target environment profile:
- Every experiment must resolve a `target_profile` (default now: `esp32s3_csi_v1`).
- Profile must define board/chip, firmware paths, serial defaults, and baseline toolchain metadata.

FR-02 Unified metadata propagation:
- Capture outputs must include `target_profile`.
- Run-level metadata/manifests must include full environment profile snapshot.

FR-03 Backward-compatible experiment execution:
- Existing distance and angle workflows must keep working.
- Legacy command entry points remain available.

FR-04 Configuration quality:
- Config parsing must reject unknown target profiles.
- CLI must provide a way to list available target profiles.

FR-05 Documentation and design completeness:
- Requirements, design, plan, and validation artifacts must be versioned.
- Design diagrams must be available in source (`.puml`) and rendered (`.png`) forms.

FR-06 UA experiment execution docs:
- Ukrainian operational docs must exist per experiment type and include commands, setup, and checklists.

## 4) Non-Functional Requirements

NFR-01 Reproducibility:
- Run manifests include config snapshot, git revision, and resolved device path.

NFR-02 Extensibility:
- Adding a new board profile should be additive in one registry module.

NFR-03 Safety/operability:
- Serial access checks must provide actionable Linux/macOS guidance.

NFR-04 Testability:
- Unit tests cover config validation, environment profile resolution, schema checks, and CLI smoke paths.

## 5) Constraints and Assumptions

- Current operational target is a single baseline profile (`esp32s3_csi_v1`).
- Future multi-target support is planned but not yet activated in field runs.
- Hardware-in-the-loop validation depends on lab availability and active TX source.

## 6) Acceptance Criteria

AC-01 `target_profile` exists in:
- config-driven angle/distance runs
- static_sign capture metadata
- run manifests

AC-02 CLI behavior:
- `./tools/exp --list-target-profiles` returns available profiles.
- unknown profile in config is rejected with a clear error.

AC-03 Design package:
- `docs/design/plantuml/*.puml` and matching `.png` are present.

AC-04 QA evidence:
- `python3 -m unittest discover -s tests -p 'test_*.py' -v` passes.
- validation report documents command results.

## 7) Current Requirement Status

- FR-01: PASS
- FR-02: PASS
- FR-03: PASS
- FR-04: PASS
- FR-05: PASS
- FR-06: PASS
- NFR-01: PASS
- NFR-02: PASS
- NFR-03: PASS
- NFR-04: PASS
