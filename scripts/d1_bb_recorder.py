#!/usr/bin/env python3
"""Linux bb recorder: real pinned executable, unchanged proof inputs, local CRS.

Installed as `bb` on PATH only for the frozen honest-chain attempt. Refuses a
fifth prove call. Copies ephemeral input/output bytes before their Rust owners
delete them. No proof or verification result is substituted.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

cap = Path(os.environ['D1_CAPTURE_DIR'])
cap.mkdir(parents=True, exist_ok=True)
args = sys.argv[1:]
with (cap / 'counter.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    prior = list(cap.glob('[0-9][0-9][0-9]-*'))
    if args[0] == 'prove' and sum(p.name.endswith('-prove') for p in prior) >= 4:
        raise SystemExit('frozen prove-call limit reached')
    dest = cap / f'{len(prior)+1:03d}-{args[0]}'
    dest.mkdir(exist_ok=False)

def option(name):
    return Path(args[args.index(name)+1]) if name in args else None

def copy_file(flag, name):
    p = option(flag)
    if p and p.is_file():
        shutil.copy2(p, dest / name)

for flag, name in (('-b', 'program.json'), ('-w', 'witness.gz'), ('-k', 'key'),
                   ('-p', 'proof_in'), ('-i', 'public_inputs_in')):
    copy_file(flag, name)
crs = cap.parent / 'crs'
crs.mkdir(exist_ok=True)
command = [os.environ['D1_REAL_BB'], '-c', str(crs), *args]
(dest / 'command.json').write_text(json.dumps({'harness_argv': args, 'actual_argv': command,
    'only_argument_addition': 'explicit local CRS directory',
    'bb_sha256': hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()}, indent=2)+'\n')
started = time.monotonic()
with (dest / 'stdout.log').open('wb') as out, (dest / 'stderr.log').open('wb') as err:
    code = subprocess.call(command, stdout=out, stderr=err)
output = option('-o')
if output and output.is_dir():
    shutil.copytree(output, dest / 'out')
record = {'exit_status': code, 'elapsed_s': time.monotonic()-started,
          'max_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
(dest / 'result.json').write_text(json.dumps(record, indent=2)+'\n')
for name, stream in (('stdout.log', sys.stdout.buffer), ('stderr.log', sys.stderr.buffer)):
    stream.write((dest / name).read_bytes())
sys.exit(code if code >= 0 else 128-code)
