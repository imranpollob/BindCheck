#!/usr/bin/env bash
# AZ1 step 3 on the real target: BindCheck freeze 2 and Slither on Aztec Connect
# RollupProcessorV3 source. Reads public source only: the GitHub repository
# (hold-out guard first) and the Sourcify verified-source record. No chain RPC,
# no transaction, no deployed-contract interaction.
#
# usage: bash prototypes/az1/tools_real.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_ID="az1-real-$(date -u +%Y%m%dT%H%M%SZ)-$$"
OUT="$ROOT/results/raw/AZ1/$RUN_ID"
STEPS="$OUT/steps.tsv"
REPO=AztecProtocol/aztec-connect
COMMIT=69de49b1be49ae3757ccb53f07d9cb04a1987184   # head of PR #67 (cl/ejector), adds RollupProcessorV3.sol
IMPL=0x7d657Ddcf7e2A5fD118dC8A6dDc3dC308AdC2728     # implementation named in the write-ups; used only as a Sourcify lookup key
V3=contracts/src/core/processors/RollupProcessorV3.sol
DEC=contracts/src/core/Decoder.sol
SOLC_BIN="$HOME/.solc-select/artifacts/solc-0.8.10/solc-0.8.10"
SOLC_SHA=c7effacf28b9d64495f81b75228fbf4266ac0ec87e8f1adc489ddd8a4dd06d89
FREEZE2=92789fad12050a3058a21cc5c2326e7d41604ad5ade0f09f72a35789437e6c1a
CIRCOM="${BINDCHECK_TOOLS:-$ROOT/../bindcheck-zk/tools}/circom-src/target/release/circom"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/az1-real.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
mkdir -p "$OUT"; : > "$STEPS"

run() {
  local name="$1" expected="$2"; shift 2
  local log="$OUT/$name.log" observed=0
  set +e; { printf '$'; printf ' %q' "$@"; printf '\n'; "$@"; } >"$log" 2>&1; observed=$?; set -e
  local status=PASS; [[ "$observed" -eq "$expected" ]] || status=FAIL
  printf '%s\texpected=%s\tobserved=%s\t%s\n' "$name" "$expected" "$observed" "$status" | tee -a "$STEPS"
  [[ "$status" == PASS ]]
}

run 00_holdout_guard 0 python3 "$ROOT/scripts/check_holdout.py" "$REPO"
[[ "$(sha256sum "$SOLC_BIN" | awk '{print $1}')" == "$SOLC_SHA" ]] || { echo "solc 0.8.10 pin mismatch" >&2; exit 2; }
[[ "$(python3 "$ROOT/bindcheck_zk/freeze.py" | tail -1 | cut -d= -f2)" == "$FREEZE2" ]] || { echo "not freeze 2" >&2; exit 2; }
ln -s "$SOLC_BIN" "$SCRATCH/solc"

SRC="$OUT/src-aztec-connect"
run 01_clone 0 git clone -q --filter=blob:none --no-checkout "https://github.com/$REPO.git" "$SRC"
run 02_checkout 0 git -C "$SRC" checkout -q "$COMMIT"
run 03_sourcify_fetch 0 curl -fsS --max-time 60 -o "$OUT/sourcify.json" \
  "https://sourcify.dev/server/v2/contract/1/$IMPL?fields=sources,compilation"
python3 -I - "$OUT/sourcify.json" "$SRC" "$OUT/deployed" > "$OUT/04_source_correspondence.txt" <<'EOF'
import hashlib, json, pathlib, sys
d = json.load(open(sys.argv[1])); src = pathlib.Path(sys.argv[2]); out = pathlib.Path(sys.argv[3])
print("compiler", d["compilation"]["compilerVersion"], json.dumps(d["compilation"]["compilerSettings"].get("optimizer")))
for name, v in sorted(d["sources"].items()):
    p = out / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(v["content"])
    h = hashlib.sha256(v["content"].encode()).hexdigest()
    repo = src / "contracts" / name
    state = "NOT_IN_REPO_PATH"
    if repo.exists():
        state = "IDENTICAL" if hashlib.sha256(repo.read_bytes()).hexdigest() == h else "DIFFERS"
    print(h, state, name)
(out / "remaps.txt").write_text(" ".join(r.lstrip(":") for r in d["compilation"]["compilerSettings"]["remappings"]))
EOF
cat "$OUT/04_source_correspondence.txt"
grep -q "IDENTICAL src/core/processors/RollupProcessorV3.sol" "$OUT/04_source_correspondence.txt"
grep -q "IDENTICAL src/core/Decoder.sol" "$OUT/04_source_correspondence.txt"
sha256sum "$SRC/$V3" "$SRC/$DEC" "$OUT/sourcify.json" > "$OUT/05_hashes.txt"

# BindCheck freeze 2: verified-source tree, and pinned checkout, consumer named explicitly.
run 10_bindcheck_deployed 0 env BINDCHECK_CIRCOM="$CIRCOM" sh -c \
  'cd "$1" && python3 -m bindcheck_zk.cli analyze "$2" --consumer src/core/processors/RollupProcessorV3.sol > "$3"' \
  _ "$ROOT" "$OUT/deployed" "$OUT/10_bindcheck_deployed.json"
run 11_bindcheck_checkout 0 env BINDCHECK_CIRCOM="$CIRCOM" sh -c \
  'cd "$1" && python3 -m bindcheck_zk.cli analyze "$2" --consumer "$4" > "$3"' \
  _ "$ROOT" "$SRC" "$OUT/11_bindcheck_checkout.json" "$V3"

# Slither default detectors on the verified-source tree with its recorded settings.
cp -r "$OUT/deployed" "$SCRATCH/deployed"
set +e
(cd "$SCRATCH/deployed" && slither src/core/processors/RollupProcessorV3.sol --solc "$SCRATCH/solc" \
   --solc-remaps "$(cat remaps.txt)" --solc-args "--optimize --optimize-runs 2000 --evm-version london" \
   --json "$OUT/20_slither_deployed.json" > "$OUT/20_slither_deployed.log" 2>&1)
echo "20_slither_deployed	exit=$?	(json: success field decides)" | tee -a "$STEPS"
set -e

python3 -I - "$OUT" > "$OUT/30_summary.txt" <<'EOF'
import collections, json, pathlib, re, sys
out = pathlib.Path(sys.argv[1])
for n in ("10_bindcheck_deployed", "11_bindcheck_checkout"):
    d = json.load(open(out / f"{n}.json"))
    print(n, "discovery", json.dumps(d["discovery"]))
    for p in ("P1", "P2", "P3", "P4", "P5"):
        r = d["patterns"][p]; print(" ", p, r["verdict"], r.get("reasons"), r.get("evidence_grade"))
s = json.load(open(out / "20_slither_deployed.json"))
det = s["results"].get("detectors", []) if s.get("success") else []
print("slither success", s.get("success"), "results", len(det))
for k, v in sorted(collections.Counter((x["check"], x["impact"]) for x in det).items()): print(" ", v, k)
pat = re.compile(r"numTxs|numRealTxs|processDepositsAndWithdrawals|processRollupProof|decodeProof")
rel = [x for x in det if pat.search(x["description"]) and x["check"] not in ("naming-convention", "assembly", "cyclomatic-complexity")]
print("non-style results touching the settlement/decoder path:", len(rel))
for x in rel: print("  ", x["check"], "|", x["description"].strip().splitlines()[0][:220])
EOF
cat "$OUT/30_summary.txt"
echo "out=$OUT"
