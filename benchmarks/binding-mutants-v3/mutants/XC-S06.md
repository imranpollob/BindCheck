# XC-S06 (xchain, P2, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-X4 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | destination accepts a refund-claim proof without the configured finality delay after ackDeadline |
| Unbound value | finality of the observed origin state (refund-claim event) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `submitRefundClaimProof` |
| Edited file(s) | `baselines/xchain/smart-contracts/src/connectors/Connector.sol` |
| Related locations | Connector._enforceFinality; Connector.executeBurn |
| Attacker effect | a refund claim from a non-final (reorgable) origin block unlocks the destination burn path while the origin transfer may still complete |
| Notes | Weak: needs an origin reorg past ackDeadline. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/smart-contracts/src/connectors/Connector.sol
-        _enforceFinality(tx_.sourceChainId, tx_.ackDeadline);
+++ edited
```
