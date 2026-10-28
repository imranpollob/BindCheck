# WT-C05 — root/anchor swap (WarpToad circuit)

- Family: WarpToad circuit. Operator: swap root checks.
- Change: the `else` branch verifies `destination_local_root` against the
  giga root instead of `origin_local_root`. Same types, same arity —
  compiles cleanly.
- Ground truth: the committed destination root gains a membership proof
  while the private origin root goes unconstrained. Expected effect:
  honest same-root withdrawals still verify (dest == origin), so the swap
  is behavior-preserving on the honest path and only diverges adversarially.
- Reachability (cheap): honest `nargo execute` must still pass. Expected: pass.
- Non-equivalence: artifact hash differs from pinned.
