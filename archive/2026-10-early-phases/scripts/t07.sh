#!/usr/bin/env bash
# BindCheck T07: direct Foundry invariant baseline vs the trace checker over a finite enumeration.
# usage: bash scripts/t07.sh   (runs scripts/t05.sh first for fixtures/artifacts)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T07; SPEC=bindcheck/spec/batch_backing.spec.json
mkdir -p "$L"
ms() { python3 -c 'import time;print(int(time.time()*1000))'; }
run() { local n="$1"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1; local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); echo "[exit $c] $n"; return "$c"; }

run 10_t05_pipeline bash scripts/t05.sh || { echo "FAILED: see $L/10_t05_pipeline.log"; exit 1; }
# Full regression (all suites, includes the T06 exporter and the T07 suite).
run 20_forge_regression forge test; REG=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/20_forge_regression.log" | grep -E '^(Ran [0-9]+ test suites|Suite result: FAILED)'

# Clean slate for the experiment itself.
rm -rf "$L/records" "$L/baseline" "$L/analysis" "$L/summary.json"

# Execution + export + baseline evaluation (one Foundry run; fresh state per case).
T0=$(ms)
run 30_forge_enumeration forge test --match-path test/T07Baseline.t.sol; ENUM=$?
T1=$(ms)
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_enumeration.log" | grep -E '^(\[|Ran |Suite result)'
FORGE_REPORTED=$(sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_enumeration.log" | grep -m1 'Suite result' | sed -E 's/.*finished in ([^ ]+) .*/\1/')
echo "records: $(ls "$L/records" | wc -l | tr -d ' ')  baseline results: $(ls "$L/baseline" | wc -l | tr -d ' ')"

# Verifier-result enforcement evidence (code excerpts; behavior is tested by test_eachEvaluatedConsumerEnforcesTheVerifierResult).
{
  echo "# Lines where each evaluated consumer enforces the verifier's boolean result"
  for f in contracts/BackedBatchConsumer.sol contracts/research/MutantBackedBatchConsumer.sol contracts/research/RepairedPrefixBatchConsumer.sol; do
    echo "## $f"; grep -n 'verifyProof(pA' "$f"; grep -n 'error InvalidProof' "$f"
  done
} > "$L/verifier_enforcement.txt"

# Checker + comparison (timed separately, whole process wall clock; in-process timing is inside the output).
T2=$(ms)
run 40_compare node bindcheck/compare_baseline.js "$SPEC" "$L/records" "$L/baseline" "$L/analysis"; CMP=$?
T3=$(ms)
cat "$L/analysis/comparison.md"
run 50_checker_unit_tests node --test --test-reporter=spec bindcheck/test/checker.test.js; UT=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_checker_unit_tests.log" | grep -E '^ℹ (tests|pass|fail)'

# Code size (non-blank, non-comment-only lines) -- a rough proxy for effort, not a time measurement.
loc() { grep -v -E '^\s*(//|\*|/\*|$)' "$1" | wc -l | tr -d ' '; }
jloc() { grep -v -E '^\s*$' "$1" | wc -l | tr -d ' '; }
node -e '
const [reg, enumc, cmpc, ut, forgeRep, t0, t1, t2, t3, bl, obs, enumt, chk, spec, cmps, specAssump] = process.argv.slice(1);
const cmp = JSON.parse(require("fs").readFileSync("results/raw/T07/analysis/comparison.json")).summary;
const out = {
  exitStatus: { regression: +reg, enumeration: +enumc, compare: +cmpc, checkerUnitTests: +ut },
  timing: { executionExportBaselineWallMs_forgeInvocation: (+t1) - (+t0), forgeReportedSuiteTime: forgeRep,
            checkerInProcess: cmp.timing, checkerAndCompareProcessWallMs: (+t3) - (+t2),
            note: "execution/export/baseline time includes JSON writing and the baseline evaluation; compile is cached. Elapsed task time not measured." },
  codeLines_nonBlankNonComment: { baselineProperty_sol: +bl, observationExporter_sol: +obs, enumerationHarness_T07Baseline_sol: +enumt, checker_js: +chk, spec_json_nonblank: +spec, compare_baseline_js: +cmps },
  summary: cmp,
};
require("fs").writeFileSync("results/raw/T07/summary.json", JSON.stringify(out, null, 2) + "\n");
' "$REG" "$ENUM" "$CMP" "$UT" "${FORGE_REPORTED:-unknown}" "$T0" "$T1" "$T2" "$T3" "$(loc test/BaselineProperty.sol)" "$(loc test/Observation.sol)" "$(loc test/T07Baseline.t.sol)" "$(loc bindcheck/checker.js)" "$(jloc $SPEC)" "$(loc bindcheck/compare_baseline.js)" 0
node -e 'const s=require("./results/raw/T07/summary.json"); console.log(JSON.stringify({timing:s.timing,codeLines:s.codeLines_nonBlankNonComment},null,1))'
shasum -a 256 test/BaselineProperty.sol test/Observation.sol test/T07Baseline.t.sol bindcheck/checker.js bindcheck/compare_baseline.js "$SPEC" > "$L/90_sha256.txt"
if [ $REG = 0 ] && [ $ENUM = 0 ] && [ $CMP = 0 ] && [ $UT = 0 ]; then echo "T07 OK"; else echo "T07 FAILED (regression=$REG enumeration=$ENUM compare=$CMP unit=$UT)"; exit 1; fi
