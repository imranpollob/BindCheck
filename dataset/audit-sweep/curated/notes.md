# curated notes

| source | reports | IN | KEEP | BORDERLINE | DROP |
|---|---|---|---|---|---|
| 0xPARC zk-bug-tracker | 27 | 19 | 4 | 5 | 12 |
| GitHub Security Advisories | 15 | 5 | 0 | 3 | 2 |
| zkSecurity zkbugs | 41 | 27 | 13 | 14 | 91 |
| zkSecurity zkbugs (non-PDF source) | 19 | 6 | 0 | 1 | 10 |

Totals: 102 reports, 57 IN, 17 KEEP, 23 BORDERLINE, 115 DROP (rows include DUPLICATE-marked cross-source duplicates).

## Sources
- 0xPARC zk-bug-tracker: 27 entries (README @56a99667).
- zkSecurity zkbugs @212cc500: 140 configs, 41 audit docs + 19 issue/advisory pages; every config in an IN report has a findings row (dups marked DUPLICATE; many provisional DROPs, effect text not read; `covered-by:` tags for other agents' auditors).
- GitHub Advisories: 16 terms x reviewed/unreviewed, pages capped at 6 (queries.csv); 535 unique advisories, ~15 ZK-relevant screened; the rest are non-ZK noise (Adobe/Siemens/etc. matching "sp1"/"proof"). Raw: /tmp/claude-1000/audit-sweep/curated/ghsa/state.json. 429 occurred once; slow pass (30 s gaps) completed all queries.
- Solodit: BLOCKED (Vercel checkpoint). Orchestrator will do it by browser.

## Ambiguities
- PROTOCOL s3 "EVM consumer": library/circuit-only reports with no EVM consumer evidenced were set OUT/NON-EVM (rows note "re-screen candidate"); well-known rollups (Scroll, Polygon zkEVM) set IN.
- "findings_total" for zkbugs-derived rows comes from reports.json or ToC; not independently counted for large audits.
- zkbugs configs used as the unit for backfilled findings, so titles follow zkbugs naming.

## Protocol slips
See blocked.md (held-out guard slips: tangle-network/protocol-solidity, summa-dev/summa-solvency, 0xPolygonHermez/zisk).

## Known gaps
Panther (72), Veridise Telepathy (36), Matter Labs ZKEmail, Self reports: only a subset read in full (see per-report notes). Commit existence not checked for backfilled and GHSA rows.
