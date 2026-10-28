# PY-C04 — commit-hash binding removed (Payy agg_agg circuit)

- Family: Payy circuit. Operator: unbind commitment.
- Change: the `commit_hash == Poseidon2(...)` assert removed. Public
  `commit_hash` feeds no constraint.
- Ground truth: batch-commitment binding lost. Expected effect: the
  aggregate claim floats free of its inner commitments.
- Reachability (cheap): `nargo compile` + structural diff audit.
