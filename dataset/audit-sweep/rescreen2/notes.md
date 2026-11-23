# rescreen2 notes
## Skipped per orchestrator (hc, 2026-11-23)
- consensys-linea-rollup-update-2026-02, consensys-linea-rollup-update-2024-12, consensys-linea-rollup-update-2024-07: covered-by:browser (browser lane did screen 2 for Consensys; curl was 403 Cloudflare, not bypassed).

## screen1-recheck (15 rows): 14 confirmed OUT, 1 corrected to IN
Test applied: s3, "an EVM contract verifies a ZK proof and acts on it", read against each report's scope section and body (ligature-normalised).
- zellic-ibc-solidity-contracts-2026-03: confirmed OUT (NO-ZK-COMPONENT). Audited light client is attestor-signature based (`_verifySignaturesThreshold`, AttestationProof = signatures). The only SP1 mention is a Discussion note ("SP1 light client cannot always prove that it expired on chain"); the SP1 client is not in scope.
- tob-alignedlayer-aligned-2024-12: confirmed OUT. Proofs (gnark, halo2, SP1, RISC0) are verified by off-chain operators in Go/Rust FFI; the EVM only checks BLS quorum signatures over the batch. No EVM ZK verifier. Flag for the orchestrator: other Aligned reports (consensys-aligned-layer-2024-08, cantina-aligned-layer-2024-12) are marked IN; if Aligned's batch-inclusion result counts as the consumer, this one should be IN too. I did not change it.
- openzeppelin-broadcaster-provers-2026-03: confirmed OUT. Hits were only site-nav strings (Zero Knowledge menu, Starknet); the audited contracts are broadcaster/state-prover pointers with no proof verification in the text.
- openzeppelin-miden-usdcx-2026-10: confirmed OUT (NON-EVM). Miden VM/node/attester code; nullifiers are Miden-native.
- openzeppelin-privacy-contracts-2026-06: confirmed OUT (NON-EVM). Cairo contracts on Starknet; proofs are verified by Starknet consensus.
- openzeppelin-zksync-crypto-precompile-2025-04: confirmed OUT. Rust BN254 pairing/precompile crates and their prover circuits; no on-chain verifier contract is audited. The zk-proof remark concerns circuit correctness (circuit-internal).
- pse-sonobe-2026-06: confirmed OUT (NON-EVM). Rust IVC/folding library; the in-scope bugs are in transcripts, sponges and the Rust verifier; EVM decider contracts are not in the audited scope.
- cantina-citrea-citrea-2025-07, cantina-citrea-49b9e08d, sigmaprime-chainway-chainway-citrea: confirmed OUT (NON-EVM). Citrea proofs are verified in the Rust node/SDK on Bitcoin; the Solidity in scope is BitcoinLightClient (header relay, no ZK). The Citrea contest page itself says `crates/sp1` is out of scope.
- cantina-x-espresso-monorepo-1003-2025-03: confirmed OUT. Only Plonky3 hash/MDS parameter finding; no EVM proof consumer.
- nethermind-nm-0901-arcx-karnot-final-2026-06: confirmed OUT (NON-EVM). Cairo contracts on Starknet.
- leastauthority-aligned-layer-layer-operator-avs-smart-contracts-2-2025-09: confirmed OUT. EigenLayer operator-AVS registration contracts; no proof verification in scope.
- c4-taiko-2024-03: confirmed OUT. Verifiers in scope are SgxVerifier and GuardianVerifier; `TIER_SGX_ZKVM` is only a tier constant. No ZK proof verified on EVM in this contest.
- cantina-azteclabs-aztec-hatch-2026-01: CORRECTED to IN (report_corrections.csv). Rollup.sol/RollupCore.sol/EpochProofLib.sol are in scope and verifyEpochProof is the L1 epoch-proof verification. Findings are governance/escape-hatch; 3.1.1 logged BORDERLINE P2, 3.5.8 DROP. Repo AztecProtocol/aztec-packages is FORBIDDEN under the held-out guard (own command, run before any request); no repo request made.

## Orchestrator decision (hc, v1.3 s3 "Attested verification")
- tob-alignedlayer-aligned-2024-12: CHANGED from confirmed OUT to IN (report_corrections.csv, reason v1.3, proof_system `attested:gnark/halo2/sp1/risc0`). Full screen 2 done: 14 findings in the report (+ appendix items). Logged 6 rows (1, 2, 3, 5, 9, 11), all DROP: operator/batcher liveness (1, 3, 5), off-chain Merkle SDK (2), ECDSA (9), payment-path front-running with no ZK proof accepted (11). Findings 4, 6, 7, 8, 10, 12, 13, 14 have no proof/verifier/commitment/effect-after-proof content (Dockerfile, keystore, dependencies, passwords, events, lock/unlock, storage gaps, block count) so are not logged. The earlier "confirmed OUT" line above for this report is superseded.
- leastauthority-aligned-layer-layer-operator-avs-smart-contracts-2-2025-09: stays OUT: EigenLayer operator registration contracts only; no attestation is consumed.

## Totals
- `findings.csv`: 65 new rows over 28 reports: 2 KEEP, 26 BORDERLINE, 37 DROP. Non-DROP pattern guesses (KEEP rows included): P1 13, P5 5, P3 4, P4 3, P2 2, OTHER 1.
- `report_corrections.csv`: 14 rows over 7 reports: aztec-hatch OUT->IN (s3, EVM rollup epoch-proof verifier in scope), tob-alignedlayer OUT->IN (v1.3 attested verification, orchestrator), and 5 ABDK TermMax/TMX reports IN->OUT (NO-ZK-COMPONENT: no occurrence of zk/snark/groth/plonk/verifier/nullifier/proof/circom/circuit in the full text).
- `disagreements.csv`: 4 rows, all `consensys-linea-plonk-verifier-2023-06` (4.2, 4.3, 4.8, 4.9; browser agent DROP -> proposed BORDERLINE under v1.1 verifier-soundness). Not rewritten.
- Candidates for the paper's reserved set: KEEP `abdk-tornado-tornadocash-anonymity-mining-first-3.1` (Reward.circom, reward drain) and `abdk-semaphore-and-mixer-...-P2-Mixer-nullifier` (second nullifier withdraws a deposit twice). Both PARTIAL: public repo exists, audited commit not named (private repos at audit time).

## KEEP / BORDERLINE rationale
- Both KEEPs meet all three s2 criteria in the auditor's own words (accepted proof, payout, unbound value).
- 13 P1 BORDERLINEs: 12 are rollup-circuit signed-message/chunk gaps in zkSync-Lite forks (EdgeSwap CVF-44/47/48/56/60/65, ZKSwap v3 CVF-16/17/18/24, zkLink v6 CVF-2/11) and 1 is Mystiko CVF-70 (join-split overflow). Auditor states the unbound value and often the loss (stolen assets, unbacked mint); proof acceptance on the EVM side is implied (circuit-side audit). They are clustered duplicates of two or three root causes; the orchestrator may prefer to collapse them to one row per root cause. Under v1.2 they could be argued DROP (NOT-BINDING-CIRCUIT-ONLY); I kept them because the unbound value is who/how-much of an effect.
- Rows I deliberately DROPPED despite scary severity: StarkEx perpetual CVF-1/2 and v3.x Cairo items, Nil Foundation circuit gadgets, zkLink CVF-1/3/5/12, Term Structure verifier CVF-38/7/8 (curve checks; precompile rejects, effect not described), Mystiko CVF-37/89, Zeropool CVF-30 (Poseidon matrix).

## Coverage and limits (honest)
- ABDK reports were read through a filtered index (Critical/Major severity plus proof/verifier/nullifier/commitment/public-input keywords), not every Minor/INFO CVF one by one. Several ABDK PDFs are letter-spaced (pdftotext output with a space between every character); for those I read a space-stripped text and verified quotes after stripping whitespace, so quotes from those 12 reports are verbatim modulo whitespace. Residual misses are possible, mostly in Minor/Moderate items.
- Old-format ABDK reports (Tornado, Semaphore, zkSync June 2020) have bullet lists, not CVF ids; I used ids like `3.1`, `5.2-k`, `P2-Mixer-nullifier`.
- Cyfrin x6 (linea 2024-05, 2025-01, mixed-upgrade 2026-03, aztec logic-module, aztec polynomial, linea forced-txns): the PDFs are deliberately abbreviated attestation summaries ("the technical detail of individual findings is not reproduced here"), so no findings are readable. Counts only: linea-2024-05 2H/2M/4L; linea-2025-01 1M/1L; mixed-upgrade 1 Critical/1 Low (scope includes PlonkVerifierForDataAggregation, worth fetching the full report); logic-module 4 Low; polynomial 15 Low; forced-txns 1 Low. Nothing logged.
- Consensys (6 with local excerpts) and Cantina competitions (5): excerpt files hold only already-logged findings (Consensys) or only the competition blurb (Cantina). Findings are not readable offline; Consensys is covered-by:browser, the Cantina competition results are login-gated. Nothing logged. The 3 `consensys-linea-rollup-update-*` reports: skipped per orchestrator (covered-by:browser).
- Halborn x4: Matterlabs verifier report states "did not identify any security risks" (0 findings); Portal Gate (12 findings, no proof/verifier content; only a copied tornado-core Verifier.sol in scope) and Sacred Finance (8 findings: Aave interest, init frontrun, zero checks, no proof content) have nothing to log; Era circuits already had HAL-01/02/04 logged (HAL-03/05 informational). Rarimo Halborn web page text lacks the informational finding's detail.
- Ackee zkEmail recovery: remaining 24 findings (guardian config, selector collisions, templateIdx check placement, gas, events) have no proof/verifier effect; not logged. Zokyo Railgun Apr 2022 / Nov 2021: no ZK-related findings (fee validation, comments), not logged.
- Screen-1 doubts for the orchestrator: halborn-portal-gate (no ZK content beyond a copied Verifier.sol in scope) and halborn-sacred-finance (a Tornado fork; scope includes circuits but no findings concern them) are IN today and might be OUT/NO-ZK on a strict reading; I did not change them.

## Artifact check
- Held-out guard run as its own command before each repo name that I might request: `AztecProtocol/aztec-packages` FORBIDDEN (rows from report text only, no request); `tornadocash/tornado-core` FORBIDDEN (BORDERLINE 5.2-k and DROP 4.3 from report text only; `peppersec/tornado-mixer` ALLOWED by name but redirects to the forbidden family so I did not request it); `tornadocash/tornado-anonymity-mining` ALLOWED; `appliedzkp/semaphore`, `kobigurk/semaphore`, `semaphore-protocol/semaphore` ALLOWED.
- Web requests (status codes only, no API calls): `github.com/tornadocash/tornado-anonymity-mining` 200, raw `circuits/Reward.circom` on master 200; `github.com/{kobigurk,appliedzkp,semaphore-protocol}/semaphore` 200 (all redirect to semaphore-protocol/semaphore). Three curl requests to diligence.security returned the Cloudflare 403 page.
- All other non-DROP rows are `NO-COMMIT`: ABDK reports name no repo or only short hashes without a repo (ZKSwap v3: `72ffa2d..1cc5b18`). No guard or request was made for those, so `holdout_flag` is blank for them.
- ToB Aligned: DROP rows only, no repo request.

## Not done
- No project-status.md update and no commits (confined to this folder; AGENTS.md checkpoint is the orchestrator's).
- Time: about two sessions across 2026-11-22/23.
