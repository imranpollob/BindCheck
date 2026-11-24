# OR-S10: program verification key made mutable with an unprotected setter

- Host: `orc`. Pattern: **P4**. Mutated layer: consumer.
- Operator: program verification key made mutable with an unprotected setter.
- Binding broken: the SP1 program vkey is not pinned: anyone can replace it.
- Consumer file and function: `src/OrcClaim.sol :: claim (setProgramVKey added)`.
- Unbound value: programVKey.
- Expected effect (prediction, not an E4 result): Anyone sets the vkey to a program they control and submits their own valid proof with arbitrary publicValues.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
- `src/OrcClaim.sol`: 1 exact replacement(s)
