#!/usr/bin/env bash
# Run the pinned Circomspect build on circuits used by the v2 experiments.
# Exit 1 means findings for Circomspect; parse/include errors are rejected.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CS_REPO="$ROOT/tools/circomspect-src"
CS="$CS_REPO/target/release/circomspect"
CS_COMMIT="50010b623ed4f3bff9d1b0363cfe952385b47af3"
RACE_REPO="$ROOT/feasibility/work/v2/repos/Servesh21__RacePass"
RACE_COMMIT="abd54b5c541ac9d26f938a6bdbd78545526249e5"
ZK_REPO="$ROOT/feasibility/work/v2/repos/ethpanda-org__ETHShanghai-2025/projects/ZKredential"
ZK_PARENT_REPO="$ROOT/feasibility/work/v2/repos/ethpanda-org__ETHShanghai-2025"
ZK_COMMIT="23917814522bac494150c7e99a123aa15a448155"
RUN_ID="circomspect-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/feasibility-v2/$RUN_ID"
STAGE="$OUT/stage"
STEPS="$OUT/steps.tsv"
mkdir -p "$STAGE/race/circuits/age_proof" "$STAGE/race/circuits/kyc_proof" "$STAGE/zk/modules"
: > "$STEPS"

[[ -x "$CS" ]]
[[ "$(git -C "$CS_REPO" rev-parse HEAD)" == "$CS_COMMIT" ]]
[[ "$(git -C "$RACE_REPO" rev-parse HEAD)" == "$RACE_COMMIT" ]]
[[ "$(git -C "$ZK_PARENT_REPO" rev-parse HEAD)" == "$ZK_COMMIT" ]]
cp "$RACE_REPO/circuits/age_proof/age_check.circom" "$STAGE/race/circuits/age_proof/"
cp "$RACE_REPO/circuits/kyc_proof/kyc_check.circom" "$STAGE/race/circuits/kyc_proof/"
ln -s "$ROOT/node_modules/circomlib" "$STAGE/race/circuits/circomlib"
cp "$ZK_REPO/packages/zk-proof-server/circuits/propertyfy_circuit.circom" "$STAGE/zk/"
cp "$ZK_REPO/packages/zk-proof-server/circuits/modules/kyc_verification.circom" "$STAGE/zk/modules/"
cp "$ZK_REPO/packages/zk-proof-server/circuits/modules/asset_verification.circom" "$STAGE/zk/modules/"
mkdir -p "$STAGE/zk/node_modules"
ln -s "$ROOT/node_modules/circomlib" "$STAGE/zk/node_modules/circomlib"

run_findings() {
  local name="$1"
  shift
  local log="$OUT/$name.log"
  local observed=0
  set +e
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$log" 2>&1
  observed=$?
  set -e
  local status="PASS"
  if [[ "$observed" -ne 0 && "$observed" -ne 1 ]]; then
    status="FAIL"
  fi
  if rg -q '^error\[P[0-9]+' "$log"; then
    status="FAIL"
  fi
  printf '%s\texpected=analysis-no-parse-errors\tobserved=%s\t%s\n' "$name" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == "PASS" ]]
}

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "circomspect_commit=$CS_COMMIT"
  echo "circomspect_binary_sha256=$(shasum -a 256 "$CS" | awk '{print $1}')"
  echo "rustc=$(rustc --version)"
  echo "cargo=$(cargo --version)"
} > "$OUT/environment.txt"

run_findings 10_unused_public "$CS" --verbose "$ROOT/feasibility/v2/public-input-unused.circom"
run_findings 20_racepass_age "$CS" --verbose "$STAGE/race/circuits/age_proof/age_check.circom"
run_findings 21_racepass_kyc "$CS" --verbose "$STAGE/race/circuits/kyc_proof/kyc_check.circom"
run_findings 30_zkredential_propertyfy "$CS" --verbose --library "$STAGE/zk/node_modules" \
  "$STAGE/zk/propertyfy_circuit.circom"

python3 - "$OUT" <<'PY'
import json
import pathlib
import re
import sys
out = pathlib.Path(sys.argv[1])
records = []
for log in sorted(out.glob("[0-9][0-9]_*.log")):
    text = log.read_text(errors="replace")
    records.append({
        "name": log.stem,
        "issue_count_reported": [int(x) for x in re.findall(r"circomspect: (\d+) issues? found", text)],
        "warning_ids": sorted(set(re.findall(r"warning\[([^]]+)\]", text))),
        "parse_error_ids": sorted(set(re.findall(r"error\[(P\d+)\]", text))),
    })
payload = {
    "scope": "circuit-only control; findings are not integration findings",
    "circomspect_commit": "50010b623ed4f3bff9d1b0363cfe952385b47af3",
    "records": records,
    "all_parse_clean": all(not record["parse_error_ids"] for record in records),
}
(out / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
PY

echo "RESULT: pinned Circomspect completed all four circuit-only controls without parse/include errors"
echo "EVIDENCE: $OUT"
