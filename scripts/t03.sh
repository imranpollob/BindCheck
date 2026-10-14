#!/usr/bin/env bash
# BindCheck T03: honest deposit-backing and consumption path. Runs the T02 pipeline first
# (exports verifier, writes calldata fixture, runs T02 tests), then the full forge suite.
# usage: bash scripts/t03.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T03; mkdir -p "$L"; rm -f "$L"/*.log
bash scripts/t02.sh > "$L/10_t02_pipeline.log" 2>&1; c=$?; echo "[exit $c] t02 pipeline (T02 tests + fixtures)"; [ $c = 0 ] || { echo "see $L/10_t02_pipeline.log"; exit 1; }
{ echo '$ forge test -vv'; forge test -vv; echo "exit=$?"; } > "$L/20_forge_test_all.log" 2>&1
code=$(tail -n1 "$L/20_forge_test_all.log" | sed 's/exit=//')
sed 's/\x1b\[[0-9;]*m//g' "$L/20_forge_test_all.log" | grep -E '^(\[|Ran |Suite result)'
shasum -a 256 contracts/BackedBatchConsumer.sol test/BackedBatchConsumer.t.sol test/T01Fixture.sol > "$L/90_sha256.txt"
echo "forge exit=$code"; exit "$code"
