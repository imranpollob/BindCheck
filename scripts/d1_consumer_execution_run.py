#!/usr/bin/env python3
"""Bounded, append-only runner for consumer-execution-01's frozen envelope."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-03/consumer-execution-01'
PROTOCOL = ROOT / 'protocols/d1/d1-03-consumer-execution-01.json'


def main():
    kind = sys.argv[1]
    frozen = (RAW / 'protocol.json').read_bytes()
    if PROTOCOL.read_bytes() != frozen:
        raise SystemExit('protocol changed')
    protocol = json.loads(frozen)
    limits = protocol['limits']
    elapsed = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(protocol['frozen_at_utc'])
    if elapsed.total_seconds() > limits['wall_minutes'] * 60:
        raise SystemExit('task wall limit exhausted')
    caps = {'python': limits['python_test_invocations'], 'artifact': limits['artifact_invocations'], 'forge': limits['forge_invocations']}
    count = len(list(RAW.glob(kind + '-[0-9][0-9]')))
    if count >= caps[kind]:
        raise SystemExit('attempt cap exhausted')
    out = RAW / f'{kind}-{count + 1:02d}'
    out.mkdir(exist_ok=False)
    snapshot = out / 'snapshot'
    files = sorted(set(p for folder in ('src/bindcheck_d1', 'tests/d1', 'scripts')
                       for p in (ROOT / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.sol')))
    hashes = {}
    for path in files:
        rel = path.relative_to(ROOT)
        dest = snapshot / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes(); dest.write_bytes(data)
        hashes[str(rel)] = hashlib.sha256(data).hexdigest()
    if kind == 'python':
        argv = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/d1', '-v']
    elif kind == 'artifact':
        argv = [sys.executable, 'scripts/d1_consumer_execution_check.py', '--output', str(out / 'outputs')]
    else:
        argv = ['/home/pollmix/.foundry/bin/forge', 'test', '--root', str(ROOT / 'build/D1-03/consumer-execution-01'), '--offline', '-vvvv']
    seconds = limits['seconds_per_forge'] if kind == 'forge' else limits['seconds_per_python_or_artifact']
    record = {'argv': argv, 'cwd': str(ROOT), 'input_sha256': hashes,
              'protocol_sha256': hashlib.sha256(frozen).hexdigest(),
              'wall_limit_seconds': seconds, 'address_space_bytes': limits['address_space_bytes'],
              'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out / 'start.json').write_text(json.dumps(record, indent=2) + '\n')
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (limits['address_space_bytes'],) * 2)

    start = time.monotonic()
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                   start_new_session=True, preexec_fn=cap)
        try:
            code = process.wait(timeout=seconds); timeout = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(); timeout = True
    record.update(exit=code, timeout=timeout, elapsed_seconds=time.monotonic() - start)
    record['logs'] = {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in ('stdout', 'stderr')}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'input_sha256'}, indent=2))
    print((out / 'stdout').read_text()[-3000:])
    print((out / 'stderr').read_text()[-4000:])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
