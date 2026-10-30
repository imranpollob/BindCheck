#!/usr/bin/env bash
# TE06: wrap the chained batch-2 agg_agg proof (double settlement) in the
# pinned agg_final and prove under the committed final key.
# Env: TE06_BATCH2_SLOT (capture slot name, e.g. 011-prove), default auto-detects
# the last 508-word prove capture in build/TE06/capture-double.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/TE06; B=build/TE06
NARGO="${BINDCHECK_NARGO_14:-/Users/imranpollob/Coding/bc/BindCheck/tools/noir-1.0.0-beta.14/nargo}"
BB="${BINDCHECK_BB:-/Users/imranpollob/Coding/bc/BindCheck/tools/bb-3.0.0-manual.20251030/bb}"
NH="${NARGO_HOME:-/Users/imranpollob/nargo}"
if [ -z "${TE06_BATCH2_SLOT:-}" ]; then
  TE06_BATCH2_SLOT=""
  for d in "$B"/capture-double/*-prove; do
    if [ -f "$d/out/proof" ] && [ "$(stat -f%z "$d/out/proof" 2>/dev/null || stat -c%s "$d/out/proof")" = "16256" ]; then
      TE06_BATCH2_SLOT="$(basename "$d")"
    fi
  done
fi
echo "batch2 slot: $TE06_BATCH2_SLOT"
python3 -I - "$B/noir/agg_final/Prover.toml" <<PY
import os, re
R = '/Users/imranpollob/Coding/bc/bindcheck-lane-x'
base = R + '/build/TE06/capture-double/${TE06_BATCH2_SLOT}/out'
vk = open('/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-c4d2c90/fixtures/circuits/agg_agg/key', 'rb').read()
assert len(vk) == 115 * 32, len(vk)
main = open(R + '/build/TE06/noir/agg_final/src/main.nr').read()
vkh = int(re.search(r'global AGG_AGG_VERIFICATION_KEY_HASH: Field = (\d+);', main).group(1)).to_bytes(32, 'big')
proof = open(base + '/proof', 'rb').read()
assert len(proof) == 508 * 32, len(proof)
pi = open(base + '/public_inputs', 'rb').read()
assert len(pi) == 1005 * 32, len(pi)
f = lambda b: '"0x' + b.hex() + '"'
arr = lambda bs, n: '[' + ','.join(f(bs[i*32:(i+1)*32]) for i in range(n)) + ']'
toml = ('verification_key = %s\nverification_key_hash = %s\nproof = %s\n'
        'old_root = %s\nnew_root = %s\ncommit_hash = %s\nmessages = %s\n'
        % (arr(vk, 115), f(vkh), arr(proof, 508), f(pi[2*32:3*32]), f(pi[3*32:4*32]), f(pi[4*32:5*32]), arr(pi[5*32:], 1000)))
open('/Users/imranpollob/Coding/bc/bindcheck-lane-x/build/TE06/noir/agg_final/Prover.toml', 'w').write(toml)
print('batch2 Prover.toml ok; msg0-3:', [pi[(5+k)*32:(6+k)*32].hex()[:10] for k in range(4)])
PY
(cd "$B/noir/agg_final" && NARGO_HOME="$NH" nice -n 19 "$NARGO" execute) > "$L/11b-execute-batch2.log" 2>&1 || { tail -8 "$L/11b-execute-batch2.log"; exit 1; }
echo "execute ok: batch2"
mkdir -p "$B/proof-batch2"
"$BB" prove --scheme ultra_honk --oracle_hash keccak -b "$B/noir/target/agg_final.json" -w "$B/noir/target/agg_final.gz" -k "$B/vk-final-pinned/vk" -o "$B/proof-batch2" > "$L/14-prove-batch2.log" 2>&1 || { tail -3 "$L/14-prove-batch2.log"; exit 1; }
"$BB" verify --scheme ultra_honk --oracle_hash keccak -k "$B/vk-final-pinned/vk" -p "$B/proof-batch2/proof" -i "$B/proof-batch2/public_inputs" > "$L/15-verify-batch2.log" 2>&1 || { tail -3 "$L/15-verify-batch2.log"; exit 1; }
echo "pinned final proof verifies: batch2"
