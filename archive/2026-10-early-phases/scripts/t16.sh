#!/usr/bin/env bash
# BindCheck T16: does the T15 earlier-revision (c4d2c9021b8fb9988816eb6987a734b830bfce15) agg_agg candidate proof propagate
# through that revision's own agg_final circuit? Reuses the exact T15 agg_agg proof/public-input BYTES on disk (no
# regeneration, no new agg_agg proving): results/raw/T15/c4d2c90/{control,candidate}/{proof,public_inputs}.
# usage: bash scripts/t16.sh   (about 20-30s; revision A's harness is already built by scripts/t15.sh)
# Prerequisites: scripts/t15.sh has run (worktree tools/cases/payy-c4d2c90 at c4d2c90, its cargo target in build/T15/cargo-target-c4d2c90,
# and results/raw/T15/c4d2c90/{control,candidate} present).
# Local testbed only. Tests proof PROPAGATION through one more circuit layer only; it is not advisory reproduction, not a
# consumer/financial-impact claim, and the synthetic record is not backed by any real burn utxo or note.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T16; B=build/T16; H=tools/cases/payy-c4d2c90; T15=results/raw/T15/c4d2c90
REV=c4d2c9021b8fb9988816eb6987a734b830bfce15
BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
mkdir -p "$L" "$B/bin"
[ -e "$H/.git" ] && [ "$(git -C "$H" rev-parse HEAD)" = "$REV" ] || die "worktree $H is not at $REV (run scripts/t15.sh first)"   # .git is a FILE in a worktree, not a directory
[ -d "build/T15/cargo-target-c4d2c90" ] || die "revision A's cargo target (build/T15/cargo-target-c4d2c90) is missing (run scripts/t15.sh first)"
for f in "$T15/control/proof" "$T15/control/public_inputs" "$T15/candidate/proof" "$T15/candidate/public_inputs"; do
  [ -f "$f" ] || die "missing T15 artifact $f (run scripts/t15.sh first)"
done
rm -f "$L"/0*.txt "$L"/1*.txt "$L"/2*.txt "$L"/3*.json "$L"/3*.log "$L"/9*.json; rm -rf "$L/control" "$L/candidate" "$L/harness_out" "$B/capture-c4d2c90"
{ echo "revision (earlier, matches T15's c4d2c90 side): $(git -C "$H" rev-parse HEAD)"; echo "bb: $("$BB" --version)"
  echo "cargo/rustc (+1.91.0): $(cargo +1.91.0 --version) / $(rustc +1.91.0 --version)"; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"
  echo; echo "## T15 c4d2c90 artifact hashes being reused as-is (no regeneration)"
  for p in control/proof control/public_inputs candidate/proof candidate/public_inputs agg_agg_key_committed; do
    [ -f "$T15/$p" ] && echo "sha256 $p: $(shasum -a 256 "$T15/$p" | cut -d' ' -f1)  ($(wc -c < "$T15/$p") bytes)"; done
  echo; echo "## agg_final source and committed key at $REV"
  echo "sha256 noir/agg_final/src/main.nr: $(git -C "$H" show "$REV:noir/agg_final/src/main.nr" | shasum -a 256 | cut -d' ' -f1)"
  echo "sha256 fixtures/circuits/agg_final/key: $(git -C "$H" cat-file -p "$REV:fixtures/circuits/agg_final/key" | shasum -a 256 | cut -d' ' -f1)"
  echo "sha256 fixtures/circuits/agg_final/program.json: $(git -C "$H" cat-file -p "$REV:fixtures/circuits/agg_final/program.json" | shasum -a 256 | cut -d' ' -f1)"
} > "$L/00_environment.txt"

# ---- 1. source evidence: how agg_final consumes an agg_agg proof (excerpts only; interpretation is in reports/T16.md) -------------------------------
{
  echo "## noir/agg_final/src/main.nr at $REV (full file: it is short)"; git -C "$H" show "$REV:noir/agg_final/src/main.nr"
  echo; echo "## Rust wiring: AggFinal takes exactly one AggAggProof (pkg/zk-primitives/src/agg_final.rs)"
  git -C "$H" show "$REV:pkg/zk-primitives/src/agg_final.rs" | grep -n -E 'pub struct AggFinal|pub fn new|pub proof: AggAggProof'
  echo; echo "## pkg/zk-circuits/src/circuits/agg_final.rs: AggFinalInput::from(AggFinal) copies proof.public_inputs.{old_root,new_root,commit_hash,messages} and proof.proof.to_fields() verbatim; no recomputation"
  git -C "$H" show "$REV:pkg/zk-circuits/src/circuits/agg_final.rs" | sed -n '/impl From<AggFinal> for AggFinalInput/,/^}/p'
  echo; echo "## final public-input layout (AggFinalPublicInput::to_bytes): old_root, new_root, commit_hash, then messages[] -- messages start at outer index 3"
  git -C "$H" show "$REV:pkg/zk-primitives/src/agg_final.rs" | sed -n '/impl AggFinalPublicInput/,/^}/p'
} > "$L/10_source_evidence.txt" 2>&1

# ---- 2. the two attempts: T15's control and candidate agg_agg proof BYTES fed into agg_final, via the existing harness --------------------------------
mkdir -p "$H/pkg/zk-circuits/tests"; cp payy-harness/t16_tail_to_agg_final.rs "$H/pkg/zk-circuits/tests/t16_tail_to_agg_final.rs"   # NEW untracked file; no upstream file edited
cp scripts/t10_bb_recorder.sh "$B/bin/bb"; chmod +x "$B/bin/bb"
env PATH="$ROOT/$B/bin:$PATH" T10_REAL_BB="$BB" T10_CAPTURE_DIR="$ROOT/$B/capture-c4d2c90" \
  RUSTFLAGS="--cfg tracing_unstable" CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1" \
  CARGO_TARGET_DIR="$ROOT/build/T15/cargo-target-c4d2c90" TS_RS_EXPORT_DIR="$ROOT/build/T15/ts-rs-c4d2c90" \
  T16_CONTROL_PI="$ROOT/$T15/control/public_inputs" T16_CONTROL_PROOF="$ROOT/$T15/control/proof" \
  T16_CANDIDATE_PI="$ROOT/$T15/candidate/public_inputs" T16_CANDIDATE_PROOF="$ROOT/$T15/candidate/proof" \
  T16_OUT_DIR="$ROOT/$L/harness_out" \
  python3 scripts/t10_run_limited.py 1800 7 "$L/30_run.log" "$L/30_run.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --test t16_tail_to_agg_final -- --nocapture
RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/30_run.log" > "$L/31_run_clean.txt"

# ---- 3. independent re-verification (fresh bb process, committed agg_final key) and decode --------------------------------------------------------
python3 -I scripts/t16_summarize.py "$H" "$B/capture-c4d2c90" "$L/harness_out" "$L" > "$L/40_summarize.out" 2>&1

# ---- 4. later-revision contrast: already established by T15, not rerun here (no agg_agg proof exists at B for this candidate) ---------------------
{
  echo "No separate run performed: at the check-added revision (dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36), T15 already found this"
  echo "exact candidate witness rejected INSIDE agg_agg's own witness generation, before any bb call and before any agg_agg proof existed"
  echo "(results/raw/T15/dcd5d96/harness.json: candidate.witness_satisfied_and_proof_generated=false;"
  echo " results/raw/T15/31_noir_diagnostic_dcd5d96.txt: \"Assertion failed: Message is not zero\", noir/agg_agg/src/main.nr:120, called from :108)."
  echo "There is therefore no agg_agg proof at that revision to feed into agg_final for this candidate; T16 cannot and does not add to that result."
} > "$L/50_later_revision_contrast.txt"

# ---- 5. summary -----------------------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import json, sys
L, rc = sys.argv[1], int(sys.argv[2])
s = json.load(open(f"{L}/40_summary.json"))
out = {"harness_exit": rc, "all_bb_calls_exit_0": s["all_bb_calls_exit_0"],
       "control": {k: s["control"].get(k) for k in ("witness_satisfied_and_proof_generated", "proof_sha256", "public_inputs_sha256") if k in s["control"]} | {"independent_native_verify_exit": s["control"].get("independent_native_verify", {}).get("exit")},
       "candidate": {k: s["candidate"].get(k) for k in ("witness_satisfied_and_proof_generated", "proof_sha256", "public_inputs_sha256") if k in s["candidate"]} | {"independent_native_verify_exit": s["candidate"].get("independent_native_verify", {}).get("exit"),
                     "record_at_outer_indices": [d["outer_public_input_index"] for d in s["candidate"].get("decoded", {}).get("nonzero_message_words", [])][4:] if s["candidate"]["witness_satisfied_and_proof_generated"] else None,
                     "tamper_control_exit": s["candidate"].get("tamper_control_last_nonzero_word_flipped", {}).get("exit")},
       "control_vs_candidate_differences": s.get("control_vs_candidate_public_input_differences")}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
git -C "$H" status --short > "$L/91_checkout_status.txt"
echo; echo "Proof-propagation test only; not advisory reproduction, not a consumer/financial-impact claim. The candidate record is synthetic."
exit $RC
