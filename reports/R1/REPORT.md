# R1 — Incident and bug-bounty census (2019–2026)

Status: DONE

Verdict/outcome: **Yes, one public money loss outside P4.** Aztec Connect
(14 June 2026) lost about $2.1M (Aztec Labs' own figure) through a binding
failure, labelled **P5** (alternative label: P1). No P1, P2 or P3 case with a
money loss was found. All other money losses are P4 (verifier layer) or OUT.
The class labels are AI-proposed and need author review (see *Assumptions*).

AI disclosure: this task was run by Claude Code with model Claude Opus 5.5
(`claude-opus-5-5`). It did the searching, the reading, the CSV transcription
and the labelling. The author has not yet reviewed any label.

## What was done

- Searched every source in the R1 minimum list (searches listed below). The
  incident databases were read in full:
  - DefiLlama hacks API: 1,360 events.
  - SlowMist Hacked: all 119 list pages, 2,372 events.
  - The rekt.news leaderboard.
  - All 90 Immunefi bugfix-review links on `immunefi.com/research`.
  - The whole 0xPARC `zk-bug-tracker` README.
- Queried GitHub Security Advisories for:
  - 17 repositories;
  - 19 ZK packages, through the global advisory API.
- Confirmed all seven known leads against the best source reachable.
  Found new cases, including two June 2026 Aztec drains and HermesVault.
- Ran `scripts/check_holdout.py` on 47 repository names. Did not open code or
  advisory pages of the four FORBIDDEN families.
- Wrote:
  - `reports/R1/incidents.csv`: 50 rows, one per case.
  - `reports/R1/summarize.py`: recomputes every table below from the CSV.
- No code was run against any system. No live contract was touched. No person
  or project was contacted.

## Evidence (paths, hashes, commands, exit codes, tool versions)

| Item | Value |
|---|---|
| Base revision | `4126b639dff504b0fc5ca52faeb4ec7574674171` (branch `sprint/R1`) |
| CSV | `reports/R1/incidents.csv`, sha256 `fbfa59a2d385c87e53d45e4a003c9d588cb47265f21cf7355f3918833a41009b`, 50 rows |
| Totals script | `python3 -I reports/R1/summarize.py` → exit 0; output saved to `results/raw/R1/summarize-output.txt` |
| CSV builder (transcription source) | `results/raw/R1/build_csv.py` (ignored; asserts the class and exploited enums) |
| Search log | `results/raw/R1/search-log.tsv` (51 entries) |
| Raw pages | `results/raw/R1/sources/` (12 MB; 207 files hashed in `results/raw/R1/SHA256SUMS`) |
| Key hashes | zk-bug-tracker README `31a39587…`; DefiLlama hacks `382c33c6…`; Xion PR #608 JSON `9894530d…`; EIP-7520 draft `e915c939…`; rekt Aztec Connect `8e1cc96e…`; rekt Aztec Bridge `fcaf6ef4…`; zkSecurity Groth16 post `bbb45b7f…`; zkSync incident 764 `e6d6b9e7…` |
| Held-out guard | `python3 scripts/check_holdout.py …`. Batch 1 (25 names) and batch 2 (22 names) both exit 1, because each batch contains FORBIDDEN names (listed below) |
| Tools | curl 8.5.0; Python 3.12.12; WebSearch/WebFetch (Claude Code); GitHub REST API (unauthenticated, read-only) |

## Results (tables; exact counts)

The tables below are the verbatim output of `summarize.py` on the committed
CSV. They have these properties:

- Sums cover numeric cells only. "(+n UNKNOWN)" counts the cells left
  UNKNOWN; none was estimated.
- The confirmed loss is a figure stated by the affected project itself.
- The claimed loss is the figure in incident databases or press.
- The USD date of each figure is in the `usd_date` column.

### Cases, exploitation and money per class

| Class | Cases | Exploited (yes) | Whitehat drain | Not exploited | Claimed loss USD | Confirmed loss USD | Recovered USD | Value at risk USD |
|---|---|---|---|---|---|---|---|---|
| P1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P3 | 7 | 0 | 0 | 7 | 0 (+7 UNKNOWN) | 0 (+7 UNKNOWN) | 0 (+7 UNKNOWN) | 0 (+7 UNKNOWN) |
| P4 | 4 | 3 | 1 | 0 | 7,294,466 | 0 (+4 UNKNOWN) | 1,840,000 (+3 UNKNOWN) | 0 (+4 UNKNOWN) |
| P5 | 4 | 1 | 0 | 3 | 2,280,000 (+3 UNKNOWN) | 2,100,000 (+3 UNKNOWN) | 0 (+4 UNKNOWN) | 0 (+4 UNKNOWN) |
| OUT | 35 | 1 | 1 | 33 | 2,197,000 (+34 UNKNOWN) | 0 (+35 UNKNOWN) | 0 (+35 UNKNOWN) | 1,905,000,000 (+33 UNKNOWN) |
| ALL | 50 | 5 | 2 | 43 | 11,771,466 (+44 UNKNOWN) | 2,100,000 (+49 UNKNOWN) | 1,840,000 (+49 UNKNOWN) | 1,905,000,000 (+48 UNKNOWN) |

Exploited cases in the counted classes (P1–P5):

| Case | Class | Project | Claimed USD | Confirmed USD | Recovered USD |
|---|---|---|---|---|---|
| R1-001 | P4 | Veil Cash | 5,000 | UNKNOWN | UNKNOWN (100% of 2.9 ETH returned) |
| R1-002 | P4 | FoomCash (whitehat drain) | 2,260,000 | UNKNOWN | 1,840,000 |
| R1-003 | P4 | ZKSwap | 5,000,000 | UNKNOWN | UNKNOWN |
| R1-004 | P4 | HermesVault | 29,466 | UNKNOWN | UNKNOWN |
| R1-005 | P5 | Aztec Connect | 2,280,000 | 2,100,000 | UNKNOWN |

### Timeline (year × class)

The year is taken from `date_incident`, else from `date_disclosed`.

| Year | P1 | P2 | P3 | P4 | P5 | OUT | Total |
|---|---|---|---|---|---|---|---|
| 2019 | 0 | 0 | 1 | 0 | 0 | 2 | 3 |
| 2022 | 0 | 0 | 2 | 0 | 2 | 1 | 5 |
| 2023 | 0 | 0 | 2 | 0 | 0 | 6 | 8 |
| 2024 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| 2025 | 0 | 0 | 0 | 1 | 0 | 5 | 6 |
| 2026 | 0 | 0 | 0 | 3 | 2 | 5 | 10 |
| UNKNOWN | 0 | 0 | 2 | 0 | 0 | 15 | 17 |

All five exploited cases in P1–P5 happened between July 2025 and June 2026.
Before July 2025, every in-scope case found was a disclosure, a bounty or a
proof-of-concept.

### The five most important cases

1. **R1-005 Aztec Connect, 14 June 2026, P5 (alternative P1). About $2.1M confirmed; $2.28M claimed.**
   - The flaw: the rollup proof committed to a full 32-row inner chunk, but
     `processRollup` settled only the first `numRealTxs` rows. Nothing bound
     the attacker-set `numRealTxs` to the proof.
   - The attack: fake deposit rows placed after `numRealTxs` were proved and
     credited, but never collected on L1. Real withdrawals at row 0 then paid
     out 909 ETH, 270,513 DAI, 167.89 wstETH and four other assets in one
     transaction (`0x074ec931…eeb1`).
   - A second actor reused the flaw the next day for about $88K.
   - The contract was immutable and its admin keys had been renounced in
     April 2024, so nothing was recovered.
   - Status: this is the only exploited case in the census where the proof
     was valid and the contract's action differed from what was proved. It
     answers the reviewer's question for the binding paper. The root cause
     comes from rekt and SlowMist/BlockSec summaries. The primary Aztec Labs
     incident report was not retrieved.
2. **R1-002 FoomCash, 26 February 2026, P4, $2.26M claimed.**
   - The Groth16 verifiers on Ethereum and Base had γ₂ = δ₂ = the G2
     generator: the snarkjs phase-2 contribution was never run. Proofs could
     therefore be forged for any `nullifierHash`.
   - Both drains were by whitehat or bounty actors:
     - Decurity returned $1.84M and received a $100K fee.
     - duha kept a $320K bounty under FoomCash's own "only rule is code"
       challenge.
   - The net cost to the protocol was about $420K.
   - Status: mechanism is primary (zkSecurity, whose team member did the Base
     drain). Amounts are secondary (FoomCash's X posts were quoted by
     Cointelegraph, not retrieved).
3. **R1-003 ZKSwap, 9 July 2025, P4, $5M claimed.**
   - In Exodus Mode, `verifyExitProof()` did not verify anything, so
     fabricated exit proofs withdrew bridge funds. Verichains says a test
     verifier was left deployed.
   - Status: no ZKSwap statement was found. The figure comes from Blockaid,
     DefiLlama and SlowMist. Verichains gives the year as 2024, against 2025
     in every other source.
4. **R1-001 Veil Cash, 20 February 2026, P4, 2.9 ETH (about $5K).**
   - The same γ = δ misconfiguration as FoomCash. Fabricated nullifiers
     `0xdead0000…0xdead001c` drained the 0.1 ETH pool in 29 withdrawals in
     one transaction.
   - The exploiter returned the funds; rekt quotes Veil as recovering 100%.
   - Status: the first publicly confirmed exploit of a deployed ZK verifier
     key. It published the technique that was reused against FoomCash.
5. **R1-016 Aztec 2.0 Private Rollup Bridge, 17 June 2026, OUT, $2.197M claimed.**
   - The escape-hatch circuit used `old_data_root` twice without an equality
     constraint. The attacker proved membership in a fake tree while exposing
     the real root, which the Solidity `require(oldDataRoot == dataRoot)`
     accepted.
   - The circuit had been removed from the code (PR #402), but its
     verification key was still deployed.
   - Status: labelled OUT (under-constrained circuit). It is a boundary case:
     the contract checked the right value, but the circuit did not bind that
     public input to the value it used.

### Answer: is there any public money loss in classes P1, P2, P3 or P5?

**Yes, with one case.** R1-005, Aztec Connect, June 2026, is labelled P5
(alternative P1):

- Aztec Labs' own statement, quoted verbatim by rekt, says "~$2.1m was
  transferred from the immutable smart contract".
- Claimed total over two attackers: $2.28M.
- Independent alerts and analyses: CertiK, BlockSec Phalcon, SlowMist,
  Blockaid, DefiLlama ($2.1M) and SlowMist Hacked ($2.1M).

By class:

- **P1 and P2:** zero cases of any kind found, with or without loss.
- **P3:** seven disclosures (2019–2023 and a gnark advisory). None had a
  recorded loss; all were fixed before exploitation, or only demonstrated.

This answer depends on one AI label. If the author reclassifies Aztec Connect
as OUT, the answer becomes **No**. Grounds for OUT would be that the circuit's
padding semantics, not the contract's count, are the root cause. Aztec Labs'
incident report should be read before the 21 Nov gate.

### Leads (completion criterion)

| Lead | Row | Primary source | Note |
|---|---|---|---|
| FoomCash (Feb 2026, ~$2.26M) | R1-002 | zkSecurity post (mechanism) | Amounts secondary. $2.26M is gross; net ~$420K; early counts $1.5–1.8M. |
| Veil Cash (Feb 2026, ~$5.7K, returned) | R1-001 | Base tx `0x5ff6…a17d` (URL recorded; explorer not opened) | $5,000 in SlowMist/DefiLlama amount fields; $5.7K in DefiLlama text; 5 ETH per zkSecurity. No Veil statement found. |
| ZKSwap (Jul 2025, ~$5M) | R1-003 | Etherscan label page (URL recorded; not opened) | No ZKSwap post-mortem exists in any source searched. |
| Xion PR #608 (Sep 2026) | R1-006 | PR #608 (read through the API) | Merged 2026-09-04. No exploit or value stated. |
| Semaphore #90 | R1-007 | Issue #90 | **Disagreement with prompt:** the prompt lists it as a P3 example; the issue describes a liveness failure (groupId ≥ r reverts every proof). Labelled P5. The double-spend Semaphore case is issue #16 (R1-009). |
| EIP-7520 | R1-009 (notes and secondary URLs) | EIPs PR #7733 + draft text at the PR head | EIP-7520 is an **unmerged draft ERC** by Beosin (2023-09-20, PR closed). It is a standards proposal motivated by Semaphore #16 and CVE-2023-33252, not an incident, so it has no row of its own. |
| Zcash 2018 counterfeiting | R1-018 | ECC blog, 2019-02-05 | OUT. ECC found no evidence of exploitation. |

## Assumptions and limitations

- **Labels are AI-proposed** (`label_source=AI` on every row). The boundary
  rules used were:
  - P4 = key, deployment or verification bypass;
  - verifier *implementation* bugs (Aztec "0 bug", Frozen Heart) = OUT;
  - in-circuit under-constraint = OUT, except where the prompt names the case
    as P3 (Aztec 2.0 nullifier, StealthDrop).
  - R1-004 HermesVault is low confidence: SlowMist's text cannot separate a
    verification bypass from a consumer logic bug.
- **Loss columns:**
  - `loss_confirmed_usd` is filled only where the affected project states a
    USD figure. Only Aztec Connect qualifies, and only through rekt's verbatim
    quote.
  - Native-token amounts (2.9 ETH, 261,000 ALGO, 1,158 ETH, …) are in `notes`
    and were not converted.
  - `recovered_usd` is UNKNOWN for Veil although 100% was returned, because no
    USD figure was stated.
- **Primary sources:** many rows are `source_grade=SECONDARY` in `notes`.
  - The Aztec Labs incident reports, FoomCash and HermesVault X posts and the
    OtterSec post were not retrieved.
  - medium.com (Immunefi copies, ChainLight, SlowMist's Aztec analysis)
    returned Cloudflare 403. Immunefi's own site copies were used where they
    exist.
  - Explorer and Etherscan-label URLs were recorded but not opened.
- **Scope of "every case":**
  - Rows are incidents, bounties, advisories and public disclosures.
  - Audit-report findings (for example OpenZeppelin's Linea PLONK verifier
    finding, small-repo GitHub issues, CodeHawks contest findings) are left to
    R2 and not counted.
  - OUT is recorded broadly but not exhaustively: 54 further Noir advisories,
    three further 2026 gnark advisories and four RISC Zero advisories have no
    rows.
- **Screened out (not ZK-proof failures, or too little evidence):** these
  DefiLlama "Forged Proof / Proof Verifier Bug" entries are not ZK:
  - BNB Bridge 2022 (IAVL Merkle);
  - Hyperbridge 2026 (MMR proof);
  - Taiko Bridge 2026 (leaked SGX key);
  - zkLink Nova 2026 (message-hash reuse);
  - Verus, Syscoin, Alephium, Adshares, TAC and Nomad.

  Also screened out:
  - Vara Bridge 2026-10-19 ($12,776): the ZK relay path cannot be confirmed
    from available text.
  - The "snarkjs verifier checked q instead of r (Feb 2025)" claim: a single
    secondary source.
  - Typhoon Network: no incident evidence.
  - zk-bug-tracker items that are not soundness or binding bugs: Dusk
    blinding, Aleo encryption, Light Protocol atomicity.
  - Unread disclosures (Jolt uniskip, Dusk PLONK 2026, Stwo, Scroll Keccak)
    were not ingested.
- **Dates:** 17 rows have no recoverable year. These are mostly 0xPARC
  tracker entries, which carry no dates.
- **Project checkpoint:** `AGENTS.md` asks for an update to
  `docs/project-status.md`. R1 owns only `reports/R1/` and the R1 prompt
  forbids other paths. The stricter rule was followed, and the checkpoint row
  is left to the reviewer.

## Failed approaches / surprises

- The FoomCash figure is gross, not net. The prompt's "~$2.26M" includes
  $1.84M returned within hours, and both drains were by whitehat or bounty
  actors.
- Aztec Connect: the largest binding-class loss was not on any lead list. It
  appeared only through a "legacy Aztec" search and the incident databases.
- EIP-7520 is not on eips.ethereum.org (404). It was found only as the closed
  EIPs PR #7733.
- The SlowMist Hacked site search needs a CSRF-protected POST, so all list
  pages were crawled instead (0.4 s between requests).
- Fetching Medium through a third-party reader proxy was blocked by the
  session's permission policy and was not retried. Those facts stay
  secondary.
- A shell typo (`cat >` with no input) created an empty stray file at
  `/home/pollmix/Coding/bc_txt.py`, outside the worktree. It was empty, was
  created by this session, and was deleted at once. No other files outside
  R1's paths were changed.

## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)

- **Repositories whose GitHub pages or API records were read** (all ALLOWED):
  - `burnt-labs/xion` (PR #608);
  - `semaphore-protocol/semaphore` (issues #16, #90, PR #91);
  - `privacy-scaling-explorations/zk-kit` (issue #23);
  - `a16z/zkdrops` (PR #2);
  - `ethereum/EIPs` (PR #7733);
  - the security-advisory lists of 17 repositories, all ALLOWED or not in the
    corpus;
  - `0xPARC/zk-bug-tracker` README.
- **No repository was cloned and no source code was opened.**
- **FORBIDDEN names found:**
  - `AztecProtocol/aztec-packages` (v2-family:481e9487608e6e49df68);
  - `tornadocash/tornado-core` (v2-family:288524d1ec6a14d95809);
  - `darkforest-eth/darkforest-v0.3` (v2-family:e636c7f0034c63ddce2e);
  - `summa-dev/summa-solvency` (v2-family:edca876b5659d700d9cd).

  For these, only third-party write-ups were read: rekt, 0xPARC tracker text.
  Their repositories, code and advisory pages were not opened. Barretenberg
  advisories under `aztec-packages` were therefore **not** searched.
- I confirm that no unused EVAL family was opened.

## Recommended next task (one, with a measurable completion criterion)

**R1b — primary-source and label review of the counted rows.**

1. The author reviews the class label of all 15 P1–P5 rows and sets
   `label_source=AUTHOR` where accepted.
2. The coder retrieves:
   - Aztec Labs' incident reports for R1-005 and R1-016;
   - FoomCash's 1–2 March 2026 posts;
   - a ZKSwap statement, or records that none exists.

Completion criterion:

- Every exploited P1–P5 row has a project-authored primary URL, or a recorded
  reason why none exists.
- R1-005 carries an author-confirmed class.
- `summarize.py` output is regenerated and pasted unchanged into an R1b
  report.

This settles the single label the 21 Nov gate answer depends on.
