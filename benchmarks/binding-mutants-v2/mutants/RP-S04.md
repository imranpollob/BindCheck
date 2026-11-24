# RP-S04: pairing result ignored: failing pairing returns success code

- Host: `redpacket`. Pattern: **P4**. Mutated layer: consumer.
- Operator: pairing result ignored: failing pairing returns success code.
- Binding broken: verifier accepts proofs whose pairing check fails.
- Consumer file and function: `contracts/Verifier.sol :: verify (called from RedPacket.sol :: open)`.
- Unbound value: whole proof statement.
- Expected effect (prediction, not an E4 result): Every proof is accepted: anyone claims any packet with a garbage proof.
- Honest path: Honest claim works (and so does every forgery).
- Edits (see `make_mutants.py`):
- `contracts/Verifier.sol`: 1 exact replacement(s)
