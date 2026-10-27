# D1P-C03 — taxonomy and annotation protocol

Version `0.2.0`, 27 October 2026. The protocol design is planner-approved;
`design_frozen`, `reservation_completed`, and `annotation_round_completed`
remain separate recorded states. No state becomes true merely because the
schema validates. This task performs no source traversal, screening, labeling,
reservation draw, build, or security analysis.

The [research contract](../research-contract.md) controls the security
semantics and evidence vocabulary. The live [ledger schema](ledger.schema.json)
specifies future records; schema validity is not evidence validity. Version
`0.1.0`, including its fixtures and validation evidence, is preserved under
[`history/v0.1.0/`](history/v0.1.0/README.md).

## 1. Claim and sampling frame

The sampling frame is public disclosures about **proof-consuming ZK systems**
across languages, chains, proof systems, and application stacks. A candidate
may use Halo2, Circom, Noir, another circuit language, or a generated IR. This
taxonomy scope is intentionally broader than BindCheck's supported analysis
fragment: support affects the tool funnel, never disclosure inclusion.

Payy rollup, WarpToad, 0xbow Privacy Pools, and Aztec v6 epoch rollup are
already-exposed D1P-11 development cases. They may inform codebook development
but are never eligible for reservation or an independence claim.

The strongest permitted descriptive claim is:

> These mechanisms recur across independent families in the sampled public
> disclosures.

Do not infer ecosystem prevalence, incidence, audit quality, or comparative
security. Report the window, source classes, language limits, inaccessible
material, retrieval budgets, unresolved duplicates, and family denominator.

### Source-class traversal

Discovery starts from source indexes, not application names. Traverse these
classes in a frozen order:

1. audit-firm report indexes;
2. contest-platform indexes;
3. advisory databases;
4. the SNARK SoK bug set and 0xPARC zk-bug-tracker as seed collections;
5. primary reports, advisories, contest findings, patches, and cited records
   reached from those indexes.

Mechanism keyword groups supplement this traversal. They may recover records
missed by an index, but may not define the sampling backbone or replace a
source class with application-name-keyed searches. Freeze exact endpoints,
snapshots/revisions where possible, traversal order, keyword groups, date and
language limits, pagination, maximum results, active-time budget, failure
handling, and stopping rules before retrieval. Keep unavailable endpoints and
failed requests in the run log. Never stop after reaching a desired number of
positive findings.

Suggested mechanism groups retain the v0.1 vocabulary:

- proof boundary: `public input`, `public output`, `public signal`,
  `underconstrained`, `verifier`, `verification key`, `program ID`;
- representation: `encoding`, `ordering`, `field`, `range`, `canonical`,
  `truncation`, `padding`, `length`, `prefix`, `activation`;
- effect/context: `recipient`, `amount`, `asset`, `nullifier`, `replay`,
  `domain`, `chain ID`, `state root`, `withdraw`, `mint`, `settlement`,
  `omission`, `batch`, `double spend`, `fee`, `failed transfer`.

Every candidate finding records all applicable discovery routes:
`seed_snark_sok`, `seed_0xparc`, `systematic_source_index`,
`mechanism_keyword_supplement`, and `citation_following`. Seed-derived and
systematically retrieved occurrences are tagged before deduplication; overlap
retains both tags.

### Report completeness and dates

If any percentage of findings from a selected audit report will be reported,
inventory and screen **every finding in that report**, including informative,
low-severity, excluded, borderline, and unresolved candidates. The report is
the completeness unit; selected excerpts cannot supply a percentage
denominator. Contest/advisory sources use their frozen index unit analogously.

The proposed publication window is 1 January 2018 through 27 October 2026,
inclusive in UTC. Use the earliest public primary disclosure date. Preserve
incident, audit, affected revision, patch, and retrieval dates separately.
Missing or disputed dates are unresolved rather than guessed. A later mirror
does not move an older disclosure into the window.

Prefer primary records and immutable revisions. Store publisher, source class,
URI, source/disclosure ID, dates, pinpoint locations, content SHA-256 when
bytes are obtained, retrieval actor/time, and limitations. Snippets can locate
leads but cannot establish proof or consumer semantics.

### Deduplication and counting

Retrieval hits, source documents, candidate findings, canonical findings,
applications, provisional families, and conservative independence groups are
distinct units. Deduplicate reports about the same root cause, affected
boundary, and repair lineage while preserving source aliases and every
discovery route. Split independent missing relations that require independent
repairs. Do not split merely by severity, attacker address, publication,
deployment, or secondary consequence.

Fork manifestations of an inherited defect share a canonical finding with
multiple application manifestations. Independently introduced defects remain
separate even in one family. Unresolved duplicate matches remain explicit;
report their count and sensitivity bounds. A duplicate row never enters the
canonical-finding denominator.

## 2. Inclusion boundary

A candidate is relevant when evidence supports a disagreement between what
the accepted proof relation establishes and what the consumer interprets as
authorized or required. Relevance is independent of tool support and is not a
security verdict. Record `include`, `exclude`, or `unresolved`.

An included boundary argument identifies:

1. the accepted relation `R_v(p,w)`, public statement, and program/key setup;
2. decoding `D_v(p,x)`, verifier argument mapping, guards, and consumer use;
3. independent policy permissions `P`, obligations `O`, and transformations;
4. a possible committed incompatible effect or undischarged obligation; and
5. actor capabilities, reachable state/history, proof feasibility, and gaps.

Pure circuit and pure consumer bugs are excluded unless the accepted relation
and consumer interpretation disagree. Cryptographic soundness failures are
outside the initial sound-relation premise. A reverted effect is not committed.
Unsupported recursion, hashing, aggregation, EVM behavior, or token semantics
creates a tool limitation—not a taxonomy exclusion.

## 3. Family definition and reservation

A family is the connected component of demonstrated application lineage or a
shared application-specific circuit/consumer template. Forks, ports, renames,
repairs, and mutants preserve family membership when ancestry remains.
Generic verifiers, proof stacks, compilers, libraries, or shared organizations
alone do not merge families. Uncertain ancestry is provisionally grouped
conservatively for independence and reservation.

### Name-only enumeration

Before findings are read, agents may prepare a metadata-only enumeration from
source indexes: candidate application name, index identifier, public metadata
needed for grouping, and tool-transfer eligibility. Agents must not open or
summarize findings during this step. If an index places bug descriptions next
to names, the human custodian supplies a sanitized name-only list instead.

Before the draw, the custodian groups known forks and templates into
conservative provisional family groups. The grouped list declares which groups
are newly eligible and unexposed. It records tool-transfer eligibility
(`eligible`, `ineligible`, or `unknown`) separately from taxonomy eligibility.
Predeclared strata must include that eligibility so reservation cannot
accidentally consist entirely of unsupported systems.

### Private family draw

The default is to reserve half of the newly eligible, unexposed family groups
within each predeclared stratum. The grouped input fixes either ceiling or
floor rounding before the draw; `ceil_per_stratum` is recommended. The human
custodian runs [`reserve_families.py`](../../scripts/taxonomy/reserve_families.py)
in a plain terminal outside every agent session. The script:

1. reads the frozen grouped name-only list;
2. uses a private random seed and nonce;
3. selects the fixed count within each stratum;
4. writes a manifest containing the selection, seed, and nonce only to a
   human-chosen path outside every Git worktree; and
5. prints only `SHA256(nonce || canonical_selection_manifest)`.

**A04 (v0.2.0 amendment):** the repository stores only the 64-hex commitment
and a custodian attestation
that the draw followed the frozen rule, both recorded before development
screening. It stores no reserved membership, selection path, nonce, seed, or
opening. The commitment demonstrates consistency with a later opening; it
does **not** demonstrate randomness or when the draw occurred.

The essential protection is operational: no reserved family's code, findings,
results, snippets, summaries, or indirect context may enter development.
Agents screen only non-reserved families. Accidental exposure disqualifies the
affected group from reserved evaluation. Later family merges propagate the
union of exposure: if any merged component was exposed, the merged family is
exposed and cannot regain reserved status through renaming or regrouping.

## 4. Annotation codebook

The unit is one canonical finding and its pinned affected boundary. Cause,
consequence, and attacker role are independent multi-label fields. Each field
partitions labels into `present`, `absent`, and `uncertain`; `unassessed` uses
three empty arrays. `complete` covers every label exactly once as present or
absent. Empty never means absent. Every present or uncertain label needs a
rationale and evidence pinpoint. “Other” needs a mechanism description.

### Cause labels

| Code | Rule |
| --- | --- |
| `C_RELATION_GAP` | Accepted constraints omit a dependency needed by consumer interpretation. |
| `C_FIELD_MAPPING` | Producer/verifier/consumer disagree on identity, order, slice, or forwarded value. |
| `C_REPRESENTATION` | Field/integer/byte range, width, sign, canonicality, or encoding differs. |
| `C_ACTIVATION_EXTENT` | Count, prefix, padding, tag, length, or activation differs. |
| `C_CONTEXT_IDENTITY` | Domain, app, actor, asset, state, or version is not bound to the executing context. |
| `C_VERIFICATION_CONFIG` | Sound relation selection/key/configuration is interpreted as another relation. |
| `C_OCCURRENCE_ACCOUNTING` | Identity, multiplicity, or single-use accounting is lost. |
| `C_DISCHARGE_TRANSFORMATION` | Selection, aggregation, split, cancellation, or pending handling violates policy. |
| `C_OTHER_BINDING` | Another evidenced binding cause; explanation and human review required. |

### Consequence labels

| Code | Rule |
| --- | --- |
| `K_AUTHORIZATION` | A committed protected effect has no compatible permission. |
| `K_COVERAGE` | A required obligation lacks discharge, valid cancellation, or permitted pending state. |
| `K_MISDIRECTED` | Beneficiary, asset, domain, or semantic identity is wrong. |
| `K_QUANTITY` | Quantity, split, or total is incompatible. |
| `K_DUPLICATE_REPLAY` | An occurrence or permission is reused beyond allowed multiplicity. |
| `K_OMITTED_DISCHARGE` | An accepted required occurrence is skipped or silently dropped. |
| `K_STATE_INCONSISTENCY` | Protected committed state disagrees with the accepted transition. |
| `K_OTHER_EFFECT` | Another evidenced authorization/coverage consequence. |

Every complete included finding has `K_AUTHORIZATION`, `K_COVERAGE`, or both.
Severity, privacy, loss, and liveness may be retained as source claims but do
not replace the top-level properties.

### Attacker-role labels

| Code | Rule |
| --- | --- |
| `A_PUBLIC_CALLER` | Public caller can realize the path with obtainable inputs. |
| `A_WITNESS_PROVER` | Witness or proof construction control is required. |
| `A_RELAYER` | Relaying/processing control or inputs are required. |
| `A_REGISTERED_PROVER` | Admission to a configured prover set is required. |
| `A_OPERATOR_ORDERER` | Sequencing, batching, or ordering authority is required. |
| `A_PRIVILEGED_CONFIGURATOR` | Admin, upgrade, key, or configuration authority is required. |
| `A_OTHER_ROLE` | Another explicitly evidenced capability. |

Record minimum sufficient roles and use attack paths to distinguish
conjunctions from alternatives. Unknown capabilities remain uncertain.

## 5. Pilot, agreement, and adjudication

The development pilot contains exactly 20 packets from several non-reserved
families, including likely includes, borderline/unresolved candidates, and
exclusions:

- packets 1–4: one jointly discussed, **unscored** calibration round;
- packets 5–20: 16 fresh packets independently labeled by exactly two humans.

An annotation packet contains only frozen public disclosure and policy
materials. Annotators receive no BindCheck output, tool-funnel status, E4
replay result, AI-suggested label, or other annotator's rating. Two human
annotators work independently; one distinct human adjudicator resolves the
sealed disagreements afterward. AI systems are never raters or tie-breakers.

Predeclare Krippendorff nominal alpha per binary label or, for exactly two
fixed raters, Cohen kappa per label. Report for every cause, consequence, and
role: comparable denominator, positive/negative counts, raw agreement,
coefficient, missing/null count, and interval. Also report agreement for the
three-way relevance decision `include`/`exclude`/`unresolved`. Exact-set field
agreement and completion/missingness tables are secondary summaries.

Uncertain, unassessed, and omitted are missing rather than absent. If chance
variance, comparable observations, or an interval denominator is inadequate,
report `null` and call the interval uninformative explicitly. Do not substitute
a perfect value. If bootstrapping, resample whole family independence groups
with the predeclared seed and report undefined replicates.

Seal original ratings before agreement or adjudication. The adjudicator cites
the rule and evidence and records upheld, changed, or unresolved without
overwriting original ratings. Any codebook change increments its version. The
next reliability round uses fresh packets; previously discussed or labeled
packets never become a fresh independent round.

## 6. Approval and completion states

Design approval consists of typed AI-planner review records naming both actual
planner identities and the design items each approved. It is not a per-item
human checklist. The ledger contains no `approved_by_human_id` for design.
`design_frozen` may become true only when the protocol/search plan hashes,
budgets/endpoints, and two approving AI-planner records are present.

Human-only empirical controls are limited to the short
[sign-off sheet](review-checklist.md):

- staffing exactly two annotators and one adjudicator;
- conducting and attesting the private family reservation draw; and
- conducting the calibration, independent, and adjudication rounds.

`reservation_completed` requires the salted commitment and custodian
attestation, but no membership data. `annotation_round_completed` requires a
completed round record; it is independent of the other two states. Never
fabricate a human name, signature, timestamp, or attestation to satisfy schema
validation. The [planner approval record](planner-approval-v0.2.0.json) names
Codex Astra 6 and Claude Opus 5.5 as the two approving AI planners for D01–D06;
it makes no human claim.

Planner approval alone does not freeze empirical retrieval. D1P-C04 drafts a
non-synthetic [search plan](search-plan-v0.2.0.json) fixing endpoint tiers and
snapshot handling, seed IDs, English-language coverage, traversal order,
supplemental keyword groups, pagination, and stopping rules. Its three numeric
choices—results per endpoint, total active-time budget, and consecutive
irrelevant-page stop count—remain `PROPOSED`. The exact remaining design-freeze
step is planner approval of those values; until then, `design_frozen` is false
and `design_frozen_at` is null.

Store both protocol and search-plan hashes in `protocol_states`.
`search_plan_sha256` is the SHA-256 of the canonical UTF-8 JSON `search_plan`
payload (sorted keys, no insignificant whitespace), excluding its envelope so
the digest is not self-referential. Reservation and annotation completion
remain false.

## 7. Exposure accounting

Maintain an append-only log of each human or AI actor that reads a family's
code, findings, results, policy, metadata, snippets, prompts, diffs, summaries,
or inherited context. Record direct/indirect access, bounded material,
revision/hash when known, purpose, time precision, recorder, and corrections.
No event found means unknown exposure. AI provider/model/session metadata is
recorded when known and left null with a reason when not known.

Repository exposure events concern development families only. Never log or
infer reserved family membership. Preserve the v0.1 provenance that D1P-11
gave the authoring agent indirect finding/result and application-mapping
context for its four already-exposed development cases. A family merge carries
forward the union of exposure histories.

## 8. Separate disclosure and tool funnels

Human annotation produces disclosure counts only:

`candidate → screened → include / exclude / unresolved`.

Tool feasibility is a separate conditional funnel for relevant findings:

`artifacts available → supported → analyzed → validated`.

Never combine these into one attrition percentage. A Halo2 or Circom finding
may count as a disclosure even when BindCheck cannot ingest it. Annotation
never depends on tool execution or E4 replay. Tool support, timeout, build
failure, or `UNKNOWN` can explain tool attrition but cannot revise a human
disclosure label.

Each stage records `not_attempted`, `pending`, `met`, or `not_met`, actor/time,
reason, evidence, and prerequisites. Tool stages are monotone among themselves.
`validated` requires a human semantic review and result-specific evidence;
`UNKNOWN` never passes. Report raw retrieval hits, unique sources, duplicate
rows, canonical candidates, disclosure decisions, and tool-stage counts with
their own denominators.

## 9. Validation and handoff

Schema validation uses JSON Schema draft 2020-12 with date/date-time format
assertion. Synthetic fixtures contain no corpus findings or labels. Beyond
schema checks, a populated ledger must resolve references, enforce unique IDs,
recompute counts, validate family/exposure propagation, verify report-level
completeness and frozen retrieval budgets, check label partitions and sealed
independent ratings, and confirm every tool-stage prerequisite.

The [validation report](validation-report.md) and machine-readable results
record the v0.2.0 run. The integrator, not this lane, owns canonical README and
project-status updates. No commit, push, or merge is part of D1P-C03.
