# DEV-F14 / P4 — meridian-link

**Frozen result:** `VIOLATION / GAMMA_EQUALS_DELTA_SOURCE_KEY` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F14--result.json>)). **Revision:** `5a5a9f6eb2983ea38fb9475c9cd781514569e166`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F14--RippnerLabs__meridian-link--5a5a9f6eb298/`.

- **Verifier reality:** `evm-bridge/contracts/SolDepositVerifier.sol:36-43` has equal gamma/delta coordinates and `:178` invokes pairing precompile 8. This is a real pairing verifier.
- **Consumer wiring:** `evm-bridge/contracts/evm-bridge.sol:4,85-86,132-141` imports/calls this named verifier. `evm-bridge/scripts/deploy.ts:116-124` deploys `SolDepositVerifier` and passes its address to `SolanaEVMBridge`. The flagged file is the script-selected source verifier; live address correspondence is MISSING.
- **Policy:** `evm-bridge/README.md:164-182` describes a Solana withdrawal record, including amount, and public signal `[3]` as amount. The actual `processWithdrawal` transfers `record.amount` after proof verification (`evm-bridge.sol:114-146`). Arbitrary proof acceptance conflicts with the stated verification step.
- **P4 setup:** The executable `circom/Makefile:11-15` creates `1_0000.zkey` by `groth16 setup` and exports the same key with **no** contribution. `circom/README.md:716-731` instead shows one contribution before export, and `:775-802` describes further contributions. The Makefile path predicts gamma = delta; the README is a conflicting recommended ceremony. The committed verifier's equal points match the uncontributed shape, but exact zkey provenance is MISSING.

**AI opinion:** `TRUE` as a used source-key flaw; no E3/E4, deployed exposure, or circuit/key provenance established. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
