# Preregistration amendment — adjudication sample (2026-11-09)

**Reason.** The one-shot held-out run produced 793 blind cards (331 BindCheck,
462 arm C). Two raters cannot label all of them before submission. This
amendment is committed **before any human label exists** on any held-out card.
The full sheets in `review/heldout/` remain valid for optional complete
labeling later; nothing in the run, cards or key is changed.

**Design.** Seeded (20261109), stratified random sample of 100 cards drawn by
`eval/draw_adjudication_sample.py` from `reports/heldout/warning-unblind-key.csv`.
The manifest records the card-id list and its SHA-256
(`review/heldout-sample/sample-manifest.json`).

| Tool | Stratum | Population | Sampled |
| --- | --- | ---: | ---: |
| BindCheck | P1 VIOLATION | 21 | 15 |
| BindCheck | P3 VIOLATION | 53 | 15 |
| BindCheck | P4 γ = δ VIOLATION | 56 | 10 |
| BindCheck | P4 scalar guard not found (UNKNOWN-verdict source warning) | 128 | 10 |
| BindCheck | P4 duplicate IC | 1 | 0 |
| BindCheck | P5 VIOLATION | 72 | 15 |
| Arm C | 10 native codes, proportional (largest remainder, min 1) | 462 | 35 |

**Estimation.** Precision is reported per stratum (TP / labeled, with Wilson
95% intervals) and as a population-weighted estimate per tool. `unclear` and
unresolved cards are reported separately and are never counted as TP or FP.
No comparative claim between tools is made (framing 2).

**Blinding.** The sample sheets omit `pattern` and `reason_code` for every row.
In the full sheets, the pattern column was blank only for arm C rows, which
revealed tool identity. Cards still show rule text, so blinding is partial;
this is disclosed.

**Procedure.** Unchanged from PREREG: two raters, separate sheets
(`SAMPLE-SHEET-rater-a.csv`, `SAMPLE-SHEET-rater-b.csv`), labels `TP` / `FP` /
`unclear` with a one-line reason, no exchange before both sheets are sealed,
then agreement and disagreement resolution with cited reasons.

## Addendum — self-contained rater packets (2026-11-09, still before any label)

Raters receive packets built by `eval/build_rater_packet.py` (guide and README
in `eval/rater-packet/`). Each packet holds set H (these 100 cards) and set D
(the 16 DEV cards W01–W16), a rater guide, full local copies of the analysed
Solidity files, and GitHub permalinks pinned to the analysed commits. To
strengthen blinding, every card's tool-specific rule statement and reason code
are replaced by a uniform warning kind (K1–K6) and a neutral concern sentence.
A scan confirmed that no tool reason code appears in the packets. Sheets are
`LABELS-set-{H,D}-rater-{A,B}.csv` and are keyed by `warning_id`, the same
ids as `SAMPLE-SHEET-*` and the DEV `BLIND-SHEET-*`.
