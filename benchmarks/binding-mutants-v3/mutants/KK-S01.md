# KK-S01 (kakushi, P1, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-P1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | the relayer fee is paid to the transaction sender, not to the relayer in the statement |
| Unbound value | fee payee (msg.sender instead of the proved relayer) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `withdraw` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool._publicInputs pi[3]; KakushiPool._spend |
| Attacker effect | anyone who copies a pending withdraw from the mempool collects the fee |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-            address(recipient).sendNative(denomination - fee);
-            if (fee > 0) address(relayer).sendNative(fee);
+++ edited
+            address(recipient).sendNative(denomination - fee);
+            if (fee > 0) address(msg.sender).sendNative(fee);
```
