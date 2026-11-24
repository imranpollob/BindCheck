# RP-S01: constant public input: caller replaced by `address(this)` in the proof statement

- Host: `redpacket`. Pattern: **P1**. Mutated layer: consumer.
- Operator: constant public input: caller replaced by `address(this)` in the proof statement.
- Binding broken: caller identity (`msg.sender`) is no longer a public input of the proof; the proof binds only the passcode hash and a constant.
- Consumer file and function: `contracts/RedPacket.sol :: open`.
- Unbound value: msg.sender (claimer / payout recipient).
- Expected effect (prediction, not an E4 result): Anyone who observes one claimer's proof (made for address(this)) replays it from any number of fresh addresses and drains the packet without knowing the passcode.
- Honest path: Honest prover must use addr = contract address; honest claim still works (proof for that statement verifies).
- Edits (see `make_mutants.py`):
- `contracts/RedPacket.sol`: 1 exact replacement(s)
