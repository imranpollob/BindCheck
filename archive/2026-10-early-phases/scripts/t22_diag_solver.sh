#!/usr/bin/env bash
# T22-v2 diagnosis: solve one SMT query with the pinned cvc5 under a wall-clock and memory limit, recording the result.
#
# Usage: bash scripts/t22_diag_solver.sh QUERY.smt2 SECONDS MODE OUT_PREFIX
#   MODE is the cvc5 finite-field solver: gb (default mode) or split.
# Runs: (ulimit -v 4000000; timeout -s KILL SECONDS cvc5 --lang=smt2 --ff-solver=MODE QUERY)
# Writes OUT_PREFIX.out (solver output) and OUT_PREFIX.status (one line); refuses to overwrite.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CVC5="${CVC5:-$ROOT/tools/cvc5-1.4.2-gpl/bin/cvc5}"
Q="$1"; SECONDS_LIMIT="$2"; MODE="$3"; PREFIX="$4"

for f in "$PREFIX.out" "$PREFIX.status"; do
  if [ -e "$f" ]; then echo "refusing to overwrite $f" >&2; exit 1; fi
done
s=$(date +%s.%N)
( ulimit -v 4000000; timeout -s KILL "$SECONDS_LIMIT" "$CVC5" --lang=smt2 --ff-solver="$MODE" "$Q" > "$PREFIX.out" 2>&1 ); st=$?
e=$(date +%s.%N)
echo "query=$Q mode=$MODE limit_s=$SECONDS_LIMIT exit=$st seconds=$(echo "$e - $s" | bc) query_sha256=$(sha256sum "$Q" | cut -d' ' -f1) first_line=$(head -1 "$PREFIX.out")" | tee "$PREFIX.status"
