# WT-C04 — origin membership dropped (WarpToad circuit)

- Family: WarpToad circuit. Operator: remove admission guard (circuit side).
- Change: the `else` branch no longer calls
  `evm_merkle_verify(giga_root, origin_local_root, giga_merkle_data)`.
  When `destination_local_root != origin_local_root`, the private origin
  root is unconstrained.
- Ground truth: cross-root path binds nothing. Expected effect: a proof
  over a fabricated origin root verifies whenever the outer equality
  branch is avoided.
- Reachability (cheap): honest same-root `nargo execute` takes the empty
  `if` branch, so it must still pass. Expected: pass.
- Non-equivalence: artifact hash differs from pinned.
