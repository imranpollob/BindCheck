# DV-S05 (davinci, P4, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-V1 (see `OPERATORS.md`) |
| Pattern | P4 |
| Broken binding | DealVerifier returns true for any in-field input |
| Unbound value | dealing proof validity (pairing result discarded) |
| GT consumer file | `DealVerifier.sol` |
| GT function (where the unbound value enters the effect) | `verifyProof` |
| Edited file(s) | `baselines/davinci/solidity/src/verifiers/DealVerifier.sol` |
| Related locations | CouncilManager.deal |
| Attacker effect | unproven dealings (arbitrary commitments and shares) are folded into the ceremony key |
| Notes | Edit in the committed snarkjs verifier. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/davinci/solidity/src/verifiers/DealVerifier.sol
-            mstore(0, isValid)
+++ edited
+            mstore(0, 1)
```
