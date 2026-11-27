#!/usr/bin/env bash
# BindCheck T04: research-authored coverage failure (mutant consumer) vs correct T03 consumer.
# usage: bash scripts/t04.sh   (runs the T02 pipeline first to ensure verifier/fixtures exist)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T04; B1=build/T01; SNARKJS="$ROOT/node_modules/.bin/snarkjs"
mkdir -p "$L"; rm -f "$L"/*.log "$L"/*.diff
run() { local n="$1"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1; local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); echo "[exit $c] $n"; [ "$c" = 0 ] || { echo "FAILED: see $L/$n.log"; exit 1; }; }

run 10_t02_pipeline bash scripts/t02.sh
# The proof the contracts receive is the T01 proof: re-check witness satisfaction and off-chain verification now.
run 20_wtns_check "$SNARKJS" wtns check "$B1/batch_deposit.r1cs" "$B1/witness.wtns"
run 21_offchain_verify "$SNARKJS" groth16 verify "$B1/verification_key.json" "$B1/public.json" "$B1/proof.json"
run 22_public_order node scripts/check_public_order.js "$B1/input.json" "$B1/public.json" "$B1/batch_deposit.sym" "$B1/verification_key.json"

# Minimal diff showing the mutation (correct T03 contract -> research mutant).
diff -u contracts/BackedBatchConsumer.sol contracts/research/MutantBackedBatchConsumer.sol > "$L/mutation.diff"
echo "mutation.diff: $(grep -c '^[+-][^+-]' "$L/mutation.diff") changed lines"

{ echo '$ forge test -vv'; forge test -vv; echo "exit=$?"; } > "$L/30_forge_test_all.log" 2>&1
code=$(tail -n1 "$L/30_forge_test_all.log" | sed 's/exit=//')
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_test_all.log" | grep -E '^(\[|Ran |Suite result)'

# Identical proof/public-input data for correct, mutant and control calls.
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_test_all.log" | grep -A1 'calldata hash' | grep -o '0x[0-9a-f]\{64\}' > "$L/40_calldata_hashes.txt"
n=$(sort -u "$L/40_calldata_hashes.txt" | wc -l | tr -d ' '); t=$(wc -l < "$L/40_calldata_hashes.txt" | tr -d ' ')
echo "calldata hashes logged: $t, distinct: $n"
shasum -a 256 contracts/research/MutantBackedBatchConsumer.sol test/MutantBackedBatchConsumer.t.sol "$L/mutation.diff" > "$L/90_sha256.txt"
[ "$code" = 0 ] && [ "$n" = 1 ] && [ "$t" = 3 ] || { echo "T04 FAILED (forge exit=$code)"; exit 1; }
echo "T04 OK"
