# PY-C03 — root chaining removed (Payy agg_agg circuit)

- Family: Payy circuit. Operator: remove admission guard (circuit side).
- Change: `assert(proof.old_root == root, ...)` removed; `root` still
  advances to each proof's `new_root`.
- Ground truth: state continuity unbound. Expected effect: proofs from
  disjoint histories aggregate into one claim.
- Reachability (cheap): `nargo compile` + structural diff audit.
