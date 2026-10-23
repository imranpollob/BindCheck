#!/usr/bin/env python3
"""One-shot bounded validation and actual-artifact inventory for extraction 01."""
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
import Crypto

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'results/raw/D1-03/v2-extraction-01'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(name, data):
    (RAW/name).write_text(json.dumps(data, indent=2)+'\n')


def run(name, argv):
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    env = dict(os.environ, PYTHONPATH=str(ROOT/'src'), PYTHONDONTWRITEBYTECODE='1', GIT_OPTIONAL_LOCKS='0')
    record = {'argv':argv,'cwd':str(ROOT),'environment_overrides':{k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','GIT_OPTIONAL_LOCKS')},
              'started_at_utc':now(),'wall_limit_seconds':120,'address_space_bytes':4*1024**3}
    start=time.monotonic()
    with (RAW/(name+'.stdout')).open('wb') as out, (RAW/(name+'.stderr')).open('wb') as err:
        proc=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True,preexec_fn=limit)
        try:
            record['exit']=proc.wait(timeout=120);record['timeout']=False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);record['exit']=proc.wait();record['timeout']=True
    record.update(elapsed_seconds=time.monotonic()-start,finished_at_utc=now())
    record['outputs']={str(p.relative_to(ROOT)):digest(p) for p in [RAW/(name+'.stdout'),RAW/(name+'.stderr')]}
    save(name+'.json',record)
    return record


def main():
    with (RAW/'run-started.json').open('x') as guard:
        json.dump({'started_at_utc':now()},guard)
    paths=list((ROOT/'src/bindcheck_d1').rglob('*.py'))
    paths += [ROOT/'tests/d1/test_v2_core.py', Path(__file__), ROOT/'scripts/d1_03_v2_extraction_gate.py',
              ROOT/'protocols/d1/d1-03-v2-extraction-01.json',ROOT/'protocols/d1/d1-03-joint-semantics-v2.json',
              ROOT/'protocols/d1/d1-03-joint-semantics-v2.md',
              ROOT/'build/D1-03/v2-design/out/RollupV1.sol/RollupV1.json',
              ROOT/'build/D1-03/consumer/src/rollup3/RollupV1.sol',
              ROOT/'results/raw/D1-03/setup/21_producer_hashes.txt']
    paths += list((ROOT/'build/D1-03/acir').glob('*.acir.txt'))
    paths += list((ROOT/'build/D1-03/acir').glob('*.program.json'))
    historical={}
    for line in (ROOT/'results/raw/D1-03/setup/21_producer_hashes.txt').read_text().splitlines():
        expected,path=line.split(None,1)
        historical[path]=digest(ROOT/path)==expected
    if not all(historical.values()):
        save('setup-mismatch.json',historical)
        raise SystemExit('Inherited compilation hash mismatch; no tests or gate run')
    test=[sys.executable,'-m','unittest','discover','-s','tests/d1','-p','test_v2_core.py','-v']
    audit=[sys.executable,'scripts/d1_03_v2_extraction_gate.py','--output','results/raw/D1-03/v2-extraction-01/artifacts']
    save('execution-freeze.json',{'frozen_at_utc':now(),'python':sys.version,'python_executable_sha256':digest(Path(sys.executable)),
                                'pycryptodome_version':Crypto.__version__,'inputs':{str(p.relative_to(ROOT)):digest(p) for p in paths},
                                'historical_compile_hash_checks':historical,'commands':{'tests':test,'artifact_gate':audit},
                                'primary_queries':0})
    tests=run('tests',test)
    gate=run('gate',audit) if tests['exit']==0 else {'not_run':'synthetic regressions failed'}
    save('run-summary.json',{'tests':tests,'gate':gate,'primary_queries':0,'new_proofs':0,'full_replays':0})
    print(json.dumps({'tests_exit':tests['exit'],'gate_exit':gate.get('exit'),'gate_not_run':gate.get('not_run')}))


if __name__=='__main__':
    main()
