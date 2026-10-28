# PY-S03 — burn recipient misbound (Payy consumer)

- Family: Payy consumer. Operator: misbind word (type-compatible swap).
- Change: `burn_addr` decodes `messages[i + 1]` (the note-kind word)
  instead of `messages[i + 4]`. Compiles: both are `bytes32`.
- Ground truth: beneficiary binding broken. Expected effect: burn payout
  goes to an address derived from the note kind, not the proof's
  recipient.
- Reachability (cheap): solc compile + diff audit.
