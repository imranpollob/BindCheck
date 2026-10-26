# D1P-C01 — taxonomy and annotation protocol

Draft version `0.1.0`, 26 October 2026. **Protocol authoring complete; human
review and prospective freeze pending.** This task performs no searches for
findings, screening, labeling, builds, or security validation. It creates no
populated corpus. The companion [ledger schema](ledger.schema.json) specifies
future records; schema validity is not evidence validity.

The [research contract](../research-contract.md) controls semantics, threat
model, and evidence. [D1P-11](../../reports/D1P-11.md) and its
[frozen protocol](../../protocols/d1/d1p-11-screening.json) supply development
scope and prior exposure context, not independent annotations. This protocol
does not replace or relabel that screen. The current task permits only the
four applications in D1P-11's `permitted_applications`: Payy rollup, WarpToad,
0xbow Privacy Pools, and Aztec v6 epoch rollup. No application source was
opened for this task. Broader search below is a prospective method, not
authorization to execute it. Any future execution needs a separately frozen,
human-approved development scope; discovery cannot silently expand it.

The original task wrote only the protocol and schema. The authorized follow-up
adds validation fixtures, results, tooling, and a human review package only
under `docs/taxonomy/`. The integrator owns canonical README and project-status
updates. No commit, push, or merge is part of C01.

## 1. Prospective search protocol

### Sampling frame and dates

The proposed first publication window is **1 January 2018 through 26 October
2026, inclusive, in UTC**. This is a pragmatic retrospective window, not a
claim that earlier work is irrelevant. The inclusion date is the earliest
public primary disclosure of the finding, not the search-engine date, date
of an exploit, or date of a later mirror. Record disclosure, incident, audit,
affected revision, patch, and retrieval dates separately. Missing or disputed
disclosure dates remain unresolved; do not guess them into the denominator.
An in-window finding can concern older code. An older disclosure resurfacing
in-window is background only. Supporting artifacts outside the window may
explain an in-window finding and must be identified as such.

Before running searches, humans freeze scope, source endpoints, query matrix,
language coverage (initially English; record untranslated exclusions), query
order, pagination policy, time budget, and stopping rule in a versioned
search-plan record. Suggested retrieval cap: first 100 results per query in
returned order, without severity-based selection; record a shorter result
list or inaccessible pagination. Freeze an explicit active-time budget before
execution. Log skipped or truncated queries, not just successful searches.
Never stop because a desired number of positive findings has been reached.

### Sources and query matrix

Use each allowed application's exact name, documented aliases, and repository
identifier as the application term. Cover every source class, including
classes with no hits. Catalog endpoints must be scoped to the permitted
application; do not browse unrelated project lists. Freeze exact endpoints
before a future run, and keep unavailable endpoints in the search log.

| Source class | Retrieval and evidence rule |
| --- | --- |
| Audit firms | Application-specific audit landing pages and full reports, scope/commit manifests, amendments, and remediation appendices. A landing-page count is not a finding record or verified remediation. |
| Audit contests | Application-specific contest reports, individual submissions, judging/duplicate decisions, and sponsor responses. Preserve rejected/disputed status; contest severity is not semantic validation. |
| Advisories | First-party security advisories, repository advisories, and vulnerability records with primary links. Keep issuer, disclosure ID, affected revisions, and revision history. |
| Postmortems | First-party incident reports and technical analyses linked to primary artifacts. Distinguish claimed impact from demonstrated committed effects. |
| Patches | Pinned commits, pull requests, issues, diffs, regression tests, and release notes. A patch without a disclosure is a candidate lead, not proof of an exploitable defect. |

For each application and source class, run the following lexical groups as
separate queries rather than requiring every term in one overly narrow query:

1. Discovery terms: `audit`, `security review`, `contest`, `advisory`,
   `postmortem`, `incident`, `fix`, `patch`.
2. Proof boundary: `public input`, `public output`, `public signal`,
   `proof binding`, `underconstrained`, `unconstrained`, `verifier`,
   `verification key`, `circuit ID`, `program ID`.
3. Representation: `encoding`, `decoding`, `ordering`, `field`, `range`,
   `canonical`, `truncation`, `padding`, `length`, `prefix`, `activation`.
4. Effects and context: `recipient`, `amount`, `asset`, `nullifier`, `replay`,
   `domain`, `chain ID`, `state root`, `withdraw`, `mint`, `settlement`,
   `omission`, `batch`, `double spend`, `fee`, `failed transfer`.

**AI-written illustrative query template (not executed):**
`"<permitted application>" "public input" audit`.
Run broad application-specific discovery terms as well as mechanism terms
so vocabulary choice does not preselect the taxonomy. Search within retrieved
reports for the mechanism groups. Citation/patch following stays within the
frozen application scope. Record exact query text, engine or endpoint,
filters, result positions, pages, hit counts (or unknown), retrieval interval,
actor, returned source IDs, failures, and stop reason. Search absence means
only “not located under this protocol.” Record inaccessible full reports and
missing source separately; neither establishes absence of defects.

Prefer original primary records and immutable revisions. Store source URI,
publisher, source class, disclosure/finding ID, dates, pinpoint locations,
content SHA-256 when bytes are retrieved, retrieval actor/time, and evidence
limitations. Summaries and snippets can identify leads but cannot establish
relation/consumer semantics. Do not fetch live-chain data, contact maintainers,
or execute third-party systems under this protocol.

### Deduplication and counting

Preserve retrieval hits, source documents, candidate findings, applications,
and families as different units. One document may contain several findings;
one finding may have several documents. Normalize document URLs by removing
tracking fragments while preserving version identifiers; use content hashes
to identify identical copies. Retain all source aliases and provenance edges.
Audit/advisory/contest/postmortem/patch descriptions of the same root cause,
affected boundary, and repair lineage map to one canonical finding ID.

Split findings when independent missing relations require independent repairs,
even if they occur in one report. Do not split by severity, attacker address,
transaction count, publication, affected deployment, or a second consequence
of the same cause. Fork manifestations of an inherited defect share one
canonical finding with multiple affected application IDs and manifestation
notes; independently introduced defects remain distinct findings in a shared
family. Historical repairs, mutants, and legitimate controls are linked
variants, not new independent historical findings.

Uncertain duplicate matches stay explicit and unresolved until human review.
Do not silently merge, discard, or count them as independent. A reviewer
records the equivalence rationale, source IDs, canonical ID, author/time,
and decision history. Preserve duplicate candidate rows with
`duplicate_of`; exclude those rows from the canonical finding denominator.
Report unresolved duplicate counts and sensitivity bounds rather than a
single purportedly exact deduplicated total.

## 2. Inclusion: proof-to-execution binding

A candidate is **relevant** when evidence supports a disagreement between
what the actual accepted proof relation establishes and what the consumer
interprets as authorized or required by that proof. This definition is
independent of whether the current analyzer supports the implementation.
Relevance can be supported by a sufficiently specific disclosure; it is not
a security verdict or confirmation that the disclosure is correct.

Document all five parts of the boundary argument:

1. **Accepted relation:** identify `R_v(p,w)`, public statement, and program/key
   configuration. State what is actually established and what is merely
   reported or assumed; honest witness-generator behavior is not a constraint.
2. **Interpretation:** identify decoding `D_v(p,x)`, verifier argument mapping,
   and the consumer's use of those values, including guards and forwarding.
3. **Policy:** independently justify permissions `P`, required obligations
   `O`, and any transformations under reviewed `sigma`. Policy must not assert
   the missing implementation equality or the expected security verdict.
4. **Committed consequence:** describe a possible successful execution with
   an incompatible effect in `E`, or an undischarged required obligation after
   allowed cancellation/deferral. Reverted effects do not count as committed.
5. **Feasibility and uncertainty:** record actor capabilities, admitted state
   or bounded reachable history, proof feasibility, and missing evidence.
   Missing proof artifacts can block later stages without erasing relevance.

Use `include`, `exclude`, or `unresolved` for relevance decisions; these are
sampling decisions, never substitutes for the contract's security verdicts.
If policy or the boundary argument is too vague, use unresolved with an
explicit gap. Do not force an exclusion because the analyzer lacks a frontend.
Pure circuit bugs and pure contract bugs are excluded **unless the accepted
relation and consumer interpretation disagree**. Neither the location of a
patch nor the presence of the word “ZK” decides inclusion.

**Every example in the following table is AI-written and illustrative.
None describes or labels an application, observed finding, or validated attack.**

| Illustrative situation | Inclusion decision and reason |
| --- | --- |
| Relation constrains active records but leaves inactive tail words free; consumer decodes those words into transfers. | Include: accepted statement can authorize no such record while execution interprets it as an effect. |
| Producer exposes `(amount, recipient)` but consumer uses the same positions in reverse. | Include if a feasible accepted vector causes a mismatched protected effect; retain feasibility gaps. |
| Relation authorizes one withdrawal occurrence; consumer permits the proof to drive two committed withdrawals. | Include: multiplicity disagreement. A replay-guard patch in a contract does not make this a pure contract exclusion. |
| Proof binds a transition requiring two discharges; consumer commits one and silently drops the other with no permitted pending record. | Include: coverage disagreement, even if every performed transfer is authorized. |
| Consumer accepts a key for a different application relation and treats its output as authorization here. | Include: configuration-to-interpretation mismatch, assuming soundness for the relation actually verified. |
| Arithmetic gadget computes an internal value incorrectly, but the erroneous value neither changes a protected obligation nor reaches consumer interpretation. | Exclude: pure circuit issue with no demonstrated binding disagreement. |
| Underconstrained value becomes a withdrawal quantity not backed by the proof-authorized debit. | Include: a circuit defect can create the required boundary mismatch. |
| An unrelated administrator-only sweep function lacks an access check and never interprets proof-backed authorization. | Exclude: pure contract bug. |
| Verifier accepts forged proofs because cryptographic soundness is broken. | Exclude from initial scope: no sound accepted-relation premise; do not conflate with selecting the wrong otherwise-sound key. |
| Consumer uses only selected outputs; unused outputs authorize no effects or required obligations. | Exclude absent another mismatch: subset use alone is not a defect. |
| A failed transfer creates an explicitly permitted, fully backed pending claim; eventual payment is delayed. | Exclude as a binding finding absent an authorization/coverage failure; unconditional liveness is out of scope. |
| Disclosure says “invalid proof accepted” but supplies no relation, key, or consumer mapping. | Unresolved until the boundary can distinguish soundness failure, configuration mismatch, and reporting ambiguity. |

Do not elevate taxonomy relevance into current implementation support.
Recursion, hashes, aggregation, splitting, deferral, unsupported EVM behavior,
and token assumptions must remain explicit limitations or `UNKNOWN` under the
contract. Conservation is a matching condition of authorization and coverage,
not a third top-level property. A clean audit is not a negative control;
property-specific legitimate behavior and repair controls require evidence.

## 3. Family definition

A family is the connected component of demonstrated **application code
lineage or shared application-specific circuit/consumer templates**. Forks,
renames, ports, versions, repairs, and synthetic mutants remain in the same
family when they preserve that ancestry. Copied application-specific circuit
or settlement templates can merge families even across organizations; both
producer and consumer need not be identical. Establish a substantive shared
authorization/transition template, not just similar vocabulary.

Use pinned ancestry, a documented fork, or a located copied/ported template as
evidence. Record both endpoints, relation type, source locations, revisions,
reviewer, and rationale for every merge edge. Shared generic verifier code,
proof stack, compiler, hash/Merkle library, token base, or organization alone
**does not merge families**. Record organization membership and shared
libraries in separate registries with versions and use roles. The same
organization may own independent families; one family may span organizations.

Uncertain ancestry is `unresolved`, not an asserted merge or proof of
independence. For conservative cap/independence accounting, put potentially
related families in one `independence_group_id` until reviewed; retain their
provisional family IDs. Report both provisional families and conservative
groups. A merge preserves old IDs as aliases, moves all variants together,
and carries forward the union of exposure histories. Never create apparent
independence by splitting an exposed fork or repair into a new family.
Freeze the family map before evaluation and record dated changes and affected
counts. D1P-11's assignments are prior development metadata, not newly
adjudicated ancestry in C01.

## 4. Annotation handbook

### Unit, evidence, and missingness

The unit is one canonical finding and its pinned affected boundary, with
manifestations and repaired versions attached. Assign **cause × consequence
× attacker role** as independent multi-label fields. Store causal links from
each supported cause to consequence and required role; do not assume that
every Cartesian combination of assigned labels is feasible.

For every field, partition the codebook labels into `present`, `absent`, and
`uncertain`. `unassessed` has three empty arrays. `partial` preserves known
decisions and missing/uncertain ones. `complete` requires every codebook label
to appear exactly once in present or absent, with no uncertain labels.
An empty array is never automatically a negative judgment. Each present or
uncertain decision needs a source pinpoint and rationale; recorded absence
means the annotator reviewed that label against the available packet.
“Other” requires a mechanism description; it does not mean unknown.

Annotators receive the same versioned source/policy packet. Keep reported
claims separate from inspected implementation facts and separately record
`EXTRACTED`, `PROVED`, and `ASSUMED`. Record model/proof/replay limits. A patch
location does not establish a root cause; source inspection does not establish
real-proof feasibility. Policy unresolved means no forced effect label or
security conclusion. Never pass expected annotations into analyzer policies.

### Cause labels

| Code | Definition and decision rule |
| --- | --- |
| `C_RELATION_GAP` | Accepted constraints omit a dependency that consumer interpretation needs. Use only with the missing semantic binding identified, not every circuit imperfection. |
| `C_FIELD_MAPPING` | Producer/verifier/consumer disagree on field identity, order, slice, or forwarded value. Mere unused output is insufficient. |
| `C_REPRESENTATION` | Field/integer/byte width, range, sign, canonicality, or encoding interpretation differs. Record representations on both sides. |
| `C_ACTIVATION_EXTENT` | Length, count, prefix, padding, tag, or activation predicate disagrees about which occurrences are meaningful. |
| `C_CONTEXT_IDENTITY` | Domain, application, actor, asset, state/version, or other semantic identity is not bound to the context executing the effect. |
| `C_VERIFICATION_CONFIG` | Program/key/circuit selection or configuration allows a sound relation to be interpreted as another one. Cryptographic soundness breaks are excluded. |
| `C_OCCURRENCE_ACCOUNTING` | Accepted authorizations/obligations lose identity, multiplicity, or single-use accounting across execution. Do not infer from shared numeric totals alone. |
| `C_DISCHARGE_TRANSFORMATION` | Consumer effect selection, aggregation, split, cancellation, or pending-state handling violates an independently specified discharge rule. |
| `C_OTHER_BINDING` | A documented binding cause satisfies inclusion but fits none of the above. Human review is required before adding a new code. |

Allow multiple causes when evidence independently supports each mechanism.
For instance, an extent disagreement may also involve a relation gap, but
neither automatically implies the other. Prefer a specific code to “other.”

### Consequence labels

| Code | Definition and decision rule |
| --- | --- |
| `K_AUTHORIZATION` | A committed protected effect has no compatible permission under `sigma`. Includes exceeding permitted quantity/multiplicity. |
| `K_COVERAGE` | A required obligation lacks a compatible committed discharge, valid cancellation, or permitted pending transformation. |
| `K_MISDIRECTED` | Wrong beneficiary, asset, domain, or semantic identity. Pair with the supported top-level property or properties. |
| `K_QUANTITY` | Too much/little value, incorrect split, or incompatible total. Identify amount and units; balance conservation alone does not prove identity matching. |
| `K_DUPLICATE_REPLAY` | An occurrence/permission is reused beyond its allowed multiplicity. Record whether within one call, across calls, or across domains. |
| `K_OMITTED_DISCHARGE` | An accepted required occurrence is skipped or silently dropped. Pair with coverage. |
| `K_STATE_INCONSISTENCY` | A committed root, claim, spent flag, deposit, or other protected state disagrees with the accepted transition. State writes themselves may be protected effects. |
| `K_OTHER_EFFECT` | Another evidenced authorization/coverage consequence; explain it and retain the top-level property code. |

For a complete included finding, at least one of `K_AUTHORIZATION` or
`K_COVERAGE` must be present. Wrong quantities, recipient, or replay can cause
both; justify each rather than mechanically assigning both. No separate
conservation, privacy, severity, monetary-loss, or liveness label is a
top-level property. Uncommitted/reverted traces establish neither property
failure. Severity and claimed losses may be preserved as source statements
but do not drive inclusion or these labels.

### Attacker-role labels

| Code | Definition and decision rule |
| --- | --- |
| `A_PUBLIC_CALLER` | Arbitrary caller can realize the pathway using public entry points and obtainable inputs. Do not assign merely because a function is public. |
| `A_WITNESS_PROVER` | Attacker must choose/deviate in witness or proof construction; this is a capability, not automatically a privileged on-chain role. |
| `A_RELAYER` | Requires control of the relaying/processing role or its inputs. State whether the role is permissionless or restricted. |
| `A_REGISTERED_PROVER` | Requires admission to a configured prover set. Do not generalize to arbitrary callers. |
| `A_OPERATOR_ORDERER` | Requires sequencer, batch builder, or ordering authority beyond ordinary transaction submission. |
| `A_PRIVILEGED_CONFIGURATOR` | Requires administrator, upgrader, key selector, or configuration authority within the evaluated deployment threat model. |
| `A_OTHER_ROLE` | Another explicitly evidenced capability/role; describe it and whether the contract threat model admits it. |

Record minimum sufficient capabilities, honest parties, available proofs,
state prerequisites, and any collusion. Label only roles required by at least
one feasible pathway, not all roles a stronger adversary could possess.
Use `attack_paths` to distinguish conjunctions (all roles within a path) from
alternatives (separate paths). Record role/control unknowns as uncertainty.
If the attack requires breaking a trusted assumption, state the exclusion or
unsupported-model reason; do not silently expand the threat model.

### Independent annotation and agreement

Use at least two **human** annotators who independently read the frozen packet
and complete the same codebook before seeing each other's labels or tool
verdicts. Log prior exposure; common AI suggestions are not independent human
judgments. AI drafts may assist preparation, but preserve them separately as
`ai_draft` or `human_ai_assisted`. Only rounds marked `independent_human` enter
the primary reliability calculation. Do not count AI agents as raters.

Before a future round, freeze the assignment of records to raters and whether
the entire eligible corpus or a specified probability sample will be double
coded. Record missing ratings and sampling probabilities. Use development
calibration packets to clarify rules, then freeze version, packets, and
measurement plan; do not score a jointly discussed calibration round as
independent reliability. Revisions require a new round; preserve old ratings.

Primary metric: **Krippendorff's nominal alpha per binary label**, separately
for causes, consequences, and roles. Expand each multi-label field into one
present/absent variable per code, retaining item/annotator IDs. Uncertain,
unassessed, and omitted decisions are missing, never absent. Alpha uses
observed versus chance-expected nominal disagreement (`1 - Do/De`); include
only items with at least two determinate human ratings for that label. For
exactly two fixed raters, predeclared per-label Cohen's kappa
(`(po - pe)/(1 - pe)`) is an allowed alternative, not a result-selected metric.
Record metric implementation/version, counts, marginal prevalences, missing
ratings, and the calculation matrix or its immutable hash.

Also report raw pairwise agreement per label (agreeing comparable rater pairs
over all comparable pairs), positive and negative agreement for two-rater
labels, and exact-set agreement per field on fully assessed packets. For
two raters, positive agreement is `2a/(2a+b+c)` and negative agreement is
`2d/(2d+b+c)` from the present/absent 2×2 table. Report undefined values and
denominators explicitly. Report a missingness/completion table so selective
abstention is visible. Do not compute one nominal statistic over concatenated
label sets or pool all labels into a prevalence-dominated score. If providing
a macro average, list all per-label estimates and omitted undefined labels.

If expected disagreement is zero, there are no comparable ratings, or a
denominator is zero, report `null` with the reason, not perfect reliability.
Report 95% uncertainty intervals using a predeclared bootstrap that resamples
whole family independence groups (2,000 replicates, recorded seed); report
undefined replicates and do not claim precise intervals when too few groups
support them. Agreement is descriptive: no threshold can make disputed labels
true, and no unmeasured reliability value is asserted in C01.

### Written adjudication rules

1. Seal the original human ratings and calculate pre-adjudication agreement.
   Keep packet/codebook hashes and all AI assistance/exposure declarations.
2. Compare disagreements label by label, including relevance, family links,
   deduplication, and uncertainty. Cite the competing evidence and exact rule.
3. A human adjudicator reviews both rationales, the pinned packet, and policy.
   If the original raters cannot resolve it, use an additional human reviewer;
   AI output cannot break a tie. Record reviewer identities and conflicts.
4. Produce a separate resolution: upheld, changed, or unresolved, with original
   rating IDs, decided labels, evidence, rationale, reviewer, and timestamp.
   Missing artifacts/policy leave a disputed label uncertain. A majority vote
   without a semantic rationale is insufficient.
5. If a new rule is necessary, version the handbook, identify every affected
   earlier record, and reannotate them in a new round. Never rewrite the
   independent ratings or report adjudicated agreement as reliability.

## 5. Exposure accounting

Maintain an append-only event log of **which human or AI agent read which
family's code, findings, or results, and when**, including indirect exposure
through reports, snippets, prompts, diffs, generated summaries, and handoffs.
This ledger contains development records only. **Reserved families are chosen
and stored by humans outside all worktrees before any new development
screening.** This is a prospective prerequisite, not a claim that selection
has occurred. Selection identities,
locations, membership flags, and hashes must not be requested, named,
inferred, or stored here.

Register each actor with a stable pseudonymous ID, type (`human` or `ai`),
role, and, for AI, known provider/model/version and session/agent ID. Unknown
model metadata stays null with a reason. A shared model name is not an agent
identity. Human identities may use a controlled external identity mapping.
One event covers one actor, one family, and a clearly bounded reading event;
expand a multi-family report into separate linked events. For AI, inherited
context and summaries count as exposure even without an explicit file-open.

Each event records event ID, actor/session, family, application IDs if known,
material kinds (`code`, `finding`, `result`, `policy`, `metadata`), source IDs
or local document locations, exact revision/hash where available, direct or
indirect access, purpose, start/end UTC timestamps, logging timestamp,
recorder, and whether it was contemporaneous or retrospective. When exact
time is unknown, store the UTC date or an approximate interval, precision,
and basis; never invent an exact time. Corrections append an event referring
to `corrects_event_id`. “No event found” means unknown exposure, not unexposed.

Record both AI preparation and subsequent human reading of its output. Keep
the union of exposure after family merges, preserve former IDs, and propagate
exposure through documented lineage/template links. Log accidental exposure
promptly without further inspection. Human review determines downstream
eligibility; exposure is not erased by changing agent, organization, branch,
or worktree.

C01 provenance note (actual task activity, not an example): the authoring
Codex agent read the contract, repository instructions/status/roadmap,
D1P-11 report and protocol on **2026-10-26 UTC**. Through D1P-11 it received
indirect findings/results and application-mapping context for the four
permitted development families. Exact per-read times were not captured; date
precision is retrospective. No application code was opened and no human
reading is asserted. A future ledger importer must preserve this as separate
family exposure events, with unknown agent-version details left unknown;
this note creates no screening or annotation records.

## 6. Ledger and screening funnel

The JSON Schema uses draft 2020-12. The top-level ledger holds plan identity,
actors, search runs, source records, organizations, shared libraries, families,
applications, candidate findings, exposure events, annotation rounds,
agreement reports, derived funnel counts, and append-only change history.
Arrays may be empty; C01 supplies a schema, not populated records or counts.
Unknowns are explicit and never implicitly false. Nonempty decisions need
evidence references and rationale. The schema rejects unknown fields so a
codebook extension requires a version change.

Use stable IDs and evidence links, with publication claims separate from
artifact metadata, implementation facts, analyst policy, and analysis results.
Artifacts record kind, URI/path, immutable revision/hash (or an explicit gap),
availability, correspondence status, and retrieval provenance. Build/analysis
attempts record command, tool/version, source/environment pins, interval,
exit/resource outcomes, bounds, assumptions, logs/hashes, and blockers.
Future result records retain only `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, or
`UNKNOWN`, with evidence grade, fact status, non-vacuity, and reason codes.
No analysis yet means a null result, not an invented verdict.

Each canonical finding has all six stage records, each with status
`not_attempted`, `pending`, `met`, or `not_met`, decision time/actor,
reason codes, rationale, evidence references, and missing prerequisites.
Later stages can be met only if every earlier stage is met. A pending or
failed stage remains in earlier denominators; it is never silently dropped.

| Stage | Entry evidence required to mark `met` |
| --- | --- |
| `screened` | A human has reviewed the candidate record, checked scope/date, and recorded a relevance decision or a specific unresolved question. Retrieval alone is not screening. |
| `relevant` | Inclusion decision is `include` with a documented accepted-relation/consumer/policy mismatch. A specific reported claim can pass; confirmation is separate. |
| `artifacts_available` | Required pinned producer source/constraints/ABI, program/key/verifier, consumer/configuration, policy, and owned local proof/replay route are accessible for the proposed analysis. Record each missing, unavailable, or justified not-applicable item; an inventory listing alone does not pass. Repairs are additionally required for repair-validation claims. |
| `supported` | A versioned capability review finds the boundary, representations, roles, state/history, and effect model within the declared fragment; artifact correspondence is established or explicit permitted assumptions are reviewed. Unimplemented operations and unresolved policy block this stage. |
| `analyzed` | At least one declared analysis attempt has completed with a recorded contract verdict, scope, provenance, resources, and logs. Timeout/build failure is a recorded attempt, but cannot by itself pass this stage. A completed inconclusive analysis may be `UNKNOWN`. |
| `validated` | Independent human semantic review and result-specific checks support the stated claim. For `VIOLATION`, check concrete feasibility plus a real accepted proof and committed effect replay on the pinned original consumer in an owned local environment. For `VERIFIED_WITHIN_SCOPE`, require non-vacuity, justified extraction/abstraction, complete bounded obligation discharge, and legitimate controls. `UNKNOWN` never passes. Repair validation additionally needs faulty and repaired checks plus legitimate behavior. |

Keep evidence grade separate: `reported`, `source_confirmed`,
`model_confirmed`, `locally_reproduced`, `repair_validated`. Attach grades to
individual evidence claims; contradictory claims remain visible. A concrete
model violation is not an end-to-end attack. An abstract SAT candidate that
cannot be concretized remains `UNKNOWN`. A mock verifier, source availability,
unlocated audit, or unsupported feature cannot pass validation or imply safety.
Taxonomy annotations and result validation have different reviewer records.

Primary funnel unit: **unique canonical candidate findings**. Count `met` at
each stage, yielding `screened ≥ relevant ≥ artifacts_available ≥ supported
≥ analyzed ≥ validated`. Also report per-stage pending, not-met, and
not-attempted counts; counts of raw retrieval hits (or unknown), unique source
records, duplicate rows, unresolved duplicate rows, applications, families,
and conservative independence groups. Count a family/application at a stage
only if at least one linked canonical finding meets it, and label this
“at least one,” not whole-family success. Counts describe this sample only;
they do not estimate ecosystem prevalence. D1P-11's four-application screen
is a different unit and must not be imported as four screened findings.

### Semantic validation beyond JSON Schema

Before publishing a populated ledger, validate the schema **with format
assertion enabled**, then perform these cross-record checks:

- IDs are unique in their registries; every ID reference resolves with the
  proper type. Canonical duplicate pointers have no cycles; duplicate rows
  are not counted. Recompute all counts from records at the reporting cutoff.
- Family edges justify merges; generic verifier/library/organization edges
  cannot be merge evidence. Application, finding, and exposure family links
  agree with the versioned family map, including inherited exposure.
- Search dates/caps match the frozen plan; start ≤ end; edits and exposures
  have honest chronology and timestamp precision. Missing retrieval history
  remains visible. A stop or failed request has its actual reason.
- Label partitions are disjoint and complete when claimed; evidence/rationale
  covers each present/uncertain label. Causal links and attack-path roles refer
  to present labels. Complete included annotations have a top-level consequence.
- Independence claims involve distinct humans and sealed pre-adjudication
  ratings. Agreement inputs match eligible rounds; adjudication does not
  overwrite ratings or count as an independent vote.
- All funnel prerequisites, artifact requirements, capability checks,
  successful attempt requirements, and result-specific validation evidence
  hold. Evidence claims resolve to pinned locations. Unsupported/timeout/build
  failures cannot be relabeled as safe; `UNKNOWN` cannot pass validated.
- Every read actor and material has an exposure record, including indirect
  context; no event means unknown rather than evidence of no exposure.

Schema shape checks cannot establish these scientific invariants. Freeze the
validator version, record failures, and correct them before publishing counts.

## 7. C01 handoff

Inputs were read at lane HEAD
`9fabd0893bcc0d3851247484da9017e5ff37ab95`; initial working tree was clean.
Tooling: Git 2.51.0 and Python 3.14.7. Reads used `cat`/`sed` for the named
protocol documents and `rg --files` for instruction/report discovery; no
application discovery, source retrieval, or application inspection ran.
The original deliverables were `docs/taxonomy/protocol.md` and
`docs/taxonomy/ledger.schema.json`; the follow-up below adds supporting files
within the same directory. No independent human annotation, agreement
statistic, corpus finding, or security result is claimed.

Validation: Python JSON parsing, schema-keyword/shape checks over 1,722 nodes,
98 resolved local schema references, 54 in-memory positive/negative structural
checks, codebook parity, and local documentation links all passed (exit 0).
The synthetic checks used only AI-written illustrative records, kept in
memory; no corpus record or label was written. They exercised missing and
conflicting label decisions, skipped funnel stages, generic-only merge edges,
unapproved plan freezing, missing validation checks, invalid verdicts,
`UNKNOWN` validation, and timeout-only analysis. The exact inline Python
commands remain in the C01 tool transcript. Re-runnable basic checks are:

```sh
python3 -m json.tool docs/taxonomy/ledger.schema.json > /dev/null
git diff --no-index --check /dev/null docs/taxonomy/protocol.md
git diff --no-index --check /dev/null docs/taxonomy/ledger.schema.json
git status --short --untracked-files=all
```

The initial schema-generation command had a Python syntax error before any
file write; correcting it produced the schema checked above. Python
`jsonschema` and Node Ajv were unavailable. Consequently a standard Draft
2020-12 meta-schema validator was **not** run; focused local structural checks
are not a substitute for that review gate or the cross-record semantic checks.
No package was installed. Runtime/analyzer tests are unnecessary for this
protocol-only change.
Assumptions needing review are the proposed date window, retrieval cap,
English-language coverage, artifact threshold, codebook granularity, and
independent-human annotation staffing. These are draft choices, not a frozen
evaluation protocol.

Recommended next task: human review and freeze of the review package, with a
versioned search plan and annotation assignment. Completion criterion: every
draft choice has an explicit recorded disposition, schema/semantic checks
are agreed, and the approved development scope, endpoints, budget, and human
roles are fixed before any new retrieval or annotation begins.

### Validation follow-up — 26 October 2026

The earlier validator-availability limitation is now resolved, without changing
the schema bytes or its draft `0.1.0` version. A standard
`jsonschema.Draft202012Validator` **4.26.0** passed `check_schema` against the
Draft 2020-12 meta-schema. With explicit date/date-time format assertions, it
accepted all three valid fixtures and rejected all three invalid fixtures for
their intended reasons; four format controls also passed. These fixtures are
AI-written illustrative ledger rows, not corpus data or application labels.

See the [validation report](validation-report.md),
[machine-readable results](validation-results.json),
[fixture manifest](fixtures/manifest.json), and
[human review checklist](review-checklist.md). All human dispositions and the
prospective freeze remain pending. Structural validation does not discharge
the cross-record evidence checks in Section 6.
