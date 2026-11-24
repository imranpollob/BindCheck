# OR-S01: sender check removed

- Host: `orc`. Pattern: **P1**. Mutated layer: consumer.
- Operator: sender check removed.
- Binding broken: the claim is no longer bound to `msg.sender` (public value `ethAddress`).
- Consumer file and function: `src/OrcClaim.sol :: claim`.
- Unbound value: msg.sender (whose account is credited).
- Expected effect (prediction, not an E4 result): A front-runner submits a victim's observed (publicValues, proof); the claim and nullifier are recorded for the attacker (Claimed(account=msg.sender)), consuming the victim's one-per-account slot.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `src/OrcClaim.sol`: 1 exact replacement(s)
