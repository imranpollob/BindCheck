# RP-C01: constraint removed: `out <== hash.out` replaced by unconstrained assignment `<--`

- Host: `redpacket`. Pattern: **P2**. Mutated layer: circuit.
- Operator: constraint removed: `out <== hash.out` replaced by unconstrained assignment `<--`.
- Binding broken: the public output (passcode hash) is not constrained to the MiMC of the secret.
- Consumer file and function: `contracts/RedPacket.sol :: open (consumer unchanged; verifier is the baseline one, see note)`.
- Unbound value: passcodeHash (public output).
- Expected effect (prediction, not an E4 result): A prover can choose `out` freely, so a proof exists for any stored hash: anyone claims any packet. NOTE: the baseline Verifier.sol is not regenerated, so this is a circuit-layer target for circomspect/Picus; an end-to-end claim would need a regenerated verifier (not done).
- Honest path: Circuit compiles; witness/proving not run (no node/snarkjs available).
- Edits (see `make_mutants.py`):
- `circuits/passcode.circom`: 1 exact replacement(s)
