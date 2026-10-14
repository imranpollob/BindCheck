#!/usr/bin/env bash
# BindCheck T10: can Payy's existing route produce one valid agg_final proof (revision dcd5d96)?
# Route used: upstream test `zk-circuits circuits::tests::test_agg_final` (utxo -> agg_utxo -> agg_agg -> agg_final),
# unmodified, run with a pass-through `bb` recorder on PATH that only copies what the real pinned bb receives/writes.
#
# usage: bash scripts/t10.sh
# knobs: T10_BUILD_TIMEOUT (s, default 2400)  T10_TEST_TIMEOUT (s, default 3600)  T10_MAX_RSS_GIB (default 7)
# Needs scripts/t09.sh to have run once (pinned nargo/bb, payy checkout at dcd5d96, CRS dir). Network on first run.
# Newly generated artifacts live in build/T10/ and are NOT related to the committed fixtures/proofs/*.proof file.
# An all-padding-message proof establishes pipeline feasibility only: no effectful message, no advisory reproduction.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T10; B=build/T10; H=tools/cases/payy-history
REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36
BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
BUILD_TO="${T10_BUILD_TIMEOUT:-2400}"; TEST_TO="${T10_TEST_TIMEOUT:-3600}"; MAX_RSS="${T10_MAX_RSS_GIB:-7}"
mkdir -p "$L" "$B/bin" "$B/ts-rs"
step() { echo "[$(date +%H:%M:%S)] $*"; }

# ---- 0. preconditions ---------------------------------------------------------------------------------------------
[ -x "$BB" ] && [ -d "$H/.git" ] || { echo "run scripts/t09.sh first (pinned bb and payy checkout)"; exit 1; }
[ "$(git -C "$H" rev-parse HEAD)" = "$REV" ] || git -C "$H" checkout --quiet "$REV" || { echo "cannot check out $REV"; exit 1; }
[ "$(git -C "$H" rev-parse HEAD)" = "$REV" ] || { echo "worktree not at $REV"; exit 1; }
{ echo "revision: $(git -C "$H" rev-parse HEAD)"; echo "bb: $("$BB" --version)"; echo "cargo/rustc (pinned by rust-toolchain.toml, invoked as +1.91.0): $(cargo +1.91.0 --version) / $(rustc +1.91.0 --version)"
  echo "host: $(uname -srm), RAM $(sysctl -n hw.memsize | awk '{printf "%.1f GiB", $1/2^30}')"; echo "limits: build ${BUILD_TO}s, test ${TEST_TO}s, polled RSS cap ${MAX_RSS} GiB"; echo "date_utc: $(date -u +%FT%TZ)"; } > "$L/00_environment.txt"

# ---- 1. inspection evidence (no proving) --------------------------------------------------------------------------------
step "inner-key binding: bb vk hashes vs constants in the circuits"
{
  echo -e "revision\tcircuit\tbb_vk_hash_decimal\tkey_bytes_identical_to_committed"
  for r in c4d2c90 dcd5d96; do for c in agg_agg agg_utxo utxo; do d="$B/vkhash/$r-$c"; mkdir -p "$d"
    git -C "$H" cat-file -p "$r:fixtures/circuits/$c/program.json" > "$d/program.json"
    "$BB" write_vk --scheme ultra_honk -b "$d/program.json" -o "$d" -c build/T09/crs > "$d/log.txt" 2>&1
    h=$(python3 -I -c 'import sys;print(int.from_bytes(open(sys.argv[1],"rb").read(),"big"))' "$d/vk_hash")
    same=no; cmp -s "$d/vk" <(git -C "$H" cat-file -p "$r:fixtures/circuits/$c/key") && same=yes
    echo -e "$r\t$c\t$h\t$same"; done; done
  echo; echo "## constants (noir/agg_final/src/main.nr, noir/agg_utxo/src/main.nr)"
  for r in c4d2c90 dcd5d96; do echo "# $r"; git -C "$H" show "$r:noir/agg_final/src/main.nr" | grep -n 'global'; git -C "$H" show "$r:noir/agg_utxo/src/main.nr" | grep -n 'global'; done
} > "$L/10_inner_key_binding.txt" 2>&1
{ echo "## padding handling in code (dcd5d96)"
  echo "-- agg_utxo: verification always runs; slot 0 must be real"; git -C "$H" show "$REV:noir/agg_utxo/src/main.nr" | grep -n -E 'first proof cannot|ALWAYS|is_padding|verify_proof_with_type|UTXO_VERIFICATION_KEY_HASH,'
  echo "-- agg_agg: padding slots re-verify proofs[0]; allowed inner vk hashes are public inputs"; git -C "$H" show "$REV:noir/agg_agg/src/main.nr" | grep -n -E 'verification_key_hash|old_root == 0|proofs\[0\]|first_public_inputs|verify_proof_with_type'
  echo "-- agg_final: constants and assertions"; git -C "$H" show "$REV:noir/agg_final/src/main.nr" | grep -n -E 'global|assert|public_inputs\[[0-4]\]|verify_proof_with_type'
  echo "-- Rust: padding chunk handling (pkg/aggregator/src/block_prover/prove.rs)"; git -C "$H" show "$REV:pkg/aggregator/src/block_prover/prove.rs" | grep -n -E 'chunk_is_padding|padding_proof|ProofBytes::default|AggUtxoPublicInput::default'
  echo "-- upstream harness: pkg/zk-circuits/src/circuits/tests.rs test_agg_final"; git -C "$H" show "$REV:pkg/zk-circuits/src/circuits/tests.rs" | grep -n -E 'async fn test_agg_final\b|UtxoKind::Send|UtxoProofBundleWithMerkleProofs::default|prove_and_verify\(&agg'
} > "$L/11_padding_route_evidence.txt" 2>&1

# ---- 2. build the upstream test binary (bounded) ------------------------------------------------------------------------
export CARGO_TARGET_DIR="$ROOT/$B/cargo-target" RUSTFLAGS="--cfg tracing_unstable" TS_RS_EXPORT_DIR="$ROOT/$B/ts-rs"   # mirrors the repo's .cargo/config.toml
# Local toolchain workaround (not an upstream change): on this machine plain `c++` does not search the SDK's libc++ headers
# (attempt 1 failed in librocksdb-sys with "fatal error: 'memory' file not found"). Add the directory explicitly.
export CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"
echo "CXXFLAGS=$CXXFLAGS" >> "$L/00_environment.txt"
step "cargo build of zk-circuits tests (limit ${BUILD_TO}s)"
python3 scripts/t10_run_limited.py "$BUILD_TO" "$MAX_RSS" "$L/20_cargo_build.log" "$L/20_cargo_build.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --no-run || { echo "build did not complete (see $L/20_cargo_build.json)"; python3 -I scripts/t10_summarize.py "$L" || true; exit 2; }
python3 scripts/t10_run_limited.py 60 "$MAX_RSS" "$L/21_list_tests.log" "$L/21_list_tests.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits -- --list >/dev/null

# ---- 3. run the upstream test with the pass-through recorder on PATH --------------------------------------------------------
rm -rf "$B/capture"; cp scripts/t10_bb_recorder.sh "$B/bin/bb"; chmod +x "$B/bin/bb"
step "running circuits::tests::test_agg_final (limit ${TEST_TO}s)"
env T10_REAL_BB="$BB" T10_CAPTURE_DIR="$ROOT/$B/capture" PATH="$ROOT/$B/bin:$PATH" \
  python3 scripts/t10_run_limited.py "$TEST_TO" "$MAX_RSS" "$L/30_test_agg_final.log" "$L/30_test_agg_final.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits -- --exact circuits::tests::test_agg_final --nocapture
TEST_RC=$?

# ---- 4. summarize: identify the agg_final proof among captured bb calls, verify independently, decode ------------------------
python3 -I scripts/t10_summarize.py "$L" || true
echo; echo "An all-padding-message proof establishes pipeline feasibility only; it does not exercise effectful messages or reproduce the advisory."
exit $TEST_RC
