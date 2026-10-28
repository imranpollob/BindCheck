# PY-C07 — public-word misorder (Payy agg_agg circuit)

- Family: Payy circuit. Operator: misorder public words.
- Change: `old_root` and `new_root` swap positions in the `main`
  signature. Arity unchanged.
- Ground truth: field-mapping disagreement with the unchanged
  `agg_final` forwarder and consumer. Expected effect: chained roots
  are interpreted swapped downstream.
- Reachability (cheap): `nargo compile` + artifact ABI order diff.
