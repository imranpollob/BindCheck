"""Concrete occurrence and token-state semantics; not a solver or extractor."""
from collections import Counter
from dataclasses import dataclass
from .model_v2 import EvmWord, Occurrence, Policy, Unsupported


@dataclass(frozen=True)
class TraceAssessment:
    authorization_deficits: tuple
    coverage_deficits: tuple
    reason: str | None
    scope: str = 'one concrete committed trace; no universal verdict'


def assess_trace(policy: Policy, effects: tuple[Occurrence, ...], *, committed: bool,
                 deferred: bool = False):
    if not committed:
        return TraceAssessment((), (), 'TRANSITION_REVERTED')
    if len({x.identity for x in effects}) != len(effects):
        raise Unsupported('DUPLICATE_EFFECT_ID', '')
    p = Counter(x.key for x in policy.permissions)
    o = Counter(x.key for x in policy.obligations)
    e = Counter(x.key for x in effects)
    auth = tuple((key, n - p[key]) for key, n in e.items() if n > p[key])
    cov = tuple((key, n - e[key]) for key, n in o.items() if n > e[key])
    # Failed immediate discharge has no implemented deferral policy. Preserve
    # observations but explicitly block a joint coverage conclusion.
    return TraceAssessment(auth, cov, 'DEFERRAL_UNSUPPORTED' if deferred else None)


@dataclass(frozen=True)
class Transfer:
    success: bool
    balances: dict[int, int]
    recipient: int
    amount: int


def standard_transfer(balances, sender, recipient_word: EvmWord, amount):
    """OZ ERC20 _transfer/_update fragment, assuming pinned unmodified code."""
    EvmWord(amount)
    if type(sender) is not int or not 0 < sender < 2**160:
        raise Unsupported('INVALID_TOKEN_SENDER', repr(sender))
    for address, value in balances.items():
        if type(address) is not int or not 0 < address < 2**160:
            raise Unsupported('INVALID_BALANCE_ADDRESS', repr(address))
        EvmWord(value)
    if sum(balances.values()) >= 2**256:
        raise Unsupported('TOKEN_SUPPLY_INVARIANT_MISSING', '')
    recipient = recipient_word.address()
    after = dict(balances)
    if recipient == 0 or balances.get(sender, 0) < amount:
        return Transfer(False, after, recipient, amount)
    after[sender] = after.get(sender, 0) - amount
    after[recipient] = after.get(recipient, 0) + amount
    return Transfer(True, after, recipient, amount)
