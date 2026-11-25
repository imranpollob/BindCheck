# ZK-C01 (zkerc20, P1, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | input note's `owner` is no longer constrained to be 0 or the public `sender` |
| Unbound value | spender identity of an owner-locked input note (note owner vs public `sender`) |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `split` |
| Edited file(s) | `baselines/zkerc20/circuits/circuit.circom` |
| Related locations | circuits/circuit.circom Split (input-note loop); TransactionKeeper._checkProof (pub[0]=sender); Node.unlock; ZKERC20.transferFrom |
| Attacker effect | ZKERC20.transferFrom -> TransactionKeeper.split nullifies a victim's owner-locked notes and inserts attacker-chosen output commitments (theft of the note's value); same for Node.unlock -> drop |
| Notes | Circuit-only edit; verifier.sol unchanged (built from the clean circuit). Exploit needs the note salt, which the note's creator (payer) knows. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/circuit.circom
-        // either owner is 0 (salt only auth)
-        // or owner is the sender (owner+salt auth)
-        commitments[i].owner * (sender - commitments[i].owner) === 0;
+++ edited
```
