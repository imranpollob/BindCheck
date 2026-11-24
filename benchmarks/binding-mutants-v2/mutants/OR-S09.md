# OR-S09: nullifier truncated to 64 bits before the replay-set lookup and write

- Host: `orc`. Pattern: **P5**. Mutated layer: consumer.
- Operator: nullifier truncated to 64 bits before the replay-set lookup and write.
- Binding broken: the replay key is `uint64(nullifier)`, not the proved 256-bit nullifier word.
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: nullifier (only 64 bits used).
- Expected effect (prediction, not an E4 result): Verifier accepts the honest proof; two GitHub accounts whose nullifiers share the low 64 bits (about 2^32 accounts to find a pair) alias, so one account consumes another's one-claim slot.
- Honest path: Honest claim call succeeds (no revert); host tests that read `nullifierUsed(fullNullifier)` fail by assertion, which only shows the key changed.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
- `src/OrcClaim.sol`: 1 exact replacement(s)
