# ZK-S05 (zkerc20, P5, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-E1 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | the message carries the proved local commitment instead of the proved remote one |
| Unbound value | which proved output commitment is sent to the destination chain |
| GT consumer file | `Node.sol` |
| GT function (where the unbound value enters the effect) | `bridge` |
| Edited file(s) | `baselines/zkerc20/contracts/Node.sol` |
| Related locations | TransactionKeeper.bridge; BridgeManager._sendMessage/receiveMessage; Node._receiveMessage |
| Attacker effect | the local remainder note is minted on the destination too (duplicated); destination mint not backed by the proved remote output |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/contracts/Node.sol
-            destChainId,
-            remoteCommitment
-        );
+++ edited
+            destChainId,
+            localCommitment
+        );
```
