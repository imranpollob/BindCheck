# BindCheck-zk: Project Closeout (2026-11-11)

## 1. Decision

- **Abstract registered:** IEEE S&P 2027 Cycle 2, on 2026-11-10.
- **Paper:** the authors are withdrawing it before the 2026-11-17 paper deadline.
- **Reason:** the evidence does not yet meet the S&P bar. Section 3 lists the gaps.
- **Status:** the project is paused, not abandoned. Everything below is preserved so the work can resume for a later venue.

Registered title:

> BindCheck: Assessing the Binding Between Zero-Knowledge Circuits and Smart Contracts in Blockchain Applications

The abstract drafts are in `/Users/imranpollob/Coding/bc/abstract-claude.md` and `abstract-chatgpt.md`, outside the repo.

## 2. What we have (findings with evidence)

### 2.1 Analyzer

- **Analyzer.** BindCheck is a fail-closed cross-layer checker. It traces a contract effect through the verifier's public inputs to the circuit's public interface. It also checks the verifier configuration.
- **Patterns:**
  - P1: unbound effect.
  - P2: context binding.
  - P3: replay key and field alias.
  - P4: verifier invariants, including γ = δ.
  - P5: public-input count and order.
- **Verdicts:** `VIOLATION`, `VERIFIED_WITHIN_SCOPE` or `UNKNOWN`.
- **Freeze 2:** content hash `92789fad…`, tag `bindcheck-zk-frozen-92789fad`, documented in `docs/FREEZE-2.md`.
- **Held-out run:** a single, one-shot run under that freeze.

### 2.2 Held-out measurement

- **Sample:** 277 preregistered open-source families. Artifact triples were recovered in 246.
- **Family-level VIOLATIONs:**
  - P1: 17.
  - P3: 33.
  - P4: 18.
  - P5: 38.
- **Decided per pattern:**
  - P1: 19/63.
  - P2: 3/113.
  - P3: 52/86.
  - P4: 110/246.
  - P5: 40/246.
- **Location:** `reports/heldout/`, with raw outputs under `results/raw/`.

### 2.3 Human labels

- **Analysis files:** `reports/labels/LABEL-ANALYSIS.md`. Labels were sealed (`review/labels/SEAL.md`) before analysis.
- **Set H:** 100 seeded stratified cards.
  - Raw agreement: 92/100, κ = 0.853.
  - Agreement on cards both raters decided: 91/91.
  - All 8 disagreements were "unclear versus decided". All were resolved to the decided label (`RESOLUTION-SHEET.csv`).
- **Final precision by stratum:**

  | Stratum | Precision |
  |---|---|
  | P4 γ = δ | 10/10 |
  | P4 guard | 7/10 |
  | P1 | 9/15 |
  | P3 | 9/15 |
  | P5 | 2/15 |

- **BindCheck overall precision:** weighted 0.60, unweighted 37/65. Arm C weighted: 0.23.
- **Rater A is an author.** Any future paper must disclose this.

### 2.4 Weak verifier keys (γ = δ)

- **Prevalence:** 56 γ = δ artifacts in 18 of the 142 families with parsed keys.
- **Root cause:** in every case γ = δ = the default BN254 G2 generator. That means an uncontributed setup, such as snarkjs `_0000.zkey`. Such keys admit forged proofs for arbitrary admissible public inputs.
- **Deployed signature matches:** 43 contracts, on four of the seven queried chains:

  | Chain | Matches |
  |---|---|
  | Base | 22 |
  | Ethereum | 13 |
  | Optimism | 7 |
  | Polygon | 1 |

- **No consumer link and no funds** for any of the 43.
- **Private data:** the census ledger `dataset/onchain-census.csv` stays private. Never publish addresses.
- **Prior report:** the class was already reported publicly (Zeto issue #186). Credit it.

### 2.5 Two new binding flaws

Both were reproduced at E4: genuine proofs on a local chain, with the repair rejecting the attack and legitimate runs passing. Details are in `findings/zkredential/`, `findings/racepass/` and `findings/POLICY-ANSWERS-2026-11-10.md`.

- **Z1, ZKredential.**
  - The gateway mint recipient is not bound to the proof's `walletAddress`.
  - Whoever first submits an unused proof receives the mint.
- **R1, RacePass.**
  - The `credHash` the contract acts on, which is also used for the revocation check, is not bound to the proof's `credentialHash`.
  - The code permits a revocation bypass, but we have not demonstrated one.
- **Not claimed:**
  - Z2 and R3 are unknown.
  - R2 is unresolved.
  - The replay and duplicate-claim interpretation for RacePass must not be asserted.
- **Origin:** both flaws came from development cases, not from the held-out run.

### 2.6 Benchmark

- **Size:** 68 cases.
  - 46 synthetic cases, with a mock verifier and AI-proposed labels.
  - 6 DEV-history cases.
  - 16 public pairs, giving 32 slots.
- **Public slot outcomes:**
  - 4 built successfully (BUILD_OK).
  - 14 timed out.
  - 2 failed.
  - 12 were structural only.
- **Location:** `reports/bench/REPORT.md`.

## 3. Key blockers (why we withdrew)

Ordered by how much each one would hurt the paper in review.

1. **No high-impact real-world finding.**
   - The two new flaws are in small or demo projects. The RacePass KYC circuit is marked "simplified demo".
   - None of the 43 γ = δ deployments has a consumer or funds.
2. **The headline numbers rest on a known, non-binding class.**
   - γ = δ is a key-equality check on uncontributed setups, and it was already publicly reported.
   - It is not cross-layer reasoning, yet it supplies most of the quantitative impact.
3. **The held-out run produced no reproduced flaw.**
   - Z1 and R1 came from DEV.
   - Held-out precision is moderate: 0.60 weighted, and P5 is 2/15.
   - The P5 false positives have known causes:
     - the proof array was counted as public inputs;
     - PLONK pairing-point inputs;
     - the wrong circuit was selected.
4. **The benchmark is weak evidence.**
   - Only 4 of 32 public slots build.
   - The synthetic cases use a mock verifier, and their labels were proposed by AI.
   - The synthetic BindCheck cells ran on the pre-freeze analyzer (`paper/zk/STATUS.md` §(c)).
5. **No recall and no comparison.**
   - Circomspect and Picus have no binding interface, so their UNKNOWN verdicts are only a normalization.
   - ZKAP was unavailable on all 277 families.
   - Recall on real code is unmeasured.
6. **Novelty is unclear against prior work.** The taxonomy overlaps with the SNARK-vulnerability SoK (Chaliasos et al.) and with ZKAP's integration-layer findings. The difference was never stated.
7. **The paper is unfinished.** `paper/zk/` has 45 `\MISSING{}` placeholders, and DEV-F34 still needs a decision (`STATUS.md` §(b)).

## 4. Obligations that survive the withdrawal

- **Disclosure.** The advisor should still disclose Z1 (ZKredential) and R1 (RacePass) to the maintainers. These flaws are real whether or not a paper exists.
  - The human sends the disclosures. Do not contact maintainers directly.
  - Record the dates. A future paper needs them.
- **Confidentiality.**
  - Keep `dataset/onchain-census.csv` private.
  - Never interact with deployed contracts.
  - Stop and report privately if a funded vulnerable deployment is ever found.
- **Data preservation.**
  - Keep `bindcheck-d1-paper/results/raw/` (16 GB, untracked).
  - Keep each worktree's `results/raw/`, which is git-ignored. Move it before removing any worktree.
- **The held-out sample is now spent.** The 277 families were measured once under freeze 2, and the false-positive analysis has been studied. Any future evaluation needs a new preregistered held-out sample, and the old 277 become DEV.

## 5. Recommended path to a future submission

The main goal is to find a reproduced binding flaw in a project that matters, discovered by the frozen tool on held-out data. Everything else supports that.

### Phase A: fix the analyzer (DEV only, on the old 277 plus the existing DEV)

1. **Fix the known P5 false-positive causes:**
   - exclude proof-array arguments;
   - model PLONK pairing-point public inputs;
   - improve circuit selection.
2. **Review P1 and P3 false positives.** Use the 6/15 false positives in each stratum from the Set H cards.
3. **Decide on `zk-relational`.** It has 8 commits and about 2.6k lines on the `relational` mechanism. It conflicts with `zk-paper` only in `bindcheck_zk/cli.py`. Merge it as part of the next freeze if it raises decided P1 or P3 coverage on DEV.
4. **Rerun the synthetic set on the frozen analyzer.** This closes `STATUS.md` §(c).
5. **Declare freeze 3** in `docs/FREEZE-3.md`, with a content hash and a tag.

### Phase B: impact-oriented held-out evaluation

1. **Preregister a new sample weighted toward deployed and used applications.** Examples: audited projects, projects with on-chain deployments that have consumers, and identity, airdrop or bridge applications. Unlike the old sample, this one should not be popularity-agnostic.
2. **Run one shot under freeze 3.**
3. **Reproduce every VIOLATION at E4 on a local chain, then disclose.**
4. **Keep the stop rule:** if a funded vulnerable deployment turns up, stop and report privately.

### Phase C: evidence quality

1. **Benchmark.**
   - Raise the public-pair build rate above 4/32: pin toolchains and cache ptau files.
   - Replace mock verifiers with generated ones.
   - Have humans label the synthetic expectations.
2. **Recall.**
   - Report recall on the buildable benchmark.
   - Add seeded-mutation recall: inject P1, P3 and P5 binding breaks into repaired applications.
3. **Comparison.** Build an adapter that gives one binding-relevant baseline (ZKAP if obtainable) a shared subtask, or state precisely why no tool can be compared.
4. **Raters.** Use two raters who are not authors and do not use AI. Seal their labels before analysis, as before.

### Phase D: paper

1. **Position against prior work.** Add an explicit novelty table against the SNARK-vulnerability SoK, ZKAP, Circomspect, Picus, zkFuzz, CIVER and ELSA.
2. **Rescope γ = δ.** Present it as a measurement finding with root cause, crediting Zeto #186, not as the headline result.
3. **Lead with cross-layer binding findings from the held-out evaluation.**
4. **Disclose AI use and author-raters.**
5. **Close every `\MISSING`.** Choose the venue after Phase B results are in: S&P, USENIX Security, CCS or NDSS. Check each CFP's resubmission rules and deadlines then. None are assumed here.

## 6. Repository state at closeout

- **`main`** is at `16eb597`. It is an ancestor of `zk-paper`, so it can be fast-forwarded.
- **`zk-paper`** holds `main` plus the paper, findings, policy answers, this document and the A26 chain-count fix.
- **`zk-relational`** is not merged (see §5 A3). It conflicts in `bindcheck_zk/cli.py`. Merging it changes the frozen analyzer's content, so keep tag `bindcheck-zk-frozen-92789fad` as the reference.
- **All other lane branches** are already in `main`.
- **Worktrees:** `BindCheck` (main), `bindcheck-d1-paper`, `bindcheck-zk`, `bindcheck-zk-paper` and `bindcheck-zk-relational`.
