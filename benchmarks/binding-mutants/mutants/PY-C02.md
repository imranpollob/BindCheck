# PY-C02 — export binding removed (Payy agg_agg circuit)

- Family: Payy circuit. Operator: leave-public-unconstrained.
- Change: `assert(proof_message == messages[messages_index], ...)` removed.
  Active-branch words still advance the counter, but the public `messages`
  array is never equated to inner proof words.
- Ground truth: the full 1,000-word public output is unconstrained (the
  check-added repair's core property is gone). Expected effect: arbitrary
  public messages verify — the maximal producer-side break in this set.
- Reachability (cheap): `nargo compile` + structural diff audit.
