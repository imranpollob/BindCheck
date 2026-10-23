"""Pinned beta.14 legacy-bincode decoder. No solver or cryptographic semantics.

Schema provenance: metadata/d1/noir-typed-schema-01.json. Unknown variants,
noncanonical encodings, excessive sizes and trailing bytes fail closed.
"""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
from ..model_v2 import FIELD_MODULUS, Unsupported

REV = '60ccd48e18ad8ce50d5ecda9baf813b712145051'
VERSION = '1.0.0-beta.14+' + REV
MAX_ITEMS = 2_000_000
MAX_BYTES = 256 * 1024**2


class Reader:
    def __init__(self, data):
        if len(data) > MAX_BYTES:
            raise Unsupported('BINARY_SIZE_LIMIT', str(len(data)))
        self.data, self.pos = data, 0

    def fail(self, reason, detail=''):
        raise Unsupported(reason, f'byte {self.pos}: {detail}')

    def take(self, n):
        if n < 0 or self.pos+n > len(self.data):
            self.fail('TRUNCATED_BINARY')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def u8(self): return int.from_bytes(self.take(1), 'little')
    def u32(self): return int.from_bytes(self.take(4), 'little')
    def u64(self): return int.from_bytes(self.take(8), 'little')

    def tag(self, allowed):
        tag = self.u32()
        if tag not in allowed:
            self.fail('UNSUPPORTED_VARIANT', str(tag))
        return tag

    def count(self):
        count = self.u64()
        if count > MAX_ITEMS:
            self.fail('COLLECTION_SIZE_LIMIT', str(count))
        return count

    def vec(self, read): return [read() for _ in range(self.count())]
    def string(self): return self.take(self.count()).decode('utf8')

    def field(self):
        size = self.u64()
        if size != 32:
            self.fail('FIELD_ENCODING_SIZE', str(size))
        value = int.from_bytes(self.take(32), 'big')
        if value >= FIELD_MODULUS:
            self.fail('NONCANONICAL_FIELD_ENCODING')
        return value

    def expression(self):
        mul = self.vec(lambda: [self.field(), self.u32(), self.u32()])
        linear = self.vec(lambda: [self.field(), self.u32()])
        return {'mul': mul, 'linear': linear, 'constant': self.field()}

    def option(self, read):
        tag = self.u8()
        if tag == 0: return None
        if tag == 1: return read()
        self.fail('INVALID_OPTION', str(tag))

    def function_input(self):
        tag = self.tag((0, 1))
        return {'constant': self.field()} if tag == 0 else {'witness': self.u32()}

    def blackbox(self):
        tag = self.tag((3, 11, 12))
        if tag == 3:
            return {'kind':'RANGE','input':self.function_input(),'num_bits':self.u32()}
        if tag == 11:
            return {'kind':'RecursiveAggregation',
                    'verification_key':self.vec(self.function_input),
                    'proof':self.vec(self.function_input),
                    'public_inputs':self.vec(self.function_input),
                    'key_hash':self.function_input(), 'proof_type':self.u32(),
                    'predicate':self.function_input()}
        return {'kind':'Poseidon2Permutation', 'inputs':self.vec(self.function_input),
                'outputs':self.vec(self.u32)}

    def brillig_input(self):
        tag = self.tag((0,1,2))
        if tag == 0: return {'single': self.expression()}
        if tag == 1: return {'array': self.vec(self.expression)}
        return {'memory_array':self.u32()}

    def brillig_output(self):
        tag = self.tag((0,1))
        return {'single':self.u32()} if tag == 0 else {'array':self.vec(self.u32)}

    def opcode(self):
        start = self.pos
        tag = self.tag((0,1,2,3,4)) # constrained function calls remain unsupported
        if tag == 0:
            result = {'kind':'AssertZero', 'expression':self.expression()}
        elif tag == 1:
            result = self.blackbox()
        elif tag == 2:
            result = {'kind':'MemoryOp', 'block_id':self.u32(), 'operation':self.expression(),
                      'index':self.expression(), 'value':self.expression()}
        elif tag == 3:
            result = {'kind':'MemoryInit','block_id':self.u32(),'init':self.vec(self.u32)}
            result['block_type'] = self.tag((0,1,2))
            if result['block_type'] == 1: result['call_data_id'] = self.u32()
        else:
            result = {'kind':'BrilligCall','id':self.u32(),'inputs':self.vec(self.brillig_input),
                      'outputs':self.vec(self.brillig_output),'predicate':self.option(self.expression)}
        result['byte_range'] = [start, self.pos]
        return result

    def witness_set(self):
        values = self.vec(self.u32)
        if values != sorted(set(values)):
            self.fail('NONCANONICAL_WITNESS_SET')
        return values

    def assertion_payload(self):
        tag = self.tag((0,1))
        location = [self.u64()] if tag == 0 else [self.u64(),self.u64()]
        selector = self.u64()
        def value():
            tag = self.tag((0,1))
            return {'expression':self.expression()} if tag == 0 else {'memory':self.u32()}
        return {'location':location,'error_selector':selector,'payload':self.vec(value)}

    def circuit(self):
        start = self.pos
        result = {'function_name':self.string(),'current_witness_index':self.u32(),
                  'opcodes':self.vec(self.opcode),'private_parameters':self.witness_set(),
                  'public_parameters':self.witness_set(),'return_values':self.witness_set(),
                  'assert_messages':self.vec(self.assertion_payload)}
        result['byte_range'] = [start,self.pos]
        return result

    def address(self):
        return [self.tag((0,1)), self.u64()]

    def bitsize(self):
        tag = self.tag((0,1))
        return [tag] if tag == 0 else [tag,self.tag(range(6))]

    def brillig_opcode(self):
        start = self.pos
        tag = self.tag(tuple(range(11))+(12,13,14,15,17,18))
        # Decode supported hints structurally; never use these to establish a constraint.
        if tag == 0:
            data = [self.address(),self.tag(range(8)),self.address(),self.address()]
        elif tag == 1:
            data = [self.address(),self.tag(range(12)),self.tag(range(6)),self.address(),self.address()]
        elif tag == 2:
            data = [self.address(),self.address(),self.tag(range(6))]
        elif tag == 3:
            data = [self.address(),self.address(),self.bitsize()]
        elif tag == 4:
            data = [self.address(),self.u64()]
        elif tag in (5,7):
            data = [self.u64()]
        elif tag == 6:
            data = [self.address(),self.address(),self.address()]
        elif tag in (8,9):
            data = [self.address(),self.bitsize(),self.field()]
        elif tag == 10:
            data = []
        elif tag == 13:
            data = [self.address() for _ in range(4)]
        else:
            data = [self.address(),self.address()]
        return {'tag':tag,'data':data,'byte_range':[start,self.pos]}

    def brillig(self):
        return {'function_name':self.string(),'bytecode':self.vec(self.brillig_opcode)}

    def program(self):
        result = {'functions':self.vec(self.circuit),'unconstrained_functions':self.vec(self.brillig)}
        if self.pos != len(self.data):
            self.fail('TRAILING_BINARY_BYTES', str(len(self.data)-self.pos))
        if len(result['functions']) != 1:
            self.fail('CONSTRAINED_FUNCTION_COUNT_UNSUPPORTED')
        return result


def decode(path):
    artifact = json.loads(Path(path).read_text())
    if artifact.get('noir_version') != VERSION:
        raise Unsupported('COMPILER_VERSION_UNSUPPORTED', str(artifact.get('noir_version')))
    compressed = base64.b64decode(artifact['bytecode'], validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        data = stream.read(MAX_BYTES+1)
    result = Reader(data).program()
    result['identity'] = {'path':str(path),'artifact_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                          'decoded_sha256':hashlib.sha256(data).hexdigest(), 'decoded_bytes':len(data),
                          'format':'legacy bincode; pinned beta.14 subset'}
    result['abi'] = artifact['abi']
    return result


def abi_bindings(abi, circuit):
    """Pinned noirc_abi::Abi::encode flattens parameters from witness zero."""
    cursor, table, public, private = 0, {}, [], []
    def visit(ty, name):
        nonlocal cursor
        start = cursor
        kind = ty['kind']
        if kind in ('field','integer','boolean'):
            cursor += 1
        elif kind == 'array':
            if not 0 <= ty['length'] <= MAX_ITEMS:
                raise Unsupported('ABI_SIZE_LIMIT', name)
            for i in range(ty['length']): visit(ty['type'],f'{name}[{i}]')
        elif kind == 'struct':
            for field in ty['fields']: visit(field['type'],name+'.'+field['name'])
        else:
            raise Unsupported('ABI_TYPE_UNSUPPORTED',kind)
        if name in table:
            raise Unsupported('DUPLICATE_ABI_PATH',name)
        table[name] = list(range(start,cursor))
        return table[name]
    for parameter in abi['parameters']:
        ids = visit(parameter['type'],parameter['name'])
        visibility = parameter['visibility']
        if visibility == 'public': public.extend(ids)
        elif visibility == 'private': private.extend(ids)
        else: raise Unsupported('ABI_VISIBILITY_UNSUPPORTED',visibility)
    if public != circuit['public_parameters'] or private != circuit['private_parameters']:
        raise Unsupported('ABI_DECLARATION_IDENTITY_MISMATCH','typed declaration differs from pinned ABI allocation')
    if abi.get('return_type') is not None or circuit['return_values']:
        raise Unsupported('ABI_RETURN_MAPPING_UNSUPPORTED','')
    return table
