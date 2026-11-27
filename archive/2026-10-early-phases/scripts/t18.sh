#!/usr/bin/env bash
# BindCheck T18: does the T16 synthetic burn record produce an actual token transfer on a locally deployed instance of the
# EARLIER Payy revision's own consumer and verifier? Reuses T16's exact control/candidate proof+public-input BYTES (no new
# proof, no circuit/key change). usage: bash scripts/t18.sh (about 1-2 minutes; no proving)
# Prerequisites: scripts/t15.sh and t16.sh have run (tools/cases/payy-c4d2c90 worktree, results/raw/T16/{control,candidate},
# results/raw/T12/11_hash_derivation.txt for the earlier revision's registry key); payy-consumer/src populated by scripts/t12.sh
# (consumer source is byte-identical between revisions, confirmed in T15).
# Local testbed only: owned prover/validator/minter accounts. Not advisory reproduction, not an arbitrary-user-exploit or
# historical-deployment-impact claim.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/T18; H=tools/cases/payy-c4d2c90
die() { echo "PREREQUISITE/CHECK FAILED: $*"; exit 1; }
mkdir -p "$L" build/T18/bins
[ -e "$H/.git" ] || die "worktree $H missing (run scripts/t15.sh first)"
for f in results/raw/T16/control/proof results/raw/T16/control/public_inputs results/raw/T16/candidate/proof results/raw/T16/candidate/public_inputs results/raw/T16/40_summary.json; do
  [ -f "$f" ] || die "missing T16 artifact $f (run scripts/t16.sh first)"
done
[ -f payy-consumer/src/rollup3/RollupV1.sol ] || die "payy-consumer/src missing (run scripts/t12.sh first)"
for f in agg_final_HonkVerifier.bin agg_final_HonkVerifier.linkrefs.json agg_final_ZKTranscriptLib.bin; do
  cp "$H/eth/contracts/noir/$f" "build/T18/bins/$f"
done
rm -f "$L"/0*.txt "$L"/5*.log "$L"/5*.txt "$L"/9*.json; rm -rf "$L/observations"
{ echo "revision (earlier, matches T15/T16's c4d2c90 side): $(git -C "$H" rev-parse HEAD)"; forge --version | head -1; echo "host: $(uname -srm)"; echo "date_utc: $(date -u +%FT%TZ)"
  echo; echo "## reused T16 artifact hashes (no regeneration)"
  for p in control/proof control/public_inputs candidate/proof candidate/public_inputs; do
    [ -f "results/raw/T16/$p" ] && echo "sha256 $p: $(shasum -a 256 "results/raw/T16/$p" | cut -d' ' -f1)"; done
  echo; echo "## earlier revision's agg_final registry key (Rust vk_hash binary, results/raw/T12/11_hash_derivation.txt)"
  grep '^\[c4d2c90\] agg_final vk_hash binary' results/raw/T12/11_hash_derivation.txt 2>/dev/null || echo "(results/raw/T12/11_hash_derivation.txt not present; registry key is hard-coded in the test, see reports/T18.md)"
  echo; echo "## earlier revision's committed agg_final verifier bytecode (build/T18/bins, copied from the worktree)"
  for f in agg_final_HonkVerifier.bin agg_final_HonkVerifier.linkrefs.json agg_final_ZKTranscriptLib.bin; do echo "sha256 $f: $(shasum -a 256 "build/T18/bins/$f" | cut -d' ' -f1)"; done
} > "$L/00_environment.txt"

FOUNDRY_PROFILE=payy-consumer forge test --match-path 'payy-consumer/test/BurnPropagation.t.sol' -vv > "$L/50_forge.log" 2>&1; RC=$?
sed 's/\x1b\[[0-9;]*m//g' "$L/50_forge.log" | grep -E '^\[(PASS|FAIL)|Suite result|Ran [0-9]+ tests?' | tee "$L/51_forge_results.txt"

python3 -I - "$L" "$RC" <<'PY'
import glob, json, os, sys
L, rc = sys.argv[1], int(sys.argv[2])
obs = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f"{L}/observations/*.json")}
out = {"forge_exit": rc, "cases": {k: {"status": v["status"], "reason": v["reason"], "verifierCall": v["verifierCall"], "burnedEvent": v["burnedEvent"],
       "pre_tokenBalances": v["pre"]["tokenBalances"], "post_tokenBalances": v["post"]["tokenBalances"]} for k, v in sorted(obs.items())}}
json.dump(out, open(f"{L}/90_summary.json", "w"), indent=2); open(f"{L}/90_summary.json", "a").write("\n")
print(json.dumps(out, indent=1))
PY
echo; echo "Local result for the earlier revision and owned test identities only: not advisory reproduction, not an arbitrary-user-exploit or historical-deployment-impact claim."
exit $RC
