# WT-S06 — fee-cap admission removed (WarpToad consumer)

- Family: WarpToad consumer. Operator: unbind fee.
- Change: `require(_relayerFee <= _maxFee, ...)` removed.
- Ground truth: the max-fee cap is unenforced. Expected effect: a
  relayer collects a fee above the user's stated maximum (up to the
  underflow boundary at `_amount`).
- Reachability (cheap): solc compile + diff audit.
