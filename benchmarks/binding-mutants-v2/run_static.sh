#!/bin/sh
# Run one static tool on one tree of a B2 build. Usage: run_static.sh TOOL TREE_ID   (env RUN=abs path of build run dir, VENV dirs)
# TOOL in: slither mythril circomspect picus nargo. Output under $RUN/static/<tool>/<TREE_ID>.{json,log,meta}
set -u
RUN="${RUN:?}"; TOOL="$1"; ID="$2"
SCR="${SCR:?scratch dir with venv/ (slither) and mvenv/ (mythril)}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SOLC="$HOME/.solc-select/artifacts"
T="$RUN/trees/$ID"; O="$RUN/static/$TOOL"; mkdir -p "$O"
case "$ID" in RP-*|CLEAN-redpacket) H=redpacket;; PV-*|CLEAN-privacyvaults) H=privacyvaults;; OR-*|CLEAN-orc) H=orc;; esac
start=$(date +%s)
case "$TOOL:$H" in
  slither:redpacket) (cd "$T" && "$SCR/venv/bin/slither" contracts/RedPacket.sol --filter-paths "lib|test" --json "$O/$ID.json") >"$O/$ID.log" 2>&1; EC=$?;;
  slither:privacyvaults) (cd "$T/contracts" && "$SCR/venv/bin/slither" src/PrivacyVault.sol --filter-paths "lib|test" --json "$O/$ID.json") >"$O/$ID.log" 2>&1; EC=$?;;
  slither:orc) (cd "$T" && "$SCR/venv/bin/slither" src/OrcClaim.sol --filter-paths "lib|test" --json "$O/$ID.json") >"$O/$ID.log" 2>&1; EC=$?;;
  mythril:redpacket) echo '{"remappings":["@openzeppelin/contracts/=lib/oz/contracts/"]}' > "$O/$ID.remap.json"
     (cd "$T" && SOLC="$SOLC/solc-0.8.17/solc-0.8.17" timeout 420 "$SCR/mvenv/bin/myth" analyze contracts/RedPacket.sol:RedPacket --solc-json "$O/$ID.remap.json" --execution-timeout 300 --max-depth 22 --no-onchain-data -o json) >"$O/$ID.json" 2>"$O/$ID.log"; EC=$?;;
  mythril:privacyvaults) echo '{"remappings":["@openzeppelin/contracts=lib/openzeppelin-contracts/contracts","@poseidon/=lib/poseidon2-evm/","forge-std/=lib/forge-std/src/"]}' > "$O/$ID.remap.json"
     (cd "$T/contracts" && SOLCX_BINARY_PATH="$SCR/solcx" timeout 420 "$SCR/mvenv/bin/myth" analyze src/PrivacyVault.sol:PrivacyVault --solv 0.8.28 --solc-json "$O/$ID.remap.json" --execution-timeout 300 --max-depth 22 --no-onchain-data -o json) >"$O/$ID.json" 2>"$O/$ID.log"; EC=$?;;
  mythril:orc) echo '{"remappings":["forge-std/=lib/forge-std/src/","@sp1-contracts/=lib/sp1-contracts/contracts/src/"]}' > "$O/$ID.remap.json"
     (cd "$T" && SOLC="$SOLC/solc-0.8.20/solc-0.8.20" timeout 420 "$SCR/mvenv/bin/myth" analyze src/OrcClaim.sol:OrcClaim --solc-json "$O/$ID.remap.json" --execution-timeout 300 --max-depth 22 --no-onchain-data -o json) >"$O/$ID.json" 2>"$O/$ID.log"; EC=$?;;
  circomspect:redpacket) (cd "$T" && "$ROOT/tools/circomspect-src/target/release/circomspect" circuits/passcode.circom) >"$O/$ID.log" 2>&1; EC=$?;;
  picus:redpacket) (cd "$T" && timeout 600 "$ROOT/tools/picus-src/run-picus" circuits/passcode.circom) >"$O/$ID.log" 2>&1; EC=$?;;
  nargo:privacyvaults) NG="$ROOT/tools/noir-1.0.0-beta.14/nargo"; : >"$O/$ID.log"
     (cd "$T/circuits" && "$NG" check) >>"$O/$ID.log" 2>&1; echo "exit circuits $?" >>"$O/$ID.log"
     (cd "$T/circuits_borrow" && "$NG" check) >>"$O/$ID.log" 2>&1; EC=$?; echo "exit circuits_borrow $EC" >>"$O/$ID.log";;
  *) echo "unsupported layer for $TOOL on $H" >"$O/$ID.log"; EC=unsupported;;
esac
end=$(date +%s); echo "tool=$TOOL id=$ID exit=$EC seconds=$((end-start))" > "$O/$ID.meta"
echo "$TOOL $ID exit=$EC $((end-start))s"
