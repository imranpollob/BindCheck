# RP-S06: sender re-encoded to its low 32 bits before it is used as the public input

- Host: `redpacket`. Pattern: **P5**. Mutated layer: consumer.
- Operator: sender re-encoded to its low 32 bits before it is used as the public input.
- Binding broken: the proved identity is `uint32(msg.sender)`, not the 160-bit address (encoding mismatch with the circuit's `addr` field).
- Consumer file and function: `contracts/RedPacket.sol :: open`.
- Unbound value: full address (only 32 bits are in the statement).
- Expected effect (prediction, not an E4 result): Verifier accepts the proof for the truncated value; any sender whose address shares the low 32 bits (about 2^32 vanity grinding) reuses a victim's observed proof and takes a slot. The standard client (full address) would be rejected, so honest compatibility needs a client that uses the consumer's truncation.
- Honest path: Honest claim works for a prover using the consumer's truncated encoding.
- Edits (see `make_mutants.py`):
- `contracts/RedPacket.sol`: 1 exact replacement(s)
