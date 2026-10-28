# PY-C06 — final root match removed (Payy agg_agg circuit)

- Family: Payy circuit. Operator: leave-public-unconstrained.
- Change: `assert(new_root == root, "Roots must match")` removed. Public
  `new_root` feeds no constraint.
- Ground truth: the claimed resulting state is proof-unbound. Expected
  effect: the aggregate verifies while asserting an arbitrary new root.
- Reachability (cheap): `nargo compile` + structural diff audit.
