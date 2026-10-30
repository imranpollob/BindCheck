#!/bin/sh
# Build every binding mutant: compile (+ cheap honest-execution where applicable).
# Reads pinned sources/dependencies from read-only reference paths (recorded
# in manifest.json); writes only under $OUT (default results/raw/X-BM).
# All compiler invocations run at idle priority. No proving, no network.
set -u

XBM_ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-$XBM_ROOT/../../results/raw/X-BM}"
ONLY="${ONLY:-}"

ROOT="${BINDCHECK_ROOT:-$(cd "$XBM_ROOT/../.." && pwd)}"
PIN_SRC="${BINDCHECK_WARPTOAD_BACKEND:-$ROOT/results/raw/D1P-19/workspace/pinned-source/backend}"
PAYY_ROOT="${BINDCHECK_PAYY_ROOT:-$ROOT}"
PAYY_NOIR="${BINDCHECK_PAYY_NOIR:-$PAYY_ROOT/tools/cases/payy-c4d2c90/noir}"
PAYY_ETH="${BINDCHECK_PAYY_ETH:-$PAYY_ROOT/tools/cases/payy-c4d2c90/eth}"
NM12="${BINDCHECK_WARPTOAD_NODE_MODULES:-$ROOT/results/raw/D1P-19/workspace/source/backend/node_modules}"
NARGO22="${BINDCHECK_NARGO_22:-$ROOT/results/raw/artifact-tools/bin/nargo-beta22}"
NARGO14="${BINDCHECK_NARGO_14:-$ROOT/results/raw/artifact-tools/bin/nargo-beta14}"
SOLC29="${BINDCHECK_SOLC_0_8_29:-$ROOT/results/raw/artifact-tools/bin/solc-0.8.29}"
SOLC20="${BINDCHECK_SOLC_0_8_20:-$ROOT/results/raw/artifact-tools/bin/solc-0.8.20}"
HONEST_TOML="${BINDCHECK_HONEST_TOML:-$ROOT/results/raw/D1P-15/workspace/source/backend/circuits/withdraw/D1P15_12R.toml}"

MUTDIR="$OUT/mutants"; BUILDDIR="$OUT/build"; LOGDIR="$OUT/logs"
mkdir -p "$MUTDIR" "$BUILDDIR" "$LOGDIR"
uptime > "$LOGDIR/load.txt"

rm -f "$OUT/build-summary.tsv"
python3 "$XBM_ROOT/make_mutants.py" --baseline "$XBM_ROOT/baselines" \
  --out "$MUTDIR" ${ONLY:+--only "$ONLY"} --record "$OUT/generation-record.json" || exit 1

IDS="$(echo "${ONLY:-$(cd "$MUTDIR" && ls | tr '\n' ' ')}" | tr ',' ' ')"
RESULTS=""; N=0; PASS_COMPILE=0
for ID in $IDS; do
  N=$((N+1)); B="$BUILDDIR/$ID"; rm -rf "$B"; mkdir -p "$B"
  COMPILE_EXIT=""; EXEC_EXIT="null"; ART_SHA="null"
  case "$ID" in
    WT-C*)
      cp -r "$PIN_SRC/circuits" "$B/"; rm -rf "$B/circuits/withdraw/target"
      cp "$MUTDIR/$ID/warptoad-withdraw-main.nr" "$B/circuits/withdraw/src/main.nr"
      if [ -f "$MUTDIR/$ID/warptoad-nargo-hashing-lib.nr" ]; then
        cp "$MUTDIR/$ID/warptoad-nargo-hashing-lib.nr" "$B/circuits/nargo_hashing/src/lib.nr"
      fi
      [ -f "$HONEST_TOML" ] && cp "$HONEST_TOML" "$B/circuits/withdraw/Prover.toml"
      # C03 adds a struct field the honest Prover.toml lacks; drop the stale
      # witness file so compile is still checked and execute isHonestly skipped.
      if [ "$ID" = "WT-C03" ]; then rm -f "$B/circuits/withdraw/Prover.toml"; fi
      (cd "$B/circuits/withdraw" && nice -n 19 "$NARGO22" compile >"$LOGDIR/$ID-compile.log" 2>&1)
      COMPILE_EXIT=$?
      [ -f "$B/circuits/withdraw/target/withdraw.json" ] && ART_SHA=$(shasum -a 256 "$B/circuits/withdraw/target/withdraw.json" | cut -d' ' -f1)
      if [ "$COMPILE_EXIT" -eq 0 ] && [ -f "$B/circuits/withdraw/Prover.toml" ]; then
        (cd "$B/circuits/withdraw" && nice -n 19 "$NARGO22" execute >"$LOGDIR/$ID-execute.log" 2>&1)
        EXEC_EXIT=$?
      fi
      ;;
    WT-S*)
      cp -r "$PIN_SRC/contracts" "$B/"
      mkdir -p "$B/node_modules/@zk-kit" "$B/node_modules/@openzeppelin"
      cp -rL "$NM12/poseidon-solidity" "$B/node_modules/"
      cp -rL "$NM12/@zk-kit/lazy-imt.sol" "$B/node_modules/@zk-kit/"
      cp -rL "$NM12/@openzeppelin/contracts" "$B/node_modules/@openzeppelin/"
      cp "$MUTDIR/$ID/WarpToadCore.sol" "$B/contracts/core/WarpToadCore.sol"
      (cd "$B" && nice -n 19 "$SOLC29" --bin --base-path "$B" --allow-paths "$B" \
        --no-cbor-metadata contracts/core/WarpToadCore.sol -o "$B/out" \
        "poseidon-solidity/=node_modules/poseidon-solidity/" \
        "@zk-kit/=node_modules/@zk-kit/" \
        "@openzeppelin/=node_modules/@openzeppelin/" >"$LOGDIR/$ID-compile.log" 2>&1)
      COMPILE_EXIT=$?
      ;;
    PY-C*)
      cp -r "$PAYY_NOIR" "$B/noir"; rm -rf "$B/noir/target" "$B/noir"/*/target
      cp "$MUTDIR/$ID/payy-agg-agg-main.nr" "$B/noir/agg_agg/src/main.nr"
      (cd "$B/noir/agg_agg" && nice -n 19 "$NARGO14" compile >"$LOGDIR/$ID-compile.log" 2>&1)
      COMPILE_EXIT=$?
      [ -f "$B/noir/target/agg_agg.json" ] && ART_SHA=$(shasum -a 256 "$B/noir/target/agg_agg.json" | cut -d' ' -f1)
      ;;
    PY-S*)
      mkdir -p "$B/contracts/rollup3" "$B/contracts/noir" \
        "$B/node_modules/@openzeppelin" "$B/stubs"
      cp "$MUTDIR/$ID/RollupV1.sol" "$B/contracts/rollup3/"
      cp "$MUTDIR/$ID/payy-IVerifier.sol" "$B/contracts/noir/IVerifier.sol"
      cp "$MUTDIR/$ID/payy-IUSDC.sol" "$B/contracts/IUSDC.sol"
      mkdir -p "$B/stubs/proxy/utils" "$B/stubs/access"
      cp "$XBM_ROOT/_stubs/payy/proxy/utils/Initializable.sol" "$B/stubs/proxy/utils/"
      cp "$XBM_ROOT/_stubs/payy/access/OwnableUpgradeable.sol" "$B/stubs/access/"
      cp -rL "$NM12/@openzeppelin/contracts" "$B/node_modules/@openzeppelin/"
      # Payy hardhat pins viaIR + optimizer runs=200; mirror both (compile check only).
      (cd "$B" && nice -n 19 "$SOLC20" --bin --base-path "$B" --allow-paths "$B" \
        --no-cbor-metadata --optimize --optimize-runs 200 --via-ir \
        contracts/rollup3/RollupV1.sol -o "$B/out" \
        "@openzeppelin/=node_modules/@openzeppelin/" \
        "@openzeppelin/contracts-upgradeable/=stubs/" >"$LOGDIR/$ID-compile.log" 2>&1)
      COMPILE_EXIT=$?
      ;;
  esac
  [ "$COMPILE_EXIT" -eq 0 ] && PASS_COMPILE=$((PASS_COMPILE+1))
  printf '%s\t%s\t%s\t%s\n' "$ID" "$COMPILE_EXIT" "$EXEC_EXIT" "$ART_SHA" >> "$OUT/build-summary.tsv"
  echo "$ID compile=$COMPILE_EXIT execute=$EXEC_EXIT"
done
echo "compiled $PASS_COMPILE/$N"
