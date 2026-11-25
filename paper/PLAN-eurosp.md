# EuroS&P paper plan (fresh draft, 2026-11-24, 7-day push)

**Format:** IEEE conference, A4, 13 body pages; references and appendices not counted. A new LaTeX draft goes in `paper/eurosp/` (fresh; nothing reused from earlier drafts).
**Thesis (draft, author to confirm):** A ZK proof works like a signature on a statement, but the consumer acts on an effect. A binding flaw is any effect-deciding value that the attacker controls and that the statement does not fix. These flaws are common, severe and invisible to existing tools. A two-ledger agent finds them and confirms them by execution.
**Tables:** every table gets its final columns now. Missing numbers are written `\TBD{}` and filled from `mvp/eval` once it finishes.

| # | Section | Pages | Content | Data source |
|---|---|---|---|---|
| – | Abstract | – | Hook, definition, RQ1 numbers, BindCheck, headline results | all |
| 1 | Introduction | 1.5 | "A valid proof is not a valid effect"; gap (circuit tools vs contract tools vs the link); contributions; results preview | – |
| 2 | Background and threat model | 1.0 | Circuit / verifier / consumer; attacker = any sender or mempool observer; running example (front-run proof redirects a mint) | – |
| 3 | Binding flaws: definition and taxonomy | 1.5 | Two-ledger definition (statement vs effect); C1–C3; P1–P5 with a signature-misuse analogy and code snippets; scope (proof-system soundness is adjacent) | `audit-sweep/labeling/GUIDE.md`, `labels-v1/DECISIONS.md` |
| 4 | Measurement study (RQ1) | 2.0 | Funnel 7,190→340→300→264; labeling protocol; prevalence, severity, patterns, families, years, auditor severity vs mechanism; finding boxes | `labels-v1/CHARACTERIZATION.md`, `audit-sweep/merged/FUNNEL.md` |
| 5 | BindCheck design | 2.25 | Architecture figure; brain + skill procedure (inventory → effect ledger → statement ledger → pattern checks → adversarial pass → confirm); skills derived on dev only; tool layer (extractor, harness generator, local-chain oracle); evidence ladder E1/E2/E4 | `mvp/tool` (FREEZE-v2, skills/) |
| 6 | Evaluation | 3.25 | Setup: B1 audit test (round 1 + round 2), B2 binding mutants, tools, fairness, scoring. RQ2 detection vs Slither / Mythril / circomspect / Picus / Foundry (out-of-box + assisted). RQ3 new flaws (hunt). RQ4 confirmation rate. RQ5 cost/time | `docs/EVAL-PLAN.md`, `mvp/eval/RESULTS-*`, `fuzz/RESULTS-fuzz.md`, `benchmarks/binding-mutants-v2` |
| 7 | Discussion, threats to validity, limitations | 0.6 | Threats to validity as its own subsection (labels without κ, sampling, LLM nondeterminism); what BindCheck cannot see; advice for developers | – |
| 8 | Related work | 0.6 | ZK circuit bugs and tools, smart-contract analyzers, LLM-based auditors, signature/API misuse | literature search (new) |
| 9 | Conclusion | 0.15 | | |
| – | Ethics and open science | 0.25 | No live interaction; disclosure; artifact | |
| App | Appendices | – | Labeling guide, matching rules, mutant list, per-item results | |

Total ≈ 13.1 pages.

## Changes after EUROSP-STYLE.md (2026-11-25)
- **Fig. 1 is a real case,** not a synthetic one: one audited binding flaw shown as circuit, contract and attack (as CHARON does with a real bug).
- **Intro:** a hook with scale (audit count and severity), a gap with numbers (static tools 0 strict, fuzzers 0 out of the box), then a "this work" paragraph with headline numbers, then 4 contributions as nouns plus numbers, each pointing to its section.
- **§4:** a funnel table plus RQ1 sub-findings grouped by theme, each with a bold one-line takeaway.
- **§6:**
  - report counts in the order raw warnings → confirmed → PoC (E4);
  - give the false-positive rate and its root causes openly;
  - repeated runs (3x) with spread;
  - cost and time per target;
  - keep dev and held-out cases clearly apart;
  - include the plain-LLM arm from round 1, already collected, as the minimal component comparison (no new LLM runs).
- **End matter:** separate *Ethics considerations* and *Open science* paragraphs before the references.
- **Related work** stays late (the tool-paper convention); the closest prior tools are already named in the intro's gap paragraph and in T2.

## Figures and tables
- F1: running example (front-run proof → redirected effect).
- F2: two-ledger picture.
- F3: dataset funnel + pattern × severity.
- F4: BindCheck architecture.
- T1: taxonomy (pattern, signature analog, example, count).
- T2: capability matrix (which layer each tool sees).
- T3: RQ2 detection (`\TBD`).
- T4: new flaws (`\TBD`).
- T5: cost.

## Open author decisions
1. Title.
2. Thesis, and the answer to "this is just missing input validation".
3. Hunt scope (audited commits only vs live apps; disclosure).
4. Exact deadlines (abstract registration, paper).
