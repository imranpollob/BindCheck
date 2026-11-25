# KK-D01 (decoy, kakushi, circuit-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | DEC-4 (see `OPERATORS.md`) |
| Edited file(s) | `baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr` |
| Location | `main.nr` / `main` |
| Why it stays bound | recipient is still a public input of the committed UltraHonk verifier (bound by the transcript), and the consumer always passes a uint160 address |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
--- baselines/kakushi/packages/zk/circuits/shielded_withdraw/src/main.nr
-    recipient.assert_max_bit_size::<160>();
+++ edited
```
