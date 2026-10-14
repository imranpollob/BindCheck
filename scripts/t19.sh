#!/usr/bin/env bash
# BindCheck T19: check the Payy repair (assert_message_tail_zero) against the T18 result, at the check-added revision
# dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36. Reuses: T15's t15_tail.rs harness (replayed, not modified) and T13's existing
# agg_final mint proof (not regenerated). No new proof, no circuit/consumer change.
# usage: bash scripts/t19.sh   (about a minute; the Rust replay reuses T15/T16's cached cargo target, no cold build)
# Prerequisites: scripts/t15.sh (worktree tools/cases/payy-history at dcd5d96, build/T10/cargo-target, the untracked
# pkg/zk-circuits/tests/t15_tail.rs) and scripts/t13.sh (results/raw/T13/agg_final_mint, build/T12/bins) have run.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T19; H=tools/cases/payy-history
REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36; BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
mkdir -p "$L" build/T19/bin
[ "$(git -C "$H" rev-parse HEAD)" = "$REV" ] || die "checkout $H is not at $REV (run scripts/t15.sh/t09.sh first)"
[ -f "$H/pkg/zk-circuits/tests/t15_tail.rs" ] || die "T15's harness is missing from the checkout (run scripts/t15.sh first)"
[ -f results/raw/T13/agg_final_mint/proof ] && [ -f results/raw/T13/40_proof_summary.json ] || die "run scripts/t13.sh first"
[ -f build/T12/bins/agg_final_HonkVerifier.bin ] || die "run scripts/t12.sh first"
rm -f "$L"/0*.txt "$L"/3*.log "$L"/3*.json "$L"/3*.txt "$L"/5*.log "$L"/5*.txt "$L"/9*.json; rm -rf "$L/dcd5d96" "$L/observations" build/T19/capture-dcd5d96
{ echo "revision: $(git -C "$H" rev-parse HEAD)"; echo "bb: $("$BB" --version)"; forge --version | head -1; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"
  echo; echo "## reused-artifact hashes"
  echo "T13 agg_final proof : $(shasum -a 256 results/raw/T13/agg_final_mint/proof | cut -d' ' -f1)"
  echo "T13 public inputs    : $(shasum -a 256 results/raw/T13/agg_final_mint/public_inputs | cut -d' ' -f1)"
  echo "revision B agg_final key sha256 (from T15): $(git -C "$H" cat-file -p "$REV:fixtures/circuits/agg_final/key" | shasum -a 256 | cut -d' ' -f1)"
  echo "revision A agg_final key sha256 (from T15, for contrast only, NOT used below): $(shasum -a 256 results/raw/T15/c4d2c90/control/public_inputs > /dev/null; git -C tools/cases/payy-c4d2c90 cat-file -p HEAD:fixtures/circuits/agg_final/key 2>/dev/null | shasum -a 256 | cut -d' ' -f1)"
} > "$L/00_environment.txt"

# ---- 1. replay T15's candidate witness against this (the check-added) revision's agg_agg circuit; reuse the existing harness file verbatim ---------
cp scripts/t10_bb_recorder.sh build/T19/bin/bb; chmod +x build/T19/bin/bb
env RUST_MIN_STACK=536870912 PATH="$ROOT/build/T19/bin:$PATH" T10_REAL_BB="$BB" T10_CAPTURE_DIR="$ROOT/build/T19/capture-dcd5d96" \
  RUSTFLAGS="--cfg tracing_unstable" CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1" \
  CARGO_TARGET_DIR="$ROOT/build/T10/cargo-target" TS_RS_EXPORT_DIR="$ROOT/build/T10/ts-rs" T15_OUT_DIR="$ROOT/$L/dcd5d96" \
  python3 scripts/t10_run_limited.py 1800 7 "$L/30_run_dcd5d96.log" "$L/30_run_dcd5d96.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --test t15_tail -- --nocapture
sed 's/\x1b\[[0-9;]*m//g' "$L/30_run_dcd5d96.log" | awk '/^error: /{p=1} /^test t15/{p=0} p' > "$L/31_noir_diagnostic_dcd5d96.txt"

# ---- 2+3. legitimate mint-only control through the matching dcd5d96 agg_final/consumer path; direct balance checks (new, minimal test) ------------
FOUNDRY_PROFILE=payy-consumer forge test --match-path 'payy-consumer/test/RepairedMintControl.t.sol' -vv > "$L/50_forge.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_forge.log" | grep -E '^\[(PASS|FAIL)|Suite result|Ran [0-9]+ tests?' | tee "$L/51_forge_results.txt"

# ---- 4. revisions are never mixed here: the two agg_final keys differ (recorded above and in T12/T15); T18's earlier-revision proof is not
#         submitted to this revision's verifier, and no such result is reported. -----------------------------------------------------------------
{
  echo "Not performed: submitting T18's c4d2c90 agg_final proof to this (dcd5d96) revision's verifier."
  echo "Reason: the two revisions' committed agg_final keys differ (sha256 above; also results/raw/T12/11_hash_derivation.txt and the vk_hash"
  echo "binary values 0x122d2ac7... (A) vs 0x0701c58c... (B)), so the registry-key lookup and the verifier bytecode itself are revision-specific;"
  echo "any such cross-submission would not be a valid test of this revision's circuit and is excluded by design, not by a result."
} > "$L/60_no_cross_revision_submission.txt"

# ---- 5. summary -----------------------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import json, sys
L, rc = sys.argv[1], int(sys.argv[2])
h = json.load(open(f"{L}/dcd5d96/harness.json"))
diag = open(f"{L}/31_noir_diagnostic_dcd5d96.txt").read()
ctrl = json.load(open(f"{L}/observations/legitimate_mint_control_at_repaired_revision.json")) if __import__("os").path.exists(f"{L}/observations/legitimate_mint_control_at_repaired_revision.json") else None
out = {
    "forge_exit": rc,
    "agg_agg_replay": {
        "control_witness_satisfied": h["control"]["witness_satisfied_and_proof_generated"],
        "control_native_verify": h["control"]["native_verify_via_harness"],
        "candidate_witness_satisfied": h["candidate"]["witness_satisfied_and_proof_generated"],
        "candidate_failure_stage": h["candidate"]["failure_stage"],
        "candidate_error": h["candidate"]["error"],
        "diagnostic_mentions_Message_is_not_zero": "Message is not zero" in diag,
        "diagnostic_lines": sorted(set(__import__("re").findall(r"agg_agg/src/main\.nr:(\d+)", diag))),
    },
    "legitimate_mint_control_at_repaired_revision": ctrl,
}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
echo; echo "Local result for the repaired revision and owned test identities only; no live deployment impact is claimed."
exit $RC
