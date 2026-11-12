# BindCheck: Project Status, Review, and Next Steps (2026-11-11)

This is a self-contained handoff. Read it first on the new machine. The detailed closeout record is
`BindCheck/docs/PROJECT-CLOSEOUT-2026-11-11.md`, and the paper's working status is `BindCheck/paper/zk/STATUS.md`.

---

## 1. Snapshot

| Item | State |
|---|---|
| Venue | IEEE S&P 2027, Cycle 2 |
| Abstract registration | Registered on 2026-11-10. Withdrawal was considered on 11-11; the current plan is a 7-day push. Check the HotCRP status (active or withdrawn, abstract editable or locked). |
| Paper deadline | **2026-11-17** |
| Title | BindCheck: Assessing the Binding Between Zero-Knowledge Circuits and Smart Contracts in Blockchain Applications |
| Current abstract | `BindCheck/abstract.md`. Number-free, so it can absorb new results (staged, not committed). |
| Framing | Benchmark + measurement study. BindCheck is a fail-closed cross-layer checker. The paper makes **no** comparative "detects better than X" claims. |
| Analyzer | Freeze 2. Content hash `92789fad…`, tag `bindcheck-zk-frozen-92789fad`. Any change to `bindcheck_zk/` requires a new freeze declaration. |
| Paper draft | `BindCheck/paper/zk/`. **44 `\MISSING{}` placeholders** remain across the sections. |
| Git | `main` @ `beba4bb`, pushed (private repo `github.com/imranpollob/BindCheck`). Branches: `main` and `zk-relational` (8 unmerged commits). Tags: `bindcheck-zk-closeout-2026-11-11`, `archive/claude-code`, `archive/evidence-d1-n8`. |

---

## 2. What the project has (with evidence locations)

### Problem and method

- **The problem.** A contract can accept a valid ZK proof yet act on values the proved statement does not fix. Binding the proof to the action requires agreement among three artifacts: the circuit, the generated verifier, and the consuming contract.
- **The checker.** BindCheck traces contract effects through the verifier's public inputs to the circuit's public interface. It also checks the verifier key and configuration.
- **Patterns:**
  - P1: unbound effect
  - P2: context binding
  - P3: replay key / field alias
  - P4: verifier invariants, including γ = δ
  - P5: public-input count/order
- **Verdicts:** `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or `UNKNOWN`. Timeouts and unsupported inputs never count as safe.

### Held-out measurement (one-shot, preregistered, under freeze 2) — `reports/heldout/`

- **Sample.** 277 families. Artifact triples were recovered for 246.
- **Family VIOLATIONs:**

  | Pattern | Families |
  |---|---|
  | P1 | 17 |
  | P3 | 33 |
  | P4 | 18 |
  | P5 | 38 |

- **Decided per pattern:**

  | Pattern | Decided |
  |---|---|
  | P1 | 19/63 |
  | P2 | 3/113 |
  | P3 | 52/86 |
  | P4 | 110/246 |
  | P5 | 40/246 |

- **This sample is now spent as held-out data.** It is DEV from here on.

### Human labels (sealed before analysis) — `reports/labels/LABEL-ANALYSIS.md`, `review/labels/`

- **Set H.** 100 seeded cards; 92/100 agreement, κ = 0.853; 91/91 on decided cards. All 8 disagreements were "unclear vs decided" and were resolved to the decided label.
- **Precision:**

  | Stratum | Precision |
  |---|---|
  | P4 γ = δ | 10/10 |
  | P4 guard | 7/10 |
  | P1 | 9/15 |
  | P3 | 9/15 |
  | P5 | 2/15 |

  Weighted 0.60; unweighted 37/65. Arm C weighted 0.23.
- **Rater A is an author.** Disclose this.

### Weak verifier keys (γ = δ)

- **Prevalence.** 56 artifacts in 18 of the 142 families with parsed keys.
- **Root cause.** γ = δ equals the default BN254 G2 generator, which comes from an uncontributed setup (snarkjs `_0000.zkey`).
- **Census.** 43 deployed signature matches on 4 of 7 chains: Base 22, Ethereum 13, Optimism 7, Polygon 1. None has a consumer link and none is funded.
- **Prior report.** The class was reported publicly in Zeto #186. Credit it.
- **Census ledger.** `dataset/onchain-census.csv` is **private**. Never publish addresses.

### Two new binding flaws (E4: genuine proofs, local chain, repair validated) — `findings/`

- **Z1 (ZKredential).** The mint recipient is not bound to the proof's `walletAddress`.
- **R1 (RacePass).** The contract acts on a `credHash` (also used for the revocation check) that is not bound to the proof's `credentialHash`.
- **Not claimed:** Z2 and R3 (unknown) and R2 (unresolved). Do not assert the RacePass replay or duplicate-claim reading.
- **Origin.** Both came from **development cases**, not from the held-out run.
- **Policy answers.** `findings/POLICY-ANSWERS-2026-11-10.md`.

### Benchmark — `reports/bench/REPORT.md`

- **Composition.** 68 cases: 46 synthetic (mock verifier, AI-proposed labels), 6 DEV-history cases, and 16 public pairs (32 slots).
- **Public slot outcomes:** 4 BUILD_OK, 14 timeout, 2 failed, 12 structural.
- **Stale cells.** The synthetic BindCheck cells were run on the **pre-freeze** analyzer, so a rerun is pending.

---

## 3. Review from a program-committee perspective

**Likely outcome if submitted today:** weak reject, with a major revision as the best case. The paper is coherent and rigorous, but the evidence is thin where S&P reviewers look first.

### Strengths a reviewer will credit

1. **A real, under-served problem.** Circuit-only and contract-only tools structurally cannot see binding flaws. The cross-layer framing is the core idea.
2. **Methodological discipline:**
   - preregistration and a one-shot held-out run under a declared freeze;
   - sealed blind labels with high agreement;
   - fail-closed verdicts.
3. **Concrete, reproduced findings.** Z1 and R1 were reproduced with genuine proofs and validated repairs.

### Weaknesses, ranked by damage

1. **Impact is thin.** Both new flaws are in small or demo projects; the RacePass KYC circuit is marked "simplified demo". None of the 43 γ = δ deployments has funds or a consumer. Reviewers will ask, "Who is actually at risk?"
2. **The numbers rest on a known, non-binding class.** γ = δ is a key-equality check on uncontributed setups, and it has already been reported publicly. It is not cross-layer reasoning.
3. **The held-out run produced no reproduced flaw.** Z1 and R1 came from DEV, and held-out precision is moderate. The P5 false positives have known causes:
   - the proof array was counted as public inputs;
   - PLONK pairing-point inputs;
   - the wrong circuit was selected.
4. **Weak benchmark.** Only 4/32 public slots build, and the synthetic cases use a mock verifier with AI-proposed labels.
5. **No recall and no comparison.** Circomspect and Picus have no binding interface, and ZKAP was unavailable.
6. **Novelty against prior work is not stated.** The SNARK-vulnerability SoK (Chaliasos et al.) and ZKAP both cover integration-layer bugs. The paper must say what the taxonomy and the checker add.
7. **The paper is unfinished.** There are 44 `\MISSING`, and the DEV-F34 decision is pending (`paper/zk/STATUS.md` §(b)).

**The one change that would move the verdict most:** a binding flaw that the frozen tool discovered on held-out data, reproduced at E4, in a project that matters.

---

## 4. Seven-day plan (to 2026-11-17), if attempting submission

**Goal:** turn held-out true positives into reproduced findings, and finish the paper from existing results. **No new held-out run** — there is not enough time to do one validly.

### Day 1–3 — Lane R (reproduction), max 2 parallel cases

The 18 held-out cards that the raters labelled TP (`reports/labels/set-H-ledger.csv`, `final = TP`):

| Pattern | Repository (warning IDs) |
|---|---|
| P1 | kenyiu/zk-comments (W0095) |
| P1 | elohcrypto/zk-hybrid-rollup (W0196) |
| P1 | nara020/zk-private-lending (W0225, W0241, W0497) |
| P1 | andrea-rizzini/A-Private-Smart-Wallet-with-Probabilistic-Compliance (W0419) |
| P1 | overhyped-pratham/agriproof-ai (W0555) |
| P1 | naizo01/TrustlessInheritance (W0579) |
| P1 | mihwuan/H-ZKA (W0746) |
| P3 | 0xbri3t/Privacy-Vaults (W0239) |
| P3 | TuCopFinance/ShieldMoney (W0388) |
| P3 | SolidityDrone/Gazometer (W0403) |
| P3 | hyluc-oss/e-chaguzi (W0432) |
| P3 | iitianpushkar/Unicloak (W0460, W0700, W0768) |
| P3 | NandakishorP/ZK_Privacy_LendingProtocol (W0629) |
| P3 | iitianpushkar/VeilForge (W0678) |

1. **Triage.** Rank the cards by buildability, by whether a clear policy can be stated, and by impact (funds or assets involved, a lending or vault application). Pick 2–4.
2. **Reproduce at E4, as was done for Z1/R1:**
   - genuine proof;
   - local chain only (Anvil/Hardhat);
   - synthetic assets;
   - the repair rejects the attack and the legitimate run passes.
3. **Policy questions.** Each case needs a policy answer from the human (as with Z1/R1) before it can be called a vulnerability.
4. **Payoff.** A reproduced P3 replay/field-alias case would also support "duplicate asset claims" in the abstract.

**Caveat:** these are also small projects. This step fixes the held-out-discovery blocker (#3), not the impact blocker (#1).

### Day 1–4 — Lane P (paper), in parallel

1. Fill the 44 `\MISSING` items from existing results. Do not invent numbers; mark anything unavailable as a limitation.
2. Rerun the 46 synthetic cases on the frozen analyzer (closes `STATUS.md` §(c)).
3. Add a novelty paragraph and table against the SoK, ZKAP, Circomspect, Picus, zkFuzz, CIVER, and ELSA.
4. Present γ = δ as a measurement finding with its root cause, credited to Zeto #186. It is not the headline.
5. Cover the required disclosures:
   - the author-rater;
   - AI use;
   - the P5 limitation;
   - that the new flaws came from DEV (unless Lane R adds held-out ones);
   - the 4/32 benchmark build rate.
6. Table 11 leads with the Z1/R1 effects.

### Day 5–7

1. Write up any reproduced held-out cases.
2. Do a full read and check consistency against the abstract:
   - Either cite an incident for "duplicate asset claims" or drop that phrase.
   - The paper must show that "Guided by this taxonomy" holds, i.e. that P1–P5 map to the taxonomy.
3. Build the anonymized artifact.

**Go/no-go on day 5.** If no held-out case has reproduced and more than ~10 `\MISSING` remain, consider withdrawing and pursuing §5 instead.

---

## 5. Path to a strong paper (beyond 11-17)

### A. Analyzer — DEV only

- **Inputs.** Old 277 plus existing DEV.
- **Fix P5:**
  - exclude proof arrays;
  - model PLONK pairing points;
  - improve circuit selection.
- **Fix P1/P3.** Review the false positives (6/15 each).
- **zk-relational.** Evaluate the branch and merge it if it raises decided coverage. It conflicts only in `bindcheck_zk/cli.py`.
- **Freeze 3.** Declare it in `docs/FREEZE-3.md` with a hash and a tag.

### B. Impact-oriented held-out run (the deciding step)

1. **Preregister a new sample weighted toward used and deployed applications:**
   - audited projects;
   - deployed contracts that have consumers;
   - identity, airdrop, bridge, and privacy-pool applications.
2. **Run one shot under freeze 3.**
3. **Reproduce every VIOLATION at E4**, then disclose it through the advisor.

### C. Evidence quality

- **Benchmark:**
  - raise the public build rate (pin toolchains, cache ptau);
  - replace mock verifiers with real ones;
  - have humans label the synthetic expectations.
- **Recall:**
  - on the buildable benchmark;
  - seeded-mutation recall (inject P1/P3/P5 breaks into repaired apps).
- **Comparison.** Give ZKAP (or another binding-relevant tool) a shared subtask, or state precisely why that is impossible.
- **Raters.** Two non-author raters who do not use AI; seal the labels before analysis.

### D. Paper and venue

- **Lead with cross-layer findings from held-out data.**
- **Choose the venue after B:** S&P, USENIX Security, CCS, or NDSS. Check each CFP's resubmission rules then.

---

## 6. Obligations (apply regardless of submission)

- **Disclosure.** The advisor sends the Z1 (ZKredential) and R1 (RacePass) disclosures. Do not contact maintainers directly; a human sends them. Record the dates.
- **Live systems:**
  - Never transact on live networks or interact with deployed contracts.
  - If a funded vulnerable deployment turns up, **stop and report privately**.
- **Census ledger.** `dataset/onchain-census.csv` stays private.
- **Content limits.** No exploit-construction or forged-proof demonstration content.
- **AI use:**
  - AI output is not independent annotation.
  - Raters must not use AI.
  - Disclose AI use in the paper.

---

## 7. Moving to another machine

1. **Copy the whole `bc/` folder.** Most of it is git-ignored, so `git clone` alone is not enough.

   | Path | Size | Contents |
   |---|---|---|
   | `BindCheck/results/raw/` | 12.9 GB | Evidence; the only copy. Includes the held-out run and the census snapshot, which cannot be regenerated. |
   | `BindCheck/feasibility/work/` | 10.7 GB | DEV corpus checkouts (~6 GB of that is rebuildable `.git`/`node_modules`/`build`). |
   | `BindCheck/dataset/clones`, `dataset/raw`, `tools/` | — | Pinned toolchains: circom 2.1.9, circomspect, picus, noir, cvc5. |

2. **Symlink.** `bc/bindcheck-zk` is a **symlink → `BindCheck`**. Preserve it when copying (`rsync -a` or `cp -a`). About 10 scripts hard-code `/Users/imranpollob/Coding/bc/bindcheck-zk/...`.
   - If the new machine uses a different path or user name, either recreate the same path or replace those paths with repo-relative ones. Find them with:

     ```
     git grep -l "bc/bindcheck-zk/" -- '*.py' '*.sh'
     ```

3. **Toolchains are macOS arm64 builds.** On Linux, rebuild circom/circomspect/picus at the same pinned versions (the `tools/*-src` folders hold the sources).
4. **Python:**
   - The tests ran on Homebrew python3; 3.15 is currently installed and **pytest is missing**.
   - Install pytest, or run `python3 -m unittest discover -s tests -p 'test_bindcheck_zk*.py'`.
   - Set `BINDCHECK_CIRCOM` to the circom 2.1.9 binary.
5. **Not in the folder:** Claude's project memory (`~/.claude/projects/...`). This file and `docs/PROJECT-CLOSEOUT-2026-11-11.md` carry the essential context instead.
6. **Uncommitted.** `BindCheck/abstract.md` is staged but not committed.
