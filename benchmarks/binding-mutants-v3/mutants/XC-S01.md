# XC-S01 (xchain, P1, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-P1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | release pays the (permissionless) proof submitter |
| Unbound value | payout recipient (msg.sender instead of the stored, proved receiver) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `submitAckProof` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol` |
| Related locations | Connector._recordDestinationLockTx |
| Attacker effect | whoever submits the ack proof first takes the bridged tokens |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-        IERC20(tx_.currencyTo).safeTransfer(tx_.to, tx_.amount);
+++ edited
+        IERC20(tx_.currencyTo).safeTransfer(msg.sender, tx_.amount);
```
