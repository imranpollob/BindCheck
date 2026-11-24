# OR-S03: snapshot check removed

- Host: `orc`. Pattern: **P2**. Mutated layer: consumer.
- Operator: snapshot check removed.
- Binding broken: proof is not bound to this contract's configured snapshot (policy).
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: snapshot.
- Expected effect (prediction, not an E4 result): A proof computed for a later snapshot (more commits counted, new accounts) is accepted.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
