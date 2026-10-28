# WT-S07 — recipient share misdirected (WarpToad consumer)

- Family: WarpToad consumer. Operator: misdirect beneficiary.
- Change: `_mint(_recipient, _amount - _relayerFee)` becomes
  `_mint(_relayer, _amount - _relayerFee)`.
- Ground truth: beneficiary binding broken. Expected effect: the relayer
  receives fee plus principal; the recipient receives nothing while the
  proof authorizes a recipient payout.
- Reachability (cheap): solc compile + diff audit.
