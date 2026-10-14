#!/usr/bin/env bash
# BindCheck T02: export the real verifier from T01's final zkey and run the local-EVM consumer tests.
# usage: bash scripts/t02.sh   (runs scripts/t01.sh first if build/T01 is missing)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T02; B1=build/T01; B2=build/T02
SNARKJS="$ROOT/node_modules/.bin/snarkjs"
FORGE_STD_TAG=v1.9.7; FORGE_STD_COMMIT=77041d2ce690e692d6e03cc812b57d1ddaa4d505
mkdir -p "$L" "$B2" contracts/generated; rm -f "$L"/*.log
step() { local n="$1"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1; local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); echo "[exit $c] $n"; [ "$c" = 0 ] || { echo "FAILED: see $L/$n.log"; exit 1; }; }

[ -f "$B1/circuit_final.zkey" ] && [ -f "$B1/proof.json" ] && [ -f "$B1/public.json" ] || bash scripts/t01.sh || exit 1
if [ ! -d lib/forge-std ]; then mkdir -p lib; git clone --quiet --depth 1 --branch "$FORGE_STD_TAG" https://github.com/foundry-rs/forge-std lib/forge-std || exit 1; fi
[ "$(git -C lib/forge-std rev-parse HEAD)" = "$FORGE_STD_COMMIT" ] || { echo "forge-std not at pinned commit"; exit 1; }

{ forge --version; echo "solc pinned in foundry.toml: $(grep solc_version foundry.toml)"; } > "$L/10_versions.log" 2>&1
step 20_export_verifier "$SNARKJS" zkey export solidityverifier "$B1/circuit_final.zkey" contracts/generated/Groth16Verifier.sol
# calldata order [pA, pB, pC, pubSignals]; wrap the four comma-separated groups into one JSON array
"$SNARKJS" zkey export soliditycalldata "$B1/public.json" "$B1/proof.json" 2> "$L/21_calldata.err" | { printf '['; cat; printf ']'; } > "$B2/calldata.json"
echo "calldata.json bytes: $(wc -c < "$B2/calldata.json")" > "$L/21_calldata.log"
step 30_forge_build forge build
step 40_forge_test forge test -vv --match-path test/BatchConsumer.t.sol
shasum -a 256 contracts/generated/Groth16Verifier.sol contracts/BatchConsumer.sol test/BatchConsumer.t.sol foundry.toml "$B2/calldata.json" "$B1/circuit_final.zkey" > "$L/90_sha256.txt"
sed 's/\x1b\[[0-9;]*m//g' "$L/40_forge_test.log" | grep -E '^(\[|Ran |Suite result)'
