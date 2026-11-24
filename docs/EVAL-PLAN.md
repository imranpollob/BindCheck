# BindCheck evaluation plan (EuroS&P), 2026-11-24

Agreed with the author on 2026-11-24. **Must-haves** are what reviewers would reject without. **Nice-to-haves** strengthen the paper but are optional.

## Research questions
- **RQ1 Characterization.** Prevalence, severity, patterns and sources of binding flaws in 264 auditor findings (`dataset/labels-v1/CHARACTERIZATION.md`).
- **RQ2 Detection.** Does BindCheck find known binding flaws that existing tools miss?
- **RQ3 New bugs.** Does it find critical binding flaws that auditors missed (audited commits) or that are still live?
- **RQ4 Confirmation.** What share of warnings reach E4 (real proof, unmodified verifier and consumer, unauthorized effect on a local chain)?
- **RQ5 Cost.** Time, money and unsupported-target rate per tool.

## Benchmarks
| ID | Set | Use |
|---|---|---|
| B1 | Audit test set: round 1 (14 positives / 6 hard negatives / 6 fixed) plus round 2 (16 newly pinned test items after the rater's Pass 2) | RQ2, real bugs |
| B2 | Mutant benchmark: existing 30 WarpToad/Payy mutants, plus injected binding mutants (at least 3 per pattern P1–P5) in hosts outside every dataset family | RQ2, larger n, per-pattern recall |
| B3 | Circuit-bug control (zkbugs / 0xPARC tracker cases) | Shows the tools are complementary; circuit tools should win here |
| B4 | Hunt pool: audited commits of sweep projects not used in development, plus 20–30 recent live ZK apps | RQ3/RQ4 |

## Tools
**Must:**
- Slither;
- Mythril;
- circomspect;
- Picus or ZKAP;
- one fuzzer: Foundry invariant testing (Echidna if it installs), out-of-the-box **and** assisted with the generic binding invariant;
- the same LLM without skills (round-1 numbers, already collected; no further runs);
- BindCheck, run 3 times on B1/B2 with the spread reported.

**Nice:** an open-weight local brain (after the v2 freeze; the author's lab machine), Aderyn, Semgrep rule packs, Halmos, Medusa, zkFuzz, GPTScan. Skill/pass ablations only if reviewers ask.

**Capability matrix** (per tool): which layer it can see (circuit / verifier / consumer / proof-to-effect link), and how many targets it supports.

## Fairness rules (fixed before runs)
- Identical cleaned snapshots for every tool. Build failure = "unsupported", reported separately, never a miss.
- A per-tool matching rule (based on `dataset/labels-v1/SCORING.md`, v1.1 amendments disclosed), committed before that tool runs.
- **Assisted fuzzing:**
  - A mock verifier accepts exactly the honest proof's public-input vector, which stands in for "a valid proof of statement S".
  - The fuzzer varies every other call argument and the sender.
  - The invariant: no accepted call commits an effect whose recipient, amount, state or count differs from what the honest statement entitles. The same invariant is given to every dynamic tool.
- Every warning from every tool is triaged by a human for precision.
- BindCheck v2 is developed on dev only by a fresh lane; B1 round 2 is the clean re-test.

## Order
1. Static and circuit tools on B1 and B2 (no LLM cost).
2. Fuzzer harnesses on B1 and B2.
3. Build the mutant benchmark (B2).
4. BindCheck v2 on dev, then freeze, then B1 round 2 and B2 (3 runs each).
5. Hunt (B4), E4 confirmations, disclosure (the author decides the live-target scope).
6. Optional: open-weight brain on B1 and B2.
