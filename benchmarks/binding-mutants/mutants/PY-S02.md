# PY-S02 — mint single-use removed (Payy consumer)

- Family: Payy consumer. Operator: drop single-use accounting.
- Change: `require(mints[hash].spent == false, ...)` removed; the
  `spent = true` write stays (a write with no check still replays).
- Ground truth: mint replay. Expected effect: the same registered mint
  settles twice.
- Reachability (cheap): solc compile + diff audit.
