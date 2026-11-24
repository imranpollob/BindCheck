# PV-S01: recipient public input replaced by constant 0 (circuit leaves the recipient word unconstrained)

- Host: `privacyvaults`. Pattern: **P1**. Mutated layer: consumer.
- Operator: recipient public input replaced by constant 0 (circuit leaves the recipient word unconstrained).
- Binding broken: payout recipient `_recipient` is not fixed by the proof.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: _recipient.
- Expected effect (prediction, not an E4 result): A front-runner copies a withdrawal proof from the mempool and calls withdraw with their own `_recipient`, taking the payout.
- Honest path: Honest prover proves with recipient word 0; withdraw works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
