#!/usr/bin/env bash
# AZ1 synthetic extent-binding fixture: faulty/fixed pair with a real Groth16
# verifier on an owned local Anvil chain, then BindCheck freeze 2, Slither and
# the D1 R-EXTENT interface on both variants.
#
# Scope: owned local chain only, synthetic test token, no fork, no public RPC,
# no broadcast outside the local Anvil started here. Toy trusted setup with
# fixed entropy: reproducible, and insecure by design (fixture only).
#
# usage: bash prototypes/az1/run.sh
# env:   AZ1_PORT (default 18545+$$%1000)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIX="$ROOT/prototypes/az1"
RUN_ID="az1-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/AZ1/$RUN_ID"
WORK="$OUT/work"
STEPS="$OUT/steps.tsv"
PORT="${AZ1_PORT:-$((18545 + $$ % 1000))}"
RPC="http://127.0.0.1:$PORT"
ANVIL_PID=""
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/az1-slither.XXXXXX")"   # outside the worktree (foundry.toml)

# ---- pinned tools -----------------------------------------------------------
TOOLS="${BINDCHECK_TOOLS:-$ROOT/../bindcheck-zk/tools}"
CIRCOM="$TOOLS/circom-src/target/release/circom"
CIRCOM_SHA=599552d8027722ee9de3cf21a5a78f3f36bad07d0e0f40a627d6c3a35dff6cb7   # T0 pin, circom 2.2.3
SOLC_BIN="$HOME/.solc-select/artifacts/solc-0.8.11/solc-0.8.11"
SOLC_SHA=717c239f3a1dc3a4834c16046a0b4b9f46964665c8ffa82051a6d09fe741cd4f    # solc 0.8.11 linux-amd64
FREEZE2=92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a
SNARKJS="$ROOT/node_modules/.bin/snarkjs"
# Anvil's default local dev keys (accounts 0..3). Local chain only.
K_DEPLOYER=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
K_ALICE=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
K_BOB=0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
K_CAROL=0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6

mkdir -p "$WORK"/{circuit,setup,proofs,contracts,build} "$OUT/analysis"
: > "$STEPS"

cleanup() {
  if [[ -n "$ANVIL_PID" ]] && kill -0 "$ANVIL_PID" 2>/dev/null; then
    kill "$ANVIL_PID" 2>/dev/null || true
    wait "$ANVIL_PID" 2>/dev/null || true
  fi
  rm -rf "$SCRATCH"
}
trap cleanup EXIT

# run NAME EXPECTED_EXIT cmd... : log the command and its output, compare exit code.
run() {
  local name="$1" expected="$2"; shift 2
  local log="$OUT/$name.log" observed=0
  set +e
  { printf '$'; printf ' %q' "$@"; printf '\n'; "$@"; } >"$log" 2>&1
  observed=$?
  set -e
  local status=PASS
  [[ "$observed" -eq "$expected" ]] || status=FAIL
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == PASS ]]
}

# check NAME EXPECTED OBSERVED : record a state assertion.
check() {
  local name="$1" expected="$2" observed="$3" status=PASS
  [[ "$observed" == "$expected" ]] || status=FAIL
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == PASS ]]
}

sha() { sha256sum "$1" | awk '{print $1}'; }

# ---- 00 environment and pins ------------------------------------------------
[[ -x "$CIRCOM" && "$(sha "$CIRCOM")" == "$CIRCOM_SHA" ]] || { echo "circom pin mismatch: $CIRCOM" >&2; exit 2; }
[[ -x "$SOLC_BIN" && "$(sha "$SOLC_BIN")" == "$SOLC_SHA" ]] || { echo "solc 0.8.11 pin mismatch: $SOLC_BIN" >&2; exit 2; }
if [[ ! -x "$SNARKJS" ]]; then
  run 00_npm_ci 0 npm ci --no-audit --no-fund --prefix "$ROOT"
fi
[[ "$(node -p "require('$ROOT/node_modules/snarkjs/package.json').version")" == 0.7.6 ]] || { echo "snarkjs != 0.7.6" >&2; exit 2; }
FREEZE_OBS="$(python3 "$ROOT/bindcheck_zk/freeze.py" | tail -1 | cut -d= -f2)"
[[ "$FREEZE_OBS" == "$FREEZE2" ]] || { echo "bindcheck_zk is not freeze 2: $FREEZE_OBS" >&2; exit 2; }
ln -s "$SOLC_BIN" "$SCRATCH/solc"   # crytic-compile parses a versioned file name and tries to download

ALICE="$(cast wallet address --private-key $K_ALICE)"
BOB="$(cast wallet address --private-key $K_BOB)"
CAROL="$(cast wallet address --private-key $K_CAROL)"
{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "workspace_git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "workspace_dirty_files=$(git -C "$ROOT" status --porcelain | wc -l)"
  echo "host=$(uname -srm)"
  echo "circom=$("$CIRCOM" --version) sha256=$(sha "$CIRCOM")"
  echo "snarkjs=$(node -p "require('$ROOT/node_modules/snarkjs/package.json').version")"
  echo "circomlib=$(node -p "require('$ROOT/node_modules/circomlib/package.json').version")"
  echo "circomlibjs_lock=$(node -p "require('$ROOT/package-lock.json').packages['node_modules/circomlibjs'].version")"
  echo "package_lock_sha256=$(sha "$ROOT/package-lock.json")"
  echo "node=$(node --version)"
  echo "solc=$("$SOLC_BIN" --version | tail -1) sha256=$(sha "$SOLC_BIN")"
  echo "anvil=$(anvil --version | head -1)"
  echo "cast=$(cast --version | head -1)"
  echo "slither=$(slither --version)"
  echo "python=$(python3 --version)"
  echo "bindcheck_zk_content_sha256=$FREEZE_OBS"
  echo "anvil_port=$PORT"
  echo "alice=$ALICE bob=$BOB carol=$CAROL (anvil default dev accounts 1..3)"
} > "$OUT/environment.txt"

# ---- 10 circuit, toy setup, verifier ----------------------------------------
cp "$FIX/circuits/batch4.circom" "$WORK/circuit/"
run 10_circom_compile 0 "$CIRCOM" "$WORK/circuit/batch4.circom" --r1cs --wasm --sym \
  -l "$ROOT/node_modules" -o "$WORK/circuit"
run 11_r1cs_info 0 "$SNARKJS" r1cs info "$WORK/circuit/batch4.r1cs"
S="$WORK/setup"
run 12_ptau_new 0 "$SNARKJS" powersoftau new bn128 12 "$S/pot12_0.ptau"
run 13_ptau_contribute 0 "$SNARKJS" powersoftau contribute "$S/pot12_0.ptau" "$S/pot12_1.ptau" \
  --name=az1-toy -e=az1-fixed-toy-entropy-not-secure
run 14_ptau_prepare 0 "$SNARKJS" powersoftau prepare phase2 "$S/pot12_1.ptau" "$S/pot12_final.ptau"
run 15_groth16_setup 0 "$SNARKJS" groth16 setup "$WORK/circuit/batch4.r1cs" "$S/pot12_final.ptau" "$S/batch4_0.zkey"
run 16_zkey_contribute 0 "$SNARKJS" zkey contribute "$S/batch4_0.zkey" "$S/batch4.zkey" \
  --name=az1-toy -e=az1-fixed-toy-entropy-not-secure-2
run 17_zkey_verify 0 "$SNARKJS" zkey verify "$WORK/circuit/batch4.r1cs" "$S/pot12_final.ptau" "$S/batch4.zkey"
run 18_export_vkey 0 "$SNARKJS" zkey export verificationkey "$S/batch4.zkey" "$S/vkey.json"
run 19_export_verifier 0 "$SNARKJS" zkey export solidityverifier "$S/batch4.zkey" "$WORK/contracts/Groth16Verifier.sol"
# The fixture contracts pin pragma 0.8.11; the generated verifier's range pragma admits it.
grep -q 'pragma solidity >=0.7.0 <0.9.0;' "$WORK/contracts/Groth16Verifier.sol"

# ---- 20 inputs, witnesses, proofs --------------------------------------------
P="$WORK/proofs"
run 20_make_inputs 0 node "$FIX/scripts/fixture.js" inputs "$P" "$ALICE" "$BOB" "$CAROL"
WASM="$WORK/circuit/batch4_js/batch4.wasm"
for b in honest fault; do
  run "21_${b}_fullprove" 0 "$SNARKJS" groth16 fullprove "$P/$b-input.json" "$WASM" "$S/batch4.zkey" \
    "$P/$b-proof.json" "$P/$b-public.json"
  run "22_${b}_verify" 0 "$SNARKJS" groth16 verify "$S/vkey.json" "$P/$b-public.json" "$P/$b-proof.json"
done
python3 -I -c '
import json,sys
p,e=sys.argv[1],json.load(open(sys.argv[1]+"/expected.json"))
for b in ("honest","fault"):
    pub=json.load(open(f"{p}/{b}-public.json"))
    assert pub==[e[b]["commitment"],e[b]["creditTotal"]],(b,pub,e[b])
    t=list(pub); t[1]=str(int(t[1])+1); json.dump(t,open(f"{p}/{b}-public-tampered.json","w"))
print("public signals match off-circuit commitment and credit")' "$P" > "$OUT/23_public_matches_expected.log"
check 23_public_matches_expected 0 0
run 24_tampered_public_rejected 1 "$SNARKJS" groth16 verify "$S/vkey.json" "$P/honest-public-tampered.json" "$P/honest-proof.json"
# A witness with a non-no-op row cannot hide a deposit as kind 0 (control on circuit semantics).
python3 -I -c '
import json,sys
d=json.load(open(sys.argv[1])); d["kind"][1]="0"; json.dump(d,open(sys.argv[2],"w"))' \
  "$P/fault-input.json" "$P/fault-input-hidden-kind.json"
run 25_noop_with_amount_unsatisfiable 1 "$SNARKJS" wtns calculate "$WASM" "$P/fault-input-hidden-kind.json" "$P/hidden.wtns"

# ---- 30 compile contracts ---------------------------------------------------
cp "$FIX/contracts/"*.sol "$WORK/contracts/"
run 30_solc_compile 0 "$SOLC_BIN" --optimize --optimize-runs 200 --combined-json abi,bin \
  --base-path "$WORK/contracts" -o "$WORK/build" --overwrite \
  "$WORK/contracts/SettlementFaulty.sol" "$WORK/contracts/SettlementFixed.sol"
bin() { python3 -I -c '
import json,sys
d=json.load(open(sys.argv[1]))["contracts"]
k=[k for k in d if k.endswith(":"+sys.argv[2])]; assert len(k)==1,k
print("0x"+d[k[0]]["bin"])' "$WORK/build/combined.json" "$1"; }

# ---- 40 local chain and deployment ------------------------------------------
if cast chain-id --rpc-url "$RPC" >/dev/null 2>&1; then echo "port $PORT already in use" >&2; exit 2; fi
anvil --silent --port "$PORT" --chain-id 31337 >"$OUT/anvil.log" 2>&1 &
ANVIL_PID=$!
for _ in $(seq 1 100); do cast chain-id --rpc-url "$RPC" >/dev/null 2>&1 && break; sleep 0.1; done
kill -0 "$ANVIL_PID" 2>/dev/null || { echo "anvil failed to start" >&2; exit 1; }
check 40_local_chain_id 31337 "$(cast chain-id --rpc-url "$RPC")"

deploy() { # NAME CREATION_HEX -> prints address
  local receipt="$OUT/41_deploy_$1.json"
  cast send --rpc-url "$RPC" --private-key $K_DEPLOYER --json --create "$2" > "$receipt"
  python3 -I -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] in ("0x1",1), r; print(r["contractAddress"])' "$receipt"
}
TOKEN="$(deploy token "$(bin TestToken)")"
P3="$(deploy poseidon3 "$(tr -d '\n' < "$P/poseidon3.hex")")"
P4="$(deploy poseidon4 "$(tr -d '\n' < "$P/poseidon4.hex")")"
VERIFIER="$(deploy verifier "$(bin Groth16Verifier)")"
ARGS="$(cast abi-encode 'constructor(address,address,address,address)' "$VERIFIER" "$TOKEN" "$P3" "$P4")"
FAULTY="$(deploy faulty "$(bin SettlementFaulty)${ARGS#0x}")"
FIXED="$(deploy fixed "$(bin SettlementFixed)${ARGS#0x}")"
printf 'token=%s\nposeidon3=%s\nposeidon4=%s\nverifier=%s\nfaulty=%s\nfixed=%s\n' \
  "$TOKEN" "$P3" "$P4" "$VERIFIER" "$FAULTY" "$FIXED" > "$OUT/addresses-local.txt"
check 41_commitment_matches_contract_poseidon \
  "$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["honest"]["commitment"])' "$P/expected.json")" \
  "$(cast call --rpc-url "$RPC" "$P4" 'poseidon(uint256[4])(uint256)' \
      "[$(for i in 0 1 2 3; do python3 -I -c '
import json,sys; d=json.load(open(sys.argv[1])); i=int(sys.argv[2])
print(d["kind"][i],d["owner"][i],d["amount"][i])' "$P/honest-input.json" $i | \
      { read k o a; cast call --rpc-url "$RPC" "$P3" 'poseidon(uint256[3])(uint256)' "[$k,$o,$a]" | awk '{print $1}'; }; done | paste -sd,)]" | awk '{print $1}')"

send() { # NAME EXPECTED_STATUS(1|0) KEY TO SIG ARGS... : mined tx with fixed gas, check receipt status
  local name="$1" expected="$2" key="$3" to="$4"; shift 4
  local receipt="$OUT/$name.json" observed
  set +e
  cast send --rpc-url "$RPC" --private-key "$key" --gas-limit 3000000 --json "$to" "$@" > "$receipt" 2>"$OUT/$name.err"
  set -e
  observed="$(python3 -I -c '
import json,sys
try: r=json.load(open(sys.argv[1])); print(int(r["status"],16) if isinstance(r["status"],str) else int(r["status"]))
except Exception: print("no-receipt")' "$receipt")"
  check "$name" "$expected" "$observed"
}
why() { # NAME KEY TO SIG ARGS... : simulate to capture the revert reason (expected to fail)
  local name="$1" key="$2" to="$3"; shift 3
  run "$name" 1 cast call --rpc-url "$RPC" --from "$(cast wallet address --private-key "$key")" "$to" "$@"
}
SIG='processBatch(uint256[2],uint256[2][2],uint256[2],uint256,uint256[4],uint256[4],uint256[4],uint256)'
batch_args() { node "$FIX/scripts/fixture.js" castargs "$P/$1-proof.json" "$P/$1-public.json" "$P/$1-input.json" "$2" ${3:-}; }
readarray -t HONEST2 < <(batch_args honest 2)
readarray -t HONEST2_TAMPER < <(batch_args honest 2 tamper)
readarray -t FAULT1 < <(batch_args fault 1)
readarray -t FAULT2 < <(batch_args fault 2)
u() { cast call --rpc-url "$RPC" "$1" "$2" "${@:3}" | awk '{print $1}'; }
state() { # POOL PREFIX : record and print credit/backing/gap/token balance
  local pool="$1"
  echo "credit=$(u "$pool" 'totalL2Credit()(uint256)') backing=$(u "$pool" 'settledBacking()(uint256)') gap=$(u "$pool" 'unbackedCredit()(uint256)') tokens=$(u "$TOKEN" 'balanceOf(address)(uint256)' "$pool")"
}

send 42_mint_alice 1 $K_DEPLOYER "$TOKEN" 'mint(address,uint256)' "$ALICE" 1000
send 42_mint_bob 1 $K_DEPLOYER "$TOKEN" 'mint(address,uint256)' "$BOB" 1000
for pool in FAULTY FIXED; do
  addr="${!pool}"
  send "43_${pool}_approve_alice" 1 $K_ALICE "$TOKEN" 'approve(address,uint256)' "$addr" 1000
  send "43_${pool}_approve_bob" 1 $K_BOB "$TOKEN" 'approve(address,uint256)' "$addr" 1000
  send "44_${pool}_alice_pending_100" 1 $K_ALICE "$addr" 'depositPendingFunds(uint256)' 100
  send "44_${pool}_bob_pending_50" 1 $K_BOB "$addr" 'depositPendingFunds(uint256)' 50
done
check 45_carol_has_no_pending_deposit_faulty 0 "$(u "$FAULTY" 'userPendingDeposits(address)(uint256)' "$CAROL")"

# ---- 50 faulty consumer -----------------------------------------------------
why 50_faulty_tampered_reason $K_ALICE "$FAULTY" "$SIG" "${HONEST2_TAMPER[@]}"
send 50_faulty_tampered_public_input 0 $K_ALICE "$FAULTY" "$SIG" "${HONEST2_TAMPER[@]}"
send 51_faulty_honest_k2 1 $K_ALICE "$FAULTY" "$SIG" "${HONEST2[@]}"
check 52_faulty_after_honest "credit=150 backing=150 gap=0 tokens=150" "$(state "$FAULTY")"
# any caller: carol submits; carol never deposited
send 53_faulty_fault_k1 1 $K_CAROL "$FAULTY" "$SIG" "${FAULT1[@]}"
check 54_faulty_after_fault "credit=1150 backing=150 gap=1000 tokens=150" "$(state "$FAULTY")"
check 55_faulty_carol_pending_after 0 "$(u "$FAULTY" 'userPendingDeposits(address)(uint256)' "$CAROL")"

# ---- 60 fixed consumer (same verifier, same proofs) --------------------------
why 60_fixed_fault_k1_reason $K_CAROL "$FIXED" "$SIG" "${FAULT1[@]}"
send 60_fixed_fault_k1 0 $K_CAROL "$FIXED" "$SIG" "${FAULT1[@]}"
check 61_fixed_after_fault_k1 "credit=0 backing=0 gap=0 tokens=150" "$(state "$FIXED")"
why 62_fixed_fault_k2_reason $K_CAROL "$FIXED" "$SIG" "${FAULT2[@]}"
send 62_fixed_fault_k2 0 $K_CAROL "$FIXED" "$SIG" "${FAULT2[@]}"
send 63_fixed_honest_k2 1 $K_ALICE "$FIXED" "$SIG" "${HONEST2[@]}"
check 64_fixed_after_honest "credit=150 backing=150 gap=0 tokens=150" "$(state "$FIXED")"
kill "$ANVIL_PID"; wait "$ANVIL_PID" 2>/dev/null || true; ANVIL_PID=""

# ---- 70 detectors on both variants ------------------------------------------
for v in Faulty Fixed; do
  d="$OUT/analysis/$v"
  mkdir -p "$d/circuits" "$d/contracts"
  cp "$FIX/circuits/batch4.circom" "$d/circuits/"
  cp "$WORK/contracts/Groth16Verifier.sol" "$FIX/contracts/TestToken.sol" "$FIX/contracts/Settlement$v.sol" "$d/contracts/"
  run "70_bindcheck_unhinted_$v" 0 env BINDCHECK_CIRCOM="$CIRCOM" \
    sh -c 'cd "$1" && python3 -m bindcheck_zk.cli analyze "$2" > "$3"' _ "$ROOT" "$d" "$OUT/70_bindcheck_unhinted_$v.json"
  run "71_bindcheck_explicit_$v" 0 env BINDCHECK_CIRCOM="$CIRCOM" \
    sh -c 'cd "$1" && python3 -m bindcheck_zk.cli analyze "$2" --circuit circuits/batch4.circom --consumer "contracts/Settlement$4.sol" > "$3"' \
    _ "$ROOT" "$d" "$OUT/71_bindcheck_explicit_$v.json" "$v"
  rm -rf "$SCRATCH/$v"; cp -r "$d" "$SCRATCH/$v"
  # slither exits non-zero when it reports results; record the exit, judge from JSON
  set +e
  (cd "$SCRATCH/$v/contracts" && slither "Settlement$v.sol" --solc "$SCRATCH/solc" \
     --json "$OUT/72_slither_$v.json" > "$OUT/72_slither_$v.log" 2>&1)
  echo "72_slither_$v	exit=$?	(json: success field decides)" | tee -a "$STEPS"
  set -e
done
python3 -I - "$OUT" > "$OUT/73_detector_summary.txt" <<'EOF'
import json,sys,collections,pathlib
out=pathlib.Path(sys.argv[1])
for v in ("Faulty","Fixed"):
    for kind in ("unhinted","explicit"):
        d=json.load(open(out/f"70_bindcheck_unhinted_{v}.json" if kind=="unhinted" else out/f"71_bindcheck_explicit_{v}.json"))
        print(f"bindcheck {kind} {v}: discovery={json.dumps(d['discovery'])}")
        for p in ("P1","P2","P3","P4","P5"):
            r=d["patterns"][p]; print(f"  {p} {r['verdict']} {r.get('reasons')} grade={r.get('evidence_grade')}")
    s=json.load(open(out/f"72_slither_{v}.json"))
    det=s["results"].get("detectors",[]) if s.get("success") else []
    c=collections.Counter((x["check"],x["impact"]) for x in det)
    print(f"slither {v}: success={s.get('success')} results={len(det)} {dict(c)}")
    for x in det:
        if "processBatch" in x["description"]:
            print("   processBatch:",x["check"],"|",x["description"].strip().splitlines()[0][:200])
EOF
cat "$OUT/73_detector_summary.txt"

# D1 R-EXTENT comparator on ASSUMED facts for this shape (no extraction is claimed):
# producer binds every row word on every path; consumer relies on rows only below numRealRows.
run 74_r_extent_interface 0 python3 -c '
import sys, json; sys.path.insert(0, sys.argv[1] + "/src")
from bindcheck_d1.static_analyzer_v1 import _extent_coverage
prod = {"status": "EXACT", "condition": {"kind": "always"}}
cons = {"status": "EXACT", "condition": {"kind": "prefix", "extent": "num_real_rows"}}
print(json.dumps({"provenance": "ASSUMED", "producer": prod, "consumer": cons,
                  "coverage": _extent_coverage(prod, cons)}, indent=1, sort_keys=True))' "$ROOT"

# ---- 80 checksums -------------------------------------------------------------
{
  cd "$ROOT"
  sha256sum prototypes/az1/run.sh prototypes/az1/expected-outcomes.md prototypes/az1/circuits/batch4.circom \
    prototypes/az1/contracts/*.sol prototypes/az1/scripts/fixture.js package-lock.json
  cd "$WORK"
  sha256sum circuit/batch4.r1cs circuit/batch4_js/batch4.wasm setup/pot12_final.ptau setup/batch4.zkey \
    setup/vkey.json contracts/Groth16Verifier.sol build/combined.json proofs/*.json proofs/*.hex
} > "$OUT/checksums.sha256"

fails="$(awk -F'\t' '$NF=="FAIL"' "$STEPS" | wc -l)"
echo "steps=$(wc -l < "$STEPS") fail=$fails out=$OUT"
[[ "$fails" -eq 0 ]]
