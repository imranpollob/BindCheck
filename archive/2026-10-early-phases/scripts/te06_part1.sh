#!/usr/bin/env bash
# TE06 part 1: wrap PINNED agg_agg proofs (control mint + tail burn) in the
# PINNED agg_final and prove under the COMMITTED final key. No mutant keys
# anywhere: every proof verifies natively before replay.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/TE06; B=build/TE06; mkdir -p "$L" "$B"
REF="${BINDCHECK_PAYY_REF:-/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-c4d2c90}"
NARGO="${BINDCHECK_NARGO_14:-/Users/imranpollob/Coding/bc/BindCheck/tools/noir-1.0.0-beta.14/nargo}"
BB="${BINDCHECK_BB:-/Users/imranpollob/Coding/bc/BindCheck/tools/bb-3.0.0-manual.20251030/bb}"
NH="${NARGO_HOME:-/Users/imranpollob/nargo}"
step() { echo "[$(date +%H:%M:%S)] $*"; }

step "stage pristine agg_final (committed key, no constant change)"
rm -rf "$B/noir" && cp -r "$REF/noir" "$B/noir" && rm -rf "$B/noir/target" "$B/noir"/*/target
grep -c AGG_AGG_VERIFICATION_KEY_HASH "$B/noir/agg_final/src/main.nr"

for ATT in control tail; do
if [ "$ATT" = control ]; then SLOT=005; else SLOT=007; fi
step "Prover.toml for $ATT (pinned slot $SLOT)"
SLOT="$SLOT" ATT="$ATT" python3 -I - "$B/noir/agg_final/Prover.toml" <<'PY'
import os, re, sys
out = sys.argv[1]
R = '/Users/imranpollob/Coding/bc/bindcheck-lane-x'
slot = os.environ['SLOT']
base = R + f'/build/TC02/capture-pinned/{slot}-prove/out'
vk = open('/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-c4d2c90/fixtures/circuits/agg_agg/key', 'rb').read()
assert len(vk) == 115 * 32, len(vk)
main = open(R + '/build/TE06/noir/agg_final/src/main.nr').read()
m = re.search(r'global AGG_AGG_VERIFICATION_KEY_HASH: Field = (\d+);', main)
assert m, 'committed constant missing'
vkh = int(m.group(1)).to_bytes(32, 'big')
proof = open(base + '/proof', 'rb').read()
assert len(proof) == 508 * 32, len(proof)
pi = open(base + '/public_inputs', 'rb').read()
assert len(pi) == 1005 * 32, len(pi)
f = lambda b: '"0x' + b.hex() + '"'
arr = lambda bs, n: '[' + ','.join(f(bs[i*32:(i+1)*32]) for i in range(n)) + ']'
old, new, commit = f(pi[2*32:3*32]), f(pi[3*32:4*32]), f(pi[4*32:5*32])
msgs = arr(pi[5*32:], 1000)
toml = ('verification_key = %s\nverification_key_hash = %s\nproof = %s\n'
        'old_root = %s\nnew_root = %s\ncommit_hash = %s\nmessages = %s\n'
        % (arr(vk, 115), f(vkh), arr(proof, 508), old, new, commit, msgs))
open(out, 'w').write(toml)
print(os.environ['ATT'], 'Prover.toml bytes:', len(toml), 'vkh:', m.group(1)[:12])
PY
cp "$B/noir/agg_final/Prover.toml" "$B/Prover-$ATT.toml"
done
step "nargo compile once + execute per attempt (pinned agg_final)"
(cd "$B/noir" && NARGO_HOME="$NH" nice -n 19 "$NARGO" compile --package agg_final) > "$L/10-compile.log" 2>&1 || { tail -5 "$L/10-compile.log"; exit 1; }
for ATT in control tail; do
cp "$B/Prover-$ATT.toml" "$B/noir/agg_final/Prover.toml"
(cd "$B/noir/agg_final" && NARGO_HOME="$NH" nice -n 19 "$NARGO" execute) > "$L/11-execute-$ATT.log" 2>&1 || { tail -8 "$L/11-execute-$ATT.log"; exit 1; }
echo "execute ok: $ATT"
done
step "bb write_vk (must equal committed key) + prove + verify per attempt"
mkdir -p "$B/vk-final-pinned" "$B/crs"
"$BB" write_vk --scheme ultra_honk --oracle_hash keccak -b "$B/noir/target/agg_final.json" -o "$B/vk-final-pinned" -c "$B/crs" > "$L/12-write_vk.log" 2>&1 || { tail -3 "$L/12-write_vk.log"; exit 1; }
if ! cmp -s "$B/vk-final-pinned/vk" "/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-c4d2c90/fixtures/circuits/agg_final/key"; then echo "VK-MISMATCH vs committed key"; exit 1; fi
echo "final VK == committed agg_final key"
for ATT in control tail; do
cp "$B/Prover-$ATT.toml" "$B/noir/agg_final/Prover.toml"
(cd "$B/noir/agg_final" && NARGO_HOME="$NH" nice -n 19 "$NARGO" execute) > "$L/11b-execute-$ATT.log" 2>&1 || exit 1
WIT="$B/noir/target/agg_final.gz"; mkdir -p "$B/proof-$ATT"
"$BB" prove --scheme ultra_honk --oracle_hash keccak -b "$B/noir/target/agg_final.json" -w "$WIT" -k "$B/vk-final-pinned/vk" -o "$B/proof-$ATT" > "$L/14-prove-$ATT.log" 2>&1 || { tail -3 "$L/14-prove-$ATT.log"; exit 1; }
"$BB" verify --scheme ultra_honk --oracle_hash keccak -k "$B/vk-final-pinned/vk" -p "$B/proof-$ATT/proof" -i "$B/proof-$ATT/public_inputs" > "$L/15-verify-$ATT.log" 2>&1 || { tail -3 "$L/15-verify-$ATT.log"; exit 1; }
echo "pinned final proof verifies: $ATT"
done
echo "PART1-DONE"
