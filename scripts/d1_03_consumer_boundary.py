#!/usr/bin/env python3
"""One-shot full-transition coverage audit, not a settlement execution."""
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bindcheck_d1.frontends.consumer_boundary_v1 import load_boundaries


def main():
    raw=ROOT/'results/raw/D1-03/consumer-boundary-01/artifacts'
    raw.mkdir(exist_ok=False)
    boundary,artifacts=load_boundaries(ROOT/'build/D1-03/v2-design/out')
    entries=[n for n in boundary.nodes.values() if n['nodeType']=='FunctionDefinition' and n['name']=='verifyRollup']
    if len(entries)!=1:raise RuntimeError('entry must be unambiguous')
    result=boundary.audit(entries[0]['id'])
    (raw/'transition-boundary.json').write_text(json.dumps(result,indent=2)+'\n')
    (raw/'artifact-identities.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    summary={'security_verdict':'UNKNOWN','complete_transition_implemented':False,
             'functions':[x['function'] for x in result['functions']],
             'call_categories':dict(Counter(x['kind'] for x in result['calls'])),
             'loops':[{'function':x['function'],'condition':x['condition']['excerpt'] if x['condition'] else None} for x in result['loops']],
             'state_writes':[{'function':x['function'],'roots':x['roots'],'expression':x['location']['excerpt']} for x in result['state_writes']],
             'crypto_builtins':[{'function':x['function'],'name':x['name']} for x in result['calls'] if x['kind']=='builtin' and x.get('name') in ('keccak256','ecrecover')],
             'unresolved':['Validator/signature loops have no numeric bounds in v2 and no implemented preservation-checked summary',
                           'Full transition semantics, including internal library reverts and external-call outcomes, remain unimplemented',
                           'AST call inventory and message-helper tests do not discharge these obligations'],
             'primary_queries':0,'replays':0}
    (raw/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
