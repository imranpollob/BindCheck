# ZK-D01 (decoy, zkerc20, consumer/verifier-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | DEC-1 (see `OPERATORS.md`) |
| Edited file(s) | `baselines/zkerc20/contracts/TransactionKeeper.sol` |
| Location | `TransactionKeeper.sol` / `_checkProof` |
| Why it stays bound | `if (!valid) { return false; }` follows, and every caller wraps _checkProof in require(...) |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
--- baselines/zkerc20/contracts/TransactionKeeper.sol
-        require(valid, "_checkProof: invalid proof");
+++ edited
```
