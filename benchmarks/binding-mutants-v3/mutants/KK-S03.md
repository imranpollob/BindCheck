# KK-S03 (kakushi, P3, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-R1 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | spent set never written |
| Unbound value | replay key (nullifier hash checked but never recorded) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `_spend` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool.withdraw; KakushiPool.withdrawAndCall |
| Attacker effect | the same withdraw proof is accepted again until the pool is drained |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-        nullifierHashes[nullifierHash] = true;
+++ edited
```
