# DEV-F27 / P3 — CropChain

**Frozen result:** `VIOLATION / REPLAY_KEY_NOT_BOUND_TO_PROOF` ([ledger](../../reports/freeze2/dev-ledger.csv); [raw](</Users/imranpollob/Coding/bc/bindcheck-zk/results/raw/coverage/after-20261109T165844Z-58315/DEV-F27--result.json>)). **Revision:** `ae1e95e99c504018b4f43acd2ca7d1c59b3f116d`. Source root: `/Users/imranpollob/Coding/bc/bindcheck-zk/feasibility/work/full-dev/DEV-F27--Nitya-003__CropChain--ae1e95e99c50/`.

- **Verifier reality:** `smart-contracts/contracts/Verifier.sol:39-44` explicitly labels its condition “Mock verification” and returns true for nonzero `a`; there is no pairing. It does apply a scalar range screen (`:32-37`), which does not make it a Groth16 verifier.
- **Consumer wiring:** `smart-contracts/contracts/CropChain.sol:856-857` lets the owner set `verifierAddress`. `verifyQualityAttestation` calls that address only when nonzero (`:880-883`); at zero it accepts without verifying any proof. No deployment address tying this source mock to the consumer was established.
- **Policy:** The function comment says it “Protects against replay attacks using spentProofHashes” (`CropChain.sol:862-864`). It checks/sets a caller-supplied `proofHash` at `:871-878`, but never computes it from `a,b,c,input`. The anti-replay mechanism is bypassable by changing the hash; the optional-verifier branch is a separate issue. The intended one-attestation-per-batch rule is suggested by `qualityAttestationVerified[batchId]` at `:878`, but an explicit policy is MISSING.

**AI opinion:** `UNDECIDABLE` for a Groth16 binding finding because the matched verifier is a mock and optional; the independent replay-key source flaw is visible. **Human label:** ____  **Human reviewer/date:** ____  **Reason or correction:** ____
