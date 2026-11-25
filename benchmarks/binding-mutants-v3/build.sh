#!/bin/sh
# Build every B3 tree: 36 mutants, 5 decoys, 5 clean hosts. Compile-only per tree (honest paths: run_honest.sh).
# Usage: OUT=results/raw/B3/run-N sh benchmarks/binding-mutants-v3/build.sh   (OUT must not exist; nothing is deleted)
# Optional: ONLY="ZK-C01 CLEAN-zkerc20" to build a subset.
# Needs: fetch-deps.sh done; forge 1.4.1; solc in ~/.local/share/svm; nargo beta.22; circom 2.2.2 + tools/circom-src 2.2.3; cargo.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
OUT="${OUT:?set OUT to a fresh dir}"; case "$OUT" in /*) ;; *) OUT="$PWD/$OUT";; esac
DEPS="${DEPS:-$ROOT/results/raw/B3/deps}"; SVM="$HOME/.local/share/svm"
NARGO="${NARGO:-$ROOT/tools/noir-1.0.0-beta.22/nargo}"; CIRCOM223="$ROOT/tools/circom-src/target/release/circom"
CIRCOM="${CIRCOM:-$HOME/.cargo/bin/circom}"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/results/raw/B3/hostbuild/xchain-target}"
[ -e "$OUT" ] && { echo "OUT exists: $OUT" >&2; exit 2; }
mkdir -p "$OUT/logs"
python3 "$HERE/make_mutants.py" --out "$OUT/trees" || exit 1
for H in zkerc20 dark davinci xchain kakushi; do cp -r "$HERE/baselines/$H" "$OUT/trees/CLEAN-$H"; done
printf 'id\thost\tlayer\tstep\texit\n' > "$OUT/build-summary.tsv"
host_of() { case "$1" in ZK-*|CLEAN-zkerc20) echo zkerc20;; DK-*|CLEAN-dark) echo dark;; DV-*|CLEAN-davinci) echo davinci;;
  XC-*|CLEAN-xchain) echo xchain;; KK-*|CLEAN-kakushi) echo kakushi;; esac; }
step() { # id host layer name cmd...
  id=$1; h=$2; layer=$3; name=$4; shift 4
  ( "$@" ) >"$OUT/logs/$id-$name.log" 2>&1; ec=$?
  printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$h" "$layer" "$name" "$ec" >> "$OUT/build-summary.tsv"; echo "$id $name exit=$ec"
}
for T in "$OUT"/trees/*/; do
  ID=$(basename "$T"); H=$(host_of "$ID"); [ -n "$H" ] || continue
  if [ -n "${ONLY:-}" ]; then case " $ONLY " in *" $ID "*) ;; *) continue;; esac; fi
  case "$ID" in CLEAN-*) L=all;; *-C*|*-D*) L=c;; *-G*) L=g;; *) L=s;; esac   # decoys: build both layers
  case "$ID" in *-D0*) L=all;; esac
  case "$H" in
  zkerc20)
    ln -s "$DEPS/zkerc20-node/node_modules" "$T/node_modules"
    printf '[profile.default]\nsrc="contracts"\nout="out"\nlibs=["node_modules"]\nsolc="%s/0.8.27/solc-0.8.27"\nauto_detect_solc=false\nremappings=["@openzeppelin/=node_modules/@openzeppelin/","hardhat/=node_modules/hardhat/","@layerzerolabs/=node_modules/@layerzerolabs/"]\n' "$SVM" > "$T/foundry.toml"
    case "$L" in s|all) step "$ID" "$H" sol forge sh -c "cd '$T' && nice -n 10 forge build --offline";; esac
    case "$L" in c|all) mkdir -p "$T/build"; step "$ID" "$H" circuit circom sh -c "cd '$T/circuits' && nice -n 10 '$CIRCOM' circuit.circom --r1cs --sym -o ../build";; esac;;
  dark)
    ln -s "$DEPS/dark-node/node_modules" "$T/contracts/node_modules"
    case "$L" in s|all) step "$ID" "$H" sol forge sh -c "cd '$T/contracts' && nice -n 10 forge build --offline"
      mkdir -p "$T/build"; step "$ID" "$H" sol solc-verifiers sh -c "cd '$T/circuits/verifiers' && for v in register transfer withdraw; do '$SVM/0.8.30/solc-0.8.30' --optimize --optimize-runs 200 --evm-version cancun --bin --overwrite -o ../../build/\$v \$v/Verifier.sol || exit 1; done";; esac
    case "$L" in c|all) step "$ID" "$H" circuit nargo-check sh -c "cd '$T/circuits' && '$NARGO' check --workspace";; esac;;
  davinci)
    ln -s "$DEPS/davinci-node/node_modules" "$T/circuits/node_modules"
    case "$L" in s|all) step "$ID" "$H" sol forge sh -c "cd '$T/solidity' && nice -n 10 forge build --offline";; esac
    case "$L" in c|all) mkdir -p "$T/build"; step "$ID" "$H" circuit circom223 sh -c "cd '$T/circuits' && for c in deal partial; do nice -n 10 '$CIRCOM223' \$c.circom --O2 --r1cs --sym -l node_modules -o ../build || exit 1; done";; esac;;
  xchain)
    mkdir -p "$T/smart-contracts/lib"; ln -s "$DEPS/forge-std-v1.15.0" "$T/smart-contracts/lib/forge-std"; ln -s "$DEPS/risc0-ethereum-v3.0.1" "$T/smart-contracts/lib/risc0-ethereum"
    case "$L" in s|all) step "$ID" "$H" sol forge sh -c "cd '$T/smart-contracts' && nice -n 10 forge build --offline";; esac
    case "$L" in g|all) step "$ID" "$H" guest cargo-check-core sh -c "for r in lock_event mint_event ack_event burn_event non_accept_event refund_claim_event; do c=\$(sed -n 's/^name = \"\\(.*\\)\"/\\1/p' '$T/zk-proofs/risc_zero/'\$r/core/Cargo.toml | head -1); (cd '$T/zk-proofs/risc_zero/'\$r && nice -n 10 cargo check -q -p \$c) || exit 1; done";; esac;;
  kakushi)
    case "$L" in s|all) step "$ID" "$H" sol forge sh -c "cd '$T/packages/contracts' && nice -n 10 forge build --offline";; esac
    case "$L" in c|all) step "$ID" "$H" circuit nargo-check sh -c "cd '$T/packages/zk/circuits/shielded_withdraw' && '$NARGO' check";; esac;;
  esac
done
echo "summary: $OUT/build-summary.tsv"
