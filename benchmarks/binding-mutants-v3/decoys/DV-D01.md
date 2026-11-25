# DV-D01 (decoy, davinci, circuit-side)

Semantic-preserving edit: looks like a removed binding check, but the binding still holds.

| Field | Value |
|---|---|
| Decoy operator | DEC-3 (see `OPERATORS.md`) |
| Edited file(s) | `baselines/davinci/circuits/deal.circom` |
| Location | `deal.circom` / `Deal` |
| Why it stays bound | ctxHi/ctxLo still appear in constraints (Num2Bits(128) range checks and the Poseidon mask inputs), so they keep a non-zero verifier coefficient and stay bound |

Any binding warning on this tree counts as a false alarm (`MATCHING.md`).

## Edit
```diff
--- baselines/davinci/circuits/deal.circom
-    pubSq[0] <== ctxHi * ctxHi;
-    pubSq[1] <== ctxLo * ctxLo;
+++ edited
+    pubSq[0] <== 0;
+    pubSq[1] <== 0;
```
