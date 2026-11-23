# R-ledger: provenance ledger of binding cases (in repo and to acquire)

**Status:** DONE (research only; no code built or run). Repository access was limited to GitHub metadata/tree API calls, plus reading two Anon Aadhaar contract files at the audited commit (`AnonAadhaar.sol` and `example/AnonAadhaarVote.sol`) after the held-out guard returned ALLOWED.
**Date:** 2026-11-22. **Branch read:** `snapshot/research-roadmap-2026-11-19`, plus the remote sprint branches named below via `git show`.
**AI disclosure:** produced by Claude Code (Claude Opus 5.5, `claude-opus-5-5`). Every label below is `label_source = AI` and needs author review. AI output is not independent annotation.

## How to read this ledger

**Provenance labels.**

| Label | Meaning |
|---|---|
| OUR-OWN-FINDING | Found by BindCheck work. No prior public report was found in a bounded search. That search does not prove novelty. |
| PUBLIC-DISCLOSURE-REPRODUCTION | Someone else disclosed it first, through an advisory, a public PR or issue, or an incident write-up. |
| AUDIT-REPORT | Comes from a published professional audit or contest report. |

**Reproduction grades.** The grades follow the repository's E-scale, as used in `paper/zk/sections/cases.tex`.

| Grade | Meaning |
|---|---|
| E4 reproduced | A real proof, the unchanged verifier and consumer, and a committed local effect. |
| partial | Some local execution, but not E4 on the real target. |
| source-only | Inspected at a pinned commit; nothing executed. |
| none | Not inspected. |

**Ground truth.** An audit report is ground truth for positives only. Nothing in this ledger implies that an unaudited or unflagged code path is safe.

**Pattern labels** follow `docs/PROJECT-CLOSEOUT-2026-11-11.md` §2.1:

- P1: unbound effect.
- P2: context binding.
- P3: replay key or field alias.
- P4: verifier invariants.
- P5: public-input count or order.

**Evidence paths.** Paths prefixed `origin/sprint/<X>:` exist only on that remote branch. Read them with `git show origin/sprint/<X>:<path>`. They are not on this checkout.

---

## Part A: Cases already in this repo

### A.1 Confirmed or reproduced cases

| # | Case | Provenance | Source | Repo + pinned vulnerable commit | Fix / repair commit | Pattern(s) | Reproduction status | Evidence in repo |
|---|---|---|---|---|---|---|---|---|
| A1 | **Z1: ZKredential gateway mint recipient** | OUR-OWN-FINDING | Internal, from the DEV set (DEV-F30), not from the held-out run. No prior report found (bounded search, 2026-11-09). | `ethpanda-org/ETHShanghai-2025@23917814522bac494150c7e99a123aa15a448155`, `projects/ZKredential` | No upstream fix. Local design contrast only: `findings/zkredential/repair.py`. Disclosure draft is **unsent**. | P1 (recipient not bound to the proof's `walletAddress`) | **E4 reproduced.** The repair rejects the attack, and the legitimate run passes. | `findings/zkredential/` (`expected-outcomes.md`, `prior-and-deployment.md`, `policy.md`, `run.sh`, `*.test.js`), `findings/POLICY-ANSWERS-2026-11-10.md`, `paper/zk/sections/cases.tex` |
| A1a | Z2: ZKredential mint amount | OUR-OWN (conditional) | Same as A1 | Same as A1 | n/a | P1 | **Not claimed.** The policy is UNKNOWN (author answer, 2026-11-10). | `findings/POLICY-ANSWERS-2026-11-10.md` |
| A2 | **R1: RacePass EventPass `credHash`** | OUR-OWN-FINDING | Internal, from DEV, not held-out. No prior report found. PR #1 "Credientals fix" does not touch `EventPass.sol`. | `Servesh21/RacePass@abd54b5c541ac9d26f938a6bdbd78545526249e5` | No upstream fix. Local contrast only: `findings/racepass/repair.py`. Disclosure draft is **unsent**. | P1 in the paper table. The consumer acts on a caller-chosen `credHash` that is not tied to the KYC proof's `credentialHash`. It can also be read as P2/P3. Labelling it P1 is an author decision to confirm. | **E4 reproduced** for the credential binding. A revocation bypass is permitted by the code but **not demonstrated**: the circuit's revocation check is inert. | `findings/racepass/`, `findings/POLICY-ANSWERS-2026-11-10.md` |
| A2a | R2 / R3: RacePass recipient, and one pass per credential | OUR-OWN (conditional) | Same as A2 | Same as A2 | n/a | P1 / P3 | **Not claimed.** R2 is unresolved and R3 is UNKNOWN. Do not assert a replay or duplicate-claim reading. | `findings/POLICY-ANSWERS-2026-11-10.md` |
| A3 | **Payy `agg_agg` message tail** | PUBLIC-DISCLOSURE-REPRODUCTION | Advisory [GHSA-fhxc-63vg-9gwr](https://github.com/polybase/payy/security/advisories/GHSA-fhxc-63vg-9gwr). Not a BindCheck discovery. | `polybase/payy@c4d2c9021b8fb9988816eb6987a734b830bfce15`. This is the revision whose `agg_agg` lacks `assert_message_tail_zero`. T08/T20 caution against calling it "the vulnerable version", because the advisory's version labels do not map to the Noir sources. | `dcd5d96ee15664a59bc24ed0dc2bb78b73ac5e36` adds `assert_message_tail_zero`. | No clean P-label: the gate manifest says "NONE (closest P1)". It is a producer-side flaw: the circuit leaves the outer tail unconstrained while the consumer parses the full 1000-word array (prefix versus extent). The consumer itself is faithful (T08 §4). | **E4 reproduced** on macOS arm64 (T15–T19). Rollup balance went 100→93 with a burn of 7. The repaired circuit rejects the witness, and a mint control passes. Not re-run on Linux: T0 is PARTIAL because `bb` 3.0.0 is blocked. | `docs/payy-case-study.md`, `reports/T08.md`, `T15.md`, `T16.md`, `T18.md`, `T19.md`, `T20.md`. Raw logs are under `results/raw/T1x/` (ignored). |
| A4 | **zkDrops nullifier field alias** | PUBLIC-DISCLOSURE-REPRODUCTION | Public fix [a16z/zkdrops PR #2](https://github.com/a16z/zkdrops/pull/2). Also in the R1 census as R1-011. | `a16z/zkdrops@4002962fb632578dd12477346d2e5c4159ffb2ef` | `f6f58020911cd2a19e1639f0dc93ec9fca2a9e17` | P3 (raw-integer spent key versus field-reduced verifier) | **E4 reproduced (historical).** One proof redeemed twice, leaving a redeemer balance of 20000. The verifier is snarkJS **PLONK**, which is outside the Groth16 subset. | `reports/impact/REPORT.md` §Historical calibration, `feasibility/v2/REPORT.md`, `benchmark/cases/DEV-H01`, `DEV-H02`, `reports/groundtruth/CLAIMS.md` B10, `gate/GATE-MANIFEST.csv` row 22 |
| A5 | **Aztec Connect `numRealTxs` extent** (about $2.1M, 2026-06-14) | PUBLIC-DISCLOSURE-REPRODUCTION (incident) | Aztec Labs incident report, plus BlockSec, Rekt and Halborn write-ups (hashed in AZ1) | `AztecProtocol/aztec-connect@69de49b1be49ae3757ccb53f07d9cb04a1987184`, the head of PR #67 (unmerged). The deployed V3 source matches it byte-for-byte per Sourcify. | None. The system is deprecated, and no fix commit is known. | **Disagreement, left open.** The R1 census labels it P5. AZ1 frames it as extent binding, which is outside P1–P5 as implemented. | **partial.** The real target is source-confirmed only; BindCheck returned UNKNOWN because no consumer was recovered. A synthetic Circom/Anvil faulty-versus-fixed testbed reproduces the shape (53/53 steps). That is **not** E4 on Aztec code. | `origin/sprint/AZ1:reports/AZ1/REPORT.md`, `origin/sprint/AZ1:prototypes/az1/`, `origin/sprint/R1:reports/R1/incidents.csv` (R1-005) |
| A6 | **zk_voting** (DEV-F34) | OUR-OWN candidate (**undecided**). The closeout claims only Z1 and R1, and `paper/zk/STATUS.md` §(b) says DEV-F34 still needs a decision. | Internal, DEV | `avitenzer/zk_voting@18d3a277ccd82736757a34ad56690a241ae77744` | None known | P3 / P4 / P5 (P5 and verifier-kind entries are AI opinion: `paper/zk/STATUS.md`) | **source-only (E1)**. Not executed. The disclosure plan is `\MISSING`. | `reports/soundness/REPORT-2.md` §case adjudication, `paper/zk/data/zkvoting-facts.json` |
| A7 | **γ = δ weak verifying keys** (a class, not one case) | PUBLIC-DISCLOSURE (class previously reported) | Zeto issue #186 (credit it). Exploited in the wild: Veil Cash (R1-001) and FoomCash (R1-002). | 56 artifacts in 18 of 142 families with parsed keys. Per-family commits are in the held-out ledgers. **Deployed addresses are private** (`dataset/onchain-census.csv`) and are not reproduced here. | n/a (setup ceremony) | P4 | **source/key-level only.** No consumer link and no funds for any of the 43 signature matches. | `reports/heldout/`, `paper/zk/data/p4-g2-constant-check.json`, `docs/PROJECT-CLOSEOUT-2026-11-11.md` §2.4 |

### A.2 Public audit and disclosure pairs already acquired (recall gate / benchmark)

All of these are `AUDIT-REPORT` or `PUBLIC-DISCLOSURE` pairs taken from `gate/GATE-MANIFEST.csv`.

- **Reproduction:** none of them has an E4 run in this repo except zkDrops (A4) and Payy (A3). The benchmark built only 4 of 32 public slots (`reports/bench/REPORT.md`). Treat every pair below as **source-only**.
- **Exposure:** EXPOSED pairs are DEV-exposed and cannot count as held-out recall.

| Gate row | Case | Provenance / source | Repo | Vulnerable → fixed | Pattern (gate proposal) | Gate disposition | Exposed? |
|---|---|---|---|---|---|---|---|
| 21 | Semaphore nullifier field alias | PUBLIC-DISCLOSURE (R1-009, Semaphore issue #16 lineage) | `semaphore-protocol/semaphore` | `8d703c124c663537966d6fc35cfec84146e236b2` → `3dcf79f6a095397352f71384e3dc6889c640a50f` | P3 | KEEP | EXPOSED |
| 36 | Semaphore root-history collision | AUDIT-REPORT (Semaphore audit) | `semaphore-protocol/semaphore` | `fd3cc6f7db46aec83c0f807a8155dcd66561a0db` → `c6667d98b8c72a424afd118da6cbde03a4945690` | P2 (**disputed**: R2's `excluded-borderline.csv` rejected SEM20 W1 with "no unauthorized effect described") | KEEP; human to confirm severity | EXPOSED |
| 28 | zkEmail skipped subject prefix | AUDIT-REPORT (Zellic) | `zkemail/ether-email-auth` | `b5694a9e0e49d07a862232f665dc4d0886c5a15f` → `1455cd221dcb0849190879911688152669e4ed36` | P1 (partial) | KEEP | — |
| 29 | zkEmail wrong public-input modulus (q instead of r) | AUDIT-REPORT (Zellic) | `zkemail/ether-email-auth` | `b5694a9e…` → `e84065db4fa087b8d6152bb9682de71f6676e3ff` | P3 | KEEP | — |
| 31 | zkEmail last-timestamp zero | AUDIT-REPORT (Zellic) | `zkemail/ether-email-auth` | `b5694a9e…` → `4e2f119a428b694c1115e59dc52cfbe278c0e494` | P3 (partial) | KEEP | — |
| 38 | zkEmail guardian repeat | AUDIT-REPORT (Matter Labs) | `zkemail/email-recovery` | `041a882677622b580693d2a4f08d6661bf77ea89` → `c866ecb3dd326fe17850c61a9e38eb3db8a45695` | P3 (partial) | KEEP | — |
| 40 | zkEmail proof-coordinate range | AUDIT-REPORT (Matter Labs) | `zkemail/ether-email-auth` | `8a62db1e676aedbb20a403be95fffebef12b97e4` → `984b5919a9be715b743b08863ab6471c2b5356a6` | P4 | NEEDS-PAIR-REPAIR | — |
| 14 | MACI "data not fully verified during state update" | AUDIT-REPORT (HashCloak) | `privacy-scaling-explorations/maci` | `2db5f625b67a6b810bd851950d7a42c26189088b` → `6df6a4054da926b07f35c5befab4f1f8af33dcc6` | none (relational candidate) | DEMOTE | EXPOSED |
| 30, 32, 33 | zkEmail stale regex, nine-digit timestamp, overlapping masks | AUDIT-REPORT (Zellic) | `zkemail/ether-email-auth` | `b5694a9e…` → `9deaf804…`, `b7fc2f6f…`, `0096e59b…` | none (circuit-only) | DEMOTE / DROP | — |
| 15, 47 | Self SMT alias; Self index range checks | AUDIT-REPORT (zkSecurity) | `selfxyz/self` | `4f18c75041bb47c1862169eef82c22067642a83a` → `99e8eece…` / `49de5496…` | none (circuit-only) | DEMOTE. `selfxyz/self` is sampled EVAL rank 259 (spent). | — |
| 20 | Tangle membership initialization | AUDIT-REPORT (Veridise) | `tangle-network/protocol-solidity` | `848d073b…` → `eeb4fc7a…` (bulk "Veridise audit fixes" commit) | none (circuit-only) | DEMOTE | — |

---

## Part B: Audit-sourced candidates to acquire

### B.0 Method

**Source of the candidates.** I did not re-mine audits from scratch. The R2 audit census (`origin/sprint/R2:reports/R2/findings.csv`) had already read 68 audits and found 54 findings, all AI-labelled. I filtered it against this task's definition: a valid proof is accepted, but the consumer acts on a recipient, amount, identity or nullifier that the proof does not fix, in a Circom/Noir + Solidity application.

**Report text re-read on 2026-11-22.** I re-read the finding text and scope sections in these reports:

- Singularity (Zellic)
- Anon Aadhaar (PSE)
- Railgun (ABDK)
- Telepathy (Zellic)
- Nocturne (Zellic)
- iden3 (Trail of Bits): read only by grepping for "challenge" and the finding header
- Self 2 (zkSecurity)
- Hinkal (zkSecurity)
- Aleph Zero (zkSecurity): scope section and the "User's Account Can Be Poisoned" finding
- Renegade and Lighter (zkSecurity; scope sections only)

Downloads went to the session scratchpad and are not committed. I confirmed that each audited or fix commit exists with an unauthenticated `api.github.com/repos/<o>/<r>/commits/<sha>` call; the HTTP code is recorded in the table.

**Held-out guard.** I ran `scripts/check_holdout.py`, taken from `origin/sprint/R2` with ROOT pointed at this checkout, in two batches. Together they cover every repository named in Part B: anon-aadhaar, selfxyz/self, Railgun-Privacy/contract and circuits-v2, Hinkal-Protocol/Hinkal-Protocol, hinkal-team/hinkal-contracts, iden3/circuits and contracts, nocturne-xyz/protocol, succinctlabs/telepathy-contracts and eth-proof-of-consensus, the three portalgateme Singularity repos, Cardinal-Cryptography/zkOS-monorepo and zkOS-circuits, renegade-fi/renegade, elliottech/lighter-prover, and avitenzer/zk_voting. All of them are **ALLOWED**. `tornadocash/tornado-core` is **FORBIDDEN**, so I did not use any Tornado audit.

**Filtered out (outside this task's scope, though still in R2):**

- Recursive, aggregation and zkVM verifiers: Nebra, SP1, Scroll Euclid, Nori, Brevis.
- Cairo (Tongo) and DarkFi.
- CRS/setup findings: AZTEC v1 TOB-7, the SP1 dev SRS.
- Reentrancy before the nullifier write: Singularity 3.2/3.7, Railgun Zokyo-2. R2 labels these P3, but they are **not** "the consumer acts on a value the proof does not fix" under this task's definition. They are ordering bugs.

**Novelty.** Every row below is a **reproduction target**: auditors have already reported it. No novel candidate was identified. I did not read protocol code deeply enough to claim one.

### B.1 Candidates

**Commit check legend.** Codes are HTTP status codes from the commit check.

| Code | Meaning |
|---|---|
| ✔200 | The commit was found in the public repo. |
| ✘422 | The SHA is not in the repo. |
| ✘404 | The repository is not public. |

| # | Project | Audit (firm, report, date, finding ID) | Public repo, vulnerable commit, fix commit | Pattern | Why it is a binding flaw | Artifact availability | Priority |
|---|---|---|---|---|---|---|---|
| B1 | **Anon Aadhaar** | EF PSE (Garg, Li, Charbonnet), *AnonAadhaar audit*. The report header says "March 2024", but the audited commit is dated 2024-04-22; this discrepancy is unresolved. **Critical C1** "Incorrect order of inputs from smart contract to circuit" | [anon-aadhaar/anon-aadhaar](https://github.com/anon-aadhaar/anon-aadhaar). Audited `c4ef0180cddda39a92779d432265f7f75190977b` (✔200, 2024-04-22). Fix `bbdfd9d3037f5126dd69c672b72c668b763f4ac7` (✔200, PR #203 "audit-fix", 2024-05-31). | **P5** | The `AnonAadhaar.sol` wrapper passes `revealArray[2]`/`[3]` (labelled pincode/state) into the verifier slots that the circuit outputs as `state` then `pinCode`. Any consumer that reads `revealArray` acts on swapped identity attributes. **But no in-repo consumer reads them:** the wrapper returns a `bool`, and `example/AnonAadhaarVote.sol` uses only `nullifier` (checked at `c4ef0180`). E4 would need an authored consumer, so this is a verifier-interface P5, not a demonstrated effect. | Public; build cost unverified. The circuit is RSA-heavy Circom + Groth16, and the ptau size is unknown. | 3 |
| B2 | **Anon Aadhaar** | Same report, **High H1** "User can bypass nullifier by changing photo" | Same repo and audited commit. **No fix.** The auditor states "there is no way to avoid this situation". | **P3** | The nullifier includes the mutable photo, so one identity gets two valid nullifiers. In-repo effect: `AnonAadhaarVote.voteForProposal` keys `hasVoted[nullifier]`, so the identity votes twice. | Public; build cost unverified. Reproducing it needs two signed QR payloads that differ only in the photo. That is only feasible with test signing keys, so confirm that the test-key path exists. | 3 |
| B3 | **Singularity** (darkpool) | Zellic, *Singularity Zero Knowledge Security Assessment*, 2024-04-12, **Critical 3.8**: relayer and relayerGasFee are not public inputs. | Audited `portalgateme/darkpool-v1-zk-contracts@b9f2c713310c7a85ad50c9de78bfeee86b77a0a4` and `darkpool-v1-proof@608fa72d416ffa7fb4b4be15f24834937c203862`. **Both repos ✘404 (private).** Fix `b22be7df` is in a private repo. Public `portalgateme/singularity-contracts` is a 2-commit post-audit snapshot from 2024-08; the audited SHA is ✘422 there, and it has no circuits. | **P1** | Anyone resubmits an observed withdraw proof naming themselves as relayer with fee = amount; the consumer pays an unbound recipient. | **Low. UNPINNED for reproduction:** the vulnerable circuits (Noir) and contracts are not public. | Report only |
| B4 | Singularity | Same report, **Critical 3.5**: `amountOutMin`/`poolFee` are not public inputs (fixed in `c2e68b4b`). | Same as B3. **UNPINNED.** | **P1** | A front-runner reuses the swap proof with slippage 0 and a thin fee tier, stealing the note's value. | Low (private) | Report only |
| B5 | Singularity | Same report, **Critical 3.3**: fungible and position notes not domain-separated (fixed in `c2e68b4b`, `b37a1eab`, `a8a9968d`). | Same as B3. **UNPINNED.** | **P2** | A fungible-note proof is accepted as a claim on another user's Uniswap LP position note. | Low (private) | Report only |
| B6 | Singularity | Same report, **Critical 3.6**: dummy-note nullifier unconstrained in `curve_add_liquidity` (fixed in `fe268599`). | Same as B3. **UNPINNED.** | **P3** | An attacker's valid proof marks a victim's nullifier as used. The consumer consumes a replay key the proof did not legitimately own. | Low (private) | Report only |
| B7 | **Railgun** (v1) | ABDK, *Railgun Circom and Solidity Review*, 2021-07-02, **Critical CVF-20**: "Hashes of second and third commitments are missing" (Verifier.sol). Status: Fixed. | [Railgun-Privacy/contract](https://github.com/Railgun-Privacy/contract). Audited `6281cb0dac6a6e0da743e3ba56c437803657872d` (✔200, 2021-05-26). Audited circuits `2c3c31`: ✘422 in `Railgun-Privacy/circuits-v2`, and `Railgun-Privacy/circuits` is ✘404. **Circuit side UNPINNED.** **Fix commit not stated** in the report. | **P1** | The `inputsHash` preimage, the single public input, omits output commitments 2 and 3. Those outputs reach the Merkle tree without being bound by the proof. | **Medium.** The contract is public and pinned. You must find the v1 circuits (maybe vendored or with keys in the contract repo; check on acquisition) and the fix commit by diffing `Verifier.sol` history. | 2 |
| B8 | **Self** (OpenPassport) | zkSecurity, *Audit of Self EU ID cards Circuits, OFAC Checks, and Smart Contracts*, 2025-06-17, **High**: "Defaulting to a zeroed config on unknown configId enables verification bypass" | [selfxyz/self](https://github.com/selfxyz/self). Audited `4f18c75041bb47c1862169eef82c22067642a83a` (✔200, 2025-06-16). **Fix commit not given.** The client "is working on a fix … to revert on non-existing IDs". It must be found by diffing `IdentityVerificationHubImplV2.sol` history. | **P2** | The caller-supplied `userContextData.configId` picks the policy the proof is checked against. An unknown ID yields an all-false config, so a valid proof passes with no OFAC, age or country policy. | Public; build cost unverified (RSA/ECDSA passport circuits). The gate already holds two circuit-only Self pairs at the same commit, so the build path may be shared. **Caveat:** `selfxyz/self` is sampled EVAL family rank 259, which is spent under freeze 2. The guard says ALLOWED, but the family is already exposed. | 1 |
| B9 | **Succinct Telepathy** | Zellic, *Succinct Telepathy*, 2023-03-10, **High 3.1** "Missing replay protection on step" | [succinctlabs/telepathy-contracts](https://github.com/succinctlabs/telepathy-contracts). Audited `1c747c5c7d853a9b2761062c759a5c41feebaaf4` (✔200). Fix `485c2474cf18fb7375a48e999012616f1802ad57` (✔200, "check that a LightClient step update is newer than head (#221)"). | **P3** | A previously accepted `step` proof is re-accepted and rolls back `head` and the timestamp. The consumer has no consumed or monotone replay key. | **Medium-low.** Contracts are public and pinned. The circuits are Circom, but in a separate repo (not pinned here) and very large: a BLS sync-committee proof. A real proof may be unaffordable; a replay test needs only **one** honest proof plus its calldata. | 4 |
| B10 | **Nocturne** | Zellic, *Nocturne*, 2023-10-20, **Low 3.3** "Bundler calls can be identified by MEV bots and front-run" | [nocturne-xyz/protocol](https://github.com/nocturne-xyz/protocol). Audited `bfcbfcfcb8cf1a2209c874700a43ecac28e18fe7` (✔200, 2023-10-28, "Rebuild circuits"). **Not fixed** per R2. | **P1** | The gas refund goes to `msg.sender`, which the joinsplit proofs do not bind. A front-runner resubmits the bundle and takes the refund. | **High.** Circom circuits (`joinsplit.circom` etc.) and Solidity in one public repo at the audited commit. Low severity. | 3 |
| B11 | **Polygon ID / iden3** | Trail of Bits, *Iden3 Circuits Security Review*, 2024-05-03, **Informational TOB-IDEN3-6** "Signature challenge does not bind claim or query". Status: Unresolved. | [iden3/circuits](https://github.com/iden3/circuits). Audited `7a1e04de3e5f3a9f0cfb27a43c9f41c986c1b9ed` (✔200). **No fix.** The consumer is `iden3/contracts`, commit **not pinned** by the report. | **P1** | On chain the challenge is `msg.sender` only, so a signature or proof is not tied to the specific claim or query it authorizes. | **Medium.** Circuits are public and pinned; you must pick a contemporaneous `iden3/contracts` commit. Informational severity, and the auditor states no concrete effect. Weak positive. | 5 |
| B12 | **Hinkal** | zkSecurity, *Audit of Hinkal Protocol Smart Contracts and Circom Circuits*, 2024-09-06, **Medium**: "encryptedOutput and encryptedStakeCommitmentContent are not binding to the verified ZKP proofs". Status: Acknowledged. | Report links `github.com/Hinkal-Protocol/Hinkal-Protocol` (commit `cec95d4f…`, cited in another finding): **✘404 (private).** No audited commit stated for scope. **UNPINNED.** | **P1** | `encryptedOutputs` are left out of the proof-bound `calldataHash`. A front-runner replaces the note ciphertexts, and the consumer stores attacker data for the victim's outputs. | **Low** (private) | Report only |
| B13 | **Aleph Zero Shielder** | zkSecurity, *Audit of Aleph Zero Shielder*, 2025-03-25. R2 finding `ZSALEPH-0`, **Medium**: NewAccount/Deposit proofs do not commit to the fund sender. | [Cardinal-Cryptography/zkOS-monorepo](https://github.com/Cardinal-Cryptography/zkOS-monorepo) at `22e2f52` (short SHA, not API-checked). Finding text re-read: the proof "does not commit to the sender of the fund" (`depositERC20`). The circuits (`zkOS-circuits@491a0dd`) were **private** at audit time. Fix PRs in the report: monorepo #209–#212, circuits #90/#91. | **P1** | Anyone holding a deposit proof can deposit into, and poison, the user's account, because the sender is `msg.sender` and is absent from the public inputs. | **Off-language:** Halo2, not Circom/Noir. Keep only as a P1 contrast if the circuits are now public. | Alternate |

| B14 | **Railgun** (v1) | ABDK, same report as B7, 2021-07-02, **Critical CVF-58** (`Snark.sol`): "The function always returns true. It should return (out[0] != 0)." Status: Fixed; the client comment says it was changed to `return out[0] != 0`. | `Railgun-Privacy/contract@6281cb0dac6a6e0da743e3ba56c437803657872d` (✔200). The fix commit is **not stated**. | **P4** | The pairing check returns `true` unconditionally, so the consumer accepts any proof and acts on arbitrary public inputs. | **Medium-high for P4.** Contract-only: no circuit is needed to show acceptance of a garbage proof, but you need a deployable consumer at `6281cb`. | 2 |

**Language/toolchain check: rejected despite a binding-shaped finding.** These were read from the report scope sections only.

| Project | Finding | Reason rejected |
|---|---|---|
| Renegade | zkSecurity 2024-02-26, permit2 deposit not bound, P1 | PLONK/MPC in Rust with Stylus contracts; not Circom/Noir. |
| Lighter | zkSecurity desert-exit 2025-11-05, P1 | Plonky2/gnark, scope commit `b99c425b…`; not Circom/Noir. |
| Self `configId` | — | Kept as B8. |

### B.2 Coverage by pattern

| Pattern | Pinned, public candidates (reproducible) | Report-only (unpinned) |
|---|---|---|
| P1 | B7 Railgun (contract side only), B10 Nocturne, B11 iden3 | B3, B4 Singularity; B12 Hinkal; B13 Aleph (off-language) |
| P2 | B8 Self | B5 Singularity |
| P3 | B2 Anon Aadhaar, B9 Telepathy | B6 Singularity |
| P4 | B14 Railgun CVF-58 (constant-true pairing). CVF-60 (no on-curve check) is at the same commit. Gate row 40 (zkEmail proof-coordinate range) is already in Part A. | — |
| P5 | B1 Anon Aadhaar | — |

### B.3 Recommended acquisition order

1. **B8 (Self, P2, High)** first. It has a pinned audited commit and an in-repo consumer (the hub); the fix commit still has to be found.
2. **B14 and B7 (Railgun)** next. They share one pinned contract commit. B14 needs no circuit; B7 needs the v1 circuits located first.
3. **B10 (Nocturne), B2 and B1 (Anon Aadhaar)** after that. B1 is only an interface-level P5 unless a consumer reads `revealArray`.
4. **B9** only if a single honest Telepathy proof can be obtained.
5. **B3–B6 and B12** are not acquirable: their source is private. Cite them only as audit-reported prevalence. They cannot be reproduction targets.

---

## Assumptions, limitations, flags

- **Labels.** All P-labels and the "why it is a binding flaw" sentences are AI-written and await author review. The R2 census is likewise all AI-labelled.
- **Severity and fix status** are as stated in each report. Statements like "Fixed" in the ABDK report are not verified against code.
- **Unpinned sources:**
  - Singularity (all findings): private repos.
  - Hinkal: private repo.
  - Railgun: circuits `2c3c31` and the CVF-20 fix commit.
  - Self `configId`: fix commit.
  - iden3: consumer contracts commit.
  - Aleph Zero: short SHA unchecked; circuits were private.
  - Telepathy: circuits repo.
- **Exposure:**
  - `selfxyz/self` is a spent, sampled EVAL family. Anything found there is DEV evidence, not held-out evidence.
  - Under the build spec's anti-contamination rule, every Part B row has a public audit and is therefore a "known audit exists" case.
- **Excluded branch:** `sprint/R2` was BLOCKED on Solodit, so the census did not cover contest platforms beyond the few listed in `audits_read.csv`. More P4/P5 candidates may exist there.
- **Not done:** `docs/project-status.md` was **not** updated, because this task allowed writing only this file. A reviewer should add the checkpoint row if this ledger is accepted.

## Recommended next task

Acquire **B8 (Self `configId`, P2)**:

1. Pin `selfxyz/self@4f18c75041bb47c1862169eef82c22067642a83a`.
2. Locate the fix commit by diffing the history of `IdentityVerificationHubImplV2.sol`.
3. Build the circuits and verifiers locally with mock passport data.
4. Write frozen expected outcomes before any harness.

**Completion criterion:** E4 that a genuine proof with an unregistered `configId` is accepted by the unchanged hub and reaches the dApp callback with no policy applied; the fix commit reverts on the same input; and a legitimate run with a registered config passes. Record it in `reports/` with hashes. Record it as DEV evidence (spent family).

**Fallback:** if the Self build exceeds the budget, do B14 (Railgun CVF-58), which needs no circuit.
