#!/usr/bin/env bash
# BindCheck T05: repaired prefix consumer + padded second proof from the SAME circuit and T01 zkey.
# usage: bash scripts/t05.sh   (runs the T02 pipeline first; build/T01 artifacts and fixtures are preserved)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T05; B1=build/T01; B5=build/T05; SNARKJS="$ROOT/node_modules/.bin/snarkjs"
mkdir -p "$L" "$B5"; rm -f "$L"/*.log "$L"/*.diff "$L"/*.txt
run() { local n="$1"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1; local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); echo "[exit $c] $n"; [ "$c" = 0 ] || { echo "FAILED: see $L/$n.log"; exit 1; }; }

run 10_t02_pipeline bash scripts/t02.sh
# Additional ordinary proof: unchanged circuit, T01 wasm/r1cs/zkey/verification key.
run 20_make_padded_input node scripts/make_input_padded.js "$B5/input.json"
run 21_witness "$SNARKJS" wtns calculate "$B1/batch_deposit_js/batch_deposit.wasm" "$B5/input.json" "$B5/witness.wtns"
run 22_wtns_check "$SNARKJS" wtns check "$B1/batch_deposit.r1cs" "$B5/witness.wtns"
run 23_prove "$SNARKJS" groth16 prove "$B1/circuit_final.zkey" "$B5/witness.wtns" "$B5/proof.json" "$B5/public.json"
run 24_offchain_verify "$SNARKJS" groth16 verify "$B1/verification_key.json" "$B5/public.json" "$B5/proof.json"
run 25_public_order node scripts/check_public_order.js "$B5/input.json" "$B5/public.json" "$B1/batch_deposit.sym" "$B1/verification_key.json"
"$SNARKJS" zkey export soliditycalldata "$B5/public.json" "$B5/proof.json" 2> "$L/26_calldata.err" | { printf '['; cat; printf ']'; } > "$B5/calldata.json"
echo "calldata.json bytes: $(wc -c < "$B5/calldata.json")" > "$L/26_calldata.log"
# Original proof fixtures must be untouched by this task.
( cd "$ROOT" && shasum -a 256 "$B1/proof.json" "$B1/public.json" "$B1/circuit_final.zkey" build/T02/calldata.json ) > "$L/27_original_fixture_sha256.txt"

# Minimal repair diff: T04 mutant -> repaired consumer.
diff -u contracts/research/MutantBackedBatchConsumer.sol contracts/research/RepairedPrefixBatchConsumer.sol > "$L/repair.diff"
echo "repair.diff: $(grep -c '^[+-][^+-]' "$L/repair.diff") changed lines"

{ echo '$ forge test -vv'; forge test -vv; echo "exit=$?"; } > "$L/30_forge_test_all.log" 2>&1
code=$(tail -n1 "$L/30_forge_test_all.log" | sed 's/exit=//')
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_test_all.log" | grep -E '^(\[|Ran |Suite result)'
shasum -a 256 contracts/research/RepairedPrefixBatchConsumer.sol test/RepairedPrefixBatchConsumer.t.sol scripts/make_input_padded.js "$L/repair.diff" "$B5/proof.json" "$B5/public.json" > "$L/90_sha256.txt"
[ "$code" = 0 ] || { echo "T05 FAILED (forge exit=$code)"; exit 1; }
echo "T05 OK"
