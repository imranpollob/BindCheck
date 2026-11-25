# KK-S07 (kakushi, P1, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-P1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | the native refund is sent to the transaction sender, not the recipient in the statement |
| Unbound value | refund payee (msg.sender instead of the proved recipient) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `withdraw` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool._publicInputs pi[5]; KakushiPool._spend (msg.value == refund) |
| Attacker effect | ERC-20 withdraw with refund > 0: the submitting relayer gets back the native refund it is paid (via the proved fee) to deliver to the recipient; the proved recipient receives no refund |
| Notes | Weaker than KK-S01: the refund is funded by msg.value of the submitting transaction, so the loss is the recipient's prepaid gas top-up. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-                (bool ok,) = recipient.call{value: refund}("");
+++ edited
+                (bool ok,) = payable(msg.sender).call{value: refund}("");
```
