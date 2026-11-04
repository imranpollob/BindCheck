#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -x "$ROOT/dataset/raw/venv/bin/python" ]] || "$ROOT/dataset/setup_dataset.sh"
exec "$ROOT/dataset/raw/venv/bin/python" "$ROOT/dataset/census_sourcify.py"
