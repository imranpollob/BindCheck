# ZK-C04 (zkerc20, P1, circuit-side)

| Field | Value |
|---|---|
| Operator | OP-C1 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | public `leftCommitment` is not tied to (asset, leftAmount, salt, owner) of the conserved split |
| Unbound value | value of the left output note (public `leftCommitment`) |
| GT consumer file | `TransactionKeeper.sol` |
| GT function (where the unbound value enters the effect) | `drop` |
| Edited file(s) | `baselines/zkerc20/circuits/circuit.circom` |
| Related locations | circuits/circuit.circom Split (output commitments); TransactionKeeper.split/insert; Node.unlock |
| Attacker effect | drop/unlock: contract-computed burn commitment for `amount` is accepted regardless of input value -> Node.unlock transfers `amount` ERC-20s; split inserts an arbitrary left note |
| Notes | Circuit-only edit; verifier unchanged. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/zkerc20/circuits/circuit.circom
-    left.commitment === leftCommitment;
+++ edited
```
