#!/usr/bin/env python3
"""Actual-AST component executions; explicit abstract guard/verifier choices.

Names select declarations only. No message semantics are generated from names.
This harness supplies synthetic states and expectations outside analyzer input.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from bindcheck_d1.frontends.consumer_boundary_v1 import load_boundaries
from bindcheck_d1.frontends.consumer_execution_v1 import Machine, Token, BoundaryChoices
from bindcheck_d1.model_v2 import Unsupported
from bindcheck_d1.consumer_scope_v2 import assess
from d1_guard_frame_check import check as guard_check


def serialize(value):
    if isinstance(value, bytes): return {'bytes_hex': value.hex()}
    raise TypeError(type(value).__name__)


def check():
    directory = ROOT / 'build/D1-03/v2-design/out'
    b, artifacts = load_boundaries(directory)
    certificate, _, _ = guard_check(directory)

    def one(kind, name, **attrs):
        found = [n for n in b.nodes.values() if n['nodeType'] == kind and n.get('name') == name
                 and all(n.get(k) == v for k, v in attrs.items())]
        if len(found) != 1: raise Unsupported('EXEC_SELECTION_AMBIGUOUS', name)
        return found[0]['id']

    # Choose the interface used by the actual call site (IERC20 can have more
    # than one transfer declaration in a compiler artifact set).
    from bindcheck_d1.frontends.consumer_boundary_v1 import walk
    token_fn = b.nodes[one('FunctionDefinition', 'executeBurnToAddress')]
    transfer = [n['referencedDeclaration'] for n in walk(token_fn['body'])
                if n['nodeType'] == 'MemberAccess' and n['memberName'] == 'transfer'][0]
    caller = one('FunctionDefinition', 'verifyRollup')
    verifier = [n['referencedDeclaration'] for n in walk(b.nodes[caller]['body'])
                if n['nodeType'] == 'MemberAccess' and n['memberName'] == 'verify'][0]
    machine = Machine(b, caller, frame_certificate=certificate,
                      context=certificate['payload']['context'],
                      verifier_declaration=verifier, transfer_declaration=transfer)
    roots = {name: one('VariableDeclaration', name, stateVariable=True)
             for name in ('rootHash', 'blockHeight', 'mints', 'tokens', 'provers',
                          'zkVerifiers', 'validatorSetIndex', 'substitutedBurns')}
    C, T, S, V = 0xc0, 0x70, 0xa0, 0xb0
    max_amount = 2**64 - 1
    records = []

    def run(name, messages, expected, *, n=8, registry=None, funds=None, height=2,
            guard=True, verification=True, root=0x11, prover=1, enabled=True,
            expected_transfers=0, expected_mints=0, expected_recipient_gain=None,
            admitted=None):
        state = {roots['rootHash']: 0x11, roots['blockHeight']: 1,
                 roots['validatorSetIndex']: 0, roots['mints']: registry or {},
                 roots['tokens']: {0x4b: T}, roots['provers']: {S: prover},
                 roots['zkVerifiers']: {1: {'enabled': enabled, 'messages_length': n, 'verifier': V}},
                 roots['substitutedBurns']: {}}
        balance = n * max_amount if funds is None else funds
        token = Token(T, {C: balance}, balance)
        words = [root, 0x12, 0x13] + messages
        result = machine.execute([height, 1, b'', words, 0, ()], state, token,
                                 sender=S, contract=C, choices=BoundaryChoices(
                                     guard, {roots['validatorSetIndex']: 7}, verification))
        ok = result.outcome == expected
        ok &= len(result.transfers) == expected_transfers
        ok &= sum(e['event'] == 'Minted' for e in result.events) == expected_mints
        if expected != 'RETURN':
            ok &= result.state == state and result.token == token and not result.writes and not result.events
        if expected == 'RETURN':
            ok &= result.state[roots['rootHash']] == 0x12 and result.state[roots['blockHeight']] == height
            ok &= result.state[roots['validatorSetIndex']] == 7
            gain = expected_transfers * 7 if expected_recipient_gain is None else expected_recipient_gain
            ok &= result.token.balances.get(0xdead, 0) == gain
            ok &= result.token.balances.get(C, 0) == balance - gain
            ok &= result.token.supply == balance
            if expected_mints:
                ok &= result.state[roots['mints']][42]['spent'] is True
            verifier_calls = [c for c in result.boundary_calls if c['kind'] == 'verifier']
            ok &= len(verifier_calls) == 1 and verifier_calls[0]['arguments'] == [b'', words]
        admission = assess(n=n, words=words, roots=roots, state=state, token=token,
                           contract=C, execution=result)
        if admitted is None: admitted = expected == 'RETURN'
        ok &= admission.admitted == admitted
        records.append({'control': name, 'pass': bool(ok), 'expected_outcome': expected,
                        'arguments': [height, 1, b'', words, 0, ()], 'initial_state': state,
                        'initial_token': asdict(token), 'result': asdict(result),
                        'admission': asdict(admission)})

    burn = [3, 0x4b, 7, 42, 0xdead]
    mint = [2, 0x4b, 100, 42]
    registry = {42: {'note_kind': 0x4b, 'amount': 100, 'spent': False}}
    run('funded', burn + [0]*3, 'RETURN', expected_transfers=1)
    run('last_complete_burn', [0]*3 + burn, 'RETURN', expected_transfers=1)
    run('last_slot_padding', [0]*8, 'RETURN')
    run('last_slot_overread', [0]*7 + [3], 'REVERT')
    run('truncated_mint', [0]*5 + [2, 0x4b, 100], 'REVERT')
    run('duplicate_registry', mint*2, 'REVERT', registry=registry)
    run('matching_registry', mint + [0]*4, 'RETURN', registry=registry, expected_mints=1)
    run('default_zero_registry', [2, 0, 0, 42] + [0]*4, 'RETURN', expected_mints=1)
    run('wrong_registry_amount', mint + [0]*4, 'REVERT')
    run('registry_then_verifier_revert', mint + [0]*4, 'REVERT', registry=registry, verification=False)
    run('transfer_then_verifier_revert', burn + [0]*3, 'REVERT', verification=False)
    run('transfer_then_height_revert', burn + [0]*3, 'REVERT', height=1)
    run('guard_revert', burn + [0]*3, 'REVERT', guard=False)
    run('guard_unresolved', burn + [0]*3, 'UNKNOWN', guard=None)
    run('verifier_unresolved', burn + [0]*3, 'UNKNOWN', verification=None)
    run('wrong_root', burn + [0]*3, 'REVERT', root=0x15)
    run('not_prover', burn + [0]*3, 'REVERT', prover=0)
    run('disabled_verifier', burn + [0]*3, 'REVERT', enabled=False)
    run('wrong_length', burn, 'REVERT')
    run('unsupported_message_reverts_in_consumer', [4] + [0]*7, 'REVERT')
    run('high_recipient_bits', burn[:4] + [2**160 + 0xdead] + [0]*3, 'RETURN', expected_transfers=1)
    run('zero_amount_occurrence', [3, 0x4b, 0, 42, 0xdead] + [0]*3, 'RETURN', expected_transfers=1, expected_recipient_gain=0)
    run('self_transfer_occurrence', burn[:4] + [C] + [0]*3, 'RETURN', expected_transfers=1, expected_recipient_gain=0)
    run('insufficient_funding_control', burn + [0]*3, 'RETURN', funds=6, admitted=False)
    run('decoded_zero_control', burn[:4] + [2**160] + [0]*3, 'RETURN', admitted=False)
    run('unknown_token', [3, 0x4c, 7, 42, 0xdead] + [0]*3, 'UNKNOWN')
    run('sequential_duplicate_burns', burn*2 + [0]*990, 'RETURN', n=1000, expected_transfers=2)
    run('partial_effect_then_overread', burn + [0]*2 + [2], 'REVERT')
    run('mixed_registry_and_transfer', mint + burn + [0]*991, 'RETURN', n=1000, registry=registry,
        expected_transfers=1, expected_mints=1)
    return {'artifact_identities': artifacts, 'ast_identity': machine.identity,
            'closure': [{'id': i, 'name': b.nodes[i]['name']} for i in machine.closure],
            'controls': records, 'pass': all(r['pass'] for r in records),
            'security_verdict': 'UNKNOWN', 'primary_queries': 0,
            'guard_frame_cache_key': certificate['cache_key'],
            'full_joint_semantics': False, 'symbolic_lowering': 'NOT_IMPLEMENTED',
            'guard_acceptance': 'NOT_ESTABLISHED', 'proof_acceptance': 'NOT_ESTABLISHED',
            'non_vacuity': 'NOT_ESTABLISHED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = check()
    except (Unsupported, OSError, ValueError, KeyError) as error:
        result = {'pass': False, 'security_verdict': 'UNKNOWN',
                  'reason': getattr(error, 'reason', type(error).__name__), 'detail': str(error)}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2, default=serialize) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('controls', 'artifact_identities')}, indent=2))
    if 'controls' in result:
        print(json.dumps({r['control']: r['pass'] for r in result['controls']}, indent=2))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
