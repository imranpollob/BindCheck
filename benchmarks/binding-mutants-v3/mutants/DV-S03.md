# DV-S03 (davinci, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | a member's partial for a request is no longer checked before acceptance |
| Unbound value | replay key of a partial decryption (member bit in partialBitmap) |
| GT consumer file | `CouncilManager.sol` |
| GT function (where the unbound value enters the effect) | `submitPartial` |
| Edited file(s) | `baselines/davinci/solidity/src/CouncilManager.sol` |
| Related locations | CouncilManager.submitPartial; CouncilManager._published; CouncilManager.combine |
| Attacker effect | a published partial can be resubmitted; per-request partial accounting (_published) over-counts |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/solidity/src/CouncilManager.sol
-        if (r.partialBitmap & bit != 0) revert AlreadyPartial();
+++ edited
```
