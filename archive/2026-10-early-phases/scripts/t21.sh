#!/usr/bin/env bash
# T21: source-based message-tail check. Reads circuit sources from git objects (nothing checked out or modified),
# no proofs, no transactions. Usage: bash scripts/t21.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; OUT="$ROOT/results/raw/T21"; SRC="$OUT/src"
REPO="$ROOT/tools/cases/payy-history"
A=c4d2c9021b8fb9988816eb6987a734b830bfce15; B=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36
mkdir -p "$SRC/A_c4d2c90/agg_agg" "$SRC/A_c4d2c90/agg_utxo" "$SRC/B_dcd5d96/agg_agg" "$SRC/B_dcd5d96/agg_utxo" "$SRC/extra"
for pair in A_c4d2c90:$A B_dcd5d96:$B; do n=${pair%%:*}; c=${pair##*:}
  for f in agg_agg agg_utxo; do git -C "$REPO" show "$c:noir/$f/src/main.nr" > "$SRC/$n/$f/main.nr"; done; done
git -C "$REPO" show "$B:noir/agg_final/src/main.nr" > "$SRC/extra/agg_final_B.nr"
{ echo "A=$A"; echo "B=$B"; shasum -a 256 "$SRC"/*/*/main.nr "$SRC"/extra/*.nr; } > "$OUT/10_source_hashes.txt"
T="python3 -I $ROOT/scripts/t21_tailcheck.py"
{
 for c in "A_c4d2c90/agg_agg" "B_dcd5d96/agg_agg" "A_c4d2c90/agg_utxo" "B_dcd5d96/agg_utxo"; do $T "$SRC/$c/main.nr"; echo; done
 echo "## with explicit annotation --message-array messages"
 for c in "A_c4d2c90/agg_agg" "B_dcd5d96/agg_agg" "A_c4d2c90/agg_utxo"; do $T "$SRC/$c/main.nr" --message-array messages | head -1; done
 echo; echo "## out-of-scope circuit (agg_final)"; $T "$SRC/extra/agg_final_B.nr"
} > "$OUT/20_cases.txt"
python3 -I "$ROOT/scripts/t21_mutants.py" "$SRC" > "$OUT/30_mutants.txt" || true
cat "$OUT/20_cases.txt" "$OUT/30_mutants.txt"
