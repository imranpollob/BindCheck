#!/usr/bin/env bash
# Generate a real PropertyFy proof and exercise the unchanged ZKredential
# gateway/token on Hardhat's owned in-process EVM. No public RPC is contacted.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$ROOT/../bindcheck-zk/feasibility/work/full-dev/DEV-F30--ethpanda-org__ETHShanghai-2025--23917814522b"
COMMIT="23917814522bac494150c7e99a123aa15a448155"
CIRCOM_COMMIT="ad44e915a12bb047b05745c2884aad9cc8326bc6"
RUN_ID="zkredential-impact-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/impact/$RUN_ID"
WORK="$OUT/work"
PROOFS="$OUT/proofs"
CIRCUIT_BUILD="$OUT/circuit-build"
STEPS="$OUT/steps.tsv"
mkdir -p "$WORK" "$PROOFS" "$CIRCUIT_BUILD"
: > "$STEPS"

run_in() {
  local directory="$1"
  local name="$2"
  local expected="$3"
  shift 3
  local log="$OUT/$name.log"
  local observed=0
  set +e
  {
    printf '$ (cd %q &&' "$directory"
    printf ' %q' "$@"
    printf ')\n'
    (cd "$directory" && "$@")
  } >"$log" 2>&1
  observed=$?
  set -e
  local status="PASS"
  [[ "$observed" -eq "$expected" ]] || status="FAIL"
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == "PASS" ]]
}

[[ "$(git -C "$REPO" rev-parse HEAD)" == "$COMMIT" ]]
[[ "$(git -C "$ROOT/../bindcheck-zk/tools/circom-src" rev-parse HEAD)" == "$CIRCOM_COMMIT" ]]
git -C "$REPO" archive --format=tar --output="$OUT/zkredential-source.tar" "$COMMIT:projects/ZKredential"
tar -xf "$OUT/zkredential-source.tar" -C "$WORK"

{
  echo "run_id=$RUN_ID"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "workspace_git_head=$(git -C "$ROOT" rev-parse HEAD)"
  echo "source_commit=$COMMIT"
  echo "circom_source_commit=$(git -C "$ROOT/../bindcheck-zk/tools/circom-src" rev-parse HEAD)"
  echo "circom=$($ROOT/../bindcheck-zk/tools/circom-src/target/release/circom --version)"
  echo "node=$(node --version)"
  echo "npm=$(npm --version)"
  echo "pnpm_runner=npx --yes pnpm@10.18.3"
  echo "source_tar_sha256=$(shasum -a 256 "$OUT/zkredential-source.tar" | awk '{print $1}')"
} > "$OUT/environment.txt"

run_in "$WORK" 10_pnpm_install 0 npx --yes pnpm@10.18.3 install --frozen-lockfile \
  --filter zkredential-contracts --filter zkredential-proof-server
if [[ ! -e "$WORK/packages/zk-proof-server/circuits/node_modules" ]]; then
  ln -s ../node_modules "$WORK/packages/zk-proof-server/circuits/node_modules"
fi

CIRCOM="$ROOT/../bindcheck-zk/tools/circom-src/target/release/circom"
SNARKJS="$WORK/packages/zk-proof-server/node_modules/.bin/snarkjs"
CIRCUITS="$WORK/packages/zk-proof-server/circuits"
KEYS="$CIRCUITS/keys"
CONTRACTS="$WORK/packages/zk-contracts"

run_in "$CIRCUITS" 20_compile_circuit 0 "$CIRCOM" propertyfy_circuit.circom \
  --r1cs --wasm --sym -o "$CIRCUIT_BUILD" -l "$WORK/packages/zk-proof-server/node_modules"
run_in "$CIRCUITS" 21_zkey_correspondence 0 "$SNARKJS" zkey verify \
  "$CIRCUIT_BUILD/propertyfy_circuit.r1cs" "$KEYS/powersOfTau_final.ptau" "$KEYS/propertyfy_final.zkey"
run_in "$ROOT" 22_make_input 0 node "$ROOT/findings/zkredential/make_input.js" "$PROOFS/input.json"
run_in "$CIRCUITS" 23_fullprove 0 "$SNARKJS" groth16 fullprove \
  "$PROOFS/input.json" "$CIRCUIT_BUILD/propertyfy_circuit_js/propertyfy_circuit.wasm" \
  "$KEYS/propertyfy_final.zkey" "$PROOFS/proof.json" "$PROOFS/public.json"
run_in "$CIRCUITS" 24_export_vkey 0 "$SNARKJS" zkey export verificationkey \
  "$KEYS/propertyfy_final.zkey" "$PROOFS/vkey.json"
run_in "$CIRCUITS" 25_offchain_verify 0 "$SNARKJS" groth16 verify \
  "$PROOFS/vkey.json" "$PROOFS/public.json" "$PROOFS/proof.json"

cp "$ROOT/findings/zkredential/original.test.js" "$CONTRACTS/test/v2-zkredential-e4.test.js"
mkdir -p "$CONTRACTS/contracts-v2/core" "$CONTRACTS/contracts-v2/verifiers" \
  "$CONTRACTS/contracts-v2/demo" "$CONTRACTS/contracts-v2/interfaces" "$CONTRACTS/contracts-v2/adapters"
cp "$CONTRACTS/contracts/core/ComplianceGateway.sol" "$CONTRACTS/contracts-v2/core/"
cp "$CONTRACTS/contracts/core/ZKRWARegistry.sol" "$CONTRACTS/contracts-v2/ZKRWARegistry.sol"
cp "$CONTRACTS/contracts/verifiers/PropertyFyVerifier.sol" "$CONTRACTS/contracts-v2/verifiers/"
cp "$CONTRACTS/contracts/demo/ZKRWATokenERC3643.sol" "$CONTRACTS/contracts-v2/demo/"
cp "$CONTRACTS/contracts/adapters/ZKComplianceModule.sol" "$CONTRACTS/contracts-v2/adapters/"
cp "$CONTRACTS/contracts/interfaces/"*.sol "$CONTRACTS/contracts-v2/interfaces/"
cp "$ROOT/findings/zkredential/hardhat.config.js" "$CONTRACTS/hardhat.v2.config.js"
run_in "$CONTRACTS" 30_hardhat_compile 0 "$CONTRACTS/node_modules/.bin/hardhat" compile \
  --config hardhat.v2.config.js
export ZKREDENTIAL_PROOF="$PROOFS/proof.json"
export ZKREDENTIAL_PUBLIC="$PROOFS/public.json"
export ZKREDENTIAL_OBSERVATION="$OUT/observation.json"
export ZKREDENTIAL_COMMIT="$COMMIT"
run_in "$CONTRACTS" 40_unchanged_consumer_e4 0 "$CONTRACTS/node_modules/.bin/hardhat" test \
  --config hardhat.v2.config.js --no-compile test/v2-zkredential-e4.test.js

run_in "$ROOT" 50_apply_repair 0 python3 "$ROOT/findings/zkredential/repair.py" \
  "$CONTRACTS/contracts-v2/core/ComplianceGateway.sol"
cp "$ROOT/findings/zkredential/repair.test.js" "$CONTRACTS/test/v2-zkredential-repair.test.js"
run_in "$CONTRACTS" 51_repair_compile 0 "$CONTRACTS/node_modules/.bin/hardhat" compile \
  --config hardhat.v2.config.js
export ZKREDENTIAL_REPAIR_OBSERVATION="$OUT/repair-observation.json"
run_in "$CONTRACTS" 52_repair_control 0 "$CONTRACTS/node_modules/.bin/hardhat" test \
  --config hardhat.v2.config.js --no-compile test/v2-zkredential-repair.test.js

shasum -a 256 \
  "$CIRCUITS/propertyfy_circuit.circom" \
  "$KEYS/propertyfy_final.zkey" \
  "$CONTRACTS/contracts/verifiers/PropertyFyVerifier.sol" \
  "$CONTRACTS/contracts/core/ComplianceGateway.sol" \
  "$CONTRACTS/contracts/demo/ZKRWATokenERC3643.sol" \
  "$PROOFS/proof.json" "$PROOFS/public.json" "$OUT/observation.json" > "$OUT/sha256.txt"
shasum -a 256 "$CONTRACTS/contracts-v2/core/ComplianceGateway.sol" \
  "$OUT/repair-observation.json" "$ROOT/findings/zkredential/repair.py" \
  "$ROOT/findings/zkredential/repair.test.js" >> "$OUT/sha256.txt"

python3 - "$OUT" <<'PY'
import csv
import json
import pathlib
import sys
out = pathlib.Path(sys.argv[1])
steps = []
with (out / "steps.tsv").open(newline="") as handle:
    for name, expected, observed, status in csv.reader(handle, delimiter="\t"):
        steps.append({"name": name, "expected": expected, "observed": observed, "status": status})
result = {
    "target": "ethpanda-org/ETHShanghai-2025 projects/ZKredential",
    "pattern": "P1 unproven mint amount and proof-wallet/effect-recipient mismatch",
    "verdict": "VIOLATION",
    "evidence_grade": "E4",
    "local_only": True,
    "real_verifier": True,
    "zkey_r1cs_correspondence_verified": True,
    "unchanged_consumer_exploit": True,
    "prospective_repair_control": True,
    "unchanged_token": True,
    "all_steps_pass": all(step["status"] == "PASS" for step in steps),
    "steps": steps,
}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
PY

echo "RESULT: ZKredential real proof for one wallet minted a caller-chosen amount to a different caller through unchanged contracts"
echo "EVIDENCE: $OUT"
