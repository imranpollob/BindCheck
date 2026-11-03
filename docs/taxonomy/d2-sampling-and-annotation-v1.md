# D2 taxonomy sampling and annotation procedure v1

**Codebook:** frozen v0.3.0  
**Empirical status:** ready for human/custodian planning; no corpus draw, packet,
rating, or adjudication is complete

## 1. Corpus construction

The coordinator starts from the frozen v0.2.0 source-class traversal, or a
prospectively reviewed amendment made before reading new findings. Audit-firm,
contest, advisory, seed-collection, and citation routes retain their own
coverage and failure logs. Application-name searches and the 0xPARC seed alone
cannot define the corpus. Do not stop when a target number of relevant items
or mechanisms is reached.

Inventory every finding in a selected report/index completeness unit. Preserve
inaccessible sources, screening failures, uncertain dates, and duplicate
candidates. Deduplicate to canonical findings by root mechanism, affected
boundary, and repair lineage; group forks/templates conservatively into
families before sampling. Exposure propagates across merged families.

For every candidate chosen for packet construction, a coordinator prepares
the blank primary-evidence template. A packet may record that primary evidence
is missing; it must not fill the gap with an aggregator summary. Such an item
remains eligible to demonstrate `unresolved` handling rather than silently
leaving the denominator.

## 2. Primary scored sample

The sampling unit is a conservative family. Select at most one canonical
finding from each sampled family for the primary agreement analysis. Freeze,
before annotation:

- the complete candidate/family manifest and hashes;
- source-class and any non-outcome strata;
- sample size or census rule and its budget rationale;
- randomization method, seed custody, draw record, and replacement rule;
- inaccessible/withdrawn packet handling;
- calibration packets, which are excluded from scoring; and
- the exact codebook, packet, form, and analysis-script hashes.

Sampling must not use an expected category, analyzer support, E-grade,
severity, or desired agreement level as a selection or replacement criterion.
If the completed frame is too small for a planned sample, use the frozen
census/fallback rule and report the smaller denominator; do not add exposed
pilot items as though fresh.

The 17 Lane-X human-included findings and their 27-entry seed sheet are
development material. Re-annotation can only be a separately labeled
`exposed_pilot` study. A primary `fresh_independent` round requires packets
fresh to both raters. Rater-specific exposure is recorded, not assumed from
family-level logs.

## 3. Packet assembly and blinding

The coordinator—not either rater—assembles packets from pinned primary
material. Each packet separates:

1. relation/configuration evidence;
2. public-statement decoding and consumer-use evidence;
3. policy/permission/obligation evidence;
4. actor, reachability, proof-feasibility, and committed-effect evidence;
5. repair and duplicate-lineage evidence; and
6. missing, conflicting, or inaccessible evidence.

Include exact source IDs, immutable revisions or hashes, pinpoints, retrieval
provenance, and permitted excerpts/links. Packet text may quote the primary
source but must not summarize toward a category.

Packets and forms contain no BindCheck warning, analyzer prediction,
AI-suggested label, prior human label, other-rater judgment, adjudication,
taxonomy frequency, or E-level validation result. If an E-level fact is
inseparable from the original disclosure, include the source passage without
the project's later grade. A coordinator checklist certifies these exclusions
before packet release.

## 4. Independent rating

Exactly two humans rate the same frozen packets independently. Each records:

- actual prior exposure to the family/material;
- relevance: `include`, `exclude`, or `unresolved`;
- every cause, consequence, and role category as `present`, `absent`,
  `uncertain`, or `unassessed`;
- evidence pinpoints and rationale for every non-`unassessed` decision; and
- minimum-sufficient role conjunctions/alternatives in prose.

No discussion occurs after packet release until both rating sets are sealed.
Questions go to the coordinator, who sends the same clarification to both
raters and appends it to every affected packet. A clarification that changes a
rule increments the codebook version and makes that round developmental.

The coordinator hashes the two original rating files separately and creates a
combined agreement input containing only those ratings. AI systems may check
format or run the deterministic script but are not raters or tie-breakers.

## 5. Agreement analysis

Run:

```sh
PYTHONPATH=src python3 scripts/d2_taxonomy_agreement.py \
  combined-original-ratings.json --output agreement.json
```

The primary relevance statistic is three-category Cohen's kappa. The design
has exactly two fixed human raters, so Krippendorff alpha is not substituted.
Each multilabel category is a separate binary present/absent decision with
Cohen's kappa. Report raw agreement, both marginal positive prevalences,
positive and negative agreement, comparable denominator, and missing count
for every label. These diagnostics make low-prevalence and kappa paradoxes
visible; they are not alternative coefficients from which to choose a
favorable result.

`uncertain`, `unassessed`, null, and omitted values are missing, never absent.
Kappa is `null` when there are no comparable pairs or no chance variance.
Raw exact-set agreement per complete axis is secondary. Do not pool categories
into a macro kappa.

This preparation does not compute confidence intervals. The sample size and
number of independent families are unknown, and multiple findings within a
family would invalidate item bootstrap assumptions. If intervals are desired,
a pre-annotation amendment must fix a family-cluster resampling or analytic
design, seed, minimum independent-unit rule, treatment of undefined
replicates, and interpretation. Otherwise report point estimates and exact
denominators only.

## 6. Disagreement and adjudication

Seal agreement output before adjudication. A distinct third human receives
the packets, codebook, and both original ratings. For every disagreement the
adjudicator cites the governing rule and primary-evidence pinpoint, then
appends one of `rater_1_upheld`, `rater_2_upheld`, `new_resolution`, or
`unresolved`. Original ratings are immutable.

Report pre-adjudication agreement and post-adjudication distributions
separately. Adjudication cannot improve the reported agreement coefficient.
If adjudication exposes a codebook defect, preserve the round, increment the
codebook, and use fresh packets for another reliability round.

## 7. Human dependencies and permitted claims

Required human work remains:

- custodian/coordinator completion of the source frame, family grouping,
  exposure-safe draw, and packet blinding;
- two independent human raters with disclosed prior exposure;
- a distinct human adjudicator; and
- author inspection of packets, code, labels, citations, and claims.

Until that work exists, the taxonomy contribution is unvalidated. Agreement
would measure reproducibility on the sampled disclosure packets, not truth,
security, tool accuracy, or ecosystem prevalence. The project may report the
exposed pilot as codebook-development history only.
