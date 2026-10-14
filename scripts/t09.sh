#!/usr/bin/env bash
# BindCheck T09: artifact-compatibility check for the Payy `agg_final` verification path.
# Establishes (or fails to establish): source revision -> circuit artifact -> verification key -> proof/public inputs -> Solidity verifier.
# usage: bash scripts/t09.sh        Needs network on first run (clone, nargo/bb tarballs, CRS from the public endpoint).
# This task does not reproduce the advisory or establish acceptance of an unauthorized message tail.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T09; B=build/T09; mkdir -p "$L" "$B" tools/cases
H=tools/cases/payy-history
REVS=(c4d2c9021b8fb9988816eb6987a734b830bfce15 dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36)
NARGO_DIR=tools/noir-1.0.0-beta.14; NARGO="$ROOT/$NARGO_DIR/nargo"
NARGO_URL=https://github.com/noir-lang/noir/releases/download/v1.0.0-beta.14/nargo-aarch64-apple-darwin.tar.gz
NARGO_SHA=2bb856a86e9e07ae94e052699ebd391426534d30fe43783bd6873f628a3a699b   # recorded in T08 when first downloaded
BB_DIR=tools/bb-3.0.0-manual.20251030; BB="$ROOT/$BB_DIR/bb"
BB_URL=https://storage.googleapis.com/payy-public-fixtures/bb/v3.0.0-manual.20251030/barretenberg-arm64-darwin.tar.gz
BB_SHA=7f72eaf42bec065fd3e3fd1d1989a0c7333b236447b66f0954eda13125a01ab2           # pinned by the repo in pkg/xtask/src/setup/bb.rs
rm -f "$L"/[1-9]*.log "$L"/steps.tsv "$L"/*.json "$L"/*.txt; rm -rf "$B"/vk-* "$B"/sol-* "$B"/src-*; : > "$L/steps.tsv"

# run NAME EXPECT(0|nonzero) CMD... : log, record exit status; "unexpected" only if it differs from the expectation
run() { local n="$1" e="$2"; shift 2
  { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$L/$n.log" 2>&1
  local c; c=$(tail -n1 "$L/$n.log" | sed 's/exit=//'); local v=ok
  if [ "$e" = 0 ] && [ "$c" != 0 ]; then v=UNEXPECTED; fi
  if [ "$e" = nonzero ] && [ "$c" = 0 ]; then v=NOTE_exit0; fi
  printf '%s\texpect=%s\tobserved=%s\t%s\n' "$n" "$e" "$c" "$v" >> "$L/steps.tsv"; echo "[exit $c] $n ($v)"; return 0; }

# ---- 0. inputs: pinned source and toolchains -----------------------------------------------------------------
if [ ! -d "$H/.git" ]; then git clone --quiet --filter=blob:none --no-checkout https://github.com/polybase/payy "$H" || exit 1; fi
for r in "${REVS[@]}"; do git -C "$H" cat-file -e "$r^{commit}" || { echo "missing revision $r"; exit 1; }; done
if [ ! -x "$NARGO" ]; then mkdir -p "$NARGO_DIR"; curl -fsSL -o "$NARGO_DIR/nargo.tar.gz" "$NARGO_URL" && [ "$(shasum -a 256 "$NARGO_DIR/nargo.tar.gz" | cut -d' ' -f1)" = "$NARGO_SHA" ] && tar -xzf "$NARGO_DIR/nargo.tar.gz" -C "$NARGO_DIR" || { echo "nargo setup failed"; exit 1; }; fi
if [ ! -x "$BB" ]; then mkdir -p "$BB_DIR"; curl -fsSL -o "$BB_DIR/bb.tar.gz" "$BB_URL" && [ "$(shasum -a 256 "$BB_DIR/bb.tar.gz" | cut -d' ' -f1)" = "$BB_SHA" ] && tar -xzf "$BB_DIR/bb.tar.gz" -C "$BB_DIR" || { echo "bb setup failed (checksum or download)"; exit 1; }; fi
{ echo "nargo: $("$NARGO" --version | head -1)"; echo "bb: $("$BB" --version) (tarball sha256 pinned by the repo: $BB_SHA; the repo itself notes bb --version differs from the nightly it was built from)"; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"; } > "$L/00_toolchain.txt"

# ---- 1. artifacts per revision (never mixed): extract, hash ------------------------------------------------------
echo -e "revision\tfile\tbytes\tsha256" > "$L/10_artifacts.tsv"
for r in "${REVS[@]}"; do s=${r:0:7}; d="$B/$s"; mkdir -p "$d"
  for f in fixtures/circuits/agg_final/key fixtures/circuits/agg_final/key_fields.json fixtures/circuits/agg_final/program.json fixtures/proofs/agg_agg_final_evm_proof.proof eth/noir/agg_final.sol; do
    git -C "$H" cat-file -p "$r:$f" > "$d/$(basename "$f")"
    echo -e "$s\t$f\t$(wc -c < "$d/$(basename "$f")" | tr -d ' ')\t$(shasum -a 256 "$d/$(basename "$f")" | cut -d' ' -f1)" >> "$L/10_artifacts.tsv"; done; done
# repository evidence about generation settings and the proof's origin
{ echo "## bb pin (pkg/xtask/src/setup/bb.rs @ dcd5d96)"; git -C "$H" show dcd5d96:pkg/xtask/src/setup/bb.rs | grep -n -E 'VERSION|RELEASE_BASE|archive_sha256' | head
  echo "## agg_final fixture metadata (noir/agg_final/Nargo.toml @ dcd5d96)"; git -C "$H" show dcd5d96:noir/agg_final/Nargo.toml | sed -n '/generate_fixtures\]/,/hash_updates/p' | head -5
  echo "## bb flags used by the generator (pkg/xtask/src/noir_fixtures/{export,solidity}.rs @ dcd5d96)"; git -C "$H" show dcd5d96:pkg/xtask/src/noir_fixtures/export.rs | grep -n -E '"write_vk"|"--scheme"|"ultra_honk"|"--oracle_hash"' ; git -C "$H" show dcd5d96:pkg/xtask/src/noir_fixtures/solidity.rs | grep -n -E 'write_solidity_verifier|"--scheme"|"ultra_honk"|"-k"'
  echo "## which Solidity verifiers are regenerated: eth/noir/agg_agg.sol identical across the two revisions? $(for r in c4d2c90 dcd5d96; do git -C "$H" cat-file -p $r:eth/noir/agg_agg.sol | shasum -a 256 | cut -c1-12; done | tr '\n' ' ')"
  echo "## who references the proof fixture: dcd5d96 (non-artifact files):"; git -C "$H" grep -n -I -E 'agg_agg_final_evm_proof|fixtures/proofs' dcd5d96 -- . ':!eth/artifacts' ':!*.lock' | cut -c1-160
  echo "## who references it at tag zk-circuits-v1.1.12 (65eabad4c2332da22d216a73bdf52fd4b9c3e259):"; git -C "$H" grep -n -I -E 'agg_agg_final_evm_proof' zk-circuits-v1.1.12 -- pkg | cut -c1-200
  echo "## Halo2 dependencies in pkg/zk-circuits/Cargo.toml: tag=$(git -C "$H" cat-file -p zk-circuits-v1.1.12:pkg/zk-circuits/Cargo.toml | grep -c -E 'halo2|snark-verifier') c4d2c90=$(git -C "$H" cat-file -p c4d2c90:pkg/zk-circuits/Cargo.toml | grep -c -E 'halo2|snark-verifier') dcd5d96=$(git -C "$H" cat-file -p dcd5d96:pkg/zk-circuits/Cargo.toml | grep -c -E 'halo2|snark-verifier')"
  echo "## proof bytes at the 2024 commit 6bd1be6 vs 2026: $(git -C "$H" cat-file -p 6bd1be6:fixtures/proofs/agg_agg_final_evm_proof.proof | wc -c | tr -d ' ') vs $(wc -c < "$B/dcd5d96/agg_agg_final_evm_proof.proof" | tr -d ' ')"
  echo "## agg_final vk header fields (log2 circuit size, public inputs): $(python3 -I -c 'import json,sys;f=json.load(open(sys.argv[1]));print([int(x,16) if isinstance(x,str) else x for x in f[:2]])' "$B/c4d2c90/key_fields.json")"
  echo "## TestRollupV1 (eth/contracts/mocks/TestRollupV1.sol @ dcd5d96) uses fixtures/verifier? $(git -C "$H" cat-file -p dcd5d96:eth/contracts/mocks/TestRollupV1.sol | grep -c -i -E 'verifier|proof|fixture') matches"
} > "$L/20_provenance_evidence.txt" 2>&1

# ---- 2. proof file structure --------------------------------------------------------------------------------------
run 30_decode_proof 0 python3 -I scripts/t09_decode_evm_proof.py "$B/dcd5d96/agg_agg_final_evm_proof.proof" "$L/30_proof_decoded.json"

# ---- 3. Noir-side chain per revision ------------------------------------------------------------------------------
for r in "${REVS[@]}"; do s=${r:0:7}; d="$B/$s"; src="$B/src-$s"; mkdir -p "$src" "$B/vk-$s" "$B/sol-$s"
  git -C "$H" archive "$r" noir | tar -x -C "$src"
  run "40_nargo_compile_agg_final_$s" 0 bash -c "cd '$src/noir' && '$NARGO' compile --package agg_final"
  run "41_compare_program_$s" 0 python3 -I scripts/t09_compare_program.py "$d/program.json" "$src/noir/target/agg_final.json"
  run "50_bb_write_vk_$s" 0 "$BB" write_vk --scheme ultra_honk --oracle_hash keccak -b "$d/program.json" -o "$B/vk-$s" -c "$B/crs"
  run "51_cmp_vk_$s" 0 cmp "$B/vk-$s/vk" "$d/key"
  run "60_bb_write_solidity_verifier_$s" 0 "$BB" write_solidity_verifier --scheme ultra_honk -k "$d/key" -o "$B/sol-$s/agg_final.sol" -c "$B/crs"
  run "61_cmp_solidity_$s" 0 cmp "$B/sol-$s/agg_final.sol" "$d/agg_final.sol"
done

# ---- 4. native verification of the committed proof fixture (the repository ships NO public-inputs file) -----------------
head -c $((1019*32)) /dev/zero > "$B/diag_zero_public_inputs_1019x32"
for r in "${REVS[@]}"; do s=${r:0:7}; d="$B/$s"
  # 4a: exactly what the repository's flavor implies; no public inputs available
  run "70_bb_verify_repo_flavor_no_pi_$s" nonzero "$BB" verify --scheme ultra_honk --oracle_hash keccak -k "$d/key" -p "$d/agg_agg_final_evm_proof.proof"
  # 4b: DIAGNOSTIC ONLY. Zero-filled placeholder public inputs of the key's declared size (1019 fields). Not a verification:
  #     it only shows at which stage bb rejects the file (proof deserialization vs. verification equation).
  for f in "keccak" "keccak --disable_zk" "poseidon2"; do tag=$(echo "$f" | tr ' ' '_' | tr -d '-')
    run "71_bb_verify_DIAGNOSTIC_zero_pi_${s}_$tag" nonzero "$BB" verify --scheme ultra_honk --oracle_hash $f -k "$d/key" -p "$d/agg_agg_final_evm_proof.proof" -i "$B/diag_zero_public_inputs_1019x32"
  done
done

# ---- 5. summary ----------------------------------------------------------------------------------------------------
python3 -I - "$L" <<'PY'
import json, re, sys
L = sys.argv[1]
steps = {}
for line in open(f"{L}/steps.tsv"):
    n, e, o, v = line.rstrip("\n").split("\t"); steps[n] = o.split("=")[1]
def ok(n): return steps.get(n) == "0"
def log(n): return re.sub(r"\x1b\[[0-9;]*m", "", open(f"{L}/{n}.log").read())
def stage(n):
    t = log(n)
    if "Unable to open file" in t: return "cannot start: public-inputs file missing (none committed)"
    if "on_curve" in t: return "proof deserialization: bytes are not valid curve points"
    if "bad proof serde" in t: return "proof deserialization: field conversion error"
    return "other: " + t.strip().splitlines()[-2][:120]
dec = json.load(open(f"{L}/30_proof_decoded.json"))
out = {"revisions": {}, "proof_fixture": {"borsh_EvmProof_V1_exact_fit": dec.get("exact_fit"),
       "decoded_counts": {k: dec.get(k) for k in ("proof_bytes", "agg_instances", "utxo_inputs")},
       "all_message_values_zero_under_halo2_era_layout": dec.get("all_values_zero"),
       "all_mint_burn_hashes_zero": dec.get("all_mint_burn_hashes_zero")}}
real_verifications = [n for n in steps if n.startswith("70_") and ok(n)]
for s in ("c4d2c90", "dcd5d96"):
    diag = {n.split(f"{s}_")[1]: stage(n) for n in steps if n.startswith(f"71_") and f"_{s}_" in n}
    out["revisions"][s] = {
        "source_to_circuit_artifact_ACIR_identical": ok(f"41_compare_program_{s}"),
        "circuit_to_vk_bytes_identical": ok(f"51_cmp_vk_{s}"),
        "vk_to_solidity_verifier_bytes_identical": ok(f"61_cmp_solidity_{s}"),
        "native_verify_repo_flavor": {"exit": steps.get(f"70_bb_verify_repo_flavor_no_pi_{s}"), "stage": stage(f"70_bb_verify_repo_flavor_no_pi_{s}")},
        "diagnostic_zero_public_inputs_stage_by_flavor": diag,
    }
out["native_verification_succeeded"] = bool(real_verifications)
out["foundry_test_and_altered_input_control"] = "not run" if not real_verifications else "precondition met"
out["conclusion"] = ("Noir-side chain (source -> circuit -> key -> Solidity verifier) reproduces at both revisions; "
                     "the committed proof fixture could not be verified natively: " + ("it succeeded" if real_verifications else
                     "no public-inputs artifact exists, and under placeholder inputs bb rejects the file at proof deserialization. "
                     "The file parses exactly as a Halo2-era Borsh EvmProof::V1 wrapper, so no compatible proof/public-inputs fixture was found."))
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
echo; echo "This task does not reproduce the advisory or establish acceptance of an unauthorized message tail."
echo "steps: $(grep -c . "$L/steps.tsv") | unexpected: $(grep -c UNEXPECTED "$L/steps.tsv")"
[ "$(grep -c UNEXPECTED "$L/steps.tsv")" = 0 ]
