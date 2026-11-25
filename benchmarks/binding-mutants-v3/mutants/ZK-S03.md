# ZK-S03 (zkerc20, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V1 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | verifyProof returns true for any proof with in-field inputs |
| Unbound value | proof validity (pairing result discarded) |
| GT consumer file | `verifier.sol` |
| GT function (where the unbound value enters the effect) | `verifyProof` |
| Edited file(s) | `baselines/zkerc20/circuits/verifier.sol` |
| Related locations | TransactionKeeper._checkProof; TransactionKeeper._verifyInsertProof |
| Attacker effect | any statement is accepted: arbitrary splits/unlocks drain the Node |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/verifier.sol
-            mstore(0, isValid)
+++ edited
+            mstore(0, 1)
```
