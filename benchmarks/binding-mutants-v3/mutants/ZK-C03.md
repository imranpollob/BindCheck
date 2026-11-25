# ZK-C03 (zkerc20, P3, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C3 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | public `nullifiers[i]` no longer equal the input note's derived nullifier |
| Unbound value | nullifier (replay key) of each input note |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `_checkProof` |
| Edited file(s) | `baselines/zkerc20/circuits/circuit.circom` |
| Related locations | circuits/circuit.circom Split; TransactionKeeper._checkProof spent[] loop |
| Attacker effect | the same note is spent repeatedly with fresh arbitrary nullifiers; `spent[]` never collides (double spend / unlock drain) |
| Notes | Circuit-only edit; verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/circuit.circom
-        commitments[i].nullifier === nullifiers[i];
+++ edited
```
