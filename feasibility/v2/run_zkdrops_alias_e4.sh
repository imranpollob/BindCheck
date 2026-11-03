#!/usr/bin/env bash
# Rebuild the publicly disclosed zkDrops nullifier-alias bug at the exact
# vulnerable parent of PR #2. Execution uses Hardhat's owned in-process EVM.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$ROOT/feasibility/work/v2/historical/zkdrops"
LIB_REPO="$ROOT/feasibility/work/v2/historical/zkp-merkle-airdrop-lib"
VULNERABLE_COMMIT="4002962fb632578dd12477346d2e5c4159ffb2ef"
FIX_COMMIT="f6f58020911cd2a19e1639f0dc93ec9fca2a9e17"
LIB_COMMIT="c793c2d8aa864ece151d57c04905c973a45a0416"
RUN_ID="zkdrops-alias-e4-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/feasibility-v2/$RUN_ID"
WORK="$OUT/work"
STEPS="$OUT/steps.tsv"
mkdir -p "$WORK"
: > "$STEPS"

run_in_work() {
  local name="$1"
  local expected="$2"
  shift 2
  local log="$OUT/$name.log"
  local observed=0
  set +e
  {
    printf '$ (cd %q &&' "$WORK"
    printf ' %q' "$@"
    printf ')\n'
    (cd "$WORK" && "$@")
  } >"$log" 2>&1
  observed=$?
  set -e
  local status="PASS"
  [[ "$observed" -eq "$expected" ]] || status="FAIL"
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == "PASS" ]]
}

[[ "$(git -C "$REPO" rev-parse "$FIX_COMMIT^")" == "$VULNERABLE_COMMIT" ]]
[[ "$(git -C "$LIB_REPO" rev-parse "$LIB_COMMIT")" == "$LIB_COMMIT" ]]
git -C "$REPO" archive --format=tar --output="$OUT/zkdrops-vulnerable-source.tar" "$VULNERABLE_COMMIT"
tar -xf "$OUT/zkdrops-vulnerable-source.tar" -C "$WORK"
mkdir -p "$WORK/zkp-merkle-airdrop-lib"
git -C "$LIB_REPO" archive "$LIB_COMMIT" | tar -x -C "$WORK/zkp-merkle-airdrop-lib"
cp "$ROOT/feasibility/v2/zkdrops_alias_e4.test.js" "$WORK/test/v2-zkdrops-alias.test.js"

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "workspace_git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "zkdrops_vulnerable_commit=$VULNERABLE_COMMIT"
  echo "zkdrops_fix_commit=$FIX_COMMIT"
  echo "zkdrops_library_commit=$LIB_COMMIT"
  echo "node=$(node --version)"
  echo "npm=$(npm --version)"
  echo "source_tar_sha256=$(shasum -a 256 "$OUT/zkdrops-vulnerable-source.tar" | awk '{print $1}')"
} > "$OUT/environment.txt"

run_in_work 10_npm_ci 0 npm ci --no-audit --no-fund
run_in_work 20_compile 0 "$WORK/node_modules/.bin/hardhat" compile
run_in_work 30_static_screen 0 python3 "$ROOT/feasibility/v2/screen_consumers.py" \
  --repo "$WORK" --output-json "$OUT/static-screen.json" --output-csv "$OUT/static-screen.csv"
export ZKDROPS_COMMIT="$VULNERABLE_COMMIT"
export ZKDROPS_OBSERVATION="$OUT/observation.json"
run_in_work 40_same_proof_double_effect 0 "$WORK/node_modules/.bin/hardhat" test --no-compile test/v2-zkdrops-alias.test.js

shasum -a 256 \
  "$WORK/contracts/PrivateAirdrop.sol" \
  "$WORK/contracts/compiled/MerkVerifier.sol" \
  "$WORK/build/circuit.r1cs" \
  "$WORK/build/circuit_final.zkey" \
  "$WORK/build/circuit_js/circuit.wasm" \
  "$OUT/observation.json" > "$OUT/sha256.txt"

python3 - "$OUT" <<'PY'
import csv
import json
import pathlib
import sys
out = pathlib.Path(sys.argv[1])
steps = []
with (out / "steps.tsv").open(newline="") as handle:
    for name, expected, observed, status in csv.reader(handle, delimiter="\t"):
        steps.append({"name": name, "expected": expected, "observed": observed, "status": status})
screen = json.loads((out / "static-screen.json").read_text())
p3 = [record for record in screen["records"] if record["warnings"]["P3"]]
result = {
    "target": "a16z/zkdrops",
    "historical_public_disclosure": "https://github.com/a16z/zkdrops/pull/2",
    "pattern": "P3 nullifier field alias",
    "verdict": "VIOLATION",
    "evidence_grade": "E4",
    "local_only": True,
    "real_verifier": True,
    "unchanged_consumer": True,
    "same_proof_committed_two_transfers": True,
    "static_check_fired": bool(p3),
    "static_warnings": p3,
    "all_steps_pass": all(step["status"] == "PASS" for step in steps),
    "steps": steps,
}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
if not p3:
    raise SystemExit("P3 static check did not fire")
PY

echo "RESULT: zkDrops vulnerable parent accepted one real proof under nullifier h and h+r and transferred twice"
echo "EVIDENCE: $OUT"
