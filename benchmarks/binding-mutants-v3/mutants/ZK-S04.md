# ZK-S04 (zkerc20, P5, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-E1 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | consumer stores the proved remote (left) commitment in the local tree instead of the proved local (right) one |
| Unbound value | which proved output commitment is stored locally (role of public slots left/right) |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `bridge` |
| Edited file(s) | `baselines/zkerc20/contracts/TransactionKeeper.sol` |
| Related locations | Node.bridge; BridgeManager._sendMessage; TransactionKeeper._checkProof (left/right order) |
| Attacker effect | the bridged note exists on both chains (local copy + remote message) -> value duplicated |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/contracts/TransactionKeeper.sol
-        localIndex = _insert(localCommitment);
+++ edited
+        localIndex = _insert(remoteCommitment);
```
