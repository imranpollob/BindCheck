# DV-S04 (davinci, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V1 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | the Groth16 verifier returns false on an invalid proof; the consumer discards the result |
| Unbound value | partial-decryption proof validity (boolean result ignored) |
| GT consumer file | `CouncilManager.sol` |
| GT function (where the unbound value enters the effect) | `submitPartial` |
| Edited file(s) | `baselines/davinci/solidity/src/CouncilManager.sol` |
| Related locations | PartialVerifier.verifyProof; CouncilManager.combine |
| Attacker effect | unproven decryption shares D are accepted and published for combine |
| Notes | - |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/solidity/src/CouncilManager.sol
-        if (!IPartialVerifier(partialVerifier).verifyProof(pA, pB, pC, pub)) revert ProofInvalid();
+++ edited
+        IPartialVerifier(partialVerifier).verifyProof(pA, pB, pC, pub);
```
