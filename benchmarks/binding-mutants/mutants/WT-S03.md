# WT-S03 — nullifier check and write removed (WarpToad consumer)

- Family: WarpToad consumer. Operator: drop single-use accounting.
- Change: both the `nullifiers[_nullifier] == false` require and the
  `nullifiers[_nullifier] = true` write removed.
- Ground truth: occurrence accounting lost. Expected effect: the same
  proof/calldata mints repeatedly (duplicate/replay); no state records
  the spend.
- Reachability (cheap): solc compile + diff audit. Replay execution is
  future work (needs EDR harness per mutant).
