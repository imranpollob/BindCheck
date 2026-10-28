# PY-S01 — mint admission removed (Payy consumer)

- Family: Payy consumer (`RollupV1`, solc 0.8.20, via-IR + optimizer
  runs=200 per the pinned hardhat config). Operator: remove admission guard.
- Change: the three `verifyMint` requires (value, note kind, single-use)
  removed; spend marking and event kept.
- Ground truth: mint registration lost. Expected effect: unregistered
  mints settle — the mint-side mirror of the in-scope burn gap.
- Reachability (cheap): solc compile + diff audit. No EDR execution here.
