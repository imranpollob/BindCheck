# KK-C02 (kakushi, P2, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C2 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | the note commitment is no longer proven to be under the public `root` |
| Unbound value | membership of the spent commitment in a known pool root |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `_spend` |
| Edited file(s) | `baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr` |
| Related locations | shielded_withdraw main; KakushiPool._spend isKnownRoot |
| Attacker effect | withdraw without a deposit (drains the pool) |
| Notes | Circuit-only edit; verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr
-    assert(compute_root(commitment, path, path_bits) == root, "commitment not in tree");
+++ edited
```
