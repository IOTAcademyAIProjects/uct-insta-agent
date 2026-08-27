#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$PROJECT_DIR/cli.py" generate "$1" --tone "${2:-casual}"