# Reading guide: what the paper needs to get in

Read this next to `paper/eurosp-draft-v2.pdf`. It's the reviewer's checklist, written in plain words: what each part of the paper has to show, what we already have, and what's still missing.

**How to read the PDF**
- **Black** text is measured and real.
- **Red** text is a placeholder for an expected result. Don't trust its numbers yet.
- **Red [ID: ...]** is a task. You'll find it in `TODO.md` under the same ID.

---

## The one-paragraph pitch (what a reviewer should walk away with)

A ZK proof is like a signature on a statement. But the contract then *does* something (pays someone, mints, writes state), and some of the values it acts on were never part of that statement. Anyone who sees the proof can then redirect or repeat the action. We name this bug class, show it's common and severe in real audits, show today's tools can't see it, and build a tool that finds these bugs and backs each warning with an attack test it actually ran.

---

## The 6 things reviewers will check

Each item lists what they ask, what we have, and what's missing.

### 1. "Is this a real, new class, or just input validation?"
- **Have:**
  - the two-ledger definition and P1–P5 taxonomy (§3);
  - the "not input validation" paragraph (§1);
  - the signature analogy, backed by D4: most fixes look like signature-misuse fixes.
- **Have:** positioning against the closest prior work, the Chaliasos et al. SoK. They saw 13 such bugs and we measure 3.8× more. P1 has no category in their taxonomy.
- **Missing:**
  - **T1:** a short formal version of the definition. It's one paragraph and doesn't need a theorem, but reviewers like seeing the property stated precisely.
  - **F1:** Fig. 1 must be a *real* bug, not the current simplified demo.

### 2. "Is the measurement study trustworthy?" (§4)
- **Have:**
  - the funnel table (7,190 → 264 → 103);
  - the pattern × severity table;
  - the real-examples table;
  - the trend (now honest: about 1 in 4 audits, no "rising" claim);
  - the layer split (D3).
- **Missing:**
  - **D1, κ:** an independent human re-labels about 30 items. Without it, reviewers say "AI made your labels." This is a must.
  - **D5:** your 15-item check of the D3 layer tags. The D4 fix tags need a check too.
  - **W3:** the 87 vs 103 headline decision.

### 3. "Do existing tools really miss these?" (baseline tables in §6)
- **Have:**
  - the capability matrix (what each tool can see);
  - B1 detection table: Slither 0 hits, circomspect 0, Picus can't run;
  - B2 mutants table;
  - the fuzzer comparison: with our invariant it finds 5 of 13, without it 0. This is our best argument that the missing piece is the *spec*.
- **Problem:** Mythril. On B3 it couldn't even deploy 24 of 26 targets, so its "0" there means "never analyzed". The B1/B2 Mythril logs can't be checked; they need a verbose rerun (**E13**). Until then, the paper must say "unsupported or unknown", not "found nothing". The post-hoc Mythril pass with proper deployment is running now.
- **Fairness rule reviewers expect:** same snapshots for every tool, best-effort builds, and "couldn't run" kept separate from "missed it". We follow it.

### 4. "Does your tool actually work?" (RQ2)
- **Have:** v2 frozen results:
  - B2 mutants 22/27;
  - audit test set 6/22 strict, 2/8 on the clean round;
  - plain LLM 3/14 for comparison.
- **Missing, and the biggest one:**
  - **v3 (the auditor-style loop):** build it, freeze it, and run it *blind* on B3 (37 new mutants) and round 3. Only blind runs count as clean evidence for v3.
  - **E2:** 3 repeat runs with min/median/max, because LLMs are noisy and n is small.
  - **Plot to add:** per-pattern recall (P1–P5) as a bar chart, with error bars from the repeat runs.

### 5. "Are the warnings real, or is it spamming?" (RQ4, precision)
- **Plan (DEC-1):**
  - Phase 1 scores warnings against the audit labels.
  - Phase 2 is two humans judging every other warning, using the evidence package the tool attaches: the reasoning, the paths tried, and the attack test that ran.
- **Missing:**
  - **E5:** write the phase-2 rules down *before* the v3 freeze, so nobody can say we adjusted them afterwards;
  - **a second human rater**;
  - the κ between the two raters;
  - the precision table (currently all red).
- **Nice plot:** "real-bug rate of warnings with a passing attack test vs claim-only warnings." If it shows a big gap, it proves the loop is worth having, with no extra experiments.

### 6. "Did you find anything new?" (RQ3, the strongest lever)
- **Missing:**
  - **E3, the hunt:** run frozen v3 on recently audited apps, then do phase-2 review and real-proof attack tests on a local chain.
  - **Disclosure** before publication.
- **Why it matters:** even 1–3 confirmed new bugs move the paper from borderline to accept.
- **Needs your call:** hunt scope (live versions or audited commits only) and the disclosure plan.

---

## Other things reviewers always look for

- **Contamination (E6):** "the LLM may have seen these audits in training." Our answers are the B2/B3 mutants (synthetic, never published), the blind round 3, new bugs, and splitting results by report date vs the model's cutoff.
- **Cost (RQ5):** about $1 and 4–6 minutes per scan. The spike showed the v3 loop costs about the same. That's a good selling point, so keep it visible.
- **Threats to validity:**
  - selection bias (public audits only);
  - AI-assisted labels;
  - LLM nondeterminism;
  - our own exposure to test results (it's logged).

  Each threat should come with a sentence on how we mitigated it.
- **Ethics:** local chains only, no live transactions, responsible disclosure. Already written; it just needs the disclosure status at the end.
- **Artifact (W5):** dataset, mutants, tool and prompts released with an anonymous link.

---

## Figures and tables checklist

| # | What | Status |
|---|---|---|
| Fig 1 | Real motivating bug (code + attack) | demo, needs a real dev case (F1) |
| Fig 2 | Two-ledger picture | done |
| Fig 3 | Architecture with the exploration loop | updated for v3; dashed parts not built yet |
| Fig 4 | Controller pseudocode | updated for v3 |
| Tab | Taxonomy P1–P5 + signature analogues | done |
| Tab | Funnel | done |
| Tab | Pattern × severity | done |
| Tab | Real examples | done |
| Tab | Tool capability matrix | done |
| Tab | B1 detection (all tools) | done, Mythril cells need E13 |
| Tab | B2 mutants by pattern | done, Mythril cells need E13 |
| Tab | B3 + round 3 (v3, blind) | **missing**: after the v3 freeze |
| Tab | New flaws found | **missing**: hunt |
| Tab | Two-phase precision (RQ4) | **missing**: red placeholders |
| Plot | Per-pattern recall with error bars | **to add** (after E2 repeats) |
| Plot | Real-bug rate: tested vs claim-only warnings | **to add** (after phase 2) |

---

## Order of work (why this order)

1. **Fixed-code check of the v3 loop** (10 min). Makes sure the attack test doesn't "pass" when there's no bug. If it does, everything downstream is worthless.
2. **Build and freeze v3** (1–2 days, dev only). Everything blind depends on it.
3. **Write the phase-2 + B3 + round-3 protocol before the freeze.** Cheap, and it kills the "you tuned on the test" objection.
4. **Blind runs:** B3, round 3, then the hunt.
5. **Humans:** phase-2 judging, κ on labels (D1), your spot-checks.
6. **Fill the red text**, add the two plots, and do a final reviewer pass.

**What makes or breaks acceptance:**
- v3 works blind;
- at least one new confirmed bug;
- a real second human for κ.

The rest is polish.
