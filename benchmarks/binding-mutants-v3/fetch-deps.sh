#!/bin/sh
# Fetch pinned third-party dependencies for B3 into $DEPS (default results/raw/B3/deps, git-ignored).
# Nothing fetched here is committed. Re-run is idempotent. Network required.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
DEPS="${DEPS:-$ROOT/results/raw/B3/deps}"; mkdir -p "$DEPS"
NODE_BIN="${NODE_BIN:-$HOME/.nvm/versions/node/v22.20.0/bin}"; PATH="$NODE_BIN:$PATH"
clone() { # name url rev
  if [ ! -d "$DEPS/$1/.git" ]; then git init -q "$DEPS/$1"; git -C "$DEPS/$1" remote add origin "$2"; fi
  git -C "$DEPS/$1" fetch -q --depth 1 origin "$3"; git -C "$DEPS/$1" checkout -q FETCH_HEAD
  echo "$1 $(git -C "$DEPS/$1" rev-parse HEAD)"
}
# xchain: smart-contracts/foundry.lock pins
clone forge-std-v1.15.0 https://github.com/foundry-rs/forge-std 0844d7e1fc5e60d77b68e469bff60265f236c398
clone risc0-ethereum-v3.0.1 https://github.com/risc0/risc0-ethereum 365e7b2db4f620fa256580c27558d2623362b9ae
git -C "$DEPS/risc0-ethereum-v3.0.1" submodule update -q --init --depth 1 lib/openzeppelin-contracts lib/forge-std
# zkerc20: package.json ranges resolved 2026-11-25 (lock committed in deps/zkerc20-package-lock.json)
mkdir -p "$DEPS/zkerc20-node"
cp "$ROOT/benchmarks/binding-mutants-v3/baselines/zkerc20/package.json" "$DEPS/zkerc20-node/package.json"
cp "$HERE/deps/zkerc20-package-lock.json" "$DEPS/zkerc20-node/package-lock.json"
(cd "$DEPS/zkerc20-node" && npm ci --ignore-scripts --no-audit --no-fund >/dev/null && echo "zkerc20-node ok")
# dark: contracts/package-lock.json (in the baseline)
mkdir -p "$DEPS/dark-node"
cp "$HERE/baselines/dark/contracts/package.json" "$HERE/baselines/dark/contracts/package-lock.json" "$DEPS/dark-node/"
(cd "$DEPS/dark-node" && npm ci --ignore-scripts --no-audit --no-fund >/dev/null && echo "dark-node ok")
# davinci: circuits/package.json pins circomlib 2.0.5 (only circomlib is needed to compile the circuits)
mkdir -p "$DEPS/davinci-node"
(cd "$DEPS/davinci-node" && [ -f package.json ] || echo '{"name":"b3-davinci-circomlib","private":true}' > package.json; npm install --no-audit --no-fund circomlib@2.0.5 >/dev/null && echo "davinci-node ok")
# kakushi honest path only: bb.js / noir_js at the host-declared pins (packages/zk/TOOLCHAIN)
mkdir -p "$DEPS/kakushi-prover"
cp "$HERE/deps/kakushi-prover-package.json" "$DEPS/kakushi-prover/package.json"
cp "$HERE/deps/kakushi-prover-package-lock.json" "$DEPS/kakushi-prover/package-lock.json"
(cd "$DEPS/kakushi-prover" && npm ci --no-audit --no-fund >/dev/null && echo "kakushi-prover ok")
# ptau for zkerc20 (Groth16 setup, 2^19); blake2b recorded in HOSTS.md
mkdir -p "$DEPS/ptau"
[ -f "$DEPS/ptau/powersOfTau28_hez_final_19.ptau" ] || curl -fsSL -o "$DEPS/ptau/powersOfTau28_hez_final_19.ptau" https://circom.info/powersOfTau28_hez_final_19.ptau
echo "bca9d8b04242f175189872c42ceaa21e2951e0f0f272a0cc54fc37193ff6648600eaf1c555c70cdedfaf9fb74927de7aa1d33dc1e2a7f1a50619484989da0887  $DEPS/ptau/powersOfTau28_hez_final_19.ptau" | b2sum -c -
