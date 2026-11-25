# KK-S04 (kakushi, P1, consumer/verifier-side)

| Field | Value |
|---|---|
| Operator | OP-P2 (see `OPERATORS.md`) |
| Pattern | P1 |
| Broken binding | ext_data_hash no longer commits to the call data |
| Unbound value | private-call calldata `data` |
| GT consumer file | `KakushiPool.sol` |
| GT function (where the unbound value enters the effect) | `withdrawAndCall` |
| Edited file(s) | `baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol` |
| Related locations | KakushiPool.extDataHash; PrivateCallExecutor.execute |
| Attacker effect | a front-runner replays the proof with different calldata to the same target (e.g. a payment router paying the attacker) |
| Notes | Clients must use the contract's extDataHash/callPublicInputs (the honest path does). |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/kakushi/packages/contracts/src/privacy/KakushiPool.sol
-        return uint256(keccak256(abi.encode(target, data, refundTo, block.chainid, address(this)))) % FIELD_SIZE;
+++ edited
+        return uint256(keccak256(abi.encode(target, refundTo, block.chainid, address(this)))) % FIELD_SIZE;
```
