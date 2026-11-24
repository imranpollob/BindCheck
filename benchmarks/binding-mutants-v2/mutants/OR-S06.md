# OR-S06: nullifier write removed

- Host: `orc`. Pattern: **P3**. Mutated layer: consumer.
- Operator: nullifier write removed.
- Binding broken: no replay protection (nullifier never marked used).
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: nullifier.
- Expected effect (prediction, not an E4 result): The same account claims repeatedly in one campaign.
- Honest path: Honest first claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
