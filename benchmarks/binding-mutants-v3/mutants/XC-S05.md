# XC-S05 (xchain, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | after a transfer is released/cleaned up, the same lock proof is accepted again |
| Unbound value | durable replay key of the lock route (destinationLockAccepted) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `_enforceDestinationLockPreconditions` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol` |
| Related locations | Connector._submitLockProofImpl; Connector._cleanupTx; Connector.submitAckProof |
| Attacker effect | the same deposit is minted into holding again and (with the same ack proof) paid out again |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-        if (destinationLockAccepted[_txId]) revert Errors.DestinationLockAlreadyAccepted(_txId);
+++ edited
```
