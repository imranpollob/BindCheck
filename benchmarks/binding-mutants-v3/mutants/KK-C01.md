# KK-C01 (kakushi, P3, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C3 (see `OPERATORS.md`) |
| Pattern | P3 |
| Broken binding | public nullifier_hash is not derived from the note's nullifier |
| Unbound value | nullifier hash (replay key) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `_spend` |
| Edited file(s) | `baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr` |
| Related locations | shielded_withdraw main; KakushiPool._spend nullifierHashes; KakushiPool.withdraw |
| Attacker effect | one deposit is withdrawn repeatedly under fresh nullifier hashes |
| Notes | Circuit-only edit; verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr
-    assert(nullifier_hash_of(nullifier) == nullifier_hash, "nullifier hash mismatch");
+++ edited
```
