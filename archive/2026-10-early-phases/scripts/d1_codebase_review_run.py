#!/usr/bin/env python3
"""Append-only executions for the frozen D1 codebase review 01."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-review/codebase-01'
PROTOCOL = ROOT / 'protocols/d1/d1-codebase-review-01.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('python', 'node', 'guard'))
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text())
    caps = {'python': protocol['limits']['python_test_invocations'],
            'node': protocol['limits']['node_test_invocations'],
            'guard': protocol['limits']['guard_artifact_invocations']}
    attempts = sorted(RAW.glob(args.kind + '-[0-9][0-9]'))
    if len(attempts) >= caps[args.kind]:
        raise SystemExit('Frozen invocation limit exhausted')
    now = datetime.datetime.now(datetime.timezone.utc)
    if (now - datetime.datetime.fromisoformat(protocol['frozen_at_utc'])).total_seconds() > 90 * 60:
        raise SystemExit('Frozen wall budget exhausted')
    if args.kind == 'guard':
        tests = sorted(RAW.glob('python-*/execution.json'))
        if not tests or json.loads(tests[-1].read_text())['exit_status'] != 0:
            raise SystemExit('Current passing Python controls required before artifact check')
    out = RAW / f'{args.kind}-{len(attempts) + 1:02d}'
    out.mkdir(exist_ok=False)
    files = [Path('protocols/d1/d1-codebase-review-01.json'),
             Path('scripts/d1_codebase_review_run.py'), Path('scripts/d1_guard_frame_check.py'),
             Path('requirements-d1.txt')]
    files.extend(p for p in (ROOT / 'tests/d1/fixtures').rglob('*') if p.is_file())
    for folder, pattern in [('src/bindcheck_d1', '*.py'), ('tests/d1', '*.py'),
                            ('bindcheck', '*.js'), ('bindcheck/spec', '*.json'),
                            ('protocols/d1', '*')]:
        files.extend(p for p in (ROOT / folder).rglob(pattern) if p.is_file())
    if args.kind == 'guard':
        files.extend((ROOT / 'build/D1-03/v2-design/out').glob('*/*.json'))
    if args.kind == 'node':
        files.extend((ROOT / 'results/raw/T06/records').glob('*.json'))
    inputs = {}
    for p in sorted({(ROOT / p).resolve() for p in files}):
        rel = p.relative_to(ROOT)
        inputs[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
        if rel.parts[0] not in ('build', 'results'):
            dst = out / 'inputs' / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
    command = {'python': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/d1', '-v'],
               'node': ['node', '--test', 'bindcheck/test/checker.test.js'],
               'guard': [sys.executable, 'scripts/d1_guard_frame_check.py', '--output', str(out / 'outputs')]}[args.kind]
    execution_root = ROOT
    if args.kind == 'python':
        execution_root = out / 'workspace'
        execution_root.mkdir()
        for folder in ('src/bindcheck_d1', 'tests/d1'):
            shutil.copytree(ROOT / folder, execution_root / folder,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    env = dict(os.environ, PYTHONPATH=str(execution_root / 'src'),
               PYTHONDONTWRITEBYTECODE='1', GIT_OPTIONAL_LOCKS='0')
    if args.kind == 'guard':
        latest = json.loads((tests[-1].parent / 'freeze.json').read_text())
        for name, digest in latest['inputs'].items():
            if name.startswith(('src/', 'tests/')) and inputs.get(name) != digest:
                raise SystemExit('Code changed since passing controls')
    freeze = {'frozen_at_utc': now.isoformat(), 'python': sys.version,
              'node': subprocess.check_output(['node', '--version'], text=True).strip(),
              'command': command, 'cwd': str(execution_root), 'inputs': inputs,
              'seconds': 120, 'address_space_bytes': 4294967296}
    (out / 'freeze.json').write_text(json.dumps(freeze, indent=2) + '\n')

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))

    started = time.monotonic()
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        try:
            status = subprocess.run(command, cwd=execution_root, env=env, stdout=stdout, stderr=stderr,
                                    timeout=120, preexec_fn=limits).returncode
        except subprocess.TimeoutExpired:
            status = 124
    result = {'command': command, 'exit_status': status, 'wall_seconds': time.monotonic() - started}
    (out / 'execution.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
