# XC-S03 (xchain, P5, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-E2 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | the proved receiver is stored as `from` and the proved sender as `to` |
| Unbound value | role of proved addresses (sender vs receiver) in the stored transfer |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `_recordDestinationLockTx` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol` |
| Related locations | Connector._submitLockProofImpl; Connector.submitAckProof |
| Attacker effect | submitAckProof later pays the depositor instead of the receiver |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-            from: _from,
-            to: _to,
+++ edited
+            from: _to,
+            to: _from,
```
