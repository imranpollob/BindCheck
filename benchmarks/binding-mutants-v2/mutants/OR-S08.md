# OR-S08: threshold check reads the repoDatabaseId word instead of the threshold word

- Host: `orc`. Pattern: **P5**. Mutated layer: consumer.
- Operator: threshold check reads the repoDatabaseId word instead of the threshold word.
- Binding broken: the minimum-commit policy is checked against `pv.repoDatabaseId`, not the proved `threshold`.
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: threshold (the proved commit count is never compared).
- Expected effect (prediction, not an E4 result): Verifier and all other checks accept the honest proof; a proof attesting any threshold (e.g. 0 commits) passes because the large repo id is compared instead.
- Honest path: Honest claim works (repo id is far above the configured threshold).
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
