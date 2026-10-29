#!/usr/bin/env bash
# TE04: E4 for PY-C02 W002 with zero mock components (mutant agg_agg proof
# wrapped by a mutant-keyed agg_final, verified by a real bb Solidity
# verifier, replayed against the pinned consumer on anvil).
# Part 1 (this script): mutant agg_final circuit -> prove -> verify ->
# Solidity verifiers (mutant + pinned contrast).
# Part 2 (python, reuses scripts/xav_run.py payy helpers): anvil replay.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
L=results/raw/TE04; B=build/TE04; mkdir -p "$L" "$B"
REF=/Users/imranpollob/Coding/bc/BindCheck/tools/cases/payy-c4d2c90
NARGO=/Users/imranpollob/Coding/bc/BindCheck/tools/noir-1.0.0-beta.14/nargo
BB=/Users/imranpollob/Coding/bc/BindCheck/tools/bb-3.0.0-manual.20251030/bb
MUT_VK_HASH_DEC=708245891687198352379886827440093080741855674602516992578420797617962603861
step() { echo "[$(date +%H:%M:%S)] $*"; }

step "stage agg_final with mutant VK-hash constant"
rm -rf "$B/noir" && cp -r "$REF/noir" "$B/noir" && rm -rf "$B/noir/target" "$B/noir"/*/target
python3 -I - "$B/noir/agg_final/src/main.nr" "$MUT_VK_HASH_DEC" <<'PY'
import sys
p, h = sys.argv[1], sys.argv[2]
t = open(p).read()
old = [l for l in t.splitlines() if l.startswith('global AGG_AGG_VERIFICATION_KEY_HASH')]
assert len(old) == 1, old
t = t.replace(old[0], f'global AGG_AGG_VERIFICATION_KEY_HASH: Field = {h};')
open(p, 'w').write(t)
print('constant set;', old[0][:80])
PY

step "build agg_final Prover.toml from TC02 tail-candidate artifacts (007)"
python3 -I - "$B/noir/agg_final/Prover.toml" <<'PY'
import sys
out = sys.argv[1]
R = '/Users/imranpollob/Coding/bc/bindcheck-lane-x'
vk = open(R + '/build/TC02/vk-mutant/vk', 'rb').read()
assert len(vk) == 115 * 32
proof = open(R + '/build/TC02/capture-mutant2/007-prove/out/proof', 'rb').read()
assert len(proof) == 508 * 32, len(proof)
pi = open(R + '/build/TC02/capture-mutant2/007-prove/out/public_inputs', 'rb').read()
assert len(pi) == 1005 * 32, len(pi)
f = lambda b: '"0x' + b.hex() + '"'
arr = lambda bs, n: '[' + ','.join(f(bs[i*32:(i+1)*32]) for i in range(n)) + ']'
old, new, commit = f(pi[2*32:3*32]), f(pi[3*32:4*32]), f(pi[4*32:5*32])
msgs = arr(pi[5*32:], 1000)
toml = ('verification_key = %s\nverification_key_hash = %s\nproof = %s\n'
        'old_root = %s\nnew_root = %s\ncommit_hash = %s\nmessages = %s\n'
        % (arr(vk, 115), f(open(R + '/build/TC02/vk-mutant/vk_hash', 'rb').read()),
           arr(proof, 508), old, new, commit, msgs))
open(out, 'w').write(toml)
print('Prover.toml bytes:', len(toml), 'old_root:', old[:18])
PY

step "nargo compile + execute (mutant agg_final)"
(cd "$B/noir" && NARGO_HOME=/Users/imranpollob/nargo nice -n 19 "$NARGO" compile --package agg_final) > "$L/10-compile.log" 2>&1 || { tail -5 "$L/10-compile.log"; exit 1; }
(cd "$B/noir/agg_final" && NARGO_HOME=/Users/imranpollob/nargo nice -n 19 "$NARGO" execute) > "$L/11-execute.log" 2>&1 || { tail -8 "$L/11-execute.log"; exit 1; }
echo "execute ok"

step "bb write_vk (mutant agg_final) + prove + verify"
mkdir -p "$B/vk-final-mutant" "$B/crs"
"$BB" write_vk --scheme ultra_honk --oracle_hash keccak -b "$B/noir/target/agg_final.json" -o "$B/vk-final-mutant" -c "$B/crs" > "$L/12-write_vk.log" 2>&1 || { tail -3 "$L/12-write_vk.log"; exit 1; }
python3 -I -c "print(int.from_bytes(open('$B/vk-final-mutant/vk_hash','rb').read(),'big'))" | tee "$L/13-final-vk-hash.txt"
WIT="$B/noir/target/agg_final.gz"; echo "witness: $WIT"; ls -la "$WIT"
mkdir -p "$B/proof-final"
"$BB" prove --scheme ultra_honk --oracle_hash keccak -b "$B/noir/target/agg_final.json" -w "$WIT" -k "$B/vk-final-mutant/vk" -o "$B/proof-final" > "$L/14-prove.log" 2>&1 || { tail -3 "$L/14-prove.log"; exit 1; }
ls -la "$B/proof-final/"
"$BB" verify --scheme ultra_honk --oracle_hash keccak -k "$B/vk-final-mutant/vk" -p "$B/proof-final/proof" -i "$B/proof-final/public_inputs" > "$L/15-verify.log" 2>&1 || { tail -3 "$L/15-verify.log"; exit 1; }
echo "mutant agg_final proof verifies"

step "Solidity verifiers (mutant + pinned contrast)"
"$BB" write_solidity_verifier --scheme ultra_honk -k "$B/vk-final-mutant/vk" -o "$B/verifier-mutant.sol" -c "$B/crs" > "$L/16-sol-mutant.log" 2>&1 || { tail -3 "$L/16-sol-mutant.log"; exit 1; }
"$BB" write_solidity_verifier --scheme ultra_honk -k "$REF/fixtures/circuits/agg_final/key" -o "$B/verifier-pinned.sol" -c "$B/crs" > "$L/16-sol-pinned.log" 2>&1 || { tail -3 "$L/16-sol-pinned.log"; exit 1; }
grep -n "function verify" "$B/verifier-mutant.sol" | head -3
echo "PART1-DONE"
