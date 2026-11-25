#!/bin/sh
# Honest-path evidence per B3 host: an honest proof is accepted (real proofs; mock verifier for the zkVM host).
# Runs the hosts' OWN tests on clean copies of the pinned clones (git archive of the pinned commit + pinned deps).
# Usage: CAND=results/raw/B3/candidates OUT=results/raw/B3/honest-N sh run_honest.sh   (OUT must not exist)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
CAND="${CAND:-$ROOT/results/raw/B3/candidates}"; DEPS="${DEPS:-$ROOT/results/raw/B3/deps}"
OUT="${OUT:?}"; case "$OUT" in /*) ;; *) OUT="$PWD/$OUT";; esac; [ -e "$OUT" ] && { echo "OUT exists" >&2; exit 2; }
NODE_BIN="${NODE_BIN:-$HOME/.nvm/versions/node/v22.20.0/bin}"; export PATH="$NODE_BIN:$PATH"
MEM="systemd-run --user --scope -q -p MemoryMax=8G env PATH=$PATH"
mkdir -p "$OUT/src" "$OUT/logs"; printf 'host\tcheck\texit\n' > "$OUT/honest-summary.tsv"
x() { # host clone sha
  mkdir -p "$OUT/src/$1"; git -C "$CAND/$2" archive --format=tar "$3" | tar -x -C "$OUT/src/$1"; }
run() { h=$1; n=$2; shift 2; ( "$@" ) >"$OUT/logs/$h-$n.log" 2>&1; ec=$?; printf '%s\t%s\t%s\n' "$h" "$n" "$ec" >> "$OUT/honest-summary.tsv"; echo "$h $n exit=$ec"; }

# zkerc20: real Groth16 proofs; verifier/zkey/wasm from the documented local setup (HOSTS.md)
x zkerc20 Zellic_zkerc20 ff7b1016390074d428c8d469df7f5d47f99a6628; Z="$OUT/src/zkerc20"
ln -s "$DEPS/zkerc20-node/node_modules" "$Z/node_modules"
cp "$HERE/baselines/zkerc20/circuits/verifier.sol" "$Z/circuits/"; cp "$ROOT/results/raw/B3/hostbuild/zkerc20/circuit_final.zkey" "$Z/circuits/"
cp -r "$ROOT/results/raw/B3/hostbuild/zkerc20/circuit_js" "$Z/circuits/"
run zkerc20 hardhat-integration sh -c "cd '$Z/circuits' && $MEM npx hardhat test"

# dark: committed fixture proofs on committed verifiers + consumer tests (verifier mock pins the PI vector)
x dark DarkWalletRH_dark-contracts 053ab0f7524658c74200d54bd26ad6cfc13469d4; D="$OUT/src/dark"
ln -s "$DEPS/dark-node/node_modules" "$D/contracts/node_modules"
run dark real-verifiers sh -c "cd '$D/circuits' && $MEM forge test"
run dark consumer-tests sh -c "cd '$D/contracts' && $MEM forge test"

# davinci: real fixture proofs through CouncilManager
x davinci vocdoni_davinci-dkg-council cf539b008a0e5b7a6e2cbb22ec82a851398b2f65; V="$OUT/src/davinci"
run davinci real-verifiers sh -c "cd '$V/solidity' && $MEM forge test --match-contract CouncilRealVerifiers"

# xchain: mock RISC Zero verifier (zkVM host)
x xchain fiit-ba_A-Resumable-Zero-Knowledge-Cross 643cee89594a85e83e1956cf0571fd0fadbe36ea; C="$OUT/src/xchain/smart-contracts"
mkdir -p "$C/lib"; ln -s "$DEPS/forge-std-v1.15.0" "$C/lib/forge-std"; ln -s "$DEPS/risc0-ethereum-v3.0.1" "$C/lib/risc0-ethereum"
run xchain mock-verifier-tests sh -c "cd '$C' && $MEM forge test --offline --no-match-path 'test/fuzzing/*'"

# kakushi: real UltraHonk proofs via the pinned @aztec/bb.js (ffi), verified by the committed verifier
x kakushi krishnacodes9_kakushi-monad da0684b9275eaaf147f2189f49cbeb65cc1fc22f; K="$OUT/src/kakushi"
FS="$(git -C "$CAND/krishnacodes9_kakushi-monad" ls-tree HEAD packages/contracts/lib/forge-std | awk '{print $3}')"
[ "$FS" = 0258fe875e1d8e207c1eb7175e542ea32356773c ] || { echo "kakushi forge-std gitlink changed" >&2; exit 3; }
[ -d "$DEPS/forge-std-0258fe8" ] || { git init -q "$DEPS/forge-std-0258fe8"; git -C "$DEPS/forge-std-0258fe8" remote add origin https://github.com/foundry-rs/forge-std; git -C "$DEPS/forge-std-0258fe8" fetch -q --depth 1 origin "$FS"; git -C "$DEPS/forge-std-0258fe8" checkout -q FETCH_HEAD; }
rmdir "$K/packages/contracts/lib/forge-std" 2>/dev/null; ln -s "$DEPS/forge-std-0258fe8" "$K/packages/contracts/lib/forge-std"
ln -s "$DEPS/kakushi-prover/node_modules" "$K/packages/attest-core/node_modules"
run kakushi real-proof-pool sh -c "cd '$K/packages/contracts' && $MEM forge test --match-path 'test/privacy/*'"
echo "summary: $OUT/honest-summary.tsv"
