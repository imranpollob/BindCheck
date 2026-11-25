# KK-S05 (kakushi, P5, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-E2 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | the consumer pays the principal to the proved relayer and the fee to the proved recipient |
| Unbound value | role of proved addresses (recipient vs relayer) in the payout |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `withdraw` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool._publicInputs pi[2], pi[3] |
| Attacker effect | the relayer named in the proof receives denomination - fee |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-            address(recipient).sendNative(denomination - fee);
-            if (fee > 0) address(relayer).sendNative(fee);
+++ edited
+            address(relayer).sendNative(denomination - fee);
+            if (fee > 0) address(recipient).sendNative(fee);
```
