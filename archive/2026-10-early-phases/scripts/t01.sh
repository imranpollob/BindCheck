#!/usr/bin/env bash
# BindCheck T01: build, set up (toy, local), prove and verify one honest batch.
# usage: bash scripts/t01.sh        (from anywhere; repo root is derived)
# Pinned: circom v2.2.3 (built from source, --locked), snarkjs 0.7.6, circomlib 2.0.5,
# circomlibjs 0.1.7 (see package.json / package-lock.json).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
B=build/T01
L=results/raw/T01
CIRCOM="$ROOT/tools/circom-src/target/release/circom"
SNARKJS="$ROOT/node_modules/.bin/snarkjs"
CIRCOM_TAG=v2.2.3
CIRCOM_COMMIT=ad44e915a12bb047b05745c2884aad9cc8326bc6
PTAU_POWER=12

mkdir -p "$B" "$L" tools
rm -rf "${B:?}"/* ; rm -f "$L"/[1-9]*.log "$L"/steps.tsv "$L"/result.json
STEPS="$L/steps.tsv"; : > "$STEPS"
T0=$(date +%s)
OVERALL=0

# run NAME EXPECT_EXIT CMD...   -> logs to $L/NAME.log, records exit status, flags unexpected status
run() {
  local name="$1" expect="$2"; shift 2
  local log="$L/$name.log"
  { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$log" 2>&1
  local code; code=$(tail -n1 "$log" | sed 's/exit=//')
  local verdict=ok
  if [ "$code" != "$expect" ]; then verdict=UNEXPECTED; OVERALL=1; fi
  printf '%s\t%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$*" "$expect" "$code" "$verdict" >> "$STEPS"
  echo "[$verdict] $name (exit $code, expected $expect)"
  [ "$verdict" = ok ] || { echo "see $log"; return 1; }
}
fatal() { echo "STOPPING: $1"; echo "T01 FAILED at $1" ; exit 1; }

# --- 10: environment -------------------------------------------------------
{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "uname=$(uname -a)"
  echo "hw=$(sysctl -n hw.model 2>/dev/null) cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null) cores=$(sysctl -n hw.ncpu 2>/dev/null)"
  echo "node=$(node -v) npm=$(npm -v) rustc=$(rustc --version 2>&1) cargo=$(cargo --version 2>&1)"
} > "$L/10_env.log"

# --- 11: pinned circom compiler (source build; no prebuilt macOS arm64 release) ----
if [ ! -x "$CIRCOM" ]; then
  [ -d tools/circom-src ] || git clone --quiet --depth 1 --branch "$CIRCOM_TAG" https://github.com/iden3/circom tools/circom-src
  run 11_circom_build 0 cargo build --release --locked --manifest-path tools/circom-src/Cargo.toml || fatal 11_circom_build
fi
HEAD_REV=$(git -C tools/circom-src rev-parse HEAD 2>/dev/null)
[ "$HEAD_REV" = "$CIRCOM_COMMIT" ] || fatal "circom source is $HEAD_REV, expected $CIRCOM_COMMIT"
run 12_versions 0 bash -c "'$CIRCOM' --version; '$SNARKJS' --help 2>&1 | head -1; node -p \"const l=require('./package-lock.json').packages; ['snarkjs','circomlib','circomlibjs'].map(n=>n+'@'+l['node_modules/'+n].version).join(' ')\"" || fatal 12_versions

# --- 20: dependencies from lockfile ---------------------------------------------
run 20_npm_ci 0 npm ci --no-audit --no-fund || fatal 20_npm_ci

# --- 30: honest input (independent Poseidon via circomlibjs) -----------------
run 30_make_input 0 node scripts/make_input.js "$B/input.json" || fatal 30_make_input

# --- 40: compile -----------------------------------------------------------------
run 40_compile 0 "$CIRCOM" circuits/batch_deposit.circom --r1cs --wasm --sym -l node_modules -o "$B" || fatal 40_compile
run 41_r1cs_info 0 "$SNARKJS" r1cs info "$B/batch_deposit.r1cs" || fatal 41_r1cs_info

# --- 50: TOY local setup (deterministic, publicly recomputable entropy) ---------
run 50_ptau_new 0 "$SNARKJS" powersoftau new bn128 $PTAU_POWER "$B/pot_0000.ptau" || fatal 50_ptau_new
run 51_ptau_contribute 0 "$SNARKJS" powersoftau contribute "$B/pot_0000.ptau" "$B/pot_0001.ptau" --name="bindcheck-T01-toy" -e="bindcheck T01 public toy entropy - not secret" || fatal 51_ptau_contribute
run 52_ptau_prepare 0 "$SNARKJS" powersoftau prepare phase2 "$B/pot_0001.ptau" "$B/pot_final.ptau" || fatal 52_ptau_prepare
run 53_ptau_verify 0 "$SNARKJS" powersoftau verify "$B/pot_final.ptau" || fatal 53_ptau_verify
run 54_zkey_new 0 "$SNARKJS" groth16 setup "$B/batch_deposit.r1cs" "$B/pot_final.ptau" "$B/circuit_0000.zkey" || fatal 54_zkey_new
run 55_zkey_contribute 0 "$SNARKJS" zkey contribute "$B/circuit_0000.zkey" "$B/circuit_final.zkey" --name="bindcheck-T01-toy" -e="bindcheck T01 public toy phase2 entropy - not secret" || fatal 55_zkey_contribute
run 56_zkey_verify 0 "$SNARKJS" zkey verify "$B/batch_deposit.r1cs" "$B/pot_final.ptau" "$B/circuit_final.zkey" || fatal 56_zkey_verify
run 57_vkey_export 0 "$SNARKJS" zkey export verificationkey "$B/circuit_final.zkey" "$B/verification_key.json" || fatal 57_vkey_export

# --- 60: witness and satisfaction check --------------------------------------------
run 60_witness 0 "$SNARKJS" wtns calculate "$B/batch_deposit_js/batch_deposit.wasm" "$B/input.json" "$B/witness.wtns" || fatal 60_witness
run 61_wtns_check 0 "$SNARKJS" wtns check "$B/batch_deposit.r1cs" "$B/witness.wtns" || fatal 61_wtns_check

# --- 70: proof and off-chain verification --------------------------------------------
run 70_prove 0 "$SNARKJS" groth16 prove "$B/circuit_final.zkey" "$B/witness.wtns" "$B/proof.json" "$B/public.json" || fatal 70_prove
run 71_verify 0 "$SNARKJS" groth16 verify "$B/verification_key.json" "$B/public.json" "$B/proof.json" || fatal 71_verify
run 72_public_order 0 node scripts/check_public_order.js "$B/input.json" "$B/public.json" "$B/batch_deposit.sym" "$B/verification_key.json" || fatal 72_public_order

# --- 80: sanity controls (NOT the vulnerability experiments; they only show the checks are live) ---
# 80: relation violated (newBalance off by one, commitment recomputed) -> witness generation must fail
node scripts/make_input.js "$B/input_wrong_sum.json" wrong-sum > "$L/80_make_wrong_sum_input.log" 2>&1
run 81_wrong_sum_witness 1 "$SNARKJS" wtns calculate "$B/batch_deposit_js/batch_deposit.wasm" "$B/input_wrong_sum.json" "$B/witness_wrong_sum.wtns"
# 82: valid proof, one public signal altered (amount[0]+1) -> verification must reject
node -e '
const fs=require("fs");const p=JSON.parse(fs.readFileSync(process.argv[1]));
p[0]=(BigInt(p[0])+1n).toString();fs.writeFileSync(process.argv[2],JSON.stringify(p));' "$B/public.json" "$B/public_tampered.json"
run 82_tampered_public_verify 1 "$SNARKJS" groth16 verify "$B/verification_key.json" "$B/public_tampered.json" "$B/proof.json"

# --- 90: digests and result file -------------------------------------------------------
( cd "$ROOT" && shasum -a 256 circuits/batch_deposit.circom scripts/make_input.js scripts/check_public_order.js scripts/t01.sh package.json package-lock.json \
    "$B/batch_deposit.r1cs" "$B/batch_deposit.sym" "$B/batch_deposit_js/batch_deposit.wasm" "$B/input.json" "$B/witness.wtns" \
    "$B/pot_final.ptau" "$B/circuit_final.zkey" "$B/verification_key.json" "$B/proof.json" "$B/public.json" ) > "$L/90_sha256.txt"
T1=$(date +%s)
node -e '
const fs=require("fs");
const steps=fs.readFileSync(process.argv[1],"utf8").trim().split("\n").map(l=>{const [name,cmd,e,o,v]=l.split("\t");return {name,expected:e.split("=")[1],observed:o.split("=")[1],verdict:v};});
fs.writeFileSync(process.argv[2],JSON.stringify({task:"T01",elapsed_seconds:Number(process.argv[3]),all_steps_as_expected:steps.every(s=>s.verdict==="ok"),steps},null,2)+"\n");
' "$STEPS" "$L/result.json" "$((T1-T0))"

echo
if [ "$OVERALL" = 0 ]; then echo "T01 OK: witness satisfied, proof verified (elapsed $((T1-T0))s). Logs: $L  Artifacts: $B"; else echo "T01: some steps differed from expectation; see $STEPS"; exit 1; fi
