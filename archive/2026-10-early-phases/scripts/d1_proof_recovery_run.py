#!/usr/bin/env python3
"""Append-only runner for the frozen proof-recovery-01 envelope (Linux)."""
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
RAW = ROOT / 'results/raw/D1-03/proof-recovery-01'
PROTOCOL = ROOT / 'protocols/d1/d1-03-proof-recovery-01.json'
CATEGORIES = {
    'setup': ('setup_commands', 'setup_timeout_seconds'),
    'build': ('build_attempts', 'build_timeout_seconds'),
    'prove': ('honest_chain_attempts', 'honest_chain_timeout_seconds'),
    'verify': ('native_verify_controls', 'native_verify_timeout_seconds'),
    'forge': ('forge_attempts', 'forge_timeout_seconds'),
    'check': ('other_checks', 'other_check_timeout_seconds'),
}


def main():
    category, *argv = sys.argv[1:]
    if argv and argv[0] == '--':
        argv.pop(0)
    if category not in CATEGORIES or not argv:
        raise SystemExit('category and command required')
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert digest == (RAW / 'protocol.sha256').read_text().strip(), 'protocol changed'
    protocol = json.loads(PROTOCOL.read_text())
    frozen = datetime.datetime.fromisoformat(protocol['frozen_utc']).timestamp()
    left = frozen + protocol['bounds']['task_wall_seconds'] - time.time()
    if left <= 0:
        raise SystemExit('task wall budget exhausted')
    count_key, timeout_key = CATEGORIES[category]
    number = len(list(RAW.glob(f'{category}-[0-9][0-9]'))) + 1
    if number > protocol['bounds'][count_key]:
        raise SystemExit('attempt budget exhausted')
    directory = RAW / f'{category}-{number:02d}'
    directory.mkdir(exist_ok=False)
    timeout = min(protocol['bounds'][timeout_key], left)
    limit = protocol['bounds']['process_address_space_bytes']

    def child_limits():
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.time()
    record = {'argv': argv, 'cwd': os.getcwd(), 'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeout_s': timeout, 'address_space_limit_bytes': limit, 'protocol_sha256': digest,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'environment': {k: os.environ.get(k) for k in ('PATH', 'CARGO_TARGET_DIR', 'CARGO_BUILD_JOBS',
                  'RUSTFLAGS', 'RUST_MIN_STACK', 'TS_RS_EXPORT_DIR', 'T13_OUT_DIR', 'D1_REAL_BB', 'D1_CAPTURE_DIR',
                  'LIBCLANG_PATH', 'LD_LIBRARY_PATH', 'BINDGEN_EXTRA_CLANG_ARGS', 'HARDWARE_CONCURRENCY',
                  'RAYON_NUM_THREADS', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')}}
    (directory / 'runner.py').write_bytes(Path(__file__).read_bytes())
    (directory / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    timed_out = False
    with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
        try:
            proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=child_limits)
        except OSError as error:
            stderr.write((str(error)+'\n').encode())
            code = 127
            record['launch_error'] = str(error)
        else:
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait()
    record.update(exit_status=code, timed_out=timed_out, elapsed_s=time.time()-started,
                  max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (directory / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'directory': str(directory.relative_to(ROOT)), 'exit': code,
                      'elapsed_s': record['elapsed_s'], 'timed_out': timed_out}), flush=True)
    return 124 if timed_out else (code if code >= 0 else 128-code)


if __name__ == '__main__':
    sys.exit(main())
