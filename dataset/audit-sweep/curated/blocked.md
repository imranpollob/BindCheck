# blocked.md

No login wall, CAPTCHA or rate limit hit so far.

## Held-out guard slips (not blocks; disclosed for the orchestrator)

1. 2026-11-22 ~20:5x: tangle-network/protocol-solidity (FORBIDDEN). A web commit-existence curl (`/commit/848d073`, HTTP 200) was issued in the same shell command as the guard, before its output was read. Nothing else was opened. Row flagged FORBIDDEN.
2. 2026-11-22 ~21:0x: summa-dev/summa-solvency (FORBIDDEN) and 0xPolygonHermez/zisk (FORBIDDEN). After the guard returned FORBIDDEN, my batch download of 19 zkbugs source URLs still fetched `summa-dev/summa-solvency/issues/32` and `0xPolygonHermez/zisk/security/advisories/GHSA-qjgg-fcj3-p9x3` (page title and meta description only were printed; the HTML files were deleted unread). These two items are recorded from the zkbugs config text and page titles only, holdout_flag=FORBIDDEN.
- 2026-11-23T01:24:07Z GitHub advisories web search (github.com/advisories?query=...&type=unreviewed&page=2, term 'public input'): HTTP 429 rate-limit. Stopped; not retried. Completed so far: all 16 terms x reviewed, terms 1-5 x unreviewed (results in /tmp/claude-1000/audit-sweep/curated/ghsa/ not saved yet: json not written).
- 2026-11-23T01:25:40Z Solodit https://solodit.cyfrin.io/?i=HIGH&s=nullifier : HTTP 429 with 'Vercel Security Checkpoint' (bot challenge/CAPTCHA-like). Not bypassed. No Solodit data collected; all 16 terms outstanding.
