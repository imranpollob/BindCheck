# BindCheck D2: Evidence-Led Status of Proof-to-Execution Binding Analysis

> **Status — 2 November 2026:** Research verdict `UNKNOWN`. Gate A
> `INCONCLUSIVE`. **Not submission-ready.** This is a concise status
> manuscript, not a final-results paper, formatted submission, security
> verdict, or claim of novelty. The preserved historical manuscript remains
> `paper/draft.md` and is not superseded as an evidence record.

## Abstract

A zero-knowledge verifier establishes a circuit relation, while a consuming
program decodes accepted public values and commits effects. For some effects,
deciding whether the proof authorizes execution requires relating producer
constraints, decoded identities, consumer reliance, and reviewed policy.
BindCheck investigates whether those relations can be recovered from artifacts
and validated end to end.

The current evidence does not establish that capability. On an exposed
two-lineage, 30-mutant development benchmark, the integrated analyzer records
17 detected targets, 13 unsupported cases, 26 warning objects, and 23
associated warnings; all are E1 diagnostics. A corrected exposed ablation
records 7/7 supported detections for the full arm and 5/7 for its unjoined
union, with one additional `UNKNOWN` positive and one matching control. These
known cases motivate a relational comparison but do not establish novelty.

Gate A stopped before scoring because policy, review, information-parity, and
comparator prerequisites were absent. No analyzer, baseline, proof system,
fuzzer, or human scorer ran in that gate; every scored denominator is zero.
The result is `INCONCLUSIVE`, not a tie, failure rate, or safety result.

Subsequent bounded prototypes define compiler-backed object/context identity,
a common authorization-boundary interface, and typed extraction records.
Their mechanical controls pass under an `UNREVIEWED_DEVELOPMENT_FIXTURE`, but
the corrected extractor emits no derived producer guarantee and no eligible
derived consumer-reliance fact. Both comparison arms therefore remain
effectively `UNKNOWN`. Historical and injected real-proof evidence is retained
separately from current capability. There is no supported independent transfer,
fair comparative advantage, or final capability result. The research verdict
is `UNKNOWN`, and this manuscript is not submission-ready.

## 1. Problem and research posture

Zero-knowledge applications distribute one security decision across a
producer relation and a consumer transition. Let `R_v(p,w)` be the relation
accepted by a verifier configuration `v`, where `p` is public and `w` is a
witness. Let `D_v(p,x)` describe the actual mapping from accepted public values
to consumer values, and let `T(s,d,tau,s')` describe a successful consumer
execution and committed trace. Cryptographic soundness says that an accepted
proof corresponds to a statement in `R_v`; it does not by itself say that the
consumer interpreted the statement as the protocol intended.

The research contract represents policy through permissions `P`, obligations
`O`, committed protected effects `E`, and an independently reviewed
specification `sigma`. Authorization asks whether each committed protected
effect is justified by a compatible permission. Compatibility can depend on
object identity, asset, amount, beneficiary, domain, state version, activation
condition, multiplicity, and discharge rule. Occurrence, a shared variable
name, or an accepted proof is not sufficient by itself.

This yields a qualified thesis. **Some** authorization judgments require
relating producer and consumer facts. It does not follow that every defect is
invisible to a one-sided analyzer. Compiler lint and circuit analyzers can find
unused or insufficiently constrained values. Contract analyzers and
same-policy harnesses can find consumer defects. The empirical question is
whether a cross-boundary method adds a valid, transformation-stable diagnosis
or higher evidence grade under equal information and total cost.

The intended contribution remains prospective: automatically recover the
relevant implementation facts, derive a relational mismatch without encoding
the expected verdict, and automatically validate that candidate to a real
proof and committed policy-violating effect. The current record does not
establish that contribution. This manuscript is organized around what the
evidence supports, what it leaves unresolved, and which result would be needed
to change the disposition.

## 2. Threat model, outcomes, and evidence discipline

### 2.1 Adversary and trusted boundary

Within a supported application, the attacker may choose witnesses, public
inputs, proof bytes, calldata, and permitted transaction ordering; deviate
from an honest witness generator; and invoke accessible consumer entry points.
The analysis may rely on the soundness of the pinned proof system, correct
artifact/key/configuration provenance, sound supported extraction, a reviewed
policy, and the declared asset and external-call model. An unverified
assumption cannot silently become a derived fact.

Unsupported instructions, recursive relations, dynamic memory behavior,
ambiguous mapping, effect identity, or policy produce `UNKNOWN`. The project
does not initially claim unrestricted EVM semantics, live-system security,
arbitrary token behavior, compiler correctness, liveness, or cryptographic
soundness beyond the pinned assumptions.

### 2.2 Research outcomes versus mechanical states

The controlling research outcomes are:

- `VIOLATION`: a supported model and validation chain establishes a policy
  violation within declared bounds;
- `VERIFIED_WITHIN_SCOPE`: no violation exists within a declared supported
  model, bounds, and assumptions; and
- `UNKNOWN`: extraction, policy, modeling, provenance, solving, or validation
  is insufficient.

The later prototype uses internal states named `ESTABLISHED`,
`MISMATCH_CANDIDATE`, and `UNKNOWN`. Those are mechanical interface states,
not research verdicts. Under an unreviewed policy fixture their effective
result is always `UNKNOWN`. Similarly, a warning is E1 evidence, an accepted
real proof is E3, and an unauthorized committed effect with the required
policy and causal evidence is E4. No lower level is promoted by wording.

### 2.3 Evidence strata

The following strata remain separate throughout this paper.

| Stratum | Current material | What it may support | What it cannot support |
|---|---|---|---|
| Historical known case | Publicly disclosed Payy message-tail mechanism and later local proof/effect/repair reproduction | The mechanism exists and can produce a committed local effect under pinned historical artifacts | Independent discovery, current-warning validation, transfer, or prevalence |
| Injected development | Authored WarpToad variants and mutation benchmark | Controlled mechanism and validation studies on known targets | A defect in the pinned project, unbiased discovery, or independent accuracy |
| Current exposed development | Integrated analyzer and corrected ablation | Bounded E1 associations and support behavior on known cases | Novelty, precision/recall, security, or generality |
| Construction and smoke | Internal arms, transformations, comparator inventory, two Foundry smoke cases | Runnable plumbing, native-output preservation, and explicit applicability | Detection scores, safe controls, or comparative advantage |
| Mechanical fixture | Identity, authorization-boundary, and typed-extraction prototypes | Schema invariants, exact-reference checks, parity, and fail-closed behavior | Policy correctness, semantic soundness, E2–E4, or a paper claim |
| Independent/reserved | Prior unsupported attempts only; no authorized D2 result | Compatibility barriers | Transfer, misses, safety, or an independent family outcome |

Mock-versus-real proof and warning-versus-committed-effect grades are
orthogonal to these strata. A historical E4 does not transform a current E1
warning into E4. A matching control is property-specific and never global
safety evidence.

## 3. Current D2 system boundary

### 3.1 Integrated development interface

The current integrated development interface combines corrected static and
conditional-extent analysis with a typed role-correspondence analysis. It
records component support states, provenance, stable warning identities, and
validation-facing routing. It can associate producer occurrence, extent, or
source-derived role facts with modeled consumer guards, state identities, and
effects on bounded exposed inputs.

These are E1 diagnostics. A role correspondence says that two modeled values
are associated in a supported source-derived representation. It does not prove
that the relation is the protocol's authorization relation, that the consumer
effect is the exact committed AST occurrence, or that an attack is reachable.
Warnings should therefore be read as candidate mismatches or diagnostic
associations, not unauthorized effects.

### 3.2 Compiler-backed identity prototype

The identity prototype separates semantic object and context identities from
display names and source locations. An opaque reference contains a schema,
semantic hash, and canonical-bytes hash. Object and context fields determine
the security identity; compiler, source, line, display, and derivation
observations remain separately hashed provenance. Mapping certificates bind
exact source and destination references.

On one original exposed fixture and four bounded transformations, the
prototype creates five bundles and four mapping certificates. Identifier
rename, helper extraction, equality-operand commutation, and matched
public-input reorder controls pass their preregistered mechanical checks. The
reorder is intentionally not order-preserving and succeeds only through an
explicit bijection. Same display name with a different object, the same object
in a different context, and crossed object/context pairs mismatch as expected.

This is mechanical evidence only. The transformations are bounded controls,
not general equivalence proofs. Compiler provenance does not establish object
authenticity or policy correctness. The logical slots themselves are
unreviewed fixture annotations.

### 3.3 Authorization-boundary prototype

The authorization-boundary interface gives the full and strong-simple arms
the same canonical `BoundaryInput`, policy, fact set, identity bundle, and
hashes. It models a finite, one-transition, one-to-one fragment with explicit
action, asset, quantity, beneficiary, domain, state version, authorization
identity, effect identity, activation, and discharge fields. Unsupported
splitting, aggregation, deferral, unbounded history, conditions, assumptions,
or mappings remain `UNKNOWN`.

Only a `MUST`, `EXACT`, `DERIVED`, `SUPPORTED` producer fact with provenance
can discharge a MUST obligation. The exact identity chain requires the
producer fact to connect the authorization identity to one public-value
identity and consumer reliance to connect the protected-effect identity to
that same value. Same-name/different-object, same-object/different-context,
swapped-effect, and broken-value links fail closed.

The ten synthetic fixtures include an adjustable `p = private_x`
counterexample, a matched `p = authorized_x` control, an exact context
mismatch, and seven insufficient-fact/condition controls. The internal count
is one `ESTABLISHED`, two `MISMATCH_CANDIDATE`, and seven `UNKNOWN`, but all ten
effective results are `UNKNOWN`: the policy is an
`UNREVIEWED_DEVELOPMENT_FIXTURE`, no score exists, and no concrete application
claim follows.

### 3.4 Typed extraction trust prototype

The corrected typed extractor inventories sixteen implementation-fact
families and records quantifier, condition, approximation, derivation,
support, reason, provenance, assumptions, annotations, mapping references,
and exact subject/object identities. Its validator replays source and record
hashes, parent/provenance references, serialized mapping certificates,
predicate and term shapes, unmapped indices, `UNKNOWN` rows, summary counters,
and completion status.

The most important result is negative and fail-closed. Proof-enforced
occurrence within the current bounded extractor does not prove cryptographic
injectivity, protocol intent, or a relational authorization guarantee.
Similarly, structural consumer use does not prove that a caller-supplied
protected-effect identity denotes the exact AST effect occurrence. The
corrected authoritative run therefore records:

| Fact class in the exact fixture | Count and strength | Consequence |
|---|---|---|
| Eligible `producer_guarantee` | 0 | No MUST authorization obligation can be discharged |
| Eligible derived `consumer_used` | 0 | No exact protected-effect reliance relation is established |
| `producer_binding_candidate` | 1, `MAY`/over-approximation/`ANNOTATED` | Candidate only |
| `consumer_reliance_candidate` | 1, `MAY`/over-approximation/`ANNOTATED` | Candidate only |
| Conditional extent | 1 exact derived fact in the supported fixture | Extent only; not authorization |

Both arms receive identical input, policy, and fact hashes and return
`UNKNOWN`. The run also passes five permanent extraction regressions, seven
condition/approximation/mapping controls, and three adversarial identity-swap
controls. It executes no compiler, proof system, policy scorer, reserved input,
or network analysis.

An initially sealed run was later found to validate predicate operators
without fully replaying operands, to omit serialized mapping-certificate
replay, and to overstate a caller-linked effect relation as derived. That
first run remains preserved but non-authoritative. The corrected protocol is
SHA-256
`910ce6464a947fa552be08d34a596d97b179669401305adc577676d5172ce3ec`;
the authoritative run summary is
`0ebf8ca1f555701a6cbc942b0140df1440e7e5e60eb4daec87fd4bffb1dc42ab`;
and its 9/9 verified content seal is
`c5bb3163283c7b16a0d341067c6f2c3f8fa9965d85ab13dc761d4e948fcf21e6`.

These components are not integrated into a scored final analyzer. Their value
at this stage is to make unsupported semantic leaps explicit.

## 4. Evidence ledger

### 4.1 Current development benchmark

The 30 mutation targets come from two known application lineages. They are not
30 projects, independent systems, or a population sample. The tool changed
across the three recorded rows, so the rows are versions rather than a trend.

| Version | Detected | Unsupported | Misses | Warning objects | Associated warning objects |
|---|---:|---:|---:|---:|---:|
| Historical v1.1 | 16 | 14 | 0 | 53 | not recorded on the current association schema |
| Corrected static-only successor | 11 | 19 | 0 | 13 | not applicable |
| Current integrated development interface | 17 | 13 | 0 | 26 | 23 |

All current results are E1. The six additional detections relative to the
corrected static-only row are predeclared typed role targets. The 13
unsupported targets are one WarpToad mutant plus all 12 Payy mutants.
`Unsupported` remains `UNKNOWN`; it is not a miss. The zero-miss field means
only that no predeclared target classified as supported lacked its frozen
association on this exposed benchmark. It is not an estimate of recall,
precision, or ecosystem security.

### 4.2 Separate ablation versions

The preliminary and successor ablations must not be merged.

| Experiment | Producer | Consumer | Unjoined union | Full | Other rows | Interpretation |
|---|---:|---:|---:|---:|---|---|
| Historical preliminary | 3/8 | 3/8 | 6/8 | 6/8 | one clean control | Earlier analyzer assumptions; history only |
| Corrected successor | 3/7 | 2/7 | 5/7 | 7/7 | one `UNKNOWN` positive and one matching control | Exposed E1 motivation for a relational comparison |

The two successor differences are known typed state/role relationship cases.
They were selected and labeled before this run, use source-derived role atoms,
and were not accompanied by a fair external comparison or proof/replay. The
result motivates a prospective experiment; it does not establish novelty.

### 4.3 Payy evidence layers

Payy supplies three different observations.

First, the exact earlier/check-added artifact pair has an artifact-specific
recursive mapping certificate. The earlier revision emits an E1 conditional
extent warning and a separate consumer diagnostic. The check-added revision
emits no extent warning and retains the consumer diagnostic. Silence for the
exact repaired property is not global safety.

Second, all 12 Payy mutation-benchmark targets remain unsupported because the
exact certificates do not transfer to changed bytes and the required consumer
relation is absent. They are not misses.

Third, a historical real-proof chain reproduces the publicly disclosed earlier
tail mechanism, obtains a committed local effect, and records a repair
contrast. That is E4 evidence for the known historical mechanism. It was
constructed after disclosure and independently of the current warning set. It
does not establish automated discovery, validate the 12 mutants, or transfer
to another family.

### 4.4 Construction and smoke

Six internal arms were constructed over 13 exposed case appearances: 78
construction rows, of which 72 were supported and six were `UNKNOWN`. The 13
appearances are overlapping case sources, not independent systems. Four narrow
transformations passed build, mapping, execution-vector, consumer-algebra, and
warning-identity controls; two application-level transformations were rejected
before mutation. An early alias-control failure and its recovery remain
preserved.

The external inventory records native/default and possible same-policy status
for compiler checks, contract analyzers, fuzzers, circuit tools, cross-program
analysis, and ELSA. A fresh two-case Foundry smoke preserved native output: the
pinned case completed its seven named invariants, and an injected missing-root-
admission case emitted one native failure under a relational verifier stub.
The first smoke attempt failed on a Boolean environment spelling and is
preserved; the recovery changes only that setup spelling.

These are construction facts. The policy harness was AI-authored and has no
recorded human author/adopter or independent human review. Its stub caps the
failure at E1. A passing fuzz campaign is not safety evidence, and the smoke
rows are not target scores.

### 4.5 Gate A

Gate A produced no scientific score. It stopped on four global prerequisites:

1. no human policy author/adopter was supplied;
2. no distinct human policy reviewer was supplied;
3. the then-current strong/full adapters did not consume an equal reviewed
   P/O/E policy interface; and
4. the fair same-policy and applicable-comparator arm set was incomplete.

No analyzer, baseline, proof system, fuzzer, warning matcher, or human scorer
ran in the gate. The objective subset was empty and every target, diagnosis,
safe-control, validation, transformation, and comparator score denominator was
zero. The later common interface prototypes address plumbing but do not
retroactively rescore Gate A or supply the missing human roles and semantic
facts.

The exact result is `INCONCLUSIVE`. It neither supports nor contradicts the
proposed comparative advantage because no eligible equal-information row
exists. Zero rows do not mean zero misses or false warnings.

### 4.6 Independent evidence and taxonomy

Two earlier frozen scans comprise 12 attempts over eight projects, including
four repeat attempts, and completed zero supported analyses. No rule ran and
no independent family result was adjudicated. The records identify compiler,
opcode, memory, and consumer-boundary barriers. They do not establish misses,
safety, transfer, or generality.

Subsequent public dependency audits are non-execution records, not experiments.
They record that Steps 11–14 were not executed and Gate B was not evaluated;
Steps 15–17 were not executed and Gate C was not reached. No frozen evaluated
release, custodian release, reserved run, immutable primary output, independent
triage, or exploratory campaign exists. These absences block later claims but
are not failed runs or negative security results.

The taxonomy track has a frozen codebook, blank packets/forms, and tested
agreement tooling. Its D2 human study has not started: there is no final frame,
draw, packet set, pair of independent human ratings, adjudication, or agreement
result. A historical single-human-versus-AI comparison is not inter-human
agreement. Taxonomy therefore remains framing and preparation, not a current
empirical contribution.

## 5. Claims the evidence does not support

The current record does not support any of the following:

- that BindCheck establishes a vulnerability from a current E1 warning;
- that matching role, amount, beneficiary, state, domain, or name establishes
  authorization;
- that a mechanical `ESTABLISHED` result is `VERIFIED_WITHIN_SCOPE`;
- that the full arm has a fair comparative advantage;
- that the automated join is novel, first, unique, or absent from prior work;
- that the analyzer transfers to an independently developed supported family;
- that unsupported analysis or silence is safe;
- that the exposed benchmark estimates precision, recall, prevalence, or
  ecosystem security;
- that the current prototypes prove extraction soundness, arbitrary
  transformation equivalence, or a formal authorization theorem; or
- that the research contract's capability gate, Gate B, or Gate C has passed.

The narrow supportable statement is that the project has an exposed-development
E1 diagnostic interface and bounded mechanical prototypes that make identity,
fact strength, approximation, provenance, and unresolved authorization links
explicit. The proposed automatic discovery-and-E4-validation capability
remains unresolved.

## 6. Closest related work

The comparison is organized around actual overlap rather than a claim that no
prior tool performs a named operation.

| Work | Verified overlap | Current access/experiment limit |
|---|---|---|
| [ZKAP](https://www.usenix.org/system/files/usenixsecurity24-wen_1.pdf) | Circuit-dependence graph, nine detectors, and direct unused-public-input overlap | Circom-oriented native artifact; no fair adapted consumer-relevance experiment |
| [CIVER](https://ieeexplore.ieee.org/document/10646792/) | Modular verification, tags, weak safety, pre/postconditions, and expressive circuit specifications documented by its artifact | Publisher full text not retrieved; equal-property specification and effort comparison absent |
| [CCC-Check](https://vdb.space/papers/zkp2026.pdf) | Computation-constraint consistency through value inference and CirC IR; paper reports Noir among frontends | Exact pinned target compatibility and runnable comparison not established |
| [SmartAxe](https://people.cs.umass.edu/~juanzhai/papers/fse24liao.pdf) | Cross-program graph alignment, protected-resource inference, and semantic bridge inconsistency | Native paired-bridge applicability and strongest-simple adaptation unresolved |
| [ELSA](https://conf.researchr.org/details/issta-2026/issta-2026-research-papers/131/Augmenting-Multi-Technique-Static-Analysis-with-Large-Language-Models-A-Neuro-Symbol) | Official abstract describes constraint-guided LLM-assisted analyzers, conflict-resolving ensemble, and self-constructed ZKP-based smart-contract evaluation | Full paper, artifact, models, prompts, benchmark, and exact circuit/consumer scope not primary-sourced or inspected |

ZKAP prevents any unused-public-input novelty claim. CIVER makes rich modular
specification and summaries prior art. CCC-Check means producer semantics
cannot be reduced to occurrence counting when claiming an advance. SmartAxe
shows that cross-program semantic joining and resource/check association are
not new in themselves. These tools may require native inputs or adaptations,
but frontend mismatch is not an algorithmic miss.

ELSA is an unresolved closest-work item. The official ISSTA abstract names
Ensemble LLM-assisted Static Analysis, constraint-guided neural semantic
reasoning, analyzer conflict resolution, three open-source datasets, and
self-constructed ZKP-based smart contracts. The proceedings identifier is
[DOI 10.1145/3832222](https://doi.org/10.1145/3832222). The abstract is not
enough to say whether ELSA consumes circuit constraints, consumer semantics,
or their relation. It supports neither an overlap conclusion nor a novelty
conclusion.

A minimal distinguishing experiment would hold the producer fixed while
changing only a protected consumer relation, include state/domain/identity
swaps and semantics-preserving renamings, and give producer-only,
consumer-only, union, strongest-simple, full, same-policy, and applicable
closest-work arms the same facts and reviewed policy. Every adapter,
annotation, prompt, model, setup correction, and human minute must be counted.
Candidates must proceed through the same E1-to-E4 route. That experiment has
not occurred.

## 7. Limitations, ethics, AI assistance, and artifact boundary

### 7.1 Technical and empirical limitations

The current analyzer covers a bounded Noir/ACIR-to-Solidity/EVM fragment. It
does not establish arbitrary compiler or ABI identity, dynamic-memory and path
soundness, aggregation, splitting, deferral, unbounded histories, proxies,
delegate calls, inline assembly, reentrancy, or general external-call
semantics. Occurrence is not injectivity or intent. Source-derived roles are
annotations unless a compiler-backed semantic relation establishes them.

The benchmark uses two known lineages and authored variants. Case selection,
labels, rules, and validation harnesses were exposed during development. The
historical proof chains and current warning set use different versions and
purposes. No confidence interval, prevalence estimate, real-world recall, or
independent precision estimate is warranted.

Gate A has no eligible row. The mechanical fixtures are synthetic or
explicitly annotated, use no reviewed human policy, and return effective
`UNKNOWN`. Passing targeted controls does not prove general soundness.

### 7.2 Ethics and disclosure boundary

The D2 work reported here used exposed development material and bounded local
or synthetic fixtures. It did not open reserved sources for evaluation, test a
live third-party deployment, broadcast an exploit transaction, or contact a
maintainer. The Payy mechanism was publicly disclosed by others; the local
chain reproduces a known mechanism. WarpToad variants were injected by the
project and imply no defect in the pinned application.

Later credible findings would require an explicit disclosure plan and separate
authorization before maintainer contact. Validation tooling can construct
malicious witnesses and proofs against local fixtures, so a release decision
must weigh reproducibility against misuse. No private or reserved evidence
belongs in a public artifact.

The taxonomy human study has not begun. No institutional review determination
is asserted. Human authors must decide whether future annotation work needs an
approval or waiver and record the actual decision.

### 7.3 Generative-AI assistance

AI agents materially contributed to code, protocols, tests, evidence audits,
source screening, reports, and this status draft. They also operated tools and
prepared comparison and evaluation scaffolding. AI suggestions and outputs are
not independent annotation, policy review, scoring, adjudication, or
coauthorship.

Human authors have not yet completed the required inspection of every claim,
citation, generated code path, table, and disclosure. The official venue's
suggested editorial-use statement says that all outputs were inspected by the
authors; that statement must not be used until the inspection actually occurs.
A future disclosure must cover both methodological and editorial use,
reproducibility limits, independent validation, why AI was used, available
model/hardware information, and how query volume and environmental cost were
bounded. No AI agent may be listed as an author or counted as a missing human
role.

### 7.4 Artifact boundary

The local repository contains sealed development records, ignored raw
evidence, internal task identifiers, and non-anonymous paths. It is not an
anonymous submission artifact. A future artifact must include only approved
release material, preserve exact manifests and versions, redact or omit
private evidence, avoid author-identifying repository/account names, and be
frozen at the paper deadline if linked from the submission. Post-acceptance
artifact evaluation has separate permanent-hosting and reproducibility
requirements.

## 8. Submission-readiness disposition

The official [IEEE S&P 2027 Call for Papers](https://sp2027.ieee-security.org/cfpapers.html)
sets the Cycle 2 abstract deadline at 10 November 2026 and paper deadline at
17 November 2026, both 23:59:59 AoE. Abstract registration requires a full and
complete abstract, complete author list with ORCIDs, and conflicts; title,
abstract, and author list then lock. The venue permits 13 pages of text plus 5
pages of references and appendices, requires US-letter IEEEtran 1.8b with
`conference,compsoc`, and does not require reviewers to read appendices.
Anonymous artifact repositories are strongly encouraged and cannot be updated
after the paper deadline. Ethics and generative-AI HotCRP fields are mandatory,
and authors bear responsibility for a draft uploaded 24 hours before the
deadline.

This project does not currently meet those scientific or administrative
conditions. There is no supported central comparative/capability result,
independent transfer, Gate B/C outcome, complete human review, final author
metadata, approved ethics/AI disclosure, anonymous artifact, or rendered
IEEEtran PDF. The document is intentionally Markdown and intentionally retains
an internal evidence map.

The appropriate disposition is **NOT SUBMISSION READY**. Registering a
successful final-results abstract would overstate the evidence and lock the
overstatement. A later submission decision requires either new sealed evidence
that supports the candidate contribution or an explicit human decision to
narrow the paper to a venue-appropriate negative/status contribution.

## 9. Conclusion

Proof-to-execution authorization can require a relation across producer
constraints, decoded identities, consumer reliance, and policy. BindCheck's
current exposed-development interface emits bounded E1 associations, and its
new identity, authorization-boundary, and typed-extraction prototypes make
several previously implicit assumptions explicit.

The strongest current result is fail-closed rather than positive. Gate A has
no eligible comparison row and is `INCONCLUSIVE`. The corrected extractor
derives neither the producer authorization guarantee nor the exact protected-
effect reliance relation needed to discharge a MUST obligation. The common
arms therefore agree on `UNKNOWN`, as they should. Historical real-proof cases
show that the problem class can matter, but they do not supply current
automatic discovery or independent transfer.

The remaining measurable prerequisite is a preregistered, hash-bound method
that derives at least one `MUST`/`EXACT`/`DERIVED`/`SUPPORTED` producer
guarantee and exact effect-reliance link from actual supported semantics, with
a paired negative control and reviewed human policy. Only after a fair scored
comparison, supported independent run, and human triage can the capability and
contribution be assessed. Until then, the research verdict remains `UNKNOWN`,
Gate A remains `INCONCLUSIVE`, and the manuscript remains not submission-ready.

## Internal evidence map

This section exists for author traceability and must be replaced by anonymized,
reader-appropriate citations before any submission.

| Manuscript subject | Controlling local record |
|---|---|
| Current integrated interface and versioned counts | [`reports/D2-01.md`](../reports/D2-01.md) |
| Claim corrections and primary-source positioning | [`reports/D2-03.md`](../reports/D2-03.md) |
| Taxonomy preparation and missing human study | [`reports/D2-04.md`](../reports/D2-04.md) |
| Construction and transformations | [`reports/D2-06A.md`](../reports/D2-06A.md) |
| External inventory and same-policy smoke | [`reports/D2-06B.md`](../reports/D2-06B.md) |
| Gate A `INCONCLUSIVE` | [`reports/D2-07.md`](../reports/D2-07.md) |
| Compiler-backed identity prototype | [`reports/D2-08.md`](../reports/D2-08.md) |
| Authorization-boundary prototype | [`reports/D2-09.md`](../reports/D2-09.md) |
| Corrected typed-extraction prototype | [`reports/D2-10.md`](../reports/D2-10.md) |
| Steps 11–14 non-execution and Gate B dependency audit | [`reports/D2-11-14-dependency-audit.md`](../reports/D2-11-14-dependency-audit.md) |
| Steps 15–17 non-execution and Gate C readiness audit | [`reports/D2-15-17-readiness-audit.md`](../reports/D2-15-17-readiness-audit.md) |
| Versioned claim ledger | [`docs/d2/claim-ledger-v2.json`](../docs/d2/claim-ledger-v2.json) |
| Related-work matrix | [`docs/d2/related-work-matrix-v2.json`](../docs/d2/related-work-matrix-v2.json) |
| Source and access record | [`paper/d2-status-sources.md`](d2-status-sources.md) |
| Venue readiness | [`paper/ieee-sp-2027-readiness-checklist.md`](ieee-sp-2027-readiness-checklist.md) |
