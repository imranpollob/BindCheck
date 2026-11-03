# BindCheck D2 empirical-validity review - PDF only

## Source binding and verification scope

- Reviewed artifact: `bindcheck-d2-evidence-status.pdf`
- SHA-256: `1697834e0c47de365ad04f8a1108dfd21555af5c7af9e697759d44e5b9f1e12d`
- Page-count check: Poppler `pdfinfo` reports 9 pages. I rendered and visually inspected the complete numbered sequence, pages 1 through 9, and also extracted the complete text.
- Scope restriction: this review uses only the PDF bytes identified above. I did not inspect the source manuscript, the internal records listed on page 9, code, ledgers, reports, repositories, run artifacts, citations, or version history.
- Consequent verification limit: I can check the PDF's arithmetic, internal consistency, claim boundaries, and adequacy of the evidence as described. I cannot reproduce a run, verify the PDF's internal protocol/run hashes, validate provenance or preregistration dates, confirm that a proof was accepted or an effect committed, inspect target-level classifications, or verify that the cited internal records support the prose.

## Bottom-line empirical assessment

The precise contribution established by this PDF is an evidence-disciplined status report and a bounded, fail-closed research scaffold. On exposed development fixtures, BindCheck has an E1 diagnostic interface plus mechanical identity, authorization-boundary, and typed-extraction prototypes. The prototypes make provenance, approximation, support, identity, and missing semantic links explicit. They do not establish the proposed end-to-end capability to discover a cross-boundary authorization error and validate it through a real proof and policy-violating committed effect.

The strongest evidence separates into three different claims:

1. **Strongest current comparative signal:** on seven exposed, known ablation targets, the full arm records 7/7 associations and the unjoined union 5/7, a paired difference of two targets. This shows that the implemented join can add an association on those selected fixtures. It does not estimate a general advantage because the cases and labels were exposed during development, the sample is clustered and very small, and there is only one stated matching control.
2. **Strongest evidence that the problem mechanism can matter:** the PDF reports one historical Payy chain with a real proof, committed local effect, and repair contrast. That is evidence for the already disclosed mechanism under pinned historical artifacts, if the underlying record is valid. It was constructed after disclosure, uses a different purpose/version from the current warnings, and therefore does not validate current automated discovery or transfer.
3. **Strongest validity result for the current prototypes:** the corrected extractor produces zero eligible `producer_guarantee` facts and zero eligible derived `consumer_used` facts, gives both arms identical inputs, and returns effective `UNKNOWN`. This is useful negative, fail-closed evidence. It is evidence that this fixture does not silently promote two unsupported semantic links; it is not evidence that supported extraction is sound or that the system can ever establish the intended relation.

The PDF is admirably explicit that the research verdict is `UNKNOWN`. The evidence described does not support accuracy, precision, recall, prevalence, safety, independent transfer, comparative advantage, total-cost advantage, or a current end-to-end capability result.

## Units and denominators

The PDF uses several non-interchangeable units. Keeping them separate is essential.

| Reported material | Correct empirical unit and denominator | What can be computed from the PDF | What cannot be inferred |
|---|---|---|---|
| Current development benchmark | 30 authored mutation targets nested in two known lineages | 17 detected associations, 13 unsupported, and 0 supported misses; raw detection/support coverage is 17/30 = 56.7%, and abstention/unsupported coverage is 13/30 = 43.3% | Recall, precision, prevalence, or performance on 30 independent systems |
| Lineage support | Two lineages, not 30 projects | The PDF says all 12 Payy targets and one WarpToad target are unsupported. If the categories are exhaustive, all 17 supported/detected targets are therefore from WarpToad | Evidence of successful analysis in both lineages or transfer across a lineage boundary |
| Warning output | 26 warning objects, 23 associated warning objects, and 17 detected targets | Three warning objects are not counted as associated; association multiplicity is necessarily present or possible | `23/26` as precision, or one warning per independent target |
| Corrected ablation | Seven known positive targets, plus one separately reported `UNKNOWN` positive and one matching control | Full 7/7, unjoined union 5/7; descriptive paired gain is 2/7, or 28.6 percentage points, on the seven positives | A false-positive rate, uncertainty interval, or population-level effect |
| Identity transformations | One original fixture plus four transformations | Five bundles and four passing mapping certificates | Four independent applications or general transformation invariance |
| Authorization-boundary fixtures | Ten synthetic fixtures | Internal states sum to 1 established + 2 candidate + 7 unknown = 10; all ten effective research outcomes are `UNKNOWN` | Detection accuracy or policy correctness |
| Construction rows | Six arms over 13 overlapping case appearances | 78 repeated arm-by-appearance rows, 72 supported and 6 unknown | A 72/78 success rate over independent cases |
| Independent scans | 12 attempts over eight projects, including four repeats | Zero supported analyses and no rule execution | Eight misses, a measured failure rate, safety, or transfer |
| Gate A | Empty objective subset | Every stated scientific denominator is zero | A tie, zero error rate, negative comparative result, or advantage |

The PDF generally warns readers about these distinctions, but headline fractions such as 7/7 and table entries such as zero misses remain easy to misread without the coverage and clustering accounting above.

## Major empirical-validity concerns

### 1. No end-to-end capability observation exists

**Evidence status.** This is not merely an imprecise estimate. The PDF gives evidence contrary to any stronger inference that the current system has demonstrated its proposed capability: Gate A ran no analyzer, baseline, proof system, fuzzer, matcher, or human scorer; the typed-extraction run executed no compiler, proof system, policy scorer, reserved input, or network analysis; the necessary producer and consumer facts both have count zero; and the components are not integrated into a scored final analyzer. The PDF itself does not make the contradicted positive claim and correctly labels the outcome `UNKNOWN`.

**Why it matters.** Mechanical schema checks and E1 associations are upstream prerequisites. They do not test whether an automatically produced candidate is semantically correct, reachable, exploitable under the declared adversary, or causally responsible for a protected committed effect.

**What would resolve it.** Freeze one integrated version and run an end-to-end chain on actual compiler-derived semantics: extraction, candidate generation, exact warning-to-effect mapping, real proof generation/verification, committed effect observation, reviewed policy adjudication, and a paired repair or negative control. The run should preserve machine-verifiable inputs and outputs at every boundary and should include failure/abstention states in the outcome table.

**PDF-only verification limit.** I cannot determine whether such a chain exists outside the PDF. Within this PDF, it is explicitly absent for the current capability.

### 2. The zero-miss result is conditioned on tool-defined support, with highly non-random missingness

**Evidence status.** The missing evidence is an outcome-independent, immutable definition of support applied before outputs are observed. The PDF says unsupported is `UNKNOWN`, not a miss, which is epistemically appropriate, but it supplies no target-level support decision record in the reviewable artifact. The observed missingness is strongly structured: every Payy mutant is unsupported, whereas the remaining 17 supported/detected targets are, by the PDF's own totals, all from WarpToad. That directly contradicts any interpretation that successful scored analysis spans two lineages, although it does not contradict the literal statement that the benchmark contains two lineages.

**Why it matters.** Reporting zero misses only among cases the tool classifies as supported can yield a tautologically favorable denominator if support is influenced by whether an expected association can be produced. Even with a clean preregistration, 43.3% abstention is a material operational result, not ignorable missing data. Because missingness is concentrated by lineage, complete-case performance would be especially biased.

**What would resolve it.** Publish a target-level table fixed before execution with lineage, mutation, ground-truth basis, support predicate, support reason, expected output, observed output, and version hash. Report at least: support coverage over all intended targets, conditional detection among supported targets, abstention by lineage and cause, and an intent-to-analyze summary that retains `UNKNOWN` rather than dropping it. Validate support classification independently of warning success.

**PDF-only verification limit.** The aggregate sums are internally consistent, but I cannot check the timing, rule, or correctness of any individual support classification.

### 3. The effective scored sample is one development lineage, and all reported observations are clustered

**Evidence status.** Evidence is missing for cross-lineage or independent-family performance. The PDF explicitly describes two known lineages, authored variants, overlapping appearances, repeated attempts, and transformations of a single fixture. The all-Payy unsupported result means the current 17 supported target outcomes do not provide a second lineage cluster. This is contrary to a cross-lineage-performance inference, but consistent with the PDF's stated absence of transfer.

**Why it matters.** Mutants from the same code base share syntax, compiler path, policy structure, role vocabulary, and analysis behavior. Warnings within a target and rows for multiple arms are repeated measures. Transformations of one fixture are paired robustness checks, not new applications. Treating these observations as independent would sharply overstate the effective sample size. With only one scored lineage, no cluster-robust uncertainty or lineage-level generalization is identifiable.

**What would resolve it.** Add multiple independently developed, supported application families; reserve at least one family until rules and labels are frozen; report family-level results; and use a design such as leave-one-family-out evaluation. Treat mutants and transformations as within-family repeated measures and use family, not warnings or arm rows, as the primary generalization unit. A cluster-aware interval becomes meaningful only after there are enough independent families.

**PDF-only verification limit.** I can identify the nesting described in the PDF but cannot measure code or semantic similarity among targets.

### 4. Development exposure prevents an unbiased discovery or generalization estimate

**Evidence status.** The missing evidence is a sealed, genuinely unexposed evaluation. The PDF states that case selection, labels, rules, and validation harnesses were exposed during development; the role cases were known and selected; the Payy mechanism was already public; the variants were authored by the project; and no reserved run exists. Nothing in the PDF contradicts this limitation. It does contradict any inference that the current counts measure independent discovery.

**Why it matters.** "Selected and labeled before this run" is weaker than preregistered before tool and rule development. An implementation can fit expected association identities without learning a transferable authorization relation. A post-disclosure proof reproduction is a useful mechanism check but not a test of vulnerability discovery.

**What would resolve it.** Before examining outcomes, preregister a hash-bound tool, support policy, target frame, outcome definitions, association matcher, repair/control plan, and analysis. Have a custodian release unseen cases only after the freeze. Keep labels blinded during execution and use an independent adjudicator for ambiguous outputs. Preserve exploratory results separately.

**PDF-only verification limit.** The PDF reports hashes for a corrected protocol and run summary, but I cannot verify what they bind or when they were created. A hash establishes byte identity, not prospective timing or independence.

### 5. Associations and warning objects are not accuracy measurements

**Evidence status.** Evidence is missing for a target/effect-level confusion matrix. The current table mixes detected targets, warning objects, and associated warning objects. Twenty-three associated warnings over 17 detected targets implies that warning-to-target mapping is not one-to-one, but the PDF does not give the multiplicity distribution, the three unassociated warnings' meaning, duplicate suppression, or a denominator of safe effects. There is no evidence that contradicts the narrower E1-association claim; the evidence does contradict treating these warnings as verified vulnerabilities.

**Why it matters.** Association with a frozen expected identity is not the same as semantic correctness. Without negatives and adjudicated output units, neither target-level precision nor analyst burden can be computed. A tool that emits several warnings per target may score every known target while producing an impractical or misleading warning stream.

**What would resolve it.** Define the primary prediction unit, preferably a unique protected-effect occurrence under a policy. Publish the complete warning-to-target mapping, including duplicate and unassociated warnings. On both positive and safe controls, report true/false positives, false negatives, abstentions, warnings per case, warnings per effect, and adjudication rules. Follow each positive through the same E1-to-E4 validation route.

**PDF-only verification limit.** I can verify only `26 - 23 = 3` and the mismatch between 23 associated warnings and 17 targets. I cannot determine whether any warning is substantively correct.

### 6. The controls test plumbing more strongly than semantic validity or specificity

**Evidence status.** Evidence is missing for a sufficiently broad negative-control denominator and for real semantic controls. The PDF describes four bounded transformations of one fixture, ten synthetic authorization-boundary fixtures whose effective result is always `UNKNOWN`, targeted extraction regressions, three identity-swap controls, two smoke cases, one matching ablation control, and a historical repair contrast. These results do not contradict mechanical invariant claims. They are insufficient, and in some cases expressly ineligible, to support semantic soundness, specificity, or safety.

**Why it matters.** Passing exact-reference, hash, mapping, and fail-closed checks can detect representation mistakes while leaving the central semantic oracle untested. One matching control cannot estimate a false-warning rate. The Foundry failure occurs under a relational verifier stub and is capped at E1, so it does not close the proof-to-effect chain. A historical repair contrast in a different version cannot serve as a current paired validation.

**What would resolve it.** For each independent family, include matched bug/repair pairs, safe but superficially similar controls, state/domain/identity swaps, reachable and unreachable candidates, and transformations with independently justified semantic equivalence. Run identical current-version extraction, warning, proof, execution, and policy adjudication on every member. Predefine which property each control tests; do not use a control passing one property as global safety evidence.

**PDF-only verification limit.** I cannot inspect whether the stated controls actually isolate one factor or whether transformation semantics are preserved.

### 7. Version changes block trend and causal interpretation

**Evidence status.** The missing evidence is a same-version, same-input comparison across all arms. The PDF explicitly says the three 30-target rows are tool versions, not a trend; the historical and successor ablations must not be merged; and the historical proof chain and current warning set use different versions and purposes. The initial sealed typed-extraction run was later found to have incomplete operand replay, missing mapping-certificate replay, and an overstated derived relation. This is direct evidence against treating a seal or hash as semantic validation, though the PDF appropriately preserves and supersedes the flawed run.

**Why it matters.** The change from 11 detected/19 unsupported to 17 detected/13 unsupported may reflect expanded support, changed rules, changed labels, or implementation fixes. It does not identify an accuracy improvement. Likewise, a historical E4 reproduction cannot validate current E1 warnings when they are not generated and validated by the same fixed pipeline. The correction episode also shows that targeted controls can all pass while an important validator omission remains.

**What would resolve it.** Provide a per-row manifest with code, compiler, configuration, policy, support predicate, target corpus, matcher, and environment hashes. Re-run all arms on one immutable target set under one corrected version and report changes target by target. Revalidate every downstream count after a protocol correction. Add an independent semantic oracle or differential implementation for the validator, not only self-consistency seals.

**PDF-only verification limit.** I cannot verify the corrected implementation or determine which paper counts were regenerated under it. I can only verify that the PDF narrates the correction and warns against cross-version trends.

### 8. The comparative question is unevaluated, not negative

**Evidence status.** Evidence is missing for a fair comparator experiment. Gate A has no eligible equal-information row; the strong/full adapters lacked an equal reviewed policy interface at that time; the applicable external comparator set was incomplete; and no external baseline ran. The 7/7 versus 5/7 internal ablation is evidence of a difference on exposed cases, but not of superiority over a strongest simple baseline or closest prior method. There is no contradictory evidence showing that the proposed advantage is false; there is simply no eligible test, exactly as the PDF says.

**Why it matters.** A union baseline can be artificially weak if it cannot express the same policy facts or mapping information as the relational arm. Conversely, adapters can give a comparator extra or degraded information. Without equal facts, policy, support region, validation route, and engineering opportunity, a detection difference is not attributable to the relational method.

**What would resolve it.** On one fixed corpus, run producer-only, consumer-only, union, strongest-simple, full, same-policy, and all applicable closest-work arms. Give each arm a documented equivalent information budget and measure coverage, accuracy, abstention, warning burden, E1-to-E4 validation yield, and failures. Freeze adaptation rules before results and report native as well as adapted outputs.

**PDF-only verification limit.** I cannot assess actual comparator applicability or verify the related-work characterizations because the cited papers and artifacts are outside the permitted review scope.

### 9. Equal-total-cost is a stated research condition with no measurement

**Evidence status.** Cost evidence is entirely missing. The PDF proposes comparison under equal information and total cost and says future work must count adapters, annotations, prompts, models, setup corrections, and human minutes. It reports several failed or corrected attempts and material AI assistance, but no human time, compute time, token/query volume, hardware, proof-generation cost, adapter engineering effort, triage time, or cost of unsupported cases. There is no contrary cost result; the cost question has not been measured.

**Why it matters.** A method that detects two additional exposed targets could still be dominated if it requires substantial annotation, adapter construction, policy authoring, repeated correction, or warning triage. Excluding failed attempts and setup work would particularly favor a research prototype.

**What would resolve it.** Preregister a cost ledger and record, per arm and case: person-minutes by role, AI model and token/query counts, CPU/GPU time, memory, proof and execution time, adapter and annotation lines or tasks, setup/debugging/recovery time, and triage/validation time. Include failed runs and amortize shared setup transparently. Report both marginal run cost and full research/deployment cost.

**PDF-only verification limit.** The PDF contains no cost measurements from which even a descriptive comparison can be calculated.

### 10. Policy, ground truth, scoring, and review lack independence

**Evidence status.** Evidence is missing for independent semantic ground truth and independent scoring. The PDF states that the policy harness was AI-authored, there is no recorded human policy author/adopter or distinct reviewer, no human scorer ran Gate A, the taxonomy study has no pair of independent ratings, no independent triage occurred, and human authors have not completed inspection of every claim, citation, code path, table, and disclosure. AI agents materially contributed to the tool, protocol, tests, evidence audits, source screening, reports, and draft. This does not itself contradict any mechanical result, but it directly contradicts treating the present labels or audit as independent validation.

**Why it matters.** Authorization is defined against policy. Without an adopted and independently reviewed policy, a target can match an authored expectation while remaining semantically ungrounded. When the same development process creates cases, rules, harnesses, and evidence audits, correlated errors can survive all internal checks.

**What would resolve it.** Obtain a policy from an accountable human adopter, review it independently before execution, blind at least two scorers to arm and expected result, preserve disagreements, measure agreement on a frozen sample, and adjudicate by a third process. Use an independent executor or auditor for the sealed run and an independent application family not authored by the project. AI assistance can remain documented, but should not be counted as an independent role.

**PDF-only verification limit.** I cannot identify contributors, assess their separation, or audit scoring. The conclusion follows only from the independence absences the PDF expressly reports.

## Unsupported inferences to avoid

- `17/30` is not recall. It is the fraction of authored mutation targets both supported and detected on an exposed development benchmark.
- `0` misses is not zero false negatives over the intended domain. It is conditional on 17 supported targets, with 13 targets classified `UNKNOWN`.
- `23/26` associated warning objects is not precision; association is not correctness, warnings are not independent, and there is no safe-effect denominator.
- `7/7` for the full arm is not evidence of general superiority. It is a descriptive result on seven known exposed targets; the paired incremental count is two.
- `72/78` supported construction rows is not a 92.3% case success rate. The rows repeat six arms over 13 overlapping appearances.
- Four passing transformations do not establish arbitrary transformation stability; they are four bounded paired controls derived from one fixture.
- A 9/9 content seal does not establish semantic correctness. The PDF's own superseded sealed run demonstrates that replay omissions and an overstated fact can survive sealing.
- One historical E4 reproduction shows that a known mechanism can produce a local committed effect under pinned artifacts. It does not validate the current E1 warning set or demonstrate independent discovery.
- Twelve unsuccessful attempts over eight projects are not eight misses. No rule ran, so they are compatibility/support failures and evidence of limited practical coverage.
- Effective `UNKNOWN` on all mechanical policy fixtures is not a negative accuracy result. It is an abstaining state caused by absent reviewed policy and derived semantic facts.

## Minimum evidence package needed to change the empirical verdict

The shortest credible path is not a larger count of exposed mutants. It is a small but fully linked, independently grounded experiment:

1. Freeze the corrected integrated analyzer, support predicate, target/effect unit, warning matcher, and all arm adapters before outcome access.
2. Use a reviewed human policy and at least one supported, independently developed reserved family, plus matched bug/repair and safe controls.
3. Report every intended case, including `UNKNOWN`, at target, effect, family, warning, and validation levels; keep family as the generalization unit.
4. Give all internal and external arms equal facts and policy, and run them under one immutable version.
5. Route every candidate through the same real compiler/proof/execution/committed-effect chain, with blinded independent triage.
6. Record total and marginal cost, including adapters, annotation, AI use, failed attempts, correction work, and human validation.

Until such evidence exists, the empirically supportable claim should remain narrow: on bounded exposed fixtures, the project emits E1 diagnostic associations and passes targeted mechanical identity/provenance checks while correctly refusing to promote absent semantic links. The PDF's `UNKNOWN` research verdict is consistent with its reported evidence.
