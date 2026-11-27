# DEV-F35 / P1 — ShadowSats

**Frozen result:** `VIOLATION / UNBOUND_EFFECT_AMOUNT` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F35--result.json>)). **Revision:** `c08a9bca6903ece8ebb86090b79d77f6eec56d90`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F35--sambitsargam__ShadowSats--c08a9bca6903/`.

- **Verifier reality:** `contract/DarkPoolVerifier.sol:6-12` says “Stub verifier. In production, replace this with the Circom-generated verifier contract” and accepts nonempty proof/commitments. There is no pairing verification here.
- **Wiring:** `contract/DarkPool.sol:54-63` receives a verifier address in its constructor and owner setter, then calls `verifier.verifyProof(proof, commitments)` at `:141`. The flagged stub is interface-compatible, but no deployment script selecting that exact address was found in the inspected repo. Which verifier is actually used is `UNRESOLVED`.
- **Policy:** `README.md:29-30` says proofs attest hidden price/size/side/nonce and that batches correspond to committed orders. `DarkPool.sol:152-164` debits each maker's balance by caller-supplied `sizes[i]`; the only verified vector is commitments, and the function is restricted to `onlyMatcher` (`:42-43,138`). If the matcher is trusted to set fills, this may be intentional; if the proof must bind fill sizes, it is a gap. The README calls this verifier a stub (`:25-26,139`).

**AI opinion:** `UNDECIDABLE` until the matcher trust/policy and production verifier are fixed by a human. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
