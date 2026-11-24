# PV-C03: collateral-nullifier binding removed from the borrow circuit

- Host: `privacyvaults`. Pattern: **P3**. Mutated layer: circuit.
- Operator: collateral-nullifier binding removed from the borrow circuit.
- Binding broken: public `collateral_nullifier_hash` (loan key) is free.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: borrow`.
- Unbound value: collateral_nullifier_hash.
- Expected effect (prediction, not an E4 result): One collateral note backs unlimited loans under fresh loan keys. NOTE: committed BorrowVerifier.sol not regenerated; circuit-layer target.
- Honest path: nargo compile only.
- Edits (see `make_mutants.py`):
- `circuits_borrow/src/main.nr`: 1 exact replacement(s)
