# D1P-C01 — human review and freeze checklist

Review package dated **26 October 2026**; protocol/schema draft **0.1.0**.
**Not frozen. All human review decisions are pending.** This package contains
no application screening, application annotations, or measured agreement.
The [protocol](protocol.md) controls the detailed wording; the
[schema](ledger.schema.json) controls record structure. Confirming a rule is
distinct from applying it to a finding.

For **every ID below**, humans must record `CONFIRM` or `CHANGE`, rationale,
reviewer identity, UTC decision time, and exact replacement wording/location
when changed. `PENDING` or `DISPUTED` blocks freeze. Use a dated
`review-decisions-<version>.json` under this directory; do not check boxes or
record approvals on a human's behalf. A changed rule needs an implemented
edit, affected-rule/schema/fixture review, and a second human confirmation.
Contract conflicts require the integrator's authorized contract process;
this lane cannot silently amend the research contract.

Reviewers: at least two human annotators plus a designated human adjudicator
(additional reviewer when the original pair cannot resolve a dispute).
Record role assignments, conflicts, and AI assistance. AI authorship of this
checklist or fixtures is not independent human review.

## A. Authority, scope, and prerequisites

- [ ] A01 — Research contract takes precedence; D1P-11 remains historical development metadata, not independent annotation or ground truth. No old report is relabeled.
- [ ] A02 — Scope is a frozen human-approved development allowlist. Existing authorization covers only the four D1P-11 permitted applications; no discovery, inspection, or implicit allowlist expansion is authorized by this checklist.
- [ ] A03 — **Reserved families are chosen and stored by humans outside all worktrees before any new development screening.** Human custodians perform this prerequisite; this task does not perform it or claim it is done.
- [ ] A04 — No reserved-family identities, membership lists, aliases, storage paths, artifact hashes, or selection records enter any worktree, search, fixture, prompt, agent context, or development ledger. A content-free human attestation may confirm prerequisite completion; it must reveal none of that information.
- [ ] A05 — Local synthetic assets and owned execution only; no live-chain testing, transactions, contact, disclosure, or external-message action is authorized here. Scope expansion needs separate authorization.
- [ ] A06 — Protocol authorship/validation is separate from scientific validation. Fixtures never enter corpus counts, reliability calculations, training/tuning, or evidence claims. Every AI-written example remains marked illustrative.
- [ ] A07 — Only `docs/taxonomy/` is writable for this lane; integrator handles canonical README/status changes. No commit, push, merge, or other-worktree edit is part of the task.

## B. Search frame, retrieval, and provenance

- [ ] B01 — Confirm/change the proposed inclusive UTC disclosure window **2018-01-01 through 2026-10-26** and its rationale. No ecosystem-prevalence inference follows from this convenience sample.
- [ ] B02 — Earliest public primary disclosure determines eligibility; search index dates, incidents, audits, patches, and retrieval dates are separate fields. Unknown/disputed dates remain unresolved. Older code is allowed; older disclosures republished in-window are background. Out-of-window supporting artifacts are identified.
- [ ] B03 — Confirm/change initial English-language coverage and how untranslated sources and language limitations are recorded.
- [ ] B04 — Freeze exact application names, aliases, repository terms, application-specific endpoints, query strings, source-class coverage, query order, filters, pagination, active-time budget, and stop rule before retrieval. Each parameter needs a concrete value, not a placeholder.
- [ ] B05 — Confirm/change the first **100 results per query** in returned order; keep inaccessible pagination, truncation, skipped queries, and zero-hit classes visible. Never stop or select based on favorable findings, severity, or desired positive count.
- [ ] B06 — Audit-firm records include full reports, scope commits, amendments, and remediation appendices; landing-page counts do not establish findings or repairs.
- [ ] B07 — Contest records preserve submissions, judge duplicate/dispute/rejection decisions, sponsor responses, and their provenance. Contest severity is not semantic validation.
- [ ] B08 — Advisory records retain issuer, disclosure ID, affected revisions, primary links, and revision history. Secondary summaries can supply leads only.
- [ ] B09 — Postmortems distinguish claimed incidents/losses from demonstrated committed effects and point to primary evidence.
- [ ] B10 — Patch/PR/issue/release/test records are pinned leads; a patch alone is not proof of an exploitable defect.
- [ ] B11 — Confirm/change all four lexical groups in protocol Section 1: discovery; proof boundary; representation; effects/context. Run application-specific discovery as well as mechanism queries. Do not require every term in one narrow conjunction.
- [ ] B12 — Citation and patch following remain inside frozen scope; no unrelated catalog browsing. Record exact engine/endpoint, queries, filters, positions, pages/cursors, counts or unknown, interval, actor, returned IDs, failures, and stop reason.
- [ ] B13 — “Not located” is bounded search absence only. Inaccessible full reports and missing artifacts remain distinct from no findings or safety.
- [ ] B14 — Prefer primary immutable records; preserve URI, publisher/class, finding/disclosure IDs, distinct dates, pinpoint, revision/hash when available, actor/time, and limitations. Snippets do not establish producer/consumer semantics.

## C. Units and deduplication

- [ ] C01 — Retrieval hits, documents, canonical findings, manifestations, applications, families, and conservative independence groups are separate units; preserve many-to-many provenance.
- [ ] C02 — Normalize only tracking URL components; preserve version-bearing fragments/queries and source aliases. Content hashes identify identical copies, not necessarily identical semantic findings.
- [ ] C03 — Same root cause, affected boundary, and repair lineage across reports/advisories/contests/postmortems/patches becomes one canonical finding.
- [ ] C04 — Independent missing relations requiring independent repairs split findings. Do not split by severity, address, transaction/deployment count, publication, or another consequence of one cause.
- [ ] C05 — Inherited fork manifestations share a canonical finding with affected applications/revisions; independently introduced defects remain distinct even within one family. Repairs, mutants, and legitimate controls are linked variants, not independent historical findings.
- [ ] C06 — Uncertain duplicate matches stay unresolved pending human review. Keep duplicate rows and `duplicate_of`, provenance, reviewer/time, rationale, and history. No cyclic pointers or silent deletion.
- [ ] C07 — Primary counts use reviewed canonical rows; show duplicate, unresolved, and unreviewed rows separately, with sensitivity bounds for unresolved matches. Confirm the exact counting policy before using it.

## D. Inclusion and semantic boundary

- [ ] D01 — Relevance requires a disagreement between the actual accepted relation and the consumer's proof-backed interpretation of authorization/obligations. Tool support and security validation are separate decisions.
- [ ] D02 — Record `R_v(p,w)`, statement and program/key configuration; honest witness-generator behavior is not a constraint. Reported, extracted, proved, and assumed facts remain distinguishable.
- [ ] D03 — Record `D_v(p,x)`, verifier-argument mapping, decoding, guards, forwarding, and use of accepted values.
- [ ] D04 — Independently justify `sigma`, permissions `P`, obligations `O`, effects `E`, and permitted transformations. Do not place a missing equality, expected verdict, or assumed correctness into policy.
- [ ] D05 — A committed effect must match a compatible permission preserving identity, asset, beneficiary, domain, quantity, and multiplicity. A permission need not be exercised.
- [ ] D06 — Every required obligation must be discharged, validly canceled, or converted into an explicitly permitted pending obligation. Coverage is safety; unconditional eventual execution is out of scope.
- [ ] D07 — Conserved totals are matching conditions, not a third top-level property or evidence of identity correctness. Splitting/aggregation/padding/deferral need explicit policy rules and implementation support.
- [ ] D08 — Feasibility records minimum actor capabilities, obtainable proofs, admitted state or bounded reachable history, and gaps. Reverted effects are not committed effects; a fixed pre-state is a narrower guarantee.
- [ ] D09 — Relevance decisions are `include`, `exclude`, or `unresolved` (`unassessed` before review). Vague policy/boundary remains unresolved; missing frontend/proof artifacts do not by themselves exclude taxonomy relevance.
- [ ] D10 — Pure circuit and pure contract bugs are excluded unless accepted relation and consumer interpretation disagree. Patch location, “ZK” terminology, subset-output use, and a clean audit do not establish inclusion or a negative control.
- [ ] D11 — Cryptographic soundness/setup breaks are initially excluded; choosing the wrong otherwise-sound relation/key can be included. Unsupported recursion, hashes, EVM behavior, token models, and unimplemented transformations stay explicit assumptions or `UNKNOWN`, not safety.
- [ ] D12 — Confirm/change **each** of the 12 illustrative inclusion/counter-example rows in protocol Section 2, recording sub-IDs D12.01–D12.12 in row order. They remain invented examples, never application labels or observed findings.

## E. Family definition and independence

- [ ] E01 — Family is the connected component of demonstrated application code lineage or substantive application-specific circuit/consumer templates. Forks, renames, ports, versions, repairs, and mutants retain ancestry.
- [ ] E02 — Shared application circuit **or** consumer templates can merge across organizations; both sides need not be identical. Pin ancestry/fork/copy evidence, endpoints, revisions/locations, reviewer/time, and rationale for every edge.
- [ ] E03 — Generic verifier, proof stack, compiler, hash/Merkle/token library, or organization alone never merges families. Keep organizations and versioned shared-library use in separate registries; either can span multiple families.
- [ ] E04 — Uncertain lineage is unresolved, not a claimed merge or independence. Use one conservative independence group for potentially related families until reviewed; report groups separately from provisional family IDs.
- [ ] E05 — Merge aliases preserve old IDs and the union of exposure; variants move together. No apparent independence by splitting an exposed fork/repair. Freeze family map before evaluation, retaining dated changes and count effects.

## F. Annotation unit, missingness, and codebook

- [ ] F01 — Unit is a canonical finding with pinned boundary and attached manifestations/repairs. Cause, consequence, and attacker role are independent multi-label fields; store supported causal links, not an assumed full Cartesian product.
- [ ] F02 — `present`, `absent`, and `uncertain` are disjoint. `unassessed` has empty arrays; `partial` retains missing/uncertain decisions; `complete` partitions every code into present/absent with none uncertain. Empty is not automatically negative.
- [ ] F03 — Present/uncertain labels need pinpoint evidence and rationale; absent means deliberately reviewed. “Other” requires a specific mechanism, not unknown. Specific codes take precedence where they fit.
- [ ] F04 — Same versioned source/policy packet for raters. Reported claims, implementation facts, and policy remain separate. `EXTRACTED`, `PROVED`, `ASSUMED` retain provenance, preconditions, and limitations. Policy unresolved prevents forced labels.
- [ ] F05 — Multiple cause labels require independent evidence; extent does not automatically imply relation gap or conversely. Patch location does not establish cause or feasibility.
- [ ] F06 — Complete included findings have at least `K_AUTHORIZATION` or `K_COVERAGE`; justify both separately when both apply. Consequence refinements are not substitutes for top-level properties.
- [ ] F07 — No top-level privacy, liveness, severity, monetary-loss, or conservation code. Source severity/claimed loss may be retained as attributed statements, not inclusion decisions or validation.
- [ ] F08 — Roles describe minimum sufficient pathways, including role restrictions, honest parties, proofs, state prerequisites, and collusion. Public entry alone does not prove a public-caller attack. Stronger optional roles are not automatically assigned.
- [ ] F09 — Roles within one attack path are conjunctive; separate paths are alternatives. Unknown control/feasibility remains uncertain. Breaking a trusted assumption does not silently expand the threat model.
- [ ] F10 — Each code in the following tables needs its **own** CONFIRM/CHANGE disposition under its exact code ID; confirm definition, overlap, evidence threshold, and when it must remain uncertain. New codes require human review and a versioned revision.

### Cause labels — individual review dispositions

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

### Consequence labels — individual review dispositions

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

### Attacker-role labels — individual review dispositions

| Code | Definition and decision rule |
| --- | --- |
| `A_PUBLIC_CALLER` | Arbitrary caller can realize the pathway using public entry points and obtainable inputs. Do not assign merely because a function is public. |
| `A_WITNESS_PROVER` | Attacker must choose/deviate in witness or proof construction; this is a capability, not automatically a privileged on-chain role. |
| `A_RELAYER` | Requires control of the relaying/processing role or its inputs. State whether the role is permissionless or restricted. |
| `A_REGISTERED_PROVER` | Requires admission to a configured prover set. Do not generalize to arbitrary callers. |
| `A_OPERATOR_ORDERER` | Requires sequencer, batch builder, or ordering authority beyond ordinary transaction submission. |
| `A_PRIVILEGED_CONFIGURATOR` | Requires administrator, upgrader, key selector, or configuration authority within the evaluated deployment threat model. |
| `A_OTHER_ROLE` | Another explicitly evidenced capability/role; describe it and whether the contract threat model admits it. |

## G. Independence, agreement, and adjudication

- [ ] G01 — At least two distinct humans independently rate frozen packets before seeing others' ratings/tool verdicts; log prior exposure. AI drafts/AI-assisted humans are retained separately; AI agents are not independent raters.
- [ ] G02 — Only eligible `independent_human` ratings enter primary reliability. Common AI label suggestions do not create independence. Freeze staffing, assignments, full-corpus versus probability-sample design, and sampling probabilities.
- [ ] G03 — Calibration may clarify development rules but is not independent reliability. Freeze codebook/packets/measurement plan before measured rounds; revisions create new rounds and preserve earlier ratings.
- [ ] G04 — Primary metric is per-binary-label Krippendorff nominal alpha (`1 − Do/De`). With exactly two fixed raters, per-label Cohen kappa may be predeclared instead; never select the metric after results.
- [ ] G05 — Uncertain/unassessed/omitted ratings are missing, not absent. Alpha uses items with at least two determinate human ratings per label. Record item/rater IDs, comparable counts, marginals, missingness, implementation/version, and matrix hash.
- [ ] G06 — Report raw pairwise agreement per label and exact-set agreement per fully assessed field with denominators. With two raters, report positive agreement `2a/(2a+b+c)` and negative agreement `2d/(2d+b+c)`.
- [ ] G07 — Zero expected disagreement/no comparable ratings/zero denominators yield null plus reason, never perfect reliability. Do not pool concatenated sets or prevalence-dominated labels; macro averages must disclose every label and omitted undefined value.
- [ ] G08 — Confirm/change 95% intervals, whole-independence-group bootstrap, 2,000 replicates, a fixed numeric seed, undefined-replicate reporting, and the rule for too few groups. Define the small-group reporting rule and statistic implementation before freeze.
- [ ] G09 — Agreement is descriptive, not label truth; no unsupported reliability threshold is claimed. Complete a missingness table to expose selective abstention.
- [ ] G10 — Seal original ratings/packet/codebook hashes and compute pre-adjudication agreement first. Compare all disputed labels, relevance, deduplication, family relationships, and uncertainty with rule/evidence citations.
- [ ] G11 — Human adjudicator reviews both rationales and pinned evidence/policy. Additional human review resolves unresolved original-pair disagreements; AI never breaks ties. Record conflicts; majority vote alone is insufficient.
- [ ] G12 — Separate upheld/changed/unresolved resolution stores original IDs, reviewer/time, rationale, evidence, and decided labels. Missing evidence leaves uncertainty. No overwrite of independent ratings or reporting adjudicated agreement as reliability.
- [ ] G13 — New adjudication rules version the handbook, identify every affected earlier record, and reannotate in a new round. Any post-result tuning invalidates an unchanged evaluation claim under the contract.

## H. Exposure log

- [ ] H01 — Append-only events identify one human/AI agent, one family, materials, and reading time. Direct, indirect, snippets, prompts, reports, generated summaries, diffs, handoffs, and AI inherited context all count.
- [ ] H02 — Stable pseudonymous actor IDs distinguish type/role and AI provider/model/version/session. Shared model name is not agent identity. Unknown metadata has a reason; controlled human identity mapping stays appropriately separate.
- [ ] H03 — Record code/finding/result/policy/metadata kinds, source/path/pin/hash where known, application IDs, purpose, access mode, event interval, logging time/recorder, and contemporaneous versus retrospective status.
- [ ] H04 — Use honest exact/approximate/date-only/unknown time precision and basis. Do not invent exact read times. Corrections append `corrects_event_id`; absent event means unknown exposure, never unexposed.
- [ ] H05 — Expand multi-family material into linked per-family events; log AI preparation and human consumption separately. Union exposure after merges/ancestry links. Agent/organization/branch/worktree changes do not erase exposure.
- [ ] H06 — Log accidental exposure without further inspection; human review controls eligibility. C01's retrospective report-reading note is exposure context, not screening or labeling.
- [ ] H07 — Reconfirm A03–A04 before any new development screening; do not request or record the externally held selection itself.

## I. Ledger, evidence, funnel, and semantic checks

- [ ] I01 — Draft 2020-12 schema is closed to unknown fields, has stable typed IDs, explicit null/missingness, and empty registries before work. Source statements, artifacts, implementation facts, policy, analysis, and validation are distinct records.
- [ ] I02 — Artifacts carry type, required/availability/not-applicable rationale, immutable revision/hash or gap, correspondence status/evidence, actor/time. “Available” is not established correspondence or proof feasibility.
- [ ] I03 — Attempts record exact commands, tools/versions, artifact/environment pins, interval, exit/resource outcomes, bounds, assumptions, logs/hashes, blockers. Record failed builds, timeouts, unsupported work, cancellations, and errors.
- [ ] I04 — Results are only `VIOLATION`, `VERIFIED_WITHIN_SCOPE`, `UNKNOWN`; no analysis means null. Abstract SAT without concretization stays `UNKNOWN`. `VERIFIED_WITHIN_SCOPE` needs non-vacuity and justified extraction/abstraction; scope/bounds/assumptions always travel with the verdict.
- [ ] I05 — Confirm every evidence grade: `reported` (attributed claim), `source_confirmed` (pinned-source semantic support), `model_confirmed` (supported concrete model), `locally_reproduced` (owned real-proof/original-consumer committed replay), `repair_validated` (faulty/repaired and legitimate controls). Grades attach to claims; contradictions and limits stay visible.
- [ ] I06 — All six stages have status `not_attempted`, `pending`, `met`, `not_met`, actor/time, reasons, rationale, evidence, and missing prerequisites. Later met implies every earlier stage met; pending/failed rows remain in prior denominators.
- [ ] I07 — `screened`: human review of scope/date/candidate and relevance decision or explicit unresolved question. Retrieval alone does not pass.
- [ ] I08 — `relevant`: include decision backed by relation/consumer/policy mismatch; sufficiently specific reported claims can pass without independent confirmation. Date/scope questions still need resolution.
- [ ] I09 — `artifacts_available`: accessible pinned source/constraints/ABI/program/key/verifier/consumer/configuration/policy and owned proof/replay route, with itemized gaps/not-applicable reasons. Inventory alone fails; repair claims additionally need repair artifacts. Confirm this threshold rather than silently dropping hard cases.
- [ ] I10 — `supported`: versioned capability/policy review, bounds/roles/states/effects, supported representations, and established correspondence or reviewed permitted assumptions. Unimplemented behavior/unresolved policy blocks it.
- [ ] I11 — `analyzed`: completed declared analysis attempt with recorded verdict/provenance/resources/logs; completed inconclusive may be `UNKNOWN`. Build failure/timeout alone never passes; verify the result links to the qualifying attempt.
- [ ] I12 — `validated`: independent human semantics and result-specific evidence. Violations need concrete feasibility, real accepted proof, original-consumer committed replay, and state/history feasibility. Bounded guarantees need non-vacuity, extraction/abstraction justification, complete obligations, legitimate controls. `UNKNOWN` never passes; repair adds faulty/repaired controls. Mocks never establish end-to-end claims.
- [ ] I13 — Primary denominator is canonical findings; report monotone six-stage totals, all four status counts, raw hits/unknown, sources, duplicate/unresolved/unreviewed rows, applications/families/groups. Application/family/group stage counts mean “at least one linked finding,” never whole-family success. D1P-11's application denominator is not a finding count.
- [ ] I14 — Enforce cross-record ID/type/reference uniqueness, duplicate acyclicity, cutoffs, and recomputed counts. Check family edges/maps and inherited exposure, not just schema structure.
- [ ] I15 — Check chronological order, precision, frozen search caps/dates, and failure histories; check label evidence, partitions, causal links/attack paths, and required top-level consequence for complete included ratings.
- [ ] I16 — Check distinct human raters, sealed eligible rounds, assignment/packet identities, independence/AI disclosures, and pre-adjudication matrices. Schema-valid actor IDs alone cannot prove independence.
- [ ] I17 — Check actual artifacts, policy, scope, supported features, completed attempts, evidence pins, and result-specific validation. Check every read's exposure event. Standard schema validation cannot establish any of these scientific truths.
- [ ] I18 — Review all 40 `$defs` record types in the schema (one disposition per definition name) against I01–I17, including fields not enforced across records. Confirm null/status/required-field meanings, format assertions, alias handling, and where semantic checks must supplement structural checks.
- [ ] I19 — Review the six illustrative fixture rows and intended rejection paths. Confirm standard validator and dependency pins, runner hash, date/date-time controls, no remote reference fetching, and the recorded schema hash. Validation success is not human approval or freeze.

### Schema definition inventory — one disposition per ID

For each row, confirm every field, type, required/null rule, enum, conditional,
evidence requirement, and cross-record limit in the schema. Read nested
inline objects too; accepting a name alone does not review its definition.

| Disposition ID | Definition |
| --- | --- |
| `I18.time_window` | `time_window` |
| `I18.evidence_ref` | `evidence_ref` |
| `I18.actor` | `actor` |
| `I18.source_class` | `source_class` |
| `I18.search_plan` | `search_plan` |
| `I18.search_run` | `search_run` |
| `I18.source_record` | `source_record` |
| `I18.organization` | `organization` |
| `I18.library` | `library` |
| `I18.family_relation` | `family_relation` |
| `I18.family` | `family` |
| `I18.application` | `application` |
| `I18.exposure_event` | `exposure_event` |
| `I18.boundary` | `boundary` |
| `I18.relevance` | `relevance` |
| `I18.stage` | `stage` |
| `I18.funnel` | `funnel` |
| `I18.artifact` | `artifact` |
| `I18.fact` | `fact` |
| `I18.capability_review` | `capability_review` |
| `I18.attempt` | `attempt` |
| `I18.evidence_grade` | `evidence_grade` |
| `I18.evidence_claim` | `evidence_claim` |
| `I18.check` | `check` |
| `I18.validation` | `validation` |
| `I18.result` | `result` |
| `I18.causes` | `causes` |
| `I18.consequences` | `consequences` |
| `I18.attacker_roles` | `attacker_roles` |
| `I18.rating` | `rating` |
| `I18.adjudication` | `adjudication` |
| `I18.annotation_round` | `annotation_round` |
| `I18.estimate` | `estimate` |
| `I18.raw_agreement` | `raw_agreement` |
| `I18.agreement_label` | `agreement_label` |
| `I18.agreement_report` | `agreement_report` |
| `I18.finding` | `finding` |
| `I18.stage_counts` | `stage_counts` |
| `I18.funnel_summary` | `funnel_summary` |
| `I18.change_event` | `change_event` |

## J. Exact freeze procedure

This is a procedure for humans to execute after review. No version, timestamp,
signature, attestation, or freeze record below is asserted to exist now.
Freeze the taxonomy/search procedure **before new development screening**;
freeze each annotation packet/assignment **before its ratings**. Do not require
yet-undiscovered finding IDs to exist at the earlier search freeze.

1. **Complete the prerequisite outside all worktrees.** Humans choose and
   store reserved families there before any new development screening. A human
   custodian can attest only that the prerequisite is complete, with UTC time
   and custodian ID; do not supply selection identities, location, or hashes.
2. **Resolve every checklist ID.** Record A01–I19, each code ID, D12.01–D12.12,
   and each schema-definition name in `review-decisions-<version>.json` with
   `decision`, `rationale`, `reviewer_ids`, `decided_at_utc`, and
   `replacement_location` (null for confirmed unchanged text). Require two
   human confirmations for changed text and final approval; no pending or
   disputed rule can freeze. Include the content-free prerequisite attestation.
3. **Choose version and actual UTC freeze time.** Draft is `0.1.0`; proposed
   first approved release is `1.0.0`, subject to human decision. Use one
   explicit version throughout the protocol, schema `$id` and
   `schema_version` constant, six fixture envelopes, review decisions, and
   subsequent codebook/round references. Record actual UTC date-time with
   seconds (e.g., via `date -u '+%Y-%m-%dT%H:%M:%SZ'`); never backdate it to
   document authorship. Update draft/frozen wording only after approval.
4. **Finish the development search plan and measurement design.** Record exact
   approved development scope, endpoints/queries/order, window/language,
   retrieval cap/time budget/stops, search owner, human raters/adjudicator,
   sampling/assignment method, metric implementation/version, bootstrap seed,
   and small-group/undefined reporting rules. No reserved selection data.
   Hash final protocol bytes and put that SHA-256 in the search plan; the
   protocol must not embed its own hash or the later manifest hash.
5. **Validate final bytes.** In the pinned environment run the command below
   with a new versioned output name. Require standard meta-schema acceptance,
   three valid accepted, three invalid rejected at their intended paths, four
   format controls passed, and exit 0. Review the cross-record semantic rules
   separately; do not describe the six fixture checks as a complete semantic
   validator. Run local-link/codebook/whitespace checks and record dispositions.
6. **Freeze the payload by SHA-256.** List every approved relative file path
   in `freeze-inputs-<version>.txt`, one per line, including the final protocol,
   schema, checklist, review decisions, development search/measurement plan,
   six fixtures plus manifest, validator runner, requirements, validation
   report, and new machine-readable validation result. Include provenance
   records relied on for reproducibility. Exclude the venv/caches, the input
   list itself, freeze manifest, approval receipt, and all selection material.
   Use the exact script below to snapshot those bytes and produce a manifest
   with version, UTC freeze time, size and SHA-256 for every payload file.
7. **Approve the manifest digest.** Two humans sign/approve a separate
   `freeze-approval-<version>.json` containing version, actual approval UTC
   time, manifest SHA-256, reviewer IDs, and the content-free prerequisite
   attestation. The manifest does not hash itself or its approval receipt;
   this prevents a circular hash. Independently recompute the manifest digest
   and each payload hash before authorizing screening. No automatic commit or
   publication follows. The integrator can reference this digest separately.
8. **Freeze annotation rounds at their own boundary.** After permitted
   retrieval/screening yields development packets, seal each packet hash,
   finding IDs, rater assignments/probabilities, codebook version/hash,
   exposure declarations, and metric plan before independent ratings or tool
   verdict inspection. Later family maps must freeze before evaluation.
9. **Preserve and version changes.** Never overwrite a frozen snapshot,
   manifest, approval receipt, validation result, or sealed ratings. A rule,
   code, schema, date window, or evidence-threshold change gets a new version,
   UTC time, rationale/affected-record list, rerun, manifest, and human
   approval. New review/annotation rounds cannot reuse old independence claims
   after exposure or result-driven tuning. A reformat also changes byte hashes
   and requires a new package identity even if semantics are unchanged.

Run from this lane worktree after setting the approved version. These are
**unexecuted prospective freeze commands**, not evidence that a freeze exists:

```sh
TAXONOMY_VERSION=1.0.0
docs/taxonomy/.venv-validation/bin/python -B docs/taxonomy/validate_ledger.py \
  --output "validation-results-${TAXONOMY_VERSION}.json"
```

After humans create and review `freeze-inputs-<version>.txt`, run:

```sh
python3 - "$TAXONOMY_VERSION" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, re, sys

root = Path('docs/taxonomy').resolve()
version = sys.argv[1]
assert re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version)
paths = (root / f'freeze-inputs-{version}.txt').read_text().splitlines()
assert paths and len(paths) == len(set(paths))
assert all(p and not p.startswith('/') and '..' not in Path(p).parts for p in paths)
assert all(not any(part.startswith('.') for part in Path(p).parts) for p in paths)
assert all(not p.startswith(('freeze-', 'frozen/')) for p in paths)
assert all((root / p).resolve().is_relative_to(root) for p in paths)
assert all((root / p).is_file() and not (root / p).is_symlink() for p in paths)
snapshot = root / 'frozen' / version
snapshot.mkdir(parents=True, exist_ok=False)
files = []
for relative in sorted(paths):
    data = (root / relative).read_bytes()
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as out:
        out.write(data)
    files.append({'path': relative, 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest()})
manifest = {'version': version,
            'frozen_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'hash_algorithm': 'SHA-256', 'files': files}
manifest_path = root / f'freeze-manifest-{version}.json'
with manifest_path.open('x') as out:
    json.dump(manifest, out, indent=2, sort_keys=True)
    out.write('\n')
print(hashlib.sha256(manifest_path.read_bytes()).hexdigest(), manifest_path.name)
PY
```

All selection prerequisites and human sign-offs are procedural gates, not
facts established by these commands. A partially failed freeze command is an
incomplete package; retain its record and use a new version after review.
