#!/usr/bin/env python3
"""Run the single authorized honest chain after a successful locked build."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/D1-03/proof-recovery-01'
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
builds = sorted(RAW.glob('build-*/result.json'))
assert builds and json.loads(builds[-1].read_text())['exit_status'] == 0, 'successful build required'
def is_elf(path):
    with path.open('rb') as stream:
        return stream.read(4) == b'\x7fELF'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


binaries = [p for p in (BUILD / 'cargo-target/debug/deps').glob('t13_mint-*')
            if p.is_file() and os.access(p, os.X_OK) and is_elf(p)]
assert len(binaries) == 1
binary = binaries[0]
source = BUILD / 'payy-B'
manifest = json.loads((RAW / 'source-manifest.json').read_text())
for name, digest in manifest.items():
    assert sha(source / name) == digest, f'upstream input changed: {name}'
assert sha(source / 'pkg/zk-circuits/tests/t13_mint.rs') == sha(ROOT / 'payy-harness/t13_mint.rs')
argv = [str(binary), '--exact', 't13_single_mint_agg_final', '--nocapture']
(RAW / 'proof-command.json').write_text(json.dumps({'argv': argv,
    'binary_sha256': sha(binary), 'harness_sha256': sha(ROOT / 'payy-harness/t13_mint.rs'),
    'all_original_source_files_unchanged': len(manifest),
    'harness_is_unchanged_historical_control': True}, indent=2)+'\n')
print(json.dumps({'argv': argv, 'binary_sha256': sha(binary)}), flush=True)
sys.exit(subprocess.call(argv, cwd=source))
