#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEVICE=""
TARGET_PROFILE="esp32s3_csi_v1"
DATASET_ROOT="data/experiments"
DATASET_ID="$(date -u +%Y%m%d)"
RUNS_PER_LABEL=5
DURATION="20s"
SUBJECT_ID=""
ENVIRONMENT_ID=""
NOTES=""
DRY_RUN_PACKETS=5
DRY_RUN_TIMEOUT="10s"
SKIP_DRY_RUN=0

usage() {
  cat <<'USAGE'
Run static_sign_v1 capture protocol: baseline then hands_up.

Usage:
  scripts/run_static_sign_protocol.sh [options]

Options:
  --device <path>            Serial device (default: auto-detect, prefers /dev/esp32_csi)
  --target-profile <id>      Target environment profile (default: esp32s3_csi_v1)
  --dataset-root <path>      Dataset root (default: data/experiments)
  --dataset-id <id>          Dataset id (default: UTC yyyymmdd)
  --runs <n>                 Runs per label (default: 5)
  --duration <time>          Duration per run (default: 20s)
  --subject-id <id>          Optional subject id
  --environment-id <id>      Optional environment id
  --notes <text>             Optional notes attached to metadata
  --dry-run-packets <n>      Packets for serial dry-run (default: 5)
  --dry-run-timeout <time>   Dry-run timeout (default: 10s)
  --skip-dry-run             Skip dry-run probe
  -h, --help                 Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="$2"; shift 2 ;;
    --target-profile) TARGET_PROFILE="$2"; shift 2 ;;
    --dataset-root) DATASET_ROOT="$2"; shift 2 ;;
    --dataset-id) DATASET_ID="$2"; shift 2 ;;
    --runs) RUNS_PER_LABEL="$2"; shift 2 ;;
    --duration) DURATION="$2"; shift 2 ;;
    --subject-id) SUBJECT_ID="$2"; shift 2 ;;
    --environment-id) ENVIRONMENT_ID="$2"; shift 2 ;;
    --notes) NOTES="$2"; shift 2 ;;
    --dry-run-packets) DRY_RUN_PACKETS="$2"; shift 2 ;;
    --dry-run-timeout) DRY_RUN_TIMEOUT="$2"; shift 2 ;;
    --skip-dry-run) SKIP_DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if ! [[ "$RUNS_PER_LABEL" =~ ^[0-9]+$ ]] || [[ "$RUNS_PER_LABEL" -le 0 ]]; then
  echo "Error: --runs must be a positive integer" >&2
  exit 2
fi

if ! [[ "$DRY_RUN_PACKETS" =~ ^[0-9]+$ ]] || [[ "$DRY_RUN_PACKETS" -le 0 ]]; then
  echo "Error: --dry-run-packets must be a positive integer" >&2
  exit 2
fi

cd "$REPO_ROOT"

device_args=()
if [[ -n "$DEVICE" ]]; then
  device_args=(--device "$DEVICE")
fi

capture_label() {
  local label="$1"
  local label_notes
  if [[ -n "$NOTES" ]]; then
    label_notes="$NOTES | label=$label"
  else
    label_notes="label=$label"
  fi

  local cmd=(
    ./tools/exp capture
    --experiment static_sign_v1
    --target-profile "$TARGET_PROFILE"
    --label "$label"
    --runs "$RUNS_PER_LABEL"
    --duration "$DURATION"
    --dataset-root "$DATASET_ROOT"
    --dataset-id "$DATASET_ID"
    --notes "$label_notes"
  )
  if [[ ${#device_args[@]} -gt 0 ]]; then
    cmd+=("${device_args[@]}")
  fi

  if [[ -n "$SUBJECT_ID" ]]; then
    cmd+=(--subject-id "$SUBJECT_ID")
  fi
  if [[ -n "$ENVIRONMENT_ID" ]]; then
    cmd+=(--environment-id "$ENVIRONMENT_ID")
  fi

  echo "Running: ${cmd[*]}"
  "${cmd[@]}"
}

echo "Dataset: $DATASET_ROOT/static_sign_v1/$DATASET_ID"

echo "Checking devices..."
./tools/exp --list-devices

if [[ "$SKIP_DRY_RUN" -eq 0 ]]; then
  echo "Running dry-run serial probe..."
  cmd=(
    ./tools/exp capture
    --experiment static_sign_v1
    --target-profile "$TARGET_PROFILE"
    --dry-run-packets "$DRY_RUN_PACKETS"
    --dry-run-timeout "$DRY_RUN_TIMEOUT"
  )
  if [[ ${#device_args[@]} -gt 0 ]]; then
    cmd+=("${device_args[@]}")
  fi
  "${cmd[@]}"
fi

read -r -p "Set subject to BASELINE pose (back to receiver, neutral stance). Press Enter to start capture..."
capture_label "baseline"

read -r -p "Set subject to HANDS_UP sign (back to receiver, consistent pose). Press Enter to start capture..."
capture_label "hands_up"

echo "Capture protocol complete. Dataset root: $DATASET_ROOT/static_sign_v1/$DATASET_ID"
