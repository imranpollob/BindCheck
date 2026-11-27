"""V2 admission checks, separate from execution and independent P/O policy.

These checks never add a missing implementation constraint. Out-of-family
inputs are reported explicitly, even when the concrete consumer accepts them.
No admission/trace result establishes signature/proof acceptance or safety.
"""
from dataclasses import dataclass
from .model_v2 import FIELD_MODULUS


@dataclass(frozen=True)
class Admission:
    admitted: bool
    reasons: tuple[str, ...]
    security_verdict: str = 'UNKNOWN'


def assess(*, n, words, roots, state, token, contract, execution):
    reasons = []
    required = {'rootHash', 'mints', 'tokens', 'substitutedBurns'}
    if not required <= set(roots):
        return Admission(False, ('STATE_LAYOUT_MISSING',))
    if type(n) is not int:
        return Admission(False, ('MESSAGE_BOUND_OUTSIDE_V2',))
    if n not in (8, 1000):
        reasons.append('MESSAGE_BOUND_OUTSIDE_V2')
    if len(words) != n + 3:
        reasons.append('PUBLIC_INPUT_LENGTH')
    if any(type(w) is not int or not 0 <= w < FIELD_MODULUS for w in words):
        reasons.append('NONCANONICAL_FIELD')
    if not words or state.get(roots['rootHash'], 0) != words[0]:
        reasons.append('INITIAL_ROOT_OUTSIDE_V2')
    funding = n * (2**64 - 1)
    if token.supply != funding or token.balances.get(contract, 0) != funding or any(
            amount for address, amount in token.balances.items() if address != contract):
        reasons.append('INITIAL_FUNDING_OUTSIDE_V2')
    registrations = state.get(roots['tokens'], {})
    if registrations.get(0x4b, 0) != token.address or any(
            address for kind, address in registrations.items() if kind != 0x4b):
        reasons.append('TOKEN_REGISTRATION_OUTSIDE_V2')
    if any(entry.get('spent', False) for entry in state.get(roots['mints'], {}).values()):
        reasons.append('INITIAL_SPENT_REGISTRY_OUTSIDE_V2')
    if any(state.get(roots['substitutedBurns'], {}).values()):
        reasons.append('SUBSTITUTION_UNSUPPORTED')
    if execution.outcome != 'RETURN':
        reasons.append('TRANSITION_REVERTED' if execution.outcome == 'REVERT' else 'EXECUTION_UNRESOLVED')
    else:
        for call in execution.boundary_calls:
            if call['kind'] != 'token': continue
            recipient, amount = call['arguments']
            if not 0 <= amount <= 2**64 - 1:
                reasons.append('BURN_AMOUNT_OUTSIDE_V2')
            if recipient == 0:
                reasons.append('RECIPIENT_OUTSIDE_V2')
            if not call['success']:
                reasons.append('DEFERRAL_UNSUPPORTED')
    return Admission(not reasons, tuple(dict.fromkeys(reasons)))
