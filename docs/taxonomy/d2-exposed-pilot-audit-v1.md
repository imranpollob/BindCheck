# D2 audit of the exposed Lane-X taxonomy pilot

**Date:** 2 November 2026  
**Purpose:** codebook refinement only; no relabeling and no new judgment

## Preserved observations

Lane X screened all 27 entries in the pinned 0xPARC tracker snapshot. Its AI
pass suggested 19 includes. One repository author later marked 17 includes
and 10 excludes on a sheet that still contained AI-written summaries. The
author/AI comparison reported 25/27 relevance agreement and 9/17 exact
single-cause agreement. Those numbers are preserved as descriptive history;
AI output is not an independent rater and the comparison is not inter-human
reliability.

The pilot has several additional exposure limits:

- only one seed collection was screened;
- tracker summaries, not the linked primary records, supplied the evidence;
- all 23 encountered families were logged as exposed;
- the human received an ordered “stop at the first clear match” cause rule
  absent from protocol v0.2.0; and
- another AI assistant helped interpret source descriptions, although it did
  not choose the recorded labels.

The existing ledger's empty annotation rounds and agreement reports correctly
show that no protocol-compliant independent round occurred.

## Ambiguities found and frozen response

| Pilot observation | Risk | v0.3.0 response |
|---|---|---|
| Eight of 17 jointly included items differed on the one cause code. | A forced single label confounds root cause and downstream manifestation. | Causes are multilabel, but only distinct evidenced root mechanisms qualify. Consequences have a separate axis. |
| Range/selector flaws were variously called relation, mapping, activation, occurrence, or representation defects. | Category overlap lets instructions drive the label. | Specific mechanism precedence is frozen. A range/non-binary selector is representation; downstream wrong selection or replay is not another cause without an independent defective relation. |
| `C_RELATION_GAP` described nearly every missing constraint. | The catch-all swallows specific mechanisms and creates artificial disagreement. | The code is residual: use it only when no specific mechanism fully describes the omitted dependency. |
| CF-04/CF-05 inclusion differed under an availability/no-wrong-effect instruction. | Missing accepted-transition/effect evidence can be mistaken for exclusion. | Missing primary boundary evidence is `unresolved`. `exclude` needs positive evidence of an out-of-scope or pure availability/DoS item. |
| AI one-line summaries remained on the “blind” sheet. | Anchoring can survive removal of explicit labels. | Future packets contain pinned primary evidence and policy only—no AI summary, prediction, E-grade, or other judgment. |
| The pilot counted findings from a seed aggregator. | Secondary summaries cannot establish producer relation, consumer effect, or policy. | A primary-evidence packet is required before a finding enters the scored fresh corpus. |
| Multiple entries can share application lineage. | Item-level uncertainty and agreement can overstate independent sample size. | The primary scored sample uses at most one canonical finding per conservative family. |

## What did not change

No CF-01–CF-27 relevance or cause entry is modified. The prior 17-item human
distribution and AI suggestions remain historical exposed data. The audit
does not infer which prior labels would change under v0.3.0, does not compute a
new coefficient, and does not convert `unresolved` or missing evidence into a
negative.

If two previously unexposed humans later re-annotate these packets, the result
must be labeled an **exposed-pilot study**. It may estimate reproducibility on
those known items but cannot validate a fresh corpus or erase family exposure.
