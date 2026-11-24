# PV-S09: yield index narrowed to uint64 when valuing borrow collateral

- Host: `privacyvaults`. Pattern: **P5**. Mutated layer: consumer.
- Operator: yield index narrowed to uint64 when valuing borrow collateral.
- Binding broken: collateral value is computed from `uint64(_yieldIndex)`, not the proved public input.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: borrow`.
- Unbound value: _yieldIndex (low 64 bits used for the effect).
- Expected effect (prediction, not an E4 result): Verifier accepts the honest proof; collateralValue and maxBorrow are computed from the truncated value, so the LTV bound is inflated and the borrower takes a loan far above 70% of the proved note value.
- Honest path: Honest proof is accepted; the loan limit is wrong.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
