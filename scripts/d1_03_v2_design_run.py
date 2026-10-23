#!/usr/bin/env python3
"""One-shot, offline component validation for the frozen D1-03 v2 design task."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-03/v2-design'
BUILD = ROOT / 'build/D1-03/v2-design'
FORGE = Path('/home/pollmix/.foundry/bin/forge')
SOLC = Path('/home/pollmix/.local/share/svm/0.8.20/solc-0.8.20')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def run(name, argv, seconds, memory=None):
    def limits():
        if memory:
            resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    record = {'argv': argv, 'cwd': str(ROOT), 'started_at_utc': now(),
              'wall_limit_seconds': seconds, 'address_space_bytes': memory}
    start = time.monotonic()
    with (RAW / (name + '.stdout')).open('wb') as out, (RAW / (name + '.stderr')).open('wb') as err:
        proc = subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=err,
                                start_new_session=True, preexec_fn=limits)
        try:
            record['exit'] = proc.wait(timeout=seconds)
            record['timeout'] = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            record['exit'] = proc.wait()
            record['timeout'] = True
    record.update(elapsed_seconds=time.monotonic()-start, finished_at_utc=now())
    for stream in ('stdout', 'stderr'):
        p = RAW / (name + '.' + stream)
        record[stream] = {'path': str(p.relative_to(ROOT)), 'sha256': digest(p)}
    dump(RAW / (name + '.json'), record)
    return record


def main():
    # This immutable guard consumes the single permitted invocation even if a
    # later setup/build step fails. Never overwrite or retry in this namespace.
    with (RAW / 'run-started.json').open('x') as guard:
        json.dump({'started_at_utc': now()}, guard)
    BUILD.mkdir(parents=True, exist_ok=False)
    (BUILD / 'src').mkdir()
    remaps = [
        'payy/=' + str(ROOT / 'build/D1-03/consumer/src') + '/',
        '@openzeppelin/contracts/=' + str(ROOT / 'tools/oz-5.0.1/contracts') + '/',
        '@openzeppelin/contracts-upgradeable/=' + str(ROOT / 'tools/oz-5.0.1/upgradeable') + '/',
    ]
    config = ('[profile.default]\nsrc = "src"\n'
              + 'test = ' + json.dumps(str(ROOT / 'tests/d1/v2')) + '\n'
              + 'out = "out"\ncache_path = "cache"\nlibs = []\n'
              + 'solc = ' + json.dumps(str(SOLC)) + '\noffline = true\n'
              + 'evm_version = "shanghai"\nvia_ir = true\noptimizer = true\noptimizer_runs = 200\nast = true\n'
              + 'remappings = ' + json.dumps(remaps) + '\n')
    (BUILD / 'foundry.toml').write_text(config)
    inputs = [Path(__file__), ROOT / 'scripts/d1_03_v2_policy_checks.py',
              ROOT / 'tests/d1/v2/TransferConditions.t.sol', BUILD / 'foundry.toml']
    inputs += list((ROOT / 'protocols/d1').glob('d1-03-*.json'))
    inputs += list((ROOT / 'protocols/d1').glob('d1-03-*.md'))
    for directory in ('build/D1-03/consumer/src', 'tools/oz-5.0.1/contracts', 'tools/oz-5.0.1/upgradeable'):
        inputs += list((ROOT / directory).rglob('*.sol'))
    versions = {}
    for name, argv in [('forge', [str(FORGE), '--version']), ('solc', [str(SOLC), '--version']),
                       ('python', ['python3', '--version'])]:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        versions[name] = {'argv': argv, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    dump(RAW / 'validation-freeze.json', {
        'frozen_at_utc': now(), 'versions': versions,
        'tool_hashes': {str(p): digest(p) for p in (FORGE, SOLC)},
        'inputs': {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(inputs))},
        'validation_not_primary': True,
        'commands': {'forge': [str(FORGE), 'test', '--root', str(BUILD), '--offline', '-vvvv'],
                     'python': ['python3', 'scripts/d1_03_v2_policy_checks.py']}})
    forge = run('forge', [str(FORGE), 'test', '--root', str(BUILD), '--offline', '-vvvv'],
                600, 4 * 1024**3)
    policy = run('policy', ['python3', 'scripts/d1_03_v2_policy_checks.py'], 60)
    dump(RAW / 'validation-summary.json', {'forge': forge, 'policy': policy,
                                           'finished_at_utc': now(), 'primary_queries': 0})
    print(json.dumps({'forge_exit': forge['exit'], 'policy_exit': policy['exit']}))


if __name__ == '__main__':
    main()
