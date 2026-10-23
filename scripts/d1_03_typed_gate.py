#!/usr/bin/env python3
"""Versioned actual-artifact decoding/binding gate; no primary queries."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bindcheck_d1.frontends.acir_binary_v1 import decode, abi_bindings
from bindcheck_d1.frontends.acir_bindings_v1 import certify_bindings
from bindcheck_d1.frontends.binding_certificate_check_v1 import verify_tree
from bindcheck_d1.frontends.acir_v2 import inventory
from bindcheck_d1.model_v2 import Unsupported


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); args.output.mkdir(exist_ok=False)
    pins=json.loads((ROOT/'metadata/d1/noir-typed-schema-01.json').read_text())
    for path,expected in pins['source_files_sha256'].items():
        if hashlib.sha256((ROOT/pins['source_root']/path).read_bytes()).hexdigest()!=expected:
            raise Unsupported('COMPILER_SCHEMA_SOURCE_CHANGED',path)
    rows=[]
    for revision in ('A','B'):
        for layer in ('agg_agg','agg_final'):
            name=f'{revision}-1000-{layer}'
            try:
                program=decode(ROOT/f'build/D1-03/acir/{name}.program.json')
                circuit=program['functions'][0]
                bindings=abi_bindings(program['abi'],circuit)
                recs=[dict(op,opcode_index=i) for i,op in enumerate(circuit['opcodes']) if op['kind']=='RecursiveAggregation']
                # Compare only boundary witnesses. The printout is explicitly
                # non-transformed; its assertion list is NOT the binary relation.
                printed=inventory(ROOT/f'build/D1-03/acir/{name}.acir.txt',ROOT/f'build/D1-03/acir/{name}.program.json')
                for key, label in [('private_parameters','private parameters'),('public_parameters','public parameters'),('return_values','return values')]:
                    if circuit[key]!=list(printed['declarations'][label]):
                        raise Unsupported('PRINTED_BINARY_DECLARATION_MISMATCH',label)
                if len(recs)!=len(printed['recursive_calls']):raise Unsupported('PRINTED_RECURSION_COUNT_MISMATCH','')
                for rec,call in zip(recs,printed['recursive_calls']):
                    flat=rec['verification_key']+rec['proof']+rec['public_inputs']+[rec['key_hash'],rec['predicate']]
                    if flat!=[{'witness':w} for w in call['flattened_witnesses']]:
                        raise Unsupported('PRINTED_BINARY_RECURSION_MISMATCH','')
                bindings_certificate=certify_bindings(program,bindings)
                checked=verify_tree(circuit,bindings_certificate)
                (args.output/(name+'-certificates.json')).write_text(json.dumps(bindings_certificate)+'\n')
                detail={'identity':program['identity'],'abi_bindings':bindings,'recursive_calls':recs,
                        'opcode_counts':dict(Counter(op['kind'] for op in circuit['opcodes'])),
                        'unconstrained_functions':[{'name':f['function_name'],'instructions':len(f['bytecode'])} for f in program['unconstrained_functions']]}
                (args.output/(name+'.json')).write_text(json.dumps(detail,indent=2)+'\n')
                rows.append({'name':name,'decoded':True,'abi_binding':True,'binding_certificates_checked':checked,
                             'printed_boundary_correspondence':True,'recursive_calls':len(recs),
                             'shapes':[{'verification_key':len(r['verification_key']),'proof':len(r['proof']),
                                        'public_inputs':len(r['public_inputs']),'proof_type':r['proof_type'],
                                        'predicate':r['predicate']} for r in recs],
                             'opcode_counts':detail['opcode_counts'],'unconstrained_functions':detail['unconstrained_functions']})
            except Unsupported as error:
                rows.append({'name':name,'decoded':False,'reason':error.reason,'detail':str(error)})
    result={'scope':'typed artifact and ABI bindings only; no joint verdict','rows':rows,'primary_queries':0}
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if all(row['decoded'] for row in rows) else 2


if __name__=='__main__':
    raise SystemExit(main())
