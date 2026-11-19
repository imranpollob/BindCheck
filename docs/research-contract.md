# BindCheck research contract

**Status:** D1 research contract revision 4; INVESTIGATE FURTHER
**Revised:** 18 November 2026; revision 3 dated 28 October 2026; revision 2 frozen 27 October 2026; revision 1 frozen 23 October 2026; original contract frozen 20 October 2026
**Scope:** Automated discovery and end-to-end validation of proof-to-execution mismatches

This document controls prospective D1 work. [Revision 3](history/research-contract-2026-10-28.md), [revision 2](history/research-contract-2026-10-27.md), [revision 1](history/research-contract-2026-10-23.md), and the [original contract](history/research-contract-2026-10-20.md) remain the interpretation boundaries for experiments run under them. Changes follow the dated change-control entry below; no historical experiment or verdict is retroactively relabeled. The [D1 brief](d1/brief.md), [roadmap](d1/roadmap.md), and versioned [reference proposal](d1/reference-proposal.md) explain the implementation plan.

## 1. Paper thesis

A zero-knowledge verifier establishes only the relation encoded by its circuit and verification configuration. A consuming contract may interpret the accepted public values differently, perform effects that were not authorized, or omit effects required by the accepted state transition.

BindCheck D1 investigates whether a tool can **automatically discover** proof-to-execution mismatches from the actual producer constraints, public-input decoding and consumer effects, and **automatically validate** them end to end. End-to-end validation means a real proof, accepted by the unchanged verifier and consumer from an admitted or reachable state, producing a committed effect that the reviewed policy does not authorize, or omitting a required one.

BindCheck analyzes the circuit–consumer boundary and produces actionable warnings when authenticated proof outputs do not adequately bind the effects the consumer performs.

The possible novelty lies in that discovery-and-validation capability, demonstrated against generic and same-policy baselines. Integration failures, rich semantic specifications, modular summaries, selective unfolding, and the authorization/coverage (`P`/`O`/`E`) terminology and a formal transition model are prior work or framing, **not contributions by themselves** (CIVER, Coda, CCC-Check, the SNARK SoK). The specific advance over prior work must be demonstrated, not asserted. A new ACIR adapter, known-case reproduction, or more solver tuning alone does not establish a contribution.

Whether consumer-directed selection and refinement also give a **measurable efficiency advantage** is a secondary question (RQ5). It was the primary hypothesis of revision 1 and is retained with its results.

The initial scope is batched ZK applications with a Noir/ACIR producer and a Solidity/EVM consumer. Broader language support is an evaluation question, not an assumed contribution.

## 2. Research questions

- **RQ1 — Semantic fidelity:** Can supported extraction faithfully connect the compiled producer relation, exact public-input decoding, and consumer effects?
- **RQ2 — Automated discovery:** Does BindCheck automatically derive the relevant obligations and producer facts from the artifacts, and report candidate mismatches, with manual inputs counted (§6)? "Automatically derived" must be demonstrated by an experiment. The current WarpToad obligations O1 (DOM-AZ) and O2 (SRC-EVM), defined in [`docs/d1-paper/d1p-b02-discriminating.md`](d1-paper/d1p-b02-discriminating.md) §§1–2, are planner-written and do not count as derived.
- **RQ3 — Automated validation:** Does BindCheck take its candidates to an end-to-end validated mismatch (E4, §8) without hand-performed steps, or with those steps counted and disclosed?
- **RQ4 — Comparative capability and transfer:** Which E1–E4 results does BindCheck obtain that generic/default and same-policy baselines do not, at what analyst and computational cost, on development cases and on an independently developed held-out family, without a new defect-specific rule?
- **RQ5 — Efficiency:** Does consumer-directed summary selection and refinement improve solved obligations, precision or total cost over equal-information monolithic, goal-cone and modular baselines? This is a secondary, currently untested question under revision 2.

If the available cases cannot support a prevalence study, RQ1 remains a model-expressiveness question. The paper will not infer ecosystem prevalence from a convenience sample.

## 3. Candidate contributions

These are goals, not completed claims.

1. **Taxonomy.** A taxonomy of proof-to-execution binding failures, grounded in the boundary model and evaluated across supported cases.
2. **Actionable diagnostics.** Actionable cross-layer diagnostics that localize an inadequately bound proof output, explain the affected consumer effect, and suggest a repair.
3. **Capability.** Automated discovery of proof-to-execution mismatch candidates and automated end-to-end validation to E4, with the specific advance over prior work demonstrated.
4. **Justified implementation.** A precisely supported boundary model, extraction provenance, an abstraction-preservation argument, and explicit unresolved results. Authorization and coverage terminology alone is not a novelty claim.
5. **Comparative evidence.** Generic/default and same-policy baselines, development and held-out cases, ablations, and total analyst/proving/solver cost. These results do not yet exist.
6. **Efficiency.** A measured advantage, if one is found. Revision 1's null and negative results are reported regardless.

## 4. System model

For verification configuration `v`:

- `R_v(p, w)` is the actual constraint relation for public statement `p` and witness `w`.
- `T(s, d, tau, s')` is a successful supported consumer execution from state `s` to `s'`, using calldata `d` and committed trace `tau`.
- `sigma` is the reviewed protocol specification.
- `P` is the multiset of proof-backed or otherwise explicitly permitted authorizations.
- `O` is the multiset of required obligations created by the accepted transition.
- `E` is the multiset of committed protected effects.
- `q` records pending obligations when the protocol explicitly permits deferral.

Records may contain a kind, identity, asset, quantity, beneficiary, domain, state version, activation condition, and permitted discharge rule. Commitments may replace private values when their binding and encoding assumptions are explicit.

D1 also represents the actual decoding relation `D_v(p,x)` and an explicit bounded reachable-history relation `Reach_L(h,s)`. A joint counterexample requires a legal history, a satisfying producer witness, actual decoding, successful consumer execution, and a policy violation together. A fixed admitted pre-state is a narrower mode and must be labeled as such; it does not quantify over all reachable states. Pin program/key identity as well as source, constraints, ABI, and consumer configuration.

### 4.1 Authorization

Every committed protected effect must be justified by a compatible permission under `sigma`. Matching must preserve the required identity, asset, beneficiary, domain, and quantity. A permission cannot be reused beyond its multiplicity or quantity.

Authorization does not require every permission to be exercised.

### 4.2 Coverage

Every required obligation must be discharged by a compatible committed effect, validly cancelled, or transformed into a protocol-permitted pending obligation. Matching preserves identity, quantity, backing, and single-use requirements.

Coverage is a safety property. BindCheck does not initially prove that a pending action will eventually execute.

### 4.3 Conservation

Conservation is not a third top-level property. Identity, amount, asset, recipient, and multiplicity preservation are matching conditions used by both authorization and coverage. Aggregation, splitting, padding, and deferral are accepted only through explicit transformation rules.

## 5. Threat model

### 5.1 Adversary capabilities

The adversary may:

- choose witnesses, public inputs, proof bytes, calldata, and transaction ordering;
- deviate from the honest witness generator;
- invoke public entry points and roles allowed by the evaluated deployment model;
- reuse available proofs or values unless the protocol prevents it; and
- select any reachable supported pre-state.

Case-specific capabilities must be recorded. For example, a Payy experiment may require a registered prover rather than an arbitrary external caller.

### 5.2 Trusted assumptions

The bounded guarantee may rely on:

- cryptographic soundness of the proof system for the pinned relation and verification key;
- correct correspondence among the analyzed source, compiled constraints, verification key, and consumer configuration;
- stated cryptographic binding or collision-resistance assumptions;
- correctness of the reviewed semantic policy in `sigma`;
- soundness of BindCheck's producer and consumer summaries for the explicitly supported subsets; and
- the declared asset and external-call model, initially standard atomic ERC-20 behavior where applicable.

These assumptions must appear in each result. Unverified assumptions cannot silently become mechanically established facts.

### 5.3 In scope

- unconstrained or insufficiently constrained public values whose interpretation can affect execution;
- public-input ordering, width, range, activation, prefix, padding, and field-mapping disagreements;
- unauthorized, duplicated, misdirected, or incorrectly quantified protected effects;
- required effects omitted from an accepted transition;
- supported aggregation, splitting, and pending-obligation transformations; and
- state updates, deposit consumption, claims, and transfers included in the declared protected-effect model.

An underconstrained circuit is in scope when its actual accepted relation permits a proof-to-execution violation.

### 5.4 Initially out of scope

- breaking the cryptographic verifier or proof-system soundness;
- toxic-waste compromise or trusted-setup failures;
- consensus, sequencer, compiler, or hardware compromise;
- privacy leakage unrelated to execution consistency;
- unconditional liveness or censorship freedom;
- arbitrary malicious, rebasing, or fee-on-transfer token behavior;
- unsupported proxies, inline assembly, delegate calls, reentrancy, or unbounded external-call behavior; and
- interaction with live deployments or real user assets.

Unsupported behavior produces `UNKNOWN`; it is not evidence of safety.

The separately reported Payy verifier failure is outside this initial scope. The `agg_agg` message-tail defect is inside scope because it concerns the relation established by the circuit and the consumer's interpretation of accepted public values.

### 5.5 D1 initial implementation fragment

Begin with a bounded arithmetic/array producer and one supported non-reentrant Solidity/EVM settlement path, standard atomic token behavior where modeled, and a replayable initialization. Before new experiments, freeze numeric bounds, admitted states/history length, compiler/solver versions, supported operations, and resources in that task's protocol. Existing N=8 T22 controls keep their original bounds and limits.

Initially implement occurrence-level discharge with identity, asset, amount, beneficiary, and domain. Splitting, aggregation, and deferral are permitted policy concepts, not implemented capabilities; until modeled and controlled, their occurrence yields UNKNOWN. Keep field, integer, and byte semantics distinct; establish range/canonicality obligations before replacing one with another. Unsupported recursive relations and hashes remain explicit assumptions or UNKNOWN, never silently trusted producer facts.

## 6. Non-circular specification boundary

BindCheck separates **implementation facts** from **protocol policy**.

### 6.1 Facts the tool should establish

Where supported, the tool should recover:

- public-input schema, ordering, sizes, ranges, and visibility;
- constraints and dependencies involving relevant public values;
- verifier arguments and their mapping to consumer values;
- decoding, guards, loop bounds, storage accesses, and committed protected effects; and
- provenance connecting every reported fact to an artifact location.

### 6.2 Information the analyst may supply

The analyst may specify:

- semantic roles such as amount, recipient, asset, identity, or state root;
- which operations are protected effects, permissions, or required obligations;
- protocol-authorized transformations such as aggregation or safe deferral; and
- environmental assumptions and admitted initial states.

### 6.3 Information the specification must not supply

The primary automated analysis must not assume:

- that a public value is constrained merely because it should be;
- that a consumer effect is correctly bound to a proof field;
- the expected vulnerable or safe verdict;
- the exact missing implementation relation being tested; or
- a manually asserted implementation fact that erases the candidate defect.

Necessary manual implementation summaries must be marked `ASSUMED`, measured separately, and excluded from claims of automatic recovery.

Specifications for held-out cases must be versioned and frozen before BindCheck's verdict is inspected. Subsequent corrections are reported as post-hoc refinements.

Mark recovered facts `EXTRACTED`, discharged relations `PROVED`, and external/manual implementation facts `ASSUMED`. Each summary must have a checked producer implication and explicit preconditions discharged at its use site. Cache identities include artifact hashes, policy, bounds, and assumptions. Any assumed implementation summary is excluded from automatic-recovery claims and disclosed in the guarantee.

## 7. Bounded formal target

The intended theorem is over BindCheck's abstract transition model, not unrestricted EVM semantics:

> If the proof verifier is sound for `R_v`, artifact provenance is correct, producer and consumer summaries are sound for their supported subsets, and `sigma` correctly states protocol policy, then satisfaction of authorization and coverage for every admitted successful transition implies preservation of the declared proof-to-execution invariant.

The proof must identify separate assumptions for:

1. the core authorization/coverage model;
2. producer extraction from the supported circuit representation; and
3. consumer extraction from the supported Solidity/EVM representation.

No theorem may claim coverage of unsupported instructions, external behavior, unbounded executions, or liveness. Bounded solver success is reported with its bounds and assumptions.

The proposed D1 preservation obligation is that every supported concrete execution has an abstract representative preserving the relevant observations, and refinement preserves that inclusion. Only then can abstract UNSAT support the bounded concrete claim. Extraction fidelity and cryptographic/compiler assumptions remain separate obligations. Fixing omitted witnesses or surrounding state can underapproximate the relation and is useful only for explicitly restricted search unless equivalence is established. No preservation theorem has been proved in D1-00.

## 8. Required result categories

Every analysis returns one of:

- **VIOLATION:** a model satisfying the supported assumptions violates authorization or coverage;
- **VERIFIED_WITHIN_SCOPE:** no violation exists within the declared model, bounds, and assumptions; or
- **UNKNOWN:** extraction, modeling, provenance, solver, or validation is insufficient.

A candidate violation is not an end-to-end exploit claim until its proof feasibility and reachable committed effects are validated. Real-proof validation is required for the central motivating result and a declared subset of evaluation cases. Repairs must also preserve legitimate behavior.

Keep the three verdicts above and attach a separate evidence grade, bounds, assumptions, provenance, non-vacuity result, and reason codes. `SPECIFICATION_UNRESOLVED` is an UNKNOWN reason, not another verdict. An abstract SAT candidate is unresolved until checked against the supported concrete relation. A concrete model violation is distinct from a real-proof, original-consumer, reachable-effect replay. A clean legacy trace is only an observation. `VERIFIED_WITHIN_SCOPE` additionally requires non-vacuity and justified abstraction/extraction; timeout, allocation failure, probe UNSAT, or an unsupported feature never establishes it.

**Evidence ladder.** Attach one level to every candidate. **E0** no report. **E1** tool warning. **E2** a model satisfying the actual compiled producer relation, decoder and consumer model. **E3** a real proof of that assignment accepted by the pinned, unchanged verifier. **E4** that proof accepted by the unchanged consumer from an admitted or reachable state, producing an unauthorized committed effect or an undischarged required obligation, checked on state.

Only E4 is an **end-to-end validated mismatch**. Relevant E1 and E2 results earn detection credit at their level. The same validation process, budget and adjudication apply to BindCheck's and every baseline's candidates. For a mutant or historical variant, "unchanged" means the frozen variant under test with its own matching key and verifier.

The three verdicts (`VIOLATION`, `VERIFIED_WITHIN_SCOPE`, `UNKNOWN`) and all existing rules in §8 are unchanged. E2 corresponds to the existing "concrete model violation". E4 corresponds to the existing "real-proof, original-consumer, reachable-effect replay".

## 9. Evaluation commitments

- Payy and authored fixtures are development cases, not held-out evidence.
- Historical cases require pinned artifacts, primary provenance, independent semantic validation, and an evidence grade.
- Negative controls require property-specific justification; an audit label is insufficient.
- Mutations must derive from observed mechanisms, compile, remain reachable, and change the target property.
- Held-out inclusion and exclusion rules are frozen before analysis; every attempted build and exclusion is reported.
- Baselines receive equivalent specifications, assumptions, bounds, and summaries in the equal-information comparison.
- Report exact counts for confirmed findings, unresolved warnings, labeled defects, negatives, unsupported cases, and build failures.
- Measure specification size, authoring and correction time, runtime, memory, applicability, localization, and false alarms.
- Never count `UNKNOWN` as safe or as a semantic false negative when a baseline does not support the input.
- New findings require responsible disclosure before they support a submission claim.
- Run **both** a generic/default arm and a same-policy arm for every applicable baseline. Record *not applicable* with a reason where a tool has no property interface.
- Generic fuzzer invariants run on a target only with protocol justification from that target's source or documentation.
- Non-target reports are adjudicated separately and are never automatically false alarms.
- An honest fixture without a known defect is not a proven negative control.
- Development cases can show capability on those cases. They cannot show transfer, unbiased discovery or generality; those require a held-out family frozen before analysis.
- Baseline budgets are development caps never below BindCheck's per-case budget. Setup and proving are declared separately.

The preregistered details are in [`paper/baselines.md`](../paper/baselines.md).

D1 compares direct Foundry property tests with the same valid-proof seeds, a monolithic joint query, and a CIVER-style modular adaptation on the same extracted relation. Identify an adaptation honestly; do not claim to reproduce CIVER unless reproduced. Charge specification, extraction, adapter, proving, solver, and adjudication effort. Compare shared bug-finding tasks separately from verification guarantees. An unsupported native frontend is not an algorithmic baseline failure.

Inventory independent targets early, before D1 tuning. Availability screening is not an honest build or transfer result. Freeze mechanism and policy procedure before held-out analysis, disclose prior exposure, and retire a holdout if its results drive new rules. Payy variants stay development data.

## 10. AI-assisted research integrity

AI agents may help implement code, search candidate sources, prepare tests, and edit prose. They do not constitute independent human annotators. All generated claims, citations, labels, code, and experimental results must be inspected by the authors. Preserve task prompts, reports, commands, versions, and raw evidence needed for the conference's generative-AI disclosure.

## 11. Change control and immediate gate

Changes to this contract require a dated entry recording the reason, affected claims, and whether prior experiments must be rerun. After the held-out protocol is frozen, semantic rules may not be changed and then evaluated on the same cases as if they remained held out.

Open decisions are deliberately not frozen yet:

- the independent historical-case set;
- whether a second circuit frontend is feasible;
- the exact generic-verification baseline;
- whether pending deferral enters the initial implementation; and
- final solver bounds and supported EVM subset.

**Next gate:** The capability gate passes only with (a) automated discovery of a mismatch candidate from artifacts with manual inputs counted, (b) automated validation to E4 on at least one development case, (c) a comparison under both baseline arms, and (d) transfer to a frozen held-out family without a new defect-specific rule. If these are not obtained within the decision budget, report the failed gate and decide explicitly whether to narrow or stop. A tie with a routine baseline, hand-supplied correspondence or hand-performed validation undermines the claimed contribution.

The initial ten-researcher-day budget is a feasibility decision budget, not a completion promise.

### Revision 4 — Analyzer scope for held-out v3, 18 November 2026

**Semantic exclusions.** Apply the frozen path rules case-insensitively. The excluded directory components are `test`, `tests`, `mocks`, `fixtures`, `test-fixtures`, `script`, `scripts`, `ctf`, `writeup`, `writeups`, `tutorial`, `tutorials`, `example`, and `examples`. Also exclude directory components ending in `ctf` and filenames ending in `.t.sol` or `.s.sol`. These classes are outside application scope. Excluded Solidity sources contribute no application triples, findings or warnings and never receive `VIOLATION` or `VERIFIED_WITHIN_SCOPE`. Record the paths and count of excluded sources encountered by the semantic filter in `coverage.semantic_excluded_paths` and `coverage.semantic_excluded_count`. This count covers parsed Solidity sources after file discovery, which has its own directory exclusions and resource limits. If exclusion leaves no applicable triple, the triple-based patterns return `UNKNOWN / NO_APPLICABLE_TRIPLE`. [Frozen configuration](../bindcheck_zk/config.json) and [S2a, §R1.6](../reports/S2a/REPORT.md#r16-semantic-exclusion-moved-into-config)

**P1-EXTENT (direction b, binding beyond discharge).** This consumer-side check compares the fixed calldata rows covered by a commitment in a checked verifier input with the prefix processed by a zero-based settlement loop over the same rows. An independent caller-controlled bound that permits a shorter prefix with an unchecked omitted effect yields `VIOLATION` at E1. `VERIFIED_WITHIN_SCOPE` for extent requires a bound equal to the committed length or a complete tail check excluding every recognized effect on every skipped row. The result assumes that the verifier authenticates the recovered vector and that the hash binds the rows. Establishing producer feasibility and the policy obligation for an omitted row requires separate evidence under §§6–8. The rule was designed on the AZ1 development fixture. [S2c](../reports/S2c/REPORT.md)

Return `UNKNOWN` when the entry point, statements, call or public vector cannot be recovered, the full-region commitment cannot be associated with that vector, or assembly obscures the verifier input. Unsupported control flow, loop scope, effects or bound provenance also yield `UNKNOWN`, as do unresolved independence of the bound, tail control or feasibility, and inability to establish a feasible shorter prefix. If no extent consumer is found, record `EXTENT_CONSUMER_NOT_FOUND`. The verified-source V3 case remains `UNKNOWN / EXTENT_ASSEMBLY_VERIFIER_INPUT_UNSUPPORTED`. [S2c results](../reports/S2c/REPORT.md#results-tables-exact-counts)

**Verifier correspondence.** A `VERIFIED_WITHIN_SCOPE` claim relying on a verifier implementation requires exact source correspondence between that implementation and the call receiver. A conflicting receiver type yields `UNKNOWN / VERIFIER_CALL_CORRESPONDENCE_UNRESOLVED` for P1 and consumer-triple P4. Crediting an inherited P4 guard requires a directly imported single base, an unambiguous wrapper forwarding the same fixed vector unchanged, and checks at base-method entry covering every word. Unresolved override or dispatch yields `UNKNOWN / INHERITED_VERIFIER_GUARD_UNRESOLVED`. Source correspondence alone cannot establish deployed bytecode identity. [F1](../reports/F1/REPORT.md) and [XR2, XR-03/04](../reports/XR2/REVERIFY.md)

**Circuit interface completeness.** P5 may return `VERIFIED_WITHIN_SCOPE` only with a known public count and a complete flattened public order, including for a length-guarded dynamic consumer vector. Even then a length-only result establishes only the declared length property. An unresolved user-defined Noir composite leaves the interface incomplete and the order check `UNKNOWN / CIRCUIT_INTERFACE_INCOMPLETE`. An independently established verifier/consumer count mismatch can still yield its own `VIOLATION`. [F1](../reports/F1/REPORT.md) and [XR2, XR-05](../reports/XR2/REVERIFY.md)

**Honk/UltraHonk layout.** Recover the external caller's public arity from the supported generated layout, including `NUMBER_OF_PUBLIC_INPUTS` in an exactly imported key file. Deduct the pairing-point and aggregation words explicitly reserved by the recognized external length check. A word count establishes arity only. The Honk canonicality rule (S2b) is deferred and excluded from freeze 3. [S2a](../reports/S2a/REPORT.md)

**Held-out v3.** Reserve the remaining 1,106 of dataset v2's 1,384 EVAL-only families for a single run with the analyzer identified in the freeze-3 declaration. The 278 freeze-2 families are spent development data. Freeze the family manifest, policy procedure, exclusions and reporting denominators before inspecting results. Record every attempted family, including unsupported inputs and failures. No tuning on held-out results is permitted. A family whose result informs a subsequent change is exposed and must leave the headline measurement. [S0 mandate](orchestration/S0-contract-rev4-freeze3.md) and [freeze 3](FREEZE-3.md)

**E4 confirmation.** The execution oracle is a separate tool outside the analyzer hash. An analyzer warning or passing regression suite cannot establish E4. Before any oracle confirmation counts for held-out v3 or contributes an E4 number to the paper, the F3 oracle repairs must pass the oracle's own XR3 re-review. Each eligible case must still meet §8 and its reviewed policy. [XR2](../reports/XR2/REVERIFY.md) and [reviewer decision of 18 November](orchestration/DECISIONS.md)

### Change log

| Date | Revision and reason | Effect on earlier results |
| --- | --- | --- |
| 2026-10-23 | D1 revision 1, authorized by the user's request to start D1-00. Focus the method and RQs on consumer-directed extraction/refinement; specify the initial fragment, evidence grades, preservation obligations, baselines, and bounded decision gates. Replace an open-ended next encoding repair with T22 reporting closure plus independent intake. | Authorization and coverage definitions, threat-model restrictions, and three verdicts are retained. Original contract bytes are preserved in `docs/history/research-contract-2026-10-20.md`. No old report or result is changed; no rerun is required to preserve its original meaning. Earlier experiments cannot count as validation of the new D1 method; fresh separately versioned evaluation is required for that claim. |
| 2026-10-27 | Revision 2, authorized by the planner decision recorded in D1P-D03. Move the target contribution from a measurable efficiency advantage to capability: automated discovery and end-to-end validation of proof-to-execution mismatches. Demote the old RQ2 to secondary RQ5. Add the E0–E4 evidence ladder, two-arm baselines and development-case scope rules. | No result is relabeled. D1P-07, D1P-09, D1P-10, D1-01/T22 and the historical synthetic-branch results keep their original meaning as evidence on the revision-1 efficiency hypothesis (now RQ5). No rerun is required. These results cannot be cited as capability evidence. Revision-1 bytes are archived under `docs/history/research-contract-2026-10-23.md` before editing. |
| 2026-10-28 | Revision 3, authorized by D1P-31. Add a taxonomy of proof-to-execution binding failures and actionable cross-layer diagnostics to the candidate contributions, and state the core BindCheck boundary-analysis claim prospectively. | No earlier result is relabeled or rerun. Revision-2 bytes are preserved byte-identically in `docs/history/research-contract-2026-10-27.md`; earlier experiments retain the contract and interpretation under which they were run. |
| 2026-11-18 | Revision 4, authorized by the author (sprint decision of 18 November 2026; see `docs/orchestration/DECISIONS.md`), drafted by lane S0. Define the freeze-3 analyzer scope, evidence boundaries and one-shot v3 population prospectively. | Revision 3 is archived byte-for-byte. Earlier experiments retain their original contract, verdicts and grades without rerun. The 56-row F1 results are development evidence. Future v3 claims require the freeze-3 hash and the separate oracle gate above. |
