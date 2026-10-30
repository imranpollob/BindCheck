# Taxonomy v1 — human vs AI-suggested labels

Date: 2026-10-30. Human annotator: the repository author, labeling blind on
`v1-blind-labels.md`. The sheet had the AI labels and include/exclude tags
removed, but kept the AI-written one-line summaries. AI suggestions:
`v1-corpus.md` (Lane X). This measures agreement with an AI suggester, **not
inter-annotator agreement**. There is one human annotator, and AI output is
not independent annotation.

## Results

| Measure | Agreement | Cohen's κ |
| --- | --- | --- |
| Include / exclude (27 entries) | 25/27 = 92.6% | 0.83 |
| Cause label, entries both included (17) | 9/17 = 52.9% | 0.35 |

Include counts: AI 19, human 17. Every human-included entry was also
AI-included.

Human label distribution: C_REPRESENTATION 10, C_RELATION_GAP 6,
C_FIELD_MAPPING 1. AI distribution on the same 17: C_REPRESENTATION 5,
C_RELATION_GAP 5, C_ACTIVATION_EXTENT 3, C_OCCURRENCE_ACCOUNTING 2,
C_FIELD_MAPPING 1, C_CONTEXT_IDENTITY 1.

## Disagreements

| ID | AI | Human | Human rationale (abridged) |
| --- | --- | --- | --- |
| CF-04 | include, C_REPRESENTATION | exclude | Unusable groups only; availability, no wrong effect |
| CF-05 | include, C_REPRESENTATION | exclude | Audit describes failed leaf removal, not an accepted unauthorized proof |
| CF-03 | C_RELATION_GAP | C_REPRESENTATION | Missing coordinate range enforcement |
| CF-06 | C_OCCURRENCE_ACCOUNTING | C_REPRESENTATION | Unbounded index yields distinct nullifiers |
| CF-08 | C_OCCURRENCE_ACCOUNTING | C_RELATION_GAP | Signature determinism omitted |
| CF-10 | C_ACTIVATION_EXTENT | C_RELATION_GAP | Message-to-leaf binding missing |
| CF-21 | C_FIELD_MAPPING | C_REPRESENTATION | Path selector lacks binary range |
| CF-22 | C_CONTEXT_IDENTITY | C_FIELD_MAPPING | CTX zero aliases slots |
| CF-23 | C_ACTIVATION_EXTENT | C_REPRESENTATION | Sign selector not restricted to 0/1 |
| CF-27 | C_ACTIVATION_EXTENT | C_REPRESENTATION | Byte collides with start sentinel |

## Interpretation and threats

1. **Systematic, not random.** The human labeled the root mechanism, such as
   a missing range check or a missing constraint. The AI often labeled the
   downstream manifestation, such as duplicate nullifiers or branch
   activation. Six of the eight label disagreements move to
   C_REPRESENTATION or C_RELATION_GAP.
2. **Instruction-induced precedence.** The labeling guide the annotator
   received (planner session, 2026-10-30) listed the cause labels as an
   ordered decision list with C_REPRESENTATION first and C_RELATION_GAP second,
   and said "stop at the first clear match". The protocol codebook defines
   no precedence. The human notes cite this priority explicitly (CF-08, 10,
   20, 23, 27). Part of the label disagreement is therefore produced by the
   instructions; the AI never saw them. Any future round must fix a
   precedence rule in the protocol and give it to every annotator.
3. **Codebook overlap.** Concentration in two labels shows the causes are not
   mutually exclusive as written. Range defects often also create
   occurrence or activation effects.
4. **Include-rule ambiguity.** CF-04 and CF-05 were excluded under a
   "no wrong effect / availability-only" rule that appears in the sheet's
   Step 1 text. Protocol §2 defines relevance as a proof/consumer
   disagreement and does not exclude availability explicitly. The protocol
   should decide this.
5. **Anchoring residue.** The sheet still showed AI-written summaries. The
   annotator corrected one of them (CF-01 note).
6. Single annotator, single source (zk-bug-tracker seed), 27 entries.
