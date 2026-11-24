# PV-S11: borrow recipient public input replaced by constant 0

- Host: `privacyvaults`. Pattern: **P1**. Mutated layer: consumer.
- Operator: borrow recipient public input replaced by constant 0.
- Binding broken: loan recipient `_recipient` is not fixed by the proof.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: borrow`.
- Unbound value: _recipient.
- Expected effect (prediction, not an E4 result): A front-runner copies a borrow proof and receives the loan against someone else's collateral note.
- Honest path: Honest prover proves with recipient word 0; borrow works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
