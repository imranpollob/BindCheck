# PY-C05 — verification-key allowlist removed (Payy agg_agg circuit)

- Family: Payy circuit. Operator: remove verification-config check.
- Change: `assert(is_valid_proof, ...)` removed; inner proofs are still
  `verify_proof_with_type`'d against their own keys, but the outer
  allowlist no longer constrains which keys aggregate.
- Ground truth: relation-selection binding lost. Expected effect: proofs
  under unlisted keys aggregate.
- Reachability (cheap): `nargo compile` + structural diff audit.
