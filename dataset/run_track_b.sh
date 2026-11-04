#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPSC="$ROOT/feasibility/work/v2/repos/NethermindEth__spsc/circuits/circom"

if [[ ! -d "$SPSC/node_modules/circomlib" ]]; then
  (cd "$SPSC" && npm ci --ignore-scripts --no-audit --no-fund)
fi

exec python3 "$ROOT/dataset/run_track_b.py"
