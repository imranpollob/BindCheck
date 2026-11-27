# DEV-F14 / P1 — meridian-link

**Frozen result:** `VIOLATION / UNBOUND_EFFECT_AMOUNT` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F14--result.json>)). **Revision:** `5a5a9f6eb2983ea38fb9475c9cd781514569e166`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F14--RippnerLabs__meridian-link--5a5a9f6eb298/`.

- **Verifier reality and wiring:** The flagged `evm-bridge/contracts/SolDepositVerifier.sol:77,178` uses a real pairing precompile; `evm-bridge/contracts/evm-bridge.sol:4,85-86,132-141` calls it, and `evm-bridge/scripts/deploy.ts:116-124` constructs/passes it. Its equal gamma/delta key is separately reviewed in [F14/P4](DEV-F14-P4.md).
- **Pattern and policy:** `processWithdrawal` checks a proof but transfers `record.amount` (`evm-bridge.sol:114-146`) without comparing it to a public signal. `evm-bridge/README.md:164-182` states the Solana deposit record has an amount and signal `[3]` is amount. That supports the intended rule that withdrawal quantity equals the proof-authorized deposit quantity; a caller-chosen record amount is not plausibly authorized. The README's four-signal example differs from the seven-signal Solidity verifier, so exact signal mapping still needs human inspection.
- **Scope:** A usable state root, funded bridge, accepted proof and committed transfer were not tested in this lane. The source warning is E1, not an E4 bridge exploit.

**AI opinion:** `TRUE` for the source amount-binding gap at the selected consumer, subject to policy/signal-map review. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
