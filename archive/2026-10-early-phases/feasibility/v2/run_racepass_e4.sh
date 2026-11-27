#!/usr/bin/env bash
# Reproduce the RacePass proof-to-recipient/credential mismatch on owned local
# Anvil only. Source and proof artifacts are copied from the pinned repository.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/feasibility/work/v2/repos/Servesh21__RacePass"
EXPECTED_COMMIT="abd54b5c541ac9d26f938a6bdbd78545526249e5"
EXPECTED_CIRCOM_COMMIT="2eaaa6dface934356972b34cab64b25d382e59de"
RUN_ID="racepass-e4-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/feasibility-v2/$RUN_ID"
WORK="$OUT/work"
PROOFS="$OUT/proofs"
CIRCUIT_BUILD="$OUT/circuit-build"
STEPS="$OUT/steps.tsv"
ANVIL_PID=""

mkdir -p "$WORK" "$PROOFS" "$CIRCUIT_BUILD/age" "$CIRCUIT_BUILD/kyc"
: > "$STEPS"

cleanup() {
  if [[ -n "$ANVIL_PID" ]] && kill -0 "$ANVIL_PID" 2>/dev/null; then
    kill "$ANVIL_PID" 2>/dev/null || true
    wait "$ANVIL_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

run() {
  local name="$1"
  local expected="$2"
  shift 2
  local log="$OUT/$name.log"
  local observed=0
  set +e
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$log" 2>&1
  observed=$?
  set -e
  local status="PASS"
  [[ "$observed" -eq "$expected" ]] || status="FAIL"
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == "PASS" ]]
}

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

COMMIT="$(git -C "$SRC" rev-parse HEAD)"
[[ "$COMMIT" == "$EXPECTED_COMMIT" ]]
[[ "$(git -C "$ROOT/tools/circom-2.1.9" rev-parse HEAD)" == "$EXPECTED_CIRCOM_COMMIT" ]]
git -C "$SRC" archive --format=tar --output="$OUT/racepass-source.tar" "$COMMIT"
tar -xf "$OUT/racepass-source.tar" -C "$WORK"
cp "$ROOT/feasibility/v2/racepass_e4.test.js" "$WORK/test/v2-racepass-e4.test.js"

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "workspace_git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "racepass_commit=$COMMIT"
  echo "racepass_circom_commit=$(git -C "$ROOT/tools/circom-2.1.9" rev-parse HEAD)"
  echo "racepass_circom=$($ROOT/tools/circom-2.1.9/target/release/circom --version)"
  echo "node=$(node --version)"
  echo "npm=$(npm --version)"
  echo "anvil=$(anvil --version | head -1)"
  echo "source_tar_sha256=$(shasum -a 256 "$OUT/racepass-source.tar" | awk '{print $1}')"
} > "$OUT/environment.txt"

run 10_npm_ci 0 npm ci --no-audit --no-fund --prefix "$WORK"
if [[ -d "$WORK/circuits/circomlib" && ! -L "$WORK/circuits/circomlib" ]]; then
  rmdir "$WORK/circuits/circomlib"
  ln -s "$WORK/node_modules/circomlib" "$WORK/circuits/circomlib"
fi
SNARKJS="$WORK/node_modules/.bin/snarkjs"
CIRCOM="$ROOT/tools/circom-2.1.9/target/release/circom"
run 11_age_compile 0 "$CIRCOM" "$WORK/circuits/age_proof/age_check.circom" \
  --r1cs --wasm --sym -o "$CIRCUIT_BUILD/age"
run 12_age_zkey_correspondence 0 "$SNARKJS" zkey verify \
  "$CIRCUIT_BUILD/age/age_check.r1cs" "$WORK/circuits/pot12_final.ptau" \
  "$WORK/frontend/public/circuits/age_proof/age_check_final.zkey"
run 13_kyc_compile 0 "$CIRCOM" "$WORK/circuits/kyc_proof/kyc_check.circom" \
  --r1cs --wasm --sym -o "$CIRCUIT_BUILD/kyc"
run 14_kyc_zkey_correspondence 0 "$SNARKJS" zkey verify \
  "$CIRCUIT_BUILD/kyc/kyc_check.r1cs" "$WORK/circuits/pot12_final.ptau" \
  "$WORK/frontend/public/circuits/kyc_proof/kyc_check_final.zkey"
run 20_make_inputs 0 node "$ROOT/feasibility/v2/racepass_make_inputs.js" "$PROOFS"

AGE_WASM="$WORK/frontend/public/circuits/age_proof/age_check.wasm"
AGE_ZKEY="$WORK/frontend/public/circuits/age_proof/age_check_final.zkey"
KYC_WASM="$WORK/frontend/public/circuits/kyc_proof/kyc_check.wasm"
KYC_ZKEY="$WORK/frontend/public/circuits/kyc_proof/kyc_check_final.zkey"

run 30_age_fullprove 0 "$SNARKJS" groth16 fullprove \
  "$PROOFS/age-input.json" "$AGE_WASM" "$AGE_ZKEY" \
  "$PROOFS/age-proof.json" "$PROOFS/age-public.json"
run 31_age_vkey 0 "$SNARKJS" zkey export verificationkey "$AGE_ZKEY" "$PROOFS/age-vkey.json"
run 32_age_verify 0 "$SNARKJS" groth16 verify \
  "$PROOFS/age-vkey.json" "$PROOFS/age-public.json" "$PROOFS/age-proof.json"
run 40_kyc_fullprove 0 "$SNARKJS" groth16 fullprove \
  "$PROOFS/kyc-input.json" "$KYC_WASM" "$KYC_ZKEY" \
  "$PROOFS/kyc-proof.json" "$PROOFS/kyc-public.json"
run 41_kyc_vkey 0 "$SNARKJS" zkey export verificationkey "$KYC_ZKEY" "$PROOFS/kyc-vkey.json"
run 42_kyc_verify 0 "$SNARKJS" groth16 verify \
  "$PROOFS/kyc-vkey.json" "$PROOFS/kyc-public.json" "$PROOFS/kyc-proof.json"

anvil --silent --port 8545 >"$OUT/anvil.log" 2>&1 &
ANVIL_PID=$!
for _ in $(seq 1 50); do
  if cast chain-id --rpc-url http://127.0.0.1:8545 >"$OUT/anvil-chain-id.txt" 2>"$OUT/anvil-wait.log"; then
    break
  fi
  sleep 0.1
done
if ! kill -0 "$ANVIL_PID" 2>/dev/null; then
  echo "anvil failed to start" >&2
  exit 1
fi

export AGE_PROOF="$PROOFS/age-proof.json"
export AGE_PUBLIC="$PROOFS/age-public.json"
export KYC_PROOF="$PROOFS/kyc-proof.json"
export KYC_PUBLIC="$PROOFS/kyc-public.json"
run_in_work 50_unchanged_consumer_e4 0 "$WORK/node_modules/.bin/hardhat" test \
  --config "$WORK/hardhat.config.js" \
  --network localhost --no-compile "$WORK/test/v2-racepass-e4.test.js"

shasum -a 256 \
  "$SRC/contracts/passes/EventPass.sol" \
  "$SRC/contracts/verifiers/AgeVerifier.sol" \
  "$SRC/contracts/verifiers/KYCVerifier.sol" \
  "$SRC/frontend/public/circuits/age_proof/age_check.wasm" \
  "$SRC/frontend/public/circuits/age_proof/age_check_final.zkey" \
  "$SRC/frontend/public/circuits/kyc_proof/kyc_check.wasm" \
  "$SRC/frontend/public/circuits/kyc_proof/kyc_check_final.zkey" \
  "$CIRCUIT_BUILD/age/age_check.r1cs" "$CIRCUIT_BUILD/kyc/kyc_check.r1cs" \
  "$PROOFS/age-proof.json" "$PROOFS/age-public.json" \
  "$PROOFS/kyc-proof.json" "$PROOFS/kyc-public.json" > "$OUT/sha256.txt"

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
result = {
    "target": "Servesh21/RacePass",
    "pattern": "P1 unproven effect recipient plus unbound credential/replay",
    "verdict": "VIOLATION",
    "evidence_grade": "E4",
    "local_only": True,
    "real_verifiers": True,
    "source_r1cs_zkey_correspondence_verified": True,
    "unchanged_consumer": True,
    "same_proofs_accepted_twice": True,
    "state_effect": "two valid EventPass tokens minted to caller-selected recipients with caller-selected linked credentials",
    "all_steps_pass": all(step["status"] == "PASS" for step in steps),
    "steps": steps,
}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
PY

echo "RESULT: RacePass unchanged consumer accepted the same real proofs twice and committed two caller-directed pass mints"
echo "EVIDENCE: $OUT"
