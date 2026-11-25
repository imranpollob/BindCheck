# XC-S04 (xchain, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V4 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | the adapter returns the caller's journal digest without verifying the seal |
| Unbound value | seal validity (RISC Zero verifier call skipped) |
| GT consumer file | `RiscZeroAdapter.sol` |
| GT function (where the unbound value enters the effect) | `verify` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol` |
| Related locations | Connector._verifyProof; all submit*Proof routes |
| Attacker effect | any journal digest is accepted on every route: mint into holding, release, refund |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/zk-proof/adapters/RiscZeroAdapter.sol
-        _RISC0_VERIFIER.verify(seal, imageId, commitment);
+++ edited
```
