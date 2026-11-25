# KK-S08 (kakushi, P5, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-E2 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | the principal goes to the proved relayer and only the fee to the executor |
| Unbound value | role of proved payees (relayer vs executor) in the ERC-20 private call |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `withdrawAndCall` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool._spend; PrivateCallExecutor.execute |
| Attacker effect | the relayer named in the proof receives denomination - fee; the private call runs on the fee |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-            if (fee > 0) token.safeTransfer(relayer, fee);
-            token.safeTransfer(address(executor), amount);
+++ edited
+            if (fee > 0) token.safeTransfer(address(executor), fee);
+            token.safeTransfer(relayer, amount);
```
