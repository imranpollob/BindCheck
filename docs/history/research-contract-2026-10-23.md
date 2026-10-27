# BindCheck research contract

**Status:** D1 research contract revision 1; INVESTIGATE FURTHER
**Revised:** 23 October 2026; original contract frozen 20 October 2026
**Scope:** Consumer-directed proof-to-effect analysis feasibility study

This document controls prospective D1 work. The [original contract](history/research-contract-2026-10-20.md) remains the interpretation boundary for earlier experiments. Changes follow the dated change-control entry below; no historical experiment or verdict is retroactively relabeled. The [D1 brief](d1/brief.md), [roadmap](d1/roadmap.md), and versioned [reference proposal](d1/reference-proposal.md) explain the implementation plan.

## 1. Paper thesis

A zero-knowledge verifier establishes only the relation encoded by its circuit and verification configuration. A consuming contract may interpret the accepted public values differently, perform effects that were not authorized, or omit effects required by the accepted state transition.

BindCheck D1 investigates whether **consumer-directed extraction and checked summary refinement** can connect facts established by the actual proof relation to protected consumer effects, with a measurable advantage over equally informed monolithic and modular analysis. Start from relevant effects, recover the producer/decoder/consumer obligations, prove summaries from supported constraints, and refine them when an abstract candidate cannot be concretized.

The possible novelty lies in this extraction/refinement mechanism and its demonstrated benefit. Integration failures, rich semantic specifications, modular summaries, and selective unfolding are prior work, notably CIVER, Coda, CCC-Check, and the SNARK SoK cited in the reference proposal. A new ACIR adapter, known-case reproduction, or more solver tuning alone does not establish a contribution.

The initial scope is batched ZK applications with a Noir/ACIR producer and a Solidity/EVM consumer. Broader language support is an evaluation question, not an assumed contribution.

## 2. Research questions

- **RQ1 — Semantic fidelity:** Can supported extraction faithfully connect the compiled producer relation, exact public-input decoding, and consumer effects?
- **RQ2 — Analysis effectiveness:** Does consumer-directed summary selection/refinement improve solved obligations, precision, or total cost over equal-information monolithic and modular baselines?
- **RQ3 — Transfer:** Does the frozen mechanism work on an independently developed application without a new defect-specific rule?
- **RQ4 — Security usefulness:** Which confirmed effects or useful bounded guarantees does it obtain beyond direct contract tests with the same valid proofs and policy, and at what analyst and computational cost?

If the available cases cannot support a prevalence study, RQ1 remains a model-expressiveness question. The paper will not infer ecosystem prevalence from a convenience sample.

## 3. Candidate contributions

These are goals, not completed claims.

1. **Method.** Consumer-directed recovery of joint producer/decoder/consumer obligations, with observation-specific proved summaries and a concrete refinement mechanism that improves on a fair modular adaptation.
2. **Justified implementation.** A precisely supported boundary model, extraction provenance, an abstraction-preservation argument, and explicit unresolved results. Authorization/coverage terminology alone is not a novelty claim.
3. **Comparative evidence.** Historical defects and repairs, legitimate controls, held-out applications, ablations, and total analyst/proving/solver cost compared with equal-information baselines. These results do not yet exist for D1.

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

**Next gate:** D1-01 audits and closes the existing T22-v5 evidence/reporting boundary under its six-query, 300-second/query, 4 GiB protocol, retaining UNKNOWN and explicit missing/blocked outcomes. D1-02 independently inventories non-Payy targets without waiting for solver success. New implementation then proceeds through minimal joint semantics, equal-information baselines, and consumer-directed refinement before a frozen comparison/transfer decision. Do not indefinitely extend T22 or call reduced queries decisions of its original formulas.

The initial ten-researcher-day budget is a feasibility decision budget, not a completion promise. Continue only with meaningful clean/faulty controls, baseline benefit, and independent transfer evidence. If these are not obtained, report the failed gate and decide explicitly whether to narrow or stop. A tie with a routine modular adapter, hand-supplied correspondence, or infeasible independent proving paths undermines the claimed contribution.

### Change log

| Date | Revision and reason | Effect on earlier results |
| --- | --- | --- |
| 2026-10-23 | D1 revision 1, authorized by the user's request to start D1-00. Focus the method and RQs on consumer-directed extraction/refinement; specify the initial fragment, evidence grades, preservation obligations, baselines, and bounded decision gates. Replace an open-ended next encoding repair with T22 reporting closure plus independent intake. | Authorization and coverage definitions, threat-model restrictions, and three verdicts are retained. Original contract bytes are preserved in `docs/history/research-contract-2026-10-20.md`. No old report or result is changed; no rerun is required to preserve its original meaning. Earlier experiments cannot count as validation of the new D1 method; fresh separately versioned evaluation is required for that claim. |
