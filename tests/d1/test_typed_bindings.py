"""Typed decoder/certificate controls; all fixtures are synthetic or pinned upstream tests."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import unittest

from bindcheck_d1.frontends.acir_binary_v1 import Reader, abi_bindings, MAX_ITEMS
from bindcheck_d1.frontends.acir_bindings_v1 import Certificates, add, mul, constant, witness, certify_bindings
from bindcheck_d1.frontends.binding_certificate_check_v1 import verify, verify_tree
from bindcheck_d1.model_v2 import FIELD_MODULUS as P, Unsupported

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tests/d1/fixtures/noir_serialization'


def snapshot(name):
    source=SOURCE/'test_program_serialization.rs'
    provenance=json.loads((SOURCE/'provenance.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=provenance['excerpt_sha256']:
        raise ValueError('Pinned upstream fixture identity mismatch')
    text=source.read_text()
    block=text.split('fn '+name+'()',1)[1].split('\nfn ',1)[0]
    values=re.search(r'assert_compact_debug_snapshot!\(bytes, @"(\[.*?\])"\)',block).group(1)
    return gzip.decompress(bytes(json.loads(values)))


def op(poly):
    return {'kind':'AssertZero','expression':{'mul':[[c,*m] for m,c in poly.items() if len(m)==2],
                                            'linear':[[c,m[0]] for m,c in poly.items() if len(m)==1],
                                            'constant':poly.get((),0)}}


class BinaryTests(unittest.TestCase):
    def test_upstream_addition_golden(self):
        circuit=Reader(snapshot('addition_circuit')).program()['functions'][0]
        self.assertEqual(circuit['private_parameters'],[1,2])
        self.assertEqual(circuit['return_values'],[3])
        self.assertEqual(circuit['opcodes'][0]['expression'],
                         {'mul':[],'linear':[[1,1],[1,2],[P-1,3]],'constant':0})

    def test_upstream_unsupported_msm_is_rejected(self):
        with self.assertRaises(Unsupported):
            Reader(snapshot('multi_scalar_mul_circuit')).program()

    def test_upstream_foreign_call_is_rejected(self):
        with self.assertRaises(Unsupported):
            Reader(snapshot('simple_brillig_foreign_call')).program()

    def test_every_truncation_of_upstream_golden_is_rejected(self):
        data=snapshot('addition_circuit')
        for size in range(len(data)):
            with self.subTest(size=size),self.assertRaises(Unsupported):Reader(data[:size]).program()

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(Unsupported):Reader(snapshot('addition_circuit')+b'\0').program()

    def test_noncanonical_field_rejected(self):
        with self.assertRaises(Unsupported):Reader(struct.pack('<Q',32)+P.to_bytes(32,'big')).field()

    def test_little_endian_field_not_silently_reduced(self):
        self.assertEqual(Reader(struct.pack('<Q',32)+(1).to_bytes(32,'big')).field(),1)
        self.assertEqual(Reader(struct.pack('<Q',32)+(1).to_bytes(32,'little')).field(),2**248)

    def test_collection_cap_before_allocation(self):
        with self.assertRaises(Unsupported):Reader(struct.pack('<Q',MAX_ITEMS+1)).vec(lambda:None)

    def test_typed_recursion_layout_with_distinct_lengths(self):
        # Hand-authored legacy-bincode shape, not serialized by production code.
        u32=lambda n:struct.pack('<I',n);u64=lambda n:struct.pack('<Q',n)
        inputs=lambda values:u64(len(values))+b''.join(u32(1)+u32(v) for v in values)
        data=u32(11)+inputs([10,11])+inputs([20])+inputs([30,31,32])+u32(1)+u32(40)+u32(7)+u32(0)+u64(32)+(1).to_bytes(32,'big')
        result=Reader(data).blackbox()
        self.assertEqual(result['verification_key'],[{'witness':10},{'witness':11}])
        self.assertEqual(result['proof'],[{'witness':20}])
        self.assertEqual(result['public_inputs'],[{'witness':30},{'witness':31},{'witness':32}])
        self.assertEqual((result['key_hash'],result['proof_type'],result['predicate']),({'witness':40},7,{'constant':1}))

    def test_unknown_enum_tag_rejected(self):
        with self.assertRaises(Unsupported):Reader(struct.pack('<I',99)).opcode()


class AbiTests(unittest.TestCase):
    def fixture(self):
        abi={'parameters':[{'name':'a','visibility':'public','type':{'kind':'field'}},
                           {'name':'b','visibility':'private','type':{'kind':'struct','fields':[
                               {'name':'x','type':{'kind':'array','length':2,'type':{'kind':'field'}}},
                               {'name':'y','type':{'kind':'boolean'}}]}},
                           {'name':'c','visibility':'public','type':{'kind':'field'}}],'return_type':None}
        circuit={'public_parameters':[0,4],'private_parameters':[1,2,3],'return_values':[]}
        return abi,circuit

    def test_interleaved_visibility_and_nested_fields(self):
        table=abi_bindings(*self.fixture())
        self.assertEqual(table['b.x'],[1,2]);self.assertEqual(table['c'],[4])

    def test_changed_declaration_identity_rejected(self):
        abi,circuit=self.fixture();circuit['public_parameters']=[0,5]
        with self.assertRaises(Unsupported):abi_bindings(abi,circuit)

    def test_reordered_struct_fields_not_hidden(self):
        abi,circuit=self.fixture();table=abi_bindings(abi,circuit)
        abi['parameters'][1]['type']['fields'].reverse()
        changed=abi_bindings(abi,circuit)
        self.assertNotEqual(table['b.x'],changed['b.x'])

    def test_return_mapping_not_guessed(self):
        abi,circuit=self.fixture();circuit['return_values']=[8]
        with self.assertRaises(Unsupported):abi_bindings(abi,circuit)


class CertificateTests(unittest.TestCase):
    def test_split_mux_is_certified_and_independently_checked(self):
        z,a,b,out,aux=map(witness,(0,1,2,3,4))
        first=add(aux,mul(b,z),-1)
        second=add(add(add(out,mul(a,z),-1),aux),b,-1)
        circuit={'opcodes':[op(first),op(second)]}
        goal=add(out,add(mul(a,z),mul(add(constant(1),z,-1),b)),-1)
        certificate=Certificates(circuit).prove(goal,3)
        self.assertEqual(len(certificate['linear_combination']),2)
        self.assertTrue(verify(circuit,certificate))

    def test_missing_constraint_is_not_filled_in(self):
        circuit={'opcodes':[op(add(witness(4),mul(witness(2),witness(0)),-1))]}
        with self.assertRaises(Unsupported):Certificates(circuit).prove(add(witness(3),witness(1),-1),3)

    def test_corrupt_coefficient_rejected(self):
        circuit={'opcodes':[op(add(witness(1),witness(2),-1))]}
        proof=Certificates(circuit).prove(add(witness(1),witness(2),-1),1)
        proof['linear_combination'][0][1]+=1
        with self.assertRaises(Unsupported):verify(circuit,proof)

    def test_non_assert_reference_rejected(self):
        with self.assertRaises(Unsupported):verify({'opcodes':[{'kind':'BrilligCall'}]}, {'goal':[], 'linear_combination':[[0,1]]})

    def test_zero_test_requires_both_constraints(self):
        r,z,inv=map(witness,(0,1,2))
        annihilator=op(mul(r,z));inverse=op(add(add(mul(r,inv),z),constant(-1)))
        good=Certificates({'opcodes':[annihilator,inverse]}).zero_test(0)
        self.assertEqual(good['selector'],1)
        for incomplete in ([annihilator],[inverse]):
            with self.assertRaises(Unsupported):Certificates({'opcodes':incomplete}).zero_test(0)

    def test_circular_definition_is_not_a_proof(self):
        circuit={'opcodes':[op(add(witness(1),witness(2),-1)),op(add(witness(2),witness(1),-1))]}
        with self.assertRaises(Unsupported):Certificates(circuit).prove(witness(1),1)

    def test_duplicate_certificate_monomials_rejected(self):
        with self.assertRaises(Unsupported):verify({'opcodes':[]},{'goal':[[[0],1],[[0],P-1]],'linear_combination':[]})


class FrameTests(unittest.TestCase):
    def fixture(self):
        table={'proofs':[],'verification_key_hash':[0,1]};cursor=2;operations=[]
        for frame in range(2):
            for name,count in [('proof',1),('old_root',1),('new_root',1),('commit_hash',1),('messages',1),('verification_key',1),('verification_key_hash',1)]:
                table[f'proofs[{frame}].{name}']=list(range(cursor,cursor+count));cursor+=count
        selectors=[]
        for frame in range(2):
            root=table[f'proofs[{frame}].old_root'][0];z=cursor;inv=cursor+1;cursor+=2;selectors.append(z)
            operations.extend([op(mul(witness(root),witness(z))),op(add(add(mul(witness(root),witness(inv)),witness(z)),constant(-1)))])
        logical=lambda frame:[0,1]+sum([table[f'proofs[{frame}].'+name] for name in ['old_root','new_root','commit_hash','messages']],[])
        def fi(w):return {'witness':w}
        for frame in range(2):
            z=witness(selectors[frame])
            def mux(active,padding):
                nonlocal cursor
                if active==padding:return fi(active)
                out=cursor;cursor+=1
                wanted=add(mul(z,witness(padding)),mul(add(constant(1),z,-1),witness(active)))
                operations.append(op(add(witness(out),wanted,-1)))
                return fi(out)
            proof=[mux(table[f'proofs[{frame}].proof'][0],table['proofs[0].proof'][0])]
            public=[mux(a,b) for a,b in zip(logical(frame),logical(0))]
            operations.append({'kind':'RecursiveAggregation','verification_key':[fi(table[f'proofs[{frame}].verification_key'][0])],
                               'proof':proof,'public_inputs':public,'key_hash':fi(table[f'proofs[{frame}].verification_key_hash'][0]),
                               'predicate':{'constant':1},'proof_type':7,'byte_range':[0,0]})
        return {'functions':[{'opcodes':operations}],'identity':{'fixture':'SYNTHETIC'}},table

    def test_active_padding_and_distinct_occurrences(self):
        program,table=self.fixture();result=certify_bindings(program,table)
        self.assertEqual([b['logical_frame'] for b in result['bindings']],[0,1])
        self.assertGreater(verify_tree(program['functions'][0],result),0)

    def test_recursive_call_order_is_not_frame_identity(self):
        program,table=self.fixture();ops=program['functions'][0]['opcodes']
        indices=[i for i,op in enumerate(ops) if op['kind']=='RecursiveAggregation']
        ops[indices[0]],ops[indices[1]]=ops[indices[1]],ops[indices[0]]
        result=certify_bindings(program,table)
        self.assertEqual(result['bindings'][0]['recursive_opcode'],indices[1])

    def test_changed_padding_vector_rejected(self):
        program,table=self.fixture();rec=[op for op in program['functions'][0]['opcodes'] if op['kind']=='RecursiveAggregation'][1]
        rec['public_inputs'][-1]={'witness':table['proofs[1].messages'][0]}
        with self.assertRaises(Unsupported):certify_bindings(program,table)

    def test_disabled_recursive_call_rejected(self):
        program,table=self.fixture()
        next(op for op in program['functions'][0]['opcodes'] if op['kind']=='RecursiveAggregation')['predicate']={'constant':0}
        with self.assertRaises(Unsupported):certify_bindings(program,table)

    def test_changed_key_association_rejected(self):
        program,table=self.fixture()
        next(op for op in program['functions'][0]['opcodes'] if op['kind']=='RecursiveAggregation')['verification_key']=[{'witness':99}]
        with self.assertRaises(Unsupported):certify_bindings(program,table)

    def test_changed_proof_type_rejected(self):
        program,table=self.fixture()
        next(op for op in program['functions'][0]['opcodes'] if op['kind']=='RecursiveAggregation')['proof_type']=9
        with self.assertRaises(Unsupported):certify_bindings(program,table)


if __name__=='__main__':unittest.main()
