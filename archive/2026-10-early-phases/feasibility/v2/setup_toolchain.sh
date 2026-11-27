#!/usr/bin/env bash
# Fetch and build the pinned feasibility-v2 toolchain. Generated dependencies
# and tool sources remain ignored; exact revisions are checked before use.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CIRCOM_DIR="$ROOT/tools/circom-src"
CIRCOM_COMMIT="ad44e915a12bb047b05745c2884aad9cc8326bc6"
RACE_CIRCOM_DIR="$ROOT/tools/circom-2.1.9"
RACE_CIRCOM_COMMIT="2eaaa6dface934356972b34cab64b25d382e59de"
CIRCOMSPECT_DIR="$ROOT/tools/circomspect-src"
CIRCOMSPECT_COMMIT="50010b623ed4f3bff9d1b0363cfe952385b47af3"

if [[ ! -d "$CIRCOM_DIR/.git" ]]; then
  git clone --filter=blob:none --branch v2.2.3 https://github.com/iden3/circom.git "$CIRCOM_DIR"
fi
git -C "$CIRCOM_DIR" checkout --detach "$CIRCOM_COMMIT"
[[ "$(git -C "$CIRCOM_DIR" rev-parse HEAD)" == "$CIRCOM_COMMIT" ]]
cargo build --release --locked --manifest-path "$CIRCOM_DIR/Cargo.toml"

if [[ ! -d "$RACE_CIRCOM_DIR/.git" ]]; then
  git clone --filter=blob:none --branch v2.1.9 https://github.com/iden3/circom.git "$RACE_CIRCOM_DIR"
fi
git -C "$RACE_CIRCOM_DIR" checkout --detach "$RACE_CIRCOM_COMMIT"
[[ "$(git -C "$RACE_CIRCOM_DIR" rev-parse HEAD)" == "$RACE_CIRCOM_COMMIT" ]]
cargo build --release --locked --manifest-path "$RACE_CIRCOM_DIR/Cargo.toml"

if [[ ! -d "$CIRCOMSPECT_DIR/.git" ]]; then
  git clone https://github.com/trailofbits/circomspect.git "$CIRCOMSPECT_DIR"
fi
git -C "$CIRCOMSPECT_DIR" checkout --detach "$CIRCOMSPECT_COMMIT"
[[ "$(git -C "$CIRCOMSPECT_DIR" rev-parse HEAD)" == "$CIRCOMSPECT_COMMIT" ]]
cargo build --release --locked --manifest-path "$CIRCOMSPECT_DIR/Cargo.toml"

(cd "$ROOT" && npm ci --no-audit --no-fund)

{
  "$CIRCOM_DIR/target/release/circom" --version
  "$ROOT/node_modules/.bin/snarkjs" --help | head -n 1
  echo "circom_commit=$CIRCOM_COMMIT"
  echo "racepass_circom_commit=$RACE_CIRCOM_COMMIT"
  echo "circomspect_commit=$CIRCOMSPECT_COMMIT"
  echo "circomspect_sha256=$(shasum -a 256 "$CIRCOMSPECT_DIR/target/release/circomspect" | awk '{print $1}')"
  forge --version | head -n 1
  anvil --version | head -n 1
}
