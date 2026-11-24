#!/bin/sh
# Build clean hosts and every mutant of B2: compile (+ cheap honest check where the host ships tests).
# Usage: OUT=results/raw/B2/run-N sh build.sh   (OUT must not exist yet: no deletion is ever done)
# Needs: ./fetch-deps.sh done; forge; solc binaries in ~/.solc-select/artifacts; nargo beta.14.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../.." && pwd)"
OUT="${OUT:?set OUT to a fresh dir}"; DEPS="${DEPS:-$ROOT/results/raw/B2/deps}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT";; esac
[ -e "$OUT" ] && { echo "OUT exists: $OUT" >&2; exit 2; }
SOLC="$HOME/.solc-select/artifacts"
NARGO14="${NARGO14:-$ROOT/results/raw/artifact-tools/bin/nargo-beta14}"
[ -x "$NARGO14" ] || NARGO14="$ROOT/tools/noir-1.0.0-beta.14/nargo"
mkdir -p "$OUT/logs" "$OUT/trees"
python3 "$HERE/make_mutants.py" --out "$OUT/trees" || exit 1
for H in redpacket privacyvaults orc; do cp -r "$HERE/baselines/$H" "$OUT/trees/CLEAN-$H"; done
printf 'id\thost\tcompile_exit\ttest_exit\ttest_summary\n' > "$OUT/build-summary.tsv"
for T in "$OUT"/trees/*/; do
  ID=$(basename "$T"); [ "$ID" = generation-record.json ] && continue
  case "$ID" in RP-*|CLEAN-redpacket) H=redpacket;; PV-*|CLEAN-privacyvaults) H=privacyvaults;; OR-*|CLEAN-orc) H=orc;; esac
  CE=""; TE=""; TS=""
  case "$H" in
    redpacket)
      mkdir -p "$T/lib/oz"; cp -r "$DEPS/oz-4.8.1/contracts" "$T/lib/oz/"
      printf '[profile.default]\nsrc="contracts"\nout="out"\nlibs=["lib"]\nsolc="%s/solc-0.8.17/solc-0.8.17"\nauto_detect_solc=false\n' "$SOLC" > "$T/foundry.toml"
      echo '@openzeppelin/contracts/=lib/oz/contracts/' > "$T/remappings.txt"
      case "$ID" in RP-C*) # circuit mutant: compile circuit only
        (cd "$T" && nice -n 19 circom circuits/passcode.circom --r1cs --sym -o "$T" >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;;
      *) (cd "$T" && nice -n 19 forge build --offline >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;; esac;;
    privacyvaults)
      mkdir -p "$T/contracts/lib"; for p in oz-5.5.0:openzeppelin-contracts poseidon2-evm:poseidon2-evm forge-std-1.14.0:forge-std; do cp -r "$DEPS/${p%%:*}" "$T/contracts/lib/${p##*:}"; done
      printf '@openzeppelin/contracts=lib/openzeppelin-contracts/contracts\n@poseidon/=lib/poseidon2-evm/\nforge-std/=lib/forge-std/src/\n' > "$T/contracts/remappings.txt"
      printf '[profile.default]\nsrc="src"\nout="out"\nlibs=["lib"]\noptimizer=true\noptimizer_runs=1\nbytecode_hash="none"\nsolc="%s/solc-0.8.28/solc-0.8.28"\nauto_detect_solc=false\nevm_version="cancun"\n' "$SOLC" > "$T/contracts/foundry.toml"
      case "$ID" in
      PV-C0[12]) (cd "$T/circuits" && nice -n 19 "$NARGO14" compile >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;;
      PV-C03|PV-C01) (cd "$T/circuits_borrow" && nice -n 19 "$NARGO14" compile >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;;
      CLEAN-privacyvaults)
        (cd "$T/circuits" && nice -n 19 "$NARGO14" compile >"$OUT/logs/$ID-nargo.log" 2>&1); echo "nargo circuits exit $?" >>"$OUT/logs/$ID-nargo.log"
        (cd "$T/circuits_borrow" && nice -n 19 "$NARGO14" compile >>"$OUT/logs/$ID-nargo.log" 2>&1); echo "nargo circuits_borrow exit $?" >>"$OUT/logs/$ID-nargo.log"
        (cd "$T/contracts" && nice -n 19 forge build --offline >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;;
      *) (cd "$T/contracts" && nice -n 19 forge build --offline >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?;; esac;;
    orc)
      mkdir -p "$T/lib"; cp -r "$DEPS/orc-forge-std" "$T/lib/forge-std"; cp -r "$DEPS/sp1-contracts" "$T/lib/sp1-contracts"
      sed -i 's#^solc = "0.8.20"#solc = "'"$SOLC"'/solc-0.8.20/solc-0.8.20"#; s#^deny = "warnings"#deny = "never"#' "$T/foundry.toml"
      (cd "$T" && nice -n 19 forge build --offline >"$OUT/logs/$ID-compile.log" 2>&1); CE=$?
      if [ "$CE" -eq 0 ]; then
        (cd "$T" && nice -n 19 forge test --offline >"$OUT/logs/$ID-test.log" 2>&1); TE=$?
        TS=$(grep -E '^Ran [0-9]+ tests? for|Suite result' "$OUT/logs/$ID-test.log" | tr '\n' ' ' | cut -c1-200)
        grep -E '^\[(FAIL|PASS)' "$OUT/logs/$ID-test.log" | sed 's/ (gas.*//; s/ (runs.*//' | sort > "$OUT/logs/$ID-tests.txt"
      fi;;
  esac
  printf '%s\t%s\t%s\t%s\t%s\n' "$ID" "$H" "$CE" "$TE" "$TS" >> "$OUT/build-summary.tsv"
  echo "$ID compile=$CE test=$TE"
done
