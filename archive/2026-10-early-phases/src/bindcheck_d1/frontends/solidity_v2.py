"""Extract AST locations and calldata forwarding facts, not path semantics."""
import json
from pathlib import Path
from Crypto.Hash import keccak
from ..model_v2 import Artifact, EvidenceGrade, Provenance, Unsupported


def walk(node):
    if isinstance(node, dict):
        if 'nodeType' in node:
            yield node
        for child in node.values():
            yield from walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from walk(child)


def inventory(artifact_path, source_path):
    artifact = Artifact.read(artifact_path)
    data = json.loads(Path(artifact_path).read_text())
    source = Path(source_path).read_bytes()
    metadata = json.loads(data['rawMetadata'])
    if metadata['compiler']['version'] != '0.8.20+commit.a1b79de6':
        raise Unsupported('SOLC_VERSION_UNSUPPORTED', metadata['compiler']['version'])
    ast = data['ast']
    target = ast['absolutePath']
    expected = metadata['sources'].get(target, {}).get('keccak256')
    actual = '0x' + keccak.new(digest_bits=256, data=source).hexdigest()
    if actual != expected:
        raise Unsupported('SOLIDITY_SOURCE_HASH_MISMATCH', target)
    contracts = [n for n in ast['nodes'] if n['nodeType'] == 'ContractDefinition' and n['name'] == 'RollupV1']
    if len(contracts) != 1:
        raise Unsupported('CONSUMER_CONTRACT_MISSING', '')
    functions = {n['name']: n for n in contracts[0]['nodes'] if n['nodeType'] == 'FunctionDefinition'}
    required = ['verifyRollup', 'verifyAllMessages', 'verifyMessages', 'verifyMint',
                'verifyBurn', 'bytes32ToAddress', 'executeBurn', 'executeBurnToAddress']
    if not all(name in functions for name in required):
        raise Unsupported('CONSUMER_PATH_MISSING', '')
    entry = functions['verifyRollup']
    params = [p for p in entry['parameters']['parameters'] if p['name'] == 'publicInputs']
    if len(params) != 1 or params[0]['storageLocation'] != 'calldata':
        raise Unsupported('PUBLIC_INPUT_PARAMETER_UNSUPPORTED', '')
    param_id = params[0]['id']
    proof_calls, scanner_calls = [], []
    for node in walk(entry['body']):
        if node['nodeType'] != 'FunctionCall':
            continue
        expr = node['expression']
        args = node.get('arguments', [])
        if expr.get('nodeType') == 'MemberAccess' and expr.get('memberName') == 'verify':
            proof_calls.append(node)
        if expr.get('referencedDeclaration') == functions['verifyAllMessages']['id']:
            scanner_calls.append(node)
    if len(proof_calls) != 1 or len(scanner_calls) != 1:
        raise Unsupported('FORWARDING_CALL_COUNT', '')
    proof, scanner = proof_calls[0], scanner_calls[0]
    def is_input(n):
        return n.get('nodeType') == 'Identifier' and n.get('referencedDeclaration') == param_id
    if len(proof['arguments']) != 2 or not is_input(proof['arguments'][1]):
        raise Unsupported('VERIFIER_INPUT_FORWARDING_MISMATCH', '')
    if len(scanner['arguments']) != 3 or not is_input(scanner['arguments'][1]):
        raise Unsupported('SCANNER_INPUT_FORWARDING_MISMATCH', '')
    skip = scanner['arguments'][0]
    if skip.get('nodeType') != 'Literal' or skip.get('value') != '3':
        raise Unsupported('SCANNER_OFFSET_UNSUPPORTED', '')
    def located(n):
        start, length, file_id = map(int, n['src'].split(':'))
        if start < 0 or length < 0 or start + length > len(source):
            raise Unsupported('AST_SOURCE_RANGE_INVALID', n['src'])
        return {'node_id': n['id'], 'node_type': n['nodeType'],
                'provenance': Provenance(artifact, f"ast:{n['id']};src:{n['src']}", EvidenceGrade.EXTRACTED),
                'source_excerpt': source[start:start+length].decode()}
    index_accesses = [located(n) for name in required for n in walk(functions[name])
                      if n['nodeType'] == 'IndexAccess']
    return {'artifact': artifact, 'source_artifact': Artifact.read(source_path),
            'source_keccak256': actual, 'compiler': metadata['compiler'],
            'functions': {name: located(functions[name]) for name in required},
            'verifier_call': located(proof), 'scanner_call': located(scanner),
            'same_public_input_parameter': param_id, 'scanner_literal_offset': 3,
            'index_accesses': index_accesses,
            'reason_codes': ['CONSUMER_TRANSITION_SEMANTICS_NOT_EXTRACTED'],
            'scope': 'AST/source identity and forwarding facts; no path/state/bytecode equivalence proof'}
