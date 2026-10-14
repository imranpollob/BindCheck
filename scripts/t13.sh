#!/usr/bin/env bash
# BindCheck T13: one proof with a single MINT message (upstream route) and its settlement through Payy's real local consumer.
# usage: bash scripts/t13.sh          reuses the proof from results/raw/T13/agg_final_mint if it exists (no re-proving)
#        T13_FORCE=1 bash scripts/t13.sh   regenerates the proof (about a minute on the T10 machine)
# knobs: T10_BUILD_TIMEOUT (s, 2400)  T13_PROVE_TIMEOUT (s, 3600)  T10_MAX_RSS_GIB (7)
# Prerequisites: scripts/t09.sh, scripts/t10.sh and scripts/t12.sh have run (payy checkout at the revision, pinned bb/nargo, the cargo target cache,
# OpenZeppelin 5.0.1 under tools/oz-5.0.1, consumer sources under payy-consumer/src); forge.
# Local testbed only. This demonstrates one local effectful execution; it is not advisory reproduction, a vulnerability claim or BindCheck detection.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T13; H=tools/cases/payy-history; B=build/T13
REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36; BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
mkdir -p "$L" "$B/bin" "$B/../T12/bins"
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
[ "$(git -C "$H" rev-parse "$REV^{commit}" 2>/dev/null)" = "$REV" ] || die "payy checkout at $REV missing (scripts/t09.sh)"
[ -x "$BB" ] && [ -d tools/oz-5.0.1/contracts ] && [ -f payy-consumer/src/rollup3/RollupV1.sol ] || die "run scripts/t09.sh, t10.sh and t12.sh first"
for f in agg_final_HonkVerifier.bin agg_final_HonkVerifier.linkrefs.json agg_final_ZKTranscriptLib.bin; do git -C "$H" cat-file -p "$REV:eth/contracts/noir/$f" > "build/T12/bins/$f"; done
rm -f "$L"/1*.txt "$L"/5*.log "$L"/5*.txt "$L"/90_summary.json; rm -rf "$L/observations"
{ echo "revision: $REV"; echo "bb: $("$BB" --version)"; echo "cargo/rustc: $(cargo +1.91.0 --version) / $(rustc +1.91.0 --version)"; forge --version | head -1; echo "host: $(uname -srm), RAM $(sysctl -n hw.memsize | awk '{printf "%.1f GiB", $1/2^30}')"; echo "date_utc: $(date -u +%FT%TZ)"; } > "$L/00_environment.txt"

# ---- 1. mint-path trace (source excerpts at the pinned revision; interpretation is in reports/T13.md) --------------------------------------
{
  echo "## leaf circuit noir/utxo/src/main.nr: mint branch and message layout"
  git -C "$H" show "$REV:noir/utxo/src/main.nr" | grep -n -E 'messages: pub|let kind = messages\[0\]|msg_note_kind|msg_value|let mint_hash|kind == 2|Mint output must match|Mint hash must match|Mint note kind must match|assert_max_bit_size::<240>'
  echo; echo "## noir/agg_utxo/src/main.nr: mint message placement"
  git -C "$H" show "$REV:noir/agg_utxo/src/main.nr" | grep -n -E 'is_mint|proof .kind. must match message|msg_note_kind = messages|messages_index \+= 4|Verify all other messages are zero'
  echo; echo "## noir/agg_agg/src/main.nr: compaction (mint consumes 4 words) and tail check"
  git -C "$H" show "$REV:noir/agg_agg/src/main.nr" | grep -n -E 'proof_message == 2|next_check \+= 4|assert_message_tail_zero\(messages'
  echo; echo "## consumer rollup3/RollupV1.sol: registration, verification, token mapping"
  git -C "$H" show "$REV:eth/contracts/rollup3/RollupV1.sol" | grep -n -E 'Mint hash is hash of commitments|function mint\(|Mint already exists|Token not found for note kind|safeTransferFrom|mints\[mint_hash\] = Mint|emit MintAdded|function verifyMint|Mint value invalid|Mint note kind invalid|Mint already spent|mints\[hash\]\.spent = true|emit Minted|function addToken|tokens\[initialNoteKind\]|_setRootHash\(|0x0577b5b4aa3eaba7'
  echo; echo "## empty-tree root constant used by Rust (pkg/contracts/src/empty_merkle_tree_root_hash.txt)"
  git -C "$H" show "$REV:pkg/contracts/src/empty_merkle_tree_root_hash.txt"
  echo; echo "## upstream proof-generation tests that already build mint proofs (pkg/zk-circuits/src/circuits/tests.rs)"
  git -C "$H" show "$REV:pkg/zk-circuits/src/circuits/tests.rs" | grep -n -E 'async fn test_(utxo_mint|agg_utxo_mint_burn|agg_final_with_mint_and_burn)|UtxoKind::Mint|UtxoKind::Burn'
  echo; echo "## block prover padding (pkg/aggregator/src/block_prover/prove.rs)"
  git -C "$H" show "$REV:pkg/aggregator/src/block_prover/prove.rs" | grep -n -E 'fn padding_proof|ProofBytes::default|AggUtxoPublicInput::default'
} > "$L/10_mint_path_evidence.txt" 2>&1

# ---- 2. proof generation (reused unless forced) ------------------------------------------------------------------------------------------
if [ "${T13_FORCE:-0}" = 1 ] || [ ! -f "$L/agg_final_mint/proof" ] || [ ! -f "$L/40_proof_summary.json" ]; then
  echo "[proof] generating (harness payy-harness/t13_mint.rs, upstream route, pinned bb)"
  export CARGO_TARGET_DIR="$ROOT/build/T10/cargo-target" RUSTFLAGS="--cfg tracing_unstable" TS_RS_EXPORT_DIR="$ROOT/build/T10/ts-rs"   # mirrors the repo's .cargo/config.toml
  export CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"                                                             # local toolchain workaround recorded in T10
  mkdir -p "$H/pkg/zk-circuits/tests" "$L/harness_out"; cp payy-harness/t13_mint.rs "$H/pkg/zk-circuits/tests/t13_mint.rs"            # NEW untracked file; no upstream file is edited
  python3 scripts/t10_run_limited.py "${T10_BUILD_TIMEOUT:-2400}" "${T10_MAX_RSS_GIB:-7}" "$L/20_cargo_build.log" "$L/20_cargo_build.json" -- \
    cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --test t13_mint --no-run || die "harness build did not complete (see $L/20_cargo_build.json)"
  rm -rf "$B/capture"; cp scripts/t10_bb_recorder.sh "$B/bin/bb"; chmod +x "$B/bin/bb"
  env T10_REAL_BB="$BB" T10_CAPTURE_DIR="$ROOT/$B/capture" T13_OUT_DIR="$ROOT/$L/harness_out" PATH="$ROOT/$B/bin:$PATH" \
    python3 scripts/t10_run_limited.py "${T13_PROVE_TIMEOUT:-3600}" "${T10_MAX_RSS_GIB:-7}" "$L/30_harness_run.log" "$L/30_harness_run.json" -- \
    cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --test t13_mint -- --nocapture || { echo "proof generation did not complete (see $L/30_harness_run.json)"; python3 -I scripts/t13_summarize.py "$L" > /dev/null; exit 2; }
  python3 -I scripts/t13_summarize.py "$L" > "$L/41_summarize.out"
else
  echo "[proof] reusing results/raw/T13/agg_final_mint (set T13_FORCE=1 to regenerate)"
fi
python3 -I - <<'PY' || die "proof not natively verified in the recorded summary"
import json
a = json.load(open("results/raw/T13/40_proof_summary.json"))["agg_final_proof"]
assert a["independent_native_verify"]["exit"] == 0 and a["control_value_tampered_native_verify"]["exit"] != 0
print("proof", a["proof_sha256"][:16], "public inputs", a["public_inputs_sha256"][:16], "mint:", a["decoded"]["mint_message"])
PY

# ---- 3. settlement through the real local consumer (T12 pattern) ----------------------------------------------------------------------------
FOUNDRY_PROFILE=payy-consumer forge test --match-path 'payy-consumer/test/MintSettlement.t.sol' -vv > "$L/50_forge.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_forge.log" | grep -E '^\[(PASS|FAIL)|Suite result|Ran [0-9]+ tests?' | tee "$L/51_forge_results.txt"

# ---- 4. merged summary ------------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import glob, json, os, sys
L, rc = sys.argv[1], int(sys.argv[2])
p = json.load(open(f"{L}/40_proof_summary.json"))
a = p["agg_final_proof"]
obs = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/observations/*.json")}
out = {"revision": p["revision"], "proof": {"status": p["status"], "proof_sha256": a["proof_sha256"], "public_inputs_sha256": a["public_inputs_sha256"],
       "native_verify_exit": a["independent_native_verify"]["exit"], "tampered_value_native_verify_exit": a["control_value_tampered_native_verify"]["exit"],
       "decoded": a["decoded"], "generation": {"harness_run": {k: p["harness_run"][k] for k in ("elapsed_s", "polled_peak_group_rss_gib", "largest_single_process_maxrss_gib")} if p.get("harness_run") else None,
       "bb_calls": [{k: c[k] for k in ("call", "circuit", "real_s", "max_rss_gib", "exit")} for c in p["bb_calls"]]}},
       "forge_exit": rc, "observations": {k: {"status": v["status"], "reason": v["reason"], "registrationGas": v["registrationGas"], "settlementGas": v["settlementGas"],
       "registeredValue": v["registeredValue"], "verifierCall": v["verifierCall"], "rootBefore": v["pre"]["rootHash"], "rootAfter": v["post"]["rootHash"],
       "mintSpentBefore": v["pre"]["mint"]["spent"], "mintSpentAfter": v["post"]["mint"]["spent"], "balancesBefore": v["pre"]["tokenBalances"], "balancesAfter": v["post"]["tokenBalances"]}
       for k, v in sorted(obs.items())}}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out["observations"], indent=1)[:1800])
PY
echo; echo "One local effectful execution only: not advisory reproduction, not a vulnerability claim, not BindCheck detection."
exit $RC
