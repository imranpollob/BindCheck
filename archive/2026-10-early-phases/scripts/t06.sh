#!/usr/bin/env bash
# BindCheck T06: export execution records from real Foundry executions, run the trace-based
# coverage checker, compare with the independent Foundry oracle, run checker unit tests.
# usage: bash scripts/t06.sh   (runs scripts/t05.sh first for fixtures/artifacts)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T06; SPEC=bindcheck/spec/batch_backing.spec.json
mkdir -p "$L"
run() { local n="$1"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1; local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); echo "[exit $c] $n"; return "$c"; }

run 10_t05_pipeline bash scripts/t05.sh || { echo "FAILED: see $L/10_t05_pipeline.log"; exit 1; }
# Fresh export: remove any records/oracle/verdicts from earlier runs (incl. the t05 pipeline's forge run).
rm -rf "$L/records" "$L/oracle" "$L"/checker_verdicts.json "$L"/comparison.md "$L"/comparison.json
run 20_forge_test_all forge test -vv; FORGE=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/20_forge_test_all.log" | grep -E '^(Ran |Suite result)'
[ -d "$L/records" ] && [ -d "$L/oracle" ] || { echo "no records exported"; exit 1; }
echo "records: $(ls "$L/records" | wc -l | tr -d ' ')  oracle labels: $(ls "$L/oracle" | wc -l | tr -d ' ')"

run 30_checker node bindcheck/checker.js "$SPEC" "$L/records" "$L/checker_verdicts.json"; CHK=$?
cat "$L/30_checker.log" | sed '1d;$d'
run 40_compare node bindcheck/compare.js "$L/checker_verdicts.json" "$L/oracle" "$L/comparison.md" "$L/comparison.json"; CMP=$?
sed '1d;$d' "$L/40_compare.log"
run 50_checker_unit_tests node --test --test-reporter=spec bindcheck/test/checker.test.js; UT=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_checker_unit_tests.log" | grep -E '^ℹ (tests|pass|fail)'
shasum -a 256 "$SPEC" bindcheck/checker.js bindcheck/compare.js bindcheck/test/checker.test.js test/T06Export.t.sol "$L"/records/*.json "$L"/oracle/*.json > "$L/90_sha256.txt"
if [ $FORGE = 0 ] && [ $CHK = 0 ] && [ $CMP = 0 ] && [ $UT = 0 ]; then echo "T06 OK"; else echo "T06 FAILED (forge=$FORGE checker=$CHK compare=$CMP unit=$UT)"; exit 1; fi
