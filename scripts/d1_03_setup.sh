#!/usr/bin/env bash
# D1-03 setup: export pinned Payy sources, compile producers, stage the unchanged consumer and pinned OpenZeppelin,
# build the consumer AST. Writes only build/D1-03/, tools/oz-5.0.1/ (ignored) and results/raw/D1-03/setup/.
# Requires: tools/cases/payy-history (blobless clone of github.com/polybase/payy), tools/noir-1.0.0-beta.14/nargo, forge 1.4.1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
H=tools/cases/payy-history; B=build/D1-03; L=results/raw/D1-03/setup; NARGO="$ROOT/tools/noir-1.0.0-beta.14/nargo"
mkdir -p "$B" "$L"
declare -A REV=([A]=c4d2c9021b8fb9988816eb6987a734b830bfce15 [B]=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36)
{ echo "date_utc: $(date -u +%FT%TZ)"; echo "host: $(uname -srm)"; "$NARGO" --version | tr '\n' ' '; echo; forge --version | head -1
  echo "python: $(python3 --version)"; echo "node: $(node --version)"; echo "payy-history HEAD: $(git -C "$H" rev-parse HEAD)"; } > "$L/00_environment.txt"

# 1. Pinned source export (git archive; no third-party code is executed except the compilers).
for t in A B; do
  d="$B/payy-$t"
  if [ ! -d "$d/noir" ]; then mkdir -p "$d"; git -C "$H" archive "${REV[$t]}" noir eth/contracts fixtures/circuits/agg_agg fixtures/circuits/agg_final | tar -x -C "$d"; fi
  echo "$t ${REV[$t]} agg_agg/src/main.nr $(sha256sum "$d/noir/agg_agg/src/main.nr" | cut -d' ' -f1)" >> "$L/10_sources.txt"
  echo "$t ${REV[$t]} agg_final/src/main.nr $(sha256sum "$d/noir/agg_final/src/main.nr" | cut -d' ' -f1)" >> "$L/10_sources.txt"
  echo "$t ${REV[$t]} rollup3/RollupV1.sol $(sha256sum "$d/eth/contracts/rollup3/RollupV1.sol" | cut -d' ' -f1)" >> "$L/10_sources.txt"
done
cmp "$B/payy-A/eth/contracts/rollup3/RollupV1.sol" "$B/payy-B/eth/contracts/rollup3/RollupV1.sol" && echo "RollupV1.sol byte-identical at A and B" >> "$L/10_sources.txt"

# 2. Producer compilation (actual N=1000 programs). Printed ACIR + ABI are the analyzer inputs.
for t in A B; do for pkg in agg_agg agg_final; do
  out="$B/acir/$t-1000-$pkg"; mkdir -p "$(dirname "$out")"
  if [ ! -f "$out.acir.txt" ]; then
    ( cd "$B/payy-$t/noir" && "$NARGO" compile --package "$pkg" --print-acir > "$ROOT/$out.acir.txt" 2> "$ROOT/$out.compile.stderr" ); echo "compile $t $pkg exit=$?" >> "$L/20_compile.txt"
    cp "$B/payy-$t/noir/target/$pkg.json" "$out.program.json"
  fi
done; done
sha256sum "$B"/acir/* > "$L/21_producer_hashes.txt"

# 3. Pinned OpenZeppelin 5.0.1 (npm tarballs checked against eth/yarn.lock integrity at revision A).
OZ=tools/oz-5.0.1; mkdir -p "$OZ"
( cd "$OZ"
  for pkg in contracts contracts-upgradeable; do [ -f "openzeppelin-$pkg-5.0.1.tgz" ] || npm pack "@openzeppelin/$pkg@5.0.1" --silent > /dev/null; done )
for pkg in contracts contracts-upgradeable; do
  want=$(git -C "$H" show "${REV[A]}:eth/yarn.lock" | grep -A3 -E "^\"?@openzeppelin/$pkg@" | grep integrity | awk '{print $2}')
  got="sha512-$(openssl dgst -sha512 -binary "$OZ/openzeppelin-$pkg-5.0.1.tgz" | base64 | tr -d '\n')"
  [ "$want" = "$got" ] || { echo "OZ $pkg integrity MISMATCH" | tee -a "$L/30_oz_integrity.txt"; exit 1; }
  echo "OZ $pkg MATCHES yarn.lock $got" >> "$L/30_oz_integrity.txt"
done
[ -d "$OZ/contracts" ] || { mkdir -p "$OZ/contracts" "$OZ/upgradeable"; tar -xzf "$OZ/openzeppelin-contracts-5.0.1.tgz" -C "$OZ/contracts" --strip-components=1; tar -xzf "$OZ/openzeppelin-contracts-upgradeable-5.0.1.tgz" -C "$OZ/upgradeable" --strip-components=1; }

# forge-std at the repository's existing pin (scripts/t02.sh), used only by the replay test harness.
FORGE_STD_TAG=v1.9.7; FORGE_STD_COMMIT=77041d2ce690e692d6e03cc812b57d1ddaa4d505
[ -d lib/forge-std ] || { mkdir -p lib; git clone --quiet --depth 1 --branch "$FORGE_STD_TAG" https://github.com/foundry-rs/forge-std lib/forge-std; }
[ "$(git -C lib/forge-std rev-parse HEAD)" = "$FORGE_STD_COMMIT" ] || { echo "forge-std not at pinned commit"; exit 1; }
echo "forge-std $FORGE_STD_TAG $FORGE_STD_COMMIT" >> "$L/30_oz_integrity.txt"

# 4. Consumer workspace: unchanged RollupV1 (revision A; byte-identical at B), compiled like upstream (solc 0.8.20, viaIR, runs 200).
C="$B/consumer"; mkdir -p "$C/src/rollup3" "$C/src/noir" "$C/test"
cp "$B/payy-A/eth/contracts/rollup3/RollupV1.sol" "$C/src/rollup3/RollupV1.sol"
cp "$B/payy-A/eth/contracts/IUSDC.sol" "$C/src/IUSDC.sol"
cp "$B/payy-A/eth/contracts/noir/IVerifier.sol" "$C/src/noir/IVerifier.sol"
cat > "$C/foundry.toml" <<EOF
[profile.default]
src = "src"
test = "test"
out = "out"
cache_path = "cache"
libs = []
solc_version = "0.8.20"
evm_version = "cancun"
via_ir = true
optimizer = true
optimizer_runs = 200
ast = true
fs_permissions = [{ access = "read", path = "./replay" }]
remappings = [
  "@openzeppelin/contracts/=$ROOT/$OZ/contracts/",
  "@openzeppelin/contracts-upgradeable/=$ROOT/$OZ/upgradeable/",
  "forge-std/=$ROOT/lib/forge-std/src/",
]
EOF
( cd "$C" && forge build --ast > "$ROOT/$L/40_forge_build.log" 2>&1 ); echo "forge build exit=$?" >> "$L/40_forge_build.log"
sha256sum "$C"/src/rollup3/RollupV1.sol "$C"/out/RollupV1.sol/RollupV1.json > "$L/41_consumer_hashes.txt"
echo "setup complete"
