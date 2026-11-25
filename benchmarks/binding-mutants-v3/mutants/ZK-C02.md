# ZK-C02 (zkerc20, P2, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C2 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | input commitments are no longer required to be in the tree under the public `root` |
| Unbound value | membership of spent notes in the consumer's stored Merkle root (`MerkleTree.root`) |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `_checkProof` |
| Edited file(s) | `baselines/zkerc20/circuits/circuit.circom` |
| Related locations | circuits/circuit.circom Split; TransactionKeeper._checkProof pub[1]=MerkleTree.root; Node.unlock |
| Attacker effect | spend notes that were never deposited: split mints value, unlock (Node.unlock -> drop) releases locked ERC-20s |
| Notes | Circuit-only edit; verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/circuit.circom
-        // either the commitment is in the tree
-        // or it represents zero tokens
-        merkleValid[i] <== verifiers[i].root - root;
-        merkleValid[i] * amounts[i] === 0;
+++ edited
+        merkleValid[i] <== verifiers[i].root - root;
```
