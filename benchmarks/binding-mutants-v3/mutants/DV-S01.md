# DV-S01 (davinci, P2, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-X3 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | caller-supplied roster keys are no longer authenticated against the stored participants |
| Unbound value | recipient roster keys X_i (rosterKeys calldata) |
| GT consumer file | `CouncilManager.sol` |
| GT function (where the unbound value enters the effect) | `deal` |
| Edited file(s) | `baselines/davinci/solidity/src/CouncilManager.sol` |
| Related locations | CouncilManager.deal pub[39..70]; CouncilCurve.authenticate; c.participants |
| Attacker effect | a dealing whose shares are encrypted to attacker-chosen keys is accepted and folded into the ceremony key; the attacker learns other members' shares |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/solidity/src/CouncilManager.sol
-                CouncilCurve.authenticate(x, y, c.participants[i].compressedX);
+++ edited
```
