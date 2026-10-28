# WT-C08 — zero-recipient guard removed (WarpToad circuit)

- Family: WarpToad circuit. Operator: remove admission guard (circuit side).
- Change: `assert(recipient_address != 0, ...)` removed.
- Ground truth: the zero-address exclusion is proof-unbound. Expected
  effect: a mint to `address(0)` verifies at circuit level (consumer
  ERC20 reverts on zero receiver — joint verdict needs both sides).
- Reachability (cheap): honest `nargo execute` must still pass. Expected: pass.
- Non-equivalence: artifact hash differs from pinned.
