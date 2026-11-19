# BindCheck: research roadmap toward a strong security paper

Date: 2026-11-13. Planning status: complete; research verdict: **INVESTIGATE FURTHER**.

The author has removed the November submission deadline as a project target. The goal is a substantive, independently evaluated security contribution, followed by venue selection. This roadmap controls the new work sequence; it does not retroactively change experimental protocols, evidence grades, or the research contract. Its proposed scope must be reconciled with the canonical contract in R00 before new semantic experiments begin. No acceptance outcome is guaranteed.

## 1. Intended contribution and research questions

Working thesis: **effect-directed analysis can determine whether an application's committed actions are authorized by the actual circuit relation and consumer checks, with less manual specification or better capability than strong existing alternatives.** This is a hypothesis, not an established novelty claim.

The first paper should target one coherent mechanism across multiple independently developed applications. Candidate mechanisms are conditional enforcement versus consumer reliance, representation disagreement, and proof scope versus replay scope. Do not commit to implementing all three. Choose from evidence in R01. Direct recipient checks are useful controls, but do not alone establish the intended semantic advance.

- RQ1: Which realistic authorization failures require facts from both the circuit and consumer, and what is missing from existing methods?
- RQ2: Can a bounded analysis recover and check those facts without being given the defect or expected verdict?
- RQ3: Does the method improve validated detection, false-alarm avoidance, or analyst cost over an equally informed baseline?
- RQ4: Does the capability transfer to independent applications without defect-specific changes?
- RQ5: Can another researcher reproduce the central findings and understand the supported guarantee?

The core property is conditional on proof-system soundness, correct artifact correspondence, admitted state, and reviewed policy. A successful protected effect must be permitted by the proof-established facts and relevant application state. This is not a requirement that every proof determine one unique effect: relayers, optional actions, and authorized choices can be legitimate. Coverage of required effects is a separate extension; initially prioritize authorization. Verifier-key weaknesses remain a separate dimension, not evidence for this core hypothesis.

## 2. Evidence and reuse boundaries

The starting checkout was clean at `5e22657` on `main`. This is a planning observation, not a replay validation.

| Existing asset | Intended use | Required boundary |
| --- | --- | --- |
| Freeze-2 analyzer and prior runs | Reproduction reference and baseline | Preserve existing hashes, tags, raw results, and interpretation |
| Previously analyzed 277-family sample | Exposed development material for future improvements | Retain its historical held-out designation for the original run; never call reuse a new held-out test |
| Historical and Z1/R1 local findings | Mechanism examples, harness reuse, regression controls | Audit exact policies, keys, proof provenance, and repair scope before reuse |
| `zk-relational` branch | Candidate extraction components | Its report states no natural DEV applicability for four central dimensions; do not merge on synthetic success alone |
| Pinned benchmark and evaluation scripts | Infrastructure | Human-reviewed labels, buildability, correspondence, and current-version reproducibility must be established |
| D1/Noir work | Historical evidence and possible reusable techniques | Do not pool results with a different language, analyzer, or evaluation population |

The current contract names Noir/ACIR, while the recent paper targets Circom/Solidity. R00 resolves that prospectively and archives the old contract exactly. Existing README and checkpoint entries retain historical inconsistencies; they are not evidence that old EVAL data is still unseen.

No blanket rewrite or automatic branch merge is planned. Preserve the old analyzer as an executable comparator. Reuse a component only after its provenance and semantic limits are reviewed.

## 3. Ordered work packages and decision gates

Effort ranges below are planning estimates for focused research work, not deadlines. Human review, artifact recovery, and disclosure may take longer. Complete one bounded task and its evidence report before moving to dependent work.

### R00 — Align the research contract and evidence inventory [NEXT]

Estimated effort: 2–3 working days.

Tasks:

1. Archive and prospectively revise the contract around the selected research questions, evidence rules, and initial Circom/Groth16–Solidity feasibility scope. This language choice is provisional until R01 establishes suitable natural applications.
2. Write a claim–evidence matrix: every desired paper claim, falsifying observation, required experiment, and current evidence status.
3. Inventory retained raw evidence, exact versions, portability blockers, and dataset exposure. Hash named central bundles; do not rehash or rebuild the entire archive without need.
4. Reconcile the current entry-point documentation without rewriting immutable reports. Record which historical results remain reproducible, present but unchecked, or missing.

Deliverables: revised/archived contract; `reports/R00.md`; claim matrix; exposure ledger; component-reuse ledger.

Exit gate: no ambiguity about the prospective claim, evidence interpretation, exposed data, or next experiment. All desired results remain explicitly unproven.

### R01 — Establish the research gap and natural feasibility [WAITING]

Depends on R00. Estimated effort: 5–10 working days, then a written decision.

Tasks:

1. Audit closest prior work using primary texts and available artifacts: integration SoKs, circuit analyzers, specification-based verification, and cross-component/relational checking. Record exact supported inputs, property, assumptions, analyst effort, and unavailable evidence.
2. Inspect a small, deliberately selected DEV pool of approximately 6–10 independent application families. Selection should reflect application use, meaningful security policy, artifact availability, and relevant mechanisms. Record rejected candidates and reasons. This is feasibility sampling, not prevalence measurement.
3. Select one central mechanism supported by real code. Prepare paired cards explaining the property, consumer reliance, producer enforcement, source/key correspondence, policy source, attacker model, and secure alternative.
4. Build the simplest competent contract/verifier-only comparator and an equal-information composition of available circuit facts with that comparator. Include specification-based testing where applicable. Give all arms the same policy; measure extra implementation summaries and manual assistance.
5. Construct a minimal semantic prototype and validate a discriminating example. Use genuine proof/effect validation for the central vulnerable path; label authored mutations separately from natural defects.

Internal continuation threshold (not a conference acceptance quota): at least two independent natural application families exercise the selected relationship; at least one supported vulnerable path and one legitimate indirect-binding control have independently reviewed expectations; the full analysis adds a reproducible semantic distinction or measured cost benefit beyond the comparator. An authored defect can demonstrate feasibility but cannot support a new natural-vulnerability claim.

Stop/reframe if applications do not exercise the mechanism, the baseline explains the apparent advantage, or results depend on names, a supplied missing constraint, or a missing-input gate. Do not spend months generalizing an unsupported hypothesis. A recorded artifact-access failure is inconclusive, not a scientific negative.

Deliverables: `reports/R01.md`; collision matrix; pinned pilot manifests; policy cards; comparator/prototype results; explicit pursue, narrow, or drop decision.

### R02 — Formalize the selected property and implement a vertical slice [WAITING]

Depends on R01 continuation. Estimated effort: 2–3 weeks.

Tasks:

- Define concrete producer, decoder, consumer, and policy semantics, including successful committed state transitions and bounded histories when replay matters.
- Define the policy interface: protected effects, semantic roles, permitted transformations, and environmental assumptions. Annotations may express intent; they may not assert that implementation binding holds.
- Implement one end-to-end slice: pinned triple → checked correspondence → recovered facts → obligation → decision → explanation → local validation.
- Prefer compiler/constraint-backed extraction and explicit declaration identities. Establish coefficient, range, and encoding semantics needed for the property; graph connectivity and wire incidence alone are insufficient.
- State and justify the bounded guarantee. Prove the relevant abstract implication and explain extraction/abstraction obligations. An abstract counterexample remains a candidate until concrete feasibility is established; an absence result requires justified overapproximation and non-vacuity.

Exit gate: the supported fragment and assumptions are written; every decisive fact has provenance; secure and vulnerable pilot variants separate correctly; a human reviewer can follow the guarantee; unresolved algebra and ambiguous correspondence remain UNKNOWN.

### R03 — Establish development reliability and the benchmark [WAITING]

Depends on R02. Estimated effort: 3–5 weeks. Benchmark curation can start during R02 once policy definitions are stable.

Tasks:

- Generalize the selected mechanism across the pilot's independent implementations before adding another mechanism or language.
- Assemble separate historical vulnerable/repaired pairs, natural secure controls, realistic reviewed mutations, and exposed development findings. Keep their results separate.
- Audit proof/key/circuit correspondence and feasible consumer execution for central benchmark cases. Build success alone is insufficient.
- Add semantic stress tests: renaming, helper extraction, equivalent expressions, invalid ranges, contradictory guards, wrong artifact pairings, and legitimate relaying/commitment patterns.
- Strengthen competing baselines using DEV failures. A baseline must not be weakened merely to create a performance gap.
- Isolate each repair's effect; do not silently enforce unresolved gifting or reuse policies. Check legitimate behavior and non-vacuity after repair.

Exit gate: every scored case has reviewed policy and expected behavior; false certifications found during development are resolved or the affected feature is explicitly unsupported; failures are reported; the intended contribution survives the strong comparison and semantics-preserving transformations.

Deliverables: versioned benchmark, label provenance, build/replay manifests, baseline package, cost ledger, and `reports/R03.md`.

### R04 — Freeze an independent evaluation protocol [WAITING]

Depends on R03. Estimated effort: 1–2 weeks plus reviewer availability.

Tasks:

- Recruit a human policy/label reviewer and, preferably, a separate dataset custodian. Disclose author roles; AI opinions are not independent labels.
- Reserve fresh families with family-level separation from all development work. A custodian can perform build-only checks under a predefined protocol without revealing semantic outcomes to method developers.
- Freeze scope, inclusion/exclusion rules, sample selection, budgets, analyzer/baseline versions, policies, metrics, and adjudication before the evaluation.
- Select sample size from the target inference, family diversity, expected warning yield, desired interval precision, and validation budget. Do not choose a large round number for appearance.
- Define two populations separately: a labeled benchmark for recall and paired discrimination; a fresh application sample for transfer, warning precision, coverage, and discovery. New-source sampling alone cannot measure recall.
- Predeclare fault handling and rerun rules. Infrastructure retries retain original attempts; semantic rule changes create a new experiment version and end the affected cases' unseen status.

Exit gate: signed/versioned protocol with a complete analysis plan, reserved data, working independent baselines, and a clean-environment rehearsal using DEV only.

### R05 — Run the frozen study and validate findings [WAITING]

Depends on R04. Estimated effort: 3–5 weeks plus external response time.

Tasks:

- Execute all frozen arms with recorded commands, versions, hashes, resource costs, exits, and exceptions.
- Measure precision, recall on labeled cases, paired vulnerable/repaired discrimination, applicable coverage, unresolved outcomes, total effort, and localization. Report uncertainty with family clustering accounted for.
- Report both conditional performance on supported cases and end-to-end yield on the sampled population. Unavailable tools and unsupported inputs receive neither wins nor safety credit.
- Use mechanism ablations that retain input presence and extraction infrastructure while replacing specific semantic reasoning with weaker facts. Separate metadata-only, syntax-only, and full-relation arms where relevant.
- Validate all findings used as central vulnerability claims with genuine proofs, original consumer behavior, admitted/reachable state, and committed effects. Apply the same validation budgets to baseline candidates. If validating only a subset of other warnings, predeclare sampling and account for every unvalidated warning.
- Validate scoped repairs and legitimate controls. Record policy uncertainty separately from execution success. Prepare disclosure material for the human author/advisor; no automatic maintainer contact.

Exit gate: the claimed advantage transfers without defect-specific tuning; central findings are concretely supported; reported denominators and costs reconcile; independent adjudication is complete. Null or adverse results remain publishable evidence but require reconsidering the paper claim, not silently changing the evaluation.

### R06 — Write, reproduce, and adversarially review the paper [WAITING]

Depends on R05 for empirical conclusions. Estimated effort: 2–3 weeks; maintain the methods draft and evidence-linked tables throughout earlier stages.

- Write the paper around the narrowest contribution supported by the results. Lead with a security consequence and the technical obstacle resolved.
- Generate every quantitative table from versioned evidence. Separate natural discoveries, historical reproductions, and authored cases.
- Have someone other than the implementer reproduce the central result and attempt to falsify the extraction assumptions, guarantee, comparison, and policy interpretation.
- Package portable, pinned artifacts with a small smoke path and full reproduction path, expected outputs, resource requirements, and documented failures.
- Complete limitations, ethics, disclosure status, AI-use reporting, and open-science documentation. Check the chosen venue's current requirements at submission time.

Exit gate: no central claim lacks evidence; no result requires undisclosed hand repair; the independent reproduction succeeds; the strongest reviewer objections have direct answers. Select a venue only then.

## 4. Proposed implementation boundaries

Use these logical modules; choose final filesystem paths after the reuse audit rather than rebuilding by default:

1. Artifact resolver: exact source/compiler/key identity and checked producer-to-consumer correspondence.
2. Consumer frontend: effects, guards, decoding, state/replay operations, and rollback semantics.
3. Producer frontend: relevant compiled constraints and justified summaries.
4. Policy interface: independently supplied intent with source and human-review provenance.
5. Obligation engine: shared typed facts, conditional relations, bounded decision procedure, and explanations.
6. Validation runner: honest/attack/repaired execution, genuine proof acceptance, state assertions, and provenance.
7. Evaluation runner: isolated versions, exposure tracking, equal-budget arms, metrics, and generated tables.

Every finding records artifact hashes, policy version, assumptions, extracted/proved/assumed facts, verdict, evidence grade, limits, validation status, and analyst interventions. Check mapping identity before interpreting semantic mismatches. Preserve the three research verdicts and distinguish E1 warnings from E4 effects.

## 5. Immediate execution checklist

The next implementation turn should execute **R00 only**:

- [ ] Preserve current index/worktree state and archive the controlling contract byte-for-byte.
- [ ] Create a prospective contract revision and claim–evidence matrix for the new thesis.
- [ ] Create the exposure/reuse ledger, including the original held-out run and `zk-relational` limitations.
- [ ] Identify pilot-selection criteria and a candidate DEV shortlist without opening reserved fresh evaluation material.
- [ ] Write `reports/R00.md`, reconcile entry points, and update the checkpoint.

The first human research input is review of the proposed authorization policies and selection of an independent reviewer/custodian. Routine inventory, provenance checks, and pilot preparation can proceed before that review; unresolved policy cannot support a vulnerability claim.

## 6. Reviewer objections and required answers

| Likely objection | Required answer | Gate |
| --- | --- | --- |
| Integration bugs are already known | Precise surviving technical gap against primary sources | R01 |
| A simple contract check suffices | Strong comparator plus causally meaningful ablation | R01, R05 |
| The oracle supplies the answer | Independent policy and measured manual inputs | R02, R04 |
| Wrong circuit/verifier pairing creates findings | Checked correspondence and adversarial mapping controls | R02, R03 |
| Synthetic templates are doing all the work | Natural applicability and fresh-family transfer | R01, R05 |
| Real proofs cannot trigger the alleged effect | Genuine-proof local state evidence | R02, R05 |
| The repair simply forbids legitimate behavior | Minimal repair and policy-backed legitimate controls | R03, R05 |
| Results cherry-pick supported cases | Full acquisition/build/support/decision/validation funnel | R04, R05 |
| The guarantee exceeds the model | Explicit assumptions, preservation argument, non-vacuity | R02, R06 |
| The artifact cannot be reproduced | Independent reproduction and pinned portable pipeline | R06 |

These are internal evidence gates, not numeric acceptance rules. A few deep, independent cases can be more informative than a large noisy corpus; neither case count nor a high precision figure substitutes for a substantive contribution.

## 7. Opportunity log and stop conditions

- Primary opportunity: semantic authorization checking, if R01 establishes a useful relational mechanism in natural systems.
- Alternative: an executable integration benchmark, if reliable cases and a genuinely new comparative insight support a separate paper.
- Separate opportunity: setup/configuration measurement, only if consumer use and exposure can be established. Do not use it to inflate semantic-analysis findings.
- Stop or narrow the primary thesis if the apparent advantage vanishes against a fair baseline, annotations encode the defect, natural applicability remains absent, or unsupported features encompass the intended target population.

## 8. Sources and review boundary

- [SNARK security SoK, USENIX Security 2024](https://www.usenix.org/system/files/usenixsecurity24-chaliasos.pdf): integration failures and combined circuit/application testing are prior motivation.
- [ZKAP](https://www.cs.utexas.edu/~isil/zkap.pdf): circuit dependence analysis and vulnerability patterns are prior techniques to compare with.
- [USENIX Security 2027 CFP](https://www.usenix.org/conference/usenixsecurity27/call-for-papers), checked 2026-11-13: originality, relevance, scientific rigor, correctness, and clarity; open-science requirements. No venue deadline drives this roadmap.
- Local evidence: [research contract](research-contract.md), [held-out report](../reports/heldout/REPORT.md), [benchmark report](../reports/bench/REPORT.md), [policy answers](../findings/POLICY-ANSWERS-2026-11-10.md), and `git show zk-relational:reports/relational/REPORT.md`.

Papers needed from the author: none to start R00. R01 must track full-text access gaps rather than assume abstract-only reading establishes a novelty comparison. This plan is not a completed literature audit or new experimental result.
