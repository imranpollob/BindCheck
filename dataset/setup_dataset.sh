#!/usr/bin/env bash
# Install the pinned local-only Python dependency used for remote Sourcify
# Parquet queries. The virtual environment is ignored under dataset/raw/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/dataset/raw/venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check 'duckdb==1.4.1'
"$VENV/bin/python" - <<'PY'
import duckdb
assert duckdb.__version__ == "1.4.1"
print(f"duckdb={duckdb.__version__}")
PY
