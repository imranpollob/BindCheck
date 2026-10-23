"""Lossless printed-ACIR inventory; typed recursion is a required gate.

No constraint elimination, source-tail rule, assumed recursive input offset,
or security verdict is supplied by this frontend.
"""
from collections import Counter
from dataclasses import dataclass
import json
import re
from ..model_v2 import Artifact, EvidenceGrade, Provenance, Unsupported


@dataclass(frozen=True)
class Opcode:
    kind: str
    text: str
    provenance: Provenance


def width(ty):
    kind = ty['kind']
    if kind in ('field', 'boolean', 'integer'):
        return 1
    if kind == 'array':
        return ty['length'] * width(ty['type'])
    if kind == 'struct':
        return sum(width(f['type']) for f in ty['fields'])
    raise Unsupported('ABI_TYPE_UNSUPPORTED', kind)


def witnesses(text):
    if not re.fullmatch(r'\[(?:w\d+(?:, w\d+)*)?\]', text):
        raise Unsupported('WITNESS_LIST_FORMAT', text[:80])
    return tuple(int(x) for x in re.findall(r'w(\d+)', text))


def inventory(acir_path, program_path):
    from pathlib import Path
    artifact = Artifact.read(acir_path)
    program = json.loads(Path(program_path).read_text())
    if program['noir_version'] != '1.0.0-beta.14+60ccd48e18ad8ce50d5ecda9baf813b712145051':
        raise Unsupported('COMPILER_VERSION_UNSUPPORTED', program['noir_version'])
    declarations, ops, seen_main, brillig = {}, [], False, False
    for lineno, raw in enumerate(Path(acir_path).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line == 'Compiled ACIR for main (non-transformed):':
            continue
        if line == 'func 0':
            if seen_main:
                raise Unsupported('MULTIPLE_MAIN_FUNCTIONS', str(lineno))
            seen_main = True
            continue
        if line.startswith('func '):
            raise Unsupported('ACIR_FUNCTION_CALL_UNSUPPORTED', line)
        if line.startswith('unconstrained func '):
            brillig = True
            # Keep every unconstrained bytecode line as provenance. No claim
            # is made that this inventory interprets Brillig semantics.
        if brillig:
            kind = 'UNCONSTRAINED_BYTECODE'
        elif ': ' in line and line.split(': ', 1)[0] in ('private parameters', 'public parameters', 'return values'):
            name, body = line.split(': ', 1)
            if name in declarations:
                raise Unsupported('DUPLICATE_DECLARATION', name)
            declarations[name] = witnesses(body)
            continue
        elif line.startswith('ASSERT '):
            kind = 'ASSERT'
        elif line.startswith('BLACKBOX::'):
            kind = line.split()[0]
        elif line.startswith(('INIT ', 'READ ', 'WRITE ')):
            kind = line.split()[0]
        elif line.startswith('BRILLIG CALL '):
            kind = 'BRILLIG_CALL'
        else:
            raise Unsupported('ACIR_OPCODE_UNSUPPORTED', f'{lineno}: {line[:100]}')
        ops.append(Opcode(kind, raw, Provenance(artifact, f'line:{lineno}', EvidenceGrade.EXTRACTED)))
    if not seen_main:
        raise Unsupported('ACIR_MAIN_MISSING', '')
    parameters = program['abi']['parameters']
    for visibility in ('private', 'public'):
        expected = sum(width(p['type']) for p in parameters if p['visibility'] == visibility)
        actual = declarations.get(visibility + ' parameters', ())
        if expected != len(actual) or len(set(actual)) != len(actual):
            raise Unsupported('ABI_DECLARATION_MISMATCH', visibility)
    # Exact declarations do not establish an ABI path-to-witness mapping.
    # Preserve the schema and lists separately until a compiler mapping is checked.
    recs = [op for op in ops if op.kind == 'BLACKBOX::RECURSIVE_AGGREGATION']
    reasons = []
    calls = []
    for op in recs:
        if op.text.strip().startswith('BLACKBOX::RECURSIVE_AGGREGATION inputs: '):
            args = witnesses(op.text.strip().split('inputs: ', 1)[1])
            calls.append({'location': op.provenance.location, 'flattened_witnesses': args,
                          'typed_public_inputs': None, 'key_binding': None})
            reasons.append('RECURSION_LAYOUT_UNESTABLISHED')
        else:
            raise Unsupported('RECURSION_FORMAT_UNSUPPORTED', op.text[:100])
    if not recs:
        reasons.append('RECURSION_CALL_MISSING')
    reasons.extend(['ABI_WITNESS_BINDING_UNESTABLISHED', 'LOGICAL_FRAME_BINDING_UNESTABLISHED',
                    'PRODUCER_RELATION_SEMANTICS_NOT_EXTRACTED'])
    return {'artifact': artifact, 'program_artifact': Artifact.read(program_path),
            'declarations': declarations, 'abi_parameters': parameters, 'opcodes': ops,
            'opcode_counts': dict(Counter(x.kind for x in ops)), 'recursive_calls': calls,
            'reason_codes': sorted(set(reasons)),
            'scope': 'lossless inventory; no producer relation or typed recursion semantics extracted'}
