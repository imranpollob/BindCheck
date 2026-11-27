# DEV-F44 / P1 — proof-of-twitter

**Frozen result:** `VIOLATION / UNBOUND_EFFECT_RECIPIENT` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F44--result.json>)). **Revision:** `b6d9c2d6a8c99563411992ae3610ecf2afba1ee5`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F44--zkemail__proof-of-twitter--b6d9c2d6a8c9/`.

- **Verifier reality and wiring:** `packages/contracts/src/Verifier.sol:225-245` executes `Pairing.pairingProd4`, so this is a real pairing verifier. `ProofOfTwitter.sol:9,25-33,80-88` imports and stores that type; `packages/contracts/script/DeployTwitter.s.sol:25,42` constructs this verifier and passes it to the consumer.
- **Pattern and policy:** The consumer says “Check eth address committed to in proof matches msg.sender, to avoid replayability” but comments out the enforcing `require` (`ProofOfTwitter.sol:68-69`). It then calls inherited `_mint(msg.sender, tokenId)` (`:99-110`). The recipient is therefore not checked against the public address. The intent is unusually explicit in the code comment; treating this as intended gifting would contradict that comment.
- **Scope:** This is an E1 source and wiring observation. A real proof for someone else's address, successful mint, and human policy confirmation are MISSING.

**AI opinion:** `TRUE` for the correct source location. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
