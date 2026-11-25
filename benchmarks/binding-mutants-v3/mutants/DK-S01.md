# DK-S01 (dark, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V3 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | the withdraw verifier skips the Shplemini batch-opening check |
| Unbound value | proof soundness (PCS opening / final pairing check skipped) |
| GT consumer file | `Verifier.sol` |
| GT function (where the unbound value enters the effect) | `verify` |
| Edited file(s) | `baselines/dark/circuits/verifiers/withdraw/Verifier.sol` |
| Related locations | DarkVault.withdraw; DarkVault._withdrawInputs |
| Attacker effect | forged withdraw proofs pass; DarkVault.withdraw pays USDG not backed by the encrypted balance |
| Notes | Edit in the committed (vendored) bb verifier. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/dark/circuits/verifiers/withdraw/Verifier.sol
-        require(verifyShplemini(p, vk, t), Errors.ShpleminiFailed());
+++ edited
```
