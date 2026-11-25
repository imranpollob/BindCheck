# XC-D01 (decoy, xchain, consumer/verifier-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | DEC-5 (see `OPERATORS.md`) |
| Edited file(s) | `baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol` |
| Location | `RiscZeroAdapter.sol` / `verify` |
| Why it stays bound | every Connector route calls _checkRouteImageId first, which pins the payload's image ID to the route's stored image ID |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
--- baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol
-        if (!_allowedImageIds[imageId]) revert Errors.ImageIdNotAllowed(imageId);
+++ edited
```
