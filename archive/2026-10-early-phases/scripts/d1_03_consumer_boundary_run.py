#!/usr/bin/env python3
"""Freeze and record one consumer audit plus its prerequisite synthetic tests."""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'results/raw/D1-03/consumer-boundary-01'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-after-test-failure',action='store_true');args=parser.parse_args()
    suffix='-02' if args.resume_after_test_failure else ''
    if suffix:
        previous=json.loads((RAW/'execution.json').read_text())
        if previous['tests']['exit']==0 or 'audit' in previous:raise SystemExit('No authorized remaining test/audit slot')
    (RAW/('started'+suffix)).open('x').close()
    paths=[Path(__file__),ROOT/'scripts/d1_03_consumer_boundary.py',ROOT/'tests/d1/test_consumer_boundary.py',
           ROOT/'src/bindcheck_d1/frontends/consumer_boundary_v1.py',ROOT/'protocols/d1/d1-03-consumer-boundary-01.json']
    paths+=list((ROOT/'build/D1-03/v2-design/out').glob('*/*.json'))
    commands={'tests':[sys.executable,'-m','unittest','discover','-s','tests/d1','-p','test_consumer_boundary.py','-v'],
              'audit':[sys.executable,'scripts/d1_03_consumer_boundary.py']}
    freeze={'frozen_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,
            'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'commands':commands,
            'per_invocation_seconds':120,'address_space_bytes':4*1024**3}
    (RAW/('freeze'+suffix+'.json')).write_text(json.dumps(freeze,indent=2)+'\n')
    def limit():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    results={}
    for name,argv in commands.items():
        start=time.monotonic()
        if name=='audit':(RAW/'audit-started').open('x').close()
        with (RAW/(name+suffix+'.stdout')).open('xb') as out,(RAW/(name+suffix+'.stderr')).open('xb') as err:
            proc=subprocess.Popen(argv,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0'),stdout=out,stderr=err,start_new_session=True,preexec_fn=limit)
            try:code=proc.wait(timeout=120);timeout=False
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);code=proc.wait();timeout=True
        results[name]={'argv':argv,'exit':code,'timeout':timeout,'elapsed_seconds':time.monotonic()-start}
        if code!=0:break
    (RAW/('execution'+suffix+'.json')).write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))


if __name__=='__main__':main()
