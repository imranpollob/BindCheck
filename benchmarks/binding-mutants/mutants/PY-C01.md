# PY-C01 — padding-gap check removed (Payy agg_agg circuit)

- Family: Payy circuit (`agg_agg`, Noir beta.14). Operator: remove
  activation-extent guard.
- Change: `assert(proof_message == 0, "messages cannot have gaps")` removed.
- Ground truth: padding discipline lost. Expected effect: non-zero words
  after `has_ended` no longer fail witness generation; sparse trailing
  records become provable.
- Reachability (cheap): `nargo compile` only (no Prover.toml harness for
  the 2-proof aggregator in this benchmark). Structural: gap words feed
  no constraint.
