#!/usr/bin/env python3
"""Bounded append-only runner: two tests and one artifact check, never overwrite."""
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

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'results/raw/D1-03/guard-frame-01'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['tests','artifacts']);args=ap.parse_args()
    maximum={'tests':2,'artifacts':1}[args.kind]
    number=1+len(list(RAW.glob(args.kind+'-[0-9][0-9]')))
    if number>maximum:raise SystemExit('frozen attempt cap exhausted')
    if args.kind=='artifacts':
        outcomes=[json.loads(p.read_text()) for p in RAW.glob('tests-*/execution.json')]
        if not outcomes or outcomes[-1]['exit_status']!=0:raise SystemExit('passing synthetic controls required')
    protocol=json.loads((ROOT/'protocols/d1/d1-03-guard-frame-01.json').read_text())
    now=datetime.datetime.now(datetime.timezone.utc)
    started=datetime.datetime.fromisoformat(protocol['frozen_at_utc'])
    if (now-started).total_seconds()>45*60:raise SystemExit('frozen wall budget exhausted')
    out=RAW/f'{args.kind}-{number:02d}';out.mkdir(exist_ok=False)
    files=[Path(p) for p in ['scripts/d1_03_guard_frame_run.py','scripts/d1_03_guard_frame.py','tests/d1/test_guard_frame.py','protocols/d1/d1-03-guard-frame-01.json','protocols/d1/d1-03-joint-semantics.md','protocols/d1/d1-03-joint-semantics-v2.md','protocols/d1/d1-03-joint-semantics-v2.json']]
    files+=sorted(Path('src/bindcheck_d1').rglob('*.py'))
    if args.kind=='artifacts':files+=sorted(Path('build/D1-03/v2-design/out').glob('*/*.json'))
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for p in files:
        if str(p).startswith('build/'):continue
        dst=out/'inputs'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    command=([sys.executable,'-m','unittest','discover','-s','tests/d1','-p','test_guard_frame.py','-v'] if args.kind=='tests' else [sys.executable,'scripts/d1_03_guard_frame.py'])
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0')
    freeze={'frozen_at_utc':now.isoformat(),'python':sys.version,'command':command,'cwd':str(ROOT),'inputs':hashes,'timeout_seconds':120,'address_space_bytes':4294967296}
    (out/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    def limits():resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
    start=time.monotonic()
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        try:code=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=120,preexec_fn=limits).returncode
        except subprocess.TimeoutExpired:code=124
    result={'command':command,'exit_status':code,'wall_seconds':time.monotonic()-start}
    (out/'execution.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(code)


if __name__=='__main__':main()
