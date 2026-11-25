# KK-S06 (kakushi, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V1 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | a reverting verifier call (how the bb verifier rejects invalid proofs) is swallowed by an empty catch |
| Unbound value | proof validity (verifier revert swallowed) |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `_spend` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | ShieldedWithdrawVerifier.verify; KakushiPool.withdraw; KakushiPool.withdrawAndCall |
| Attacker effect | any proof bytes are accepted: withdraw/withdrawAndCall pay out without a valid proof |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-        // the bb verifiers revert (rather than return false) on most failures: normalise both
-        try verifier.verify(proof, _publicInputs(root, nullifierHash, recipient, relayer, fee, refund, extHash)) returns (
-            bool ok
-        ) {
-            if (!ok) revert Errors.InvalidProof();
-        } catch {
-            revert Errors.InvalidProof();
-        }
+++ edited
+        try verifier.verify(proof, _publicInputs(root, nullifierHash, recipient, relayer, fee, refund, extHash)) returns (
+            bool ok
+        ) {
+            if (!ok) revert Errors.InvalidProof();
+        } catch {}
```
