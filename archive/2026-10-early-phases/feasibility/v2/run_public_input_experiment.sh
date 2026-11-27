#!/usr/bin/env bash
# Test whether Groth16 verification binds a declared public input that has no
# occurrence in the compiled circuit constraints. Local toy setup only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CIRCOM="$ROOT/tools/circom-src/target/release/circom"
SNARKJS="$ROOT/node_modules/.bin/snarkjs"
SOURCE="$ROOT/feasibility/v2/public-input-unused.circom"
RUN_ID="public-input-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/feasibility-v2/$RUN_ID"
BUILD="$OUT/build"
STEPS="$OUT/steps.tsv"

mkdir -p "$BUILD"
: > "$STEPS"

if [[ ! -x "$CIRCOM" ]]; then
  echo "missing pinned circom binary: $CIRCOM" >&2
  exit 2
fi
if [[ ! -x "$SNARKJS" ]]; then
  echo "missing pinned snarkjs binary: $SNARKJS (run npm ci)" >&2
  exit 2
fi

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
  local result="PASS"
  if [[ "$observed" -ne "$expected" ]]; then
    result="FAIL"
  fi
  printf '%s\texpected=%s\tobserved=%s\t%s\n' \
    "$name" "$expected" "$observed" "$result" | tee -a "$STEPS"
  [[ "$result" == "PASS" ]]
}

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "uname=$(uname -a)"
  echo "node=$(node --version)"
  echo "npm=$(npm --version)"
  echo "circom=$($CIRCOM --version)"
  echo "circom_source=$(git -C "$ROOT/tools/circom-src" rev-parse HEAD)"
  echo "snarkjs=$(node -p "require('$ROOT/package-lock.json').packages['node_modules/snarkjs'].version")"
} > "$OUT/environment.txt"

printf '{"bound":"1","unused":"7"}\n' > "$BUILD/input.json"

run 10_compile 0 "$CIRCOM" "$SOURCE" --r1cs --wasm --sym --O0 -o "$BUILD"
run 11_r1cs_info 0 "$SNARKJS" r1cs info "$BUILD/public-input-unused.r1cs"
run 12_r1cs_print 0 "$SNARKJS" r1cs print "$BUILD/public-input-unused.r1cs" "$BUILD/public-input-unused.sym"
run 20_ptau_new 0 "$SNARKJS" powersoftau new bn128 8 "$BUILD/pot_0000.ptau"
run 21_ptau_contribute 0 "$SNARKJS" powersoftau contribute \
  "$BUILD/pot_0000.ptau" "$BUILD/pot_0001.ptau" \
  --name="bindcheck-v2-unused-public-toy" \
  -e="public deterministic experiment entropy; not a secure setup"
run 22_ptau_prepare 0 "$SNARKJS" powersoftau prepare phase2 \
  "$BUILD/pot_0001.ptau" "$BUILD/pot_final.ptau"
run 30_zkey_setup 0 "$SNARKJS" groth16 setup \
  "$BUILD/public-input-unused.r1cs" "$BUILD/pot_final.ptau" "$BUILD/circuit_0000.zkey"
run 31_zkey_contribute 0 "$SNARKJS" zkey contribute \
  "$BUILD/circuit_0000.zkey" "$BUILD/circuit_final.zkey" \
  --name="bindcheck-v2-unused-public-toy" \
  -e="public deterministic phase2 entropy; not a secure setup"
run 32_vkey_export 0 "$SNARKJS" zkey export verificationkey \
  "$BUILD/circuit_final.zkey" "$BUILD/verification_key.json"
run 40_witness 0 "$SNARKJS" wtns calculate \
  "$BUILD/public-input-unused_js/public-input-unused.wasm" \
  "$BUILD/input.json" "$BUILD/witness.wtns"
run 41_witness_check 0 "$SNARKJS" wtns check \
  "$BUILD/public-input-unused.r1cs" "$BUILD/witness.wtns"
run 42_prove 0 "$SNARKJS" groth16 prove \
  "$BUILD/circuit_final.zkey" "$BUILD/witness.wtns" \
  "$BUILD/proof.json" "$BUILD/public.json"
run 43_verify_original 0 "$SNARKJS" groth16 verify \
  "$BUILD/verification_key.json" "$BUILD/public.json" "$BUILD/proof.json"

node - "$BUILD/public.json" "$BUILD/public_unused_mutated.json" <<'NODE'
const fs = require("fs");
const values = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
if (values.length !== 2) throw new Error(`expected two public values, got ${values.length}`);
values[1] = (BigInt(values[1]) + 123456n).toString();
fs.writeFileSync(process.argv[3], JSON.stringify(values) + "\n");
NODE
run 50_verify_unused_mutated 1 "$SNARKJS" groth16 verify \
  "$BUILD/verification_key.json" "$BUILD/public_unused_mutated.json" "$BUILD/proof.json"

node - "$BUILD/public.json" "$BUILD/public_bound_mutated.json" <<'NODE'
const fs = require("fs");
const values = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
if (values.length !== 2) throw new Error(`expected two public values, got ${values.length}`);
values[0] = (BigInt(values[0]) + 1n).toString();
fs.writeFileSync(process.argv[3], JSON.stringify(values) + "\n");
NODE
run 51_verify_bound_mutated 1 "$SNARKJS" groth16 verify \
  "$BUILD/verification_key.json" "$BUILD/public_bound_mutated.json" "$BUILD/proof.json"

# A malicious prover can still choose any value for the unused input and make
# a fresh proof, because that public signal has no relation-level restriction.
printf '{"bound":"1","unused":"123463"}\n' > "$BUILD/input_attacker.json"
run 60_attacker_witness 0 "$SNARKJS" wtns calculate \
  "$BUILD/public-input-unused_js/public-input-unused.wasm" \
  "$BUILD/input_attacker.json" "$BUILD/witness_attacker.wtns"
run 61_attacker_witness_check 0 "$SNARKJS" wtns check \
  "$BUILD/public-input-unused.r1cs" "$BUILD/witness_attacker.wtns"
run 62_attacker_prove 0 "$SNARKJS" groth16 prove \
  "$BUILD/circuit_final.zkey" "$BUILD/witness_attacker.wtns" \
  "$BUILD/proof_attacker.json" "$BUILD/public_attacker.json"
run 63_attacker_verify 0 "$SNARKJS" groth16 verify \
  "$BUILD/verification_key.json" "$BUILD/public_attacker.json" "$BUILD/proof_attacker.json"

(
  cd "$ROOT"
  shasum -a 256 \
    feasibility/v2/public-input-unused.circom \
    feasibility/v2/run_public_input_experiment.sh \
    "$BUILD/public-input-unused.r1cs" \
    "$BUILD/public-input-unused.sym" \
    "$BUILD/public-input-unused_js/public-input-unused.wasm" \
    "$BUILD/circuit_final.zkey" \
    "$BUILD/verification_key.json" \
    "$BUILD/proof.json" \
    "$BUILD/proof_attacker.json" \
    "$BUILD/public.json" \
    "$BUILD/public_attacker.json" \
    "$BUILD/public_unused_mutated.json" \
    "$BUILD/public_bound_mutated.json"
) > "$OUT/sha256.txt"

python3 - "$OUT" <<'PY'
import csv
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
steps = []
with (out / "steps.tsv").open(newline="") as handle:
    for name, expected, observed, status in csv.reader(handle, delimiter="\t"):
        steps.append({
            "name": name,
            "expected_exit": int(expected.split("=", 1)[1]),
            "observed_exit": int(observed.split("=", 1)[1]),
            "status": status,
        })
original = json.loads((out / "build/public.json").read_text())
unused_mutated = json.loads((out / "build/public_unused_mutated.json").read_text())
bound_mutated = json.loads((out / "build/public_bound_mutated.json").read_text())
result = {
    "experiment": "unused-declared-public-input-groth16-binding",
    "all_steps_pass": all(step["status"] == "PASS" for step in steps),
    "original_public": original,
    "unused_mutated_public": unused_mutated,
    "bound_mutated_public": bound_mutated,
    "unused_mutation_rejected": next(s for s in steps if s["name"] == "50_verify_unused_mutated")["observed_exit"] == 1,
    "bound_mutation_rejected": next(s for s in steps if s["name"] == "51_verify_bound_mutated")["observed_exit"] == 1,
    "attacker_chosen_unused_verified_with_fresh_proof": next(s for s in steps if s["name"] == "63_attacker_verify")["observed_exit"] == 0,
    "steps": steps,
}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
PY

echo "RESULT: both post-proof mutations rejected; a fresh proof for an arbitrary unused value verified"
echo "EVIDENCE: $OUT"
