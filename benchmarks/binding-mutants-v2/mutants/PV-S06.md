# PV-S06: verifier return value ignored in withdraw

- Host: `privacyvaults`. Pattern: **P4**. Mutated layer: consumer.
- Operator: verifier return value ignored in withdraw.
- Binding broken: a verifier that returns false (instead of reverting) is accepted.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: whole proof statement.
- Expected effect (prediction, not an E4 result): Honk verifiers return false on a failed final pairing check; ignoring it lets forged proofs through where the failure is not a revert.
- Honest path: Honest withdraw works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
