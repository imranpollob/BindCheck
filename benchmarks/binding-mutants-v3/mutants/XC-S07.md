# XC-S07 (xchain, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-K1 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | neither the route's stored image ID nor the adapter allowlist is enforced (two-line edit: both pins removed) |
| Unbound value | RISC Zero image ID (program identity) taken from the caller's proof payload |
| GT consumer file | `RiscZeroAdapter.sol` |
| GT function (where the unbound value enters the effect) | `verify` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol`, `baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol` |
| Related locations | Connector._checkRouteImageId; Connector._verifyProof; RiscZeroAdapter.verify; all submit*Proof routes |
| Attacker effect | a proof of an attacker-written guest with any journal is accepted on every route: unbacked mints into holding and releases |
| Notes | Two-site edit by design: removing only one of the two pins stays bound (see decoy XC-D01). |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-        if (proofImageId != expected) {
-            revert Errors.ImageIdRouteMismatch(uint8(_route), proofImageId, expected);
-        }
+++ edited
--- baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol
-        if (!_allowedImageIds[imageId]) revert Errors.ImageIdNotAllowed(imageId);
+++ edited
```
