# PV-S04: nullifier write removed in withdraw

- Host: `privacyvaults`. Pattern: **P3**. Mutated layer: consumer.
- Operator: nullifier write removed in withdraw.
- Binding broken: no replay protection for the withdraw proof.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: _nullifierHash.
- Expected effect (prediction, not an E4 result): The same withdrawal proof is submitted repeatedly; each call pays out again until the vault is drained.
- Honest path: Honest first withdraw works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
