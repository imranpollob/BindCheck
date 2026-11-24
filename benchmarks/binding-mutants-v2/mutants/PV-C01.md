# PV-C01: Merkle membership assertion removed from the borrow circuit

- Host: `privacyvaults`. Pattern: **P2**. Mutated layer: circuit.
- Operator: Merkle membership assertion removed from the borrow circuit.
- Binding broken: borrow proof no longer shows the collateral commitment is in the tree under `root`.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: borrow`.
- Unbound value: collateral commitment membership (root).
- Expected effect (prediction, not an E4 result): Anyone proves any `collateral_nullifier_hash`/yield index for a commitment never deposited, and borrows. NOTE: the committed BorrowVerifier.sol is not regenerated; circuit-layer target.
- Honest path: nargo compile only (no honest Prover.toml in the host).
- Edits (see `make_mutants.py`):
- `circuits_borrow/src/main.nr`: 1 exact replacement(s)
