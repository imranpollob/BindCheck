#!/usr/bin/env bash
# BindCheck T12: (1) resolve Payy's two verifier hash values, (2) one zero-message settlement through the ACTUAL consumer
# (rollup3/RollupV1.sol behind a TransparentUpgradeableProxy) with the ACTUAL Honk verifier, plus controls.
# usage: bash scripts/t12.sh        (about a minute; no proving)
# Prerequisites (reused, never regenerated here): scripts/t09.sh and scripts/t10.sh have run (payy checkout at the revision, pinned bb,
# build/T09 CRS, results/raw/T10/agg_final_new/{proof,public_inputs}); forge; network on first run (npm tarballs, solc, crates cache).
# Not advisory reproduction and not a BindCheck detection result.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T12; H=tools/cases/payy-history; B=build/T12
REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36; BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
mkdir -p "$L" "$B/bins" payy-consumer/src/rollup3 payy-consumer/src/noir payy-consumer/test
rm -f "$L"/*.txt "$L"/*.json "$L"/*.log; rm -rf "$L/observations"
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }

# ---- 0. prerequisites -------------------------------------------------------------------------------------------------------------
[ -f results/raw/T10/agg_final_new/proof ] && [ -f results/raw/T10/90_summary.json ] || die "run scripts/t10.sh first"
[ -d "$H/.git" ] && [ "$(git -C "$H" rev-parse "$REV^{commit}")" = "$REV" ] || die "payy checkout at $REV missing (scripts/t09.sh)"
[ -x "$BB" ] || die "pinned bb missing (scripts/t09.sh)"
python3 -I - <<'PY' || die "T10 artifacts do not match results/raw/T10/90_summary.json"
import hashlib, json
s = json.load(open("results/raw/T10/90_summary.json"))["agg_final_proof"]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert h("results/raw/T10/agg_final_new/proof") == s["proof_sha256"] and h("results/raw/T10/agg_final_new/public_inputs") == s["public_inputs_sha256"]
PY
{ echo "revision: $REV"; forge --version | head -1; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"; } > "$L/00_environment.txt"

# ---- 1. the two hash values -----------------------------------------------------------------------------------------------------------
export CARGO_TARGET_DIR="$ROOT/build/T10/cargo-target" RUSTFLAGS="--cfg tracing_unstable" TS_RS_EXPORT_DIR="$ROOT/build/T10/ts-rs"
export CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"   # local toolchain workaround recorded in T10
python3 scripts/t10_run_limited.py 1800 7 "$L/10_build_vk_hash.log" "$L/10_build_vk_hash.json" -- \
  cargo +1.91.0 build --locked --manifest-path "$H/Cargo.toml" -p zk-circuits --bin vk_hash > /dev/null || die "could not build Payy's vk_hash binary (see $L/10_build_vk_hash.log)"
VKH="$CARGO_TARGET_DIR/debug/vk_hash"
{
  echo "## A. Payy's own generator binary (pkg/zk-circuits/src/bin/vk_hash.rs: Poseidon over all key_fields.json fields) vs the Rust/deploy constants"
  for r in c4d2c90 dcd5d96; do for c in agg_final agg_agg; do d="$B/kf-$r-$c"; mkdir -p "$d"; git -C "$H" cat-file -p "$r:fixtures/circuits/$c/key_fields.json" > "$d/key_fields.json"
    echo "[$r] $c vk_hash binary -> $("$VKH" "$d/key_fields.json" | grep '^hex:')"; done
    echo "[$r] pkg/contracts/src/rollup.rs AGG_FINAL_VERIFICATION_KEY_HASH = $(git -C "$H" show "$r:pkg/contracts/src/rollup.rs" | grep -A1 'pub const AGG_FINAL_VERIFICATION_KEY_HASH' | tr -d '\n ' | sed -E 's/.*"(0x[0-9a-f]+)".*/\1/')"
    echo "[$r] eth/scripts/deploy.ts          AGG_FINAL_VERIFICATION_KEY_HASH = $(git -C "$H" show "$r:eth/scripts/deploy.ts" | grep -A1 '^const AGG_FINAL_VERIFICATION_KEY_HASH' | tr -d '\n ' | sed -E 's/.*"(0x[0-9a-f]+)".*/\1/')"
  done
  echo; echo "## B. The Solidity VK_HASH and bb's own hash of the agg_final circuit under both oracle flavors (dcd5d96)"
  git -C "$H" cat-file -p "$REV:eth/noir/agg_final.sol" | grep -n 'uint256 constant VK_HASH'
  mkdir -p "$B/bbk" "$B/bbp"; git -C "$H" cat-file -p "$REV:fixtures/circuits/agg_final/program.json" > "$B/agg_final_program.json"
  "$BB" write_vk --scheme ultra_honk --oracle_hash keccak -b "$B/agg_final_program.json" -o "$B/bbk" -c build/T09/crs > /dev/null 2>&1
  "$BB" write_vk --scheme ultra_honk -b "$B/agg_final_program.json" -o "$B/bbp" -c build/T09/crs > /dev/null 2>&1
  echo "bb vk_hash, --oracle_hash keccak (the flavor the generator uses for agg_final) : 0x$(xxd -p -c 64 "$B/bbk/vk_hash")"
  echo "bb vk_hash, default flavor (poseidon2)                                         : 0x$(xxd -p -c 64 "$B/bbp/vk_hash")"
  echo "keccak-flavor vk bytes == committed key: $(cmp -s "$B/bbk/vk" <(git -C "$H" cat-file -p "$REV:fixtures/circuits/agg_final/key") && echo yes || echo no); flavors give identical vk bytes: $(cmp -s "$B/bbk/vk" "$B/bbp/vk" && echo yes || echo no)"
  echo; echo "## C. How the consumer uses a key hash (rollup3/RollupV1.sol @ $REV)"
  git -C "$H" show "$REV:eth/contracts/rollup3/RollupV1.sol" | grep -n -E 'mapping\(bytes32 => Verifier\) public zkVerifiers|function initialize|verifierKeyHash|function addZkVerifier|function removeZkVerifier|function addProver|function setRoot|function setValidators|public onlyOwner|function verifyRollup|bytes32 verificationKeyHash|zkVerifiers\[verificationKeyHash\]|\.verifier\.verify\(|modifier onlyProver' | cut -c1-150
  echo; echo "## D. Upstream registration (eth/scripts/deploy.ts): the registry key is the generator's constant, passed to initialize()"
  git -C "$H" show "$REV:eth/scripts/deploy.ts" | grep -n -E 'AGG_FINAL_VERIFICATION_KEY_HASH,|DEFAULT_VERIFIER_MESSAGES_COUNT,|linkAndDeployVerifier\(aggregateBinFile\)|TransparentUpgradeableProxy|functionName: "initialize"'
  echo; echo "## E. Generator wiring (noir/agg_final/Nargo.toml hash_updates write the vk_hash-binary value into deploy.ts and rollup.rs)"
  git -C "$H" show "$REV:noir/agg_final/Nargo.toml" | grep -n -E 'path =|name ='
} > "$L/11_hash_derivation.txt" 2>&1

# ---- 2. OpenZeppelin 5.0.1 (versions pinned by eth/package.json; integrity from eth/yarn.lock) ----------------------------------------------
mkdir -p tools/oz-5.0.1; ( cd tools/oz-5.0.1
  for pkg in contracts contracts-upgradeable; do [ -f "openzeppelin-$pkg-5.0.1.tgz" ] || npm pack "@openzeppelin/$pkg@5.0.1" --silent > /dev/null 2>&1; done
  want_c=$(git -C "$ROOT/$H" show "$REV:eth/yarn.lock" | grep -A3 -E '^"?@openzeppelin/contracts@' | grep integrity | awk '{print $2}')
  want_u=$(git -C "$ROOT/$H" show "$REV:eth/yarn.lock" | grep -A3 -E '^"?@openzeppelin/contracts-upgradeable@' | grep integrity | awk '{print $2}')
  got_c="sha512-$(openssl dgst -sha512 -binary openzeppelin-contracts-5.0.1.tgz | base64 | tr -d '\n')"; got_u="sha512-$(openssl dgst -sha512 -binary openzeppelin-contracts-upgradeable-5.0.1.tgz | base64 | tr -d '\n')"
  { echo "contracts          : $([ "$got_c" = "$want_c" ] && echo MATCHES yarn.lock || echo MISMATCH) ($got_c)"; echo "contracts-upgradeable: $([ "$got_u" = "$want_u" ] && echo MATCHES yarn.lock || echo MISMATCH) ($got_u)"; } > "$ROOT/$L/12_oz_integrity.txt"
  [ "$got_c" = "$want_c" ] && [ "$got_u" = "$want_u" ] || exit 1
  mkdir -p contracts upgradeable; tar -xzf openzeppelin-contracts-5.0.1.tgz -C contracts --strip-components=1; tar -xzf openzeppelin-contracts-upgradeable-5.0.1.tgz -C upgradeable --strip-components=1 ) || die "OpenZeppelin integrity check failed (see $L/12_oz_integrity.txt)"

# ---- 3. consumer sources and verifier binaries, exactly as committed -------------------------------------------------------------------------
git -C "$H" cat-file -p "$REV:eth/contracts/rollup3/RollupV1.sol" > payy-consumer/src/rollup3/RollupV1.sol
git -C "$H" cat-file -p "$REV:eth/contracts/IUSDC.sol" > payy-consumer/src/IUSDC.sol
git -C "$H" cat-file -p "$REV:eth/contracts/noir/IVerifier.sol" > payy-consumer/src/noir/IVerifier.sol
for f in agg_final_HonkVerifier.bin agg_final_HonkVerifier.linkrefs.json agg_final_ZKTranscriptLib.bin; do git -C "$H" cat-file -p "$REV:eth/contracts/noir/$f" > "$B/bins/$f"; done
shasum -a 256 payy-consumer/src/rollup3/RollupV1.sol payy-consumer/src/IUSDC.sol payy-consumer/src/noir/IVerifier.sol "$B"/bins/* > "$L/13_source_hashes.txt"

# ---- 4. tests ------------------------------------------------------------------------------------------------------------------------
FOUNDRY_PROFILE=payy-consumer forge test -vv > "$L/30_forge.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge.log" | grep -E '^\[(PASS|FAIL)|Suite result|Ran [0-9]+ tests?' | tee "$L/31_forge_results.txt"

# Evidence for the execution-EVM requirement: on a shanghai EVM the committed verifier (which contains MCOPY) cannot verify a VALID proof.
{ echo '$ FOUNDRY_PROFILE=payy-consumer forge test --evm-version shanghai --match-test test_settlement_zeroMessageProofThroughActualConsumer -vv   (expected FAIL)'
  FOUNDRY_PROFILE=payy-consumer forge test --evm-version shanghai --match-test test_settlement_zeroMessageProofThroughActualConsumer -vv 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E 'Error|\[PASS\]|\[FAIL|Suite result' | cut -c1-200; } > "$L/40_shanghai_evm_failure.log"

# ---- 5. summary ----------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import glob, json, os, sys
L, rc = sys.argv[1], int(sys.argv[2])
obs = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/observations/*.json")}
out = {"forge_exit": rc, "observations": {k: {"status": v["status"], "reason": v["reason"], "gasUsed": v["gasUsed"], "verifierCall": v["verifierCall"],
       "rootBefore": v["pre"]["rootHash"], "rootAfter": v["post"]["rootHash"], "heightBefore": v["pre"]["blockHeight"], "heightAfter": v["post"]["blockHeight"]} for k, v in sorted(obs.items())}}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
echo; echo "Not advisory reproduction; not a BindCheck detection result."
exit $RC
