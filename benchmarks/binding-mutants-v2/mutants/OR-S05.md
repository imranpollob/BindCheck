# OR-S05: verifier call wrapped in try/catch that swallows failure

- Host: `orc`. Pattern: **P4**. Mutated layer: consumer.
- Operator: verifier call wrapped in try/catch that swallows failure.
- Binding broken: failed proof verification no longer reverts.
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: whole proof statement.
- Expected effect (prediction, not an E4 result): Any publicValues with an invalid proof pass the final check; claims need no proof.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
