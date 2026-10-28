# WT-C07 — chain_id unbound from commitment (WarpToad circuit)

- Family: WarpToad circuit. Operator: unbind domain (context identity).
- Change: `hash_commitment(..., chain_id, ...)` becomes `(..., 0, ...)`.
  Public word 1 (`chain_id`) feeds no constraint.
- Ground truth: cross-chain replay shape — a proof generated for one
  chain verifies with another chain's id. Expected effect: same
  commitment/note spendable on two instances.
- Reachability (cheap): honest `nargo execute` is EXPECTED TO FAIL
  (honest pre-commitment binds the real chain id). Honest-breaking by
  design; detection target stands.
- Non-equivalence: artifact hash differs from pinned.
