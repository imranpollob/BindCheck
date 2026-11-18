# R2 — Audit-finding census: how often do auditors find binding flaws in funded protocols?
Status: BLOCKED (two of three completion criteria met; the Solodit criterion is blocked by an external outage)
Verdict/outcome: Binding flaws (P1–P3, P5) are **frequent in professional audits of ZK protocols** (18 of 68 audits, 34 findings, 17 High/Critical). This census does **not** show that the protocols were funded **at report time**: TVL at the report date is `UNKNOWN` for all 7 protocols with a High/Critical binding finding. The Solodit query set has not been run.

AI disclosure: Claude Code with Claude Opus 5.5 (`claude-opus-5-5`) ran this task on 2026-11-18. All labels are `label_source = AI` and need author review.

## What was done

1. **Read the governing files:** `AGENTS.md`, `docs/orchestration/README.md`, `docs/orchestration/R2-audit-census.md`. For P1–P5 I used the definitions in `docs/verdict-rules.md` and the signature analogy in `docs/sprint-eurosp-2027.md`.
2. **Ran the held-out guard** (`python3 scripts/check_holdout.py <owner/repo>`) on every protocol repository named in a report's scope.
   - 68 distinct repositories were ALLOWED.
   - 2 were FORBIDDEN: `tornadocash/tornado-core` and `AztecProtocol/aztec-packages`. I did not read any audit of either, and I opened no code from either.
   - For ALLOWED repositories I fetched only the `audits/` files, and only through blobless clones. I opened no protocol source code.
3. **Fetched and read the audit text:**
   - Auditor publication repos: Trail of Bits and Zellic, pinned commits.
   - In-repo audit folders, pinned commits: Semaphore, World ID, zkEmail, Privacy Pools, Anon Aadhaar, SP1 contracts, Polygon zkEVM, Taiko, zkSync.
   - zkSecurity Markdown reports.
   - Railgun's hosted audit PDFs.
   - The Sherlock reports repo.
   - Code4rena: findings repos for zkSync 2023-10 and 2024-03, and the web report for Succinct 2025-09.
4. **Triage method:**
   - For each report, I listed every finding with its severity, using small parsers in `results/raw/R2/{sec.py,tobsec.py,vsec.py,mdf.py,tri.sh,tobtri.py}`.
   - I read the full text of every candidate finding before including it.
   - A few reports were screened by finding title and severity only. Those audits are marked in `audits_read.csv` notes (Hexens zkEVM) and contributed no included rows.
5. **Recorded the census** with `reports/R2/r2tool.py` (stdlib only), which writes `findings.csv` and `audits_read.csv` and prints every total in this report.
6. **Logged borderline exclusions** in `excluded-borderline.csv`, with reasons, so the reviewer can overrule them.
7. **Recorded TVL at the report date** from the public DefiLlama API: protocol series, or chain DeFi TVL for rollups. The rule was the latest point on or before the report date, within 7 days; otherwise `UNKNOWN`. Nothing was estimated.

### Labelling rules (applied uniformly)

**Included.** Only findings where the auditor states that an accepted proof leads to one of:
- an unauthorized effect;
- a duplicated effect;
- a misdirected effect;
- a forged acceptance through the verifier or key configuration.

**Excluded:**
- Signature-only (ECDSA/EIP-712), TEE, and non-ZK Merkle-proof issues. They are listed in `excluded-borderline.csv` as signature analogues.
- Findings where the auditor gives a recommendation but no effect.

**Classes:**

| Class | Meaning |
|---|---|
| P1 | An effect field not bound by the proof: recipient, relayer, fee, slippage, outputs. |
| P2 | Missing domain or context separation: chain, policy/config selector, note type, circuit-to-circuit. |
| P3 | Replay key not canonical, not checked, not consumed, or not distinct. Includes reentrancy before the nullifier write. |
| P4 | Verifier or key configuration. **Includes in-circuit recursive or aggregation verifiers** that accept invalid inner proofs (Nebra, SP1, Scroll Euclid, Nori). Pure application-circuit under-constraint is `OUT`. |
| P5 | Public-input count or order mismatch between consumer and circuit. |
| OUT | Pure circuit under-constraint, counted only (per report, in `audits_read.csv:out_count`). Counting partly relied on finding titles. |

**`needs_circuit_to_detect`:**
- `yes` if a Solidity-only reader cannot decide the finding. That covers a circuit, a guest program, an off-chain verifier, or setup/vk tooling.
- `no` if the defect is visible in the on-chain consumer or verifier source, including Cairo, Yul, and DarkFi contracts.
- `unclear` if the cause spans both.

**`contract_only_tool_could_flag`:**
- `yes` only for a generic Solidity-level pattern: an argument that reaches an effect but not the verifier input; a nullifier write after an external call; a constant-true verifier; a missing point or scalar check; an admin-settable verifier.
- `unclear` when it needs protocol-specific semantics.

**Severity mapping:**
- The auditor's label is used as given.
- ABDK and PSE "Major" maps to H, "Moderate" to M, "Minor" to L, and "Warning" to I. Oxorio "WARNING" was never used for an included row.
- If no severity was stated: `UNKNOWN`. There are none among included rows.

## Evidence (paths, hashes, commands, exit codes, tool versions)

**Tracked (`reports/R2/`):**

| File | Contents |
|---|---|
| `findings.csv` | 54 rows. The columns are the prompt's, with plain names: `severity`, `class`, `protocol_tvl_usd_at_report`. |
| `audits_read.csv` | 68 rows: per-audit URL, sha256 of the fetched file, protocol repo, holdout flag, retrieved time, findings reviewed, included, OUT count. |
| `excluded-borderline.csv` | 29 rows. |
| `r2tool.py` | Census tool, sha256 `a6332457bbaeecf9554a0ac8ed1d82f2a2b5b733ee99cbd646a3d6e11e596064`. Run `python3 reports/R2/r2tool.py stats` to regenerate every table below. Exit status 0. |

**Raw evidence (ignored, `results/raw/R2/`):**
- `pdf-manifest.tsv`: sha256 of every PDF/MD read.
- `text/`: pdftotext output.
- `zks/`: zkSecurity Markdown.
- `railgun/`, `contests/`, `tvl/` (DefiLlama JSON, fetched 2026-11-18T00:39Z).
- `holdout-initial.tsv`.
- `solodit/access-log.txt`.
- `protocol-repo-heads.txt`.

**Pinned sources:**
- `trailofbits/publications@e08944909b8fcb747aef40ee294d92b2a9663685`
- `Zellic/publications@26c04f5b9c856e44d89cb0c9daf8c9842804e139`
- `sherlock-protocol/sherlock-reports@497f7158dcd99b7cc6512638e5da4465086832ad`
- `code-423n4/2023-10-zksync-findings@5159bc167a9958adce5de896f2383fab492963c9`
- `code-423n4/2024-03-zksync-findings@2ecd49087c9789e9dd2b3cdc41c3e444956c6416`
- Protocol repo heads are listed in `protocol-repo-heads.txt`. The `blob/<sha>` in each `report_url` carries the same pin.

**Tool versions:** pdftotext 24.02.0, Python 3.12.12, git 2.43.0, curl 8.5.0, Claude in Chrome (browser "POLLDELL") for Code4rena and Solodit.

**Solodit access log** (`results/raw/R2/solodit/access-log.txt`):

```text
2026-11-18T00:17:41Z solodit.cyfrin.io/?q=nullifier -> redirected to https://maintenance.cyfrin.io/?q=nullifier ('We're making things better.') via Chrome; WebFetch HTTP 429
2026-11-18T00:32:02Z retry 2 -> maintenance.cyfrin.io (Chrome)
2026-11-18T00:39:01Z retry 3 -> maintenance.cyfrin.io (Chrome)
2026-11-18T00:41:05Z retry 4: solodit.cyfrin.io/ (root) -> maintenance.cyfrin.io (Chrome)
```

### Solodit query table (completion criterion: not met)

| Query family (each × proof/zk/verifier/nullifier) | Run? | Result count |
|---|---|---|
| front-run / frontrun proof | no | BLOCKED (site in maintenance) |
| recipient not included in proof | no | BLOCKED |
| msg.sender not bound | no | BLOCKED |
| proof can be reused; replay proof | no | BLOCKED |
| nullifier not checked / not stored / not unique | no | BLOCKED |
| public input not validated | no | BLOCKED |
| field modulus / SNARK_SCALAR_FIELD / >= p | no | BLOCKED |
| malleable proof / proof malleability | no | BLOCKED |
| chainId not in public inputs; cross-chain replay | no | BLOCKED |
| external nullifier / scope | no | BLOCKED |
| verifying key / vkey mismatch; wrong verifier | no | BLOCKED |
| public input order / length mismatch; unchecked public signals | no | BLOCKED |

## Results (tables; exact counts)

**Coverage:**
- 68 audits or contest reports read. They come from 17 auditors or platforms:
  - Zellic 19, zkSecurity 17, Trail of Bits 7
  - EF PSE 4, Code4rena 4, Oxorio 3
  - Veridise 2, OpenZeppelin 2, Zokyo 2
  - Nethermind, yAcademy, Auditware, Hexens, Spearbit, Sherlock, ABDK, Hacken: 1 each
- They cover 43 product labels from 33 organizations (≥15 required).
- 728 individual findings were triaged.
- **54 findings included.** 80 more were pure under-constraint findings, recorded as `OUT` counts only.
- 27 audits have at least one included finding. 18 audits have at least one P1–P3/P5 finding.

**Class × severity** (from `findings.csv`):

| class | C | H | M | L | I | UNKNOWN | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| P1 | 3 | 1 | 4 | 3 | 2 | 0 | 13 |
| P2 | 1 | 1 | 1 | 1 | 3 | 0 | 7 |
| P3 | 4 | 6 | 1 | 0 | 1 | 0 | 12 |
| P4 | 6 | 11 | 1 | 1 | 1 | 0 | 20 |
| P5 | 1 | 0 | 0 | 1 | 0 | 0 | 2 |
| total | 15 | 19 | 7 | 6 | 7 | 0 | 54 |

Binding classes (P1–P3, P5): 34 findings, 17 of them High/Critical. Verifier/key (P4): 20 findings, 17 High/Critical.

**Key number: `needs_circuit_to_detect = yes`**

| Scope | yes | no | unclear |
|---|---|---|---|
| All 54 findings | **24 (44.4%)** | 26 (48.1%) | 4 (7.4%) |
| Binding classes only (34) | **13 (38.2%)** | 18 | 3 |

By class:

| Class | `needs_circuit_to_detect = yes` |
|---|---|
| P1 | 3/13 |
| P2 | 5/7 |
| P3 | 3/12 |
| P4 | 11/20 |
| P5 | 2/2 |

**`contract_only_tool_could_flag = yes`**

| Scope | yes | no | unclear |
|---|---|---|---|
| All 54 findings | **15 (27.8%)** | 24 (44.4%) | 15 (27.8%) |
| Binding classes only (34) | 12 (35.3%) | 13 | 9 |

By class:

| Class | `contract_only_tool_could_flag = yes` |
|---|---|
| P1 | 8/13 |
| P2 | 0/7 |
| P3 | 4/12 |
| P4 | 3/20 |
| P5 | 0/2 |

**Fixed:** yes 34 (63.0%), no 12 (22.2%), unknown 8 (14.8%).

**Highest-value protocols with a High/Critical finding.** TVL comes from DefiLlama at the report date, and only these High/Critical rows have a known value:

| Finding | Protocol | Class / severity | TVL at report | Source |
|---|---|---|---:|---|
| R2-ZKSFF-C-01 | zkSync Era (FFLONK verifier) | P4 / C | $87,696,009 | chain DeFi TVL 2024-09-26 |
| R2-TEUC1-1 | Scroll (Euclid aggregation circuit) | P4 / H | $65,124,156 | chain DeFi TVL 2025-04-04 |

Chain DeFi TVL is not bridge-secured value.

For the 7 protocols with a High/Critical **binding** (P1–P3, P5) finding, TVL at the report date is `UNKNOWN` in every case. In most of them the audit predates the DefiLlama series:
- Railgun (series starts 2022-01-28; ABDK audit 2021)
- Renegade (series starts 2024-09-05; audit 2024-02)
- Singularity, Succinct Telepathy, Anon Aadhaar, Self, DarkFi: no matching series

The current or later values I found are context only and were not entered in the CSV. For example, Railgun's DefiLlama TVL is about $105.9M in the 2026-11-18 snapshot.

### Five representative findings

1. **R2-ZSING-3.8 — Singularity, Zellic 2024-04-12 — P1 / C.** Relayer and fee are not public inputs, so anyone can resubmit a withdraw proof and take the fee. Auditor quote: "this function is public and msg.sender is not checked against anything". [Report p.36](https://github.com/Zellic/publications/blob/26c04f5b9c856e44d89cb0c9daf8c9842804e139/Singularity%20-%20Zellic%20Audit%20Report.pdf#page=36)
2. **R2-RGABDK-CVF-20 — Railgun, ABDK 2021 — P1 / C.** The verifier's inputs-hash preimage omits two output commitments. Auditor quote: "Hashes of second and third commitments are missing." [Report](https://assets.railgun.org/docs/audits/2021-04-01%20ABDK.pdf)
3. **R2-ZSING-3.2 — Singularity, Zellic — P3 / C.** Funds are paid before the nullifier is marked, so a reentrant recipient double-spends. Auditor quote: "transferring those funds to the relayer and/or user before marking the relevant" nullifier. [Report p.15](https://github.com/Zellic/publications/blob/26c04f5b9c856e44d89cb0c9daf8c9842804e139/Singularity%20-%20Zellic%20Audit%20Report.pdf#page=15)
4. **R2-ZSSELF2-1 — Self, zkSecurity 2025-06-17 — P2 / H.** An unknown policy `configId` silently selects an all-zero config, so a valid proof passes with no checks. Auditor title: "Defaulting to a zeroed config on unknown configId enables verification bypass". [Report](https://reports.zksecurity.xyz/reports/celo-self-audit-2.md)
5. **R2-AADH-C1 — Anon Aadhaar, EF PSE 2024-03 — P5 / C.** The consumer passes the revealed outputs in the wrong order. Auditor quote: "smart contract and TS code assign pinCode to state and state to pinCode". [Report](https://github.com/anon-aadhaar/anon-aadhaar/blob/4dad918761cfb1d7d5ed9918dcd796d0cb23ae82/audits/AnonAadhaar_audit_bbdfd9d.pdf)

### Answer: "Are binding flaws (P1–P3, P5) frequent in audits of funded protocols?"

**Yes for frequency in professional audits. Not shown for "funded at report time."**

**Evidence for frequency:**
- Binding flaws appear in 18 of 68 audits (26.5%): 34 findings, 17 of them High/Critical, across 7 audits (10.3%).
- These cover privacy pools (Singularity, Railgun, Hinkal, Aleph Zero), identity (Self, Anon Aadhaar, iden3), bridges/light clients (Telepathy, RISC Zero Helios), and dark pools (Renegade).
- The denominator includes many circuit-only and infrastructure audits with no proof consumer in scope (zkEmail circuits, Axiom, Hexens zkROM, Nebra), so 26.5% is a lower bound. The rate among audits whose scope includes an on-chain consumer would be higher. I did not compute that denominator.

**Where the evidence is weak:**
- The "funded" half of the gate fails on TVL evidence. No High/Critical binding finding has a known TVL at its report date, because these audits are mostly pre-launch.
- The two findings with a known TVL are P4 (verifier) on rollups worth tens of millions of dollars.
- The current verdict is "Yes, frequent", with the funding qualifier unsupported by TVL data.

**What this means for the gate's "Slither plus 20 lines" critique:**
- 38% of binding findings need the circuit or off-chain code.
- 35% could be flagged by a generic contract-only pattern.
- Contract-only tools catch most P1 (8/13) and miss all of P2 and P5.

## Assumptions and limitations

- **Solodit not queried.** The site was in maintenance for every attempt, so the query table is empty and the criterion is unmet.
- **Contest coverage is thin:**
  - Code4rena: 4 reports.
  - Sherlock: 1 report (Gamma–Brevis; no binding finding).
  - Cantina: the Axiom v2 report has a Critical, but I could not read it. The browser extension is denied on cantina.xyz, WebFetch shows only counts, and no PDF link was retrievable.
  - Hats: no public ZK competition found.
- **Target list gaps:** zkPassport, Sismo, Linea, Tornado forks, RISC Zero EVM verifier contracts, and Aztec Connect contracts have no audit read.
  - Tornado's canonical repo is FORBIDDEN; audit text would still be allowed.
  - The Aztec Connect folder held only a barretenberg fuzzing report, which was not counted.
  - World ID has one audit, with 1 best-practice finding.
- **Classification boundaries are judgment calls:**
  - In-circuit recursive or aggregation verifiers are labelled P4, not `OUT`.
  - Signature, TEE and non-ZK Merkle proofs are excluded. Under the "proof as signature" lens, a reviewer may prefer to include them (12 such rows are in `excluded-borderline.csv`).
- **OUT counts:** some came from finding titles and severity without full reading (Brevis, Hexens, zkEmail, Self). They are counts only and are not used in any headline rate.
- **Report dates:**
  - Month-only dates are recorded as `YYYY-MM`.
  - Undated reports are `UNKNOWN`: yAcademy zkEmail, Auditware Privacy Pools.
  - Hexens' date comes from its file name.
  - The Railgun ABDK file is named 2021-04-01, but its conclusion is dated 2 July 2021; I used 2021-07-02.
- **Holdout flag:** the Silent Protocol repo was not identified (`NOT_CHECKED`), and no code was opened.
- **Severity scales differ by auditor.** Cross-auditor severity counts are indicative only.
- **Authority conflict (stricter rule applied).** `AGENTS.md` asks for a `docs/project-status.md` checkpoint after each task, but the R2 prompt forbids edits outside `reports/R2/`. I did not edit `docs/project-status.md`. The reviewer should add the R2 node and checkpoint row on merge.

## Failed approaches / surprises

- **Solodit:** HTTP 429 to WebFetch. My curl probe with a browser user-agent was denied by the session's permission classifier, and I did not retry it. Chrome got redirected to the maintenance page.
- **Timestamps:** some `retrieved_utc` values were first typed by hand. Before the first commit I corrected all of them to file mtimes or `date -u` output.
- **Code4rena Succinct 2025-09:** the report has no public findings repo, so I read the web report in Chrome. The `sha256` field holds the hash of local excerpt notes, as marked in `audits_read.csv`.
- **Surprise:** P4 (verifier and key configuration) is as common at High/Critical as all binding classes combined (17 vs 17). Unpinned recursion vk_root recurs in two independent reports (Nori 18fa3; Code4rena Succinct M-01), and recursive-verifier digest checks fail in a third (SP1 Veridise VUL-004).

## Held-out hygiene statement (which families were read; confirm no unused EVAL family was opened)

- I checked every protocol repository named in a read audit with `scripts/check_holdout.py`. 68 were ALLOWED.
- `tornadocash/tornado-core` and `AztecProtocol/aztec-packages` were FORBIDDEN. I read no audit of either and opened no files from them.
- I opened no protocol source code at all. From ALLOWED repositories I checked out only audit report files, via blobless clones.
- One repository was not identified and not checked: Silent Protocol (`NOT_CHECKED`). Only zkSecurity's public report text was read for it.

## Recommended next task (one, with a measurable completion criterion)

**R2b — finish the Solodit query set when solodit.cyfrin.io is back.**

Completion criterion:
- Every query family × {proof, zk, verifier, nullifier} in the table above has a recorded result count and query URL.
- Every newly included finding has been read in full.
- `python3 reports/R2/r2tool.py stats` totals still match the report exactly.
- The "consumer-in-scope" denominator is recomputed. Add a `consumer_in_scope` column to `audits_read.csv` and report the binding-audit rate over it.
