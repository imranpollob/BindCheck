# PV-S08: yield index narrowed to uint64 when computing the withdraw payout (verifier still gets the full word)

- Host: `privacyvaults`. Pattern: **P5**. Mutated layer: consumer.
- Operator: yield index narrowed to uint64 when computing the withdraw payout (verifier still gets the full word).
- Binding broken: the payout is computed from `uint64(_yieldIndex)`, not the 254-bit proved public input.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: _yieldIndex (low 64 bits used for the effect).
- Expected effect (prediction, not an E4 result): Verifier accepts the honest proof; the payout divides by the truncated value (about 1e27 truncates to an unrelated 64-bit number), so the effect is not what the proved statement entitles; a note's payout can be inflated far beyond DENOMINATION.
- Honest path: Honest proof is accepted; the effect (payout amount) is wrong.
- Edits (see `make_mutants.py`):
- `contracts/src/PrivacyVault.sol`: 1 exact replacement(s)
