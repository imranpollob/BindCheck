#!/usr/bin/env python3
"""Extract checksum-pinned Ubuntu compiler libraries locally, without sudo."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/D1-03/proof-recovery-01'
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
PINS = {
    'libclang1-18': '1ed67106d743ab4f12db2726c5fc11c436c5e1fba613e9f1006bf3fa05cc69bd',
    'libclang-common-18-dev': 'd41631bb752815a8196261d1030c096591c59678c8adfbf2e6a740a691b49e80',
    'libllvm18': 'af6197096ce3b89aab86de59f01c1b5feb008b2ae1514a03906c0664edb8b0b1',
}
dest = BUILD / 'clang'
dest.mkdir(exist_ok=False)
debdir = BUILD / 'debs'
debdir.mkdir(exist_ok=False)
manifest = {}
for package, expected in PINS.items():
    paths = list(ROOT.glob(package + '_*.deb'))
    assert len(paths) == 1
    path = paths[0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, f'checksum mismatch: {package}'
    target = debdir / path.name
    shutil.move(path, target)
    metadata = subprocess.check_output(['apt-cache', 'show', package+'=1:18.1.3-1ubuntu1'], text=True)
    assert 'SHA256: '+actual in metadata
    (RAW / (package+'.apt-metadata.txt')).write_text(metadata)
    subprocess.run(['dpkg-deb', '-x', str(target), str(dest)], check=True)
    manifest[package] = {'version': '1:18.1.3-1ubuntu1', 'sha256': actual, 'file': str(target.relative_to(ROOT))}
(RAW / 'clang-setup.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('Extracted pinned libclang, headers and LLVM locally; no system packages installed')
