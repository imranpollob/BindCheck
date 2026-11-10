# DEV-F49 / P1 — Planetary Entropy Mining

**Frozen result:** `VIOLATION / UNBOUND_EFFECT_RECIPIENT` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F49--result.json>)). **Revision:** `979468c59d474f1363b9caf065e962ed10901371`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F49--KELLERBABG__Planetary-Entropy-Mining--979468c59d47/`.

- **Verifier reality and wiring:** `contracts/src/Verifier.sol:6-15,20-45` explicitly calls itself a “Drop-in stand-in” and returns true after structural checks, with no pairing. `EntropySettlement.sol:21,39-45,74-76` takes the verifier address at deployment; exact deployment selection is MISSING.
- **Policy:** The consumer states “Paid out to the node that mined the entropy window” for immutable `payee` (`EntropySettlement.sol:23-27,39-45`). It requires `msg.value >= price`, transfers exactly `price` to that payee and refunds surplus to the caller (`:61-87`). Its own comment says “the only input we trust to bind the payment is the nullifier” (`:54-60`). A fixed beneficiary and price paid by the caller are plausibly intentional; the proof is not supposed to authorize either. The stand-in verifier is a separate limitation.

**AI opinion:** `INTENDED-BEHAVIOUR` for the flagged recipient/amount relationship. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
