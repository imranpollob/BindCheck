# D2 Step 3 advisor summary and paper outline

**Version:** D2-03-v1, 2 November 2026

**Purpose:** corrected status note and writing scaffold; not manuscript text and
not a final research result

## Corrected advisor summary

BindCheck now has a content-sealed integrated **development** interface over
the corrected static/conditional-extent analysis and the typed role analysis.
On the 30 exposed mutants, D2-01 records 17 detected, 13 unsupported, 0 misses,
26 warning objects, and 23 associated warning objects. Every result is E1. The
zero-miss field means only that no predeclared supported target in this exposed
benchmark lacked its required association; it is not a precision, recall,
security, or population result.

The corrected successor ablation differs materially from the historical
D1P-41 preliminary run. D1P-41 remains 6/8 for both the unjoined union and full
arm under its original assumptions. D1P-43, on seven supported exposed
positives, records producer 3/7, consumer 2/7, union 5/7, and full 7/7, plus one
`UNKNOWN` positive and one matching control. The two additional full-arm
detections are typed state/role relationship examples. This is useful
motivation for a prospective comparison, but it is not a novelty result: the
examples are known, the role atoms are source-derived, external comparators did
not run, and no proof or replay was part of the ablation.

Payy must be described in three separate layers. D1P-42 resolves the exact
1,005-to-1,003 mapping for the earlier/check-added pair, and D2-01 reports an
E1 `R-EXTENT` diagnostic on the earlier revision. The 12 Payy benchmark mutants
remain unsupported. T15–T19 provide historical E4 evidence for the disclosed
earlier tail mechanism, but that chain was constructed after disclosure and
does not establish automatic discovery or validate every current warning.

The present supportable contribution is implementation-level: an integrated,
provenance-carrying E1 diagnostic interface that can associate producer facts
with modeled consumer guards, state identities, and effects on bounded exposed
cases. The proposed paper contribution remains automatic artifact-derived
discovery plus automatic E4 validation of a relational authorization mismatch,
distinguished from fair baselines and transferred to a frozen held-out family.
That proposed contribution is unresolved.

Closest-work positioning also remains open. ZKAP directly overlaps unused
public-input detection; CIVER overlaps modular property verification and rich
specifications; CCC-Check overlaps semantic computation/constraint
consistency and supports a Noir frontend in its paper; SmartAxe is a close
cross-program semantic-join analogue; and ELSA's official abstract reports a
ZKP-smart-contract evaluation, but the accessible primary material is
insufficient to determine its exact circuit/consumer scope. A “first” or “no
prior tool” claim is not currently authorized.

The next decision experiment should therefore be small and discriminating:
freeze relationship mutations and semantics-preserving renamings, compare full
BindCheck with producer-only, consumer-only, strongest simple
union/composition, and applicable closest-tool or same-policy arms under equal
information, and measure manual specification/adapter effort. Only after that
comparison should the project decide whether compiler-backed object/context
identity and a true relational authorization property are warranted.

The research verdict remains `UNKNOWN`. No current evidence establishes the
four-part capability gate, generality, security, or submission readiness.

## Proposed paper outline

This outline keeps existing evidence usable without turning development
observations into final claims.

### 1. Introduction: the relational decision

- State that a verifier establishes a circuit relation and a consumer commits
  effects.
- Use the qualified thesis: **some** authorization judgments require relating
  producer and consumer facts.
- Give Payy as a known historical mechanism and WarpToad variants as injected
  development cases.
- List candidate contributions in future/conditional form until Gate A/B/C.
- Do not claim that every mismatch is invisible to one-sided analysis.

### 2. System model and claim semantics

- Define `R_v`, decoding, consumer transition `T`, specification `sigma`, and
  `P`/`O`/`E`.
- Define authorization as compatibility of complete permission/effect records,
  not occurrence or role-name equality.
- Keep evidence grades E0–E4 separate from the three verdicts.
- Define prior exposure classes and the non-circular specification boundary.

### 3. Current implementation and its boundary

- Present the integrated D2 interface, component support states, provenance,
  and stable/source warning IDs.
- Separate extracted implementation facts from analyst/policy/role facts.
- Explain `R-BIND`, `R-EXTENT`, consumer rules, and `R-ROLE` as E1 diagnostic
  rules.
- Label source-derived role inference and the missing minimal causal
  authorization slice as limitations.
- Preserve historical tool versions where historical experiments use them.

### 4. Candidate method extension

- State compiler-backed semantic object/context identity as proposed, not
  implemented.
- State relational authorization as proposed, not equivalent to current
  `effect-authorization` warning labels.
- Give preservation/fail-closed conditions and transformation controls.
- Explain what information each rule may use to avoid circular labels.

### 5. Evaluation questions and protocol

- RQ1: extraction and mapping fidelity.
- RQ2: artifact-derived obligation and diagnostic discovery, with manual inputs
  counted.
- RQ3: automatic E4 validation and causal contrasts.
- RQ4: fair comparative capability and frozen held-out transfer.
- RQ5: efficiency only as a secondary question.
- Define generic/default, same-policy, simple-composition, and closest-tool
  arms before output.

### 6. Development evidence, versioned

- Table A: D1P-34, D1P-42, D2-01 benchmark rows as three versions.
- Table B: D1P-41 historical preliminary versus D1P-43 corrected successor.
- Table C: exact Payy pair versus 12 unsupported Payy mutants.
- Table D: historical E4 mechanisms and TE06 grades, explicitly not current
  validation.
- Report 49 reconciliation rows as four overlapping datasets, not 49 cases.

### 7. Prospective distinguishing comparison

- Pair a fixed producer with consumers that change effect relevance.
- Include state/domain/role swaps where both sides still locally use the word.
- Include semantics-preserving renamings to detect name-heuristic dependence.
- Run producer-only, consumer-only, union, strongest composition, applicable
  external tools, and same-policy arms.
- Report native/adapted status, information budget, effort, irrelevant warnings,
  unsupported/unresolved outcomes, and E1-to-E4 grades.

### 8. Independent transfer

- Describe D1P-33/D1P-36 only as applicability/blocker evidence.
- Keep the held-out procedure and family unit explicit.
- Do not infer transfer until a frozen supported family is analyzed without a
  defect-specific rule.

### 9. Taxonomy

- Keep descriptive taxonomy evidence separate from tool capability.
- State single-annotator and AI-assistance limits.
- Defer recurrence/prevalence language until the independent annotation and
  sampling design support it.

### 10. Related work

- Organize by producer semantics, computation/constraint consistency,
  contract analysis, cross-program semantic joins, and neuro-symbolic
  ensembles.
- Put actual overlap, assumptions, access status, and the distinguishing test in
  one table.
- Include ZKAP, CIVER, CCC-Check, SmartAxe, and ELSA.
- Replace absence language with scoped inspected-source language.

### 11. Limitations, ethics, and artifact

- Bounded language/opcode/consumer subset.
- Exposed development data and known labels.
- Source-name role inference.
- No current automatic E4 result, baseline comparison, or supported transfer.
- Owned-local execution, no live-chain action, and disclosure procedure.
- Versioned manifests, raw evidence boundaries, and AI-assistance disclosure.

### 12. Conclusion

- Before the gates: summarize the method under investigation and the next
  discriminating experiment, not a final novelty or capability result.
- After the gates: derive the conclusion mechanically from the claim ledger;
  failed or tied gates remain publishable negative evidence but do not become a
  success claim.

## Unsupported-claim annotation tags

Use these tags during the manuscript rewrite. They are editorial markers, not
new evidence classes.

| Tag | Meaning | Example from D1P-P07 | Required resolution |
|---|---|---|---|
| `[STALE-VERSION]` | Later immutable evidence supersedes the current-state wording without rewriting history. | Payy static `UNKNOWN`; role work pending; 11/19/0 as current. | Add versioned D1P-42/D1P-43/D2-01 rows. |
| `[HISTORICAL-ONLY]` | Correct result, but only for an earlier tool or evidence chain. | D1P-41 6/8; T15–T19 E4; TE06 ledger. | Name version, exposure, and non-transfer limit adjacent to the statement. |
| `[AUTHORIZATION-OVERREACH]` | E1 association or role/amount match is described as authorization. | “effect at risk”; `effect-authorization` read as a policy verdict. | Use diagnostic wording or supply policy-reviewed E4 evidence. |
| `[EVIDENCE-UPGRADE]` | Warning/model/proof is described at a higher grade. | A role warning described as an unauthorized effect. | Restore exact E1/E2/E3/E4 grade and verdict. |
| `[NEGATIVE-ABSENCE]` | Bounded search is turned into a literature-wide absence claim. | “No verified prior tool does that.” | Use inspected-source scope; resolve ELSA/full artifacts; run comparisons. |
| `[EXPOSURE-LEAK]` | Known development cases imply discovery, transfer, or generality. | Seven exposed role targets used as capability evidence. | State exposure; require frozen held-out family. |
| `[DENOMINATOR-MIX]` | Different versions, unsupported cases, controls, warnings, attempts, or projects are pooled. | 6/8 and 7/7 discussed as one ablation; 49 rows implied as 49 cases. | Give the exact dataset composition and version. |
| `[FRONTEND-AS-METHOD]` | Native incompatibility is treated as an algorithmic miss. | Circom-only tool on Noir input. | Mark unsupported; predeclare and charge a fair adaptation if needed. |
| `[FINAL-RESULTS]` | Abstract/conclusion asserts novelty, capability, security, or generality before the gates. | “We therefore claim novelty only for the automated join.” | Replace with candidate contribution and test plan. |

## Go/no-go writing rule

Do not draft a final-results abstract until the claim ledger has a supported
entry for the exact proposed contribution with a sealed result, an exposure
class, a fair-comparison record, and an evidence grade. Until then, a workshop,
thesis, or advisor draft should be framed as a research design plus versioned
development evidence.
