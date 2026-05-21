# Request to ChatGPT Pro: Refactor and Redesign This Project Into a General ESP32 CSI/RSSI Experiment Platform

You are acting as a principal software architect, research-platform engineer, and ML systems engineer. Analyze this repository and refactor it into a clean, extensible system for ESP32 CSI and RSSI experiments of any kind.

## Main Objective

Please redesign this project from a partially unified toolkit into one coherent platform that can:

- capture raw ESP32 CSI/RSSI data from serial streams
- define arbitrary experiment protocols
- validate metadata and schemas
- manage reproducible datasets and artifacts
- run preprocessing, feature extraction, train, evaluation, and reporting
- support new experiment types with minimal new code
- remain practical for student/lab use with two laptops and two ESP32 boards

The final system should not be optimized only for one experiment family. It should become a reusable framework for ESP32 CSI/RSSI research and experimentation.

## Repository Context

Repository path:

- `/home/sagecat/Projects/csi_capturing_example`

Main areas of the repo:

- `csi_capture/`: Python capture, parser, experiment runner, core utilities
- `scripts/`: operational shell scripts for TX/RX boards and experiment workflows
- `tools/`: analysis scripts
- `tests/`: unit tests
- `docs/`: architecture notes, configs, methodology, plans
- `experiments/`: local raw experiment runs
- `out/`: generated reports, figures, tables

## Key Files to Inspect First

- `README.md`
- `docs/unified_experiment_architecture.md`
- `docs/experiments/design.md`
- `docs/repo_organization.md`
- `csi_capture/parser.py`
- `csi_capture/capture.py`
- `csi_capture/experiment.py`
- `csi_capture/cli.py`
- `csi_capture/core/device.py`
- `csi_capture/core/environment.py`
- `csi_capture/core/features.py`
- `csi_capture/core/dataset.py`
- `csi_capture/core/evaluation.py`
- `csi_capture/experiments/static_sign_v1.py`
- `tools/analyze_wifi_distance_measurement.py`
- `tools/analyze_wifi_angular_localization.py`
- `tools/analyze_wifi_static_gesture.py`
- `tools/analyze_wifi_stability_statistics.py`
- `out/distance_measurement/report.md`
- `out/angular_localization_20260302/report.md`
- `out/static_gesture_20260302/report.md`
- `out/stability_statistics/report.md`

## What Already Exists

### Capture and parsing

- `csi_capture/parser.py` parses ESP32 serial lines that contain `CSI_DATA,`.
- It extracts `esp_timestamp`, `mac`, `rssi`, and the CSI list payload.
- `csi_capture/capture.py` captures serial streams into `jsonl` or `csv`.
- Serial device resolution supports `/dev/esp32_csi`, `/dev/ttyACM*`, `/dev/ttyUSB*`, `/dev/tty.usbmodem*`, `/dev/cu.usbmodem*`, `/dev/tty.usbserial*`, `/dev/cu.usbserial*`.

### Environment and device abstraction

- `csi_capture/core/environment.py` defines environment profiles.
- Current baseline profile is `esp32s3_csi_v1`.
- `csi_capture/core/device.py` resolves and validates serial devices.

### Experiment execution

- `csi_capture/experiment.py` supports config-driven `distance` and `angle` capture.
- It writes runs under `experiments/<exp_id>/<experiment_type>/run_<run_id>/...`.
- It produces `manifest.json` and per-trial `capture.jsonl`.
- `csi_capture/cli.py` exposes `tools/exp`.
- `tools/exp capture/train/eval` currently works only for `static_sign_v1`.
- `tools/exp distance` is a compatibility adapter for distance capture configs.

### Static sign pipeline

- `csi_capture/experiments/static_sign_v1.py` implements capture, train, eval, and config validation for binary static sign classification.
- It currently uses a different storage layout:
  `data/experiments/static_sign_v1/<dataset_id>/<label>/run_<run_id>/`
- Each run stores `metadata.json` and `frames.jsonl`.

### Tests

- Unit tests exist for parser, capture, CLI smoke, features, dataset schema, device resolution, and environment profile behavior.

## Verified Experiment Families and Current Results

These are not just planned ideas. The repository already contains working pipelines and generated reports.

### 1. Distance estimation

Relevant areas:

- `tools/analyze_wifi_distance_measurement.py`
- `out/distance_measurement/report.md`

Current evidence:

- Dataset size: `75,000` packets
- Scenarios: `LoS`, `NLoS_furniture`, `NLoS_human`
- Distances: `1.0, 2.0, 3.0, 4.0, 5.0 m`
- Best method: `CSI_kNN_unified`
- Best result: `MAE = 1.3312 m`, `RMSE = 1.6930 m`
- RSSI-only log-distance baselines perform very poorly under scenario changes

Interpretation:

- CSI already provides real value for distance regression in this repo.
- RSSI alone is not reliable enough as the main signal for this use case.

### 2. Angular localization / angle estimation

Relevant areas:

- `tools/analyze_wifi_angular_localization.py`
- `out/angular_localization_20260302/report.md`

Current evidence:

- Dataset size: `4,796` packets
- Unique angle points: `8`
- Runs: `001`, `002`
- Best method: `CSI_kNN`
- Best result: `MAE = 77.1487 deg`
- `P(|error| <= 10 deg) = 0.2801`

Interpretation:

- The pipeline exists end to end, but performance is currently weak.
- This experiment family needs better architecture, metadata, geometry handling, and modeling.

### 3. Static gesture / static sign classification

Relevant areas:

- `tools/analyze_wifi_static_gesture.py`
- `out/static_gesture_20260302/report.md`
- `csi_capture/experiments/static_sign_v1.py`

Current evidence:

- Labels: `baseline`, `hands_up`
- Runs: `10`
- Windows: `400`
- Best method: `CSI_logreg`
- Best result: `accuracy = 0.6813`, `F1 = 0.6792`
- Run-majority accuracy: `0.7500`

Interpretation:

- CSI-based posture or gesture classification is feasible here, but current generalization is only moderate.
- The task is implemented, but the architecture is still too experiment-specific.

### 4. Stability and channel statistics

Relevant areas:

- `tools/analyze_wifi_stability_statistics.py`
- `out/stability_statistics/report.md`
- `tools/analyze_stability_manuscript_hardening.py`
- `out/stability_statistics_hardening/report.md`

Current evidence:

- Dataset size: `75,000` packets
- Focus: distribution shape, temporal stability, fading depth, LoS/NLoS separability
- Result: LoS is more temporally stable than NLoS, but simple scenario separation remains weak
- A hardening report already exists for confidence intervals, bootstrap estimates, effect sizes, and cross-run stability

Interpretation:

- The repo is not only about predictive models.
- It already supports research workflows for channel characterization and statistical validation.

## Real Use Cases This Platform Should Support

The redesign should treat these as first-class experiment families, not side scripts.

Already implemented or partially implemented:

- distance estimation
- angular localization / angle dataset capture
- static gesture or static sign classification
- channel stability analysis
- LoS vs NLoS comparison
- CSI vs RSSI vs fusion benchmarking

Natural next use cases the new architecture should support without major rewrites:

- human presence detection
- occupancy sensing
- motion detection
- activity recognition
- posture classification
- subject-independent gesture recognition
- obstruction or blockage detection
- room or environment fingerprinting
- interference characterization
- firmware / board / antenna comparison
- channel benchmarking across rooms, channels, and layouts
- calibration and repeatability studies
- raw dataset collection for later deep-learning pipelines

## Current Architectural Problems

Please identify these issues explicitly and fix them in the redesign.

### 1. There are multiple parallel pipelines instead of one platform

- `distance` and `angle` use `csi_capture/experiment.py`
- `static_sign_v1` uses `csi_capture/cli.py` plus a separate experiment-specific module
- analysis and reporting mainly live in standalone scripts under `tools/`

### 2. Dataset schemas and storage layouts are inconsistent

Examples:

- `experiment_type` vs `experiment_name`
- `manifest.json` vs `metadata.json`
- `capture.jsonl` vs `frames.jsonl`
- `experiments/...` vs `data/experiments/...`
- run/trial layout for distance and angle vs label/run layout for static sign

### 3. The CLI is only partially unified

- `tools/exp` feels like a general platform entry point
- in reality, `capture/train/eval` are mostly static-sign-specific
- `distance` is handled through a compatibility adapter
- `angle` is available through `python -m csi_capture.experiment`, not through the same unified top-level workflow

### 4. Core abstractions are not yet generic enough

- current abstractions are split between capture-centric and experiment-specific logic
- there is no clear experiment registry or plugin model
- there is no single canonical schema for packet records, run metadata, trials, labels, geometry, subjects, environments, and derived artifacts

### 5. Analysis logic is too script-centric

- major analysis capabilities live in separate scripts in `tools/`
- feature extraction, model training, evaluation, and reporting are not organized as one reusable framework
- adding a new experiment type will likely require cloning patterns instead of composing shared modules

### 6. Reproducibility is present but not standardized across all experiment types

- some paths store `git_commit`, `config_snapshot`, and target profile data
- others use different metadata conventions
- the redesigned platform should make provenance, schema versioning, and run reproducibility uniform

### 7. Naming and repo consistency need cleanup

- some docs still reference the older repo path/name `csi_capture`
- actual repo path is `csi_capturing_example`
- this kind of drift should be cleaned up during the refactor

## What I Want You To Design and Refactor

Please do not just suggest ideas. Produce a concrete target architecture and a migration/refactor plan that can be implemented in this repo.

### A. A unified domain model

Define a clean shared model for:

- device profile
- environment profile
- experiment definition
- run
- trial
- acquisition block
- packet record
- subject
- scenario
- label set
- ground truth
- geometry
- derived features
- trained model artifact
- evaluation report

Make it generic enough for regression, classification, localization, detection, and statistics-only studies.

### B. A single extensible experiment framework

I want one framework that supports:

- capture-only experiments
- capture plus analysis experiments
- train/eval pipelines
- report-only pipelines for existing datasets
- experiment plugins or registries for adding new experiment kinds

The framework should let me add a new experiment type such as `presence_v1` or `nlos_classifier_v1` without building another parallel architecture.

### C. A canonical dataset and artifact layout

Design one standard layout for:

- raw capture data
- normalized packet data
- run metadata
- trial metadata
- derived features
- trained models
- metrics
- figures
- reports

If backward compatibility is needed, propose importers/adapters rather than keeping long-term duplication.

### D. A truly unified CLI

Design a CLI that consistently supports the whole lifecycle, for example:

- device discovery
- profile discovery
- experiment validation
- capture
- preprocess
- feature extraction
- train
- evaluate
- report
- replay or inspect

The exact command names are up to you, but the workflow should be coherent and not split between multiple unrelated entry points.

### E. A reusable processing pipeline

Separate these concerns clearly:

- serial acquisition
- raw packet parsing
- metadata injection
- schema validation
- feature extraction
- model training
- evaluation
- reporting

Please recommend which current modules should be kept, which should be moved, which should be merged, and which should be deleted.

### F. A migration path from the current repo

I need a practical phased migration plan, not a rewrite fantasy.

Please provide:

- phase 1: minimum viable unification with low breakage
- phase 2: schema consolidation and adapters
- phase 3: experiment plugin architecture
- phase 4: cleanup of legacy paths and docs

For each phase, show which files should change and why.

## Constraints and Requirements

The redesigned system must:

- preserve support for ESP32 CSI serial parsing from `CSI_DATA,` lines
- preserve the two-laptop workflow with TX and RX nodes
- preserve Linux and macOS serial-device usability
- keep support for the current baseline profile `esp32s3_csi_v1`
- support additional hardware or environment profiles later
- avoid breaking existing data if adapters can preserve it
- maintain reproducibility metadata such as git revision, device path, profile, notes, scenario tags, and ground truth
- be testable with unit tests and smoke tests
- be understandable by students and not overengineered into an academic framework nobody can operate

## Specific Pain Points I Want Solved

Please directly solve these repo-specific issues:

- unify `distance`, `angle`, and `static_sign_v1` under one architecture
- unify metadata naming and schema versioning
- unify storage layout and artifact conventions
- turn `tools/` analysis scripts into reusable platform modules where appropriate
- keep enough backward compatibility to avoid destroying already collected datasets
- make it easy to add future experiment types without copy-pasting a whole new pipeline
- make CSI-only, RSSI-only, and fusion workflows first-class citizens
- support both predictive tasks and statistics-only studies

## Expected Deliverables From You

Please return:

1. an architecture audit of the current repo
2. a proposed target architecture with clear module boundaries
3. a recommended directory tree
4. a canonical schema design for datasets and metadata
5. a unified CLI design
6. a migration map from current files to target files
7. a prioritized refactor plan with implementation order
8. concrete code-level recommendations, not only high-level theory
9. examples of how new experiment types would be added under the new system
10. recommended tests to add or update

If you can implement code changes in-place, start with the highest-leverage refactor slices first and keep the repo runnable after each step.

## Success Criteria

I will consider the redesign successful if:

- the repo becomes one coherent experimentation platform instead of several parallel mini-projects
- the same system can support distance, angle, static sign, and future experiment types
- capture, preprocessing, train, eval, and reporting feel like one product
- schemas and file layouts become consistent
- adding a new experiment does not require a new architecture
- existing experiment evidence and reports remain usable

Please be opinionated, practical, and explicit about tradeoffs.
