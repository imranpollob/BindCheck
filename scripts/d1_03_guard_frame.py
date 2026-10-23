#!/usr/bin/env python3
"""One pinned-artifact local frame check; no full-transition verdict."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bindcheck_d1.frontends.consumer_boundary_v1 import load_boundaries, walk
from bindcheck_d1.frontends.guard_frame_v1 import check_guard, check_use_site, validate_reuse
from bindcheck_d1.model_v2 import Unsupported


def main():
    out=ROOT/'results/raw/D1-03/guard-frame-01/artifacts';out.mkdir(exist_ok=False)
    boundary,identities=load_boundaries(ROOT/'build/D1-03/v2-design/out')
    def one(kind,name):
        found=[n for n in boundary.nodes.values() if n['nodeType']==kind and n.get('name')==name]
        if len(found)!=1:raise Unsupported('FRAME_UNAMBIGUOUS_SELECTION_REQUIRED',name)
        return found[0]
    entry=one('FunctionDefinition','verifyRollup');guard=one('FunctionDefinition','verifyValidatorSignatures')
    # This task checks all state except the explicitly retained validator index;
    # it does not discard that index or claim complete protocol-state equivalence.
    retained=one('VariableDeclaration','validatorSetIndex')['id']
    protected=sorted(n['id'] for n in boundary.nodes.values() if n.get('stateVariable') and n['id']!=retained)
    calls=[n for n in walk(entry['body']) if n['nodeType']=='FunctionCall' and n['expression'].get('referencedDeclaration')==guard['id']]
    if len(calls)!=1:raise Unsupported('FRAME_UNAMBIGUOUS_USE_SITE_REQUIRED','validator guard')
    policy=ROOT/'protocols/d1/d1-03-joint-semantics-v2.md';bounds=ROOT/'protocols/d1/d1-03-joint-semantics-v2.json';assumptions=ROOT/'protocols/d1/d1-03-joint-semantics.md'
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    context={'policy_sha256':h(policy),'bounds_sha256':h(bounds),'assumptions_sha256':h(assumptions)}
    frame=check_guard(boundary,guard['id'],protected)
    cert=check_use_site(boundary,entry['id'],calls[0]['id'],frame,context)
    validate_reuse(boundary,cert,context)
    (out/'certificate.json').write_text(json.dumps(cert,indent=2)+'\n')
    (out/'artifact-identities.json').write_text(json.dumps(identities,indent=2)+'\n')
    summary={'frame_check':'PASS','security_verdict':'UNKNOWN','complete_consumer_transition':False,
             'guard_bodies':[boundary.nodes[i]['name'] for i in frame['closure']],
             'may_write':[{'id':i,'name':boundary.nodes[i]['name']} for i in frame['may_write_roots']],
             'protected_root_count':len(protected),'loops':frame['loops'],
             'call_bindings':cert['payload']['bindings'],'cache_key':cert['cache_key'],
             'guard_acceptance':'NOT_ESTABLISHED','non_vacuity':'NOT_ESTABLISHED',
             'remaining':['Symbolic full transition and rollback including retained validator state',
                          'Exact message-effect transition and external verifier/token boundary composition',
                          'Producer relation composition, direct queries, original-consumer candidate replay and repair/non-vacuity gates'],
             'primary_queries':0,'replays':0}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
