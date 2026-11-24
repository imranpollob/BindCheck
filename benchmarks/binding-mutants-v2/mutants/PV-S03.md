# PV-S03: root-admission check removed in borrow

- Host: `privacyvaults`. Pattern: **P2**. Mutated layer: consumer.
- Operator: root-admission check removed in borrow.
- Binding broken: the proved Merkle root is not bound to the vault's own tree.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: borrow`.
- Unbound value: _root.
- Expected effect (prediction, not an E4 result): Attacker borrows up to 70% LTV against a fabricated collateral note.
- Honest path: Honest borrow works.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
