# quantstamp notes

Agent: quantstamp. Protocol v1.3. Date: 2026-11-23. Result line: `quantstamp DONE: 18/3/6/10` (reports/IN/KEEP/BORDERLINE). DROP rows: 22.

## Extraction (deviation from the instructions)

- The report text is embedded as a JSON string, `JSON.parse('{"reportContent":...}')`, inside a JS file. It is not a set of markdown string literals.
- **2 of 18 reports (both Boba 2023) have it in `main.<hash>.js`.** The other 16 load it from a lazy webpack chunk, `static/js/<chunkid>.<hash>.chunk.js` (chunk id 310 for the ones checked). `main.js` of those 16 contains only the renderer, so searching main.js alone finds no report text.
- The chunk filename comes from `n.u=function(e){return"static/js/"+e+".<hash>.chunk.js"}` and `n.e(<id>)` in main.js.
- Method: curl index.html, then main.js, then the chunk if needed; decode the JS string literal (escape-aware); `json.loads`; walk the JSON into a `.txt` with `## <json path>` headers.
- `report_sha256` = sha256 of that `.txt` rendering, not of a raw download. The sha256 of the bundle file holding the JSON is in each row's `notes`.
- Rendered finding IDs are `<vulnIndex>-<n>` (HNKL, HIN, DCAP), n = 1-based array position; the page anchor is `#findings-qs<n>`. The JSON array is already severity-sorted, matching the page order.
- `finding_url` is the report URL plus the anchor; the page is client-rendered so the anchor is the stable pointer.

## Screen 1

- Keyword scan: full rendered text, leading-boundary regex (so `zkvm`, `snarks`, `nullifiers`, `risc0` match). A first trailing-boundary scan undercounted (zkDCAP showed 2 `zk` hits instead of 41) and was redone.
- The `zk` hits in the two Zircuit finance reports are all the repo name `zkr-yield-aggregator`. The `zk` hits in Pheasant are env var names (`ZK_SYNC_TESTNET_PROVIDER1`, `POLYGON_ZK_EVM_GOERLI_PROVIDER1`).
- Pheasant's `verifyProof` is a Merkle-Patricia/receipt proof (optimistic bridge): NO-ZK-COMPONENT.
- Datachain LCP/ELC reports (SGX remote attestation, light clients in Rust): NO-ZK-COMPONENT (TEE attestation, §3). `verifier` hits there are `light-client-verifier` crates and the IAS attestation service.
- Zircuit Merkle distributor: Merkle inclusion only, NO-ZK-COMPONENT.
- zkDCAP is IN: RISC Zero zkVM proof of DCAP quote verification is verified on-chain by `LCPClientZKDCAP`. Scope text: "this audit does not review SGX or the Risc0 zkVM themselves".

## Judgment calls (protocol clauses)

- **Verifier-soundness (§5, v1.1):** "a verifier or recursion layer that can accept an invalid proof... constant-true or always-succeeding verification... unpinned vk". HNKL-7 and HIN-12 (owner can register a malicious or arbitrary verifier) are logged BORDERLINE P4: effect is stated for HNKL-7, implied for HIN-12, and both need a compromised privileged role.
- **DCAP-3 / DCAP-4 (cert-chain checks in the zkVM guest):** v1.2 DROPs circuit-internal issues "that do not concern the public inputs, the program/vk identity, or what the on-chain verifier is told". These concern what the guest attests to before the contract registers an enclave key, so they are BORDERLINE P4, not NOT-BINDING-CIRCUIT-ONLY. The auditor's mitigation (chain must be rooted in a trusted Intel root) is recorded, not weighed. DCAP-1, -2, -5 and -7 are DROP (liveness, parsing, edge case).
- **HNKL-37 (Groth16 malleability) and HIN-4 (signature omits destination/fee):** decided on the auditor's text per §2. Client rebuttals are in `notes`. My own doubt on HNKL-37: if nullifiers are public inputs, proof malleability alone does not normally permit double spend, so a human label may flip it.
- **HNKL-30:** auditor says the attack does not exist for the currently implemented circuits, so BORDERLINE (P4, missing range check), not KEEP.
- **HIN-3 / HIN-11:** same root cause (zero `signerAddress`). HIN-3 KEEP P3 (replay guard skipped, limited by a stateless contract). HIN-11 BORDERLINE P1 (asset theft only if assets are stranded; acknowledged).
- **BORDERLINE discipline:** HNKL-11, HNKL-31 and HIN-8 are the weakest BORDERLINEs. HIN-8 is there because v1.1 explicitly lists missing curve/subgroup checks.
- **Front-running rule:** applied to HNKL-6 (encryptedOutputs) and HNKL-32 (calldataHash).
- **Not logged (no proof, verifier, nullifier, commitment-check or post-proof-effect link):** HNKL-4, 8, 13, 15-24, 26, 27, 29, 35, 36 (test suite, gas griefing, relayer store, pragma, events, etc.); HIN-6; DCAP-6. `findings_logged` equals the rows written (19, 13, 6).
- No Discussion/informational-notes sections were counted in `findings_total`; the counts are `vulnerabilitiesArray` lengths (suggestions excluded).

## Artifact check

- Held-out guard ran as its own command before any repo request: all five repos ALLOWED.
- `github.com/<repo>/commit/<sha>` via curl, one request per ~2.5 s; no API calls.
- **Hinkal 2023:** `Novelty-Today/Hinkal-Neo-Protocol` returns 404 (repo root too). The audited commit and the fix commits I tried also return 404 under `Hinkal-Protocol/Hinkal-Contracts-Circuits`. All fix SHAs 404 under the Novelty-Today repo. Acquirability PRIVATE-OR-MISSING. (A GitHub 404 can also mean a renamed repo.)
- **Hinkal 2026:** setup repo `Hinkal-Protocol/Hinkal-Protocol@61743782` is 404. `filesAndScope` pins `Hinkal-Protocol/Hinkal-Contracts-Circuits@306b0825` (200), which has the circom, Hinkal.sol, EmporiumUpgradeable.sol and VerifierFacade.sol paths (raw 200). The generated Groth16 verifier contracts are not in its scope list. Every fix SHA is 404 in both repos. One fix SHA in the report is truncated: `061ba2d4adb05b4057add88f430308b1` (32 chars). Acquirability PARTIAL.
- **zkDCAP:** `datachainlab/zkdcap@a0f3800` and fix commits `80cc77a9...` and `309d1e48d8` (truncated in the report) all 200. Guest at `zkvm/risc0/guest/src/bin/main.rs` (200; the scope-listed path `crates/zkvm/...` is 404). `lcp-solidity@293fac8` contracts `DCAPValidator.sol` and `LCPClientZKDCAPBase.sol` 200. Acquirability PINNED.
- No code was read beyond file names.

## Spot check

- All 38 `quote` values were machine-checked as verbatim substrings of the report text (whitespace-normalised) and are at most 40 words.
- Titles, severities and statuses come from the JSON, not retyped.
- Not manually spot-checked against the rendered page (client-rendered; not opened in a browser).

## Time

Roughly 55 minutes wall clock, most of it working out the bundle layout and the finding ID scheme.
