# WT-C01 — nullifier unbound (WarpToad circuit)

- Family: WarpToad circuit (`withdraw`, Noir beta.22). Operator: leave-public-unconstrained.
- Change: `assert(_nullifier == nullifier, ...)` removed from `src/main.nr`.
  Public word 0 (`nullifier`) feeds no constraint; the private preimage still
  derives `_nullifier`, which is now unused.
- Ground truth: the proof no longer binds the public nullifier to the spent
  note. Expected effect: a mint whose public nullifier differs from the
  commitment preimage verifies; the consumer records an attacker-chosen
  nullifier while the real note stays unspent (coverage break on reuse).
- Reachability (cheap): honest `nargo execute` (D1P15_12R.toml) must still
  pass — the honest witness satisfies the weakened relation. Expected: pass.
- Non-equivalence: artifact hash differs from pinned; honest behavior preserved.
- A detector should flag public word 0 as unconstrained; a validator must
  concretize with a mismatched-nullifier witness, real proof, and consumer replay.
