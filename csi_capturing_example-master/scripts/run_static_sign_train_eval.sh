#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATASET_ROOT="data/experiments/static_sign_v1"
DATASET_ID="$(date -u +%Y%m%d)"
MODEL="svm_linear"
WINDOW="1s"
OVERLAP="0.5"
TEST_SIZE="0.3"
SEED="42"
ARTIFACT=""
REPORT=""

usage() {
  cat <<'USAGE'
Train and evaluate static_sign_v1 model from a captured dataset.

Usage:
  scripts/run_static_sign_train_eval.sh [options]

Options:
  --dataset-root <path>   Dataset root base (default: data/experiments/static_sign_v1)
  --dataset-id <id>       Dataset id folder name (default: UTC yyyymmdd)
  --model <name>          Model: svm_linear|logreg (default: svm_linear)
  --window <time>         Feature window (default: 1s)
  --overlap <ratio>       Window overlap [0,1) (default: 0.5)
  --test-size <ratio>     Group test split ratio (default: 0.3)
  --seed <int>            Random seed (default: 42)
  --artifact <path>       Model artifact output path
  --report <path>         Eval report output path
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset-root) DATASET_ROOT="$2"; shift 2 ;;
    --dataset-id) DATASET_ID="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --window) WINDOW="$2"; shift 2 ;;
    --overlap) OVERLAP="$2"; shift 2 ;;
    --test-size) TEST_SIZE="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --artifact) ARTIFACT="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

DATASET_PATH="$DATASET_ROOT/$DATASET_ID"
if [[ ! -d "$DATASET_PATH" ]]; then
  echo "Error: dataset path does not exist: $DATASET_PATH" >&2
  exit 2
fi

if [[ -z "$ARTIFACT" ]]; then
  ARTIFACT="artifacts/static_sign_v1/$DATASET_ID/${MODEL}.pkl"
fi
if [[ -z "$REPORT" ]]; then
  REPORT="out/static_sign_v1/$DATASET_ID/eval_report.json"
fi

cd "$REPO_ROOT"

./tools/exp train \
  --experiment static_sign_v1 \
  --dataset "$DATASET_PATH" \
  --model "$MODEL" \
  --window "$WINDOW" \
  --overlap "$OVERLAP" \
  --test-size "$TEST_SIZE" \
  --seed "$SEED" \
  --artifact "$ARTIFACT"

./tools/exp eval \
  --experiment static_sign_v1 \
  --dataset "$DATASET_PATH" \
  --model "$ARTIFACT" \
  --report "$REPORT"

echo "Train/eval complete."
echo "Artifact: $ARTIFACT"
echo "Report:   $REPORT"
