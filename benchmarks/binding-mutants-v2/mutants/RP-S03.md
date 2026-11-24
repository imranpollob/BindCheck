# RP-S03: recipient taken from a caller argument `to` (proved) while the once-only key stays on `msg.sender`

- Host: `redpacket`. Pattern: **P3**. Mutated layer: consumer.
- Operator: recipient taken from a caller argument `to` (proved) while the once-only key stays on `msg.sender`.
- Binding broken: replay key (`withdrawedMap[id, msg.sender]`) is not bound to the proved recipient.
- Consumer file and function: `contracts/RedPacket.sol :: open`.
- Unbound value: msg.sender in the once-per-claimer key (proved identity is `to`).
- Expected effect (prediction, not an E4 result): One proof for recipient `to` is replayed by many different senders; each call pays `to` again, draining the packet's slots into `to`.
- Honest path: Honest claim works (sender == to).
- Edits (see `make_mutants.py`):
- `contracts/RedPacket.sol`: 1 exact replacement(s)
- `contracts/RedPacket.sol`: 1 exact replacement(s)
- `contracts/RedPacket.sol`: 1 exact replacement(s)
- `contracts/RedPacket.sol`: 1 exact replacement(s)
