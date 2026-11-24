#!/bin/sh
# Fetch pinned third-party dependencies for B2 into $DEPS (default results/raw/B2/deps, git-ignored).
# Nothing fetched here is committed. Re-run is idempotent. Network required.
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPS="${DEPS:-$ROOT/results/raw/B2/deps}"
mkdir -p "$DEPS"
clone() { # name url rev
  if [ ! -d "$DEPS/$1/.git" ]; then
    git init -q "$DEPS/$1"; git -C "$DEPS/$1" remote add origin "$2"
  fi
  git -C "$DEPS/$1" fetch -q --depth 1 origin "$3"
  git -C "$DEPS/$1" checkout -q FETCH_HEAD
  echo "$1 $(git -C "$DEPS/$1" rev-parse HEAD)"
}
# redpacket: OZ 4.8.1 (package-lock.json pin)
clone oz-4.8.1 https://github.com/OpenZeppelin/openzeppelin-contracts v4.8.1
# privacyvaults: contracts/foundry.lock pins
clone oz-5.5.0 https://github.com/OpenZeppelin/openzeppelin-contracts fcbae5394ae8ad52d8e580a3477db99814b9d565
clone poseidon2-evm https://github.com/zemse/poseidon2-evm 4c52b46d82659df6d11d67b251b6aea63c8b4203
clone forge-std-1.14.0 https://github.com/foundry-rs/forge-std 1801b0541f4fda118a10798fd3486bb7051c5dd6
# orc: submodule gitlinks at the pinned host commit
clone orc-forge-std https://github.com/foundry-rs/forge-std f3dae6e6ee381f25eb6a246f7da9b85c91a68219
clone sp1-contracts https://github.com/succinctlabs/sp1-contracts d3629729c3216eb51bd4859d027a8eb729399fa4
# Noir dependency (git dep resolved by nargo at compile time; recorded for provenance)
clone noir-poseidon-0.1.1 https://github.com/noir-lang/poseidon v0.1.1
