#!/usr/bin/env python3
"""Check preservation and source identity at the recovery checkpoint."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
SOURCE = ROOT / 'build/D1-03/proof-recovery-01/payy-B'
LIVING = {'README.md', 'docs/d1/roadmap.md', 'docs/project-status.md'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check(mapping, resolve):
    failed = []
    for name, digest in mapping.items():
        path = resolve(name)
        if not path.is_file() or sha(path) != digest:
            failed.append(name)
    return {'checked': len(mapping), 'mismatches': failed}


def preserved_path(name):
    return RAW / 'prior-checkpoint' / name if name in LIVING else ROOT / name


prior = json.loads((ROOT / 'metadata/d1/d1-03-consumer-execution-01.json').read_text())
checks = {
    'prior_task_deliverables': check(prior['deliverables'], preserved_path),
    'prior_task_raw': check(prior['raw_files'], lambda n: ROOT / n),
    'starting_deliverables': check(json.loads((RAW / 'preserved.json').read_text()), preserved_path),
    'upstream_source': check(json.loads((RAW / 'source-manifest.json').read_text()), lambda n: SOURCE / n),
}
checks['protocol_frozen'] = sha(ROOT / 'protocols/d1/d1-03-proof-recovery-01.json') == (RAW / 'protocol.sha256').read_text().strip()
checks['passed'] = checks['protocol_frozen'] and all(not c['mismatches'] for c in checks.values() if isinstance(c, dict))
output = RAW / 'preservation-check.json'
with output.open('x') as stream:
    json.dump(checks, stream, indent=2)
    stream.write('\n')
print(json.dumps(checks, indent=2))
raise SystemExit(0 if checks['passed'] else 1)
