# WT-S04 — verifier call removed (WarpToad consumer)

- Family: WarpToad consumer. Operator: remove verification gate.
- Change: `require(IVerifier(withdrawVerifier).verify(...))` removed.
- Ground truth: proof gating lost — any calldata mints without a proof.
  Expected effect: open mint to arbitrary recipient/amount (bounded only
  by fee arithmetic and zero-address checks).
- Reachability (cheap): solc compile + diff audit. This is the trivial
  positive control: every sound tool must flag it; a tool that misses
  S04 cannot be trusted on subtler mutants.
