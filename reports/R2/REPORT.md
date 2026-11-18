# R2 — Audit-finding census (day-1 partial checkpoint)
Status: PARTIAL
Verdict/outcome: not yet stated (day-1 checkpoint; Solodit queries blocked)

## What was done
Day-1 checkpoint so the reviewer can check labelling early. See `findings.csv`,
`audits_read.csv`, `excluded-borderline.csv`. Final report replaces this file.

- Solodit: `solodit.cyfrin.io` redirects to `maintenance.cyfrin.io` in Chrome and
  returns HTTP 429 to WebFetch. Retried twice (log: `results/raw/R2/solodit/access-log.txt`).
  No Solodit query has been run yet. This blocks the "every Solodit query" criterion.
- Read public audit reports from Trail of Bits, Zellic, zkSecurity, Veridise,
  Nethermind, OpenZeppelin, Spearbit, Hexens, Oxorio, Auditware, yAcademy, EF PSE,
  and one Code4rena contest report.

## Results (snapshot; regenerate with `python3 reports/R2/r2tool.py stats`)
60 audits, 39 protocols, 49 findings included, 73 OUT (count only).

## Labelling rules used so far
See the final report. `label_source = AI` for every row.
