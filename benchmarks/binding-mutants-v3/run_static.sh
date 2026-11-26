#!/bin/sh
# Run ONE static tool on ONE B3 target (resumable: skips when the .meta exists). One at a time, memory-capped.
# Usage: STATIC=results/raw/B3/static-1 sh run_static.sh TOOL ID[@part]
#   TOOL: slither mythril circomspect nargo ; ID: mutant/decoy id or CLEAN-<host>; @part selects a second target:
#   @verifier (dark withdraw Verifier.sol), @dealverifier (davinci DealVerifier, mythril), @adapter (xchain RiscZeroAdapter, mythril)
# Trees come from the build runs (TREES_MAP below); outputs: $STATIC/<tool>/<ID>.{json,log,meta}
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"; R="$ROOT/results/raw/B3"
STATIC="${STATIC:?}"; case "$STATIC" in /*) ;; *) STATIC="$PWD/$STATIC";; esac
TOOL=$1; TID=$2; ID=${TID%@*}; PART=""; [ "$TID" != "$ID" ] && PART=${TID#*@}
O="$STATIC/$TOOL"; mkdir -p "$O"; [ -e "$O/$TID.meta" ] && { echo "skip $TOOL $TID (done)"; exit 0; }
SVM="$HOME/.local/share/svm"; SL="${SLITHER:-$HOME/.pyenv/versions/3.12.12/bin/slither}"; MY="$R/mvenv/bin/myth"
CS="$ROOT/tools/circomspect-src/target/release/circomspect"; NG="$ROOT/tools/noir-1.0.0-beta.22/nargo"
# Diagnostic/post-hoc knobs (defaults reproduce the frozen static-1 run): MYV="-v 4", MYX="extra flags", MYTO=outer timeout
MYV="${MYV:-}"; MYX="${MYX:-}"; MYTO="${MYTO:-420}"
MEM="systemd-run --user --scope -q -p MemoryMax=8G"
case "$ID" in ZK-*|CLEAN-zkerc20) H=zkerc20;; DK-*|CLEAN-dark) H=dark;; DV-*|CLEAN-davinci) H=davinci;; XC-*|CLEAN-xchain) H=xchain;; KK-*|CLEAN-kakushi) H=kakushi;; esac
case "$ID" in
  CLEAN-kakushi) T="$R/run-0-clean-c/trees/$ID";; CLEAN-*) T="$R/run-0-clean-b/trees/$ID";;
  XC-S07) T="$R/run-1-xchain-s07/trees/$ID";; *) T="$R/run-1-$H/trees/$ID";;
esac
[ -d "$T" ] || { echo "no tree $T" >&2; exit 2; }
FILT="node_modules|lib/|test|mocks|script"
mj() { printf '%s' "$1" > "$O/$TID.solc.json"; }
start=$(date +%s)
case "$TOOL:$H:$PART" in
  slither:zkerc20:) (cd "$T" && $MEM "$SL" . --filter-paths "$FILT" --json "$O/$TID.json");;
  slither:dark:) (cd "$T/contracts" && $MEM "$SL" . --filter-paths "$FILT" --json "$O/$TID.json");;
  slither:dark:verifier) (cd "$T/circuits/verifiers/withdraw" && $MEM "$SL" Verifier.sol --solc "$SVM/0.8.30/solc-0.8.30" --solc-args "--optimize --optimize-runs 200 --evm-version cancun" --json "$O/$TID.json");;
  slither:davinci:) (cd "$T/solidity" && $MEM "$SL" . --filter-paths "$FILT" --json "$O/$TID.json");;
  slither:xchain:) (cd "$T/smart-contracts" && $MEM "$SL" . --filter-paths "$FILT|certora" --json "$O/$TID.json");;
  slither:kakushi:) (cd "$T/packages/contracts" && $MEM "$SL" src/privacy/KakushiPool.sol --solc "$SVM/0.8.28/solc-0.8.28" --solc-args "--optimize --optimize-runs 200 --evm-version cancun" --json "$O/$TID.json");;  # project-wide run crashes in the Honk verifier (constant folding)
  mythril:zkerc20:) mj '{"remappings":["@openzeppelin/=node_modules/@openzeppelin/","hardhat/=node_modules/hardhat/","@layerzerolabs/=node_modules/@layerzerolabs/"]}'
     (cd "$T" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.27 contracts/Node.sol:Node --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:dark:) mj '{"remappings":["@openzeppelin/=node_modules/@openzeppelin/"],"viaIR":true,"optimizer":{"enabled":true,"runs":1000},"evmVersion":"cancun"}'
     (cd "$T/contracts" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.28 src/DarkVault.sol:DarkVault --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:dark:verifier) mj '{"optimizer":{"enabled":true,"runs":200}}'   # evmVersion key rejected by solc 0.8.30 via mythril
     (cd "$T/circuits/verifiers/withdraw" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.30 Verifier.sol:HonkVerifier --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:davinci:) mj '{"viaIR":true,"optimizer":{"enabled":true,"runs":1},"evmVersion":"cancun"}'
     (cd "$T/solidity" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.28 src/CouncilManager.sol:CouncilManager --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:davinci:dealverifier) mj '{"viaIR":true,"optimizer":{"enabled":true,"runs":1},"evmVersion":"cancun"}'
     (cd "$T/solidity" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.28 src/verifiers/DealVerifier.sol:DealVerifier --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:xchain:|mythril:xchain:adapter)
     mj '{"remappings":["forge-std/=lib/forge-std/src/","risc0-ethereum/=lib/risc0-ethereum/contracts/src/","openzeppelin/contracts/=lib/risc0-ethereum/lib/openzeppelin-contracts/contracts/"],"viaIR":true,"optimizer":{"enabled":true,"runs":200},"evmVersion":"cancun"}'
     TGT=src/connectors/Connector.sol:Connector; [ "$PART" = adapter ] && TGT=src/zk-proof/adapters/RiscZeroAdapter.sol:RiscZeroAdapter
     (cd "$T/smart-contracts" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.34 "$TGT" --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  mythril:kakushi:) mj '{"optimizer":{"enabled":true,"runs":200},"evmVersion":"cancun"}'
     (cd "$T/packages/contracts" && SOLCX_BINARY_PATH="$R/solcx" timeout $MYTO $MEM "$MY" $MYV analyze --solv 0.8.28 src/privacy/KakushiPool.sol:KakushiPool --solc-json "$O/$TID.solc.json" --execution-timeout 300 --max-depth 22 --no-onchain-data $MYX -o json > "$O/$TID.json");;
  circomspect:zkerc20:) (cd "$T/circuits" && $MEM "$CS" circuit.circom);;
  circomspect:davinci:) (cd "$T/circuits" && $MEM "$CS" -L node_modules deal.circom partial.circom);;
  nargo:dark:) (cd "$T/circuits" && $MEM "$NG" check --workspace);;
  nargo:kakushi:) (cd "$T/packages/zk/circuits/shielded_withdraw" && $MEM "$NG" check);;
  *) echo "unsupported layer for $TOOL on $H ($PART)"; (exit 99);;
esac >"$O/$TID.log" 2>&1
EC=$?; end=$(date +%s)
echo "tool=$TOOL id=$TID exit=$EC seconds=$((end-start)) myv=${MYV:-none} myx=${MYX:-none} myto=$MYTO" > "$O/$TID.meta"; echo "$TOOL $TID exit=$EC $((end-start))s"
