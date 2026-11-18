# PP discrepancies

The pipeline uses the tracked ledgers and final labels for numerical
aggregation. Each discrepancy below preserves the wording and provenance of
the existing evidence.

| Source claim | Tracked data and treatment |
|---|---|
| R2 `r2tool.py stats` prints **16** under “audits with >=1 H/C binding finding.” | The helper counts distinct audits from the full high/critical set, including P4. The findings CSV yields **16** audits across all classes and **7** with high/critical binding findings (P1–P3 or P5), consistent with the [R2 report prose](../R2/REPORT.md#answer-are-binding-flaws-p1p3-p5-frequent-in-audits-of-funded-protocols). The two counts are separately named in [T-audits.json](../../paper/generated/T-audits.json). |
| S2a revision 1 §R1.7 says “five FPs retired” in its P1 caveat. | The [candidate card ledger](../S2a/revision1/set-h-recomputed-cards.csv) accounts for the six original P1 FPs as **four** no longer warnings among analyzed cards, **one** retained FP, and **one** unavailable due to timeout. The [DEV precision table](../../paper/generated/T-dev-precision.tex) carries the unavailable count separately. |
| S2a revision 1 §R1.8 records a superseded inventory claim that all **13** P5 FPs were fixed. | The final revision and [candidate card ledger](../S2a/revision1/set-h-recomputed-cards.csv) agree on **six** no longer `VIOLATION` after analysis, **six** still `VIOLATION`, and **one** unavailable. The pipeline uses the final ledger. |
| S2a revision 1 §R1.4 gives **277** rows for the full executed set. The similarly named `spent-family-delta.json` accounts for **272** rows per pattern. | The [S2a aggregation code](../S2a/revision1_analysis.py) uses only `ANALYZED` and `HARNESS_TIMEOUT` for that JSON. The prose table and [PP attempted table](../../paper/generated/T-spent-patterns.json) include the **five** acquisition failures as candidate `UNKNOWN/UNKNOWN` and keep their original freeze-2 values. The **265** complete-case rows agree with the separate complete-case JSON. |

## Evidence qualifications

- The S2a P4 canonicality row has five retained TP warning cards and zero
  retained TP cards whose new pattern verdict is `VIOLATION`. These are
  distinct fields in the [recomputed summary](../S2a/revision1/set-h-recomputed-summary.json).
  The precision table uses the retained-warning denominator. Two original
  TP cards were unavailable.
- R1 records Aztec Connect as P5 with an alternative P1 label. The
  orchestrator favors P1 and the author review is deferred. The table
  groups the case by the recorded CSV class. AZ1 later retrieved the
  primary incident report and preserved R1's project-confirmed USD figure.
  [R1 report](../R1/REPORT.md) · [AZ1 report](../AZ1/REPORT.md) ·
  [Sprint decisions](../../docs/orchestration/DECISIONS.md)
- The historical freeze-2 run and Set H reports describe the original
  evaluation. The comparison with S2a uses spent families as development
  evidence. The original 56-row DEV run has its own table and denominator.
  [Freeze 2](../../docs/FREEZE-2.md) · [S2a revision 1](../S2a/REPORT.md#r17-set-h-recomputation--dev-not-held-out)
