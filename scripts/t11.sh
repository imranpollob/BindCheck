#!/usr/bin/env bash
# BindCheck T11: verify the T10 Payy agg_final proof with the matching REAL generated Solidity verifier in Foundry.
# usage: bash scripts/t11.sh        (runs in seconds; no proof generation)
# Prerequisites (reused, never regenerated here):
#   - scripts/t10.sh has run: results/raw/T10/agg_final_new/{proof,public_inputs} and results/raw/T10/90_summary.json
#   - scripts/t09.sh has run: tools/cases/payy-history checkout (revision below), pinned bb, build/T09/vk-dcd5d96/vk_hash
#   - Foundry (forge) available; solc 0.8.29 is fetched by forge on first use
# This demonstrates local Solidity verification of a ZERO-MESSAGE proof. It is not consumer settlement, effectful-message
# generation, advisory reproduction or BindCheck detection.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T11; H=tools/cases/payy-history; T10=results/raw/T10/agg_final_new
REV=dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36; BB="$ROOT/tools/bb-3.0.0-manual.20251030/bb"
VERIFIER_SHA=c749ed63e283b066cd2f54baffb80f7febae062c8d4579ff8bf492f1873ebc1a   # eth/noir/agg_final.sol @ REV (T09 table)
mkdir -p "$L" build/T11 payy/src payy/test; rm -f "$L"/*.log "$L"/*.txt "$L"/*.tsv "$L"/*.json
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }

# ---- 0. prerequisites ----------------------------------------------------------------------------------------------------
[ -f "$T10/proof" ] && [ -f "$T10/public_inputs" ] && [ -f results/raw/T10/90_summary.json ] || die "run scripts/t10.sh first (T10 artifacts missing)"
[ -d "$H/.git" ] && git -C "$H" cat-file -e "$REV^{commit}" || die "payy checkout at $REV missing; run scripts/t09.sh"
python3 -I - <<'PY' || die "T10 artifacts do not match the hashes recorded in results/raw/T10/90_summary.json"
import hashlib, json
s = json.load(open("results/raw/T10/90_summary.json"))["agg_final_proof"]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
assert h("results/raw/T10/agg_final_new/proof") == s["proof_sha256"], "proof"
assert h("results/raw/T10/agg_final_new/public_inputs") == s["public_inputs_sha256"], "public_inputs"
print("T10 artifacts match recorded hashes:", s["proof_sha256"][:16], s["public_inputs_sha256"][:16])
PY
forge --version | head -1 > "$L/00_environment.txt"
{ echo "revision: $REV"; echo "profile payy: $(sed -n '/\[profile.payy\]/,$p' foundry.toml | grep -E '^(solc_version|evm_version|optimizer|revert_strings)' | tr '\n' ' ') | effective evm_version: $(FOUNDRY_PROFILE=payy forge config 2>/dev/null | grep -E '^evm_version')"; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"; } >> "$L/00_environment.txt"

# ---- 1. the matching generated verifier (exact bytes from the pinned revision) --------------------------------------------------
git -C "$H" cat-file -p "$REV:eth/noir/agg_final.sol" > payy/src/AggFinalHonkVerifier.sol
[ "$(shasum -a 256 payy/src/AggFinalHonkVerifier.sol | cut -d' ' -f1)" = "$VERIFIER_SHA" ] || die "verifier source hash differs from the T09-recorded $VERIFIER_SHA"

# ---- 2. interface evidence (source locations; nothing is run against the proof here) ---------------------------------------------
V=payy/src/AggFinalHonkVerifier.sol
{
  echo "## generated verifier $V (sha256 $VERIFIER_SHA)"
  grep -n -E 'uint256 constant (N|LOG_N|NUMBER_OF_PUBLIC_INPUTS|VK_HASH|PAIRING_POINTS_SIZE|NUMBER_OF_ENTITIES|ZK_BATCHED_RELATION_PARTIAL_LENGTH|CONST_PROOF_SIZE_LOG_N)\b|function verify\(|if \(proof.length != expectedProofSize|publicInputs.length != vk.publicInputsSize|function calculateProofSize|function loadProof|// Pairing point object|round0\[1 \+ publicInputsSize - PAIRING_POINTS_SIZE|computePublicInputDelta\(|generateRecursionSeparator\(|convertPairingPointsToG1\(proof.pairingPointObject|contract HonkVerifier' "$V" | cut -c1-190
  echo; echo "## proof-size formula (source lines of calculateProofSize) vs the T10 file"
  python3 -I - "$V" "$T10/proof" "$T10/public_inputs" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
c = lambda n: int(re.search(rf"uint256 constant {n} = (\d+);", src).group(1))
logn, ent, rel, pair, pis_total = c("LOG_N"), c("NUMBER_OF_ENTITIES"), c("ZK_BATCHED_RELATION_PARTIAL_LENGTH"), c("PAIRING_POINTS_SIZE"), c("NUMBER_OF_PUBLIC_INPUTS")
# transcription of calculateProofSize(logN)
size = 8 * 2 + 2 * 4 + logn * rel + ent + 3 + logn + 4 + (logn - 1) * 2 + 2 * 2 + pair
proof = open(sys.argv[2], "rb").read(); pi = open(sys.argv[3], "rb").read()
print(f"LOG_N={logn} ENTITIES={ent} ZK_BATCHED_RELATION_PARTIAL_LENGTH={rel} PAIRING_POINTS_SIZE={pair} NUMBER_OF_PUBLIC_INPUTS(key header)={pis_total}")
print(f"expected proof fields = {size} -> {size*32} bytes; T10 proof file = {len(proof)} bytes ({len(proof)/32} fields): {'MATCH' if size*32 == len(proof) else 'MISMATCH'}")
print(f"expected publicInputs array length = NUMBER_OF_PUBLIC_INPUTS - PAIRING_POINTS_SIZE = {pis_total - pair}; T10 public_inputs file = {len(pi)//32} fields: {'MATCH' if pis_total - pair == len(pi)//32 and len(pi)%32==0 else 'MISMATCH'}")
first16 = [proof[i*32:(i+1)*32] for i in range(pair)]
print(f"first {pair} proof fields (read by loadProof as the pairing-point object): nonzero count = {sum(1 for f in first16 if int.from_bytes(f,'big'))}; as 32-byte big-endian words, e.g. field0 = 0x{first16[0].hex()}")
PY
  echo; echo "## VK hash agreement: verifier constant vs bb vk_hash of the committed agg_final key vs Payy's Rust constant"
  echo "verifier VK_HASH      : $(grep -E 'uint256 constant VK_HASH' "$V" | sed -E 's/.*= (0x[0-9a-f]+);/\1/')"
  echo "bb vk_hash (T09 run)  : 0x$(xxd -p -c 64 build/T09/vk-dcd5d96/vk_hash 2>/dev/null | tr -d '\n')"
  for r in c4d2c90 dcd5d96; do
    echo "[$r] rollup.rs AGG_FINAL_VERIFICATION_KEY_HASH: $(git -C "$H" show "$r:pkg/contracts/src/rollup.rs" | grep -A1 'pub const AGG_FINAL_VERIFICATION_KEY_HASH' | tr -d '\n ' | sed -E 's/.*"(0x[0-9a-f]+)".*/\1/')   bb vk_hash of that revision's agg_final key: 0x$(xxd -p -c 64 build/T09/vk-$r/vk_hash 2>/dev/null | tr -d '\n')"
  done
  echo "NOTE: Payy's Rust/registry constant differs from the verifier's VK_HASH at both revisions: two different hash values exist for agg_final."
  echo "      How the Rust one is derived is not determined here (generator runs its own vk_hash binary on key_fields.json). Irrelevant to verifier.verify(); relevant to the consumer's verificationKeyHash registry."
  echo; echo "## upstream serialization (pinned Rust @ $REV)"
  echo "-- proof.rs: raw bb output = public inputs (FIELD_COUNT x 32 bytes) followed by the proof"; git -C "$H" show "$REV:pkg/zk-circuits/src/circuits/proof.rs" | grep -n -E 'public_inputs_len =|raw_proof\[\.\.public_inputs_len\]|raw_proof\[public_inputs_len\.\.\]'
  echo "-- agg_final.rs: kzg is empty in the Honk-era conversion"; git -C "$H" show "$REV:pkg/zk-circuits/src/circuits/agg_final.rs" | grep -n 'kzg:'
  echo "-- zk-primitives agg_final.rs: public inputs are big-endian old_root, new_root, commit_hash, messages"; git -C "$H" show "$REV:pkg/zk-primitives/src/agg_final.rs" | grep -n -E 'to_be_bytes|fn to_bytes'
  echo "-- contracts/rollup.rs: call arguments (proof bytes, then [old_root,new_root,commit_hash,messages..,kzg..] as bytes32)"; git -C "$H" show "$REV:pkg/contracts/src/rollup.rs" | grep -n -E 'public_inputs.extend|public_inputs = vec|web3::types::Bytes::from\(proof\)|"verifyRollup"'
  echo "-- consumer (rollup3/RollupV1.sol): length check and verifier call"; git -C "$H" show "$REV:eth/contracts/rollup3/RollupV1.sol" | grep -n -E 'messages_length \+ 3|\.verifier\.verify\('
} > "$L/10_interface_evidence.txt" 2>&1

# ---- 3. reconciliation data: what is / is not equal across the two revisions ---------------------------------------------------
{
  echo -e "artifact\tc4d2c90_sha256_16\tdcd5d96_sha256_16\tequal"
  for f in fixtures/circuits/agg_final/key eth/noir/agg_final.sol fixtures/circuits/agg_agg/key eth/noir/agg_agg.sol fixtures/circuits/agg_utxo/key fixtures/circuits/utxo/key fixtures/proofs/agg_agg_final_evm_proof.proof; do
    a=$(git -C "$H" cat-file -p "c4d2c90:$f" | shasum -a 256 | cut -c1-16); b=$(git -C "$H" cat-file -p "dcd5d96:$f" | shasum -a 256 | cut -c1-16)
    echo -e "$f\t$a\t$b\t$([ "$a" = "$b" ] && echo yes || echo NO)"; done
} > "$L/20_cross_revision_equality.tsv"
# DIAGNOSTIC ONLY: repeat the T09 placeholder check with the CORRECT public-input size (1003 x 32 bytes, not 1019 x 32).
# It is not a verification; it shows that the failure stage (proof deserialization) does not depend on the placeholder's size.
mkdir -p build/T11; head -c $((1003*32)) /dev/zero > build/T11/diag_zero_public_inputs_1003x32
for r in c4d2c90 dcd5d96; do
  { echo "\$ bb verify --scheme ultra_honk --oracle_hash keccak -k <agg_final key @ $r> -p <committed halo2-era .proof> -i <1003x32 zero placeholder>   (DIAGNOSTIC)"
    git -C "$H" cat-file -p "$r:fixtures/circuits/agg_final/key" > "build/T11/key_$r"; git -C "$H" cat-file -p "$r:fixtures/proofs/agg_agg_final_evm_proof.proof" > "build/T11/oldproof_$r"
    "$BB" verify --scheme ultra_honk --oracle_hash keccak -k "build/T11/key_$r" -p "build/T11/oldproof_$r" -i build/T11/diag_zero_public_inputs_1003x32 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200; echo "exit=${PIPESTATUS[0]}"; } > "$L/21_diag_old_proof_1003_placeholder_$r.log" 2>&1
done

# ---- 4. Foundry tests (real verifier, explicit gas cap, repo's compiler settings) ---------------------------------------------------
FOUNDRY_PROFILE=payy forge test -vv > "$L/30_forge_payy.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/30_forge_payy.log" | grep -E '^\[(PASS|FAIL)|POSITIVE|NEGATIVE|verifier runtime|->|Suite result|Ran [0-9]+ tests?' | tee "$L/31_forge_results.txt"
FOUNDRY_PROFILE=payy forge build --sizes 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E '^\| (HonkVerifier|ZKTranscriptLib|Contract)' > "$L/32_contract_sizes.txt"; cat "$L/32_contract_sizes.txt"
# Strongest "matching verifier" evidence: the bytecode compiled here equals Payy's committed deployable artifact.
git -C "$H" cat-file -p "$REV:eth/contracts/noir/agg_final_HonkVerifier.bin" > build/T11/upstream_HonkVerifier.bin
git -C "$H" cat-file -p "$REV:eth/contracts/noir/agg_final_HonkVerifier.linkrefs.json" > build/T11/upstream_linkrefs.json
python3 -I scripts/t11_compare_bytecode.py build/T11/upstream_HonkVerifier.bin build/T11/upstream_linkrefs.json out-payy/AggFinalHonkVerifier.sol/HonkVerifier.json | tee "$L/33_bytecode_vs_upstream.txt"
BC=${PIPESTATUS[0]}

# ---- 5. summary -----------------------------------------------------------------------------------------------------------------------
python3 -I - "$L" "$RC" <<'PY'
import json, re, sys
L, rc = sys.argv[1], int(sys.argv[2])
t = re.sub(r"\x1b\[[0-9;]*m", "", open(f"{L}/30_forge_payy.log").read())
g = lambda p: (re.search(p, t) or [None, None])[1]
out = {"forge_exit": rc, "tests": {"passed": len(re.findall(r"\[PASS\]", t)), "failed": len(re.findall(r"\[FAIL", t))},
       "positive": {"returned": g(r"POSITIVE verify\(\) returned: (\w+)"), "gas_used": g(r"POSITIVE gas used[^:]*: (\d+)")},
       "negative": {"outcome": "reverted" if "NEGATIVE verify() REVERTED" in t else ("returned false" if "NEGATIVE verify() returned" in t else "unknown"),
                    "error": g(r"NEGATIVE verify\(\) REVERTED, error: (\S+)"), "gas_used": g(r"NEGATIVE gas used: (\d+)")},
       "verifier_runtime_code_bytes": g(r"verifier runtime code bytes: (\d+)"), "gas_cap_per_call": 30000000,
       "interface_checks": re.findall(r"^\s+(.*->.*)$", t, re.M),
       "overrides": f"none (no code-size-limit or other override; HonkVerifier runtime {g(r'verifier runtime code bytes: (\d+)')} B < 24,576 B)", "bytecode_identical_to_upstream_bin": ("IDENTICAL" in open(f"{L}/33_bytecode_vs_upstream.txt").read().replace("IDENTICAL (excluding","IDENTICAL (excluding") and "True" in open(f"{L}/33_bytecode_vs_upstream.txt").read())}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
echo; echo "This demonstrates local Solidity verification of a zero-message proof; not consumer settlement, not advisory reproduction, not BindCheck detection."
[ "${BC:-1}" = 0 ] || RC=1
exit $RC
