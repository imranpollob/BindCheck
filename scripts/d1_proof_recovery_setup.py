#!/usr/bin/env python3
"""Materialize pinned source and verified Linux bb; never modify tools/cases."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/D1-03/proof-recovery-01'
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
P = json.loads((ROOT / 'protocols/d1/d1-03-proof-recovery-01.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

assert sha(BUILD / 'bb.tar.gz') == P['bb_sha256'], 'bb checksum mismatch'
bbdir = BUILD / 'bb'
bbdir.mkdir(exist_ok=False)
with tarfile.open(BUILD / 'bb.tar.gz') as archive:
    archive.extractall(bbdir, filter='data')
subprocess.run(['git', '-C', str(ROOT / 'tools/cases/payy-history'), 'archive',
                '--format=tar', '--output=' + str(BUILD / 'source.tar'), P['source_revision']], check=True)
source = BUILD / 'payy-B'
source.mkdir(exist_ok=False)
with tarfile.open(BUILD / 'source.tar') as archive:
    archive.extractall(source, filter='data')
manifest = {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
(RAW / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
test = source / 'pkg/zk-circuits/tests/t13_mint.rs'
assert not test.exists()
test.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'payy-harness/t13_mint.rs', test)
(RAW / 'setup.json').write_text(json.dumps({
    'source_revision': P['source_revision'], 'source_archive_sha256': sha(BUILD / 'source.tar'),
    'source_files': len(manifest), 'bb_archive_sha256': sha(BUILD / 'bb.tar.gz'),
    'bb_files': {str(p.relative_to(bbdir)): sha(p) for p in bbdir.rglob('*') if p.is_file()},
    'harness_sha256': sha(test), 'harness_origin': 'payy-harness/t13_mint.rs',
    'source_changes': ['Added unchanged historical integration harness; no upstream source edits']
}, indent=2) + '\n')
print('Extracted', len(manifest), 'source files; verified bb checksum')
