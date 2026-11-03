#!/usr/bin/env bash
# Regenerate the tracked consumer and verifier-key census from the frozen,
# ignored 50-repository corpus. This is read-only with respect to third-party
# source and never contacts a deployment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 "$ROOT/feasibility/v2/screen_consumers.py"
python3 "$ROOT/feasibility/v2/scan_p4.py"

python3 - "$ROOT/feasibility/v2/consumer-screen.json" "$ROOT/feasibility/v2/p4-census.json" <<'PY'
import json
import pathlib
import sys

consumer = json.loads(pathlib.Path(sys.argv[1]).read_text())
p4 = json.loads(pathlib.Path(sys.argv[2]).read_text())
assert consumer["summary"]["repositories"] == 50
assert consumer["summary"]["solidity_files_screened"] == 4251
assert consumer["summary"]["functions_screened"] == 42668
assert p4["summary"]["repositories"] == 50
assert p4["summary"]["key_bearing_solidity_files"] == 116
print("RESULT: regenerated 50-repository consumer and P4 source screens")
PY
