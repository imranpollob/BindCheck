# XC-G01 (xchain, P2, guest-side)

| Field | Value |
|---|---|
| Operator | OP-G1 (see `OPERATORS.md`) |
| Pattern | P2 |
| Broken binding | guest no longer requires the observed destination block to be at/after ackDeadline |
| Unbound value | the destination block the non-acceptance observation is taken at (may predate ackDeadline) |
| GT consumer file | `Connector.sol` |
| GT function (where the unbound value enters the effect) | `submitNonAcceptanceProof` |
| Edited file(s) | `baselines/xchain/zk-proofs/risc_zero/non_accept_event/core/src/lib.rs` |
| Related locations | non_accept_event guest main.rs; Connector.submitNonAcceptanceProof (refund); Connector.submitLockProof |
| Attacker effect | a refund on the origin is proven from a destination state before the lock could be accepted; the destination can still accept and later pay -> same deposit released twice |
| Notes | Guest-side edit in the core crate (compiled natively with cargo check). Disjoint from KB-1 (anchor of the remote state). |

## Edit (exact match, applied by `make_mutants.py`)
```diff
--- baselines/xchain/zk-proofs/risc_zero/non_accept_event/core/src/lib.rs
-    if block_timestamp < ack_deadline {
-        return Err(NonAcceptValidationError::TooEarly {
-            ack_deadline,
-            block_timestamp,
-        });
-    }
+++ edited
```
