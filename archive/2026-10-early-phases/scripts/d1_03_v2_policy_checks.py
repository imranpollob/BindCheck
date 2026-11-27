#!/usr/bin/env python3
"""Finite design checks, not an analyzer, SMT proof or real-constraint replay."""
import itertools
import json
from collections import Counter


def injection(left, right):
    """Independent exhaustive assignment oracle; occurrence indices are distinct."""
    return any(all(left[i] == right[j] for i, j in enumerate(assignment))
               for assignment in itertools.permutations(range(len(right)), len(left)))


def counts_fit(left, right):
    available = Counter(right)
    return all(n <= available[key] for key, n in Counter(left).items())


def update(funds, recipient, amount):
    # recipient 1 = self, 2 = another account, 0 = zero address.
    if recipient == 0 or funds < amount:
        return False, funds
    return True, funds if recipient == 1 else funds - amount


def main():
    counts = {'matching': 0, 'funding': 0, 'controls': 0}
    vectors = [x for n in range(4) for x in itertools.product((0, 1), repeat=n)]
    for p in vectors:
        for e in vectors:
            # O is independently chosen; enumerate small distinct subsets of P's
            # occurrences, not set-deduplicated P values.
            for n in range(len(p) + 1):
                for indexes in itertools.combinations(range(len(p)), n):
                    o = tuple(p[i] for i in indexes)
                    assert counts_fit(e, p) == injection(e, p)
                    assert counts_fit(o, e) == injection(o, e)
                    counts['matching'] += 1

    # All 0..3-call sequences, amounts 0..3, self/external destinations,
    # and initial balances 0..12; include successful and failed calls.
    calls = list(itertools.product((1, 2), range(4)))
    for n in range(4):
        for sequence in itertools.product(calls, repeat=n):
            for initial in range(13):
                balance = initial
                successes = []
                for recipient, amount in sequence:
                    ok, new_balance = update(balance, recipient, amount)
                    # Independent accounting oracle for this concrete sequence.
                    spent = sum(a for (r, a), s in zip(sequence, successes) if s and r == 2)
                    assert balance == initial - spent
                    assert ok == (initial - spent >= amount)
                    successes.append(ok)
                    balance = new_balance
                if initial >= n * 3:
                    assert all(successes)
                assert 0 <= balance <= initial
                counts['funding'] += 1

    controls = {
        'optional_permission_no_obligation': counts_fit((), (0,)) and counts_fit((), ()),
        'mandatory_missing_effect': not counts_fit((0,), ()),
        'two_active_equal_occurrences': counts_fit((0, 0), (0, 0)),
        'padding_no_extra_permission': not counts_fit((0, 0), (0,)),
        'duplicate_effect_is_excess': not counts_fit((0, 0), (0,)),
        'wrong_recipient': not counts_fit((1,), (0,)),
        'recipient_alias': ((1 << 160) + 0xdead) % (1 << 160) == 0xdead,
        'nonzero_word_decodes_zero': (1 << 160) % (1 << 160) == 0,
        'insufficient_balance_failed_attempt': update(6, 2, 7) == (False, 6),
        'zero_recipient_failed_attempt': update(100, 0, 7) == (False, 100),
        'zero_amount_occurrence': update(0, 2, 0) == (True, 0),
        'self_transfer_occurrence': update(100, 1, 7) == (True, 100),
    }
    assert all(controls.values())
    counts['controls'] = len(controls)
    total = sum(counts.values())
    assert total <= 10000
    print(json.dumps({'scope': 'finite synthetic policy/token checks only',
                      'counts': counts, 'total': total, 'controls': controls,
                      'primary_query_verdict': None}, indent=2))


if __name__ == '__main__':
    main()
