#!/bin/sh
# Export the trimmed, tool-facing baseline of each B3 host from its pinned commit (git archive,
# never from a working checkout) into benchmarks/binding-mutants-v3/baselines/<host>/.
# Usage: CAND=results/raw/B3/candidates sh export-baselines.sh   (CAND holds clones of each repo)
# Refuses to overwrite an existing baseline directory. Network may be needed for lazy blobs.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
CAND="${CAND:-$ROOT/results/raw/B3/candidates}"
OUT="$HERE/baselines"; mkdir -p "$OUT"

export_host() { # host clone sha paths...
  h=$1; c=$2; sha=$3; shift 3
  [ -e "$OUT/$h" ] && { echo "exists: $OUT/$h (not overwritten)"; return 0; }
  [ "$(git -C "$CAND/$c" rev-parse HEAD)" = "$sha" ] || { echo "$c not at $sha" >&2; exit 2; }
  mkdir -p "$OUT/$h"
  git -C "$CAND/$c" archive --format=tar "$sha" -- "$@" | tar -x -C "$OUT/$h"
  echo "$h $sha $(find "$OUT/$h" -type f | wc -l) files"
}

# zkerc20: Circom/Groth16. circuits/verifier.sol is NOT in the repo; it is generated (see HOSTS.md)
# and copied in from results/raw/B3/hostbuild/zkerc20 with its recorded sha256.
export_host zkerc20 Zellic_zkerc20 ff7b1016390074d428c8d469df7f5d47f99a6628 \
  LICENSE package.json hardhat.config.js contracts \
  circuits/circuit.circom circuits/commitment.circom circuits/hashtwo.circom circuits/merkleroot.circom
if [ ! -e "$OUT/zkerc20/circuits/verifier.sol" ]; then
  V="$ROOT/results/raw/B3/hostbuild/zkerc20/verifier.sol"
  echo "e70c2a5c77de25b172b392de1d5a1d7ecee5fb3d2762169459fcf34813ebe073  $V" | sha256sum -c - >/dev/null
  cp "$V" "$OUT/zkerc20/circuits/verifier.sol"
fi
rm -rf "$OUT/zkerc20/contracts/test"   # host mocks/tests are not part of the tool-facing tree

# dark: Noir (nargo 1.0.0-beta.22) + bb UltraHonk verifiers (committed), DarkVault/DarkKeyRegistry.
export_host dark DarkWalletRH_dark-contracts 053ab0f7524658c74200d54bd26ad6cfc13469d4 \
  LICENSE-APACHE LICENSE-MIT contracts/src contracts/foundry.toml contracts/package.json contracts/package-lock.json \
  circuits/Nargo.toml circuits/lib circuits/register circuits/transfer circuits/withdraw circuits/disclose_range \
  circuits/verifiers

# davinci: Circom/Groth16 (snarkjs verifiers committed), CouncilManager.
export_host davinci vocdoni_davinci-dkg-council cf539b008a0e5b7a6e2cbb22ec82a851398b2f65 \
  LICENSE solidity/src solidity/foundry.toml \
  circuits/deal.circom circuits/partial.circom circuits/lib circuits/package.json circuits/release

# xchain: RISC Zero 3.0 + Steel guests (six routes), Connector + RiscZeroAdapter.
export_host xchain fiit-ba_A-Resumable-Zero-Knowledge-Cross 643cee89594a85e83e1956cf0571fd0fadbe36ea \
  LICENSE smart-contracts/src smart-contracts/foundry.toml smart-contracts/foundry.lock \
  zk-proofs/risc_zero/lock_event zk-proofs/risc_zero/mint_event zk-proofs/risc_zero/ack_event \
  zk-proofs/risc_zero/burn_event zk-proofs/risc_zero/non_accept_event zk-proofs/risc_zero/refund_claim_event
for r in lock_event mint_event ack_event burn_event non_accept_event refund_claim_event; do
  # host/ (off-chain prover) is kept: it is a Cargo workspace member, needed for `cargo check`.
  rm -rf "$OUT/xchain/zk-proofs/risc_zero/$r/scripts" "$OUT/xchain/zk-proofs/risc_zero/$r/README.md"
done

# kakushi: Noir (nargo 1.0.0-beta.22) + bb UltraHonk verifier (committed), KakushiPool only.
P=packages/contracts
export_host kakushi krishnacodes9_kakushi-monad da0684b9275eaaf147f2189f49cbeb65cc1fc22f \
  LICENSE $P/foundry.toml \
  $P/src/privacy/KakushiPool.sol $P/src/privacy/PoolZeros.sol $P/src/privacy/PrivateCallExecutor.sol \
  $P/src/privacy/KakushiPoolFactory.sol \
  $P/src/interfaces/IVerifier.sol $P/src/interfaces/IRootOracle.sol $P/src/interfaces/IERC20Min.sol \
  $P/src/lib/Errors.sol $P/src/lib/Poseidon2.sol $P/src/lib/ReentrancyGuard.sol $P/src/lib/SafeTransfer.sol \
  $P/src/verifiers/ShieldedWithdrawVerifier.sol \
  packages/zk/Nargo.toml packages/zk/TOOLCHAIN packages/zk/circuits/shielded_withdraw packages/zk/lib/kakushi_lib \
  packages/zk/circuits/payment_compliance packages/zk/circuits/payout_inclusion packages/zk/circuits/fee_math

# Noir sources carry their unit tests in-file (`mod tests` / `#[test]` after main). Tests are not
# part of the tool-facing tree (as for Solidity): truncate each .nr file at its first test line.
# Every test block was checked to be the file's tail (HOSTS.md). Idempotent.
for f in $(find "$OUT/dark" "$OUT/kakushi" -name '*.nr'); do
  n=$(grep -n -m1 -E '^(#\[test|mod tests|// -+ tests)' "$f" | cut -d: -f1 || true)
  [ -n "$n" ] && { head -n "$((n - 1))" "$f" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' > "$f.tmp" && mv "$f.tmp" "$f"; }
done
