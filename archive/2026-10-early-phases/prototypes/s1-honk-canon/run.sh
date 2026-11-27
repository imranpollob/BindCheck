#!/usr/bin/env bash
# S1: do generated verifiers accept non-canonical public inputs (x, x+r, x+k*r)?
# Owned synthetic circuits, local Anvil only (chain id 31337), no network RPC.
# Each run writes a fresh ignored directory results/raw/S1/run-<UTC stamp>/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK="$ROOT/prototypes/s1-honk-canon"
BC_ROOT="${BC_ROOT:-$HOME/Coding/bc/BindCheck}"
TOOLS="${BC_TOOLS:-$BC_ROOT/tools}"
SNARKJS="${SNARKJS:-$BC_ROOT/node_modules/snarkjs/build/cli.cjs}"
CIRCOM="${CIRCOM:-$TOOLS/circom-src/target/release/circom}"
PORT="${S1_ANVIL_PORT:-8547}"
RPC="http://127.0.0.1:$PORT"
RUN="$ROOT/results/raw/S1/run-$(date -u +%Y%m%dT%H%M%SZ)"
[[ -e "$RUN" ]] && { echo "refusing to overwrite $RUN" >&2; exit 2; }
mkdir -p "$RUN"/{honk,snarkjs,native}
exec > >(tee "$RUN/run.log") 2>&1

echo "base=$(git -C "$ROOT" rev-parse HEAD) dirty=$(git -C "$ROOT" status --porcelain | wc -l)"
echo "date=$(date -u +%FT%TZ) host=$(uname -srm)"
echo "== tool versions"
for t in anvil forge cast; do printf '%s: ' "$t"; "$t" --version | head -1; done
node --version
"$CIRCOM" --version
node -e "console.log('snarkjs', require('$BC_ROOT/node_modules/snarkjs/package.json').version)"
echo "== input checksums"
sha256sum "$TASK"/circuit/{Nargo.toml,Prover.toml,src/main.nr} "$TASK"/circom/{s1.circom,input.json} \
  "$TASK"/{run.sh,bbjs_probe.mjs,alias_inputs.py,anvil_replay.py}
sha256sum "$TOOLS"/noir-1.0.0-beta.14/nargo "$TOOLS"/noir-1.0.0-beta.22/nargo "$TOOLS"/bb-5.0.0/bb "$TOOLS"/bb-6.0.0/bb \
  "$TOOLS"/bbjs-3.0.0-manual.20251030/package-lock.json "$TOOLS"/bbjs-5.0.0/package-lock.json \
  "$CIRCOM" "$BC_ROOT/package-lock.json"

compile_noir() { # <noir version> <dest>
  mkdir -p "$2"; cp -R "$TASK/circuit/." "$2/"
  "$TOOLS/noir-$1/nargo" --version | head -1
  "$TOOLS/noir-$1/nargo" execute --program-dir "$2"
}

echo "== native bb CLI (5.0.0, 6.0.0)"
compile_noir 1.0.0-beta.22 "$RUN/circuit-beta22"
ART="$RUN/circuit-beta22/target/s1_canonicality"
for v in 5.0.0 6.0.0; do
  bb="$TOOLS/bb-$v/bb"; echo "bb $($bb --version)"
  for t in evm evm-no-zk noir-recursive; do
    d="$RUN/native/bb-$v/$t"; mkdir -p "$d"
    "$bb" prove -b "$ART.json" -w "$ART.gz" -o "$d" -t "$t" --write_vk > "$d/prove.log" 2>&1
    python3 -I "$TASK/alias_inputs.py" "$d/public_inputs" > "$d/aliases.json"
    for c in honest plus_r max_k; do
      set +e; "$bb" verify -p "$d/proof" -k "$d/vk" -i "$d/public_inputs_$c" -t "$t" > "$d/verify_$c.log" 2>&1; rc=$?; set -e
      printf 'native\tbb-%s\t%s\t%s\texit=%s\t%s\n' "$v" "$t" "$c" "$rc" "$(tail -1 "$d/verify_$c.log")"
    done
    if [[ "$t" == evm* ]]; then
      for opt in plain optimized; do
        h="$RUN/honk/bb-${v}_${t}_${opt}"; mkdir -p "$h"
        flag=(); [[ $opt == optimized ]] && flag=(--optimized)
        "$bb" write_solidity_verifier -k "$d/vk" -o "$h/HonkVerifier.sol" -t "$t" "${flag[@]}" > "$h/write.log" 2>&1
        cp "$d/proof" "$d/public_inputs" "$d/vk" "$h/"
      done
    fi
  done
done

echo "== bb.js (WASM) 3.0.0-manual.20251030 (nargo beta.14) and 5.0.0 (nargo beta.22)"
compile_noir 1.0.0-beta.14 "$RUN/circuit-beta14"
for pair in "3.0.0-manual.20251030 circuit-beta14" "5.0.0 circuit-beta22"; do
  read -r v c <<< "$pair"
  out="$RUN/bbjs-$v"
  node "$TASK/bbjs_probe.mjs" "$TOOLS/bbjs-$v/node_modules/@aztec/bb.js" \
    "$RUN/$c/target/s1_canonicality.json" "$RUN/$c/target/s1_canonicality.gz" "$out" > "$RUN/bbjs-$v.stdout"
  sed -n '/^{/,$p' "$RUN/bbjs-$v.stdout" > "$RUN/bbjs-$v.json"
  python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); [print("bbjs-native", d["version"], m, r.get("error") or {k: x["accepted"] for k, x in r["results"].items()}, sep="\t") for m, r in d["modes"].items()]' "$RUN/bbjs-$v.json"
  for m in "$out"/*/; do
    [[ -f "$m/HonkVerifier.sol" ]] || continue
    h="$RUN/honk/bbjs-${v}_$(basename "$m")"; mkdir -p "$h"; cp "$m"/{HonkVerifier.sol,proof,public_inputs,vk} "$h/"
  done
done

echo "== snarkjs Groth16 / PLONK / fflonk (circom)"
S="$RUN/snarkjs"; cd "$S"
"$CIRCOM" "$TASK/circom/s1.circom" --r1cs --wasm -o "$S" > circom.log
node "$S/s1_js/generate_witness.js" "$S/s1_js/s1.wasm" "$TASK/circom/input.json" "$S/w.wtns"
sj() { node "$SNARKJS" "$@"; }
# Local throwaway ceremony with fixed entropy: synthetic, not a trusted setup.
sj powersoftau new bn128 10 p0.ptau > /dev/null
sj powersoftau contribute p0.ptau p1.ptau --name=s1 -e="s1 synthetic entropy" > /dev/null
sj powersoftau prepare phase2 p1.ptau final.ptau > /dev/null
for s in groth16 plonk fflonk; do
  mkdir -p "$s"
  if [[ $s == groth16 ]]; then
    sj groth16 setup s1.r1cs final.ptau "$s/0.zkey" > /dev/null
    sj zkey contribute "$s/0.zkey" "$s/key.zkey" --name=s1 -e="s1 entropy" > /dev/null
  else
    sj "$s" setup s1.r1cs final.ptau "$s/key.zkey" > "$s/setup.log" 2>&1
  fi
  sj "$s" prove "$s/key.zkey" w.wtns "$s/proof.json" "$s/public.json" > /dev/null
  sj zkey export solidityverifier "$s/key.zkey" "$s/Verifier.sol" > /dev/null
  sj zkey export soliditycalldata "$s/public.json" "$s/proof.json" > "$s/calldata.txt"
done
cd "$ROOT"

echo "== Anvil replay (local chain 31337, port $PORT)"
anvil --port "$PORT" --chain-id 31337 --disable-code-size-limit --silent > "$RUN/anvil.log" 2>&1 &
APID=$!; trap 'kill $APID 2>/dev/null || true' EXIT
for _ in $(seq 50); do cast chain-id --rpc-url "$RPC" > /dev/null 2>&1 && break; sleep 0.2; done
python3 -I "$TASK/anvil_replay.py" "$RUN" "$RPC"
column -t -s $'\t' "$RUN/anvil/results.tsv"

echo "== output checksums"
find "$RUN/honk" "$RUN/snarkjs" -maxdepth 2 \( -name '*.sol' -o -name proof -o -name public_inputs -o -name vk -o -name calldata.txt \) -print0 \
  | sort -z | xargs -0 sha256sum > "$RUN/output-sha256.txt"
wc -l < "$RUN/output-sha256.txt"
touch "$RUN/complete"
echo "run_dir=$RUN"
