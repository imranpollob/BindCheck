# XC-G02 (xchain, P5, guest-side)

| Field | Value |
|---|---|
| Operator | OP-G2 (see `OPERATORS.md`) |
| Pattern | P5 |
| Broken binding | the guest commits the depositor in the receiver slot |
| Unbound value | receiver field of the lock journal (encoded from the wrong event field) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `submitLockProof` |
| Edited file(s) | `baselines/xchain/zk-proofs/risc_zero/lock_event/core/src/lib.rs` |
| Related locations | lock_event guest main.rs; Connector._submitLockProofImpl; _expectedDestinationLockCommitment; submitAckProof |
| Attacker effect | the destination records `to` = depositor and later pays the depositor, not the receiver named in DepositLocked |
| Notes | Guest-side edit in the core crate. |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/zk-proofs/risc_zero/lock_event/core/src/lib.rs
-        receiver: event.receiver,
+++ edited
+        receiver: event.sender,
```
