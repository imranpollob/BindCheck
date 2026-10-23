#!/usr/bin/env python3
"""Bounded append-only attempts with executable snapshots before each run."""
import argparse
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
import shutil

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'results/raw/D1-03/typed-bindings-01'


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('kind',choices=['artifacts','tests'])
    args=parser.parse_args()
    previous=list(RAW.glob(args.kind+'-*/freeze.json'))
    maximum=4 if args.kind=='artifacts' else 3
    if len(previous)>=maximum: raise SystemExit('Frozen attempt cap reached')
    attempt=RAW/f'{args.kind}-{len(previous)+1:02d}'; attempt.mkdir(exist_ok=False)
    paths=list((ROOT/'src/bindcheck_d1').rglob('*.py'))+list((ROOT/'tests/d1').glob('test_typed*.py'))
    paths += [Path(__file__),ROOT/'scripts/d1_03_typed_gate.py',ROOT/'metadata/d1/noir-typed-schema-01.json',
              ROOT/'protocols/d1/d1-03-typed-bindings-01.json']
    inputs={}
    for path in paths:
        rel=path.relative_to(ROOT);dest=attempt/'inputs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        inputs[str(rel)]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (ROOT/'build/D1-03/acir').glob('*'):
        if path.suffix=='.json' or path.name.endswith('.acir.txt'):
            inputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    argv=([sys.executable,'scripts/d1_03_typed_gate.py','--output',str((attempt/'outputs').relative_to(ROOT))]
          if args.kind=='artifacts' else [sys.executable,'-m','unittest','discover','-s','tests/d1','-p','test_typed*.py','-v'])
    record={'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(ROOT),
            'inputs':inputs,'python':sys.version,'limit_seconds':120,'address_space_bytes':4*1024**3,
            'environment_overrides':{'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1','GIT_OPTIONAL_LOCKS':'0'}}
    (attempt/'freeze.json').write_text(json.dumps(record,indent=2)+'\n')
    def limit():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    start=time.monotonic()
    with (attempt/'stdout').open('wb') as out,(attempt/'stderr').open('wb') as err:
        process=subprocess.Popen(argv,cwd=ROOT,env=dict(os.environ,**record['environment_overrides']),stdout=out,stderr=err,preexec_fn=limit,start_new_session=True)
        try: code=process.wait(timeout=120);timeout=False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);code=process.wait();timeout=True
    result={'exit':code,'timeout':timeout,'elapsed_seconds':time.monotonic()-start,'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (attempt/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(str(attempt.relative_to(ROOT)),result)


if __name__=='__main__': main()
