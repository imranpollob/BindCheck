#!/usr/bin/env python3
"""Prepare isolated unchanged-consumer replay from a recovered honest proof.

Does not run Forge or verify a proof. Those operations must use the bounded
runner. Only paths in the historical T13 test harness are changed.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/D1-03/proof-recovery-01'
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
SOURCE = BUILD / 'payy-B'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
key = SOURCE / 'fixtures/circuits/agg_final/key'
matches = [p for p in (RAW / 'capture').glob('*-prove')
           if (p / 'result.json').is_file()
           and json.loads((p / 'result.json').read_text())['exit_status'] == 0
           and sha(p / 'key') == sha(key)]
assert len(matches) == 1, 'one successful final proof required'
proof = matches[0] / 'out/proof'
inputs = matches[0] / 'out/public_inputs'
assert len(inputs.read_bytes()) == 1003 * 32
out = RAW / 'recovered'
out.mkdir(exist_ok=False)
for p in (proof, inputs, key):
    shutil.copy2(p, out / p.name)
bad = bytearray(inputs.read_bytes())
bad[5*32+31] ^= 1
(out / 'tampered_inputs').write_bytes(bad)
summary = {'evidence_level': 'GENERATED_NOT_YET_INDEPENDENTLY_VERIFIED',
           'agg_final_proof': {'proof_sha256': sha(proof), 'public_inputs_sha256': sha(inputs),
                               'key_sha256': sha(key), 'capture': str(matches[0].relative_to(ROOT))}}
(out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')

forge = BUILD / 'forge'
forge.mkdir(exist_ok=False)
shutil.copytree(SOURCE / 'eth/contracts/rollup3', forge / 'src/rollup3')
shutil.copy2(SOURCE / 'eth/contracts/IUSDC.sol', forge / 'src/IUSDC.sol')
(forge / 'src/noir').mkdir()
shutil.copy2(SOURCE / 'eth/contracts/noir/IVerifier.sol', forge / 'src/noir/IVerifier.sol')
bins = forge / 'bins'
bins.mkdir()
for name in ('agg_final_HonkVerifier.bin', 'agg_final_HonkVerifier.linkrefs.json', 'agg_final_ZKTranscriptLib.bin'):
    shutil.copy2(SOURCE / 'eth/contracts/noir' / name, bins / name)
harness = (ROOT / 'payy-consumer/test/MintSettlement.t.sol').read_text()
replacements = {'build/T12/bins/': str(bins)+'/',
                'results/raw/T13/agg_final_mint/': str(out)+'/',
                'results/raw/T13/40_proof_summary.json': str(out / 'summary.json'),
                'results/raw/T13/observations': str(RAW / 'observations')}
for old, new in replacements.items():
    assert old in harness
    harness = harness.replace(old, new)
(forge / 'test').mkdir()
(forge / 'test/MintSettlement.t.sol').write_text(harness)
q = json.dumps
(forge / 'foundry.toml').write_text(f'''[profile.default]
src = "src"
test = "test"
out = "out"
cache_path = "cache"
solc = {q(str(Path.home() / '.local/share/svm/0.8.20/solc-0.8.20'))}
evm_version = "cancun"
via_ir = true
optimizer = true
optimizer_runs = 200
remappings = [{q('forge-std/='+str(ROOT / 'lib/forge-std/src')+'/')}, {q('@openzeppelin/contracts/='+str(ROOT / 'tools/oz-5.0.1/contracts')+'/')}, {q('@openzeppelin/contracts-upgradeable/='+str(ROOT / 'tools/oz-5.0.1/upgradeable')+'/')}]
fs_permissions = [{{ access = "read", path = {q(str(bins))} }}, {{ access = "read", path = {q(str(out))} }}, {{ access = "read-write", path = {q(str(RAW / 'observations'))} }}]
''')
manifest = {'replacements': replacements,
            'original_harness_sha256': sha(ROOT / 'payy-consumer/test/MintSettlement.t.sol'),
            'files': {str(p.relative_to(forge)): sha(p) for p in forge.rglob('*') if p.is_file()}}
(RAW / 'replay-inputs.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('Prepared real proof controls and isolated consumer replay; not executed')
