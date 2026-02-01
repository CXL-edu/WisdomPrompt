#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

SRC_DIR="$ROOT_DIR/.project_info_for_ai/agents"
TARGET_DIRS=(
  "$ROOT_DIR/.cursor/agents"
  "$ROOT_DIR/.claude/agents"
  "$ROOT_DIR/.opencode/agents"
)

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: source dir missing: $SRC_DIR" >&2
  exit 1
fi

shopt -s nullglob
files=("$SRC_DIR"/*.md)
shopt -u nullglob

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No agent JSON files found in $SRC_DIR" >&2
  exit 0
fi

for dir in "${TARGET_DIRS[@]}"; do
  mkdir -p "$dir"
  cp -f "$SRC_DIR"/*.md "$dir"/
done

echo "Synced ${#files[@]} agent file(s) to tool agent directories."
