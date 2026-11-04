#!/usr/bin/env bash
# Record the expected Track B outcomes before implementation or execution.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="$ROOT/dataset/track-b-expected.json"
RUN_ID="protocol-freeze-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/dataset-track-b/$RUN_ID"
mkdir -p "$OUT"

python3 -m json.tool "$EXPECTED" > /dev/null
shasum -a 256 "$EXPECTED" > "$OUT/expected.sha256"
{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "git_status_sha256=$(git -C "$ROOT" status --porcelain=v1 | shasum -a 256 | awk '{print $1}')"
  echo "implementation_present=false"
  echo "eval_analyzer_runs=0"
} > "$OUT/environment.txt"

echo "RESULT: Track B expected outcomes frozen before implementation"
echo "EVIDENCE: $OUT"
