# DK-C01 (dark, P1, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | D_recipient is not constrained to r*pk_recipient, so the recipient's credited ciphertext is not tied to the debited amount |
| Unbound value | recipient decryption handle ct.D_recipient (hence the amount credited to `to`) |
| GT consumer file | `DarkVault.sol` |
| GT function (where the unbound value enters the effect) | `transfer` |
| Edited file(s) | `baselines/dark/circuits/transfer/src/main.nr` |
| Related locations | circuits/transfer/src/main.nr main; DarkVault._transferInputs (pi[17..18]); DarkVault.applyPending; DarkVault.withdraw |
| Attacker effect | DarkVault.transfer adds an arbitrary handle to the recipient's pending balance; a colluding recipient (key known) can set it so the credit decrypts to any value -> withdraw more USDG than was debited |
| Notes | Circuit-only edit; committed transfer verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/dark/circuits/transfer/src/main.nr
-    assert(multi_scalar_mul([pk_r], [r]) == ct_dr, "ct.D_recipient != r*pk_recipient");
+++ edited
```
