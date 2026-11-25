# ZK-S02 (zkerc20, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V2 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | verifier no longer range-checks nullifiers[0] < r; the consumer keys `spent[]` on the raw uint |
| Unbound value | canonical form of public input 4 (nullifiers[0]) |
| GT consumer file | `verifier.sol` |
| GT function (where the unbound value enters the effect) | `verifyProof` |
| Edited file(s) | `baselines/zkerc20/circuits/verifier.sol` |
| Related locations | TransactionKeeper._checkProof (spent[nullifiers[i]]); Groth16Verifier.verifyProof |
| Attacker effect | nullifiers[0] + k*r verifies as the same statement but is a fresh key in `spent[]` -> double spend / repeated unlock |
| Notes | Verifier is generated (snarkjs 0.7.6) and vendored; edit in the vendored verifier. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/verifier.sol
-            checkField(calldataload(add(_pubSignals, 128)))
+++ edited
```
