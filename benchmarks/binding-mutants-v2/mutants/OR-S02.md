# OR-S02: campaign check removed

- Host: `orc`. Pattern: **P2**. Mutated layer: consumer.
- Operator: campaign check removed.
- Binding broken: proof is not bound to this deployment (campaignId = chain, address, salt).
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: campaignId.
- Expected effect (prediction, not an E4 result): Proofs and nullifiers made for another deployment on the same chain are accepted.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
