# OR-S04: notary-key pin removed

- Host: `orc`. Pattern: **P2**. Mutated layer: consumer.
- Operator: notary-key pin removed.
- Binding broken: TLS attestation key is not pinned to the configured notary.
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: notaryKeyHash.
- Expected effect (prediction, not an E4 result): Any notary key (attacker-run) can attest the GitHub session.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
