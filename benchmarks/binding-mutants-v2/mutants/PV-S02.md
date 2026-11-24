# PV-S02: root-admission check removed in withdraw

- Host: `privacyvaults`. Pattern: **P2**. Mutated layer: consumer.
- Operator: root-admission check removed in withdraw.
- Binding broken: the proved Merkle root is not bound to the vault's own tree (`isKnownRoot`).
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: _root.
- Expected effect (prediction, not an E4 result): Attacker builds their own tree with a self-made commitment and withdraws DENOMINATION from the vault.
- Honest path: Honest withdraw works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
