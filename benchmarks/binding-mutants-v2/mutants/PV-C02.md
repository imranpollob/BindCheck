# PV-C02: nullifier-hash binding removed from the withdraw circuit

- Host: `privacyvaults`. Pattern: **P3**. Mutated layer: circuit.
- Operator: nullifier-hash binding removed from the withdraw circuit.
- Binding broken: public `nullifier_hash` is no longer tied to the note's secret `nullifier`.
- Consumer file and function: `contracts/src/PrivacyVault.sol :: withdraw`.
- Unbound value: nullifier_hash.
- Expected effect (prediction, not an E4 result): One note is withdrawn many times under fresh nullifier hashes. NOTE: committed Verifier.sol not regenerated; circuit-layer target.
- Honest path: nargo compile only.
- Edits (see `make_mutants.py`):
- `circuits/src/main.nr`: 1 exact replacement(s)
