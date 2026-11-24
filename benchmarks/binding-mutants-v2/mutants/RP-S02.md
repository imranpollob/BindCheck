# RP-S02: stored passcode hash replaced by a caller-supplied argument

- Host: `redpacket`. Pattern: **P2**. Mutated layer: consumer.
- Operator: stored passcode hash replaced by a caller-supplied argument.
- Binding broken: proof is not bound to the red packet's stored `passcodeHash`.
- Consumer file and function: `contracts/RedPacket.sol :: open`.
- Unbound value: passcodeHash (public input 0).
- Expected effect (prediction, not an E4 result): Caller proves knowledge of a passcode for a hash of their own choosing and withdraws from any packet.
- Honest path: Honest claim works when the caller passes the packet's real hash.
- Edits (see `make_mutants.py`):
- `contracts/RedPacket.sol`: 1 exact replacement(s)
- `contracts/RedPacket.sol`: 1 exact replacement(s)
