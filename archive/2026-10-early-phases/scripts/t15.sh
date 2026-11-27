#!/usr/bin/env bash
# BindCheck T15: differential test of Payy's agg_agg message-tail constraint across two source revisions.
#   Earlier revision A = c4d2c9021b8fb9988816eb6987a734b830bfce15 (no tail check in agg_agg)
#   Check-added revision B = dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36 (assert_message_tail_zero in agg_agg)
# usage: bash scripts/t15.sh        (about 3 minutes warm; the very first run also builds revision A's Rust workspace cold, ~10+ minutes)
# knobs: T15_BUILD_TIMEOUT (s, 2400)  T15_RUN_TIMEOUT (s, 3600)  T10_MAX_RSS_GIB (7)
# Prerequisites: scripts/t09.sh and t10.sh ran (checkout of B at tools/cases/payy-history, pinned nargo/bb, CRS in build/T09/crs, B's cargo cache in build/T10).
# RUST_MIN_STACK=512 MiB is set for the test thread: the generated agg_agg input struct (about 1.6k field elements plus two 508-element proofs, copied by value through async code) overflowed the default 2 MiB test stack in the first attempt (SIGABRT, no proof work done).
# Each revision is built and tested separately with its own circuit, committed key and Rust code; nothing is shared across revisions.
# Local testbed only. This tests a candidate circuit property; it is not advisory reproduction, a financial-impact claim, or BindCheck detection.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T15; B=build/T15
REV_A=c4d2c9021b8fb9988816eb6987a734b830bfce15; REV_B=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36
HB=tools/cases/payy-history; HA=tools/cases/payy-c4d2c90
BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"; NARGO="$ROOT/tools/noir-1.0.0-beta.14/nargo"
BUILD_TO="${T15_BUILD_TIMEOUT:-2400}"; RUN_TO="${T15_RUN_TIMEOUT:-3600}"; MAX_RSS="${T10_MAX_RSS_GIB:-7}"
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
step() { echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$L" "$B/bin"
[ -x "$BB" ] && [ -x "$NARGO" ] && [ -d "$HB/.git" ] || die "run scripts/t09.sh and t10.sh first"
[ "$(git -C "$HB" rev-parse "$REV_B^{commit}")" = "$REV_B" ] && [ "$(git -C "$HB" rev-parse HEAD)" = "$REV_B" ] || die "checkout $HB is not at $REV_B"
[ "$(git -C "$HB" rev-parse "$REV_A^{commit}" 2>/dev/null)" = "$REV_A" ] || die "revision $REV_A not present in $HB"
if [ ! -d "$HA" ]; then git -C "$HB" worktree add --detach "../payy-c4d2c90" "$REV_A" > /dev/null 2>&1 || die "cannot create worktree $HA"; fi
[ "$(git -C "$HA" rev-parse HEAD)" = "$REV_A" ] || die "worktree $HA is not at $REV_A"
rm -f "$L"/0*.txt "$L"/1*.txt "$L"/2*.txt "$L"/2*.json "$L"/2*.log "$L"/9*.json; rm -rf "$L/dcd5d96" "$L/c4d2c90" "$B/capture-c4d2c90" "$B/capture-dcd5d96"
{ echo "revision A (earlier): $REV_A"; echo "revision B (check added): $REV_B"; echo "bb: $("$BB" --version)"; echo "nargo: $("$NARGO" --version | tr '\n' ' ')"
  echo "cargo/rustc (+1.91.0, pinned by each revision's rust-toolchain.toml): $(cargo +1.91.0 --version) / $(rustc +1.91.0 --version)"
  echo "host: $(uname -srm), RAM $(sysctl -n hw.memsize | awk '{printf "%.1f GiB", $1/2^30}')"; echo "date_utc: $(date -u +%FT%TZ)"
  echo "limits: build ${BUILD_TO}s, run ${RUN_TO}s, polled RSS cap ${MAX_RSS} GiB"
  for r in "$REV_A:$HA" "$REV_B:$HB"; do rev=${r%%:*}; h=${r#*:}; for c in agg_agg agg_utxo utxo agg_final; do
    echo "sha256 $rev fixtures/circuits/$c/{program.json,key}: $(git -C "$h" cat-file -p "$rev:fixtures/circuits/$c/program.json" | shasum -a 256 | cut -c1-16) $(git -C "$h" cat-file -p "$rev:fixtures/circuits/$c/key" | shasum -a 256 | cut -c1-16)"; done; done; } > "$L/00_environment.txt"

# ---- 1. source evidence (excerpts; interpretation is in reports/T15.md) -----------------------------------------------------------------------------
S() { git -C "$HB" show "$1:$2"; }
{
  echo "## A. what changed in noir/ and in the consumer between the two revisions (stat only; full agg_agg diff in 11_agg_agg_diff.txt)"
  git -C "$HB" diff --stat "$REV_A" "$REV_B" -- noir/agg_agg noir/agg_utxo noir/agg_final noir/utxo noir/common | cat
  echo "(consumer eth/contracts/rollup3/ and eth/contracts/mocks differ?)"; git -C "$HB" diff --stat "$REV_A" "$REV_B" -- eth/contracts/rollup3 eth/contracts/mocks | cat; echo "(empty above = the consumer source is byte-identical at both revisions)"
  echo; echo "## B. calls of the helper and what exists at each revision"
  for r in "$REV_A" "$REV_B"; do echo "# $r"; S "$r" noir/agg_agg/src/main.nr | grep -n -E 'assert_message_tail_zero|Message is not zero|messages_index|fn main|messages: pub' || true; done
  echo; echo "## C. agg_agg message handling at B (lines 47-79: end detection, compaction, equality of exported words)"; S "$REV_B" noir/agg_agg/src/main.nr | sed -n '47,79p'
  echo; echo "## D. the new helper and its tests at B"; S "$REV_B" noir/agg_agg/src/main.nr | sed -n '108,146p'
  echo; echo "## E. agg_utxo already forces the region after its own exported words to zero (both revisions)"
  for r in "$REV_A" "$REV_B"; do echo "# $r"; S "$r" noir/agg_utxo/src/main.nr | grep -n -E 'Verify all other messages are zero|i >= messages_index|Message is not zero'; done
  echo; echo "## F. agg_final passes the 1000 message words straight through as agg_agg public inputs (no own constraint on them), at both revisions"
  for r in "$REV_A" "$REV_B"; do echo "# $r"; S "$r" noir/agg_final/src/main.nr | grep -n -E 'messages|public_inputs\[i \+ 5\]'; done
  echo; echo "## G. Rust-side documentation of the intended layout (B): compacted messages with trailing zeros"
  S "$REV_B" pkg/zk-primitives/src/agg_agg.rs | grep -n -E 'compact|trailing zeros|next_check|Mint|Burn, Swap|fn messages_count|fn iterate_messages'
  S "$REV_B" pkg/zk-primitives/src/agg_utxo.rs | grep -n -E 'compaction|trailing zeros|messages\[\.\.4\]|Remaining elements'
  echo; echo "## H. consumer parser (rollup3/RollupV1.sol at B): scans every message slot; kind 0 skips one word, 2 = mint (4 words), 3 = burn (5 words), other kinds revert"
  S "$REV_B" eth/contracts/rollup3/RollupV1.sol | sed -n '/function verifyAllMessages/,/^    function verifyMint/p' | sed '$d'
  S "$REV_B" eth/contracts/rollup3/RollupV1.sol | grep -n -E 'verifyAllMessages\(|messages_length|publicInputs.length|Invalid message kind'
  echo; echo "## I. message-kind grammar in docs/specs, if any"; git -C "$HB" grep -n -i -E 'message' "$REV_B" -- docs 2>/dev/null | head -20 || true
} > "$L/10_source_evidence.txt" 2>&1
git -C "$HB" diff "$REV_A" "$REV_B" -- noir/agg_agg > "$L/11_agg_agg_diff.txt"

# ---- 2. artifact provenance per revision: source -> compiled agg_agg -> committed program -> committed key -> vk hash -----------------------------------
mkdir -p "$B/crs"; CRS=build/T09/crs; [ -d "$CRS" ] || CRS="$B/crs"
for pair in "A:$REV_A:$HA" "B:$REV_B:$HB"; do IFS=: read -r tag rev h <<<"$pair"
  O="$L/20_provenance_$tag.txt"; : > "$O"
  { echo "## revision $tag = $rev"
    ( cd "$h/noir" && "$NARGO" compile --package agg_agg > "$ROOT/$B/nargo_compile_$tag.log" 2>&1 ); echo "nargo compile --package agg_agg exit=$?"
    echo "## compiled vs committed program.json (circuit-defining fields)"
    python3 -I scripts/t09_compare_program.py "$h/fixtures/circuits/agg_agg/program.json" "$h/noir/target/agg_agg.json" | grep -v informational
    mkdir -p "$B/vk-$tag"; "$BB" write_vk --scheme ultra_honk -b "$h/fixtures/circuits/agg_agg/program.json" -o "$B/vk-$tag" -c "$CRS" > "$B/vk-$tag/log.txt" 2>&1; echo "bb write_vk exit=$?"
    cmp -s "$B/vk-$tag/vk" "$h/fixtures/circuits/agg_agg/key" && echo "write_vk output byte-identical to committed agg_agg key: YES" || echo "write_vk output byte-identical to committed agg_agg key: NO"
    echo "bb vk_hash (decimal): $(python3 -I -c 'import sys;print(int.from_bytes(open(sys.argv[1],"rb").read(),"big"))' "$B/vk-$tag/vk_hash")"
    echo "AGG_AGG_VERIFICATION_KEY_HASH constant in this revision's agg_final: $(git -C "$h" show "$rev:noir/agg_final/src/main.nr" | grep -o 'AGG_AGG_VERIFICATION_KEY_HASH: Field = [0-9]*' | grep -o '[0-9]*$')"
  } >> "$O" 2>&1
  { echo "## nargo test --package agg_agg at $tag"; ( cd "$h/noir" && "$NARGO" test --package agg_agg 2>&1 | sed 's/\x1b\[[0-9;]*m//g' ); } > "$L/21_noir_unit_tests_$tag.txt" 2>&1
done

# ---- 3. build the harness separately in each revision's checkout -------------------------------------------------------------------------------------
export RUSTFLAGS="--cfg tracing_unstable" CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"   # repo's .cargo/config.toml flag; local libc++ header workaround recorded in T10
# Revision A's committed Cargo.lock is not accepted by `--locked` (it carries ~430 unused entries and lacks the local path member `rustbridge`).
# Let cargo rewrite it once, then require that no third-party package changed version. The diff is saved as evidence.
if ! (cd "$HA" && cargo +1.91.0 metadata --locked --format-version 1 > /dev/null 2>&1); then
  ( cd "$HA" && cargo +1.91.0 metadata --format-version 1 > /dev/null 2> "$ROOT/$L/22_lock_regeneration.log" )
fi
git -C "$HA" diff --stat -- Cargo.lock | cat > "$L/22_lock_diffstat.txt"   # the only upstream file modified in any checkout (revision A); the check below shows the rewrite changes no package version
python3 -I - "$HA" "$REV_A" "$L" <<'PY' || die "revision A lock regeneration changed a package version (see $L/22_lock_check.txt)"
import re, subprocess, sys
h, rev, L = sys.argv[1:4]
pk = lambda t: {(m.group(1), m.group(2), m.group(3)) for m in re.finditer(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"(?:\nsource = "([^"]+)")?', t)}
old = pk(subprocess.run(["git", "-C", h, "show", f"{rev}:Cargo.lock"], capture_output=True, text=True).stdout); new = pk(open(f"{h}/Cargo.lock").read())
added, removed = sorted(new - old), len(old - new)
open(f"{L}/22_lock_check.txt", "w").write(f"packages in committed lock: {len(old)}; after cargo's rewrite: {len(new)}; removed (unused) entries: {removed}; entries present only after rewrite: {added}\n(only a local path package with no source may appear here)\n")
sys.exit(0 if all(s is None for _, _, s in added) else 1)
PY
build() { # tag rev checkout target
  local tag=$1 h=$3 tgt=$4
  mkdir -p "$h/pkg/zk-circuits/tests" "$ROOT/$B/ts-rs-$tag"; cp payy-harness/t15_tail.rs "$h/pkg/zk-circuits/tests/t15_tail.rs"   # NEW untracked file; no upstream file edited
  CARGO_TARGET_DIR="$ROOT/$tgt" TS_RS_EXPORT_DIR="$ROOT/$B/ts-rs-$tag" python3 scripts/t10_run_limited.py "$BUILD_TO" "$MAX_RSS" "$L/23_build_$tag.log" "$L/23_build_$tag.json" -- \
    cargo +1.91.0 test --locked --manifest-path "$h/Cargo.toml" -p zk-circuits --test t15_tail --no-run
}
step "build harness at A (cold on the first run)"; build c4d2c90 "$REV_A" "$HA" "$B/cargo-target-c4d2c90" > /dev/null || die "revision A harness did not build (see $L/23_build_c4d2c90.log)"
step "build harness at B"; build dcd5d96 "$REV_B" "$HB" build/T10/cargo-target > /dev/null || die "revision B harness did not build (see $L/23_build_dcd5d96.log)"

# ---- 4. run each revision's differential (pass-through bb recorder on PATH; it is not a mock) ----------------------------------------------------------
cp scripts/t10_bb_recorder.sh "$B/bin/bb"; chmod +x "$B/bin/bb"
run_rev() { # tag checkout target
  local tag=$1 h=$2 tgt=$3
  mkdir -p "$L/$tag"
  env RUST_MIN_STACK=536870912 T10_REAL_BB="$BB" T10_CAPTURE_DIR="$ROOT/$B/capture-$tag" T15_OUT_DIR="$ROOT/$L/$tag" PATH="$ROOT/$B/bin:$PATH" CARGO_TARGET_DIR="$ROOT/$tgt" TS_RS_EXPORT_DIR="$ROOT/$B/ts-rs-$tag" \
    python3 scripts/t10_run_limited.py "$RUN_TO" "$MAX_RSS" "$L/30_run_$tag.log" "$L/30_run_$tag.json" -- \
    cargo +1.91.0 test --locked --manifest-path "$h/Cargo.toml" -p zk-circuits --test t15_tail -- --nocapture
}
step "run revision A (c4d2c90)"; run_rev c4d2c90 "$HA" "$B/cargo-target-c4d2c90" > /dev/null; RC_A=$?
step "run revision B (dcd5d96)"; run_rev dcd5d96 "$HB" build/T10/cargo-target > /dev/null; RC_B=$?
python3 -I scripts/t15_summarize.py c4d2c90 "$REV_A" "$HA" "$B/capture-c4d2c90" "$L/c4d2c90" > "$L/40_summarize_c4d2c90.out" 2>&1
python3 -I scripts/t15_summarize.py dcd5d96 "$REV_B" "$HB" "$B/capture-dcd5d96" "$L/dcd5d96" > "$L/40_summarize_dcd5d96.out" 2>&1

# ---- 5. merged summary: every verdict field is derived from the raw outputs ----------------------------------------------------------------------------
for t in c4d2c90 dcd5d96; do sed 's/\x1b\[[0-9;]*m//g' "$L/30_run_$t.log" | awk '/^error: /{p=1} /^test t15/{p=0} p' > "$L/31_noir_diagnostic_$t.txt"; done   # ACVM assertion diagnostic printed by the upstream executor
python3 -I - "$L" "$RC_A" "$RC_B" <<'PY'
import json, os, re, sys
L, rcA, rcB = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
def rev(tag, side, rc):
    h = json.load(open(f"{L}/{tag}/harness.json")); s = json.load(open(f"{L}/{tag}/40_summary.json"))
    prov = open(f"{L}/20_provenance_{side}.txt").read()
    unit = re.sub(r"\x1b\[[0-9;]*m", "", open(f"{L}/21_noir_unit_tests_{side}.txt").read())
    run = json.load(open(f"{L}/30_run_{tag}.json")); diag = open(f"{L}/31_noir_diagnostic_{tag}.txt").read()
    out = {"harness_exit": rc, "run_elapsed_s": run["elapsed_s"], "run_peak_rss_gib": run["polled_peak_group_rss_gib"],
           "provenance": {"compiled_program_equals_committed": "CIRCUIT-DEFINING FIELDS IDENTICAL" in prov, "write_vk_equals_committed_key": "committed agg_agg key: YES" in prov,
                          "vk_hash_equals_agg_final_constant": len(set(re.findall(r"(?:decimal\): |this revision's agg_final: )(\d+)", prov))) == 1},
           "noir_unit_tests_last_line": re.findall(r"\[agg_agg\] .*", unit)[-1:],
           "active_message_count": h["active_message_count"], "candidate_tail_index": h["candidate_tail_index"],
           "all_bb_calls_exit_0": s["all_bb_calls_exit_0"], "agg_agg_prove_calls": s["agg_agg_prove_calls"]}
    for role in ("control", "candidate"):
        r = h[role]; e = s.get(role)
        out[role] = {"witness_satisfied_and_proof_generated": r["witness_satisfied_and_proof_generated"], "failure_stage": r["failure_stage"], "error": r["error"],
                     "harness_native_verify": r["native_verify_via_harness"], "secs": r["secs"]}
        if e:
            out[role].update({"independent_native_verify_exit": e["independent_native_verify"]["exit"], "proof_sha256": e["proof_sha256"], "public_inputs_sha256": e["public_inputs_sha256"],
                              "nonzero_message_words": [(w["index"]) for w in e["decoded"]["nonzero_message_words"]],
                              "tamper_control_exit": e.get("tamper_control_last_nonzero_word_flipped", {}).get("exit")})
    out["rejection_diagnostic"] = {"mentions_Message_is_not_zero": "Message is not zero" in diag,
        "lines_cited": sorted(set(re.findall(r"agg_agg/src/main\.nr:(\d+)", diag))), "text_file": f"{L}/31_noir_diagnostic_{tag}.txt"}
    return out
A, B = rev("c4d2c90", "A", rcA), rev("dcd5d96", "B", rcB)
def fields(path): d = open(path, "rb").read(); return [d[i:i + 32] for i in range(0, len(d), 32)]
diff_idx = {}
for tag in ("c4d2c90", "dcd5d96"):
    if os.path.exists(f"{L}/{tag}/candidate/public_inputs"):
        c, k = fields(f"{L}/{tag}/control/public_inputs"), fields(f"{L}/{tag}/candidate/public_inputs")
        diff_idx[tag] = [i - 5 for i in range(len(c)) if c[i] != k[i]]   # message-word index of every public input that differs
A["candidate_vs_control_public_input_differences_at_message_index"] = diff_idx.get("c4d2c90")
ctl_ok = lambda r: r["control"]["witness_satisfied_and_proof_generated"] and r["control"]["independent_native_verify_exit"] == 0
est = (ctl_ok(A) and ctl_ok(B) and A["candidate"]["witness_satisfied_and_proof_generated"] and A["candidate"]["independent_native_verify_exit"] == 0
       and not B["candidate"]["witness_satisfied_and_proof_generated"] and B["candidate"]["failure_stage"].startswith("witness generation")
       and B["rejection_diagnostic"]["mentions_Message_is_not_zero"] and A["candidate_vs_control_public_input_differences_at_message_index"] == list(range(4, 9)))
summary = {"A_c4d2c90": A, "B_dcd5d96": B, "differential_established_on_this_candidate": est,
           "meaning": "A: candidate witness satisfiable and its ordinary proof verifies under A's committed key. B: same candidate rejected at witness generation by the helper's assertion. Nothing here shows consumer effect, loss, or exploitability."}
json.dump(summary, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
for k, v in (("A c4d2c90", A), ("B dcd5d96", B)):
    print(k, "| control:", v["control"]["witness_satisfied_and_proof_generated"], "verify exit", v["control"].get("independent_native_verify_exit"),
          "| candidate satisfied:", v["candidate"]["witness_satisfied_and_proof_generated"], "verify exit", v["candidate"].get("independent_native_verify_exit"), "| stage:", v["candidate"]["failure_stage"])
print("differential established:", est)
PY
git -C "$HB" status --short > "$L/91_checkout_status_B.txt"; git -C "$HA" status --short > "$L/91_checkout_status_A.txt"
echo; echo "Candidate circuit property only: not advisory reproduction, not a financial-impact claim, not BindCheck detection."
[ "$RC_A" = 0 ] && [ "$RC_B" = 0 ]; exit $?
