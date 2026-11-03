# D2 taxonomy codebook v0.3.0

**Frozen:** 2 November 2026, before any new annotation round  
**Status:** preparation only; no human labels created  
**Machine control:** `protocols/d2/d2-04-taxonomy-preparation-v1.json`

This revision resolves ambiguities exposed by the Lane-X seed pilot. It does
not relabel that pilot. The taxonomy unit is one canonical finding: one root
mechanism, affected producer-to-consumer boundary, and repair lineage within a
conservative application family. Duplicate reports and fork manifestations
remain aliases. Distinct missing relations requiring distinct repairs are
separate findings.

## 1. Relevance decision

Annotators choose exactly one of `include`, `exclude`, or `unresolved`.

`include` requires primary evidence for all of the following:

1. the accepted sound relation or selected verification configuration;
2. public-statement decoding and the proof consumer's interpretation;
3. an independently stated authorization or coverage policy; and
4. a possible committed incompatible protected effect or undischarged required
   obligation under stated actor/state/proof-feasibility conditions.

The evidence need not already be E4, but a secondary aggregator's summary
alone cannot establish these elements.

`exclude` requires positive evidence that the item is outside this boundary:
a cryptographic soundness or setup break, privacy-only issue, pure producer or
pure consumer bug without a cross-layer disagreement, or availability/DoS
only with no accepted transition and no committed incompatible effect or
undischarged obligation. A reverted effect is not committed.

`unresolved` is mandatory when primary evidence, relation/configuration,
decoding, policy, accepted-proof feasibility, reachability, or committed
effect evidence is absent, inaccessible, conflicting, or ambiguous. Missing
evidence is never converted to `exclude`, and `unresolved` is never safety
evidence.

Tool support is not a relevance criterion. Unsupported Circom, Halo2, Noir,
recursion, hashing, or EVM behavior belongs in the separate tool funnel.

## 2. Rating state and evidence rule

Cause, consequence, and role are independent multilabel axes. Every category
is marked `present`, `absent`, `uncertain`, or `unassessed`.

- `present`: cited primary evidence meets the definition.
- `absent`: cited primary evidence contradicts or rules out the definition.
- `uncertain`: relevant evidence exists but does not decide the definition.
- `unassessed`: the rater did not evaluate the definition.

Null, omitted, `uncertain`, and `unassessed` values are missing in agreement
analysis, never negative. Every `present`, `absent`, or `uncertain` decision
must cite a packet pinpoint and a short rationale. `C_OTHER_BINDING`,
`K_OTHER_EFFECT`, and `A_OTHER_ROLE` also require a mechanism description and
a codebook-review flag.

## 3. Cause axis

| Code | Revised rule |
|---|---|
| `C_RELATION_GAP` | The accepted relation omits a needed dependency not fully described by a more specific code below. |
| `C_FIELD_MAPPING` | The relation, verifier call, or consumer disagrees on the identity, order, slice, or actual value forwarded across the boundary. |
| `C_REPRESENTATION` | Field/integer/byte range, width, sign, canonicality, or encoding differs. A non-binary selector is representation, even if its downstream manifestation is a wrong branch. |
| `C_ACTIVATION_EXTENT` | A separately misbound count, prefix, padding, tag, length, or activation relation changes which occurrences are active. |
| `C_CONTEXT_IDENTITY` | Domain, application, actor, asset, state, or version is not bound to the executing context. |
| `C_VERIFICATION_CONFIG` | A sound relation/key/program/configuration is selected or interpreted as a different relation. Cryptographic verifier unsoundness remains excluded. |
| `C_OCCURRENCE_ACCOUNTING` | The boundary itself loses identity, multiplicity, or single-use accounting. Replay as a downstream effect alone does not earn this cause. |
| `C_DISCHARGE_TRANSFORMATION` | Selection, aggregation, split, cancellation, transformation, or pending handling violates the reviewed policy. |
| `C_OTHER_BINDING` | Another evidenced root binding mechanism; description and human codebook review required. |

### Cause/consequence and overlap rules

Annotate the root boundary mechanism, not the exploit manifestation. A forged
path, duplicate withdrawal, wrong tally, or misdirected transfer is ordinarily
a consequence. Multiple cause labels are permitted only when primary evidence
shows distinct mechanisms, not when several labels paraphrase one omission.

For one mechanism, apply this precedence:

1. use the specific mapping, representation, activation, context,
   verification-configuration, occurrence, or transformation code;
2. do not additionally mark `C_RELATION_GAP` for that same relation; and
3. use `C_RELATION_GAP` only for an otherwise-unclassified dependency omission.

Two common boundaries are fixed explicitly:

- an invalid-range selector that later chooses a wrong path is
  `C_REPRESENTATION`, not also `C_FIELD_MAPPING` or
  `C_ACTIVATION_EXTENT`, unless a second mapping/activation relation is
  independently wrong; and
- malleability that produces several claim identifiers is labeled by its
  evidenced relation or representation cause; `C_OCCURRENCE_ACCOUNTING`
  applies only if multiplicity/single-use accounting is itself lost at the
  producer-consumer boundary.

## 4. Consequence axis

| Code | Rule |
|---|---|
| `K_AUTHORIZATION` | A committed protected effect lacks a compatible permission. |
| `K_COVERAGE` | A required obligation lacks discharge, valid cancellation, or permitted pending state. |
| `K_MISDIRECTED` | Beneficiary, asset, domain, or semantic identity is wrong. |
| `K_QUANTITY` | Quantity, split, fee, or total is incompatible. |
| `K_DUPLICATE_REPLAY` | An occurrence or permission is reused beyond allowed multiplicity. |
| `K_OMITTED_DISCHARGE` | An accepted required occurrence is skipped or silently dropped. |
| `K_STATE_INCONSISTENCY` | Protected committed state disagrees with the accepted transition. |
| `K_OTHER_EFFECT` | Another evidenced authorization/coverage consequence; description and review required. |

Every complete included finding has `K_AUTHORIZATION`, `K_COVERAGE`, or both.
Secondary codes describe the concrete committed effect or obligation; they do
not replace the top-level property. Severity, monetary loss, privacy, and
liveness may be retained as source claims but are not consequence categories.

## 5. Minimum-sufficient attacker roles

| Code | Rule |
|---|---|
| `A_PUBLIC_CALLER` | A public caller can realize the path with obtainable inputs. |
| `A_WITNESS_PROVER` | Witness/proof construction control is required. |
| `A_RELAYER` | Relaying or processing control/inputs are required. |
| `A_REGISTERED_PROVER` | Admission to a configured prover set is required. |
| `A_OPERATOR_ORDERER` | Sequencing, batching, or ordering authority is required. |
| `A_PRIVILEGED_CONFIGURATOR` | Admin, upgrade, key, or configuration authority is required. |
| `A_OTHER_ROLE` | Another evidenced capability; description and review required. |

Record only minimum sufficient roles. The attack-path field distinguishes role
conjunctions from alternatives. Unevidenced capability is `uncertain`, not
`absent`.

## 6. Exposure and claim boundary

Every packet records family-level exposure before sampling and rater-specific
prior exposure before annotation. Exposure propagates through family merges.
The 17 Lane-X human-included entries, their 27-entry seed sheet, AI summaries,
and all 23 families read in that lane are exposed development material. A new
human rating cannot make them fresh or held out.

Agreement measures reproducibility, not truth. The taxonomy contribution
remains a candidate until a fresh, appropriately sampled corpus receives
independent human ratings under this frozen codebook.
