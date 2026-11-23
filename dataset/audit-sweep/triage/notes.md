# BORDERLINE triage notes (TRIAGE.md v1, PROTOCOL v1.3)

**Run date:** 2026-11-23. **Triager:** AI (Claude Code, Opus 5.5). This is a pre-screen, not a label. It orders the candidates and removes none of them.

## Decision rules

Rules 1–7 were written down before any row was judged. Rules 8–10 were added after the first pass (see "Revision before the final draw"). Every row in the final CSV applies all ten rules.

1. **Verifier or recursion soundness (P4).** Under PROTOCOL §5 (v1.1), the consumer's effect follows from accepting the proof.
   - A verifier that accepts invalid proofs does not get C2 = `fails` merely because the auditor names no effect.
   - C2 is `met` when the report's scope shows an EVM consumer acting on that verifier; otherwise C2 is `unclear`.
   - C3 is `met` when a forged or wrong statement lets the attacker choose who, what, which state or how much.
   - These rows get `proof_system_soundness=yes`, which does not change the outcome.
2. **Circuit-internal under-constraints (zkVM, rollup, recursion).** The test is whether the bug reaches the interface.
   - If it lets a prover get a wrong state root, output, public value or program identity accepted on L1, it reaches the interface and is not LN.
   - If the report shows no route to public outputs (e.g. a gadget defect that only breaks completeness, or a value that is constrained elsewhere), C3 or C1 = `fails` and the row is LN (DROP class `NOT-BINDING-CIRCUIT-ONLY`).
3. **LN requires a `fails`.** `unclear` is not `fails`, and two `unclear` values give UNSURE. LN is never used just to save human effort.
4. **PROTOCOL v1.2 DROP classes give a `fails`:** liveness or DoS only (the user's own input blocks their own action, or the system halts); gas, memory or events; circuit-internal with no interface effect; off-chain only.
   - Exception: one party's valid proof consuming or blocking *another* party's state is binding.
5. **Front-running rule (§2).** Resubmitting an observed valid proof so that the effect goes to the attacker, or changes in their favour, meets C3 (P1/P2).
6. **Completeness bugs fail C1.** If a valid proof is rejected, or honest users cannot prove, no proof is wrongly accepted. Such a row is LN unless the report also shows wrong acceptance.
7. **`source_checked`.** `yes` means the finding's description and impact were located and read in the report text. `quote-only` covers the Consensys browser excerpts (the site blocks curl, and only the verbatim excerpt is stored) and any finding that could not be located.
8. **Skipped or bypassed verification** (added after rows 0–200 were first judged; applied to all rows).
   - When the attacker can make a consumer treat an unverified operation as verified (a selector bypass, a dummy verifier registered permissionlessly), C1 is `met`.
   - When verification is skipped by design or depends on a deployment setting or off-chain party (zero joinsplits, `worldId` unset, native mode), C1 is `unclear`.
9. **Privileged roles** (added in the same revision; applied to all rows).
   - Basis: research contract §5. Adversaries may use only "roles allowed by the evaluated deployment model"; "consensus, sequencer ... compromise" is out of scope.
   - A finding that needs an owner, multisig, governance, sequencer, builder, operator or allowlisted caller to misbehave or misconfigure gets `unclear` on the affected criterion, never `fails` or `met`. It is therefore UNSURE unless another criterion clearly fails for other reasons (e.g. no ZK proof, or verification fails as completeness).
   - Humans decide whether that role is adversarial in the deployment model.
10. **A `fails` must rest on the report text.** It must come from an explicit auditor or client statement (e.g. "not exploitable", "could not find a way", "only usability", "not used") or on a standard cryptographic assumption from contract §5.2 (hash preimage resistance). My own exploit reasoning alone does not justify `fails`.

## Revision before the final draw

After a first pass over all 201 rows, a review found that trusted-role findings were judged three different ways (LN, LB and U), and that one `fails` rested on inference rather than the report. Rules 8–10 were added and applied to all rows, not only sampled ones, which changed 11 rows:

- **LN → U (8 rows):** Nocturne 3.4, Lighter 2025-11-01, PrivacyBoost VK registry key, Railgun CVF-23, SAMM revoked DKIM, OIDC senderHash endianness, SP1CC VUL-004, Privado 8.7.
- **LB → U (3 rows):** Aztec hatch 3.1.1, Malda lending VUL-001, Malda coprocessor VUL-003.

The validation sample was drawn only after this revision. A provisional draw made before it was discarded, and its keys were never used.

## Counts

The scope is 201 rows: `group_best_decision = BORDERLINE`, excluding flags starting `scope-question` (1) and `agents-disagree` (2). All 201 rows are canonical and each is its own group.

| Outcome | Rows | Share |
|---|---:|---:|
| LIKELY-BINDING | 86 | 43% |
| UNSURE | 66 | 33% |
| LIKELY-NOT | 49 | 24% |

- **Human workload:** 86 + 66 + 13 sampled LN = 165 rows to label, against 201 without triage. If the miss rate exceeds 10%, all 49 LN rows are labelled.
- **LB on an unclear criterion:** 31 of the 86 LB rows rest on two `met` plus one `unclear`. The `unclear` is:
  - C2 in 28 rows: an on-chain consumer implied but outside the audit, e.g. rollup or recursion circuits, iden3, zk-email, Intmax2, EdgeSwap/zkSwap.
  - C1 in 2 rows: Blobstream X 3.8 and Consensys Linea 4.5.
  - C3 in 1 row: Zkopru C.

  The other 55 LB rows have all three criteria `met`.
- **Which criterion failed in LN rows:** C3 34 times, C1 25 times, C2 7 times. A row can fail more than one criterion.
- **Proposed pattern:**

  | Outcome | P1 | P2 | P3 | P4 | P5 | OTHER |
  |---|---:|---:|---:|---:|---:|---:|
  | LB | 20 | 16 | 9 | 32 | 4 | 5 |
  | U | 11 | 12 | 10 | 22 | 9 | 2 |
  | LN | 4 | 6 | 6 | 20 | 10 | 3 |

- **`proof_system_soundness = yes`:** 37 rows (LB 9, U 20, LN 8). These are mostly verifier or recursion soundness items (Linea PlonkVerifier, Nebra UPA, SP1/Plonky3, OpenVM, Hypercube, Nori recursion). The field does not change any outcome.
  - Research contract §5.4 puts "breaking the cryptographic verifier or proof-system soundness" initially out of scope, which bears on the author's pending scope decision for these rows.
- **`source_checked`:** `yes` for 196 rows and `quote-only` for 5. The 5 are Consensys Diligence excerpts; the full page is Cloudflare-blocked for curl, and only the browser excerpt is stored locally.
- **Yield by agent:**

  | Agent | LB | U | LN |
  |---|---:|---:|---:|
  | rescreen | 27 | 28 | 33 |
  | firms-1 | 18 | 11 | 10 |
  | firms-2 | 12 | 12 | 1 |
  | rescreen2 | 16 | 9 | 1 |
  | curated | 11 | 3 | 3 |
  | browser | 2 | 3 | 0 |
  | contests | 0 | 0 | 1 |

  `rescreen` supplied most of the LN rows, consistent with the v1.2 BORDERLINE-discipline note.

## Recurring reasons

### LIKELY-NOT

- **Self-harm or user error only** (C3 fails, as stated by the auditor). Examples: Singularity 3.10/3.11, Nocturne 3.5, PrivacyBoost NPK mismatch, Arianee `updateCommitment`.
- **Completeness or liveness only.** Valid proofs are rejected, or the system halts, and nothing is wrongly accepted.
  - Examples: Malda wrong state root, Malda balance-query padding, SP1Helios constructor key, DendrETH verifier digest, PrivacyBoost subgroup-order off-by-one, Semaphore `nLevels`.
- **Off-chain or host-only verifier** (C2 fails).
  - Examples: SP1 Rust host `vk_root` (C4 M-01), OpenVM SDK public-values length, snarkjs JavaScript `verify.js` (CVE-2023-33252), Scroll native decider, Brevis Go SDK callback.
- **Auditor explicitly found no exploit.** The report says not exploitable, no soundness issue, or not reached.
  - Examples: Linea missing selector commitment (hardcoded), Scroll `tx_data_length`, Kailua VUL-017 and VUL-004, OpenVM #21, PrivacyBoost unused roots and PI-length check, Arianee ARIA-015.
- **No ZK proof in the path.**
  - Examples: Boundless ECDSA domain separation, zkSync Merkle library, IBC Eureka CosmWasm BLS light client (`cw-ics08-wasm-eth`, confirmed in the report's scope section), Jovay (TEE-only today), Privado `groupID` setup.
- **Infeasible under §5.2 hash assumptions.** Preimage of a zero leaf or zero root, or keccak outputting 0 or 1 (Arianee zero leaf, Webb `SetMembership`, AZTEC ToB-8).

### UNSURE

- **Exploit depends on a privileged role** (Rule 9).
  - Examples: Railgun `setVKey`, PrivacyBoost VK registry, SAMM DKIM registry, Aztec escape hatch, Malda sequencer-bug paths, World Chain PBH builder, World NFC ID `allowedCaller`, Linea decentralised-sequencer front-run, Linea data chain.
- **Missing curve or field checks in a Solidity verifier with no exploit stated.** Several such findings say "may" lead to false positives, but EVM pairing precompiles usually reject off-curve points.
  - Examples: Railgun CVF-61, Mystiko CVF-15, Consensys Linea 4.10, Term Structure CVF-16, Hexens SCRI-1 aliasing.
- **Proof malleability with the statement unchanged.** These matter only to consumers that key replay or dedup on proof bytes. The same rule was applied to every case.
  - Examples: gnark GHSA-7p92, OpenVM #06 and #07.
- **Theoretical Fiat–Shamir or commitment-model gaps with no concrete forgery.** Examples: Linea so-far-digest, Hypercube 3.12 and 3.13.
- **Non-EVM consumer.** Nori 3.1, 3.2 and 3.6 bind values consumed by the Mina-side bridge; this is a scope question for the author.
- **Conflicting-transition handling** that is reachable only if a second prover or TEE accepts a wrong transition (Taiko Shasta, Surge 6.4).
- **Auditor hedges or the client disputes.** Silent `validUntil`, zkLink CVF-2, Lighter `master_account_index`, OIDC endianness, Privado disabled requests.

### LIKELY-BINDING

- **In-circuit under-constraint of a public output or verified value** reaching an EVM consumer. This is the largest group, mostly P4.
  - Examples: Blobstream X, Lighter wrapper, Intmax2, Scroll aggregation, Singularity and Mystiko wraparound, EdgeSwap and zkSwap signature coverage.
- **Missing context or config binding** (P2): chain id, fork config, rollup or L1 config hash, KYC or zone policy.
- **Front-running or replay of an observed proof** (P1/P3): Axiom caller payment, Telepathy step replay, Singularity fee replay, PBH nullifier timing, World ID cross-app `actionId`, zkSync `proveBlocks` replay.
- **Forgeable verifier.** Pairing result unchecked or always true, randomness omitting proof elements, Plonky3 FRI, attacker-registered verifier class.

## Things that looked odd

- **Count mismatch.** TRIAGE.md says 204 unique BORDERLINE candidates. 204 is the BORDERLINE total before the flag exclusions; 3 are excluded by flag, leaving 201.
- **Probable duplicates that survived dedup**, each judged the same way:
  - `tob-polygonlabs-iden3circuits-2024-05-IDEN3-1` (G0058) and `trailofbits-iden3-circuits-2024-05-1` (G0268): same ToB PDF (142.pdf), same finding.
  - `0xparc-circomlib-mimc-tornado-UNKNOWN-1` (G0225) and `…-zkbugs-32` (G0337): the curated agent already marked the latter DUPLICATE.
  - `0xparc-zkemail-UNKNOWN-1` (G0234) and `matterlabs-zkemail-2024-10-2` (G0265): the same `\xff` regex bypass. `matterlabs-zkemail-2024-10-1` (G0264) is a related From-header issue.
  - `veridise-panther-2025-04-*` and `veridise-panther-panther-protocol-2025-04-*` share 89.pdf. PAN-017 and zkbugs-54/55 are different findings, so this is not a duplicate in this set.
  - Veridise 156.pdf is used under two report keys (`veridise-tangle-webb-2023-09` and `veridise-webb-evm-bridge-2023-09`). The findings differ (VUL-006 and VUL-005).
  - The Intmax2 rows 6.1, 6.5, 6.6, 6.8 and 6.2 are distinct findings with similar shape.
- **Source-location problems in the dumps.** The table-of-contents or fix-log hit was sometimes taken instead of the body (e.g. Scroll wave1 #16, EZKL #16, RSCZD-1, Panther zkbugs-55, EdgeSwap CVF-60, zkSwap CVF-18, Mystiko CVF-70). Three ABDK findings sit in letter-spaced text that the normalized search missed (Term Structure CVF-16, zkLink CVF-2 and CVF-11). In every case the body was found by targeted search and read, so `source_checked = yes`.
- **Field-text mismatches:**
  - `tob-zkonduit-ezkl-2025-03-EZKL-14` and `-EZKL-34` have the title "Fix Status: Resolved" in `candidates.csv`, a parsing artefact. The real titles are the DataAttestationSingle KZG check and the unvalidated selector.
  - `cantina-openvm-smart-contract-audit-for-axiom-protocol-2023-10` is an Axiom V2 query audit, not OpenVM.
- **AZTEC v1** (ToB AZT-010, AZT-008) uses non-SNARK range and commitment proofs. C1 is `unclear` or `fails` on scope grounds, which bears on the "SNARK or STARK" wording of PROTOCOL §2.
- **Nori Bridge.** The Zellic findings affect the Mina-side consumer. The v1.3 attested-verification IN decision covers the EVM path, but these particular findings bind values consumed on Mina. The author should decide.
- **Aztec hatch 3.1.1** carries `holdout_flag = FORBIDDEN`. Triage used report text only.
- **Tornado ABDK 5.2.** Under the v1.2 exception, one party's proof consuming another party's nullifier is binding, but the auditor frames it as a user mistake (k reused, guessed or stolen). Rated UNSURE with C1 `unclear`.

## Limitations

- **AI pre-screen.** These are one AI pass's judgments, not independent annotation. Criterion values depend on the auditor's stated impact; where the auditor hedged, the row usually went to UNSURE.
- **Report text only.** No project code was read.
- **Reason field.** Reasons are 25 words or fewer (validated by script).
- **Order effect.** Rows were judged in `candidates.csv` order in batches of about 10. Rules 1–7 were fixed before the first row; rules 8–10 were added after the first pass and applied to all rows. Later rows may still reflect slightly more experience with recurring classes.
- **Status file.** `docs/project-status.md` was not updated. Edits were limited to `triage/`, so that checkpoint is pending for the orchestrator.
