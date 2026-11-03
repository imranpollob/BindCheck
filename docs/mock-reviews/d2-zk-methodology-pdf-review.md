# BindCheck D2: PDF-only ZK methodology review

## Review binding and verification scope

- Reviewed artifact: /Users/imranpollob/Coding/bc/bindcheck-d1-paper/output/pdf/bindcheck-d2-evidence-status.pdf
- SHA-256: 1697834e0c47de365ad04f8a1108dfd21555af5c7af9e697759d44e5b9f1e12d
- Page-count check: pdfinfo reports 9 pages. Rendering produced nine numbered page images, and all nine were visually inspected. The PDF page labels run from Page 1 through Page 9; page 9 is intentionally sparse rather than missing content.
- Scope restriction: this review uses only the bound PDF. I did not inspect the repository, source Markdown, internal evidence records, ledgers, reports, code, git history, linked publications, or any prior discussion.

Consequently, every artifact hash, experiment count, proof execution, committed effect, control result, and related-work characterization below is assessed only as a claim made by the PDF. I could check internal consistency and whether the PDF supplies enough methodological detail, but I could not reproduce runs, resolve the internal evidence map, recompute the three hashes reported on page 4, test the prototypes, or verify external sources.

## Bottom line

The most defensible present contribution is not an analyzer that establishes proof-to-execution authorization. It is a bounded methodology and negative status result: the PDF decomposes the security question into producer relation, public-value decoding, consumer transition, identity, and policy; proposes typed interfaces for carrying those facts and their provenance; and applies a conservative rule that unresolved semantic links yield UNKNOWN rather than a vulnerability or safety claim.

That is a useful and unusually explicit research posture. The PDF also correctly prevents several category errors: an accepted proof is not consumer authorization; an E1 diagnostic is not an E4 committed unauthorized effect; a mechanical ESTABLISHED state is not VERIFIED_WITHIN_SCOPE; unsupported cases are not misses; and a zero-row gate is not a tie or a zero error rate.

The current evidence does not establish the prospective contribution stated on page 1: automatic fact recovery, relational mismatch derivation without encoding the expected verdict, and automatic validation to a real proof and committed policy-violating effect. The PDF itself mostly acknowledges this. The key methodological gap is therefore not merely low sample size. The corrected extractor currently derives neither of the two semantic facts needed to make the authorization judgment, and the only planned fair comparison has no eligible row.

## Precise contribution supported by the PDF

1. **Problem formulation.** Pages 1-2 separate the verifier relation R_v, the public-value-to-consumer mapping D_v, the consumer transition T, and policy expressed by permissions, obligations, protected effects, and a reviewed specification. This is a precise statement of where ZK soundness stops and application authorization begins, although the authorization judgment itself is not yet formalized.

2. **Evidence and outcome discipline.** Pages 2 and 5-6 distinguish VIOLATION, VERIFIED_WITHIN_SCOPE, and UNKNOWN from internal prototype states, and separate historical, injected, exposed-development, construction, mechanical-fixture, and independent evidence strata. This is the clearest current methodological contribution.

3. **Prototype schemas.** Pages 3-4 describe three bounded mechanisms: object/context identity bundles and mapping certificates; a common authorization-boundary input; and typed extraction records that preserve quantifier, approximation, support, provenance, assumptions, and exact identities.

4. **A negative correction result.** Pages 3-4 report that an earlier sealed extractor run was semantically unsound, was retained as non-authoritative, and was replaced by a corrected run that produces zero eligible producer guarantees, zero eligible derived consumer-reliance facts, and UNKNOWN in both arms.

5. **A research plan with falsifiable prerequisites.** Pages 7-8 identify a distinguishing experiment and a measurable prerequisite: derive an exact, supported producer guarantee and an exact effect-reliance link, then evaluate them under reviewed policy, equal information, fair comparators, an independent run, and human triage.

The PDF does not support novelty, independent transfer, accuracy, comparative advantage, a formal authorization theorem, general ZK-system coverage, or current end-to-end capability.

## Strongest evidence and what it actually supports

| Evidence reported in the PDF | Strongest supportable reading | What it does not support | PDF-only verification limit |
| --- | --- | --- | --- |
| Corrected typed extractor: zero eligible producer guarantees, zero eligible derived consumer-used facts, identical input/policy/fact hashes for both arms, and both outcomes UNKNOWN (pp. 3-4) | The schema can represent the absence of required facts and is intended to fail closed on the exact fixture | Extraction soundness, semantic completeness, authorization detection, or end-to-end ZK validation | No records, schemas, executable validator, canonicalization rules, or run outputs are embedded in the PDF |
| The earlier sealed run was found to omit operand replay and mapping-certificate replay and to overstate a derived relation; the run was demoted (p. 4) | Strong evidence of correction discipline and of the need to validate semantics rather than trust a seal | Correctness of the replacement protocol; a hash is not a semantic proof | The reported corrected hashes cannot be connected to retrievable bytes from the PDF alone |
| Four identity-preserving transformations and several identity-mismatch controls pass their mechanical checks (p. 3) | Bounded schema and exact-reference invariants behave as intended on authored fixtures | General transformation invariance, compiler correctness, object authenticity, or policy correctness | The PDF supplies no compiler version, IR mapping, fixture contents, certificate format, or check implementation |
| Corrected exposed ablation: full arm 7/7, unjoined union 5/7, with two predeclared typed relationship cases (p. 4) | A relational join is a plausible source of two additional E1 associations on selected known cases | Recall, precision, fair comparative advantage, novelty, or causal attribution to the proposed method | The seven cases, arm implementations, annotations, budgets, and frozen outputs cannot be inspected |
| Historical Payy real-proof chain reaches a committed local effect and has a repair contrast (p. 5) | The broad problem class can matter in at least one already disclosed historical mechanism | Automatic discovery, validation of current warnings, mutant coverage, independent transfer, or prevalence | The PDF does not include the proof, verifier/circuit binding, transaction trace, effect trace, policy record, or repair artifacts |
| Gate A has no eligible row and all score denominators are zero (p. 5) | The INCONCLUSIVE disposition follows from the described protocol state | Any positive or negative performance conclusion | The stop conditions are self-reported, but this conclusion is internally consistent with the PDF |

The strongest positive evidence is therefore about conservative bookkeeping and bounded mechanical behavior. The strongest scientific result is negative: the current pipeline lacks the exact facts required for its own authorization judgment.

## Major methodology concerns

### 1. The authorization relation is named but not formally specified

**Claim at issue.** The central thesis is that some authorization judgments require relating producer constraints, decoded identities, consumer reliance, and policy (pp. 1-2).

**Evidence status.** This is **evidence missing from the PDF**, not evidence that directly contradicts the qualified thesis. The PDF introduces R_v, D_v, T, permissions, obligations, effects, and a specification, but gives no formal authorization predicate, inference rules for MUST/EXACT/DERIVED/SUPPORTED, compatibility relation, discharge semantics, or attacker-success condition. Terms such as exact identity, reliance, derived, and compatible therefore remain partly definitional.

**Why it matters.** Without a semantic judgment, it is impossible to tell whether the prototypes conservatively approximate a stable target property or merely implement a fixture-specific vocabulary. It is also impossible to state soundness or completeness, even for the declared one-transition fragment.

**What would resolve it.** Add a self-contained formal model that defines serialized public inputs, decoded consumer values, protected effects, policy satisfaction, and violation traces. Give explicit inference rules for each fact strength and an authorization judgment. State and justify bounded soundness properties, or clearly label them as hypotheses to be tested.

**Verification limit.** A formal model may exist in code or internal reports, but it is not present in the reviewed PDF and could not be inferred safely from field names.

### 2. The PDF has not demonstrated that joint analysis is necessary or causally beneficial

**Claim at issue.** The paper motivates a cross-boundary method and asks whether it adds a valid diagnosis under equal information and total cost (p. 1).

**Evidence status.** The decisive comparison evidence is **missing**. Gate A has no eligible row, the fair comparator set is incomplete, and the seven-case ablation lacks proof/replay and an external comparison (pp. 4-5). These facts **contradict any present claim of comparative advantage**, but they do not contradict the PDF's explicitly prospective hypothesis.

**Why it matters.** The 7/7 versus 5/7 result could reflect extra relational information, different rules, extra annotations, fixture tailoring, or implementation differences. It does not yet isolate the causal value of the proposed join.

**What would resolve it.** Run the page-7 minimal-pair experiment under a frozen protocol: hold the producer fixed; vary only the protected consumer relation; include state, domain, and identity swaps plus semantics-preserving transforms; give producer-only, consumer-only, union, strongest-simple, full, same-policy, and applicable prior-work arms exactly the same facts and reviewed policy; and account for all annotations, prompts, adaptations, corrections, human time, and compute. Publish per-case outputs and an audit showing which rule or fact differs between arms.

**Verification limit.** The PDF does not expose the ablation cases or arm implementations, so I could not determine whether information and effort were actually equal.

### 3. There is no independent authorization oracle

**Claim at issue.** The benchmark reports detected and supported targets, the ablation reports supported detections, and the historical Payy chain is labeled E4.

**Evidence status.** Independent ground truth is **missing from the PDF**. The 30 targets come from two known lineages; variants, labels, rules, and harnesses were exposed during development; the two ablation differences were preselected; and the mechanical policy is an UNREVIEWED_DEVELOPMENT_FIXTURE (pp. 3-4, 7). This does not contradict the PDF's E1-only characterization. There is, however, an unresolved internal tension: page 2 defines E4 as requiring policy and causal evidence, while page 5 labels Payy E4 without showing the reviewed policy or causal record. The PDF does not establish whether this is a true contradiction or merely omitted evidence.

**Why it matters.** Authorization is a policy judgment. A tool can be perfectly consistent with its annotations and still diagnose the wrong property. Exposed labels also permit benchmark-specific rule design.

**What would resolve it.** Freeze a policy before execution, record a human policy author/adopter and a distinct reviewer, define an adjudication path, and bind the policy to the exact circuit, verifier, consumer, and deployment version. For each evaluated case, publish the protected effect, permitted condition, expected verdict, rationale, and causal validation criteria. Use blinded or held-out cases for the primary evaluation.

**Verification limit.** Because no policy packet or case packet appears in the PDF, neither the E1 labels nor the historical E4 grade can be independently adjudicated here.

### 4. The ZK statement-to-consumer binding is not instantiated at byte level

**Claim at issue.** BindCheck is presented as proof-to-execution binding analysis across a Noir/ACIR-to-Solidity/EVM fragment (pp. 3, 7).

**Evidence status.** Methodological evidence is **missing**, with no direct contradiction of the bounded claim. The PDF does not identify the proof system and version, circuit compilation mode, verification key binding, public-input serialization, field modulus and canonical encoding, calldata layout, endianness, length checks, domain separation, or how the consumer's values are proven to be the exact values accepted by the verifier. Recursion and aggregation are declared unsupported, which is appropriately conservative.

**Why it matters.** Many proof-to-execution failures occur precisely at serialization, ordering, truncation, field conversion, verifier-key selection, or domain boundaries. A source-level role association is not enough to establish this binding.

**What would resolve it.** Specify a byte-level instance model from proof bytes and verifier configuration to the accepted field-element vector, then to ABI-decoded consumer values and the committed effect. Pin circuit, compiler, backend, key, verifier, and consumer hashes. Add negative controls for reordered inputs, non-canonical field encodings, truncation/extension, wrong keys, wrong domains, and semantically equal but byte-distinct encodings.

**Verification limit.** The historical proof and the current extractor are not included, so no accepted statement or decode path could be traced from the PDF.

### 5. “Compiler-backed identity” currently has only bounded fixture evidence

**Claim at issue.** Page 3 describes compiler-backed object/context identity that survives selected transformations.

**Evidence status.** General evidence is **missing**. Four authored transforms and three mismatch patterns test useful invariants, but no compiler/IR semantics or mapping construction is given. The PDF itself says compiler provenance does not establish object authenticity and that the logical slots are unreviewed annotations. That statement **contradicts a strong reading** in which “compiler-backed” means semantically authentic, but not the paper's narrower claim of mechanical exact-reference checks.

**Why it matters.** Stable identity is the bridge between proof inputs and effects. Rename and reorder tests do not cover inlining, optimization, aliasing, phi nodes, duplicated computations, dead-code elimination, ABI lowering, compiler upgrades, or one-to-many source/IR mappings.

**What would resolve it.** Define how identities originate in compiler artifacts and how certificates are checked. Evaluate a transformation matrix across multiple compiler versions and optimization levels, with positive and negative metamorphic tests. Include aliasing, duplication, inlining, reordering, dead-code changes, and ambiguous mappings. Report when identity becomes UNKNOWN rather than forcing a match.

**Verification limit.** The PDF contains neither compiler outputs nor certificates, so “compiler-backed” could not be distinguished from “compiler-labeled.”

### 6. The sealed-run correction shows that integrity binding is not semantic validation

**Claim at issue.** The corrected protocol and run are identified by hashes and a 9/9 content seal (p. 4).

**Evidence status.** The original sealed run provides **contradictory evidence against treating sealing as correctness**: it was sealed yet failed to replay operands and certificates and promoted an annotated relation. The PDF openly reports this, so it is not a hidden inconsistency. Evidence that the corrected implementation fixes the bugs is still **missing from the PDF**.

**Why it matters.** A validator that shares assumptions or code paths with the producer can faithfully hash a semantically invalid record. Opaque hashes establish identity only when the corresponding bytes and canonicalization procedure are available.

**What would resolve it.** Publish a canonical manifest linking every reported hash to retrievable bytes; document serialization; include regression cases that make the old validator accept and the corrected validator reject; separate record generation from validation; and obtain a clean-room or independent replay. The validator should recompute claims from primary artifacts rather than only check internal record consistency.

**Verification limit.** I could not recompute any internal hash or inspect the reported regression tests from the PDF.

### 7. End-to-end causal validation is absent

**Claim at issue.** The prospective contribution includes automatic validation to a real proof and committed policy-violating effect (p. 1).

**Evidence status.** Here the PDF supplies both **missing evidence and affirmative contrary evidence** for any claim that the capability already exists. The authoritative extractor run executes no compiler, proof system, policy scorer, reserved input, or network analysis; it derives zero eligible producer guarantees and zero eligible consumer-reliance facts; and both arms return UNKNOWN (pp. 3-4). The paper correctly disclaims current capability, so the contradiction applies only to a stronger interpretation of the system title or prototype terminology.

**Why it matters.** E1 associations can arise without reachability, exploitability, or causation. A real accepted proof and a state change are still insufficient unless the exact candidate relation is shown to cause the unauthorized effect under the frozen policy.

**What would resolve it.** Demonstrate one full frozen trace: automatic extraction from pinned compiler/verifier/consumer artifacts; candidate generation; malicious witness or input construction; proof generation and acceptance; exact consumer decode; committed protected effect; policy adjudication; and a paired intervention that repairs only the binding and prevents that effect. Preserve unsuccessful candidates and report coverage.

**Verification limit.** The PDF reports a historical Payy reproduction but provides no trace or artifact, and explicitly separates it from current automatic discovery.

### 8. The empirical sample cannot support transfer or accuracy

**Claim at issue.** Counts are reported for 30 mutation targets, seven ablation cases, 13 exposed case appearances, and two earlier scans over eight projects.

**Evidence status.** Independent empirical evidence is **missing**, not contradictory. The PDF accurately states that the cases are exposed, overlapping, authored, unsupported, or non-executed and that no precision, recall, prevalence, or ecosystem-security estimate follows (pp. 4-7).

**Why it matters.** Descriptive fixture counts measure engineering progress, not scientific accuracy. Excluding unsupported cases from “misses” is reasonable for soundness discipline, but it also means capability coverage must be reported separately.

**What would resolve it.** Define the target population and sampling frame; freeze supported-language criteria before selection; evaluate held-out, independently developed systems; report support coverage, abstention reasons, false positives, false negatives, and per-family outcomes; and perform a reserved run with independent triage. Keep unsupported cases out of the accuracy denominator but make their fraction prominent.

**Verification limit.** No case list or raw per-target output is present, so counts and overlap could not be audited.

### 9. Novelty and comparator positioning remain unresolved

**Claim at issue.** The intended advance is a cross-boundary relational analysis, while the related-work section identifies overlap with ZKAP, CIVER, CCC-Check, SmartAxe, and ELSA (pp. 6-7).

**Evidence status.** Evidence for novelty is **missing**, and the PDF includes **evidence against broad novelty formulations**: unused-public-input analysis, rich circuit specifications, producer semantic analysis, and cross-program semantic joining already exist. The PDF correctly declines a novelty claim. ELSA and several runnable comparisons remain unresolved.

**Why it matters.** A contribution cannot be isolated until the comparison is against the strongest applicable method, with adaptation costs and information parity counted.

**What would resolve it.** Replace the internal evidence map with reader-accessible citations, inspect the full closest-work artifacts, define exact overlapping capabilities, and run native or transparently adapted comparators on the same policy and facts. State the narrow delta only after that comparison.

**Verification limit.** I did not follow links or inspect external papers, so I cannot validate either the overlap descriptions or completeness of the related-work set.

### 10. Scope exclusions are correct but currently dominate practical ZK application behavior

**Claim at issue.** The prototype covers a finite, one-transition, one-to-one Noir/ACIR-to-Solidity/EVM fragment.

**Evidence status.** Evidence for broader relevance is **missing**, not contradictory. The PDF explicitly excludes or leaves UNKNOWN dynamic memory, aggregation, splitting, deferral, histories, proxies, delegate calls, assembly, reentrancy, and general external-call behavior (pp. 2-3, 7).

**Why it matters.** These are not peripheral details for many deployed ZK applications. The current fragment may be valuable, but the paper does not quantify how often real applications fit it or how unsupported constructs are detected.

**What would resolve it.** Provide a machine-checkable supported-fragment specification, a coverage report over a defined corpus, and fail-closed tests for every excluded construct. Separate “unsupported but detected” from “unsupported and possibly missed.” Expand scope only with new semantic rules and targeted adversarial controls.

**Verification limit.** With no corpus or parser outputs in the PDF, practical coverage cannot be estimated.

## Unsupported inferences a reader must not draw

The PDF generally warns against these inferences, but they remain the main risks in interpreting the reported numbers:

- 17 detected targets and zero misses do not imply recall; thirteen cases are outside support and all labels were exposed.
- A 7/7 full arm versus 5/7 union does not imply superiority, because the comparison is small, selected, unvalidated to proof/effect, and not shown to have equal total cost.
- Matching hashes do not establish semantic parity, correctness, or equivalent implementation effort.
- Four passing transformations do not establish general semantic equivalence or compiler-backed authenticity.
- A historical E4 reproduction does not validate current E1 warnings or automatic discovery.
- An internal ESTABLISHED state does not establish a policy verdict.
- Both arms returning UNKNOWN is evidence of conservative handling for the fixture, not evidence that either analyzer is sound.
- A passing control or fuzz campaign is property-specific and cannot establish system safety.
- Unsupported cases are not demonstrated misses, but they are still capability gaps and must remain visible in coverage reporting.

## Most consequential limitations, in priority order

1. No independently authored and reviewed policy oracle is bound to evaluated cases.
2. The extractor derives neither the producer authorization guarantee nor the exact consumer effect-reliance fact required by the method.
3. No eligible equal-information, equal-cost comparison exists, and no independent supported family has been evaluated.
4. No current candidate proceeds through an automatic E1-to-E4 causal validation chain.
5. The byte-level proof/public-input/ABI/effect binding is not specified in the PDF.
6. Internal hashes and seals are not independently reproducible from the PDF.
7. The supported fragment and its real-world coverage are not quantified.

## Minimum evidence package that would materially change this review

A decisive next artifact would be a self-contained, preregistered case package containing: a formal authorization judgment; pinned compiler, circuit, proof-system, key, verifier, consumer, and policy artifacts; independently reviewed policy; canonical public-input and ABI mappings; one positive and one paired negative control; frozen full and baseline arms with equal inputs and cost accounting; automatic proof and effect traces; independent replay; and a held-out supported-family result. Raw per-case outcomes, abstentions, and all protocol deviations should be included.

Until such evidence exists, the PDF's strongest credible contribution is its fail-closed methodology, explicit evidence stratification, and honest identification of missing prerequisites. The document is internally strongest when read as a bounded research-status and correction report, not as evidence that BindCheck currently performs validated proof-to-execution authorization analysis.
