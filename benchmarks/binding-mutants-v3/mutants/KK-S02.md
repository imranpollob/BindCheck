# KK-S02 (kakushi, P2, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-X2 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | the proved root is never compared with the pool's roots or the root oracle |
| Unbound value | Merkle root (caller-supplied, not checked against stored root history) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `_spend` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool.isKnownRoot; IRootOracle.isKnownRoot; KakushiPool.withdraw/withdrawAndCall |
| Attacker effect | a proof over an attacker-built tree withdraws `denomination` without a deposit |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-        if (!isKnownRoot(root)) {
-            if (address(rootOracle) == address(0) || !rootOracle.isKnownRoot(address(this), root)) {
-                revert Errors.UnknownRoot(root);
-            }
-        }
+++ edited
```
