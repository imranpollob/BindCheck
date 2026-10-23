"""Small, replayable polynomial certificates for boundary bindings.

Every proved equality is an explicit linear combination of decoded AssertZero
polynomials. Unused constraints are retained in the artifact; this checker never
claims satisfiability or that a selected subset is an equivalent full circuit.
"""
from collections import defaultdict
from ..model_v2 import FIELD_MODULUS as P, Unsupported


def clean(poly): return {m:c % P for m,c in poly.items() if c % P}


def add(left, right, factor=1):
    result=dict(left)
    for monomial,coefficient in right.items():
        result[monomial]=result.get(monomial,0)+factor*coefficient
    return clean(result)


def mul(left, right):
    result={}
    for a,c in left.items():
        for b,d in right.items():
            key=tuple(sorted(a+b));result[key]=result.get(key,0)+c*d
    return clean(result)


def constant(n): return clean({():n})
def witness(w): return {(w,):1}


def function_input(value):
    if set(value)=={'witness'}:return witness(value['witness'])
    if set(value)=={'constant'}:return constant(value['constant'])
    raise Unsupported('INVALID_TYPED_FUNCTION_INPUT',str(value))


def expression(value):
    result={():value['constant']}
    for c,w in value['linear']:result[(w,)]=result.get((w,),0)+c
    for c,a,b in value['mul']:
        key=tuple(sorted((a,b)));result[key]=result.get(key,0)+c
    return clean(result)


def packed(poly):return [[list(m),c] for m,c in sorted(poly.items())]
def unpacked(poly):return clean({tuple(m):c for m,c in poly})


def normalized(poly):
    poly=clean(poly)
    if not poly:return (),1
    coefficient=poly[min(poly)]
    inverse=(1 if coefficient==1 else P-1 if coefficient==P-1 else pow(coefficient,-1,P))
    return tuple((m,c*inverse % P) for m,c in sorted(poly.items())),inverse


class Certificates:
    def __init__(self, circuit):
        self.assertions={i:expression(op['expression']) for i,op in enumerate(circuit['opcodes']) if op['kind']=='AssertZero'}
        self.direct={}
        self.linear=defaultdict(list)
        for i,poly in self.assertions.items():
            key,inverse=normalized(poly)
            self.direct.setdefault(key,(i,inverse))
            for monomial in poly:
                if len(monomial)==1:
                    self.linear[monomial[0]].append(i)

    def direct_proof(self,goal):
        key,inverse=normalized(goal)
        if not key:return []
        if key not in self.direct:return None
        i,other_inverse=self.direct[key]
        return [(i,other_inverse*pow(inverse,-1,P) % P)]

    def prove(self,goal,output=None):
        goal=clean(goal)
        direct=self.direct_proof(goal)
        if direct is not None:return self.finish(goal,direct)
        target_variables={v for m in goal for v in m}
        # Candidate construction is heuristic; acceptance is the exact polynomial
        # identity checked below. A bounded search failure is UNKNOWN, not UNSAT.
        def solve(residual,depth,used):
            direct=self.direct_proof(residual)
            if direct is not None:return direct
            if depth==0:return None
            choices=[m[0] for m in residual if len(m)==1 and m[0] not in target_variables]
            if not used and output is not None and (output,) in residual:
                choices=[output]+choices
            for variable in sorted(set(choices),reverse=True)[:8]:
                for i in self.linear.get(variable,[])[:32]:
                    if i in used:continue
                    row=self.assertions[i]
                    # Do not replace a witness which also occurs in a product
                    # by pretending this is linear elimination.
                    if any(variable in m for m in row if len(m)>1):continue
                    factor=residual[(variable,)]*pow(row[(variable,)],-1,P) % P
                    remaining=add(residual,row,-factor)
                    if len(remaining)>16:continue
                    suffix=solve(remaining,depth-1,used|{i})
                    if suffix is not None:return [(i,factor)]+suffix
            return None
        proof=solve(goal,3,set())
        if proof is None:raise Unsupported('BINDING_CERTIFICATE_NOT_FOUND',str(packed(goal)))
        return self.finish(goal,proof)

    def finish(self,goal,proof):
        result={'goal':packed(goal),'linear_combination':[[i,c] for i,c in proof]}
        self.check(result)
        return result

    def check(self,certificate):
        actual={}
        for i,factor in certificate['linear_combination']:
            if i not in self.assertions:raise Unsupported('CERTIFICATE_OPCODE_NOT_ASSERT',str(i))
            actual=add(actual,self.assertions[i],factor)
        if actual!=unpacked(certificate['goal']):
            raise Unsupported('CERTIFICATE_IDENTITY_FAILED','')
        return True

    def equals(self,left,right):
        output=left.get('witness')
        return self.prove(add(function_input(left),right,-1),output)

    def zero_test(self,root):
        # Pair r*z=0 and r*inverse+z-1=0 proves z=1 iff r=0 over a field.
        candidates=[]
        for key,(i,_) in self.direct.items():
            if len(key)==1 and len(key[0][0])==2 and root in key[0][0]:
                a,b=key[0][0];candidates.append((b if a==root else a,i))
        for selector,i in candidates:
            for j in self.linear.get(selector,[]):
                poly=self.assertions[j]
                terms=[m for m in poly if len(m)==2 and root in m]
                if len(terms)!=1:continue
                a,b=terms[0];inverse=b if a==root else a
                goal=add(add(mul(witness(root),witness(inverse)),witness(selector)),constant(-1))
                proof=self.direct_proof(goal)
                if proof is None:continue
                return {'root':root,'selector':selector,'inverse_hint':inverse,
                        'zero_product':self.prove(mul(witness(root),witness(selector))),
                        'inverse_equation':self.finish(goal,proof),
                        'deduction':'field: root=0 => selector=1; root!=0 => selector=0; no assumption about inverse hint'}
        raise Unsupported('ROOT_ZERO_TEST_NOT_CERTIFIED',str(root))


def certify_bindings(program,table):
    circuit=program['functions'][0]
    cert=Certificates(circuit)
    recs=[(i,op) for i,op in enumerate(circuit['opcodes']) if op['kind']=='RecursiveAggregation']
    if any(rec['proof_type']!=7 for _,rec in recs):
        raise Unsupported('RECURSIVE_PROOF_TYPE_UNSUPPORTED','only the pinned type-7 fragment is supported')
    def ref(path):
        if path not in table:raise Unsupported('ABI_ROLE_PATH_MISSING',path)
        return [{'witness':w} for w in table[path]]
    def verify_vector(actual,expected):
        if len(actual)!=len(expected):raise Unsupported('BINDING_LENGTH_MISMATCH','')
        return [cert.equals(a,function_input(b)) for a,b in zip(actual,expected)]
    results=[]
    if 'proofs' in table:
        frames=[i for i in range(len(recs)) if f'proofs[{i}].old_root' in table]
        if len(frames)!=2 or len(recs)!=2:
            raise Unsupported('LOGICAL_FRAME_COUNT_UNSUPPORTED','')
        logical=[]
        for frame in frames:
            prefix=f'proofs[{frame}]'
            logical.append(ref('verification_key_hash')+ref(prefix+'.old_root')+ref(prefix+'.new_root')+
                           ref(prefix+'.commit_hash')+ref(prefix+'.messages'))
        unused=dict(recs)
        for frame in frames:
            prefix=f'proofs[{frame}]'
            vk=ref(prefix+'.verification_key')
            matches=[(i,r) for i,r in unused.items() if r['verification_key']==vk]
            if len(matches)!=1:raise Unsupported('FRAME_KEY_ASSOCIATION_UNRESOLVED',prefix)
            index,rec=matches[0];del unused[index]
            zero=cert.zero_test(table[prefix+'.old_root'][0]);z=witness(zero['selector'])
            def mux_vector(actual,active,padding):
                if len(actual)!=len(active) or len(actual)!=len(padding):
                    raise Unsupported('FRAME_VECTOR_LENGTH_MISMATCH',prefix)
                equations=[]
                for a,b,c in zip(actual,active,padding):
                    # z * padding + (1-z) * active, with z derived above.
                    wanted=add(mul(z,function_input(c)),mul(add(constant(1),z,-1),function_input(b)))
                    equations.append(cert.equals(a,wanted))
                return equations
            results.append({'logical_frame':frame,'recursive_opcode':index,'byte_range':rec['byte_range'],
                            'activation':zero,'verification_key':verify_vector(rec['verification_key'],vk),
                            'proof':mux_vector(rec['proof'],ref(prefix+'.proof'),ref('proofs[0].proof')),
                            'public_inputs':mux_vector(rec['public_inputs'],logical[frame],logical[0]),
                            'key_hash':verify_vector([rec['key_hash']],ref(prefix+'.verification_key_hash')),
                            'enabled':cert.equals(rec['predicate'],constant(1)),
                            'proof_type':rec['proof_type']})
    else:
        if len(recs)!=1:raise Unsupported('FINAL_RECURSION_COUNT_UNSUPPORTED','')
        index,rec=recs[0]
        exported=ref('old_root')+ref('new_root')+ref('commit_hash')+ref('messages')
        if len(rec['public_inputs'])!=len(exported)+2:
            raise Unsupported('FINAL_PUBLIC_INPUT_LENGTH','')
        key_constants=[]
        for item in rec['public_inputs'][:2]:
            if 'constant' in item:value=item['constant']
            else:
                candidates=[]
                for j in cert.linear.get(item['witness'],[]):
                    row=cert.assertions[j]
                    if set(row)<= {(),(item['witness'],)}:
                        candidates.append((-row.get((),0)*pow(row[(item['witness'],)],-1,P))%P)
                if len(set(candidates))!=1:raise Unsupported('FINAL_KEY_CONSTANT_UNRESOLVED','')
                value=candidates[0]
            key_constants.append({'value':str(value),'certificate':cert.equals(item,constant(value))})
        results.append({'recursive_opcode':index,'byte_range':rec['byte_range'],
                        'verification_key':verify_vector(rec['verification_key'],ref('verification_key')),
                        'proof':verify_vector(rec['proof'],ref('proof')),
                        'public_inputs':verify_vector(rec['public_inputs'][2:],exported),
                        'key_hash':verify_vector([rec['key_hash']],ref('verification_key_hash')),
                        'enabled':cert.equals(rec['predicate'],constant(1)),
                        'allowed_key_constants':key_constants,'proof_type':rec['proof_type']})
    return {'scope':'local boundary implications only; not satisfiability or a joint security verdict',
            'artifact_identity':program['identity'],'bindings':results,
            'proof_rule':'each equality is replayed as a linear combination of actual decoded AssertZero polynomials; zero-test deduction uses field semantics',
            'assumptions':['correct pinned compiler/ABI and decoder schema','recursive cryptographic soundness not checked','logical message roles supplied by v2 policy'],
            'remaining':['full producer/consumer transition relation','non-vacuity','primary queries','concrete replay']}
