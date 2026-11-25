# DK-D01 (decoy, dark, consumer/verifier-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | DEC-2 (see `OPERATORS.md`) |
| Edited file(s) | `baselines/dark/contracts/src/DarkVault.sol` |
| Location | `DarkVault.sol` / `withdraw` |
| Why it stays bound | replay of the same withdraw proof is still rejected: the statement includes the account's available ciphertext, which every withdraw changes (amount >= 1) |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
--- baselines/dark/contracts/src/DarkVault.sol
-        a.netInflow = amount >= a.netInflow ? 0 : uint128(a.netInflow - amount);
-        a.nonce += 1;
+++ edited
+        a.netInflow = amount >= a.netInflow ? 0 : uint128(a.netInflow - amount);
```
