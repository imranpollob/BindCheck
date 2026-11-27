#!/usr/bin/env bash
# T22-v3 primary evaluation (v2 preserved): compile bounded Payy instances, run the ACIR/SMT
# checker, and compare with the T21 source-pattern baseline.
#
# Usage: bash scripts/t22.sh
# Optional environment: NARGO=/path/to/nargo CVC5=/path/to/cvc5 TLIMIT=300
# The primary run always selects the protocol's cvc5 finite-field backend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_ROOT="$ROOT/results/raw/T22"
RUN_ID="${T22_RUN_ID:-33_v3_primary}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "invalid T22_RUN_ID: $RUN_ID" >&2
  exit 1
fi
OUT="$OUT_ROOT/$RUN_ID"
WORK="$ROOT/build/T22/scratch-$RUN_ID"
PAYY="$ROOT/tools/cases/payy-history"
A="c4d2c9021b8fb9988816eb6987a734b830bfce15"
B="dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36"
NARGO="${NARGO:-$ROOT/tools/noir-1.0.0-beta.14/nargo}"
CVC5="${CVC5:-$ROOT/tools/cvc5-1.4.2-gpl/bin/cvc5}"
TLIMIT="${TLIMIT:-300}"
if [[ "$TLIMIT" != 300 ]]; then echo "v3 frozen primary requires TLIMIT=300" >&2; exit 1; fi
if [[ -n "${T22_ONLY_CASE:-}" ]]; then echo "v3 primary requires all nine cases" >&2; exit 1; fi
# Frozen 4 GiB virtual-memory cap; children inherit it.
ulimit -v 4194304

if [ -e "$OUT" ]; then
  echo "refusing to overwrite existing T22 run: $OUT" >&2
  exit 1
fi
mkdir -p "$OUT" "$ROOT/build/T22" "$ROOT/tools/cases"

if [ ! -d "$PAYY/.git" ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/polybase/payy "$PAYY"
fi

for revision in "$A" "$B"; do
  git -C "$PAYY" cat-file -e "$revision^{commit}" || {
    echo "missing Payy revision: $revision" >&2
    exit 1
  }
done

if [ ! -x "$NARGO" ]; then
  echo "missing pinned nargo: $NARGO" >&2
  echo "Run bash scripts/t09.sh once to fetch Noir 1.0.0-beta.14." >&2
  exit 1
fi

if ! command -v "$CVC5" >/dev/null 2>&1; then
  echo "missing cvc5 executable: $CVC5" >&2
  echo "Run bash scripts/build_cvc5_gpl.sh to build the pinned CoCoA-enabled solver." >&2
  exit 1
fi

FF_SMOKE='(set-logic QF_FF)
(define-sort F () (_ FiniteField 13))
(declare-const x F)
(assert (= x (as ff1 F)))
(check-sat)'
if [ "$(printf '%s\n' "$FF_SMOKE" | "$CVC5" --lang=smt2 --ff-solver=split 2>&1)" != "sat" ]; then
  echo "cvc5 lacks working finite-field support: $CVC5" >&2
  echo "Run bash scripts/build_cvc5_gpl.sh." >&2
  exit 1
fi

if [ -e "$WORK" ]; then echo "refusing existing scratch: $WORK" >&2; exit 1; fi
mkdir -p "$WORK/A" "$WORK/B"
git -C "$PAYY" archive "$A" noir | tar -x -C "$WORK/A"
git -C "$PAYY" archive "$B" noir | tar -x -C "$WORK/B"

{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "host=$(uname -srm)"
  echo "repository_head=$(git rev-parse HEAD)"
  echo "payy_A=$A"
  echo "payy_B=$B"
  echo "nargo=$($NARGO --version | tr '\n' ' ')"
  echo "cvc5=$($CVC5 --version | head -1)"
  echo "t22_backend=cvc5"
  echo "encoding=T22-v3 R1-R6"
  echo "cvc5_ff_solver=split"
  echo "probe_timeout_per_slot_seconds=60"
  echo "memory_limit_virtual_kib=$(ulimit -v)"
  echo "probe_schedule=slot-index order; stop only at supported audited SAT"
  echo "independent_transfer_case=NOT_RUN"
  python3 --version
  git status --short
  git -C "$PAYY" status --short
  shasum -a 256 "$NARGO" "$CVC5"
  cat "$ROOT/results/raw/T22/33_v3_freeze/00_sha256.txt"
  echo "timeout_seconds=$TLIMIT"
  shasum -a 256 \
    scripts/t22_v3_tailspec.py \
    scripts/t22_v3_eval.py \
    scripts/t22_specs/payy_agg_agg.json \
    scripts/t22_specs/payy_agg_utxo.json
} > "$OUT/10_run_manifest.txt"

NARGO="$NARGO" CVC5="$CVC5" T22_BACKEND="cvc5" TLIMIT="$TLIMIT" \
  python3 -u -I scripts/t22_v3_eval.py "$WORK" "$OUT/20_payy_eval.json" \
  2>&1 | tee "$OUT/20_payy_eval.log"

python3 -I - "$OUT/20_payy_eval.json" <<'PY'
import json
import sys

rows = json.load(open(sys.argv[1]))
wrong = [r for r in rows if r["expected"] != r["t22"]]
unknown = [r for r in rows if r["t22"] == "UNKNOWN"]
print(f"cases={len(rows)} mismatches={len(wrong)} unknown={len(unknown)}")
for row in wrong:
    print(f"mismatch: {row['case']}: expected={row['expected']} observed={row['t22']}")
if wrong:
    raise SystemExit(1)
PY
