# RP-S05: public-input range check removed

- Host: `redpacket`. Pattern: **P4**. Mutated layer: consumer.
- Operator: public-input range check removed.
- Binding broken: public inputs are not required to be < the scalar field (aliasing x and x+r).
- Consumer file and function: `contracts/Verifier.sol :: verify (called from RedPacket.sol :: open)`.
- Unbound value: public inputs (passcodeHash, sender) as field elements.
- Expected effect (prediction, not an E4 result): Public inputs become aliasable. Exploitability in this consumer is limited (sender is a 160-bit address; passcodeHash is creator-chosen): a weak mutant, scored as P4 by GUIDE shape.
- Honest path: Honest claim works.
- Edits (see `make_mutants.py`):
- `contracts/Verifier.sol`: 1 exact replacement(s)
