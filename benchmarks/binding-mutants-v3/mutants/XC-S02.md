# XC-S02 (xchain, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | the transfer record/status is not cleared on release |
| Unbound value | replay key of the ack (tx status not consumed) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `submitAckProof` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol` |
| Related locations | Connector._cleanupTx; requireStatus(MINTED_IN_HOLDING) |
| Attacker effect | the same ack proof releases tx_.amount repeatedly |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-        // proof is safe to submit at any time after MINTED_IN_HOLDING is reached.
-        _cleanupTx(_txId);
+++ edited
+        // proof is safe to submit at any time after MINTED_IN_HOLDING is reached.
```
