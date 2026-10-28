# WT-C06 — amount unbound from commitment (WarpToad circuit)

- Family: WarpToad circuit. Operator: unbind amount.
- Change: `hash_commitment(..., amount)` becomes `hash_commitment(..., 0)`.
  Public word 2 (`amount`) feeds no constraint.
- Ground truth: the minted amount is proof-unbound. Expected effect: a
  proof for a fixed commitment authorizes any consumer-side amount.
- Reachability (cheap): honest `nargo execute` is EXPECTED TO FAIL —
  the honest commitment commits to the real amount. This mutant is
  honest-breaking by design (still non-equivalent, still a valid
  detection target: word 2 is unconstrained). Recorded, not excluded.
- Non-equivalence: artifact hash differs from pinned.
