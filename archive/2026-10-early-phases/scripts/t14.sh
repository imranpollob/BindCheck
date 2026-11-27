#!/usr/bin/env bash
# BindCheck T14: define and test the Payy mint proof-to-consumer obligation with the T13 proof and the T12/T13 local deployment.
# usage: bash scripts/t14.sh      (about a minute; NO proving: reuses the T13 mint proof and the T10 zero-message proof)
# Prerequisites: scripts/t09.sh .. t13.sh have run (checkout at the revision, pinned toolchains, cargo target cache, tools/oz-5.0.1, payy-consumer/src,
# results/raw/T10/agg_final_new, results/raw/T13/agg_final_mint and 40_proof_summary.json); forge.
# Local testbed only. Not a vulnerability claim, not advisory reproduction, not BindCheck functionality.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T14; H=tools/cases/payy-history; REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
mkdir -p "$L"; rm -f "$L"/1*.txt "$L"/2*.json "$L"/2*.log "$L"/5*.log "$L"/5*.txt "$L"/90_summary.json "$L"/hash_check.json; rm -rf "$L/observations"
[ "$(git -C "$H" rev-parse "$REV^{commit}" 2>/dev/null)" = "$REV" ] || die "payy checkout at $REV missing (scripts/t09.sh)"
[ -f results/raw/T13/agg_final_mint/proof ] && [ -f results/raw/T13/40_proof_summary.json ] && [ -f results/raw/T10/agg_final_new/proof ] || die "run scripts/t10.sh and scripts/t13.sh first"
[ -d tools/oz-5.0.1/contracts ] && [ -f payy-consumer/src/rollup3/RollupV1.sol ] && [ -f build/T12/bins/agg_final_HonkVerifier.bin ] || die "run scripts/t12.sh first"
{ echo "revision: $REV"; echo "bb: $(tools/bb-3.0.0-manual.20251030/bb --version)"; forge --version | head -1; echo "cargo: $(cargo +1.91.0 --version)"; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"; } > "$L/00_environment.txt"

# ---- 1. source trace (excerpts at the pinned revision; reading and interpretation are in reports/T14.md) ----------------------------------------
S() { git -C "$H" show "$REV:$1"; }
{
  echo "## circuit noir/utxo/src/main.nr: message layout, mint branch"
  S noir/utxo/src/main.nr | grep -n -E 'messages: pub \[Field; 5\]|let kind = messages\[0\]|let msg_note_kind|let msg_value|let msg_hash|let mint_hash|kind == 2|Mint output must match|Mint hash must match|Mint note kind must match|msg_value.assert_max_bit_size'
  echo; echo "## circuit ownership check (noir/common/src/note.nr): only INPUT notes with non-zero value; a mint's inputs are zero-value padding"
  S noir/common/src/note.nr | sed -n '/pub fn check_input_note_ownership/,/^}/p'
  S noir/utxo/src/main.nr | grep -n -E 'check_input_note_ownership\(input_notes'
  echo; echo "## Rust side: pkg/zk-primitives/src/utxo.rs messages() and mint_hash()"
  S pkg/zk-primitives/src/utxo.rs | sed -n '/UtxoKind::Mint => \[/,/\],/p' | head -8
  S pkg/zk-primitives/src/utxo.rs | grep -n -A2 'pub fn mint_hash'
  echo; echo "## agg_utxo / agg_agg: placement and compaction of the 4 mint words"
  S noir/agg_utxo/src/main.nr | grep -n -E 'is_mint|must match message|msg_note_kind = messages|messages_index \+= 4'
  S noir/agg_agg/src/main.nr | grep -n -E 'proof_message == 2|next_check \+= 4'
  echo; echo "## consumer rollup3/RollupV1.sol: every touch of mints[...], and any cancel/refund path"
  S eth/contracts/rollup3/RollupV1.sol | grep -n -E 'mints\[|function (cancel|refund|removeMint)|mapping\(bytes32 => Mint\)'
  echo "(no function named cancel/refund/removeMint above means none exists)"
  echo; echo "## consumer: registration (mint) and its restrictions"
  S eth/contracts/rollup3/RollupV1.sol | sed -n '/Anyone can call mint/,/emit MintAdded/p' | head -34
  echo; echo "## consumer: second registration path (signed authorization)"
  S eth/contracts/rollup3/RollupV1.sol | grep -n -E 'function mintWithAuthorization|MINT_WITH_AUTHORIZATION_TYPE_HASH|Invalid signer|receiveWithAuthorization'
  echo; echo "## consumer: settlement path order (verifyRollup) and mint matching (verifyMint)"
  S eth/contracts/rollup3/RollupV1.sol | sed -n '/function verifyRollup/,/emit RollupVerified/p'
  S eth/contracts/rollup3/RollupV1.sol | sed -n '/function verifyMint/,/return i + 4;/p'
  echo; echo "## comments that do not match the code"
  S eth/contracts/rollup3/RollupV1.sol | grep -n -E 'Mint hash is hash of commitments|mints are removed after the rollup validates them'
  echo "(code: the hash is Poseidon of the two output psi values; verifyMint sets spent = true and keeps the entry; nothing deletes it)"
} > "$L/10_obligation_trace.txt" 2>&1

# ---- 2. mint-hash derivation (Rust, no proving) --------------------------------------------------------------------------------------------------
export CARGO_TARGET_DIR="$ROOT/build/T10/cargo-target" RUSTFLAGS="--cfg tracing_unstable" TS_RS_EXPORT_DIR="$ROOT/build/T10/ts-rs"
export CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"
mkdir -p "$H/pkg/zk-circuits/tests"; cp payy-harness/t14_hash_check.rs "$H/pkg/zk-circuits/tests/t14_hash_check.rs"   # NEW untracked file; no upstream file edited
T14_PI_FILE="$ROOT/results/raw/T13/agg_final_mint/public_inputs" T14_OUT_DIR="$ROOT/$L" \
  python3 scripts/t10_run_limited.py 1800 7 "$L/20_hash_check.log" "$L/20_hash_check.json" -- \
  cargo +1.91.0 test --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --test t14_hash_check -- --nocapture > /dev/null || die "hash check did not run (see $L/20_hash_check.log)"

# ---- 3. the five cases + reference case + property self-check, on the real consumer and verifier --------------------------------------------------
FOUNDRY_PROFILE=payy-consumer forge test --match-path 'payy-consumer/test/MintObligation.t.sol' -vv > "$L/50_forge.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_forge.log" | grep -E '^\[(PASS|FAIL)|Suite result|Ran [0-9]+ tests?' | tee "$L/51_forge_results.txt"

# ---- 4. summary -----------------------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import glob, json, os, sys
L, rc = sys.argv[1], int(sys.argv[2])
obs = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/observations/*.json")}
hc = json.load(open(f"{L}/hash_check.json"))
out = {"forge_exit": rc,
       "mint_hash_derivation": {"equals_hash_of_psi_values": hc["equals_psi_hash"], "equals_hash_of_commitments": hc["equals_commitment_hash"]},
       "cases": {k: {"status": v["status"], "rejectingCheck": v["rejectingCheck"], "verifierReached": v["verifierReached"], "gas": v["gas"],
                     "propertyHolds": v["propertyHolds"], "propertyWhy": v["propertyWhy"], "pre": v["pre"], "post": v["post"]} for k, v in sorted(obs.items())}}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps({k: (v["status"], v["rejectingCheck"] or "-", "verifier" if v["verifierReached"] else "no-verifier", v["propertyHolds"]) for k, v in out["cases"].items()}, indent=1))
print("mint hash == hash(psi values):", hc["equals_psi_hash"], "| == hash(commitments):", hc["equals_commitment_hash"])
PY
echo; echo "Property tested on production behaviour; not a vulnerability claim, not advisory reproduction, no BindCheck functionality."
exit $RC
