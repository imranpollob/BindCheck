# AZ1 testbed — expected outcomes (written before the first run)

Written 2026-11-17, before `run.sh` was executed for the first time and before
BindCheck or Slither was run on the testbed. Later edits to this file must be
recorded in `reports/AZ1/REPORT.md` as post-hoc.

## Fixture semantics (owned, synthetic, local only)

- Circuit `Batch(4)`: four rows `(kind, owner, amount)`. `kind` is boolean
  (`0` no-op, `1` deposit). A no-op row must have `owner = amount = 0`.
  `amount` is range-checked to 64 bits. Public outputs:
  `commitment = Poseidon4(Poseidon3(row_0), ..., Poseidon3(row_3))` over **all
  four rows**, and `creditTotal = sum(amount_i)` over **all four rows**.
- Consumer: recomputes `commitment` from the calldata rows, verifies the
  Groth16 proof on `[commitment, creditTotal]`, adds `creditTotal` to
  `totalL2Credit` (the proof-attested state effect), then settles rows
  `0 .. numRealRows-1` only. Settling a deposit row consumes
  `userPendingDeposits[owner]` (reverts if insufficient) and adds to
  `settledBacking`. `numRealRows` comes from calldata and is not a public input.
- Fixed consumer: identical, plus every row with index `>= numRealRows` must be
  a no-op (`kind == 0 && amount == 0`). Same circuit, same verifier, same proofs.

Accounting invariant (the policy): `totalL2Credit == settledBacking`, i.e. every
credited deposit consumed a real pending deposit of test tokens.

## Expected run outcomes

| step | batch | consumer | `numRealRows` | expected |
|---|---|---|---:|---|
| honest | rows `[dep(alice,100), dep(bob,50), noop, noop]` | faulty | 2 | success; credit 150, backing 150, gap 0 |
| fault condition | rows `[noop, dep(carol,1000), noop, noop]`, carol never deposited | faulty | 1 | success; credit +1000, backing +0, **gap 1000** |
| control: tampered public input | honest proof, `creditTotal` + 1 | faulty | 2 | revert (verifier rejects) |
| fixed rejects fault batch | same fault proof | fixed | 1 | revert; state unchanged |
| fixed control | same fault proof | fixed | 2 | revert (carol has no pending deposit) |
| fixed honest | honest proof | fixed | 2 | success; gap 0 |

snarkjs off-chain: both proofs verify; a tampered public signal does not.

## Tool expectations (predictions, not used to tune anything)

- BindCheck freeze 2 P1: not expected to flag the fault. The fault is an
  omitted obligation over an unbound loop extent, which P1 (unbound
  recipient/amount/identity of a committed effect) does not model. Predicted
  `UNKNOWN` or `VERIFIED_WITHIN_SCOPE`; a `VERIFIED_WITHIN_SCOPE` on the faulty
  consumer would be a semantic false negative.
- BindCheck freeze 2 P5: two public inputs on both sides; predicted no
  `PUBLIC_INPUT_COUNT_MISMATCH`.
- Slither default detectors: no detector models proof coverage; predicted no
  target-relevant warning.
