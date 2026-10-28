# WT-C02 — max_fee unbound (WarpToad circuit)

- Family: WarpToad circuit. Operator: leave-public-unconstrained.
- Change: `assert(!amount.lt(max_fee), ...)` removed. Public word 8
  (`max_fee`) feeds no constraint.
- Ground truth: the fee-cap policy input is proof-unbound. Expected effect:
  a proof with `max_fee` below the charged fee still verifies at circuit
  level (the consumer's own cap check may still revert — joint verdict
  needs the consumer model; the binding break is producer-side).
- Reachability (cheap): honest `nargo execute` must still pass. Expected: pass.
- Non-equivalence: artifact hash differs from pinned.
