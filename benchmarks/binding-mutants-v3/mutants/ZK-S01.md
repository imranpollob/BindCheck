# ZK-S01 (zkerc20, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | spent-nullifier set is never written |
| Unbound value | replay key (nullifiers are checked but never recorded) |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `_checkProof` |
| Edited file(s) | `baselines/zkerc20/contracts/TransactionKeeper.sol` |
| Related locations | TransactionKeeper._checkProof; Node.unlock; ZKERC20._burn |
| Attacker effect | the same unlock/transfer proof (or the same notes) is accepted repeatedly; Node.unlock drains the locked ERC-20s |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/contracts/TransactionKeeper.sol
-            spent[nullifiers[i]] = true;
+++ edited
```
