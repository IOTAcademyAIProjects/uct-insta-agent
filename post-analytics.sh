#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ARGS=()
if [ -n "$1" ]; then
  ARGS+=("$1")
fi
if [ -n "$2" ]; then
  ARGS+=("$2")
fi

python3 pipelines/get-analytics.py "${ARGS[@]}"