# curated progress

Source order: 1 0xPARC zk-bug-tracker, 2 zkSecurity zkbugs, 3 GitHub Security Advisories, 4 Solodit.

- [DONE] 1. 0xPARC zk-bug-tracker: 27 entries (README @56a99667): 19 IN, 8 OUT; 4 KEEP, 4 BORDERLINE, 11 DROP.
- [DONE] 2. zkSecurity zkbugs @212cc500: 140 bug configs -> 41 audit PDFs/MD + 19 non-PDF sources (issues/PRs/GHSA) = 60 report rows (27+6 IN, 13 KEEP, 13 BORDERLINE). Per-finding logging is partial for large reports (see notes in each reports.csv row); zkEVM Scroll reports aggregated without per-finding rows.
- [NEXT] 3. GitHub Security Advisories: web search UI (github.com/advisories?query=...) with the 16 fixed terms; log in queries.csv. Already covered via zkbugs: gnark, openvm x2, sp1 x4, risc0 x3, zisk.
- 4. Solodit: not started.
Tools: scripts in /tmp/claude-1000/audit-sweep/curated/scripts (zk.py helper, addrows.py appends w/ dedupe; gen0xparc.py overwrites - do NOT rerun).
API calls used: 1 (zkbugs tree) at ~20:10 local.
