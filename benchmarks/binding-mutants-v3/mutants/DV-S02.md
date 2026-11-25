# DV-S02 (davinci, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | a dealer's slot is no longer checked before accepting a dealing |
| Unbound value | replay key of a dealing (dealer bit in qualBitmap) |
| GT consumer file | `CouncilManager.sol` |
| GT function (where the unbound value enters the effect) | `deal` |
| Edited file(s) | `baselines/davinci/solidity/src/CouncilManager.sol` |
| Related locations | CouncilManager.deal (_fold, qualBitmap, dealtCount); CouncilManager.finalize |
| Attacker effect | anyone can resubmit a signed, proven dealing; its commitments are folded twice and dealtCount over-counts |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/solidity/src/CouncilManager.sol
-        if (c.qualBitmap & bit != 0) revert AlreadyDealt();
+++ edited
```
