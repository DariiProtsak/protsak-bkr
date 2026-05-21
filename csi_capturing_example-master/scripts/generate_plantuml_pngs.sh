#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUML_DIR="$REPO_ROOT/docs/design/plantuml"
KROKI_URL="https://kroki.io/plantuml/png"

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required to render PlantUML PNG files." >&2
  exit 2
fi

if [[ ! -d "$PUML_DIR" ]]; then
  echo "Error: PlantUML directory not found: $PUML_DIR" >&2
  exit 2
fi

shopt -s nullglob
files=("$PUML_DIR"/*.puml)
shopt -u nullglob

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No .puml files found under $PUML_DIR"
  exit 0
fi

for src in "${files[@]}"; do
  out="${src%.puml}.png"
  echo "Rendering $(basename "$src") -> $(basename "$out")"
  curl -fsSL \
    -H "Content-Type: text/plain" \
    --data-binary @"$src" \
    "$KROKI_URL" \
    -o "$out"
done

echo "Done. Rendered ${#files[@]} diagrams."
